#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

KLINES_URL = "https://api.binance.com/api/v3/klines"
EXCHANGE_INFO_URL = "https://api.binance.com/api/v3/exchangeInfo"
MAX_SYMBOLS = 5
CACHE_TTL_SECONDS = 6 * 60 * 60
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "binance-historical-price")
CACHE_FILE = os.path.join(CACHE_DIR, "exchange_info_cache.json")
STOPWORDS = {
    "show", "me", "the", "price", "of", "on", "for", "what", "was", "is",
    "give", "please", "pls", "close", "closing", "spot", "binance", "at",
    "today", "yesterday"
}
ALIASES = {
    "BITCOIN": "BTC",
    "ETHEREUM": "ETH",
    "SOLANA": "SOL",
    "RIPPLE": "XRP",
    "DOGECOIN": "DOGE",
    "SHIBAINU": "SHIB",
    "POLYGON": "POL",
    "MATIC": "POL",
    "AVALANCHE": "AVAX",
    "CHAINLINK": "LINK",
    "LITECOIN": "LTC",
    "CARDANO": "ADA",
    "TRON": "TRX",
    "TONCOIN": "TON",
}
PHRASE_ALIASES = {
    "shiba inu": "SHIB",
    "binance coin": "BNB",
}
MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9,
    "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}


def http_get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "binance-historical-price-skill/1.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def load_cached_market_symbols():
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        created_at = payload.get("createdAt", 0)
        symbols = payload.get("symbols", [])
        if not isinstance(symbols, list):
            return None
        if time.time() - created_at > CACHE_TTL_SECONDS:
            return None
        return set(symbols)
    except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError, ValueError):
        return None


def save_cached_market_symbols(symbols):
    payload = {"createdAt": int(time.time()), "symbols": sorted(symbols)}
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
    except OSError:
        pass


def get_available_market_symbols():
    cached = load_cached_market_symbols()
    if cached is not None:
        return cached
    data = http_get_json(EXCHANGE_INFO_URL)
    available = {item["symbol"] for item in data.get("symbols", [])}
    save_cached_market_symbols(available)
    return available


def normalize_text(values):
    joined = " ".join(values).strip()
    lowered = joined.lower()
    for phrase, replacement in PHRASE_ALIASES.items():
        lowered = lowered.replace(phrase, f" {replacement.lower()} ")
    return lowered


def parse_date(text, today=None):
    today = today or dt.datetime.now(dt.timezone.utc).date()
    cleaned = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", text.lower())

    if "yesterday" in cleaned:
        return today - dt.timedelta(days=1)
    if "today" in cleaned:
        return today

    iso_match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", cleaned)
    if iso_match:
        year, month, day = map(int, iso_match.groups())
        return dt.date(year, month, day)

    month_names = "|".join(sorted(MONTHS.keys(), key=len, reverse=True))
    pattern1 = re.search(rf"\b({month_names})\s+(\d{{1,2}})(?:\s+(\d{{4}}))?\b", cleaned)
    if pattern1:
        month = MONTHS[pattern1.group(1)]
        day = int(pattern1.group(2))
        year = int(pattern1.group(3)) if pattern1.group(3) else today.year
        return dt.date(year, month, day)

    pattern2 = re.search(rf"\b(\d{{1,2}})\s+({month_names})(?:\s+(\d{{4}}))?\b", cleaned)
    if pattern2:
        day = int(pattern2.group(1))
        month = MONTHS[pattern2.group(2)]
        year = int(pattern2.group(3)) if pattern2.group(3) else today.year
        return dt.date(year, month, day)

    return None


def parse_symbols(text):
    parts = re.findall(r"[A-Za-z]+", text)
    tokens = []
    truncated = False
    seen = set()
    for part in parts:
        if part in MONTHS:
            continue
        if part in STOPWORDS:
            continue
        token = part.upper()
        if token.endswith("USDT") and len(token) > 4:
            token = token[:-4]
        token = ALIASES.get(token, token)
        if token.lower() in STOPWORDS:
            continue
        if token not in seen:
            seen.add(token)
            if len(tokens) >= MAX_SYMBOLS:
                truncated = True
                continue
            tokens.append(token)
    return tokens, truncated


def format_price(value):
    number = float(value)
    if number >= 1:
        decimals = 2
    elif number >= 0.1:
        decimals = 4
    elif number >= 0.01:
        decimals = 5
    elif number >= 0.001:
        decimals = 6
    elif number >= 0.0001:
        decimals = 7
    else:
        decimals = 8
    return f"{number:,.{decimals}f}"


def format_money(value, decimals=0):
    return f"{float(value):,.{decimals}f}"


def format_api_error(exc):
    if isinstance(exc, urllib.error.HTTPError):
        if exc.code == 429:
            return "Binance is rate-limiting right now. Try again in a moment."
        if 500 <= exc.code < 600:
            return "Binance is having server issues right now. Try again shortly."
        return f"Binance request failed with HTTP {exc.code}."
    if isinstance(exc, urllib.error.URLError):
        return "Could not reach Binance right now. Check the connection and try again."
    return "Binance historical data is temporarily unavailable. Try again shortly."


def fetch_daily_kline(symbol, day):
    start = dt.datetime.combine(day, dt.time(0, 0), tzinfo=dt.timezone.utc)
    end = start + dt.timedelta(days=1)
    query = urllib.parse.urlencode({
        "symbol": f"{symbol}USDT",
        "interval": "1d",
        "startTime": int(start.timestamp() * 1000),
        "endTime": int(end.timestamp() * 1000),
        "limit": 1,
    })
    url = f"{KLINES_URL}?{query}"
    data = http_get_json(url)
    return data[0] if data else None


def format_block(symbol, day, kline):
    return (
        f"🕰️ {symbol} — {day.isoformat()}\n\n"
        f"💵 Close: ${format_price(kline[4])}\n"
        f"🌅 Open: ${format_price(kline[1])}\n"
        f"🔼 High: ${format_price(kline[2])}\n"
        f"🔽 Low: ${format_price(kline[3])}\n"
        f"⏭️ Vol: ${format_money(kline[7], 0)}"
    )


def main():
    parser = argparse.ArgumentParser(description="Fetch Binance historical daily prices for up to 5 USDT symbols.")
    parser.add_argument("query", nargs="*", help="Raw user text, e.g. show me the price of eth on march 13")
    args = parser.parse_args()

    text = normalize_text(args.query)
    if not text:
        print("Usage: /price-history eth 2026-03-13\nExample: show me the price of btc on march 13")
        return 0

    day = parse_date(text)
    if day is None:
        print("❌ Please provide a date like 2026-03-13, March 13, or yesterday.")
        return 0

    symbols, truncated = parse_symbols(text)
    if not symbols:
        print("❌ Please provide at least one coin symbol, like BTC or ETH.")
        return 0

    try:
        available = get_available_market_symbols()
    except Exception as exc:
        print(f"❌ {format_api_error(exc)}")
        return 0

    blocks = []
    for symbol in symbols:
        market = f"{symbol}USDT"
        if market not in available:
            blocks.append(f"❌ {symbol} not found")
            continue
        try:
            kline = fetch_daily_kline(symbol, day)
        except Exception as exc:
            print(f"❌ {format_api_error(exc)}")
            return 0
        if not kline:
            blocks.append(f"❌ No daily candle found for {symbol} on {day.isoformat()}")
            continue
        blocks.append(format_block(symbol, day, kline))

    if truncated:
        blocks.append("ℹ️ Showing the first 5 unique symbols only.")

    print("\n\n".join(blocks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
