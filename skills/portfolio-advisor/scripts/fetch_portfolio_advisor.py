#!/usr/bin/env python3
import hashlib
import hmac
import json
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
CACHE_DIR = Path.home() / ".cache" / "portfolio-advisor"
PRICE_CACHE = CACHE_DIR / "prices.json"
PRICE_TTL_SECONDS = 30
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
    req = urllib.request.Request(url, method=method, headers={"X-MBX-APIKEY": api_key, "User-Agent": "portfolio-advisor-skill/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def public_request(base_url, path, params=None):
    query = urllib.parse.urlencode(params or {})
    url = f"{base_url}{path}"
    if query:
        url += f"?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": "portfolio-advisor-skill/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def load_price_cache():
    try:
        payload = json.loads(PRICE_CACHE.read_text(encoding="utf-8"))
        if time.time() - payload.get("createdAt", 0) > PRICE_TTL_SECONDS:
            return None
        return payload.get("data")
    except Exception:
        return None


def save_price_cache(data):
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        PRICE_CACHE.write_text(json.dumps({"createdAt": int(time.time()), "data": data}), encoding="utf-8")
    except Exception:
        pass


def get_prices():
    cached = load_price_cache()
    if cached is not None:
        return cached
    rows = public_request(BASE_URL, "/api/v3/ticker/price")
    prices = {row["symbol"]: float(row["price"]) for row in rows}
    save_price_cache(prices)
    return prices


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


def aggregate(prices):
    wallet_map = {
        "Spot": fetch_spot(),
        "Funding": fetch_funding(),
        "Earn": fetch_simple_earn(),
        "Futures": fetch_futures(),
    }
    asset_totals = {}
    wallet_values = {}
    for wallet_name, balances in wallet_map.items():
        total = 0.0
        for asset, amount in balances:
            value = value_in_usdt(asset, amount, prices)
            total += value
            entry = asset_totals.setdefault(asset, {"amount": 0.0, "value": 0.0})
            entry["amount"] += amount
            entry["value"] += value
        wallet_values[wallet_name] = total
    return asset_totals, wallet_values


def build_payload():
    prices = get_prices()
    asset_totals, wallet_values = aggregate(prices)
    total_value = sum(wallet_values.values())
    ranked = sorted(asset_totals.items(), key=lambda kv: kv[1]["value"], reverse=True)

    top1_pct = round((ranked[0][1]["value"] / total_value * 100), 1) if ranked and total_value > 0 else 0.0
    top3_value = sum(info["value"] for _, info in ranked[:3])
    top3_pct = round((top3_value / total_value * 100), 1) if total_value > 0 else 0.0
    stable_value = sum(info["value"] for asset, info in asset_totals.items() if asset in STABLE_1_TO_1)
    stable_pct = round((stable_value / total_value * 100), 1) if total_value > 0 else 0.0
    futures_pct = round((wallet_values.get("Futures", 0.0) / total_value * 100), 1) if total_value > 0 else 0.0
    earn_pct = round((wallet_values.get("Earn", 0.0) / total_value * 100), 1) if total_value > 0 else 0.0
    dust_count = sum(1 for _, info in asset_totals.items() if 0 < info["value"] < 0.01)

    if top1_pct >= 50 or top3_pct >= 80:
        main_issue = "concentration"
    elif futures_pct > 25:
        main_issue = "futures"
    elif stable_pct > 40:
        main_issue = "stablecoins"
    else:
        main_issue = "balance"

    payload = {
        "title": "🧭 Portfolio Advisor",
        "total": round(total_value, 2),
        "metrics": {
            "topAsset": ranked[0][0] if ranked else None,
            "topAssetPercent": top1_pct,
            "top3Percent": top3_pct,
            "stablecoinPercent": stable_pct,
            "futuresPercent": futures_pct,
            "earnPercent": earn_pct,
            "dustCount": dust_count,
        },
        "signals": {
            "mainIssue": main_issue,
            "concentrationRisk": "high" if top1_pct >= 50 or top3_pct >= 80 else "moderate" if top1_pct >= 30 or top3_pct >= 60 else "low",
            "cashPosture": "high" if stable_pct > 25 else "healthy" if stable_pct >= 5 else "low",
            "riskPosture": "aggressive" if futures_pct > 25 else "moderate" if futures_pct > 10 else "low",
            "yieldUsage": "productive" if earn_pct >= 10 else "light" if earn_pct > 0 else "idle",
            "dustState": "clean" if dust_count == 0 else "moderate" if dust_count <= 3 else "messy",
        },
    }
    return payload


if __name__ == "__main__":
    print(json.dumps(build_payload(), indent=2))
