#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API_URL = "https://www.binance.com/bapi/composite/v1/public/pgc/openApi/content/add"
ENV_NAME = "BINANCE_SQUARE_OPENAPI_KEY"
WORKSPACE_ENV = Path("/home/markvincentmalacad/.openclaw/workspace/.env")


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


def mask_key(value: str) -> str:
    if len(value) <= 9:
        return "***"
    return f"{value[:5]}...{value[-4:]}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish a Binance Square post from stdin")
    parser.add_argument("--dry-run", action="store_true", help="Validate and simulate publishing without calling the live API")
    return parser.parse_args()


def main():
    args = parse_args()
    load_env_file(WORKSPACE_ENV)
    api_key = os.environ.get(ENV_NAME, "").strip()
    if not api_key:
        print(json.dumps({
            "ok": False,
            "error": f"Missing {ENV_NAME} in workspace .env",
        }))
        return 1

    body = sys.stdin.read().strip()
    if not body:
        print(json.dumps({"ok": False, "error": "Empty post body"}))
        return 1

    if args.dry_run:
        print(json.dumps({
            "ok": True,
            "dryRun": True,
            "postId": None,
            "postUrl": None,
            "maskedKey": mask_key(api_key),
            "length": len(body),
            "preview": body,
            "message": "Dry run only; live Square API was not called",
        }, ensure_ascii=False))
        return 0

    payload = json.dumps({"bodyTextOnly": body}).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=payload,
        method="POST",
        headers={
            "X-Square-OpenAPI-Key": api_key,
            "Content-Type": "application/json",
            "clienttype": "binanceSkill",
            "User-Agent": "openclaw-square-post/1.0",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw)
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read().decode("utf-8")
            detail = json.loads(raw)
        except Exception:
            detail = {"message": str(exc)}
        print(json.dumps({"ok": False, "error": "HTTP error", "detail": detail}))
        return 1
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1

    if data.get("code") == "000000":
        post_id = ((data.get("data") or {}).get("id"))
        result = {
            "ok": True,
            "dryRun": False,
            "postId": post_id,
            "postUrl": f"https://www.binance.com/square/post/{post_id}" if post_id else None,
            "maskedKey": mask_key(api_key),
            "raw": data,
        }
        print(json.dumps(result))
        return 0

    print(json.dumps({
        "ok": False,
        "error": data.get("message") or "Square API error",
        "raw": data,
        "maskedKey": mask_key(api_key),
    }))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
