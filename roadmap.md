---
layout: default
title: Roadmap
---

# Roadmap

Public roadmap view for obot-claw Requirements and linked Tasks.

## Issue conventions

- **Requirement issues** live in `obot-claw/obot-claw.github.io`.
- **Task issues** live in the repo closest to the implementation work.
- Every Requirement should include `# Overview`, `# Design`, and `# Implementation plan` sections.
- Every Requirement should have one `project:P###` label.
- Requirement implementation plans should link task sub-issues or PRs.

## Active requirements

### P007 — Refactor development framework for increased autonomy

- Requirement: https://github.com/obot-claw/obot-claw.github.io/issues/3
- Status: planned
- Tasks:
  - https://github.com/obot-claw/obot-claw.github.io/issues/1
  - https://github.com/obot-claw/obot-claw.github.io/issues/2

### P004 — Autonomous SafetyGraphics renderer modernization standard

- Requirement: https://github.com/obot-claw/obot-claw.github.io/issues/4
- Status: planned
- Tasks / evidence:
  - https://github.com/obot-claw/safety-agent/issues/5
  - https://github.com/obot-claw/safety-agent/issues/6
  - https://github.com/obot-claw/safety-agent/pull/4
  - https://github.com/obot-claw/safety-histogram/pull/1
  - https://github.com/obot-claw/safety-histogram/pull/2

## Labels

- `type:requirement` — high-level requirement.
- `type:task` — implementation task linked from a requirement.
- `project:P004`, `project:P007` — project rollup labels.
- `status:planned`, `status:in-progress`, `status:blocked`, `status:ready-review` — working status labels.

## Next update

The next iteration should automate this page from GitHub Issues rather than maintaining it manually.
