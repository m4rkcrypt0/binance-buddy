#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

SPOT_TICKER_URL = "https://api.binance.com/api/v3/ticker/24hr"
SPOT_INFO_URL = "https://api.binance.com/api/v3/exchangeInfo"
FUTURES_TICKER_URL = "https://fapi.binance.com/fapi/v1/ticker/24hr"
FUTURES_INFO_URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"
CACHE_TTL_SECONDS = 6 * 60 * 60
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "binance-movers")
SPOT_CACHE_FILE = os.path.join(CACHE_DIR, "spot_exchange_info.json")
FUTURES_CACHE_FILE = os.path.join(CACHE_DIR, "futures_exchange_info.json")
LEVERAGED_SUFFIXES = ("UPUSDT", "DOWNUSDT", "BULLUSDT", "BEARUSDT")


def http_get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "binance-movers-skill/1.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def load_cache(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if time.time() - payload.get("createdAt", 0) > CACHE_TTL_SECONDS:
            return None
        return payload.get("data")
    except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError, ValueError):
        return None


def save_cache(path, data):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"createdAt": int(time.time()), "data": data}, handle)
    except OSError:
        pass


def get_exchange_info(url, cache_path):
    cached = load_cache(cache_path)
    if cached is not None:
        return cached
    data = http_get_json(url)
    save_cache(cache_path, data)
    return data


def get_allowed_spot_symbols():
    data = get_exchange_info(SPOT_INFO_URL, SPOT_CACHE_FILE)
    allowed = set()
    for item in data.get("symbols", []):
        symbol = item.get("symbol", "")
        if not symbol.endswith("USDT"):
            continue
        if symbol.endswith(LEVERAGED_SUFFIXES):
            continue
        if item.get("status") != "TRADING":
            continue
        allowed.add(symbol)
    return allowed


def get_allowed_futures_symbols():
    data = get_exchange_info(FUTURES_INFO_URL, FUTURES_CACHE_FILE)
    allowed = set()
    for item in data.get("symbols", []):
        symbol = item.get("symbol", "")
        if not symbol.endswith("USDT"):
            continue
        if item.get("status") != "TRADING":
            continue
        allowed.add(symbol)
    return allowed


def normalize_rows(rows, allowed_symbols):
    result = []
    for row in rows:
        symbol = row.get("symbol", "")
        if symbol not in allowed_symbols:
            continue
        try:
            change = float(row["priceChangePercent"])
        except (KeyError, TypeError, ValueError):
            continue
        result.append((symbol[:-4], change))
    return result


def parse_request(text):
    lowered = text.lower()
    if "gainer" in lowered:
        direction = "gainers"
    elif "loser" in lowered:
        direction = "losers"
    else:
        direction = None

    has_spot = bool(re.search(r"\bspot\b", lowered))
    has_futures = bool(re.search(r"\bfutures?\b", lowered))

    if has_spot and not has_futures:
        market = "spot"
    elif has_futures and not has_spot:
        market = "futures"
    else:
        market = "both"

    return direction, market


def format_ranked_lines(items):
    return [f"{index}. {symbol}: {change:+.2f}%" for index, (symbol, change) in enumerate(items, 1)]


def format_both(direction, spot_items, futures_items):
    if direction == "gainers":
        header_icon = "📈"
        section_icon = "🟢"
        title = "gainers"
        section_label = "Gainers"
    else:
        header_icon = "📉"
        section_icon = "🔴"
        title = "losers"
        section_label = "Losers"

    parts = [
        f"{header_icon} Here are the top {title} for both Spot and Futures right now:\n",
        f"{section_icon} Spot Market\n",
        f"Top 5 {section_label}:\n",
        *format_ranked_lines(spot_items),
        "",
        f"{section_icon} Futures Market\n",
        f"Top 5 {section_label}:\n",
        *format_ranked_lines(futures_items),
    ]
    return "\n".join(parts)


def format_single(direction, market_label, market_icon, items):
    if direction == "gainers":
        header_icon = "📈"
        title = "gainers"
        section_label = "Gainers"
    else:
        header_icon = "📉"
        title = "losers"
        section_label = "Losers"

    parts = [
        f"{header_icon} Here are the top {title} on {market_label} right now:\n",
        f"{market_icon} {market_label}\n",
        f"Top 10 {section_label}:\n",
        *format_ranked_lines(items),
    ]
    return "\n".join(parts)


def format_api_error(exc):
    if isinstance(exc, urllib.error.HTTPError):
        if exc.code == 429:
            return "Binance is rate-limiting right now. Try again in a moment."
        if 500 <= exc.code < 600:
            return "Binance is having server issues right now. Try again shortly."
        return f"Binance request failed with HTTP {exc.code}."
    if isinstance(exc, urllib.error.URLError):
        return "Could not reach Binance right now. Check the connection and try again."
    return "Binance movers data is temporarily unavailable. Try again shortly."


def main():
    parser = argparse.ArgumentParser(description="Fetch Binance top gainers and losers for Spot and Futures.")
    parser.add_argument("query", nargs="*", help="Raw user text, e.g. show me the top gainers on spot")
    args = parser.parse_args()

    text = " ".join(args.query).strip()
    if not text:
        print("Usage: show me the top gainers\nExample: show me the top losers on futures")
        return 0

    direction, market = parse_request(text)
    if direction is None:
        print("❌ Please specify whether you want top gainers or top losers.")
        return 0

    try:
        spot_allowed = get_allowed_spot_symbols()
        futures_allowed = get_allowed_futures_symbols()
        spot_rows = normalize_rows(http_get_json(SPOT_TICKER_URL), spot_allowed)
        futures_rows = normalize_rows(http_get_json(FUTURES_TICKER_URL), futures_allowed)
    except Exception as exc:
        print(f"❌ {format_api_error(exc)}")
        return 0

    reverse = direction == "gainers"
    if market == "both":
        spot_items = sorted(spot_rows, key=lambda item: item[1], reverse=reverse)[:5]
        futures_items = sorted(futures_rows, key=lambda item: item[1], reverse=reverse)[:5]
        print(format_both(direction, spot_items, futures_items))
        return 0

    if market == "spot":
        items = sorted(spot_rows, key=lambda item: item[1], reverse=reverse)[:10]
        icon = "🟢" if direction == "gainers" else "🔴"
        print(format_single(direction, "Spot Market", icon, items))
        return 0

    items = sorted(futures_rows, key=lambda item: item[1], reverse=reverse)[:10]
    icon = "🟢" if direction == "gainers" else "🔴"
    print(format_single(direction, "Futures Market", icon, items))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
