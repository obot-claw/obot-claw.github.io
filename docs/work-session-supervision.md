---
layout: default
title: Work-session supervision
permalink: /docs/work-session-supervision/
---

# Work-session supervision

This document defines the durable supervision layer for PM, Development, Testing, cron, and subagent work sessions.

## Problem

A work cycle is not active just because a prompt was sent or a subagent id was returned. Recent failures showed that sessions can become unreachable (`not_found`) while the main session still describes them as running. That breaks status reliability.

## Contract

Every PM/Development/Testing cycle must have a ledger entry before it is called active.

Required fields:

- cycle name
- role: PM, Development, Testing, Main, Cron, or TaskFlow
- target issue/PR
- session reference: OpenClaw session id, cron id, TaskFlow id, or explicit `main-session`
- first checkpoint time
- liveness method
- recovery plan
- progress evidence: diff, commit, check, issue comment, report, or explicit blocker

## State model

- `planned`: ready but not started
- `active`: started and still within checkpoint, or has fresh evidence
- `stalled`: checkpoint passed without evidence, or liveness is not confirmed
- `failed`: unrecoverable or unsafe to continue
- `completed`: work finished with evidence
- `cancelled`: intentionally stopped

Do not report a cycle as active unless the ledger, reachable session status, or concrete evidence supports it.

## Helper

Use `scripts/work_session.py`:

```sh
python3 scripts/work_session.py start \
  --cycle "P007 session supervision" \
  --role Development \
  --target "obot-claw.github.io #25" \
  --session-ref main-session \
  --checkpoint "2026-06-06T21:00:00Z" \
  --liveness-method "main session + git diff + issue comment" \
  --recovery-plan "mark stalled, record blocker, restart from clean worktree"
```

Status:

```sh
python3 scripts/work_session.py status --open-only
```

Markdown report:

```sh
python3 scripts/work_session.py report
```

Smoke test:

```sh
python3 scripts/work_session.py self-test
```

## Runtime choice

Preferred runtime is OpenClaw-native sessions when available in the current context. If `sessions_spawn`/`sessions_yield` are unavailable or session lookup is unreliable, use a TaskFlow/cron-backed or main-session supervised fallback and record that choice in the ledger.

CLI fallback is not trusted when sandbox permissions block OpenClaw identity/session writes. In that case, record the failed command as evidence and continue with a bounded safe fallback.

## Recovery rule

If a session is `not_found`, unreachable, or silent past checkpoint:

1. mark it `stalled` or `failed` in the ledger;
2. record exact evidence or missing evidence;
3. post a concise issue comment when the work is public;
4. restart only from a clean worktree or explicitly take over in main session.

## Telegram rule

Telegram status messages should only summarize the ledger result. Put detailed status in the issue, report, or ledger output.

## Codex-first path

OpenClaw should supervise Codex-powered PM, Development, and Testing cycles rather than becoming a bespoke agent platform. See [Codex cycle contract](/docs/codex-cycle-contract/) for the role split, handoff fields, and prompt skeletons.

## Runtime sync

This public Hub contract must be mirrored into local OpenClaw runtime instructions before it is considered operational. The local runtime files are `AGENTS.md`, `HEARTBEAT.md`, and workspace `skills/`.
