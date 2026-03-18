#!/usr/bin/env python3
import hashlib
import hmac
import json
import math
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

API_KEY_ENV = "BINANCE_API_KEY"
SECRET_ENV = "BINANCE_SECRET_KEY"
ENV_FILE = Path("/home/markvincentmalacad/.openclaw/workspace/.env")
BASE_URL = "https://api.binance.com"
FAPI_URL = "https://fapi.binance.com"
CACHE_DIR = Path.home() / ".cache" / "portfolio-opportunity-scanner"
PRICE_CACHE = CACHE_DIR / "prices.json"
TICKER_CACHE = CACHE_DIR / "ticker24h.json"
KLINES_DIR = CACHE_DIR / "klines"
CACHE_TTL_SECONDS = 30
MIN_VALUE_USDT = 0.5
OUTPUT_LIMIT = 10
STABLE_1_TO_1 = {"USDT", "USDC", "FDUSD", "BUSD", "USDS", "TUSD"}


def load_env_file(path: Path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def signed_request(base_url, path, params=None, method="GET"):
    load_env_file(ENV_FILE)
    api_key = os.environ.get(API_KEY_ENV, "").strip()
    secret = os.environ.get(SECRET_ENV, "").strip()
    if not api_key or not secret:
        raise RuntimeError("Missing BINANCE_API_KEY or BINANCE_SECRET_KEY in workspace .env")
    params = dict(params or {})
    params["timestamp"] = int(time.time() * 1000)
    query = urllib.parse.urlencode(params)
    signature = hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()
    url = f"{base_url}{path}?{query}&signature={signature}"
    req = urllib.request.Request(url, method=method, headers={"X-MBX-APIKEY": api_key, "User-Agent": "portfolio-opportunity-scanner-skill/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def public_request(base_url, path, params=None):
    query = urllib.parse.urlencode(params or {})
    url = f"{base_url}{path}"
    if query:
        url += f"?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": "portfolio-opportunity-scanner-skill/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def load_cache(path: Path, ttl: int):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if time.time() - payload.get("createdAt", 0) > ttl:
            return None
        return payload.get("data")
    except Exception:
        return None


def save_cache(path: Path, data):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"createdAt": int(time.time()), "data": data}), encoding="utf-8")
    except Exception:
        pass


def get_prices():
    cached = load_cache(PRICE_CACHE, CACHE_TTL_SECONDS)
    if cached is not None:
        return cached
    rows = public_request(BASE_URL, "/api/v3/ticker/price")
    data = {row["symbol"]: float(row["price"]) for row in rows}
    save_cache(PRICE_CACHE, data)
    return data


def get_ticker24h():
    cached = load_cache(TICKER_CACHE, CACHE_TTL_SECONDS)
    if cached is not None:
        return cached
    rows = public_request(BASE_URL, "/api/v3/ticker/24hr")
    data = {row["symbol"]: row for row in rows}
    save_cache(TICKER_CACHE, data)
    return data


def get_klines(symbol: str, interval="1d", limit=30):
    key = hashlib.sha256(f"{symbol}:{interval}:{limit}".encode()).hexdigest() + ".json"
    path = KLINES_DIR / key
    cached = load_cache(path, CACHE_TTL_SECONDS)
    if cached is not None:
        return cached
    rows = public_request(BASE_URL, "/api/v3/klines", {"symbol": symbol, "interval": interval, "limit": limit})
    save_cache(path, rows)
    return rows


def value_in_usdt(asset, amount, prices):
    if amount <= 0:
        return 0.0
    if asset in STABLE_1_TO_1:
        return amount
    symbol = f"{asset}USDT"
    if symbol in prices:
        return amount * prices[symbol]
    return 0.0


def fetch_spot():
    data = signed_request(BASE_URL, "/sapi/v3/asset/getUserAsset", method="POST")
    return [(r.get("asset"), float(r.get("free", 0) or 0) + float(r.get("locked", 0) or 0)) for r in data if (float(r.get("free", 0) or 0) + float(r.get("locked", 0) or 0)) > 0]


def fetch_funding():
    data = signed_request(BASE_URL, "/sapi/v1/asset/get-funding-asset", method="POST")
    return [(r.get("asset"), float(r.get("free", 0) or 0) + float(r.get("locked", 0) or 0)) for r in data if (float(r.get("free", 0) or 0) + float(r.get("locked", 0) or 0)) > 0]


def fetch_simple_earn():
    data = signed_request(BASE_URL, "/sapi/v1/simple-earn/flexible/position")
    rows = data.get("rows", []) if isinstance(data, dict) else []
    return [(r.get("asset"), float(r.get("totalAmount", 0) or 0)) for r in rows if float(r.get("totalAmount", 0) or 0) > 0]


def fetch_futures():
    data = signed_request(FAPI_URL, "/fapi/v2/balance")
    return [(r.get("asset"), float(r.get("balance", 0) or 0)) for r in data if float(r.get("balance", 0) or 0) > 0]


def aggregate_holdings(prices):
    wallet_map = {
        "Spot": fetch_spot(),
        "Funding": fetch_funding(),
        "Earn": fetch_simple_earn(),
        "Futures": fetch_futures(),
    }
    totals = {}
    for balances in wallet_map.values():
        for asset, amount in balances:
            value = value_in_usdt(asset, amount, prices)
            entry = totals.setdefault(asset, {"amount": 0.0, "value": 0.0})
            entry["amount"] += amount
            entry["value"] += value
    return totals


def pct_change(a, b):
    if b == 0:
        return 0.0
    return ((a - b) / b) * 100


def compute_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(1, period + 1):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    for i in range(period + 1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gain = max(diff, 0.0)
        loss = max(-diff, 0.0)
        avg_gain = ((avg_gain * (period - 1)) + gain) / period
        avg_loss = ((avg_loss * (period - 1)) + loss) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def classify_opportunity(asset, weight, change24h, change7d, rsi):
    if asset in STABLE_1_TO_1:
        return "reserve"
    if (change24h >= 3 or change7d >= 7) and weight >= 1:
        return "strength"
    if (change24h <= -3 or change7d <= -7 or (rsi is not None and rsi <= 35)) and weight >= 0.5:
        return "pullback"
    return "monitor"


def attention_score(asset, weight, change24h, change7d, rsi):
    if asset in STABLE_1_TO_1:
        return round(min(weight / 20.0, 1.0), 2)
    score = min(weight / 4.0, 5.0)
    score += min(abs(change24h) / 2.0, 2.0)
    score += min(abs(change7d) / 4.0, 2.0)
    if rsi is not None and (rsi <= 35 or rsi >= 65):
        score += 1.0
    return round(score, 2)


def note_for(asset, kind, weight, change24h, change7d):
    if kind == "reserve":
        return "Largest holding acts as reserve capital rather than directional opportunity." if weight >= 10 else "Stablecoin capital provides reserve value rather than directional opportunity."
    if kind == "strength":
        return "Strong relative momentum with meaningful portfolio weight."
    if kind == "pullback":
        if weight >= 5:
            return "Weakness is meaningful because this holding still matters at portfolio level."
        return "Weakness is visible, but portfolio impact is limited by smaller size."
    if weight >= 10:
        return "Large enough position that even a moderate move deserves monitoring."
    return "Movement is notable enough to watch, but portfolio impact is still limited."


def build_payload():
    prices = get_prices()
    ticker24h = get_ticker24h()
    holdings = aggregate_holdings(prices)
    total_value = sum(info["value"] for info in holdings.values())
    ranked = sorted(((asset, info) for asset, info in holdings.items() if info["value"] >= MIN_VALUE_USDT), key=lambda kv: kv[1]["value"], reverse=True)[:OUTPUT_LIMIT]

    rows = []
    for asset, info in ranked:
        symbol = f"{asset}USDT"
        price = 1.0 if asset in STABLE_1_TO_1 else prices.get(symbol)
        if price is None:
            continue
        weight = round((info["value"] / total_value) * 100, 1) if total_value > 0 else 0.0
        if asset in STABLE_1_TO_1:
            change24h = 0.0
            change7d = 0.0
            rsi = None
        else:
            t = ticker24h.get(symbol, {})
            change24h = round(float(t.get("priceChangePercent", 0.0) or 0.0), 1)
            klines = get_klines(symbol, "1d", 30)
            closes = [float(row[4]) for row in klines]
            change7d = round(pct_change(closes[-1], closes[-8]), 1) if len(closes) >= 8 else 0.0
            rsi_value = compute_rsi(closes, 14)
            rsi = round(rsi_value, 1) if rsi_value is not None else None
        kind = classify_opportunity(asset, weight, change24h, change7d, rsi)
        score = attention_score(asset, weight, change24h, change7d, rsi)
        label = "high" if score >= 6 else "moderate" if score >= 3 else "low"
        rows.append({
            "asset": asset,
            "portfolioPercent": weight,
            "price": round(price, 6) if price is not None else None,
            "change24h": change24h,
            "change7d": change7d,
            "rsi14": rsi,
            "attentionScore": score,
            "opportunityType": kind,
            "attentionLabel": label,
            "note": note_for(asset, kind, weight, change24h, change7d),
        })

    scored_rows = sorted(rows, key=lambda r: r["attentionScore"], reverse=True)
    best_strength = next((row["asset"] for row in scored_rows if row["opportunityType"] == "strength"), None)
    best_pullback = next((row["asset"] for row in scored_rows if row["opportunityType"] == "pullback"), None)
    top_attention = next((row["asset"] for row in scored_rows if row["opportunityType"] != "reserve"), scored_rows[0]["asset"] if scored_rows else None)
    opportunity_rows = [row for row in rows if row["opportunityType"] in {"strength", "pullback", "monitor"} and row["asset"] not in STABLE_1_TO_1 and row["attentionScore"] >= 3]
    breadth_count = len(opportunity_rows)
    breadth = "broad" if breadth_count >= 4 else "mixed" if breadth_count >= 2 else "narrow"
    stable_pct = round(sum(info["value"] for asset, info in holdings.items() if asset in STABLE_1_TO_1) / total_value * 100, 1) if total_value > 0 else 0.0

    rows = sorted(rows, key=lambda r: r["attentionScore"], reverse=True)
    return {
        "title": "🎯 Portfolio Opportunity Scanner",
        "total": round(total_value, 2),
        "window": "24H + 7D",
        "rows": rows,
        "signals": {
            "bestStrengthAsset": best_strength,
            "bestPullbackAsset": best_pullback,
            "topAttentionAsset": top_attention,
            "opportunityBreadth": breadth,
            "stablecoinDominance": "high" if stable_pct >= 50 else "moderate" if stable_pct >= 20 else "low",
        },
    }


if __name__ == "__main__":
    print(json.dumps(build_payload(), indent=2))
