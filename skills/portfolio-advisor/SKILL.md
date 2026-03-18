---
name: portfolio-advisor
description: Turn portfolio diagnostics into clear portfolio guidance. Use when the user asks for portfolio advice, portfolio review, what to improve in their portfolio, risk posture, cash posture, or wants an action-oriented interpretation of their Binance portfolio.
---

# Portfolio Advisor

Interpret portfolio structure and turn it into practical portfolio guidance.

## Workflow

1. Run `scripts/fetch_portfolio_advisor.py`.
2. Read the returned JSON.
3. Present the main issue and key postures clearly.
4. Write a short natural explanation grounded in the returned metrics and signals.
5. Keep the guidance practical and focused on portfolio structure, not price predictions.

## Rules

- Reuse the same workspace `.env` with `BINANCE_API_KEY` and `BINANCE_SECRET_KEY`.
- Base guidance on the whole portfolio.
- Focus on structural advice such as concentration, cash posture, futures exposure, yield usage, and dust.
- Do not give direct buy/sell instructions.
- Let the helper compute structured signals, and let the agent write the final explanation naturally.

## Command

Run:

```bash
./scripts/fetch_portfolio_advisor.py
```

The script returns structured JSON for the agent to explain.

## Output shape

```text
🧭 Portfolio Advisor

⚠️ Main issue: Concentration is high.
A large part of the portfolio is still clustered in a small number of holdings.

💵 Cash posture: Stablecoin reserve is high.
That gives flexibility and downside protection, but it also means part of the portfolio is sitting defensively.

📈 Risk posture: Futures exposure is aggressive.
Even with a defensive cash base, futures increase portfolio sensitivity and can raise short-term risk.

✅ Positive note:
Dust is low and part of the portfolio is productive through Earn.

💡 Advisor takeaway:
Write this naturally from the current metrics and signals.
```
