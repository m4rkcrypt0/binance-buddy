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
CACHE_DIR = Path.home() / ".cache" / "correlation-alpha-matrix"
PRICE_CACHE = CACHE_DIR / "prices.json"
KLINE_CACHE = CACHE_DIR / "klines.json"
PRICE_TTL_SECONDS = 30
KLINE_TTL_SECONDS = 15 * 60
TOP_LIMIT = 15
WINDOW_DAYS = 30
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
    req = urllib.request.Request(url, method=method, headers={"X-MBX-APIKEY": api_key, "User-Agent": "correlation-alpha-matrix-skill/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def public_request(base_url, path, params=None):
    query = urllib.parse.urlencode(params or {})
    url = f"{base_url}{path}"
    if query:
        url += f"?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": "correlation-alpha-matrix-skill/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def load_cache(path, ttl):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if time.time() - payload.get("createdAt", 0) > ttl:
            return None
        return payload.get("data")
    except Exception:
        return None


def save_cache(path, data):
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"createdAt": int(time.time()), "data": data}), encoding="utf-8")
    except Exception:
        pass


def get_prices():
    cached = load_cache(PRICE_CACHE, PRICE_TTL_SECONDS)
    if cached is not None:
        return cached
    rows = public_request(BASE_URL, "/api/v3/ticker/price")
    prices = {row["symbol"]: float(row["price"]) for row in rows}
    save_cache(PRICE_CACHE, prices)
    return prices


def get_klines(symbol):
    cache = load_cache(KLINE_CACHE, KLINE_TTL_SECONDS) or {}
    if symbol in cache:
        return cache[symbol]
    rows = public_request(BASE_URL, "/api/v3/klines", {"symbol": symbol, "interval": "1d", "limit": WINDOW_DAYS + 1})
    closes = [float(r[4]) for r in rows]
    cache[symbol] = closes
    save_cache(KLINE_CACHE, cache)
    return closes


def value_in_usdt(asset, amount, prices):
    if amount <= 0:
        return 0.0
    if asset in STABLE_1_TO_1:
        return amount
    direct = f"{asset}USDT"
    if direct in prices:
        return amount * prices[direct]
    return 0.0


def fetch_spot():
    data = signed_request(BASE_URL, "/sapi/v3/asset/getUserAsset", method="POST")
    balances = []
    for row in data:
        asset = row.get("asset")
        amount = float(row.get("free", 0) or 0) + float(row.get("locked", 0) or 0)
        if amount > 0:
            balances.append((asset, amount))
    return balances


def fetch_funding():
    data = signed_request(BASE_URL, "/sapi/v1/asset/get-funding-asset", method="POST")
    balances = []
    for row in data:
        asset = row.get("asset")
        amount = float(row.get("free", 0) or 0) + float(row.get("locked", 0) or 0)
        if amount > 0:
            balances.append((asset, amount))
    return balances


def fetch_simple_earn():
    data = signed_request(BASE_URL, "/sapi/v1/simple-earn/flexible/position")
    rows = data.get("rows", []) if isinstance(data, dict) else []
    balances = []
    for row in rows:
        asset = row.get("asset")
        total = float(row.get("totalAmount", 0) or 0)
        if total > 0:
            balances.append((asset, total))
    return balances


def fetch_futures():
    data = signed_request(FAPI_URL, "/fapi/v2/balance")
    balances = []
    for row in data:
        asset = row.get("asset")
        amount = float(row.get("balance", 0) or 0)
        if amount > 0:
            balances.append((asset, amount))
    return balances


def aggregate_assets(prices):
    wallet_map = {
        "Spot": fetch_spot(),
        "Funding": fetch_funding(),
        "Earn": fetch_simple_earn(),
        "Futures": fetch_futures(),
    }
    asset_totals = {}
    for balances in wallet_map.values():
        for asset, amount in balances:
            value = value_in_usdt(asset, amount, prices)
            entry = asset_totals.setdefault(asset, {"amount": 0.0, "value": 0.0})
            entry["amount"] += amount
            entry["value"] += value
    return asset_totals


def returns(series):
    out = []
    for i in range(1, len(series)):
        prev = series[i - 1]
        cur = series[i]
        if prev > 0:
            out.append((cur - prev) / prev)
    return out


def correlation(a, b):
    n = min(len(a), len(b))
    if n < 2:
        return None
    a = a[-n:]
    b = b[-n:]
    mean_a = sum(a) / n
    mean_b = sum(b) / n
    cov = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b))
    var_a = sum((x - mean_a) ** 2 for x in a)
    var_b = sum((y - mean_b) ** 2 for y in b)
    if var_a == 0 or var_b == 0:
        return 0.0
    return cov / math.sqrt(var_a * var_b)


def classify_corr(value):
    if value is None:
        return "n/a"
    if value >= 0.8:
        return "very high"
    if value >= 0.6:
        return "high"
    if value >= 0.3:
        return "moderate"
    return "low"


def build_payload():
    prices = get_prices()
    asset_totals = aggregate_assets(prices)
    total_value = sum(info["value"] for info in asset_totals.values())
    ranked = sorted(asset_totals.items(), key=lambda kv: kv[1]["value"], reverse=True)
    top_assets = [(asset, info) for asset, info in ranked if info["value"] >= 0.01][:TOP_LIMIT]

    btc_returns = returns(get_klines("BTCUSDT"))
    rows = []
    high_corr_count = 0
    stable_reserve = 0.0
    for asset, info in top_assets:
        if asset in STABLE_1_TO_1:
            corr = 0.0
            stable_reserve += info["value"]
        else:
            symbol = f"{asset}USDT"
            if symbol == "BTCUSDT":
                corr = 1.0
            else:
                try:
                    corr = correlation(returns(get_klines(symbol)), btc_returns)
                except Exception:
                    corr = None
        if corr is not None and corr >= 0.75:
            high_corr_count += 1
        pct = (info["value"] / total_value * 100) if total_value > 0 else 0.0
        rows.append({
            "asset": asset,
            "corr": round(corr, 2) if corr is not None else None,
            "corrLabel": classify_corr(corr),
            "portfolioPercent": round(pct, 1),
        })

    stable_pct = (stable_reserve / total_value * 100) if total_value > 0 else 0.0
    if high_corr_count >= max(2, len(rows) // 2):
        diversification = "low"
    elif high_corr_count >= 1:
        diversification = "moderate"
    else:
        diversification = "strong"

    if high_corr_count >= max(2, len(rows) // 2):
        btc_linkage = "high"
    elif high_corr_count >= 1:
        btc_linkage = "moderate"
    else:
        btc_linkage = "low"

    stable_reserve_label = "strong" if stable_pct > 25 else "healthy" if stable_pct >= 5 else "weak"

    return {
        "title": "🧠 Correlation Alpha Matrix",
        "reference": "BTC",
        "window": "30D",
        "rows": rows,
        "signals": {
            "btcLinkage": btc_linkage,
            "diversificationQuality": diversification,
            "stableReserve": stable_reserve_label,
        },
    }


if __name__ == "__main__":
    print(json.dumps(build_payload(), indent=2))
