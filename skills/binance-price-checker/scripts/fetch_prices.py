#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API_URL = "https://api.binance.com/api/v3/ticker/24hr"
EXCHANGE_INFO_URL = "https://api.binance.com/api/v3/exchangeInfo"
MAX_SYMBOLS = 10
CACHE_TTL_SECONDS = 6 * 60 * 60
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "binance-price-checker")
CACHE_FILE = os.path.join(CACHE_DIR, "exchange_info_cache.json")
STOPWORDS = {
    "price", "prices", "please", "pls", "for", "of", "give", "me", "the",
    "check", "show", "quote", "quotes", "pair", "pairs", "usdt", "spot",
    "get", "tell", "current", "what", "whats", "is", "are", "now", "today"
}

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

PHRASE_ALIASES = {
    "shiba inu": "SHIB",
    "binance coin": "BNB",
}


def parse_user_symbols(values):
    tokens = []
    for value in values:
        cleaned = value.replace("/price", " ").replace("price/", " ")
        lowered = cleaned.lower()
        for phrase, replacement in PHRASE_ALIASES.items():
            lowered = lowered.replace(phrase, f" {replacement.lower()} ")
        parts = re.findall(r"[A-Za-z]+", lowered)
        for part in parts:
            raw_part = part.lower()
            if raw_part in STOPWORDS:
                continue
            token = part.upper()
            if token.endswith("USDT") and len(token) > 4:
                token = token[:-4]
            token = ALIASES.get(token, token)
            if token.lower() in STOPWORDS:
                continue
            if token:
                tokens.append(token)

    deduped = []
    seen = set()
    truncated = False
    for token in tokens:
        if token not in seen:
            seen.add(token)
            if len(deduped) >= MAX_SYMBOLS:
                truncated = True
                continue
            deduped.append(token)
    return deduped, truncated


def http_get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "binance-price-checker-skill/1.0"})
    with urllib.request.urlopen(req, timeout=15) as response:
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


def fetch_valid_market_symbols(symbols):
    available = get_available_market_symbols()
    return [f"{symbol}USDT" for symbol in symbols if f"{symbol}USDT" in available]


def fetch_24h_ticker(market_symbols):
    if not market_symbols:
        return {}
    query = urllib.parse.urlencode({"symbols": json.dumps(market_symbols, separators=(",", ":"))})
    url = f"{API_URL}?{query}"
    data = http_get_json(url)
    if isinstance(data, dict) and data.get("code"):
        raise RuntimeError(data.get("msg") or "Binance API error")
    return {item["symbol"]: item for item in data}


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


def format_money(value, decimals=2):
    return f"{float(value):,.{decimals}f}"


def format_percent(value):
    number = float(value)
    sign = "+" if number > 0 else ""
    return f"{sign}{number:.2f}%"


def sort_symbols_by_request_order(symbols, valid_market_symbols):
    valid_set = set(valid_market_symbols)
    ordered_valid = []
    ordered_invalid = []
    for symbol in symbols:
        market_symbol = f"{symbol}USDT"
        if market_symbol in valid_set:
            ordered_valid.append(symbol)
        else:
            ordered_invalid.append(symbol)
    return ordered_valid, ordered_invalid


def format_block(symbol, item):
    return (
        f"💰 {symbol}\n\n"
        f"💵 ${format_price(item['lastPrice'])}\n"
        f"📈 {format_percent(item['priceChangePercent'])} (24h)\n"
        f"🔼 High: ${format_price(item['highPrice'])}\n"
        f"🔽 Low: ${format_price(item['lowPrice'])}\n"
        f"⏭️ Vol: ${format_money(item['quoteVolume'], 0)}"
    )


def format_api_error(exc):
    if isinstance(exc, urllib.error.HTTPError):
        if exc.code == 429:
            return "Binance is rate-limiting right now. Try again in a moment."
        if 500 <= exc.code < 600:
            return "Binance is having server issues right now. Try again shortly."
        return f"Binance request failed with HTTP {exc.code}."
    if isinstance(exc, urllib.error.URLError):
        return "Could not reach Binance right now. Check the connection and try again."
    return "Binance data is temporarily unavailable. Try again shortly."


def main():
    parser = argparse.ArgumentParser(description="Fetch Binance spot USDT prices for up to 10 symbols.")
    parser.add_argument("symbols", nargs="*", help="Coin symbols or raw user text, e.g. btc eth /price sol")
    args = parser.parse_args()

    symbols, truncated = parse_user_symbols(args.symbols)
    if not symbols:
        print("Usage: /price btc eth sol\nExample: bitcoin xrp btcusdt", file=sys.stdout)
        return 0

    try:
        valid_market_symbols = fetch_valid_market_symbols(symbols)
        ticker_map = fetch_24h_ticker(valid_market_symbols)
    except Exception as exc:
        print(f"❌ {format_api_error(exc)}", file=sys.stdout)
        return 0

    ordered_valid, ordered_invalid = sort_symbols_by_request_order(symbols, valid_market_symbols)

    blocks = []
    for symbol in ordered_valid:
        market_symbol = f"{symbol}USDT"
        item = ticker_map.get(market_symbol)
        if not item:
            blocks.append(f"❌ {symbol} not found")
            continue
        blocks.append(format_block(symbol, item))

    for symbol in ordered_invalid:
        blocks.append(f"❌ {symbol} not found")

    if truncated:
        blocks.append("ℹ️ Showing the first 10 unique symbols only.")

    print("\n\n".join(blocks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
