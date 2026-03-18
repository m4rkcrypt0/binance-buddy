#!/usr/bin/env python3
import json
import os
import time
import urllib.request

COINGECKO_GLOBAL_URL = "https://api.coingecko.com/api/v3/global"
FEAR_GREED_URL = "https://api.alternative.me/fng/"
BTC_LONG_SHORT_URL = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=5m&limit=1"
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "binance-market-overview")
CACHE_FILE = os.path.join(CACHE_DIR, "overview_cache.json")
CACHE_TTL_SECONDS = 60

STABLECOINS = {"usdt", "usdc", "dai", "fdusd", "usde", "usds", "tusd", "pyusd", "usdd", "susde"}


def http_get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "binance-market-overview-skill/1.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def load_cache():
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if time.time() - payload.get("createdAt", 0) > CACHE_TTL_SECONDS:
            return None
        return payload.get("data")
    except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError, ValueError):
        return None


def save_cache(data):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as handle:
            json.dump({"createdAt": int(time.time()), "data": data}, handle)
    except OSError:
        pass


def format_large_money(number):
    if number >= 1_000_000_000_000:
        return f"${number / 1_000_000_000_000:.2f}T"
    if number >= 1_000_000_000:
        return f"${number / 1_000_000_000:.1f}B"
    if number >= 1_000_000:
        return f"${number / 1_000_000:.1f}M"
    return f"${number:,.0f}"


def derive_stablecoin_dominance(market_cap_percentage):
    total = 0.0
    for symbol, pct in market_cap_percentage.items():
        if symbol.lower() in STABLECOINS:
            total += float(pct)
    return total


def derive_signals(fear_greed_value, btc_dom, stablecoin_dom, long_ratio, short_ratio):
    if fear_greed_value < 25:
        risk_sentiment = "extreme_fear"
    elif fear_greed_value < 45:
        risk_sentiment = "fear"
    elif fear_greed_value < 56:
        risk_sentiment = "neutral"
    elif fear_greed_value < 75:
        risk_sentiment = "greed"
    else:
        risk_sentiment = "extreme_greed"

    if btc_dom >= 55:
        btc_regime = "strong"
    elif btc_dom >= 50:
        btc_regime = "firm"
    else:
        btc_regime = "soft"

    if stablecoin_dom >= 10:
        liquidity_posture = "defensive"
    elif stablecoin_dom >= 7:
        liquidity_posture = "cautious"
    else:
        liquidity_posture = "risk_on"

    spread = long_ratio - short_ratio
    if spread > 0.03:
        positioning_bias = "long_bias"
    elif spread < -0.03:
        positioning_bias = "short_bias"
    else:
        positioning_bias = "balanced"

    return {
        "riskSentiment": risk_sentiment,
        "btcRegime": btc_regime,
        "liquidityPosture": liquidity_posture,
        "positioningBias": positioning_bias,
    }


def fetch_overview():
    cached = load_cache()
    if cached is not None:
        return cached

    global_data = http_get_json(COINGECKO_GLOBAL_URL)["data"]
    fear_data = http_get_json(FEAR_GREED_URL)["data"][0]
    long_short_data = http_get_json(BTC_LONG_SHORT_URL)[0]

    market_cap = float(global_data["total_market_cap"]["usd"])
    volume_24h = float(global_data["total_volume"]["usd"])
    btc_dom = float(global_data["market_cap_percentage"]["btc"])
    stablecoin_dom = derive_stablecoin_dominance(global_data["market_cap_percentage"])
    fear_greed_value = int(fear_data["value"])
    fear_greed_label = fear_data["value_classification"]
    long_ratio = float(long_short_data["longAccount"])
    short_ratio = float(long_short_data["shortAccount"])

    data = {
        "marketCap": market_cap,
        "marketCapFormatted": format_large_money(market_cap),
        "volume24h": volume_24h,
        "volume24hFormatted": format_large_money(volume_24h),
        "btcDominance": round(btc_dom, 1),
        "stablecoinDominance": round(stablecoin_dom, 1),
        "fearGreedValue": fear_greed_value,
        "fearGreedLabel": fear_greed_label,
        "btcLongRatio": round(long_ratio, 2),
        "btcShortRatio": round(short_ratio, 2),
    }
    data["signals"] = derive_signals(
        data["fearGreedValue"],
        data["btcDominance"],
        data["stablecoinDominance"],
        data["btcLongRatio"],
        data["btcShortRatio"],
    )
    save_cache(data)
    return data


if __name__ == "__main__":
    print(json.dumps(fetch_overview(), indent=2))
