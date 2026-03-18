# Setup Guide

## 1. Create a local environment file

From the project root:

```bash
cp .env.example .env
```

Then edit `.env` and add your own credentials.

## 2. Supported environment variables

```env
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_SECRET_KEY=your_binance_secret_key_here
BINANCE_SQUARE_OPENAPI_KEY=your_binance_square_openapi_key_here
```

## 3. What each key is for

### `BINANCE_API_KEY`
Used by private/account-based Binance features such as:
- portfolio
- asset history
- reward history
- portfolio diagnostics
- portfolio-derived analysis

### `BINANCE_SECRET_KEY`
Used together with `BINANCE_API_KEY` for signed private Binance requests.

### `BINANCE_SQUARE_OPENAPI_KEY`
Used for Binance Square publishing features.

## 4. Features that may work without private account keys

Some public-data skills can work without account credentials, depending on the endpoint and helper. These may include:
- announcements
- campaigns
- some market and price tools

## 5. Security rules

- Never commit `.env`
- Never put real keys inside docs
- Never publish personal `openclaw.json` files with tokens or secrets
- Rotate keys if you think they were exposed

## 6. Recommended local flow

```bash
cp .env.example .env
nano .env
```

After editing `.env`, start a new OpenClaw session or restart the relevant workflow.

## 7. Public repo rule

Safe to commit:
- `.env.example`

Do not commit:
- `.env`
