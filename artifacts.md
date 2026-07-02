---
layout: default
title: Artifacts
permalink: /artifacts/
---

# Artifacts

Long-form work products, modeled on the
[gsm.roadmap](https://github.com/Gilead-BioStats/gsm.roadmap) artifact framework.
Three kinds live here:

| Kind | Location | Convention |
| --- | --- | --- |
| Design documents | `requirements/design/` | `{issue}_design.html`, self-contained, linked from the Requirement's Design section |
| Data specifications | `requirements/dataspec/` | `{issue}_dataspec.md`, linked from the Requirement's Data Requirement section |
| Reports | `reports/` | Self-contained HTML page with front matter (`layout: default`, `title:`) — auto-listed below |

All artifacts are AI-generated and human-reviewed; each carries a status and
attribution line.

## Design documents

One per Requirement that needs a long-form design (simple requirements keep
their design inline in the issue).

{% assign designed = site.data.dashboard.requirements | where_exp: "r", "r.design_doc" %}
{% if designed.size > 0 %}
<ul class="queue-list">
{% for r in designed %}  <li><span class="reason">#{{ r.number }}</span><a href="{{ r.design_doc | relative_url }}">{{ r.number }}_design</a> — {{ r.title }}</li>
{% endfor %}</ul>
{% else %}
_None yet._
{% endif %}

## Data specifications

_None yet — the directory and convention are reserved
([`requirements/dataspec/`](https://github.com/obot-claw/obot-claw.github.io/tree/main/requirements/dataspec))._

## Reports

**Featured: [the ten-chapter framework report]({{ '/reports/autonomous-agent-framework/' | relative_url }})** —
the design document for the agentic development framework itself, written
chapter by chapter as the project evolved. It runs from the first options
analysis through the Paperclip and supervised-runner experiments to
[Chapter 10]({{ '/reports/autonomous-agent-framework/chapter-10-claude-code-migration/' | relative_url }}),
the July 2026 migration to Claude Code and the gsm.agent/gsm.roadmap
conventions.

Other reports, newest first:

{% assign reports = site.pages | where_exp: "p", "p.path contains 'reports/'" | sort: "path" | reverse %}
<ul class="queue-list">
{% for p in reports %}{% unless p.path contains 'autonomous-agent-framework/' %}  <li><a href="{{ p.url | relative_url }}">{{ p.title }}</a></li>
{% endunless %}{% endfor %}  <li><a href="{{ '/reports/pm-portfolio-framework-2026-06-06.html' | relative_url }}">PM agent and portfolio framework review</a></li>
  <li><a href="{{ '/reports/subagent-failure-deep-dive-2026-06-06.html' | relative_url }}">Subagent failure deep dive</a></li>
</ul>

## Contract and process docs

Operating contracts from the obot era, kept for reference:
[Codex cycle contract]({{ '/docs/codex-cycle-contract/' | relative_url }}) ·
[OpenClaw runner actions]({{ '/docs/openclaw-runner-actions/' | relative_url }}) ·
[Runner status dashboard]({{ '/docs/runner-status-dashboard/' | relative_url }}) ·
[Work-session supervision]({{ '/docs/work-session-supervision/' | relative_url }})
