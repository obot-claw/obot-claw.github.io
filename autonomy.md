---
layout: default
title: Autonomy
---

# Autonomous Work Blocks

This page defines how obot should make daily evidence-backed progress on approved `obot-claw` projects when Jeremy is inactive.

## Default schedule

- Run once daily in an isolated OpenClaw session.
- Default duration: 60-90 minutes.
- Default target: the highest-priority open task linked from an active Requirement on the roadmap.
- First pilot target: P004 Safety Histogram evidence cleanup, https://github.com/obot-claw/safety-agent/issues/6.

## Authority levels

- **L1**: local planning, memory, skills, private notes.
- **L2**: docs, requirements, tests, GHA setup, evidence summaries, draft PRs.
- **L3**: implementation PRs inside `obot-claw` repos with tests/demos/evidence.
- **L4**: routine Hub diary/report updates with transparent notes.

Default daily block authority: **L2**. L3 is allowed only when the parent Requirement already approves implementation scope. Merges remain review-gated unless Jeremy explicitly approves merge.

## Task selection

1. Read the Roadmap: https://obot-claw.github.io/roadmap/
2. Prefer open tasks with assignee `@obot-claw`, parent Requirement, active milestone, and no metadata gaps.
3. Prefer tasks under P004 and P007 until those Requirements stabilize.
4. Do not start keynote/P006 work until Jeremy provides the detailed outline.

## Required supervision

Every autonomous block must be registered in the durable work-session ledger before it is described as active. Use `scripts/work_session.py` to record the target, session reference, checkpoint, liveness method, evidence requirement, and recovery plan. If liveness cannot be confirmed by the checkpoint, mark the block stalled/failed instead of reporting it as running.

See [Work-session supervision](/docs/work-session-supervision/) for the state model and helper commands.

## Required output

Every autonomous block must produce one of:

- a linked PR with tests/docs/evidence,
- an issue comment with concrete findings and next actions,
- a blocker report with exact failing command/log/link,
- or a no-op report explaining why no safe progress was possible.

## Stop conditions

Stop and report instead of pushing further if requirements are ambiguous, tests fail without a clear fix, work requires non-`obot-claw` writes, private data could be exposed, credentials/tooling are blocked, or work exceeds the active Requirement scope.

## Daily summary

Each block should end with a short Telegram update including task, PR/evidence links, tests/checks, blockers, and next step.
