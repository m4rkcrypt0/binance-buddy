#!/usr/bin/env python3
import hashlib
import hmac
import json
import os
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
    req = urllib.request.Request(url, headers={"X-MBX-APIKEY": api_key, "User-Agent": "reward-history-skill/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def format_date(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def build_payload():
    now = datetime.now(timezone.utc)
    start = int((now - timedelta(days=DAYS_BACK)).timestamp() * 1000)
    end = int(now.timestamp() * 1000)

    data = signed_request("/sapi/v1/asset/assetDividend", {
        "startTime": start,
        "endTime": end,
        "limit": LIMIT,
    })

    rows = data.get("rows", []) if isinstance(data, dict) else []
    rewards = []
    for row in rows:
        note = str(row.get("enInfo") or "").strip()
        if note.isdigit():
            note = ""
        rewards.append({
            "date": format_date(int(row.get("divTime", 0) or 0)),
            "asset": row.get("asset"),
            "amount": str(row.get("amount")),
            "note": note,
            "sortTime": int(row.get("divTime", 0) or 0),
        })

    rewards.sort(key=lambda item: item["sortTime"], reverse=True)
    rewards = rewards[:LIMIT]

    return {
        "title": "🎁 Reward History",
        "days": DAYS_BACK,
        "rewards": rewards,
    }


if __name__ == "__main__":
    print(json.dumps(build_payload(), indent=2))
