---
name: binance-movers
description: Show Binance top gainers or top losers for Spot and Futures using 24h percentage change data. Use when the user asks for top gainers, top losers, market movers, gainers on spot, losers on futures, or similar requests. Support USDT pairs only, filter to actively tradable symbols, return top 5 for both markets together, and return top 10 when the user asks for only Spot or only Futures.
---

# Binance Movers

Fetch Binance Spot and Futures 24h ticker data, rank symbols by 24h percentage change, and format the top gainers or losers for chat.

## Workflow

1. Detect whether the user wants gainers or losers.
2. Detect whether the user wants Spot, Futures, or both markets.
3. Fetch Spot and Futures exchange metadata and keep only actively tradable `USDT` pairs.
4. Fetch Spot and Futures 24h ticker data.
5. Sort by `priceChangePercent`.
6. Return top 5 each when showing both markets, or top 10 when showing only one market.

## Rules

- Support `USDT` pairs only.
- Exclude inactive, suspended, or non-tradable symbols by filtering against exchange metadata.
- Accept prompts like `show me the top gainers`, `show me the top losers`, `top gainers on spot`, `top losers on futures`, or `market movers` when gainers/losers is explicit.
- If the user asks for both markets or does not specify a market, show Spot and Futures together with top 5 each.
- If the user asks for only Spot or only Futures, show top 10 for that market.
- Use numbered lists: `1.` through `5.` or `10.` instead of bullet points.
- If the user does not specify gainers or losers, ask them to choose one.
- If Binance is unavailable or rate-limited, return a short user-friendly fallback message.

## Command

Run:

```bash
./scripts/fetch_movers.py "show me the top gainers on spot"
```

The script handles parsing, Binance API calls, filtering, sorting, and formatting.
