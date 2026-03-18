#!/usr/bin/env python3
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

BASE_URL = "https://www.binance.com/bapi/composite/v1/public/cms/article/catalog/list/query"
GENERAL_CATALOG_ID = 48
DELISTING_CATALOG_ID = 161
PAGE_SIZE = 30
OUTPUT_LIMIT = 5
DAYS_BACK = 30


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


def infer_release_date(article):
    publish_date = article.get("publishDate")
    if publish_date:
        try:
            ts = int(publish_date)
            if ts > 10_000_000_000:
                ts //= 1000
            return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        except Exception:
            pass

    title = article.get("title") or ""
    match = re.search(r"(20\d{2}-\d{2}-\d{2})", title)
    if match:
        return match.group(1)
    return None


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
    title = article.get("title", "")
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:120]
    if code:
        return f"https://www.binance.com/en/support/announcement/{slug}-{code}"
    return "https://www.binance.com/en/support/announcement"


def normalize(articles):
    items = []
    for article in articles:
        date = infer_release_date(article)
        items.append({
            "id": article.get("id"),
            "code": article.get("code"),
            "title": article.get("title"),
            "releaseDate": date,
            "link": article_link(article),
        })
    return items


def filter_listings(items):
    patterns = [r"\bwill list\b", r"\bwill add\b.*\b(futures|margin|earn|convert|buy crypto)\b", r"\bintroducing\b.*\bairdrop|launchpool\b"]
    result = []
    for item in items:
        title = (item.get("title") or "").lower()
        if "delist" in title or "removal" in title:
            continue
        if re.search(r"\bwill list\b", title) or title.startswith("binance will list"):
            result.append(item)
    return result


def filter_delistings(items):
    result = []
    for item in items:
        title = (item.get("title") or "").lower()
        if any(k in title for k in ["delist", "removal of", "will remove", "cease support"]):
            result.append(item)
    return result


def choose_mode(query):
    lowered = query.lower()
    if "delist" in lowered or "delisting" in lowered or "remove" in lowered:
        return "delistings"
    if "list" in lowered or "listing" in lowered:
        return "listings"
    return "general"


def build_payload(query):
    mode = choose_mode(query)
    general_items = normalize(fetch_catalog(GENERAL_CATALOG_ID))
    delisting_items = normalize(fetch_catalog(DELISTING_CATALOG_ID))

    if mode == "general":
        items = [item for item in general_items if within_days(item.get("releaseDate"))][:OUTPUT_LIMIT]
    elif mode == "listings":
        items = [item for item in filter_listings(general_items) if within_days(item.get("releaseDate"))][:OUTPUT_LIMIT]
    else:
        items = [item for item in filter_delistings(delisting_items) if within_days(item.get("releaseDate"))][:OUTPUT_LIMIT]

    return {
        "title": "📢 Binance Announcements",
        "mode": mode,
        "days": DAYS_BACK,
        "items": items,
    }


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]).strip()
    print(json.dumps(build_payload(query), indent=2))
