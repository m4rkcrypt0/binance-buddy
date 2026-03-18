---
name: reward-history
description: Show recent Binance reward history using asset dividend records. Use when the user asks for reward history, reward dashboard, bonus history, campaign rewards, or Binance rewards. Show up to 15 recent reward records from the last 90 days, newest first.
---

# Reward History

Fetch Binance reward history and present recent rewards in a clean list.

## Workflow

1. Run `scripts/fetch_reward_history.py`.
2. Read the returned JSON.
3. Show up to 15 recent reward records.
4. Include the note line only when present.

## Rules

- Reuse the same workspace `.env` with `BINANCE_API_KEY` and `BINANCE_SECRET_KEY`.
- Filter to the last 90 days.
- Show top 15 recent rewards.
- Sort newest to oldest.
- Use date only in `YYYY-MM-DD` format.
- Do not show time.
- If a reward note is present, show it on the next line.

## Command

Run:

```bash
./scripts/fetch_reward_history.py
```

The script returns structured JSON for the agent to format.

## Output shape

```text
🎁 Reward History

1. 2026-03-04 — USDC — 50
SAFU CARD TG ENG
2. 2026-02-11 — USDT — 0.18
```
