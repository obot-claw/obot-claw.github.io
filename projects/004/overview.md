---
layout: default
title: P004 SafetyGraphics Renderer Modernization
permalink: /projects/004/overview.html
---

# P004 SafetyGraphics Renderer Modernization

## Goal

Modernize the legacy Safety Explorer Suite JavaScript renderers so they can become maintained SafetyGraphics tools with cleaner dependencies, stronger tests, and a shared design language for both interactive monitoring graphics and future static safety displays.

The current suite documentation describes nine custom interactive graphics, maintained as separate repositories, plus supporting JavaScript/R frameworks. The legacy renderers were built on `d3` v3 and `webcharts`; this project will remove the `webcharts` dependency and move toward independent modern JavaScript renderers, likely using Chart.js where it fits the display model.

## Coordination repository

The shared agent framework for this modernization program lives at https://github.com/obot-claw/safety-agent. It contains the GxP-oriented workflow rules, requirements-harvesting process, test framework guidance, and reusable agent skills for renderer migrations.

## Source inventory

Initial forks were created under `obot-claw` as staging repositories before eventual transfer or replacement under `SafetyGraphics`.

| Area | Upstream | Staging fork | Role |
|---|---|---|---|
| AE Explorer | https://github.com/RhoInc/aeexplorer | https://github.com/obot-claw/aeexplorer | Adverse event incidence explorer |
| AE Timelines | https://github.com/RhoInc/ae-timelines | https://github.com/obot-claw/ae-timelines | Participant AE timeline display |
| Safety Outlier Explorer | https://github.com/RhoInc/safety-outlier-explorer | https://github.com/obot-claw/safety-outlier-explorer | Longitudinal participant outlier review |
| Paneled Outlier Explorer | https://github.com/RhoInc/paneled-outlier-explorer | https://github.com/obot-claw/paneled-outlier-explorer | Multi-measure participant outlier panels |
| Safety Results Over Time | https://github.com/RhoInc/safety-results-over-time | https://github.com/obot-claw/safety-results-over-time | Population trends over visits/time |
| Safety Histogram | https://github.com/RhoInc/safety-histogram | https://github.com/obot-claw/safety-histogram | Distribution review for labs/vitals/other safety measures |
| Safety Shift Plot | https://github.com/RhoInc/safety-shift-plot | https://github.com/obot-claw/safety-shift-plot | Baseline-to-postbaseline shift review |
| Safety Delta Delta | https://github.com/RhoInc/safety-delta-delta | https://github.com/obot-claw/safety-delta-delta | Change-over-time multi-measure review |
| Web Codebook | https://github.com/RhoInc/web-codebook | https://github.com/obot-claw/web-codebook | Interactive variable-level data summary |
| Safety Explorer Suite | https://github.com/RhoInc/safety-explorer-suite | https://github.com/obot-claw/safety-explorer-suite | Multi-renderer suite shell/framework |

Hep Explorer is already under SafetyGraphics at https://github.com/safetyGraphics/hep-explorer and should be handled separately from the RhoInc fork migration.

## Modernization principles

1. Keep the clinical display contract stable before changing internals.
2. Separate renderer data preparation from chart rendering.
3. Prefer explicit schemas for data mappings and settings.
4. Replace `webcharts` conventions with renderer-local state, lifecycle, and event handling.
5. Keep interactive and static chart implementations aligned around the same display definitions.
6. Add deterministic tests before major rendering rewrites.
7. Ship migration in small PRs: dependency cleanup, architecture seams, renderer rewrite, then static/interactive alignment.

## Proposed phases

### Phase 0: Inventory and planning

- Fork repositories under `obot-claw`.
- Confirm repository status, package managers, build tools, test coverage, and current examples.
- Identify common renderer patterns across the suite.
- Pick a first package for the modernization spike.

### Phase 1: Baseline maintenance pass

- Update repository metadata from RhoInc to staging/SafetyGraphics context.
- Confirm current build/test commands.
- Add current-state CI where missing.
- Document unsupported or archived paths.
- Capture screenshots or example outputs as regression baselines where browser tooling allows.

### Phase 2: Shared renderer architecture

Define a minimal renderer lifecycle that can replace Webcharts usage consistently:

- `init(data)`
- `setData(data)`
- `setSettings(settings)`
- `render()`
- `resize()`
- `destroy()`
- event hooks for filter/group/selection/listing updates

Shared modules should cover:

- data validation
- settings validation
- controls/filter state
- accessibility defaults
- browser example harness
- visual regression hooks

### Phase 3: First Chart.js renderer spike

Start with Safety Histogram because it is a focused distribution display, has clear data requirements, and exposes the main migration problems without the full complexity of AE tables or linked timelines.

Deep dive: [Safety Histogram implementation plan](./safety-histogram.html)

### Phase 4: Suite-wide migration

Apply the proven pattern renderer by renderer:

1. Safety Histogram
2. Safety Results Over Time
3. Safety Shift Plot
4. Safety Delta Delta
5. Safety Outlier Explorer
6. Paneled Outlier Explorer
7. AE Timelines
8. AE Explorer
9. Web Codebook / suite shell as needed
10. Hep Explorer coordination with the existing SafetyGraphics repo

### Phase 5: Static + interactive alignment

After the interactive renderer architecture is stable, define static chart equivalents for FDA-style reports using the same display contracts where possible. The target is a paired workflow: static submission-style graphics plus interactive monitoring graphics that share data mappings and display intent.

## Interview decisions

These decisions are being captured through the Telegram interview workflow and mirrored in the `safety-agent` interview log at https://github.com/obot-claw/safety-agent/blob/main/interviews/p004-open-questions.md.

| Topic | Decision | Status |
|---|---|---|
| Repository structure | Keep the current fork-per-renderer structure for now; revisit monorepo consolidation after the Safety Histogram spike clarifies shared tooling and release coupling. | Decided |
| Chart.js scope | Use Chart.js as the preferred reference implementation pattern, aligned with `gsm.viz`, but allow custom SVG/Canvas when justified by renderer requirements. | Decided |
| Qualification-ready testing | Use the `safety-agent` implementation-framework spike to define a traceable standard linking wiki requirements to unit, integration, browser, visual-regression, accessibility, and review-evidence checks. | Decided |
| Legacy API compatibility | Breaking changes are acceptable. Design clean nextgen APIs and release as new major versions or possibly new packages; do not preserve legacy APIs or wrappers by default. | Decided |
| Static chart API boundary | Keep static chart APIs in R-side packages such as `gsm.safety` or `safetyCharts`; nextgen renderer repos stay focused on interactive JavaScript renderers. `gsm.safety` continues orchestrating htmlwidget rendering for interactive outputs. | Decided |

## Open questions

No project-level interview questions remain open. New questions should be added as the Safety Histogram implementation spike exposes concrete design decisions.

## Immediate next step

Review the Safety Histogram implementation plan and use the `safety-agent` implementation-framework spike to define the detailed documentation, skills, tools, and test evidence needed before substantive renderer migration starts.
