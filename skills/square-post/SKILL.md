---
name: square-post
description: Generate, edit, discard, and publish Binance Square text posts, including random-topic drafts, rewrite requests, draft reuse, confirmed posting, and scheduled Square automation runs. Use when the user asks to generate a Square post, draft a Binance Square post, write something interesting for Square, edit a Square draft, delete a draft, post the current draft, or automate/prepare a future Square posting flow. Keep the agent responsible for writing the post text; use bundled scripts only for deterministic state tracking, cooldown/quota enforcement, dry-run safety checks, recent-topic memory, and final publishing.
---

# Square Post

Write Binance Square posts in chat, keep draft state locally, and publish only after explicit user confirmation unless the user later asks for automation.

## Core behavior

- Let the agent write the post.
- If the user gives a topic, follow it.
- If the user gives no topic, choose a random interesting crypto-native angle.
- Default to about 500 characters unless the user asks otherwise.
- Keep drafts engaging, scroll-stopping, and natural rather than generic or corporate.
- Use emojis naturally.
- End with relevant hashtags.
- Keep hard cap at 1900 characters.

## Manual workflow

1. When the user asks for a Square post, generate a draft in chat.
2. Save the latest draft with `scripts/square_state.py save-draft`.
3. After generating a draft, offer short actions:
   - `post`
   - `edit`
   - `regenerate`
   - `delete`
4. If the user asks to edit or regenerate, rewrite the draft, then overwrite the saved draft.
5. If the user asks to delete, clear the saved draft only.
6. If the user says `post` or `post it`, load the current saved draft first. If none exists, ask them to generate or provide one.
7. Before any publish, check deterministic local publish eligibility.
8. Publish only after explicit confirmation.
9. After a successful publish, clear the current draft and log the publish event.

## Scheduled automation workflow

Use this when a cron-triggered run or scheduled message explicitly asks for Square automation.

1. Treat the schedule itself as the user's prior authorization for that automated run.
2. Before choosing a random topic, inspect recent topic memory with `scripts/square_state.py recent-topics`.
3. If no explicit user topic was provided, read `references/random-topics.md` and choose a topic angle that is not in the recent-topic list when possible.
4. Generate one post using the requested topic, or a rotated random crypto-native topic if none is provided.
5. Save the generated text with `scripts/square_state.py save-draft --topic 'CHOSEN_TOPIC'`.
6. Publish through `scripts/publish_saved_draft.py`, not by calling the raw publisher directly.
7. If publish is blocked by cooldown or quota, return the block reason clearly.
8. If publish succeeds, return the Square post URL clearly.
9. Keep the same writing quality bar as manual mode.

## Writing guidance

- Prefer a strong opening line or hook.
- Make the post feel like a real Binance Square post, not a template.
- Keep it concise, punchy, and interesting.
- Avoid repetitive filler, generic engagement bait, or too many emojis.
- Use hashtags that match the actual topic.
- If the user asks for a tone or goal, follow it.
- For random automation runs, vary both the topic and the framing so consecutive posts do not feel like rewrites of each other.

## State handling

Use `scripts/square_state.py` for lightweight local state.

Supported commands:

```bash
./scripts/square_state.py get-draft
./scripts/square_state.py save-draft --text 'POST_TEXT' [--topic 'TOPIC']
./scripts/square_state.py clear-draft
./scripts/square_state.py log-publish --text 'POST_TEXT' [--topic 'TOPIC'] [--post-id '123'] [--post-url 'https://...']
./scripts/square_state.py can-publish
./scripts/square_state.py recent [--limit 5]
./scripts/square_state.py recent-topics [--limit 5]
./scripts/square_state.py status
```

Use state for:
- current draft text
- optional topic metadata
- last publish timestamp
- rolling publish history
- recent published topic memory
- deterministic cooldown and quota status

Current deterministic limits:
- minimum interval between posts: 15 minutes
- daily limit: 100 posts in the last 24 hours

## Topic rotation

For random Square posts, read `references/random-topics.md`.

Use it to:
- rotate across topic buckets
- avoid recent repeated topics
- keep automation fresh without switching to rigid static templates

If the user explicitly gives a topic, do not override it with the topic pool.

## Publishing

For direct raw publishing, use:

```bash
printf '%s' 'FINAL_POST_TEXT' | ./scripts/publish_square_post.py
```

For direct raw dry-run testing, use:

```bash
printf '%s' 'FINAL_POST_TEXT' | ./scripts/publish_square_post.py --dry-run
```

For normal skill-driven publishing of the currently saved draft, prefer:

```bash
./scripts/publish_saved_draft.py
```

For full local dry-run of the saved-draft flow, use:

```bash
./scripts/publish_saved_draft.py --dry-run
```

The saved-draft publish flow should:
- load the saved draft
- block publish if cooldown/quota rules fail
- support a dry-run path that does not call the live API and does not mutate publish history
- call the Square API publisher only when not in dry-run mode
- log the publish locally
- clear the current draft after success

On success, return the Binance Square post URL clearly.
On failure, summarize the API error or local block reason cleanly.
On dry-run success, clearly say that no live post was created.

## Scheduling

When the user asks for recurring Square posting, use the `schedule-manager` skill and map it to the `square-post` schedule type.

Examples:

```bash
./scripts/manage_schedules.py create --type square-post --rule interval --minutes 15 --chat-id telegram:6935201375 --channel telegram --target 6935201375
./scripts/manage_schedules.py create --type square-post --topic 'BTC market psychology' --rule daily --time 09:00 --chat-id telegram:6935201375 --channel telegram --target 6935201375
```

Scheduled Square runs should still go through the same save-draft + publish-saved-draft path.

## Safety and automation guardrails

- Do not publish anything unless the user explicitly confirms posting, unless they later ask for automation that changes this rule.
- Treat `delete` as deleting the local draft only, not a published Square post.
- Load the Square API key from `/home/markvincentmalacad/.openclaw/workspace/.env` using `BINANCE_SQUARE_OPENAPI_KEY`.
- Never reveal the full API key.
- Keep the agent as the default writer for interesting posts; do not replace normal writing with static templates unless the user asks.
- Keep scheduling, cooldown, quota tracking, publish history, and recent-topic memory deterministic and local.
- Before testing publish-path changes, prefer dry-run first.
- For automation, prefer wrapping scheduled runs around the same saved-draft / publish-status / publish-saved-draft path instead of creating a second separate publisher.

## Output style

### Draft response

```text
🚀 SQUARE POST DRAFT

<generated post text>

Options:
- post
- edit
- regenerate
- delete
```

### Successful publish

```text
✅ Posted to Binance Square

🔗 https://www.binance.com/square/post/1234567890
```

### Dry-run success

```text
🧪 Dry run successful

No live Square post was created.
```

### Blocked publish

```text
⚠️ Unable to publish yet

Reason: cooldown or daily quota reached
```
