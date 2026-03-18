---
name: binance-announcements
description: Show recent Binance announcements with support for general announcements, listing announcements, and delisting announcements. Use when the user asks for Binance announcements, recent announcements, latest listings, latest delistings, or similar Binance news requests. Show the top 5 most recent items from the last 30 days with release date, title, and Learn More link.
---

# Binance Announcements

Fetch recent Binance announcements and present them in a clean list.

## Workflow

1. Run `scripts/fetch_announcements.py` with the raw user query.
2. Read the returned JSON.
3. Detect whether the request is for:
   - general announcements
   - listings
   - delistings
4. Show the top 5 most recent items from the last 30 days.
5. Present release date, title, and Learn More link.

## Rules

- Default to general announcements if the user does not specify listings or delistings.
- Show only the top 5 most recent items.
- Use the last 30 days as the freshness window.
- Include release date when available.
- If release date is not available from the list payload, use the best reliable extracted date from the title when present.
- Always show a Learn More link.
- If no recent items are found for the chosen mode, say so plainly.

## Command

Run:

```bash
./scripts/fetch_announcements.py "recent listing announcements"
```

The script returns structured JSON for the agent to format.

## Output shape

```text
📢 Binance Announcements

1. 2026-03-17 — Binance Will List Example Token
Learn More: https://www.binance.com/en/support/announcement/...

2. 2026-03-13 — Notice of Removal of Spot Trading Pairs
Learn More: https://www.binance.com/en/support/announcement/...
```
