# Binance Buddy

Binance Buddy is a crypto-focused OpenClaw project built for Binance workflows, insights, automation, and content.

It includes skill packs for:

- live and historical price checks
- market analysis and market overview
- Binance announcements and campaign tracking
- portfolio dashboards and exports
- reward, deposit, and withdrawal history
- smart alerts and recurring schedules
- Binance Square drafting and automation

## What is inside

This public package is designed to be GitHub-ready and OpenClaw-friendly.

Included:
- `skills/` — source skill folders
- `dist/` — packaged `.skill` builds
- `INSTALL.md` — installation guide
- `SETUP.md` — environment and configuration guide
- `SKILLS.md` — skill catalog
- `.env.example` — safe placeholder environment file
- `.gitignore` — keeps secrets and runtime files out of Git

## Quick install

### Option A — Use this repo as your OpenClaw workspace

1. Clone this repo
2. Copy `.env.example` to `.env`
3. Add your own Binance keys
4. Point OpenClaw to this folder as the workspace
5. Start a new OpenClaw session

### Option B — Copy only the skills into an existing OpenClaw workspace

```bash
cp -R skills/* /path/to/your/openclaw/workspace/skills/
```

Then copy `.env.example` to `.env`, fill your keys, and start a new OpenClaw session.

## Is one-line install possible?

Yes — but it depends on how you publish the project.

### If you publish on GitHub only
The fastest install is still very simple, but it is usually a small clone/copy flow rather than a true one-click marketplace install.

### If you publish the skills to ClawHub
Then you can offer a much cleaner install flow such as:

```bash
clawhub install <skill-slug>
```

That is the closest thing to a one-line install for OpenClaw skills.

## Security reminder

Do **not** commit:
- `.env`
- personal memory files
- runtime/session state
- local exports
- personal OpenClaw configs with secrets or tokens

## Learn more

- `INSTALL.md`
- `SETUP.md`
- `SKILLS.md`
- `GITHUB-PUBLISHING.md`
