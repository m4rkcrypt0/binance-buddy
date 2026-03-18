---
name: market-analysis
description: Analyze one Binance USDT trading pair with structured technical analysis and entry framing. Use when the user asks for TA on a coin, wants an asset analysis, asks why a coin is pumping or dumping, or asks for a possible entry framework such as 'give me TA for BTC', 'analyze ETH', 'why ADA dump', or 'right entry for SOL'.
---

# Market Analysis

Analyze one market at a time and adapt the final output to the user's intent.

## Workflow

1. Run `scripts/fetch_market_analyzer.py "<user request>"`.
2. Read the returned JSON.
3. Use the returned `mode` to shape the final answer:
   - `analysis`
   - `entry`
   - `move-explainer`
4. Keep the final wording dynamic and based on the helper payload.
5. Use light emojis for section titles, not clutter.
6. End with: `⚠️ This is not financial advice. Always manage risk and do your own research.`

## Rules

- Support `1h`, `4h`, and `1d` cleanly in v1; `4h` is the default when the user does not specify a timeframe.
- Treat the helper output as structured market data, not final wording.
- Do not put canned explanation paragraphs in the Python helper.
- Keep entry framing scenario-based rather than giving direct buy commands.
- Be honest when signals are mixed or unclear.

## Command

Run:

```bash
./scripts/fetch_market_analyzer.py "analyze BTC"
```

## Output family

Use one visual family with small mode adjustments.

### Analysis mode

```text
📊 BTC Market Analyzer

💵 Price: $...
🕒 Timeframe: 4H

📈 Trend
...

⚡ Momentum
...

🧱 Key levels
- Support: ...
- Resistance: ...

📝 Takeaway
...

⚠️ This is not financial advice. Always manage risk and do your own research.
```

### Entry mode

```text
🎯 SOL Entry Analyzer

💵 Price: $...
🕒 Timeframe: 4H

📈 Structure
...

🧱 Key levels
- Support: ...
- Resistance: ...

🎯 Entry view
...

📝 Takeaway
...

⚠️ This is not financial advice. Always manage risk and do your own research.
```

### Move-explainer mode

```text
📉 ADA Move Analyzer

💵 Price: $...
🕒 Timeframe: 4H

📉 Move summary
...

🔍 Likely reason
...

🧱 Levels to watch
- Support: ...
- Resistance: ...

📝 Takeaway
...

⚠️ This is not financial advice. Always manage risk and do your own research.
```
