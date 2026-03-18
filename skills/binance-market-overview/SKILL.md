---
name: binance-market-overview
description: Build a crypto market overview using global market metrics, fear and greed data, and Binance BTC long/short ratio. Use when the user asks for market overview, market sentiment, overall crypto market status, or a daily market summary. Fetch structured data with the bundled script, then write the final market mood summary naturally from the returned metrics and signals instead of using a static hardcoded sentence.
---

# Binance Market Overview

Fetch structured market-wide metrics, then write a natural summary grounded in the numbers.

## Workflow

1. Run `scripts/fetch_market_overview.py`.
2. Read the returned JSON.
3. Present the headline metrics in this order:
   - market cap
   - 24h volume
   - BTC dominance
   - stablecoin dominance
   - fear and greed
   - BTC long/short ratio
4. Use the returned `signals` plus the raw numbers to write a short market mood summary in natural language.
5. Keep the summary grounded in the numbers and vary the wording naturally across repeated use.

## Rules

- Use the script output as the factual source of truth.
- Do not invent metrics the script did not return.
- Keep the market mood summary short, natural, and non-static.
- The final summary should be agent-written, not copied from a Python template.
- Mention the dominant sentiment, liquidity posture, BTC leadership, and positioning bias when relevant.
- If a metric source is unavailable, say so briefly instead of fabricating a value.

## Command

Run:

```bash
./scripts/fetch_market_overview.py
```

The script returns structured JSON for the agent to turn into the final overview.

## Output shape

```text
🌍 MARKET OVERVIEW 🧭

💰 Market Cap: $2.53T
📊 24h Volume: $116.2B
👑 BTC Dominance: 57.0%
💵 Stablecoin Dom: 10.4%
🔥 Fear & Greed: 15 (Extreme Fear)
⚖️ Long/Short Ratio (BTC): Long: 0.50 | Short: 0.51

💡 MARKET MOOD: Write this naturally from the current numbers and derived signals.
```
