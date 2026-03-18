---
name: binance-price-checker
description: Check Binance spot prices for USDT pairs and format the reply for chat. Use when the user asks for current crypto prices on Binance spot, including prompts like "btc", "eth price please", "what is sol now", "btc xrp eth", "/price btc", "/price btc eth sol", coin names like bitcoin or ethereum, or symbols like `btcusdt`. Infer USDT pairs by default, dedupe duplicates, support common aliases, handle up to 10 symbols, show `❌ SYMBOL not found` for unknown assets, and return clean user-facing fallback messages when Binance is unavailable or rate-limited.
---

# Binance Price Checker

Fetch Binance spot 24h ticker data for up to 10 coins and return one formatted block per symbol.

## Workflow

1. Extract coin tickers from the user message.
2. Normalize each ticker to uppercase and infer the `USDT` pair.
3. Dedupe repeated symbols and keep only the first 10 unique coins.
4. Run `scripts/fetch_prices.py` with the extracted symbols.
5. Return the script output as-is unless the user asks for a different format.

## Rules

- Support `USDT` pairs only.
- Accept plain coin symbols or mixed text such as `btc`, `eth price please`, `what is sol now`, `/price btc`, `/price btc eth sol`, `bitcoin ethereum ripple`, `btcusdt`, or `btc xrp eth sol`.
- Support common aliases such as bitcoin, ethereum, ripple, solana, dogecoin, shiba inu, polygon, matic, avalanche, chainlink, litecoin, cardano, tron, and toncoin.
- Show one full block per symbol, separated by a blank line.
- Use quote volume in USDT for the volume line.
- If Binance does not return a symbol, show `❌ SYMBOL not found`.
- If the user provides more than 10 symbols, process only the first 10 unique symbols and mention that truncation happened.
- If the user provides no usable symbols, return a short usage hint like `Usage: /price btc eth sol`.
- If Binance is unavailable, rate-limited, or returns an HTTP error, return a short user-friendly fallback message instead of a raw stack trace or transport error.

## Command

Run:

```bash
./scripts/fetch_prices.py btc eth sol
```

The script handles parsing, deduplication, Binance API calls, and final formatting.

## Output format

Return blocks in this shape:

```text
💰 BTC

💵 $83,261.40
📈 +2.35% (24h)
🔼 High: $84,100.00
🔽 Low: $81,900.00
⏭️ Vol: $1,433,303,829.00
```

Keep the symbol header, price, 24h change, high, low, and volume lines in that order. Format prices with smart decimals for low-priced assets and show volume as a whole-number USDT amount.
