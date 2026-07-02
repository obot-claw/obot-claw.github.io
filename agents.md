---
layout: default
title: Agent Overview
---

# Agent Overview

> 📦 **Archived (obot era).** This page describes the autonomous-agent setup retired in July 2026 and is kept for history. Current work lives on the [Roadmap](/roadmap/) and [Dashboard](/dashboard/); the story of the change is [Chapter 10](/reports/autonomous-agent-framework/chapter-10-claude-code-migration/).


This page summarizes the current OrangeBot working model: what exists today, what is still a proposed operating role, and how work should move from planning to implementation.

## Current status

<ul class="agent-status-list">
  <li><strong>Main obot / Orchestrator:</strong> active. Runs in Telegram/OpenClaw, handles intake, status, routing, safe bounded fixes, and recovery when worker sessions fail.</li>
  <li><strong>PM/Design cycle:</strong> operating role. Uses GitHub issues as durable memory, owns Project / Requirement / Task structure, Human ToDos, roadmap/Hub tracking, and development handoffs.</li>
  <li><strong>Development cycle:</strong> operating role. Owns implementation through PRs, evidence, checks, demos, and issue/PR updates.</li>
  <li><strong>Testing cycle:</strong> proposed/specialized role. Should own browser, GHA, Playwright, visual/regression, and evidence-hardening tasks when needed.</li>
</ul>

Today these roles are mostly prompt-scoped work sessions, not fully isolated permanent OpenClaw agents. The framework work below is intended to make them more reliable and auditable.

## Responsibilities

<div class="agent-grid">
  <section>
    <h2>Main obot</h2>
    <ul>
      <li>Intake Jeremy's requests and decide whether PM, Development, Testing, or direct bounded action is appropriate.</li>
      <li>Keep Telegram replies concise and plain-text safe.</li>
      <li>Verify work-session liveness before saying a cycle is active.</li>
      <li>Recover stalled work sessions and report failures plainly.</li>
    </ul>
  </section>

  <section>
    <h2>PM / Design</h2>
    <ul>
      <li>Run the portfolio PM audit before selecting development work.</li>
      <li>Maintain Project, Requirement, and Task issue structure.</li>
      <li>Keep Hub homepage, roadmap, reports, and Human ToDos aligned with GitHub issues.</li>
      <li>Apply the Human ToDo delegation gate before asking Jeremy for anything.</li>
      <li>Produce exact development handoffs with scope, evidence, checks, and non-goals.</li>
    </ul>
  </section>

  <section>
    <h2>Development</h2>
    <ul>
      <li>Implement through branches and PRs under <code>obot-claw</code>.</li>
      <li>Use clean worktrees or explicit branch strategy; do not overwrite dirty unrelated work.</li>
      <li>Run feasible checks and capture evidence.</li>
      <li>Update linked issues/PRs with concise status and blockers.</li>
      <li>Do not merge unless Jeremy explicitly approves.</li>
    </ul>
  </section>

  <section>
    <h2>Testing</h2>
    <ul>
      <li>Own browser and GHA evidence when feature work needs stronger validation.</li>
      <li>Document local Playwright/Chromium blockers separately from product readiness.</li>
      <li>Compare demos, console output, accessibility, and visual behavior when UI output is involved.</li>
      <li>Escalate missing test infrastructure as Tasks, not vague Human ToDos.</li>
    </ul>
  </section>
</div>

## Human ToDo delegation gate

Before creating a 🙋 Human ToDo, PM must ask:

1. Can PM decide or document this?
2. Can Development implement or verify this?
3. Can Testing produce the missing evidence?
4. Is a new specialized agent/task needed?

Only if the answer is no should the Hub show a Jeremy ToDo. When Jeremy is needed, the linked issue or PR must contain <code>@jwildfire</code> followed by explicit questions/instructions, decision criteria, and the relevant evidence.

## Portfolio framework tasks

<ul>
  <li><a href="https://github.com/obot-claw/obot-claw.github.io/issues/21">#21 Agent Overview page</a> — this page.</li>
  <li><a href="https://github.com/obot-claw/obot-claw.github.io/issues/22">#22 Portfolio audit helper and PM report workflow</a>.</li>
  <li><a href="https://github.com/obot-claw/obot-claw.github.io/issues/23">#23 Hub sync gate for portfolio tracking</a>.</li>
  <li><a href="https://github.com/obot-claw/obot-claw.github.io/issues/24">#24 PM / Development / Testing launch contracts</a>.</li>
  <li><a href="https://github.com/obot-claw/obot-claw.github.io/issues/25">#25 Durable work-session supervision</a> — implemented with <code>scripts/work_session.py</code> and the <a href="/docs/work-session-supervision/">supervision contract</a>.</li>
</ul>

## References

<ul>
  <li><a href="/reports/pm-portfolio-framework-2026-06-06.html">PM Agent and Portfolio Framework Review</a>.</li>
  <li><a href="/autonomy/">Autonomy operating contract</a>.</li>
  <li><a href="/docs/work-session-supervision/">Work-session supervision contract</a>.</li>
  <li><a href="/docs/codex-cycle-contract/">Codex cycle contract</a>.</li>
  <li><a href="/roadmap/">Roadmap</a>.</li>
</ul>
