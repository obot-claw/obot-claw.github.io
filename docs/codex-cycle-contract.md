---
layout: default
title: Codex cycle contract
permalink: /docs/codex-cycle-contract/
---

# Codex cycle contract

This contract defines how OpenClaw should supervise Codex-powered PM, Development, and Testing work cycles.

## Roles

- **OpenClaw main obot**: intake, Telegram, routing, work-session ledger, liveness checks, recovery, and concise status reporting.
- **Codex PM**: GitHub portfolio audit, Project / Requirement / Task issue maintenance, Human ToDo gate, and exact development handoff. PM must not implement feature code.
- **Codex Development**: branch/worktree or cloud-task implementation, tests, docs, demos, PR body, and evidence comments.
- **Codex Testing**: browser/GHA/static/visual evidence, failure reproduction, and blocker comments.

## Required handoff fields

Every Codex work cycle must declare:

- target issue or PR;
- repository and branch/worktree strategy;
- allowed files or modules;
- acceptance criteria;
- checks to run;
- evidence to produce;
- timeout/checkpoint;
- non-goals;
- recovery plan if the run stalls or disappears.

## Launch sequence

1. Select or create a GitHub Task issue.
2. Create a work-session ledger entry with `scripts/work_session.py start`.
3. Run Codex in the selected role using the handoff fields above.
4. Check liveness before reporting active status.
5. Update the ledger and linked issue/PR with evidence, blocker, stalled, failed, or completed status.

## Execution standards

- Use fresh clones/worktrees or Codex cloud tasks for Development.
- Keep all writes inside `obot-claw` unless Jeremy explicitly approves otherwise.
- Do not merge autonomously.
- Put detailed status in GitHub issues/PRs or reports; keep Telegram short.
- If the current context cannot expose reliable session/task status, use the PR #26 ledger as the source of truth until OpenClaw task/session visibility is repaired.

## PM prompt skeleton

```text
Role: Codex PM.
Target: <GitHub issue/requirement/project>.
Goal: audit GitHub portfolio state and produce/update issues plus a dev handoff.
Constraints: no feature-code edits; use Project / Requirement / Task structure; apply Human ToDo gate.
Evidence: issue comments, labels, linked tasks, handoff summary.
Stop if: GitHub state is ambiguous, private data is needed, or a human decision is truly required.
```

## Development prompt skeleton

```text
Role: Codex Development.
Target: <GitHub task issue>.
Repo: <repo>.
Branch/worktree: <fresh branch/worktree>.
Allowed writes: <paths/modules>.
Acceptance criteria: <criteria>.
Checks: <commands>.
Evidence: PR, test output, issue comment, screenshots/report if UI.
Stop if: dirty unrelated state, missing requirements, failing checks without bounded fix, or non-obot-claw write needed.
```
