#!/usr/bin/env python3
import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
DATA_FILE = os.path.join(ROOT_DIR, "data", "alerts.json")
SEEN_CONTENT_FILE = os.path.join(ROOT_DIR, "data", "seen_content.json")
MAX_ACTIVE_ALERTS = 20
DEFAULT_EXPIRY_MINUTES = 30
WATCHER_SCRIPT = os.path.join(os.path.dirname(__file__), "watch_alerts.py")
WATCHER_LOG = os.path.join(ROOT_DIR, "data", "alert-watcher.log")
WATCHER_LOCK = os.path.join(ROOT_DIR, "data", "alert-watcher.lock")
ANNOUNCEMENTS_URL = "https://www.binance.com/bapi/composite/v1/public/cms/article/catalog/list/query"
GENERAL_CATALOG_ID = 48
DELISTING_CATALOG_ID = 161
PAGE_SIZE = 30

ALIASES = {
    "BITCOIN": "BTC",
    "ETHEREUM": "ETH",
    "SOLANA": "SOL",
    "RIPPLE": "XRP",
    "DOGECOIN": "DOGE",
    "SHIBA": "SHIB",
    "SHIBAINU": "SHIB",
    "BINANCECOIN": "BNB",
    "BINANCE": "BNB",
    "POLYGON": "POL",
    "MATIC": "POL",
    "AVALANCHE": "AVAX",
    "CHAINLINK": "LINK",
    "LITECOIN": "LTC",
    "CARDANO": "ADA",
    "TRON": "TRX",
    "TONCOIN": "TON",
    "PEPECOIN": "PEPE",
}

ALLOWED_TYPES = {"price-above", "price-below", "announcement", "listing", "delisting", "launchpool", "campaign", "promotion"}
LAUNCHPOOL_KEYWORDS = ["launchpool", "megadrop", "airdrop"]
PROMOTION_KEYWORDS = ["earn", "simple earn", "staking", "promotion", "campaign"]


CONTENT_LABELS = {
    "announcement": "new Binance announcement",
    "listing": "new Binance listing",
    "delisting": "new Binance delisting",
    "launchpool": "new Binance launchpool",
    "campaign": "new Binance campaign",
    "promotion": "new Binance promotion",
}


def utc_now():
    return datetime.now(timezone.utc)


def parse_iso_time(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)


def isoformat_z(value):
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_store():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        data = {"alerts": []}
    except json.JSONDecodeError:
        raise ValueError("alerts.json is invalid JSON")

    alerts = data.get("alerts")
    if not isinstance(alerts, list):
        raise ValueError("alerts.json must contain an alerts array")
    return data


def load_seen_content():
    try:
        with open(SEEN_CONTENT_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        data = {
            "announcement": {},
            "listing": {},
            "delisting": {},
            "launchpool": {},
            "campaign": {},
            "promotion": {},
        }
    except json.JSONDecodeError:
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


def active_alerts_for_chat(alerts, chat_id):
    return [alert for alert in alerts if alert.get("chatId") == chat_id and alert.get("active", True)]


def http_get_json(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
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
        if general_items:
            return article_payload(general_items[0])
        return None
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


def normalize_symbol(raw_symbol):
    if not raw_symbol:
        raise ValueError("Missing symbol")

    token = "".join(ch for ch in raw_symbol.upper() if ch.isalnum())
    if not token:
        raise ValueError("Missing symbol")
    if token.endswith("USDT") and len(token) > 4:
        token = token[:-4]
    token = ALIASES.get(token, token)
    if not token.isalnum():
        raise ValueError("Invalid symbol")
    return f"{token}USDT"


def parse_target(raw_target):
    if raw_target is None:
        raise ValueError("Missing target price")
    cleaned = str(raw_target).replace(",", "").strip()
    try:
        value = float(cleaned)
    except ValueError as exc:
        raise ValueError("Target price must be numeric") from exc
    if value <= 0:
        raise ValueError("Target price must be greater than zero")
    return value


def next_id(alerts):
    highest = 0
    for alert in alerts:
        try:
            highest = max(highest, int(alert.get("id", 0)))
        except (TypeError, ValueError):
            continue
    return highest + 1


def same_price_target(left, right):
    return abs(float(left) - float(right)) < 1e-9


def find_duplicate(alerts, chat_id, alert_type, symbol, target):
    for alert in active_alerts_for_chat(alerts, chat_id):
        if alert.get("type") != alert_type:
            continue
        if alert_type in {"price-above", "price-below"}:
            if alert.get("symbol") != symbol:
                continue
            if not same_price_target(alert.get("target"), target):
                continue
            return alert
        return alert
    return None


def format_target(target):
    if float(target).is_integer():
        return f"{int(target):,}"
    return f"{target:,.8f}".rstrip("0").rstrip(".")


def format_alert_title(alert):
    alert_type = alert.get("type")
    if alert_type in {"price-above", "price-below"}:
        symbol = str(alert.get("symbol", "")).replace("USDT", "")
        target = format_target(float(alert.get("target", 0)))
        if alert_type == "price-above":
            return f"{symbol} above {target}"
        return f"{symbol} below {target}"
    return CONTENT_LABELS.get(alert_type, str(alert_type))


def build_create_message(alert):
    title = format_alert_title(alert)
    if title.startswith("new "):
        title = "New " + title[4:]
    if alert.get("type") in {"price-above", "price-below"}:
        return f"🔔 Alert Created\n\n{title} for the next {DEFAULT_EXPIRY_MINUTES} minutes."
    return f"🔔 Alert Created\n\n{title}."


def build_delete_message(alert):
    return f"❌ Alert Deleted: {format_alert_title(alert)}."


def humanize_remaining(expires_at):
    if not expires_at:
        return None
    try:
        seconds = int((parse_iso_time(expires_at) - utc_now()).total_seconds())
    except Exception:
        return None
    if seconds <= 0:
        return "expired"
    minutes = max(1, (seconds + 59) // 60)
    if minutes < 60:
        return f"{minutes}m left"
    hours = minutes // 60
    rem_minutes = minutes % 60
    if rem_minutes:
        return f"{hours}h {rem_minutes}m left"
    return f"{hours}h left"


def serialize_alert_for_list(alert):
    item = dict(alert)
    item["title"] = format_alert_title(alert)
    item["expiresIn"] = humanize_remaining(alert.get("expiresAt"))
    item["persistent"] = alert.get("type") not in {"price-above", "price-below"}
    if item["persistent"] and not item["expiresIn"]:
        item["expiresIn"] = "active"
    return item


def watcher_running():
    os.makedirs(os.path.dirname(WATCHER_LOCK), exist_ok=True)
    with open(WATCHER_LOCK, "a+", encoding="utf-8") as lock_handle:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        return False


def ensure_watcher_running():
    if watcher_running():
        return False
    os.makedirs(os.path.dirname(WATCHER_LOG), exist_ok=True)
    with open(WATCHER_LOG, "a", encoding="utf-8") as log_handle:
        subprocess.Popen(
            [WATCHER_SCRIPT],
            stdout=log_handle,
            stderr=log_handle,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    return True


def matches_filter(alert, alert_type=None, symbol=None, target=None):
    if alert_type and alert.get("type") != alert_type:
        return False
    if symbol and alert.get("symbol") != symbol:
        return False
    if target is not None:
        if alert.get("target") is None or not same_price_target(alert.get("target"), target):
            return False
    return True


def cmd_create(args):
    if args.type not in ALLOWED_TYPES:
        raise ValueError(f"Unsupported alert type: {args.type}")
    if not args.chat_id:
        raise ValueError("Missing chat id")

    data = load_store()
    alerts = data["alerts"]
    current_active = active_alerts_for_chat(alerts, args.chat_id)
    if len(current_active) >= MAX_ACTIVE_ALERTS:
        return {
            "ok": False,
            "error": f"You already have {MAX_ACTIVE_ALERTS} active alerts. Delete one before adding another.",
        }

    symbol = None
    target = None
    if args.type in {"price-above", "price-below"}:
        symbol = normalize_symbol(args.symbol)
        target = parse_target(args.target)

    duplicate = find_duplicate(alerts, args.chat_id, args.type, symbol, target)
    if duplicate:
        return {
            "ok": False,
            "error": "You already have that alert active.",
            "duplicateId": duplicate.get("id"),
        }

    created_at = utc_now()
    alert = {
        "id": next_id(alerts),
        "chatId": args.chat_id,
        "type": args.type,
        "createdAt": isoformat_z(created_at),
        "active": True,
    }
    if args.type in {"price-above", "price-below"}:
        expires_at = created_at + timedelta(minutes=DEFAULT_EXPIRY_MINUTES)
        alert["expiresAt"] = isoformat_z(expires_at)
    if symbol is not None:
        alert["symbol"] = symbol
    if target is not None:
        alert["target"] = target

    if args.type not in {"price-above", "price-below"}:
        seen = load_seen_content()
        if not seen.get(args.type):
            try:
                latest = choose_latest_item(args.type)
            except Exception as exc:
                raise ValueError(f"Could not initialize the Binance content baseline for that alert right now: {exc}") from exc
            seen[args.type] = latest or {}
            save_seen_content(seen)

    alerts.append(alert)
    save_store(data)
    started_watcher = ensure_watcher_running()

    return {
        "ok": True,
        "message": build_create_message(alert),
        "alert": alert,
        "watcherStarted": started_watcher,
    }


def cmd_list(args):
    if not args.chat_id:
        raise ValueError("Missing chat id")
    data = load_store()
    alerts = sorted(active_alerts_for_chat(data["alerts"], args.chat_id), key=lambda item: int(item.get("id", 0)))
    return {
        "ok": True,
        "count": len(alerts),
        "alerts": [serialize_alert_for_list(alert) for alert in alerts],
        "watcherRunning": watcher_running() if alerts else False,
    }


def cmd_delete(args):
    if not args.chat_id:
        raise ValueError("Missing chat id")
    if args.id is None:
        raise ValueError("Missing alert id")

    data = load_store()
    alerts = data["alerts"]
    kept = []
    deleted = None
    for alert in alerts:
        same_chat = alert.get("chatId") == args.chat_id
        same_id = str(alert.get("id")) == str(args.id)
        if same_chat and same_id and alert.get("active", True):
            deleted = alert
            continue
        kept.append(alert)

    if deleted is None:
        return {
            "ok": False,
            "error": f"Alert {args.id} not found.",
        }

    data["alerts"] = kept
    save_store(data)
    return {
        "ok": True,
        "message": build_delete_message(deleted),
        "deleted": deleted,
    }


def cmd_delete_match(args):
    if not args.chat_id:
        raise ValueError("Missing chat id")
    if not args.type:
        raise ValueError("Missing alert type")
    if args.type not in ALLOWED_TYPES:
        raise ValueError(f"Unsupported alert type: {args.type}")

    symbol = normalize_symbol(args.symbol) if args.symbol else None
    target = parse_target(args.target) if args.target is not None else None

    data = load_store()
    active = active_alerts_for_chat(data["alerts"], args.chat_id)
    matches = [alert for alert in active if matches_filter(alert, args.type, symbol, target)]
    if not matches:
        return {"ok": False, "error": "No matching active alert found."}
    if len(matches) > 1:
        return {
            "ok": False,
            "error": "More than one matching alert found. Delete by id instead.",
            "matches": [serialize_alert_for_list(alert) for alert in matches],
        }

    match = matches[0]
    kept = [alert for alert in data["alerts"] if not (alert.get("chatId") == args.chat_id and str(alert.get("id")) == str(match.get("id")) and alert.get("active", True))]
    data["alerts"] = kept
    save_store(data)
    return {
        "ok": True,
        "message": build_delete_message(match),
        "deleted": match,
    }


def cmd_status(args):
    if not args.chat_id:
        raise ValueError("Missing chat id")
    data = load_store()
    active = active_alerts_for_chat(data["alerts"], args.chat_id)
    counts = {}
    for alert in active:
        counts[alert.get("type")] = counts.get(alert.get("type"), 0) + 1
    return {
        "ok": True,
        "activeCount": len(active),
        "countsByType": counts,
        "watcherRunning": watcher_running() if active else False,
        "maxActiveAlerts": MAX_ACTIVE_ALERTS,
    }


def build_parser():
    parser = argparse.ArgumentParser(description="Manage alert-manager state for price alerts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Create a new alert")
    create_parser.add_argument("--type", required=True, help="Alert type, e.g. price-above")
    create_parser.add_argument("--symbol", help="Asset symbol, e.g. BTC or BTCUSDT")
    create_parser.add_argument("--target", help="Target price")
    create_parser.add_argument("--chat-id", required=True, help="Chat/session route key")

    list_parser = subparsers.add_parser("list", help="List active alerts")
    list_parser.add_argument("--chat-id", required=True, help="Chat/session route key")

    delete_parser = subparsers.add_parser("delete", help="Delete an alert by id")
    delete_parser.add_argument("--id", required=True, help="Alert id")
    delete_parser.add_argument("--chat-id", required=True, help="Chat/session route key")

    delete_match_parser = subparsers.add_parser("delete-match", help="Delete one alert by deterministic match")
    delete_match_parser.add_argument("--type", required=True, help="Alert type")
    delete_match_parser.add_argument("--symbol", help="Asset symbol for price alerts")
    delete_match_parser.add_argument("--target", help="Target price for exact price alert match")
    delete_match_parser.add_argument("--chat-id", required=True, help="Chat/session route key")

    status_parser = subparsers.add_parser("status", help="Show alert-manager status for a chat")
    status_parser.add_argument("--chat-id", required=True, help="Chat/session route key")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "create":
            result = cmd_create(args)
        elif args.command == "list":
            result = cmd_list(args)
        elif args.command == "delete":
            result = cmd_delete(args)
        elif args.command == "delete-match":
            result = cmd_delete_match(args)
        elif args.command == "status":
            result = cmd_status(args)
        else:
            raise ValueError(f"Unsupported command: {args.command}")
    except ValueError as exc:
        result = {"ok": False, "error": str(exc)}

    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
