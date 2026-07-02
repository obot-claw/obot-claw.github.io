# obot-claw.github.io

Public hub for the safetyGraphics → gsm modernization: requirement tracking
(gsm.roadmap-style) plus the project site — home, dashboard, roadmap, diary, and
artifacts.

Site:

https://obot-claw.github.io/

> **Planned identity consolidation:** this repo is expected to move to
> `jwildfire/obot.roadmap` (repo transfer + rename) as part of shuttering the
> `obot-claw` identity. All automation is parameterized for the move
> (`HUB_OWNER`, `HUB_REPO`, `HUB_AUTHORS`, `HUB_EXTRA_REPOS`) and internal links
> use `relative_url`, so only `_config.yml` (`url`/`baseurl`) and the workflow
> defaults change at transfer time.

## Privacy rule

Only publish open-source/public project summaries here. Keep private, personal,
credential, or ambiguous material local unless Jeremy explicitly marks it public.

## Site structure

| Page | Source | Maintained by |
| --- | --- | --- |
| Home (`/`) | `index.md` | Hand-edited; latest-diary link is automatic (Liquid) |
| Dashboard (`/dashboard/`) | `dashboard.md` + `_data/dashboard.json` + `_data/metrics.json` | Fully generated — never edit the JSON by hand |
| Roadmap (`/roadmap/`) | `roadmap.md` | Fully generated — edit GitHub Requirement issues instead |
| Diary (`/daily/`) | `daily/YYYY-MM-DD.md` | Agents add entry files; the index is automatic (Liquid) |
| Artifacts (`/artifacts/`) | `artifacts.md` | Auto-lists design docs and reports; edit only to feature/curate |
| Archive | `projects*.md`, `agents.md`, `autonomy.md`, `docs/`, `scripts/archive/` | Frozen obot-era pages, banner-marked |

## Automation

- **Update hub data** (`.github/workflows/update-hub-data.yml`) — hourly and on
  issue changes; runs `scripts/generate-hub-data.mjs`, which regenerates
  `roadmap.md` and `_data/dashboard.json` (requirements, sub-issue rollups, open
  PRs, and the Jeremy queue) from the GitHub API.
- **Update metrics** (`.github/workflows/update-metrics.yml`) — daily; runs
  `scripts/update_metrics.py`, which writes `_data/metrics.json` (commits,
  merged PRs, tracked lines, releases across the in-scope public repos).
- **Deploy GitHub Pages** (`.github/workflows/pages.yaml`) — Jekyll build on
  every push to `main`.

Run either generator locally:

```bash
GITHUB_TOKEN=$(gh auth token) node scripts/generate-hub-data.mjs
python3 scripts/update_metrics.py
```

### The Jeremy queue

The dashboard surfaces everything that blocks on Jeremy, from three signals:

1. `needs:jeremy` label on any issue or PR — the explicit flag agents apply when
   an item needs his decision (replaces the old hand-maintained homepage ToDo list).
2. `status:ready-review` label — lifecycle review gate.
3. Any open non-draft PR — nothing merges without his approval.

## Publishing a diary entry

Diary entries are AI-written summaries of the public work, published on days
with public activity. To publish one, an agent only needs to:

1. Add `daily/YYYY-MM-DD.md` with front matter `layout: default` and
   `title: YYYY-MM-DD`.
2. Optionally run `python3 scripts/update_metrics.py` to refresh delivery totals.
3. Commit and push. The diary index, homepage link, and dashboard pick the entry
   up automatically — no other file needs editing.

## Requirement lifecycle

Adopted July 2026 from the [gsm.roadmap](https://github.com/Gilead-BioStats/gsm.roadmap) requirement workflow, alongside the [gsm.agent](https://github.com/Gilead-BioStats/gsm.agent) development conventions (drafts, worktrees, TDD, approval gates). Requirement issues live in this repo; implementation work is tracked as **sub-issues** in the repo closest to the code.

A Requirement issue body has five sections, populated incrementally:

| Section | When filled | Required at creation |
|---|---|---|
| **Business Requirement** | Backlog | ✓ |
| **Overview** | Backlog | ✓ |
| **Data Requirement** | Requirement Gathering | — |
| **Design** | Design (inline, or `requirements/design/{issue_number}_design.html`) | — |
| **Sub-issues** | After Design — mirrors the linked sub-issue URLs for the roadmap rollup | — |

Stages and skills:

| Stage | Skill | Notes |
|---|---|---|
| Backlog | [`requirement-drafting`](.github/skills/requirement-drafting/SKILL.md) | `type:requirement` + `status:planned` + `project:P###` labels |
| Design | [`requirement-design`](.github/skills/requirement-design/SKILL.md) | Design signed off before decomposition |
| Tasks | [`requirement-tasks`](.github/skills/requirement-tasks/SKILL.md) | Repo-scoped sub-issues, linked via gsm.agent's `sub-issue-linking` |
| Development | gsm.agent [`tdd`](https://github.com/Gilead-BioStats/gsm.agent/blob/main/skills/tdd/SKILL.md) | One `/tdd` run per sub-issue; PRs carry evidence; no merges without Jeremy |
| Review / done | — | `status:ready-review` → close; rollup via the hub-data workflow |

Differences from gsm.roadmap, kept deliberately lean for a solo project: no quarterly milestones or planning ceremony; lifecycle stage is tracked with the existing `status:*` labels; the `Sub-issues` body section is retained (gsm.roadmap removed its equivalent) because `scripts/generate-hub-data.mjs` counts tasks from body URLs; no scheduled requirement-status rollup — the hub-data workflow covers it.

## Artifacts

Modeled on gsm.roadmap's artifact framework; indexed at
[/artifacts/](https://obot-claw.github.io/artifacts/):

- `requirements/design/{issue}_design.html` — self-contained HTML design doc per
  Requirement (see `requirements/design/README.md` for format rules).
- `requirements/dataspec/{issue}_dataspec.md` — data specification per
  Requirement, when needed.
- `reports/` — AI-generated long-form reports. New reports are self-contained
  HTML pages with Jekyll front matter (`layout: default`, `title:`); they
  auto-list on the Artifacts page.

## Legacy (obot era)

The P001–P009 project catalog, agent operating contracts, and autonomy
framework were retired in July 2026 when development moved to interactive
Claude Code sessions ([Chapter 10](https://obot-claw.github.io/reports/autonomous-agent-framework/chapter-10-claude-code-migration/)).
Their pages carry archive banners; the P007–P009 helper scripts (hub sync gate,
portfolio audit, work-session supervision, Codex runner) live unmaintained in
`scripts/archive/`.
