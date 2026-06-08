---
layout: default
title: Runner status dashboard proposal
permalink: /docs/runner-status-dashboard/
---

# Runner status dashboard proposal

This proposal defines a safe status dashboard for OpenClaw runner calls without exposing private execution records. The dashboard should show enough public progress for project review while keeping operational details local or behind a private network.

## Goals

- Show whether PM, Development, and Testing runner calls are planned, active, completed, stalled, or failed.
- Link public work back to GitHub issues, PRs, and published artifacts.
- Avoid repeating the failure mode where Telegram says a work cycle is active without durable runner evidence.
- Keep prompts, transcripts, shell commands, local paths, secrets, and detailed recovery notes out of public GitHub Pages output.

## Public GitHub Pages dashboard

The public dashboard may live on GitHub Pages as a sanitized status view. It should be generated only from a scrubbed export, not directly from raw `.codex-runs` JSON.

Allowed public fields:

- `run_id`: stable run identifier, with no local path content.
- `role`: PM, Development, Testing, Main, or Watchdog.
- `target`: public GitHub issue or PR reference.
- `state`: planned, triggered, started, completed, stalled, failed, cancelled.
- `artifact`: public issue, PR, report, release, or Pages link.
- `triggered_date`, `started_date`, `completed_date`: coarse timestamps, rounded to date or minute precision.
- `failure_category`: generic category such as startup_stall, heartbeat_stale, command_failed, ci_failed, missing_evidence, or policy_blocked.
- `public_summary`: short sanitized status sentence.

Public display rules:

- Do not expose raw `.codex-runs` records.
- Do not expose transcript paths, prompts, shell commands, command arguments, environment variables, local filesystem paths, secrets, or full alert strings.
- Do not expose detailed `failure_reason` values when they include implementation details; map them to `failure_category` instead.
- Do not publish heartbeat internals beyond coarse status and most recent public state.
- Prefer issue or PR references over raw operational logs.

## Private local or Tailscale dashboard

A private dashboard can expose operational detail for Jeremy and obot when it is served only on the local machine or a trusted private network such as Tailscale.

Private-only fields:

- full `.codex-runs` JSON records;
- transcript paths and transcript contents;
- exact command argv and executor configuration;
- prompt text and prompt templates;
- detailed failure reasons and full alert strings;
- heartbeat intervals, deadlines, process ids, and watchdog internals;
- recovery notes, operator notes, and local remediation steps;
- local checkout paths and worktree paths.

Private dashboard controls:

- Bind to localhost by default.
- Require explicit operator action before exposing over Tailscale.
- Treat transcripts as sensitive even when the repo is public.
- Add a visible warning when viewing raw records.
- Keep write actions separate from read-only status views until they have their own approval gate.

## Export and scrub step

Any GitHub Pages publication must use an export step that reads raw runner records and writes a sanitized public dataset.

Recommended export flow:

1. Read `.codex-runs/*.json` locally.
2. Validate each record against the expected runner schema.
3. Drop private-only fields.
4. Convert detailed failure reasons to generic failure categories.
5. Round timestamps and remove local timezone/path clues.
6. Require public artifacts to be public GitHub or Hub links.
7. Write a separate generated file such as `assets/data/runner-status.public.json`.
8. Build the public dashboard from that generated file only.
9. Fail the export if forbidden keys or path-like values remain.

Minimum scrub denylist:

- `command`
- `transcript`
- `prompt_template`
- `recovery`
- `failure_reason`
- `alert`
- `emitted_alert`
- `pid`
- `heartbeat_interval_seconds`
- `deadline_at`
- local absolute paths
- environment variables

## Recommended implementation sequence

1. Add a read-only scrubber script that converts `.codex-runs` records into a public JSON export.
2. Add unit tests with synthetic records that include paths, commands, alerts, and prompt-like strings.
3. Add a static GitHub Pages dashboard that reads only the scrubbed public JSON.
4. Add a private local dashboard separately, with localhost default binding.
5. Only after read-only dashboards are stable, consider operator-approved actions such as rerun, mark failed, or open linked issue.

## Acceptance criteria

- Public dashboard never reads raw `.codex-runs` files.
- Public export contains only allowlisted fields.
- Scrubber fails when forbidden keys or local paths are present.
- Private dashboard is clearly labeled and not committed as a public data source.
- Documentation distinguishes public visibility from private operational visibility.
