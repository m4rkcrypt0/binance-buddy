#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
STATE_SCRIPT = SCRIPT_DIR / "square_state.py"
PUBLISH_SCRIPT = SCRIPT_DIR / "publish_square_post.py"


def run_json(args: list[str], input_text: str | None = None) -> tuple[int, dict]:
    result = subprocess.run(
        args,
        input=input_text,
        text=True,
        capture_output=True,
        cwd=str(SCRIPT_DIR.parent),
    )
    output = (result.stdout or result.stderr or "").strip()
    try:
        data = json.loads(output) if output else {}
    except Exception:
        data = {"ok": False, "error": "Non-JSON output", "rawOutput": output}
    return result.returncode, data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish the currently saved Binance Square draft")
    parser.add_argument("--dry-run", action="store_true", help="Run the full local flow without calling the live API or mutating publish history")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    rc, draft_data = run_json([str(STATE_SCRIPT), "get-draft"])
    if rc != 0 or not draft_data.get("ok"):
        print(json.dumps({"ok": False, "error": "Failed to load current draft", "detail": draft_data}))
        return 1

    draft = draft_data.get("currentDraft") or {}
    text = (draft.get("text") or "").strip()
    topic = draft.get("topic")
    if not text:
        print(json.dumps({"ok": False, "error": "No saved draft to publish"}))
        return 1

    rc, status_data = run_json([str(STATE_SCRIPT), "can-publish"])
    if rc != 0 or not status_data.get("ok"):
        print(json.dumps({"ok": False, "error": "Failed to check publish status", "detail": status_data}))
        return 1
    if not status_data.get("canPublish"):
        print(json.dumps({
            "ok": False,
            "error": "Publish blocked",
            "reason": status_data.get("reason"),
            "cooldownRemainingSeconds": status_data.get("cooldownRemainingSeconds"),
            "postsLast24h": status_data.get("postsLast24h"),
            "dailyLimit": status_data.get("dailyLimit"),
            "dailyRemaining": status_data.get("dailyRemaining"),
        }))
        return 1

    publish_cmd = [str(PUBLISH_SCRIPT)]
    if args.dry_run:
        publish_cmd.append("--dry-run")

    rc, publish_data = run_json(publish_cmd, input_text=text)
    if rc != 0 or not publish_data.get("ok"):
        print(json.dumps({"ok": False, "error": "Publish failed", "detail": publish_data}))
        return 1

    if args.dry_run:
        print(json.dumps({
            "ok": True,
            "dryRun": True,
            "topic": topic,
            "length": len(text),
            "preview": text,
            "status": {
                "canPublish": status_data.get("canPublish"),
                "cooldownRemainingSeconds": status_data.get("cooldownRemainingSeconds"),
                "postsLast24h": status_data.get("postsLast24h"),
                "dailyRemaining": status_data.get("dailyRemaining"),
            },
            "message": "Dry run only; draft was not actually published and local publish history was not changed",
        }, ensure_ascii=False))
        return 0

    post_id = publish_data.get("postId")
    post_url = publish_data.get("postUrl")
    log_cmd = [
        str(STATE_SCRIPT),
        "log-publish",
        "--text", text,
    ]
    if topic:
        log_cmd.extend(["--topic", topic])
    if post_id:
        log_cmd.extend(["--post-id", str(post_id)])
    if post_url:
        log_cmd.extend(["--post-url", post_url])

    rc, log_data = run_json(log_cmd)
    if rc != 0 or not log_data.get("ok"):
        print(json.dumps({
            "ok": False,
            "error": "Published but failed to update local state",
            "publish": publish_data,
            "state": log_data,
        }))
        return 1

    print(json.dumps({
        "ok": True,
        "dryRun": False,
        "postId": post_id,
        "postUrl": post_url,
        "topic": topic,
        "length": len(text),
        "status": {
            "lastPublishAt": log_data.get("lastPublishAt"),
            "cooldownRemainingSeconds": log_data.get("cooldownRemainingSeconds"),
            "postsLast24h": log_data.get("postsLast24h"),
            "dailyRemaining": log_data.get("dailyRemaining"),
        }
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
