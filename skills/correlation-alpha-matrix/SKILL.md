---
name: correlation-alpha-matrix
description: Analyze portfolio behavior correlation against BTC over a 30-day window. Use when the user asks for correlation matrix, portfolio correlation, BTC linkage, diversification quality, or wants to understand whether held assets are behaving like BTC. Show up to the top 15 portfolio assets.
---

# Correlation Alpha Matrix

Measure how the portfolio’s top assets behave relative to BTC.

## Workflow

1. Run `scripts/fetch_correlation_matrix.py`.
2. Read the returned JSON.
3. Present the top held assets with BTC correlation values.
4. Present diagnostic signals such as BTC linkage, diversification quality, and stable reserve.
5. Write the final takeaway naturally from the returned signals.

## Rules

- Default reference is BTC.
- Default window is 30D.
- Show only the top 15 portfolio assets.
- Use the same workspace `.env` with `BINANCE_API_KEY` and `BINANCE_SECRET_KEY`.
- Let the helper compute the structured signals, but let the agent write the final takeaway naturally.

## Command

Run:

```bash
./scripts/fetch_correlation_matrix.py
```

The script returns structured JSON for the agent to format.

## Output shape

```text
🧠 Correlation Alpha Matrix

Reference: BTC
Window: 30D

1. WLD — Corr: 0.84
2. BNB — Corr: 0.79
3. USDC — Corr: 0.03

🚦Signals

- BTC linkage: High
- Diversification quality: Low
- Stable reserve: Strong

📑 Takeaway

Write this naturally from the current numbers and signals.
```
