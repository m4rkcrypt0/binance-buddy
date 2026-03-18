#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
DATA_FILE = os.path.join(ROOT_DIR, "data", "alerts.json")
SEEN_CONTENT_FILE = os.path.join(ROOT_DIR, "data", "seen_content.json")
API_URL = "https://api.binance.com/api/v3/ticker/price"
ANNOUNCEMENTS_URL = "https://www.binance.com/bapi/composite/v1/public/cms/article/catalog/list/query"
GENERAL_CATALOG_ID = 48
DELISTING_CATALOG_ID = 161
PAGE_SIZE = 30
USER_AGENT = "alert-manager/1.0"
LAUNCHPOOL_KEYWORDS = ["launchpool", "megadrop", "airdrop"]
PROMOTION_KEYWORDS = ["earn", "simple earn", "staking", "promotion", "campaign"]


def utc_now():
    return datetime.now(timezone.utc)


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def load_store():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        data = {"alerts": []}
    alerts = data.get("alerts", [])
    if not isinstance(alerts, list):
        raise ValueError("alerts.json must contain an alerts array")
    return data


def load_seen_content():
    try:
        with open(SEEN_CONTENT_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    return data


def save_store(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def save_seen_content(data):
    os.makedirs(os.path.dirname(SEEN_CONTENT_FILE), exist_ok=True)
    with open(SEEN_CONTENT_FILE, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def active_alerts(alerts):
    return [alert for alert in alerts if alert.get("active", True)]


def http_get_json(url, user_agent="Mozilla/5.0"):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Referer": "https://www.binance.com/en/support/announcement",
            "Accept": "application/json, text/plain, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_catalog(catalog_id, page_size=PAGE_SIZE):
    url = ANNOUNCEMENTS_URL + "?" + urllib.parse.urlencode({
        "catalogId": catalog_id,
        "pageNo": 1,
        "pageSize": page_size,
    })
    data = http_get_json(url)
    return (data.get("data") or {}).get("articles") or []


def article_link(article):
    code = article.get("code")
    title = article.get("title", "")
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:120]
    if code:
        return f"https://www.binance.com/en/support/announcement/{slug}-{code}"
    return "https://www.binance.com/en/support/announcement"


def article_marker(article):
    return str(article.get("code") or article.get("id") or article_link(article))


def article_payload(article):
    return {
        "marker": article_marker(article),
        "title": article.get("title"),
        "link": article_link(article),
    }


def choose_latest_item(alert_type):
    general_items = fetch_catalog(GENERAL_CATALOG_ID)
    if alert_type == "announcement":
        return article_payload(general_items[0]) if general_items else None
    if alert_type == "listing":
        for item in general_items:
            title = (item.get("title") or "").lower()
            if re.search(r"\bwill list\b", title) and "delist" not in title:
                return article_payload(item)
        return None
    if alert_type == "launchpool":
        for item in general_items:
            title = (item.get("title") or "").lower()
            if any(keyword in title for keyword in LAUNCHPOOL_KEYWORDS):
                return article_payload(item)
        return None
    if alert_type in {"campaign", "promotion"}:
        for item in general_items:
            title = (item.get("title") or "").lower()
            if any(keyword in title for keyword in PROMOTION_KEYWORDS):
                return article_payload(item)
        return None
    if alert_type == "delisting":
        delisting_items = fetch_catalog(DELISTING_CATALOG_ID)
        for item in delisting_items:
            title = (item.get("title") or "").lower()
            if any(k in title for k in ["delist", "removal of", "will remove", "cease support"]):
                return article_payload(item)
        return None
    return None


def fetch_prices(symbols):
    if not symbols:
        return {}
    query = urllib.parse.urlencode({"symbols": json.dumps(sorted(symbols), separators=(",", ":"))})
    url = f"{API_URL}?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=15) as response:
        payload = response.read().decode("utf-8")
    data = json.loads(payload)
    if isinstance(data, dict) and data.get("code"):
        raise RuntimeError(data.get("msg") or "Binance API error")
    prices = {}
    for item in data:
        try:
            prices[item["symbol"]] = float(item["price"])
        except (KeyError, TypeError, ValueError):
            continue
    return prices


def format_target(target):
    target = float(target)
    if target.is_integer():
        return f"{int(target):,}"
    return f"{target:,.8f}".rstrip("0").rstrip(".")


def build_trigger_text(alert, current_price=None, item=None):
    alert_type = alert.get("type")
    if alert_type in {"price-above", "price-below"}:
        symbol = str(alert.get("symbol", "")).replace("USDT", "")
        target = format_target(alert.get("target"))
        if alert_type == "price-above":
            return f"🚨 Alert Triggered\n\n📈 {symbol} broke above {target}\nNow: ${current_price:,.2f}"
        if alert_type == "price-below":
            return f"🚨 Alert Triggered\n\n📉 {symbol} dropped below {target}\nNow: ${current_price:,.2f}"
    headings = {
        "announcement": "🚨 New Announcement Detected",
        "listing": "🚨 New Listing Detected",
        "delisting": "🚨 New Delisting Detected",
        "launchpool": "🚨 New Launchpool Detected",
        "campaign": "🚨 New Campaign Detected",
        "promotion": "🚨 New Promotion Detected",
    }
    labels = {
        "announcement": "📢 New Binance Announcement",
        "listing": "🟢 New Binance Listing",
        "delisting": "🔴 New Binance Delisting",
        "launchpool": "🚀 New Binance launchpool",
        "campaign": "🎁 New Binance campaign",
        "promotion": "🎉 New Binance promotion",
    }
    title = (item or {}).get("title") or "Detected"
    link = (item or {}).get("link")
    text = f"{headings.get(alert_type, '🚨 Alert Triggered')}\n\n{labels.get(alert_type, '🔔 Alert Triggered')}\n\n{title}"
    if link:
        text += f"\n{link}"
    return text


def parse_chat_route(chat_id):
    if not chat_id or ":" not in chat_id:
        raise ValueError(f"Unsupported chat id: {chat_id}")
    channel, target = chat_id.split(":", 1)
    channel = channel.strip()
    target = target.strip()
    if not channel or not target:
        raise ValueError(f"Unsupported chat id: {chat_id}")
    return channel, target


def send_message(chat_id, text, dry_run=False):
    channel, target = parse_chat_route(chat_id)
    command = [
        "openclaw",
        "message",
        "send",
        "--channel",
        channel,
        "--target",
        target,
        "--message",
        text,
        "--json",
    ]
    if dry_run:
        command.append("--dry-run")
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "command": command,
    }


def evaluate_alert(alert, prices):
    symbol = alert.get("symbol")
    if symbol not in prices:
        return False, None
    current = prices[symbol]
    target = float(alert.get("target", 0))
    alert_type = alert.get("type")
    if alert_type == "price-above":
        return current >= target, current
    if alert_type == "price-below":
        return current <= target, current
    return False, current


def main():
    parser = argparse.ArgumentParser(description="Run one deterministic alert-manager check pass.")
    parser.add_argument("--dry-run-send", action="store_true", help="Use openclaw message send --dry-run")
    args = parser.parse_args()

    result = {
        "ok": True,
        "expired": 0,
        "triggered": 0,
        "remainingActive": 0,
        "sendFailures": 0,
        "errors": [],
    }

    try:
        data = load_store()
        seen_content = load_seen_content()
        alerts = active_alerts(data.get("alerts", []))
        now = utc_now()

        kept = []
        price_alerts = []
        content_types_needed = set()
        for alert in alerts:
            if alert.get("type") in {"price-above", "price-below"}:
                expires_at = alert.get("expiresAt")
                if expires_at:
                    try:
                        if parse_time(expires_at) <= now:
                            result["expired"] += 1
                            continue
                    except ValueError:
                        result["expired"] += 1
                        continue
                price_alerts.append(alert)
            else:
                content_types_needed.add(alert.get("type"))
            kept.append(alert)

        symbols = sorted({alert.get("symbol") for alert in price_alerts if alert.get("symbol")})
        prices = fetch_prices(symbols) if symbols else {}
        latest_items = {}
        for alert_type in sorted(t for t in content_types_needed if t):
            latest_items[alert_type] = choose_latest_item(alert_type)

        final_alerts = []
        for alert in kept:
            alert_type = alert.get("type")
            if alert_type in {"price-above", "price-below"}:
                triggered, current = evaluate_alert(alert, prices)
                item = None
            else:
                current = None
                item = latest_items.get(alert_type)
                previous = seen_content.get(alert_type) or {}
                previous_marker = previous.get("marker")
                current_marker = (item or {}).get("marker")
                triggered = bool(current_marker and current_marker != previous_marker)
            if not triggered:
                final_alerts.append(alert)
                continue
            send_result = send_message(alert.get("chatId"), build_trigger_text(alert, current, item), dry_run=args.dry_run_send)
            if send_result["ok"]:
                result["triggered"] += 1
                if alert_type not in {"price-above", "price-below"} and item:
                    seen_content[alert_type] = item
            else:
                result["sendFailures"] += 1
                result["errors"].append({
                    "alertId": alert.get("id"),
                    "message": "Failed to send trigger notification",
                    "send": send_result,
                })
                final_alerts.append(alert)

        data["alerts"] = final_alerts
        save_store(data)
        save_seen_content(seen_content)
        result["remainingActive"] = len(active_alerts(final_alerts))
    except urllib.error.HTTPError as exc:
        result["ok"] = False
        result["errors"].append({"message": f"Binance HTTP error {exc.code}"})
    except urllib.error.URLError as exc:
        result["ok"] = False
        result["errors"].append({"message": f"Binance network error: {exc.reason}"})
    except Exception as exc:
        result["ok"] = False
        result["errors"].append({"message": str(exc)})

    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
