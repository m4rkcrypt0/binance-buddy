#!/usr/bin/env python3
import json
import math
import re
import sys
import urllib.parse
import urllib.request

BASE_URL = "https://api.binance.com"
DEFAULT_INTERVAL = "4h"
ALLOWED_INTERVALS = {"15m", "1h", "4h", "1d"}
MAX_KLINES = 260


def public_request(path, params=None):
    query = urllib.parse.urlencode(params or {})
    url = f"{BASE_URL}{path}"
    if query:
        url += f"?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": "market-analyzer-skill/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_symbol(text):
    cleaned = re.sub(r"[^A-Za-z]", "", (text or "").upper())
    if not cleaned:
        return "BTCUSDT"
    if cleaned.endswith("USDT"):
        return cleaned
    return f"{cleaned}USDT"


def detect_interval(text):
    lowered = (text or "").lower()
    mapping = {
        "15m": ["15m", "15 m", "15min", "15 min"],
        "1h": ["1h", "1 h", "1hr", "1 hr", "1hour", "1 hour"],
        "4h": ["4h", "4 h", "4hr", "4 hr", "4hour", "4 hour"],
        "1d": ["1d", "1 d", "1day", "1 day", "daily"],
    }
    for interval, needles in mapping.items():
        if any(needle in lowered for needle in needles):
            return interval
    return DEFAULT_INTERVAL


def detect_mode(text):
    lowered = (text or "").lower()
    if any(token in lowered for token in ["why ", " dump", " pump", " dropped", " falling", " crashed", " surged"]):
        return "move-explainer"
    if any(token in lowered for token in ["entry", "buy", "watch", "where should i", "good entry"]):
        return "entry"
    return "analysis"


def extract_symbol(text):
    text = text or ""
    candidates = re.findall(r"\b[A-Za-z]{2,10}(?:USDT)?\b", text)
    stopwords = {
        "GIVE", "ME", "TA", "FOR", "ANALYZE", "ANALYSIS", "INSIGHTS", "ABOUT", "WHY", "RIGHT",
        "ENTRY", "DUMP", "PUMP", "ON", "THE", "THIS", "IS", "A", "GOOD", "WHAT", "WHERE", "SHOULD", "I"
    }
    for token in candidates:
        upper = token.upper()
        if upper in stopwords:
            continue
        if upper in ALLOWED_INTERVALS:
            continue
        return normalize_symbol(upper)
    return "BTCUSDT"


def sma(values, period):
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def ema(values, period):
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    value = sum(values[:period]) / period
    for price in values[period:]:
        value = (price * k) + (value * (1 - k))
    return value


def rsi(values, period=14):
    if len(values) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(1, period + 1):
        diff = values[i] - values[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    for i in range(period + 1, len(values)):
        diff = values[i] - values[i - 1]
        gain = max(diff, 0.0)
        loss = max(-diff, 0.0)
        avg_gain = ((avg_gain * (period - 1)) + gain) / period
        avg_loss = ((avg_loss * (period - 1)) + loss) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def pct_change(current, prior):
    if prior == 0:
        return 0.0
    return ((current - prior) / prior) * 100


def classify_trend(price, ema20, ema50, sma200):
    above20 = ema20 is not None and price > ema20
    above50 = ema50 is not None and price > ema50
    above200 = sma200 is not None and price > sma200
    if above20 and above50 and above200:
        return "bullish"
    if (not above20) and (not above50) and (not above200):
        return "bearish"
    return "mixed"


def classify_momentum(rsi14, change24h, change7d):
    if rsi14 is None:
        return "neutral"
    if rsi14 >= 65 or change24h >= 4 or change7d >= 10:
        return "strong"
    if rsi14 <= 35 or change24h <= -4 or change7d <= -10:
        return "weak"
    return "neutral"


def classify_extension(price, ema20, rsi14):
    if ema20 is None or rsi14 is None or ema20 == 0:
        return "normal"
    distance = abs((price - ema20) / ema20) * 100
    if distance >= 6 or rsi14 >= 70 or rsi14 <= 30:
        return "extended"
    return "normal"


def recent_levels(highs, lows, closes):
    resistance = sorted({round(max(highs[-12:]), 4), round(max(highs[-24:]), 4)})
    support = sorted({round(min(lows[-12:]), 4), round(min(lows[-24:]), 4)}, reverse=True)
    current = closes[-1]
    support = [level for level in support if level <= current][:2] or support[:2]
    resistance = [level for level in resistance if level >= current][:2] or resistance[-2:]
    return support, resistance


def build_payload(prompt):
    symbol = extract_symbol(prompt)
    interval = detect_interval(prompt)
    mode = detect_mode(prompt)

    ticker = public_request("/api/v3/ticker/24hr", {"symbol": symbol})
    klines = public_request("/api/v3/klines", {"symbol": symbol, "interval": interval, "limit": MAX_KLINES})
    closes = [float(row[4]) for row in klines]
    highs = [float(row[2]) for row in klines]
    lows = [float(row[3]) for row in klines]

    price = closes[-1]
    change24h = round(float(ticker.get("priceChangePercent", 0.0) or 0.0), 2)
    change7d = round(pct_change(closes[-1], closes[-1 - min(42, len(closes)-1)]) if interval == "4h" and len(closes) > 42 else pct_change(closes[-1], closes[-8]) if len(closes) > 8 else 0.0, 2)
    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    sma200 = sma(closes, 200)
    rsi14 = rsi(closes, 14)
    support, resistance = recent_levels(highs, lows, closes)

    trend = classify_trend(price, ema20, ema50, sma200)
    momentum = classify_momentum(rsi14, change24h, change7d)
    extension = classify_extension(price, ema20, rsi14)

    price_vs = {
        "ema20": "above" if ema20 is not None and price > ema20 else "below",
        "ema50": "above" if ema50 is not None and price > ema50 else "below",
        "sma200": "above" if sma200 is not None and price > sma200 else "below",
    }

    if mode == "entry":
        entry_view = "watch-pullback" if trend == "bullish" and extension == "extended" else "support-bounce" if trend == "bullish" else "wait-confirmation"
    elif mode == "move-explainer":
        entry_view = "breakdown-risk" if momentum == "weak" else "momentum-driven" if momentum == "strong" else "mixed-move"
    else:
        entry_view = "trend-following" if trend == "bullish" else "defensive" if trend == "bearish" else "range-watch"

    return {
        "title": "📊 Market Analyzer",
        "symbol": symbol,
        "baseAsset": symbol.replace("USDT", ""),
        "timeframe": interval,
        "mode": mode,
        "price": round(price, 6),
        "change24h": change24h,
        "change7d": change7d,
        "indicators": {
            "rsi14": round(rsi14, 2) if rsi14 is not None else None,
            "ema20": round(ema20, 6) if ema20 is not None else None,
            "ema50": round(ema50, 6) if ema50 is not None else None,
            "sma200": round(sma200, 6) if sma200 is not None else None,
        },
        "structure": {
            "trend": trend,
            "momentum": momentum,
            "extension": extension,
            "priceVs": price_vs,
        },
        "levels": {
            "support": support,
            "resistance": resistance,
        },
        "signals": {
            "entryView": entry_view,
            "marketState": f"{trend}-{momentum}",
        },
    }


if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "analyze BTC"
    print(json.dumps(build_payload(prompt), indent=2))
