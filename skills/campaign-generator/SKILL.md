---
name: campaign-generator
description: Show recent Binance campaign-style announcements with support for New Campaign, Launchpool, and Promotion views. Use when the user asks for Binance campaigns, launchpool campaigns, megadrop, airdrops, earn campaigns, staking campaigns, or promotion campaigns. Show the top 5 most recent items from the last 30 days with title, Learn More link, and date.
---

# Campaign Generator

Fetch recent Binance campaign-related announcements and present them in a clean list.

## Workflow

1. Run `scripts/fetch_campaigns.py` with the raw user query.
2. Read the returned JSON.
3. Detect whether the request is for:
   - new campaign
   - launchpool
   - promotion
4. Show the top 5 most recent campaign items from the last 30 days.
5. Present title, Learn More link, and date.

## Rules

- Use `🎁` as the main icon.
- Default to `New Campaign` if the user does not specify launchpool or promotion.
- Launchpool keywords include: `launchpool`, `megadrop`, `airdrop`.
- Promotion keywords include: `earn`, `simple earn`, `staking`, `promotion`, `campaign`.
- Show only the top 5 most recent items.
- Use the last 30 days as the freshness window.
- Show `🗓️ Date:` when a reliable published date is available.
- Insert a blank line between each campaign block.
- If no recent items are found for the chosen mode, say so plainly.

## Command

Run:

```bash
./scripts/fetch_campaigns.py "show me launchpool campaigns"
```

The script returns structured JSON for the agent to format.

## Output shape

```text
🎁 New Campaign

1. Title
Learn More: https://www.binance.com/en/support/announcement/...
🗓️ Date: 2026-03-17
```
