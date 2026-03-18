---
name: binance-portfolio
description: Show a Binance portfolio dashboard combining Spot, Funding, Simple Earn, and USDⓈ-M Futures balances, valued in USDT. Use when the user asks for their Binance portfolio, balances, wallet overview, portfolio dashboard, total holdings, or wants a CSV/export file version of their portfolio. Treat print and export as the same intent. Show wallet breakdown and top assets sorted from highest to lowest.
---

# Binance Portfolio

Fetch balances across Binance wallet types and present a compact portfolio dashboard.

## Workflow

1. Detect whether the user wants:
   - normal portfolio view
   - export output
2. If the user wants the normal portfolio view, run `scripts/fetch_portfolio.py`.
3. If the user wants export output, treat `print` and `export` as the same request.
4. Run `scripts/fetch_portfolio.py --format csv --output /tmp/binance-portfolio.csv` for export requests.
5. Reply with a short caption plus a `MEDIA:/tmp/binance-portfolio.csv` line on its own line so OpenClaw sends the real `.csv` attachment.
6. Fall back to returning CSV content in chat only if attachment delivery fails or is clearly unsupported.
7. For normal view, present:
   - total portfolio value in USDT
   - asset count
   - wallet breakdown
   - top visible assets
8. Keep wallet rows even when the value is `0.00`.
9. Sort assets from highest to lowest by USDT value.

## Rules

- Combine Spot, Funding, Simple Earn, and USDⓈ-M Futures.
- Convert portfolio value into USDT.
- On asset lines, show the token amount, not the USDT value.
- Asset percentages are based on the entire portfolio total.
- Show only the top 20 visible assets.
- Hide assets with value below `$0.01`.
- Keep wallet rows even if the wallet value is zero.
- Use the same workspace `.env` for `BINANCE_API_KEY` and `BINANCE_SECRET_KEY`.
- Do not reveal full API credentials.
- Treat `print my portfolio` and `export my portfolio` as the same export intent.
- Treat `portfolio csv` or explicit CSV wording as the same export intent.
- For CSV output, return wallet rows and asset rows in one flat table with `recordType` so the export stays simple.

## Commands

Normal portfolio JSON:

```bash
./scripts/fetch_portfolio.py
```

CSV to stdout:

```bash
./scripts/fetch_portfolio.py --format csv
```

CSV to file:

```bash
./scripts/fetch_portfolio.py --format csv --output /tmp/binance-portfolio.csv
```

## Output shape

### Normal chat view

```text
📊 Binance Portfolio

Total: 1.16 USDT
Assets: 3

📙 Wallets

• Spot: 1.14 (98.0%)
• Funding: 0.00 (0.0%)
• Earn: 0.02 (2.0%)
• Futures: 0.00 (0.0%)

🪙 Assets

1. WLD — 0.94 (80.8%)
2. USDC — 0.20 (17.2%)
3. BNB — 0.02 (2.0%)
```

### CSV columns

```text
recordType,generatedAt,portfolioTotalUsdt,name,asset,amount,valueUsdt,percent
```

- `recordType=wallet` rows use `name`
- `recordType=asset` rows use `asset` and `amount`

- `recordType=asset` rows use `asset` and `amount`
