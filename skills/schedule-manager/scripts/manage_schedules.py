#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
DATA_FILE = os.path.join(ROOT_DIR, "data", "schedules.json")
MAX_ACTIVE_SCHEDULES = 20
MAX_SNAPSHOT_SYMBOLS = 10
DEFAULT_MIN_INTERVAL_MINUTES = 60

ALIASES = {
    "BITCOIN": "BTC",
    "ETHEREUM": "ETH",
    "SOLANA": "SOL",
    "RIPPLE": "XRP",
    "DOGECOIN": "DOGE",
    "SHIBA": "SHIB",
    "SHIBAINU": "SHIB",
    "BINANCECOIN": "BNB",
    "BINANCE": "BNB",
    "POLYGON": "POL",
    "MATIC": "POL",
    "AVALANCHE": "AVAX",
    "CHAINLINK": "LINK",
    "LITECOIN": "LTC",
    "CARDANO": "ADA",
    "TRON": "TRX",
    "TONCOIN": "TON",
    "PEPECOIN": "PEPE",
}

ALLOWED_TYPES = {
    "market-overview",
    "top-movers",
    "top-gainers",
    "top-losers",
    "announcements-digest",
    "campaign-digest",
    "launchpool-digest",
    "promotion-digest",
    "price-snapshot",
    "market-analysis",
    "portfolio-overview",
    "portfolio-health-check",
    "portfolio-advisor",
    "portfolio-opportunity-scanner",
    "correlation-alpha-matrix",
    "square-post",
}

TYPE_MIN_INTERVAL_MINUTES = {
    "market-overview": 24 * 60,
    "market-analysis": 4 * 60,
    "portfolio-health-check": 24 * 60,
    "portfolio-advisor": 24 * 60,
    "portfolio-opportunity-scanner": 24 * 60,
    "correlation-alpha-matrix": 24 * 60,
    "square-post": 15,
}

TYPE_LABELS = {
    "market-overview": "market overview",
    "top-movers": "top movers",
    "top-gainers": "top gainers",
    "top-losers": "top losers",
    "announcements-digest": "announcements digest",
    "campaign-digest": "campaign digest",
    "launchpool-digest": "launchpool digest",
    "promotion-digest": "promotion digest",
    "price-snapshot": "price snapshot",
    "market-analysis": "market analysis",
    "portfolio-overview": "portfolio overview",
    "portfolio-health-check": "portfolio health check",
    "portfolio-advisor": "portfolio advisor",
    "portfolio-opportunity-scanner": "portfolio opportunity scanner",
    "correlation-alpha-matrix": "correlation alpha matrix",
    "square-post": "square post",
}

WEEKDAY_MAP = {
    "mon": 1,
    "monday": 1,
    "tue": 2,
    "tuesday": 2,
    "wed": 3,
    "wednesday": 3,
    "thu": 4,
    "thursday": 4,
    "fri": 5,
    "friday": 5,
    "sat": 6,
    "saturday": 6,
    "sun": 0,
    "sunday": 0,
}


def utc_now():
    return datetime.now(timezone.utc)


def utc_now_iso():
    return utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def format_epoch_ms(ms):
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def humanize_until_ms(ms):
    seconds = int((datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc) - utc_now()).total_seconds())
    if seconds <= 0:
        return "due now"
    minutes = max(1, (seconds + 59) // 60)
    if minutes < 60:
        return f"in {minutes}m"
    hours = minutes // 60
    rem_minutes = minutes % 60
    if rem_minutes:
        return f"in {hours}h {rem_minutes}m"
    return f"in {hours}h"


def load_store():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        data = {"schedules": []}
    except json.JSONDecodeError:
        raise ValueError("schedules.json is invalid JSON")
    schedules = data.get("schedules")
    if not isinstance(schedules, list):
        raise ValueError("schedules.json must contain a schedules array")
    return data


def save_store(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def schedules_for_chat(schedules, chat_id):
    return [item for item in schedules if item.get("chatId") == chat_id]


def active_schedules_for_chat(schedules, chat_id):
    return [item for item in schedules_for_chat(schedules, chat_id) if item.get("active", True)]


def next_id(schedules):
    highest = 0
    for item in schedules:
        try:
            highest = max(highest, int(item.get("id", 0)))
        except (TypeError, ValueError):
            continue
    return highest + 1


def normalize_symbol(raw_symbol):
    if not raw_symbol:
        raise ValueError("Missing symbol")
    token = "".join(ch for ch in raw_symbol.upper() if ch.isalnum())
    if not token:
        raise ValueError("Missing symbol")
    if token.endswith("USDT") and len(token) > 4:
        token = token[:-4]
    token = ALIASES.get(token, token)
    return f"{token}USDT"


def normalize_symbols(raw_symbols):
    if not raw_symbols:
        raise ValueError("Missing symbols")
    parts = re.split(r"[\s,]+", raw_symbols.strip())
    symbols = []
    seen = set()
    for part in parts:
        if not part:
            continue
        symbol = normalize_symbol(part)
        if symbol in seen:
            continue
        seen.add(symbol)
        symbols.append(symbol)
    if not symbols:
        raise ValueError("Missing symbols")
    if len(symbols) > MAX_SNAPSHOT_SYMBOLS:
        raise ValueError(f"Price snapshots support up to {MAX_SNAPSHOT_SYMBOLS} symbols.")
    return symbols


def parse_time_hhmm(value):
    if not value or not re.fullmatch(r"\d{2}:\d{2}", value):
        raise ValueError("Time must be in HH:MM format")
    hours, minutes = value.split(":")
    h = int(hours)
    m = int(minutes)
    if h < 0 or h > 23 or m < 0 or m > 59:
        raise ValueError("Time must be a valid HH:MM value")
    return f"{h:02d}:{m:02d}", h, m


def build_rule(args):
    rule = args.rule
    if rule == "interval":
        has_hours = args.hours is not None
        has_minutes = args.minutes is not None
        if has_hours and has_minutes:
            raise ValueError("Use either hours or minutes for interval schedules, not both.")
        if not has_hours and not has_minutes:
            raise ValueError("Missing interval duration")
        if has_minutes:
            minutes = int(args.minutes)
            if minutes < 1:
                raise ValueError("Interval minutes must be at least 1.")
            return {"kind": "interval", "minutes": minutes}
        hours = int(args.hours)
        if hours < 1:
            raise ValueError("Schedules must be at least 1 hour apart.")
        return {"kind": "interval", "minutes": hours * 60}
    if rule == "daily":
        time_text, _, _ = parse_time_hhmm(args.time)
        return {"kind": "daily", "time": time_text, "timezone": "UTC"}
    if rule == "weekly":
        if not args.weekday:
            raise ValueError("Weekly schedules require a weekday")
        weekday_key = args.weekday.strip().lower()
        if weekday_key not in WEEKDAY_MAP:
            raise ValueError("Invalid weekday")
        time_text, _, _ = parse_time_hhmm(args.time)
        return {"kind": "weekly", "weekday": weekday_key, "time": time_text, "timezone": "UTC"}
    raise ValueError(f"Unsupported rule: {rule}")


def validate_type_specific(args):
    params = {}
    if args.type == "price-snapshot":
        params["symbols"] = normalize_symbols(args.symbols)
    elif args.type == "market-analysis":
        params["symbol"] = normalize_symbol(args.symbol)
        params["timeframe"] = (args.timeframe or "4h").lower()
        if params["timeframe"] not in {"1h", "4h", "1d"}:
            raise ValueError("Market analysis timeframe must be 1h, 4h, or 1d.")
    elif args.type == "square-post":
        topic = (args.topic or "").strip()
        if topic:
            params["topic"] = topic
    return params


def validate_frequency(task_type, rule):
    if rule["kind"] == "interval":
        minimum = TYPE_MIN_INTERVAL_MINUTES.get(task_type, DEFAULT_MIN_INTERVAL_MINUTES)
        minutes = int(rule["minutes"])
        if minutes < minimum:
            if minimum % 60 == 0:
                hours = minimum // 60
                if hours == 1:
                    raise ValueError("Schedules must be at least 1 hour apart.")
                raise ValueError(f"That schedule is too frequent for this report type. Minimum: every {hours} hours.")
            raise ValueError(f"That schedule is too frequent for this schedule type. Minimum: every {minimum} minutes.")


def build_payload_message(task_type, params):
    if task_type == "market-overview":
        return "Give me the Binance market overview."
    if task_type == "top-movers":
        return "Show the top movers across Spot and Futures on Binance."
    if task_type == "top-gainers":
        return "Show the top gainers across Spot and Futures on Binance."
    if task_type == "top-losers":
        return "Show the top losers across Spot and Futures on Binance."
    if task_type == "announcements-digest":
        return "Show the latest Binance announcements."
    if task_type == "campaign-digest":
        return "Show the latest Binance campaigns."
    if task_type == "launchpool-digest":
        return "Show the latest Binance launchpool updates."
    if task_type == "promotion-digest":
        return "Show the latest Binance promotions."
    if task_type == "price-snapshot":
        symbols = " ".join(symbol.replace("USDT", "") for symbol in params["symbols"])
        return f"Show Binance spot prices for {symbols}."
    if task_type == "market-analysis":
        return f"Analyze {params['symbol'].replace('USDT', '')} on Binance using the {params['timeframe']} timeframe."
    if task_type == "portfolio-overview":
        return "Show my Binance portfolio."
    if task_type == "portfolio-health-check":
        return "Give me a Binance portfolio health check."
    if task_type == "portfolio-advisor":
        return "Give me Binance portfolio advice based on current structure."
    if task_type == "portfolio-opportunity-scanner":
        return "Scan my Binance portfolio for the holdings that deserve attention now."
    if task_type == "correlation-alpha-matrix":
        return "Analyze my Binance portfolio correlation against BTC."
    if task_type == "square-post":
        topic = (params.get("topic") or "").strip()
        if topic:
            return (
                "Generate one interesting Binance Square post and publish it automatically now. "
                f"Use this topic: {topic}. Target about 500 characters total, use natural emojis, and place hashtags at the end. "
                "Save the generated draft locally, then publish only through the saved-draft Square flow so cooldown/quota checks are enforced. "
                "After publishing, return the Square post URL or the block reason."
            )
        return (
            "Generate one interesting Binance Square post and publish it automatically now. "
            "Choose a random crypto-native topic, target about 500 characters total, use natural emojis, and place hashtags at the end. "
            "Save the generated draft locally, then publish only through the saved-draft Square flow so cooldown/quota checks are enforced. "
            "After publishing, return the Square post URL or the block reason."
        )
    raise ValueError(f"Unsupported schedule type: {task_type}")


def build_schedule_cli_args(rule):
    if rule["kind"] == "interval":
        minutes = int(rule["minutes"])
        if minutes % 60 == 0:
            hours = minutes // 60
            return ["--every", f"{hours}h"]
        return ["--every", f"{minutes}m"]
    if rule["kind"] == "daily":
        hh, mm = rule["time"].split(":")
        return ["--cron", f"{int(mm)} {int(hh)} * * *", "--tz", rule.get("timezone", "UTC"), "--exact"]
    if rule["kind"] == "weekly":
        hh, mm = rule["time"].split(":")
        dow = WEEKDAY_MAP[rule["weekday"]]
        return ["--cron", f"{int(mm)} {int(hh)} * * {dow}", "--tz", rule.get("timezone", "UTC"), "--exact"]
    raise ValueError(f"Unsupported rule kind: {rule['kind']}")


def format_interval_minutes(minutes):
    minutes = int(minutes)
    if minutes % 60 == 0:
        hours = minutes // 60
        return f"every {hours} hour{'s' if hours != 1 else ''}"
    return f"every {minutes} minute{'s' if minutes != 1 else ''}"


def build_summary(task_type, params, rule):
    labels = {
        "market-overview": "market overview",
        "top-movers": "top movers",
        "top-gainers": "top gainers",
        "top-losers": "top losers",
        "announcements-digest": "announcements digest",
        "campaign-digest": "campaign digest",
        "launchpool-digest": "launchpool digest",
        "promotion-digest": "promotion digest",
        "price-snapshot": f"price snapshot for {' '.join(symbol.replace('USDT', '') for symbol in params.get('symbols', []))}",
        "market-analysis": f"{params.get('symbol', '').replace('USDT', '')} analysis ({params.get('timeframe', '4h')})",
        "portfolio-overview": "portfolio overview",
        "portfolio-health-check": "portfolio health check",
        "portfolio-advisor": "portfolio advisor",
        "portfolio-opportunity-scanner": "portfolio opportunity scanner",
        "correlation-alpha-matrix": "correlation alpha matrix",
        "square-post": f"square post ({params.get('topic')})" if params.get("topic") else "square post (random topic)",
    }
    base = labels[task_type]
    if rule["kind"] == "interval":
        return f"{base} {format_interval_minutes(rule['minutes'])}"
    if rule["kind"] == "daily":
        return f"{base} every day at {rule['time']} UTC"
    return f"{base} every {rule['weekday']} at {rule['time']} UTC"


def run_command(command):
    return subprocess.run(command, capture_output=True, text=True, check=False)


def create_cron_job(name, message, rule, channel, target):
    command = [
        "openclaw", "cron", "add",
        "--name", name,
        *build_schedule_cli_args(rule),
        "--session", "isolated",
        "--message", message,
        "--announce",
        "--channel", channel,
        "--to", target,
        "--json",
    ]
    result = run_command(command)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Failed to create cron job")
    return json.loads(result.stdout)


def remove_cron_job(job_id):
    result = run_command(["openclaw", "cron", "rm", job_id, "--json"])
    if result.returncode == 0:
        return {"ok": True, "removed": True, "alreadyMissing": False}
    text = f"{result.stdout}\n{result.stderr}".lower()
    if "not found" in text or "no such" in text or "unknown job" in text:
        return {"ok": True, "removed": False, "alreadyMissing": True}
    raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Failed to remove cron job")


def duplicate_key(task_type, params, rule):
    return json.dumps({"type": task_type, "params": params, "rule": rule}, sort_keys=True)


def find_schedule(schedules, chat_id, schedule_id):
    for item in schedules:
        if item.get("chatId") == chat_id and str(item.get("id")) == str(schedule_id):
            return item
    return None


def matches_type(item, schedule_type):
    return not schedule_type or item.get("type") == schedule_type


def matches_delete_filter(item, schedule_type=None, symbol=None, topic=None):
    if schedule_type and item.get("type") != schedule_type:
        return False
    if symbol and (item.get("params") or {}).get("symbol") != symbol:
        return False
    if topic is not None and ((item.get("params") or {}).get("topic") or "") != topic:
        return False
    return True


def pause_schedule(item):
    removal = None
    job_id = item.get("cronJobId")
    if job_id and item.get("active", True):
        removal = remove_cron_job(job_id)
    item["active"] = False
    item["paused"] = True
    item["updatedAt"] = utc_now_iso()
    item.pop("nextRunAtMs", None)
    return removal or {"ok": True, "removed": False, "alreadyMissing": False}


def resume_schedule(item):
    cron_name = item.get("cronName") or f"schedule-manager:{item.get('summary')}"
    message = item.get("cronMessage") or build_payload_message(item.get("type"), item.get("params") or {})
    created = create_cron_job(cron_name, message, item.get("rule") or {}, item.get("channel"), item.get("target"))
    item["cronJobId"] = created.get("id")
    item["cronName"] = cron_name
    item["cronMessage"] = message
    item["active"] = True
    item["paused"] = False
    item["updatedAt"] = utc_now_iso()
    next_run_ms = ((created.get("state") or {}).get("nextRunAtMs"))
    if next_run_ms:
        item["nextRunAtMs"] = next_run_ms
    else:
        item.pop("nextRunAtMs", None)


def cmd_create(args):
    if args.type not in ALLOWED_TYPES:
        raise ValueError(f"Unsupported schedule type: {args.type}")
    if not args.chat_id:
        raise ValueError("Missing chat id")
    if not args.channel or not args.target:
        raise ValueError("Missing delivery route for this schedule.")

    data = load_store()
    schedules = data["schedules"]
    active = active_schedules_for_chat(schedules, args.chat_id)
    if len(active) >= MAX_ACTIVE_SCHEDULES:
        return {"ok": False, "error": f"You already have {MAX_ACTIVE_SCHEDULES} active schedules. Delete one before adding another."}

    rule = build_rule(args)
    validate_frequency(args.type, rule)
    params = validate_type_specific(args)
    key = duplicate_key(args.type, params, rule)
    for item in active:
        if item.get("duplicateKey") == key:
            return {"ok": False, "error": "You already have that schedule active.", "duplicateId": item.get("id")}

    summary = build_summary(args.type, params, rule)
    message = build_payload_message(args.type, params)
    cron_name = f"schedule-manager:{summary}"
    created = create_cron_job(cron_name, message, rule, args.channel, args.target)

    schedule = {
        "id": next_id(schedules),
        "chatId": args.chat_id,
        "channel": args.channel,
        "target": args.target,
        "type": args.type,
        "params": params,
        "rule": rule,
        "summary": summary,
        "duplicateKey": key,
        "cronJobId": created.get("id"),
        "cronName": cron_name,
        "cronMessage": message,
        "createdAt": utc_now_iso(),
        "updatedAt": utc_now_iso(),
        "active": True,
        "paused": False,
    }
    next_run_ms = ((created.get("state") or {}).get("nextRunAtMs"))
    if next_run_ms:
        schedule["nextRunAtMs"] = next_run_ms
    schedules.append(schedule)
    save_store(data)
    return {"ok": True, "message": f"✅ Schedule set: {summary}.", "schedule": schedule}


def serialize_schedule_for_list(item):
    payload = dict(item)
    next_run_ms = payload.get("nextRunAtMs")
    if payload.get("active", True) and next_run_ms:
        payload["nextRunText"] = format_epoch_ms(next_run_ms)
        payload["nextRunIn"] = humanize_until_ms(next_run_ms)
    payload["status"] = "paused" if payload.get("paused") else "active"
    return payload


def cmd_list(args):
    if not args.chat_id:
        raise ValueError("Missing chat id")
    data = load_store()
    items = schedules_for_chat(data["schedules"], args.chat_id)
    if not getattr(args, "all", False):
        items = [item for item in items if item.get("active", True)]
    items = sorted(items, key=lambda item: int(item.get("id", 0)))
    return {"ok": True, "count": len(items), "schedules": [serialize_schedule_for_list(item) for item in items]}


def cmd_status(args):
    if not args.chat_id:
        raise ValueError("Missing chat id")
    data = load_store()
    items = schedules_for_chat(data["schedules"], args.chat_id)
    active_items = [item for item in items if item.get("active", True)]
    paused_items = [item for item in items if item.get("paused")]
    counts = {}
    for item in items:
        counts[item.get("type")] = counts.get(item.get("type"), 0) + 1
    next_due = None
    if active_items:
        next_due_item = min((item for item in active_items if item.get("nextRunAtMs")), key=lambda x: int(x.get("nextRunAtMs")), default=None)
        if next_due_item:
            next_due = {
                "id": next_due_item.get("id"),
                "summary": next_due_item.get("summary"),
                "nextRunText": format_epoch_ms(next_due_item.get("nextRunAtMs")),
                "nextRunIn": humanize_until_ms(next_due_item.get("nextRunAtMs")),
            }
    return {
        "ok": True,
        "totalCount": len(items),
        "activeCount": len(active_items),
        "pausedCount": len(paused_items),
        "countsByType": counts,
        "nextDue": next_due,
        "maxActiveSchedules": MAX_ACTIVE_SCHEDULES,
    }


def cmd_delete(args):
    if not args.chat_id:
        raise ValueError("Missing chat id")
    if args.id is None:
        raise ValueError("Missing schedule id")
    data = load_store()
    schedules = data["schedules"]
    kept = []
    deleted = None
    warning = None
    for item in schedules:
        same_chat = item.get("chatId") == args.chat_id
        same_id = str(item.get("id")) == str(args.id)
        if same_chat and same_id:
            deleted = item
            continue
        kept.append(item)
    if deleted is None:
        return {"ok": False, "error": f"Schedule {args.id} not found."}
    job_id = deleted.get("cronJobId")
    if job_id and deleted.get("active", True):
        removal = remove_cron_job(job_id)
        if removal.get("alreadyMissing"):
            warning = "Cron job was already missing, but local schedule state was removed."
    data["schedules"] = kept
    save_store(data)
    result = {"ok": True, "message": f"❌ Schedule Deleted: {deleted.get('summary')}.", "deleted": deleted}
    if warning:
        result["warning"] = warning
    return result


def cmd_delete_match(args):
    if not args.chat_id:
        raise ValueError("Missing chat id")
    if not args.type:
        raise ValueError("Missing schedule type")
    if args.type not in ALLOWED_TYPES:
        raise ValueError(f"Unsupported schedule type: {args.type}")

    symbol = normalize_symbol(args.symbol) if args.symbol else None
    topic = args.topic.strip() if args.topic is not None else None

    data = load_store()
    matches = [
        item for item in schedules_for_chat(data["schedules"], args.chat_id)
        if matches_delete_filter(item, args.type, symbol=symbol, topic=topic)
    ]
    if not matches:
        return {"ok": False, "error": "No matching schedule found."}
    if len(matches) > 1:
        return {
            "ok": False,
            "error": "More than one matching schedule found. Delete by id instead.",
            "matches": [serialize_schedule_for_list(item) for item in matches],
        }

    match = matches[0]
    args.id = match.get("id")
    return cmd_delete(args)


def cmd_pause(args):
    if not args.chat_id:
        raise ValueError("Missing chat id")
    if args.id is None:
        raise ValueError("Missing schedule id")
    data = load_store()
    item = find_schedule(data["schedules"], args.chat_id, args.id)
    if item is None:
        return {"ok": False, "error": f"Schedule {args.id} not found."}
    if item.get("paused") or not item.get("active", True):
        return {"ok": False, "error": f"Schedule {args.id} is already paused."}
    removal = pause_schedule(item)
    save_store(data)
    result = {"ok": True, "message": f"⏸️ Schedule Paused: {item.get('summary')}.", "schedule": item}
    if removal.get("alreadyMissing"):
        result["warning"] = "Cron job was already missing, but the schedule is now marked paused locally."
    return result


def cmd_resume(args):
    if not args.chat_id:
        raise ValueError("Missing chat id")
    if args.id is None:
        raise ValueError("Missing schedule id")
    data = load_store()
    schedules = data["schedules"]
    item = find_schedule(schedules, args.chat_id, args.id)
    if item is None:
        return {"ok": False, "error": f"Schedule {args.id} not found."}
    if item.get("active", True) and not item.get("paused"):
        return {"ok": False, "error": f"Schedule {args.id} is already active."}

    active = active_schedules_for_chat(schedules, args.chat_id)
    if len(active) >= MAX_ACTIVE_SCHEDULES:
        return {"ok": False, "error": f"You already have {MAX_ACTIVE_SCHEDULES} active schedules. Delete or pause one before resuming another."}

    resume_schedule(item)
    save_store(data)
    return {"ok": True, "message": f"▶️ Schedule Resumed: {item.get('summary')}.", "schedule": item}


def cmd_pause_all(args):
    if not args.chat_id:
        raise ValueError("Missing chat id")
    data = load_store()
    items = [item for item in schedules_for_chat(data["schedules"], args.chat_id) if item.get("active", True) and matches_type(item, args.type)]
    if not items:
        label = TYPE_LABELS.get(args.type, args.type) if args.type else "matching"
        return {"ok": False, "error": f"No active {label} schedules found."}
    already_missing = 0
    for item in items:
        removal = pause_schedule(item)
        if removal.get("alreadyMissing"):
            already_missing += 1
    save_store(data)
    result = {
        "ok": True,
        "message": f"⏸️ Paused {len(items)} schedule{'s' if len(items) != 1 else ''}.",
        "count": len(items),
        "schedules": items,
    }
    if already_missing:
        result["warning"] = f"{already_missing} cron job{'s were' if already_missing != 1 else ' was'} already missing, but local schedules were paused cleanly."
    return result


def cmd_resume_all(args):
    if not args.chat_id:
        raise ValueError("Missing chat id")
    data = load_store()
    schedules = data["schedules"]
    items = [item for item in schedules_for_chat(schedules, args.chat_id) if item.get("paused") and matches_type(item, args.type)]
    if not items:
        label = TYPE_LABELS.get(args.type, args.type) if args.type else "matching"
        return {"ok": False, "error": f"No paused {label} schedules found."}
    active = active_schedules_for_chat(schedules, args.chat_id)
    remaining_capacity = MAX_ACTIVE_SCHEDULES - len(active)
    if len(items) > remaining_capacity:
        return {"ok": False, "error": f"Cannot resume {len(items)} schedules because only {remaining_capacity} active slot{'s' if remaining_capacity != 1 else ''} remain."}
    for item in items:
        resume_schedule(item)
    save_store(data)
    return {
        "ok": True,
        "message": f"▶️ Resumed {len(items)} schedule{'s' if len(items) != 1 else ''}.",
        "count": len(items),
        "schedules": items,
    }


def build_parser():
    parser = argparse.ArgumentParser(description="Manage OpenClaw-backed schedules.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Create a schedule")
    create_parser.add_argument("--type", required=True)
    create_parser.add_argument("--rule", required=True, choices=["interval", "daily", "weekly"])
    create_parser.add_argument("--hours", type=int)
    create_parser.add_argument("--minutes", type=int)
    create_parser.add_argument("--time")
    create_parser.add_argument("--weekday")
    create_parser.add_argument("--symbol")
    create_parser.add_argument("--symbols")
    create_parser.add_argument("--timeframe")
    create_parser.add_argument("--topic")
    create_parser.add_argument("--chat-id", required=True)
    create_parser.add_argument("--channel", required=True)
    create_parser.add_argument("--target", required=True)

    list_parser = subparsers.add_parser("list", help="List schedules")
    list_parser.add_argument("--chat-id", required=True)
    list_parser.add_argument("--all", action="store_true")

    status_parser = subparsers.add_parser("status", help="Show schedule status summary")
    status_parser.add_argument("--chat-id", required=True)

    delete_parser = subparsers.add_parser("delete", help="Delete schedule by id")
    delete_parser.add_argument("--id", required=True)
    delete_parser.add_argument("--chat-id", required=True)

    delete_match_parser = subparsers.add_parser("delete-match", help="Delete one schedule by deterministic match")
    delete_match_parser.add_argument("--type", required=True)
    delete_match_parser.add_argument("--symbol")
    delete_match_parser.add_argument("--topic")
    delete_match_parser.add_argument("--chat-id", required=True)

    pause_parser = subparsers.add_parser("pause", help="Pause schedule by id")
    pause_parser.add_argument("--id", required=True)
    pause_parser.add_argument("--chat-id", required=True)

    resume_parser = subparsers.add_parser("resume", help="Resume schedule by id")
    resume_parser.add_argument("--id", required=True)
    resume_parser.add_argument("--chat-id", required=True)

    pause_all_parser = subparsers.add_parser("pause-all", help="Pause all matching schedules for a chat")
    pause_all_parser.add_argument("--chat-id", required=True)
    pause_all_parser.add_argument("--type")

    resume_all_parser = subparsers.add_parser("resume-all", help="Resume all matching paused schedules for a chat")
    resume_all_parser.add_argument("--chat-id", required=True)
    resume_all_parser.add_argument("--type")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "create":
            result = cmd_create(args)
        elif args.command == "list":
            result = cmd_list(args)
        elif args.command == "status":
            result = cmd_status(args)
        elif args.command == "delete":
            result = cmd_delete(args)
        elif args.command == "delete-match":
            result = cmd_delete_match(args)
        elif args.command == "pause":
            result = cmd_pause(args)
        elif args.command == "resume":
            result = cmd_resume(args)
        elif args.command == "pause-all":
            result = cmd_pause_all(args)
        elif args.command == "resume-all":
            result = cmd_resume_all(args)
        else:
            raise ValueError(f"Unsupported command: {args.command}")
    except (ValueError, RuntimeError) as exc:
        result = {"ok": False, "error": str(exc)}

    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
