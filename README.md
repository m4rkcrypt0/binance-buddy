# Binance Buddy

**Binance Buddy** is a crypto-focused OpenClaw project built for Binance workflows, automation, portfolio tools, real-time updates, and market insights.

It was built to make crypto and Binance workflows more useful, more automated, and easier to access through chat.

## What Binance Buddy can do

### 1) Automation

- **Square Post** — generate Binance Square content, save drafts, post manually, or automate posting on your preferred schedule.
- **Campaign Generator** — get updates for new campaigns, launchpool opportunities, and promotions.
- **Announcements** — get updates for new Binance announcements, listings, delistings, and important updates.
- **CSV Export** — export portfolio balances and asset history into CSV files.
- **Smart Alerts** — get alerted when a token reaches your target price, and schedule recurring reports such as market overview, coin analysis, top movers, portfolio updates, and Square posting.

### 2) Portfolio Tools

- **Portfolio Dashboard** — view balances across Spot, Funding, Earn, and Futures in one place.
- **Portfolio Health Check** — review concentration, stablecoin share, futures exposure, Earn exposure, and dust levels.
- **Portfolio Advisor** — get action-oriented guidance based on your actual portfolio structure.
- **Portfolio Opportunity Scanner** — identify which holdings deserve attention right now.
- **Correlation Alpha Matrix** — see how portfolio assets behave relative to BTC.
- **Asset History** — review recent deposits and withdrawals.
- **Reward History** — check recent Binance reward history.

### 3) Market Intelligence

- **Market Analysis** — analyze individual tokens and get technical insights and trade-focused context.
- **Market Overview** — get a quick read on overall market mood, Fear & Greed sentiment, BTC and stablecoin dominance, and Binance BTC long/short ratio.
- **Price Checker** — check real-time crypto prices with support for up to 10 pairs.
- **Historical Price** — look up the price of a token on a specific date.
- **Top Movers** — see the top gainers and losers across Binance markets.

### 4) Real-Time Updates

- **Announcements** — get real-time Binance announcements, including listings, delistings, and important updates.
- **Campaign Generator** — track real-time campaigns, launchpool opportunities, and promotions.

## Included Skills

This repo includes:

- `alert-manager`
- `asset-history`
- `binance-announcements`
- `binance-historical-price`
- `binance-market-overview`
- `binance-movers`
- `binance-portfolio`
- `binance-price-checker`
- `campaign-generator`
- `correlation-alpha-matrix`
- `market-analysis`
- `portfolio-advisor`
- `portfolio-health-check`
- `portfolio-opportunity-scanner`
- `reward-history`
- `schedule-manager`
- `square-post`

## Project Structure

```text
binance-buddy/
├─ skills/               # source skill folders
├─ dist/                 # packaged .skill builds
├─ README.md
├─ INSTALL.md
├─ SETUP.md
├─ SKILLS.md
├─ GITHUB-PUBLISHING.md
├─ .env.example
└─ .gitignore
```

## Quick Start

### Option A — Use this repo as your OpenClaw workspace

1. Clone this repo
2. Copy `.env.example` to `.env`
3. Add your own Binance credentials
4. Point OpenClaw to this folder as the workspace
5. Start a new OpenClaw session

### Option B — Copy only the skills into an existing OpenClaw workspace

```bash
cp -R skills/* /path/to/your/openclaw/workspace/skills/
```

Then copy `.env.example` to `.env`, add your keys, and start a new OpenClaw session.

## Environment Setup

Create a local `.env` file:

```bash
cp .env.example .env
```

Supported variables:

```env
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_SECRET_KEY=your_binance_secret_key_here
BINANCE_SQUARE_OPENAPI_KEY=your_binance_square_openapi_key_here
```

## Packaged Builds

This repo also includes packaged builds in `dist/` for easier sharing:

- `dist/*.skill`

## Security Reminder

Do **not** commit:

- `.env`
- personal memory files
- runtime/session state
- local exports
- personal OpenClaw configs with secrets or tokens

## Documentation

- `INSTALL.md` — installation guide
- `SETUP.md` — environment and configuration guide
- `SKILLS.md` — skill catalog
- `GITHUB-PUBLISHING.md` — GitHub publishing notes
