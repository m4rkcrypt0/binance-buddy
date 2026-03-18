---
name: alert-manager
description: Create, list, and delete short-lived Binance alerts. Use when the user wants a price alert such as "alert me when btc hits 75000", wants alerts for new Binance announcements, listings, delistings, launchpool items, campaigns, or promotions, wants to see active alerts, or wants to delete an alert. Keep alerts limited to 30 minutes and use the management script output to format the reply.
---

# Alert Manager

Manage short-lived Binance alerts with a deterministic state file and local watcher.

## Workflow

1. Detect whether the user wants to create, show, delete, or inspect alert status.
2. Map the request to one of these alert types:
   - `price-above`
   - `price-below`
   - `announcement`
   - `listing`
   - `delisting`
   - `launchpool`
   - `campaign`
   - `promotion`
3. For price alerts, normalize the symbol to a Binance `USDT` pair and infer whether the request means `price-above` or `price-below`.
4. Prefer deterministic delete matching when the user refers to an alert by type or obvious identity, instead of listing first and manually resolving ids.
5. Run `scripts/manage_alerts.py` with the matching command.
6. Read the returned JSON.
7. Reply naturally from the script result.

## Rules

- Price phrases like `hits 75000`, `goes above 75000`, or `reaches 75000` map to `price-above`.
- Treat phrases like `goes below 70000`, `drops below 70000`, `falls under 70000`, or `under 70000` as `price-below`.
- If the user gives only a bare target like `alert me when btc is 75000` or `when btc 75000`, ask a follow-up: `Above or below 75,000?`
- Support content phrasing such as:
  - `new announcement`
  - `new listing`
  - `new delisting`
  - `new launchpool`
  - `new campaign`
  - `new promotion`
- Keep alerts scoped to the current chat by passing the current chat id as `--chat-id`.
- List and delete only alerts for the current chat.
- If the user says `delete my btc alert`, `remove my launchpool alert`, or similar, prefer `delete-match` first. Fall back to id deletion only when matching is ambiguous.
- Show script errors cleanly instead of dumping raw tracebacks.
- Alerts last 30 minutes in this version.
- Reject custom polling requests like `every second` or `every minute` with a short reply explaining that alerts do not support custom polling cadence.
- If the user asks for pause/resume, say that is not in this slice yet.

## Commands

Create a price alert:

```bash
./scripts/manage_alerts.py create --type price-above --symbol BTCUSDT --target 75000 --chat-id telegram:6935201375
```

Create a content alert:

```bash
./scripts/manage_alerts.py create --type launchpool --chat-id telegram:6935201375
```

Content alerts are persistent in this version and do not expire automatically.

List:

```bash
./scripts/manage_alerts.py list --chat-id telegram:6935201375
```

Delete by id:

```bash
./scripts/manage_alerts.py delete --id 1 --chat-id telegram:6935201375
```

Delete by deterministic match:

```bash
./scripts/manage_alerts.py delete-match --type launchpool --chat-id telegram:6935201375
./scripts/manage_alerts.py delete-match --type price-above --symbol BTCUSDT --target 75000 --chat-id telegram:6935201375
```

Status:

```bash
./scripts/manage_alerts.py status --chat-id telegram:6935201375
```

## Reply guidance

- On create, return the script message as-is.
- On list, use the script-provided `title` and `expiresIn` fields when available.
- Format active alerts like:

```text
🚨 Active Alerts

1. BTC above 74,150 — 24m left
2. new Binance launchpool — active
```

- If there is exactly one alert, still keep the numbered layout.
- On delete, return the script message as-is.
- If `delete-match` returns multiple matches, ask a short follow-up or show the matching numbered choices.
- If there are no active alerts, reply: `You have no active alerts right now.`
- For duplicate/create-limit errors, return the script error as-is.
