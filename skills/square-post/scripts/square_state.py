#!/usr/bin/env python3
import argparse
import json
import time
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent.parent / "state" / "square_state.json"
HISTORY_LIMIT = 100
MIN_INTERVAL_SECONDS = 15 * 60
DAILY_LIMIT = 100
RECENT_TOPIC_LIMIT = 12


def now_ts() -> int:
    return int(time.time())


def ensure_parent() -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)


def default_state() -> dict:
    return {
        "currentDraft": None,
        "lastPublishAt": None,
        "publishHistory": [],
    }


def load_state() -> dict:
    if not STATE_PATH.exists():
        return default_state()
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return default_state()
        data.setdefault("currentDraft", None)
        data.setdefault("lastPublishAt", None)
        data.setdefault("publishHistory", [])
        return data
    except Exception:
        return default_state()


def save_state(state: dict) -> None:
    ensure_parent()
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def count_last_24h(history: list, current_ts: int) -> int:
    cutoff = current_ts - 86400
    return sum(1 for item in history if (item or {}).get("publishedAt", 0) >= cutoff)


def normalize_topic(topic: str | None) -> str | None:
    if topic is None:
        return None
    cleaned = " ".join(str(topic).strip().split())
    return cleaned or None


def recent_topics(state: dict, limit: int = RECENT_TOPIC_LIMIT) -> list[str]:
    topics = []
    seen = set()
    for item in state.get("publishHistory") or []:
        topic = normalize_topic((item or {}).get("topic"))
        if not topic:
            continue
        key = topic.casefold()
        if key in seen:
            continue
        seen.add(key)
        topics.append(topic)
        if len(topics) >= limit:
            break
    return topics


def publish_status(state: dict, current_ts: int | None = None) -> dict:
    current_ts = current_ts or now_ts()
    history = state.get("publishHistory") or []
    last_publish_at = state.get("lastPublishAt")
    posts_last_24h = count_last_24h(history, current_ts)
    seconds_since_last = None if not last_publish_at else max(0, current_ts - last_publish_at)
    cooldown_remaining = 0
    if last_publish_at:
        cooldown_remaining = max(0, MIN_INTERVAL_SECONDS - (current_ts - last_publish_at))
    daily_remaining = max(0, DAILY_LIMIT - posts_last_24h)
    can_publish = cooldown_remaining == 0 and posts_last_24h < DAILY_LIMIT
    reason = None
    if cooldown_remaining > 0:
        reason = "cooldown"
    elif posts_last_24h >= DAILY_LIMIT:
        reason = "daily_limit"
    return {
        "canPublish": can_publish,
        "reason": reason,
        "minIntervalSeconds": MIN_INTERVAL_SECONDS,
        "dailyLimit": DAILY_LIMIT,
        "lastPublishAt": last_publish_at,
        "secondsSinceLastPublish": seconds_since_last,
        "cooldownRemainingSeconds": cooldown_remaining,
        "postsLast24h": posts_last_24h,
        "dailyRemaining": daily_remaining,
    }


def cmd_get_draft(_: argparse.Namespace) -> int:
    state = load_state()
    print(json.dumps({"ok": True, "currentDraft": state.get("currentDraft")}, ensure_ascii=False))
    return 0


def cmd_save_draft(args: argparse.Namespace) -> int:
    text = (args.text or "").strip()
    if not text:
        print(json.dumps({"ok": False, "error": "Draft text is required"}))
        return 1
    state = load_state()
    topic = normalize_topic(args.topic)
    state["currentDraft"] = {
        "text": text,
        "topic": topic,
        "savedAt": now_ts(),
        "length": len(text),
    }
    save_state(state)
    print(json.dumps({"ok": True, "currentDraft": state["currentDraft"]}, ensure_ascii=False))
    return 0


def cmd_clear_draft(_: argparse.Namespace) -> int:
    state = load_state()
    state["currentDraft"] = None
    save_state(state)
    print(json.dumps({"ok": True, "cleared": True}))
    return 0


def cmd_log_publish(args: argparse.Namespace) -> int:
    text = (args.text or "").strip()
    if not text:
        print(json.dumps({"ok": False, "error": "Published text is required"}))
        return 1
    state = load_state()
    timestamp = now_ts()
    item = {
        "text": text,
        "topic": normalize_topic(args.topic),
        "postId": args.post_id,
        "postUrl": args.post_url,
        "publishedAt": timestamp,
        "length": len(text),
    }
    history = state.get("publishHistory") or []
    history.insert(0, item)
    state["publishHistory"] = history[:HISTORY_LIMIT]
    state["lastPublishAt"] = timestamp
    state["currentDraft"] = None
    save_state(state)
    result = {"ok": True, "lastPublishAt": timestamp, "historyCount": len(state['publishHistory'])}
    result.update(publish_status(state, timestamp))
    result["recentTopics"] = recent_topics(state)
    print(json.dumps(result, ensure_ascii=False))
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    state = load_state()
    draft = state.get("currentDraft")
    result = {
        "ok": True,
        "statePath": str(STATE_PATH),
        "hasDraft": bool(draft and draft.get("text")),
        "draftLength": (draft or {}).get("length"),
        "draftTopic": (draft or {}).get("topic"),
        "draftSavedAt": (draft or {}).get("savedAt"),
        "publishHistoryCount": len(state.get("publishHistory") or []),
        "recentTopics": recent_topics(state),
    }
    result.update(publish_status(state))
    print(json.dumps(result, ensure_ascii=False))
    return 0


def cmd_can_publish(_: argparse.Namespace) -> int:
    state = load_state()
    result = {"ok": True}
    result.update(publish_status(state))
    print(json.dumps(result, ensure_ascii=False))
    return 0


def cmd_recent(args: argparse.Namespace) -> int:
    state = load_state()
    limit = max(1, min(args.limit, HISTORY_LIMIT))
    history = (state.get("publishHistory") or [])[:limit]
    print(json.dumps({"ok": True, "items": history, "count": len(history)}, ensure_ascii=False))
    return 0


def cmd_recent_topics(args: argparse.Namespace) -> int:
    state = load_state()
    limit = max(1, min(args.limit, RECENT_TOPIC_LIMIT))
    topics = recent_topics(state, limit=limit)
    print(json.dumps({"ok": True, "items": topics, "count": len(topics)}, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage Binance Square draft/publish state")
    sub = parser.add_subparsers(dest="command", required=True)

    get_draft = sub.add_parser("get-draft")
    get_draft.set_defaults(func=cmd_get_draft)

    save_draft = sub.add_parser("save-draft")
    save_draft.add_argument("--text", required=True)
    save_draft.add_argument("--topic")
    save_draft.set_defaults(func=cmd_save_draft)

    clear_draft = sub.add_parser("clear-draft")
    clear_draft.set_defaults(func=cmd_clear_draft)

    log_publish = sub.add_parser("log-publish")
    log_publish.add_argument("--text", required=True)
    log_publish.add_argument("--topic")
    log_publish.add_argument("--post-id")
    log_publish.add_argument("--post-url")
    log_publish.set_defaults(func=cmd_log_publish)

    status = sub.add_parser("status")
    status.set_defaults(func=cmd_status)

    can_publish = sub.add_parser("can-publish")
    can_publish.set_defaults(func=cmd_can_publish)

    recent = sub.add_parser("recent")
    recent.add_argument("--limit", type=int, default=5)
    recent.set_defaults(func=cmd_recent)

    recent_topics_parser = sub.add_parser("recent-topics")
    recent_topics_parser.add_argument("--limit", type=int, default=5)
    recent_topics_parser.set_defaults(func=cmd_recent_topics)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
