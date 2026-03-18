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
from datetime import datetime, timedelta, timezone
from pathlib import Path

API_KEY_ENV = "BINANCE_API_KEY"
SECRET_ENV = "BINANCE_SECRET_KEY"
ENV_FILE = Path("/home/markvincentmalacad/.openclaw/workspace/.env")
BASE_URL = "https://api.binance.com"
DAYS_BACK = 90
LIMIT = 15


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


def signed_request(path, params=None):
    load_env_file(ENV_FILE)
    api_key = os.environ.get(API_KEY_ENV, "").strip()
    secret = os.environ.get(SECRET_ENV, "").strip()
    if not api_key or not secret:
        raise RuntimeError("Missing BINANCE_API_KEY or BINANCE_SECRET_KEY in workspace .env")

    params = dict(params or {})
    params["timestamp"] = int(time.time() * 1000)
    query = urllib.parse.urlencode(params)
    signature = hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()
    url = f"{BASE_URL}{path}?{query}&signature={signature}"
    req = urllib.request.Request(url, headers={"X-MBX-APIKEY": api_key, "User-Agent": "asset-history-skill/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def format_date(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def normalize_deposits(rows):
    result = []
    for row in rows:
        amount = float(row.get("amount", 0) or 0)
        if amount <= 0:
            continue
        insert_time = row.get("insertTime") or row.get("completeTime")
        if not insert_time:
            continue
        result.append({
            "recordType": "deposit",
            "date": format_date(int(insert_time)),
            "asset": row.get("coin"),
            "amount": str(row.get("amount")),
            "sortTime": int(insert_time),
        })
    result.sort(key=lambda item: item["sortTime"], reverse=True)
    return result[:LIMIT]


def normalize_withdrawals(rows):
    result = []
    for row in rows:
        amount = float(row.get("amount", 0) or 0)
        if amount <= 0:
            continue
        apply_time = row.get("applyTime")
        if not apply_time:
            continue
        dt = datetime.strptime(apply_time, "%Y-%m-%d %H:%M:%S")
        dt = dt.replace(tzinfo=timezone.utc)
        result.append({
            "recordType": "withdrawal",
            "date": dt.strftime("%Y-%m-%d"),
            "asset": row.get("coin"),
            "amount": str(row.get("amount")),
            "sortTime": int(dt.timestamp() * 1000),
        })
    result.sort(key=lambda item: item["sortTime"], reverse=True)
    return result[:LIMIT]


def build_payload():
    now = datetime.now(timezone.utc)
    start = int((now - timedelta(days=DAYS_BACK)).timestamp() * 1000)
    end = int(now.timestamp() * 1000)

    deposits = signed_request("/sapi/v1/capital/deposit/hisrec", {
        "startTime": start,
        "endTime": end,
        "limit": LIMIT,
    })
    withdrawals = signed_request("/sapi/v1/capital/withdraw/history", {
        "startTime": start,
        "endTime": end,
        "limit": LIMIT,
    })

    normalized_deposits = normalize_deposits(deposits)
    normalized_withdrawals = normalize_withdrawals(withdrawals)

    return {
        "generatedAt": int(time.time()),
        "title": "🧾 Asset History",
        "days": DAYS_BACK,
        "deposits": normalized_deposits,
        "withdrawals": normalized_withdrawals,
    }


def payload_to_csv_rows(payload: dict) -> list[dict]:
    rows = []
    generated_at = payload.get("generatedAt")
    days = payload.get("days")
    for item in payload.get("deposits", []):
        rows.append({
            "recordType": item.get("recordType"),
            "generatedAt": generated_at,
            "days": days,
            "date": item.get("date"),
            "asset": item.get("asset"),
            "amount": item.get("amount"),
        })
    for item in payload.get("withdrawals", []):
        rows.append({
            "recordType": item.get("recordType"),
            "generatedAt": generated_at,
            "days": days,
            "date": item.get("date"),
            "asset": item.get("asset"),
            "amount": item.get("amount"),
        })
    return rows


def write_csv(rows: list[dict], output_path: str | None = None) -> None:
    fieldnames = ["recordType", "generatedAt", "days", "date", "asset", "amount"]
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
    parser = argparse.ArgumentParser(description="Fetch Binance asset history as JSON or CSV")
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
