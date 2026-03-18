#!/usr/bin/env python3
import argparse
import csv
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

API_KEY_ENV = "BINANCE_API_KEY"
SECRET_ENV = "BINANCE_SECRET_KEY"
ENV_FILE = Path("/home/markvincentmalacad/.openclaw/workspace/.env")
BASE_URL = "https://api.binance.com"
FAPI_URL = "https://fapi.binance.com"
CACHE_DIR = Path.home() / ".cache" / "binance-portfolio"
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
    req = urllib.request.Request(url, method=method, headers={"X-MBX-APIKEY": api_key, "User-Agent": "binance-portfolio-skill/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def public_request(base_url, path, params=None):
    query = urllib.parse.urlencode(params or {})
    url = f"{base_url}{path}"
    if query:
        url += f"?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": "binance-portfolio-skill/1.0"})
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
    balances = []
    for row in data:
        asset = row.get("asset")
        free = float(row.get("free", 0) or 0)
        locked = float(row.get("locked", 0) or 0)
        amount = free + locked
        if amount > 0:
            balances.append((asset, amount))
    return balances


def fetch_funding():
    data = signed_request(BASE_URL, "/sapi/v1/asset/get-funding-asset", method="POST")
    balances = []
    for row in data:
        asset = row.get("asset")
        free = float(row.get("free", 0) or 0)
        locked = float(row.get("locked", 0) or 0)
        amount = free + locked
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


def aggregate_assets(wallet_map, prices):
    asset_totals = {}
    wallet_values = {}
    for wallet_name, balances in wallet_map.items():
        wallet_total = 0.0
        for asset, amount in balances:
            usdt_value = value_in_usdt(asset, amount, prices)
            wallet_total += usdt_value
            entry = asset_totals.setdefault(asset, {"amount": 0.0, "value": 0.0})
            entry["amount"] += amount
            entry["value"] += usdt_value
        wallet_values[wallet_name] = wallet_total
    return asset_totals, wallet_values


def format_amount(amount):
    if amount >= 1:
        return f"{amount:.2f}".rstrip('0').rstrip('.')
    if amount >= 0.01:
        return f"{amount:.4f}".rstrip('0').rstrip('.')
    return f"{amount:.8f}".rstrip('0').rstrip('.')


def build_payload():
    prices = get_prices()
    wallet_map = {
        "Spot": fetch_spot(),
        "Funding": fetch_funding(),
        "Earn": fetch_simple_earn(),
        "Futures": fetch_futures(),
    }
    asset_totals, wallet_values = aggregate_assets(wallet_map, prices)
    total_value = sum(wallet_values.values())

    visible_assets = []
    for asset, info in asset_totals.items():
        if info["value"] < 0.01:
            continue
        pct = (info["value"] / total_value * 100) if total_value > 0 else 0.0
        visible_assets.append({
            "asset": asset,
            "amount": format_amount(info["amount"]),
            "value": round(info["value"], 2),
            "percent": round(pct, 1),
        })
    visible_assets.sort(key=lambda item: item["value"], reverse=True)
    visible_assets = visible_assets[:20]

    wallets = []
    for wallet_name in ["Spot", "Funding", "Earn", "Futures"]:
        value = wallet_values.get(wallet_name, 0.0)
        pct = (value / total_value * 100) if total_value > 0 else 0.0
        wallets.append({"wallet": wallet_name, "value": round(value, 2), "percent": round(pct, 1)})

    return {
        "generatedAt": int(time.time()),
        "total": round(total_value, 2),
        "assetCount": len(visible_assets),
        "wallets": wallets,
        "assets": visible_assets,
    }


def payload_to_csv_rows(payload: dict) -> list[dict]:
    rows = []
    generated_at = payload.get("generatedAt")
    total = payload.get("total")
    for wallet in payload.get("wallets", []):
        rows.append({
            "recordType": "wallet",
            "generatedAt": generated_at,
            "portfolioTotalUsdt": total,
            "name": wallet.get("wallet"),
            "asset": "",
            "amount": "",
            "valueUsdt": wallet.get("value"),
            "percent": wallet.get("percent"),
        })
    for asset in payload.get("assets", []):
        rows.append({
            "recordType": "asset",
            "generatedAt": generated_at,
            "portfolioTotalUsdt": total,
            "name": "",
            "asset": asset.get("asset"),
            "amount": asset.get("amount"),
            "valueUsdt": asset.get("value"),
            "percent": asset.get("percent"),
        })
    return rows


def write_csv(rows: list[dict], output_path: str | None = None) -> None:
    fieldnames = ["recordType", "generatedAt", "portfolioTotalUsdt", "name", "asset", "amount", "valueUsdt", "percent"]
    handle = open(output_path, "w", newline="", encoding="utf-8") if output_path else sys.stdout
    close_handle = output_path is not None
    try:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    finally:
        if close_handle:
            handle.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Binance portfolio as JSON or CSV")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", help="Write CSV output to a file path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload()
    if args.format == "json":
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    rows = payload_to_csv_rows(payload)
    write_csv(rows, args.output)
    if args.output:
        print(f"Wrote CSV to {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
