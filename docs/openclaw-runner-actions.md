---
layout: default
title: OpenClaw runner actions contract
permalink: /docs/openclaw-runner-actions/
---

# OpenClaw runner actions contract

This contract defines the Phase 5 integration surface for exposing P009 runner status through OpenClaw and Telegram.

## Allowed actions

OpenClaw and Telegram may call only this wrapper:

```sh
python3 scripts/p009_runner_action.py <action>
```

Supported actions:

- `self-test`: run the built-in runner self-test, then create one persistent safe dry-run record.
- `status`: summarize local run records without mutating them.
- `check`: run the watchdog check without marking failures.
- `check-mark-failed`: run the watchdog check and mark triggered/stale records failed.

The wrapper does not expose the raw runner `run` subcommand and does not accept arbitrary command text from chat.

## Telegram summary fields

Telegram summaries should stay short and include only the fields relevant to the action:

- `run_id`
- `state`
- `heartbeat_at`
- `transcript`
- `exit_code`
- `records_checked`
- `newly_failed`
- alert strings only when the watchdog emits them

Do not include raw JSON records, prompt text, shell argv beyond the allowlisted wrapper action, local absolute paths, secrets, or full transcripts in Telegram.

## Safety rules

- Never forward arbitrary Telegram text into `--command`.
- Never expose `.codex-runs` records directly in public pages or Telegram.
- Keep transcript paths as local operator references only.
- Treat `check-mark-failed` as a write action against local run records.
- Prefer concise summaries; put detailed evidence in issues or PRs.

## Implementation note

If future implementation moves into an OpenClaw plugin or Paperclip control plane, keep this wrapper as the compatibility contract or replace it with an equivalent allowlisted command surface.
