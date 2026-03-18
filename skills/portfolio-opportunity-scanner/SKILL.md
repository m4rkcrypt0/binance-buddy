---
name: portfolio-opportunity-scanner
description: Scan the user's actual Binance portfolio holdings for the assets that deserve attention now. Use when the user asks what in their portfolio looks interesting, which holdings are strongest or weakest, what deserves attention today, or wants a portfolio-aware opportunity scan instead of generic market movers.
---

# Portfolio Opportunity Scanner

Scan current held assets and surface the most relevant portfolio-aware opportunities.

## Workflow

1. Run `scripts/fetch_portfolio_opportunity_scanner.py`.
2. Read the returned JSON.
3. Highlight the top attention asset first.
4. Call out the best strength name and best pullback watch when present.
5. Explain whether opportunity breadth is narrow, mixed, or broad.
6. Keep the explanation grounded in both market movement and portfolio importance.

## Rules

- Reuse the same workspace `.env` with `BINANCE_API_KEY` and `BINANCE_SECRET_KEY`.
- Use the combined portfolio across Spot, Funding, Simple Earn, and USDⓈ-M Futures.
- Treat stablecoins as reserve capital, not directional opportunities.
- Focus on assets that matter at portfolio level; ignore dust and tiny balances.
- Let the helper score and classify holdings, and let the agent write the final explanation naturally.
- Do not turn the scan into direct trade instructions.

## Command

Run:

```bash
./scripts/fetch_portfolio_opportunity_scanner.py
```

## Output shape

```text
🎯 Portfolio Opportunity Scanner

🔥 Best strength: WLD
WLD is the clearest active strength name in the portfolio right now.

🛒 Best pullback watch: BNB
BNB is weaker over the recent window, but its portfolio weight is small, so the opportunity matters less at portfolio level.

👀 Highest attention asset: WLD
If only one non-stablecoin holding deserves attention right now, this is the one.

💵 Reserve capital: USDC
Most capital is still sitting defensively in stablecoins rather than spread across directional setups.

💡 Scanner takeaway
Write this naturally from the current rows and signals.
```
