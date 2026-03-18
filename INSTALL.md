# Install Guide

This guide shows the cleanest ways to use Binance Buddy with OpenClaw.

## Prerequisite

Install OpenClaw first.

Official docs:
- https://docs.openclaw.ai

## Option 1 — Recommended: use this repo as your OpenClaw workspace

### 1. Clone the repo

```bash
git clone <YOUR_GITHUB_REPO_URL> binance-buddy
cd binance-buddy
```

### 2. Create your local environment file

```bash
cp .env.example .env
```

Then add your own keys.

### 3. Point OpenClaw to this workspace

Example `openclaw.json` shape:

```json
{
  "agents": {
    "defaults": {
      "workspace": "/absolute/path/to/binance-buddy"
    }
  }
}
```

OpenClaw will then load skills from:

```text
/absolute/path/to/binance-buddy/skills
```

### 4. Start a new OpenClaw session

This lets OpenClaw pick up the workspace skills cleanly.

## Option 2 — Copy the skills into an existing OpenClaw workspace

If you already have a workspace:

```bash
cp -R skills/* /path/to/your/openclaw/workspace/skills/
```

Then copy `.env.example` to `.env`, add your keys, and start a new OpenClaw session.

## Packaged builds

The `dist/` folder contains packaged `.skill` builds.

These are useful for:
- release artifacts
- sharing packaged builds
- distribution alongside the source

But the main source-of-truth remains:

```text
skills/
```

## Can this be one-line install?

### GitHub-only version
Not truly one-click yet, but the fastest setup is usually:

```bash
git clone <YOUR_GITHUB_REPO_URL> binance-buddy && cd binance-buddy && cp .env.example .env
```

You would still need to:
- add your keys
- point OpenClaw to the workspace or copy the skills
- start a new session

### ClawHub version
If you later publish the skills to ClawHub, you can offer a cleaner one-line install such as:

```bash
clawhub install <skill-slug>
```

That is the best native one-line install experience for OpenClaw skills.
