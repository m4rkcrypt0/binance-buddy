# Skills Catalog

## Market, news, and price tools

- **binance-price-checker** — check live Binance spot prices for USDT pairs
- **binance-historical-price** — look up historical daily prices
- **binance-market-overview** — overall crypto market mood and metrics
- **binance-movers** — top gainers and losers
- **binance-announcements** — recent Binance announcements
- **campaign-generator** — Binance campaigns, launchpool, and promotion updates
- **market-analysis** — analysis for one Binance pair

## Portfolio and account tools

- **binance-portfolio** — portfolio dashboard across wallets
- **asset-history** — deposit and withdrawal history
- **reward-history** — reward/dividend history
- **portfolio-health-check** — concentration, stablecoin, futures, dust, and structure checks
- **portfolio-advisor** — action-oriented portfolio guidance
- **portfolio-opportunity-scanner** — scan holdings for assets worth attention
- **correlation-alpha-matrix** — BTC correlation view for portfolio assets

## Automation tools

- **alert-manager** — short-lived price alerts and Binance news/campaign alerts
- **schedule-manager** — recurring schedules backed by OpenClaw cron
- **square-post** — create, refine, save, and publish Binance Square posts

## Packaged builds

This project also includes packaged builds in `dist/`:

- `dist/alert-manager.skill`
- `dist/asset-history.skill`
- `dist/binance-announcements.skill`
- `dist/binance-historical-price.skill`
- `dist/binance-market-overview.skill`
- `dist/binance-movers.skill`
- `dist/binance-portfolio.skill`
- `dist/binance-price-checker.skill`
- `dist/campaign-generator.skill`
- `dist/correlation-alpha-matrix.skill`
- `dist/market-analysis.skill`
- `dist/portfolio-advisor.skill`
- `dist/portfolio-health-check.skill`
- `dist/portfolio-opportunity-scanner.skill`
- `dist/reward-history.skill`
- `dist/schedule-manager.skill`
- `dist/square-post.skill`

## Best publishing format

For GitHub, the best default is:
- publish the source skills in `skills/`
- keep `dist/` as an optional convenience layer
