---
name: asset-history
description: Show recent Binance deposit and withdrawal history for the last 90 days. Use when the user asks for asset history, deposit history, withdrawal history, wants a recent dashboard of deposits and withdrawals, or wants a CSV/export file version of their asset history. Treat print and export as the same intent. Show up to 15 recent deposits and up to 15 recent withdrawals, with date only.
---

# Asset History

Fetch Binance deposit and withdrawal history and present a recent dashboard.

## Workflow

1. Detect whether the user wants:
   - normal asset-history view
   - export output
2. If the user wants the normal view, run `scripts/fetch_asset_history.py`.
3. If the user wants export output, treat `print` and `export` as the same request.
4. Run `scripts/fetch_asset_history.py --format csv --output /tmp/binance-asset-history.csv` for export requests.
5. Reply with a short caption plus a `MEDIA:/tmp/binance-asset-history.csv` line on its own line so OpenClaw sends the real `.csv` attachment.
6. Fall back to returning CSV content in chat only if attachment delivery fails or is clearly unsupported.
7. For normal view:
   - if the user asks for full asset history, show deposits and withdrawals
   - if the user asks for deposits only, show deposits only
   - if the user asks for withdrawals only, show withdrawals only

## Rules

- Reuse the same workspace `.env` with `BINANCE_API_KEY` and `BINANCE_SECRET_KEY`.
- Filter to the last 90 days.
- Show up to 15 recent deposits.
- Show up to 15 recent withdrawals.
- Use date only in `YYYY-MM-DD` format.
- Do not show time.
- Sort most recent to oldest.
- Treat `print my asset history` and `export my asset history` as the same export intent.
- For export requests, prefer sending a real `.csv` attachment via a `MEDIA:<path>` line in the reply.

## Commands

Normal JSON:

```bash
./scripts/fetch_asset_history.py
```

CSV to stdout:

```bash
./scripts/fetch_asset_history.py --format csv
```

CSV to file:

```bash
./scripts/fetch_asset_history.py --format csv --output /tmp/binance-asset-history.csv
```

## Output shape

### Chat view

```text
🧾 Asset History

🔸 Deposits

1. 2026-03-15 — WLD — 2.6

🔸 Withdrawals

1. 2026-03-04 — USDC — 49.98
2. 2026-02-19 — OM — 46.510839
```

### CSV columns

```text
recordType,generatedAt,days,date,asset,amount
```

- `recordType=deposit` rows are deposits
- `recordType=withdrawal` rows are withdrawals
