#!/usr/bin/env python3
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

BASE_URL = "https://www.binance.com/bapi/composite/v1/public/cms/article/catalog/list/query"
DETAIL_URL = "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query"
GENERAL_CATALOG_ID = 48
PAGE_SIZE = 40
OUTPUT_LIMIT = 5
DAYS_BACK = 30

LAUNCHPOOL_KEYWORDS = ["launchpool", "megadrop", "airdrop"]
PROMOTION_KEYWORDS = ["earn", "simple earn", "staking", "promotion", "campaign"]


def fetch_catalog(catalog_id, page_size=PAGE_SIZE):
    url = BASE_URL + "?" + urllib.parse.urlencode({
        "catalogId": catalog_id,
        "pageNo": 1,
        "pageSize": page_size,
    })
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.binance.com/en/support/announcement",
            "Accept": "application/json, text/plain, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    return (data.get("data") or {}).get("articles") or []


def format_publish_date(value):
    try:
        ts = int(value)
        if ts > 10_000_000_000:
            ts //= 1000
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return None


def fetch_article_publish_date(code):
    url = DETAIL_URL + "?" + urllib.parse.urlencode({"articleCode": code})
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.binance.com/en/support/announcement",
            "Accept": "application/json, text/plain, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    detail = data.get("data") or {}
    return format_publish_date(detail.get("publishDate"))


def infer_date(article):
    publish_date = article.get("publishDate")
    if publish_date:
        date = format_publish_date(publish_date)
        if date:
            return date
    code = article.get("code")
    if code:
        try:
            date = fetch_article_publish_date(code)
            if date:
                return date
        except Exception:
            pass
    title = article.get("title") or ""
    match = re.search(r"(20\d{2}-\d{2}-\d{2})", title)
    return match.group(1) if match else None


def within_days(date_str, days=DAYS_BACK):
    if not date_str:
        return True
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except Exception:
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return dt >= cutoff


def article_link(article):
    code = article.get("code")
    if code:
        return f"https://www.binance.com/en/support/announcement/{code}"
    return "https://www.binance.com/en/support/announcement"


def normalize(articles):
    items = []
    for article in articles:
        items.append({
            "id": article.get("id"),
            "code": article.get("code"),
            "title": article.get("title"),
            "date": infer_date(article),
            "link": article_link(article),
        })
    return items


def title_matches_any(title, keywords):
    lower = (title or "").lower()
    return any(keyword in lower for keyword in keywords)


def filter_launchpool(items):
    return [item for item in items if title_matches_any(item.get("title"), LAUNCHPOOL_KEYWORDS)]


def filter_promotion(items):
    return [item for item in items if title_matches_any(item.get("title"), PROMOTION_KEYWORDS)]


def choose_mode(query):
    lowered = query.lower()
    if any(word in lowered for word in ["launchpool", "megadrop", "airdrop"]):
        return "launchpool"
    if any(word in lowered for word in ["earn", "simple earn", "staking", "promotion"]):
        return "promotion"
    return "new-campaign"


def build_payload(query):
    mode = choose_mode(query)
    items = normalize(fetch_catalog(GENERAL_CATALOG_ID))

    if mode == "launchpool":
        chosen = filter_launchpool(items)
    elif mode == "promotion":
        chosen = filter_promotion(items)
    else:
        chosen = [item for item in items if title_matches_any(item.get("title"), LAUNCHPOOL_KEYWORDS + PROMOTION_KEYWORDS)]

    chosen = [item for item in chosen if within_days(item.get("date"))][:OUTPUT_LIMIT]

    return {
        "title": "🎁 New Campaign",
        "mode": mode,
        "days": DAYS_BACK,
        "items": chosen,
    }


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]).strip()
    print(json.dumps(build_payload(query), indent=2))
