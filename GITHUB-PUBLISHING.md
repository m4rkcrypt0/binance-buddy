# GitHub Publishing Notes

This package is a public-safe export of the Binance Buddy OpenClaw project.

Included:
- skill source folders in `skills/`
- packaged `.skill` builds in `dist/`
- install and setup guides
- `.env.example`
- `.gitignore`

Not included:
- real `.env`
- personal memory files
- runtime/session state
- exports/logs
- personal OpenClaw config and tokens

## Simple GitHub flow

1. Create a new GitHub repo
2. Upload the contents of this folder
3. Review the files once before the first commit
4. After cloning locally, copy `.env.example` to `.env`

## Suggested first Git commands

```bash
git init
git add .
git commit -m "Initial public release of Binance Buddy"
git branch -M main
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```

## One-line install note

A true one-line native install is best when the skills are published to ClawHub, for example:

```bash
clawhub install <skill-slug>
```

For a GitHub-only release, the docs in `INSTALL.md` explain the fastest setup path.
