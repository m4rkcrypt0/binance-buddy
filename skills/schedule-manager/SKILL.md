---
name: schedule-manager
description: Create, list, pause, resume, and delete recurring Binance schedules backed by OpenClaw cron. Use when the user wants recurring crypto reports like "market overview every day at 3pm", "btc analysis every 4 hours", "show my portfolio every day at 9am", "send top gainers every hour", wants recurring Binance Square posting, wants to temporarily stop automation without deleting it, wants a one-command global pause/resume for all Square schedules in the current chat, or wants to view/delete saved schedules.
---

# Schedule Manager

Manage recurring Binance reports and Square posting using OpenClaw cron jobs.

## Workflow

1. Detect whether the user wants to create, show, pause, resume, delete, or inspect schedule status.
2. If the user asks for a broad action like `pause my square schedules` or `resume all square schedules`, prefer the bulk commands instead of requiring schedule IDs.
3. If the user wants to delete an obvious single schedule such as the only Square schedule or a specific market-analysis schedule, prefer deterministic `delete-match` instead of making the user find the id first.
4. Map the request to one supported schedule type.
5. Normalize the cadence into one of these rule families:
   - `interval`
   - `daily`
   - `weekly`
6. Normalize loose user wording into concrete script arguments before calling the script.
   - Example: `every day at 3pm` -> `--rule daily --time 15:00`
   - Example: `every 4 hours` -> `--rule interval --hours 4`
   - Example: `every 15 minutes` -> `--rule interval --minutes 15`
   - Example: `every monday at 9am` -> `--rule weekly --weekday monday --time 09:00`
7. Run `scripts/manage_schedules.py`.
8. Read the returned JSON.
9. Reply naturally from the result.

## Supported schedule types

- `market-overview`
- `top-movers`
- `top-gainers`
- `top-losers`
- `announcements-digest`
- `campaign-digest`
- `launchpool-digest`
- `promotion-digest`
- `price-snapshot`
- `market-analysis`
- `portfolio-overview`
- `portfolio-health-check`
- `portfolio-advisor`
- `portfolio-opportunity-scanner`
- `correlation-alpha-matrix`
- `square-post`

## Rules

- Keep schedules scoped to the current chat by passing the current chat id as `--chat-id`.
- Use the current delivery route by passing the current channel and target.
- Enforce a maximum of 20 active schedules per chat.
- For most interval schedules, enforce at least 1 hour between runs.
- For heavier report types, respect stricter minimum intervals returned by the script.
- `square-post` supports optional topic input and can run as often as every 15 minutes.
- `price-snapshot` supports up to 10 symbols.
- `market-analysis` supports exactly one symbol and an optional timeframe of `1h`, `4h`, or `1d`.
- Pause should stop the cron job without losing the saved schedule definition.
- Resume should recreate the cron job from the saved schedule definition.
- Bulk pause/resume should operate on matching schedules in the current chat without needing IDs.
- If a cron job is already missing, cleanup should still succeed locally and report a clean warning instead of failing the whole action.
- Show script errors cleanly instead of dumping raw tracebacks.

## Command patterns

Create a daily schedule:

```bash
./scripts/manage_schedules.py create --type market-overview --rule daily --time 15:00 --chat-id telegram:6935201375 --channel telegram --target 6935201375
```

Create an interval schedule:

```bash
./scripts/manage_schedules.py create --type market-analysis --symbol BTCUSDT --timeframe 4h --rule interval --hours 4 --chat-id telegram:6935201375 --channel telegram --target 6935201375
```

Create a Square post schedule:

```bash
./scripts/manage_schedules.py create --type square-post --rule interval --minutes 15 --chat-id telegram:6935201375 --channel telegram --target 6935201375
```

Status summary:

```bash
./scripts/manage_schedules.py status --chat-id telegram:6935201375
```

Pause one schedule by id:

```bash
./scripts/manage_schedules.py pause --id 1 --chat-id telegram:6935201375
```

Resume one schedule by id:

```bash
./scripts/manage_schedules.py resume --id 1 --chat-id telegram:6935201375
```

Pause all Square schedules in the current chat:

```bash
./scripts/manage_schedules.py pause-all --chat-id telegram:6935201375 --type square-post
```

Resume all paused Square schedules in the current chat:

```bash
./scripts/manage_schedules.py resume-all --chat-id telegram:6935201375 --type square-post
```

Delete one schedule by deterministic match:

```bash
./scripts/manage_schedules.py delete-match --type square-post --chat-id telegram:6935201375
./scripts/manage_schedules.py delete-match --type market-analysis --symbol BTCUSDT --chat-id telegram:6935201375
```

List active schedules:

```bash
./scripts/manage_schedules.py list --chat-id telegram:6935201375
```

List all schedules including paused:

```bash
./scripts/manage_schedules.py list --chat-id telegram:6935201375 --all
```

Delete by id:

```bash
./scripts/manage_schedules.py delete --id 1 --chat-id telegram:6935201375
```

## Reply guidance

- On create, return the script message as-is.
- On pause, resume, pause-all, resume-all, delete, and delete-match, return the script message as-is.
- On status, use the script fields like `activeCount`, `pausedCount`, `countsByType`, and `nextDue` to summarize naturally.
- On list, use the script-provided `summary`, `status`, `nextRunText`, and `nextRunIn` fields when available.
- Format active schedules like:

```text
🗓️ Active Schedules

1. market overview every day at 15:00 UTC — next run in 8h 12m
2. BTC analysis (4h) every 4 hours — next run in 2h
3. square post (random topic) every 15 minutes — next run in 14m
```

- If showing paused schedules too, label them clearly, for example:

```text
4. square post (random topic) every 15 minutes — paused
```

- Prefer `nextRunIn` for the main line. If helpful, add a second indented line like `Next: 2026-03-18 15:00 UTC`.
- If `delete-match` returns multiple matches, ask a short follow-up or show the matching numbered choices.
- If there are no active schedules, reply: `You have no active schedules right now.`
- For duplicate/create-limit/frequency errors, return the script error as-is.
