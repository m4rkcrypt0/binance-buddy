---
name: binance-historical-price
description: Look up historical Binance spot prices for USDT pairs using daily klines. Use when the user asks for the price of a coin on a past date, such as "show me the price of eth on march 13", "btc price yesterday", "what was sol on 2026-03-01", or "/price-history eth 2026-03-13". Support common aliases, infer USDT pairs, return a daily OHLCV summary, and handle up to 5 unique symbols in one request.
---

# Binance Historical Price

Fetch Binance spot daily kline data for up to 5 coins and return one historical OHLCV block per symbol.

## Workflow

1. Extract the requested date from the user message.
2. Extract coin tickers from the same message.
3. Normalize each ticker to uppercase and infer the `USDT` pair.
4. Dedupe repeated symbols and keep only the first 5 unique coins.
5. Run `scripts/fetch_historical_prices.py` with the raw user query.
6. Return the script output as-is unless the user asks for a different format.

## Rules

- Support Binance spot `USDT` pairs only.
- Support historical daily lookups only in v1.
- Accept date phrases like `2026-03-13`, `march 13`, `13 march`, `yesterday`, and `today`.
- Accept prompts like `show me the price of eth on march 13`, `btc price yesterday`, `what was sol on 2026-03-01`, or `/price-history eth 2026-03-13`.
- Support common aliases such as bitcoin, ethereum, ripple, solana, dogecoin, shiba inu, polygon, avalanche, chainlink, litecoin, cardano, tron, and toncoin.
- Return one block per symbol with close, open, high, low, and quote volume.
- If a symbol is unknown, show `❌ SYMBOL not found`.
- If the user provides more than 5 unique symbols, process only the first 5 and mention truncation.
- If the user omits a date, ask for one with a short helpful message.
- If Binance is unavailable or rate-limited, return a short user-friendly fallback message.

## Command

Run:

```bash
./scripts/fetch_historical_prices.py show me the price of eth on march 13
```

The script handles date parsing, symbol parsing, Binance API calls, and final formatting.

## Output format

Return blocks in this shape:

```text
🕰️ ETH — 2026-03-13

💵 Close: $2,245.18
🌅 Open: $2,221.50
🔼 High: $2,310.44
🔽 Low: $2,198.02
⏭️ Vol: $1,543,220,991
```

Keep the date header, close, open, high, low, and volume lines in that order.
