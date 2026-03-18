---
name: portfolio-health-check
description: Review portfolio structure using helper-returned health metrics. Use when the user asks for a portfolio health check, wants a diagnostic read on concentration, stablecoin share, futures share, earn share, or dust.
---

# Portfolio Health Check

## Workflow
1. Run `scripts/fetch_health_check.py`.
2. Read the returned JSON.
3. Use the metrics to decide what is healthy, risky, or uneven.
4. Write the final explanation yourself.

## Rules
- Helper returns metrics only.
- You handle interpretation, prioritization, and final wording.
- Focus on structure: concentration, stablecoin reserve, futures share, earn share, and dust.
- Keep the final explanation concise and natural.

## Helper output
Returns:
- total value
- top asset and top asset share
- top 3 concentration
- stablecoin share
- futures share
- earn share
- dust count
