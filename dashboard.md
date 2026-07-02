---
layout: default
title: Dashboard
permalink: /dashboard/
---

# Dashboard

{% assign dash = site.data.dashboard %}{% assign metrics = site.data.metrics %}
Live view of the project: what needs Jeremy, where the requirements stand, and
delivery totals. Data regenerates hourly from GitHub (see
[Automation](#data-freshness)).

## 🙋 Jeremy's queue

Items that block on Jeremy — flagged decisions (`needs:jeremy`), requirements and
tasks marked `status:ready-review`, and open non-draft pull requests (nothing
merges without his approval).

{% if dash.counts.queue == 0 %}
<p class="queue-empty">✨ The queue is clear — nothing is waiting on Jeremy right now.</p>
{% else %}
<ul class="queue-list">
{% for item in dash.queue %}  <li><span class="reason">{{ item.reason }}</span><a href="{{ item.url }}">{{ item.repo }}#{{ item.number }}</a> — {{ item.title }}</li>
{% endfor %}</ul>
{% endif %}

## Requirements

<ul class="metric-list">
  <li><strong>{{ dash.counts.open_requirements }}</strong><span>open requirements</span></li>
{% for tile in dash.counts.status_tiles %}  <li><strong>{{ tile.count }}</strong><span>{{ tile.icon }} {{ tile.status }}</span></li>
{% endfor %}  <li><strong>{{ dash.counts.completed_requirements }}</strong><span>✅ completed</span></li>
</ul>

Full requirement detail, grouped by project, lives on the
[Roadmap]({{ '/roadmap/' | relative_url }}).

## Pull requests in flight

<ul class="metric-list">
  <li><strong>{{ dash.counts.open_prs }}</strong><span>open PRs (review gate)</span></li>
  <li><strong>{{ dash.counts.draft_prs }}</strong><span>draft PRs (agents at work)</span></li>
</ul>

{% assign nondraft = dash.open_prs | where: "draft", false %}
{% if nondraft.size > 0 %}
<ul class="queue-list">
{% for pr in nondraft %}  <li><span class="reason">open</span><a href="{{ pr.url }}">{{ pr.repo }}#{{ pr.number }}</a> — {{ pr.title }}</li>
{% endfor %}</ul>
{% endif %}

{% assign drafts = dash.open_prs | where: "draft", true %}
{% if drafts.size > 0 %}
<details markdown="0"><summary>Show {{ drafts.size }} draft PRs</summary>
<ul class="queue-list">
{% for pr in drafts %}  <li><span class="reason">draft</span><a href="{{ pr.url }}">{{ pr.repo }}#{{ pr.number }}</a> — {{ pr.title }}</li>
{% endfor %}</ul>
</details>
{% endif %}

## Delivery totals

Cumulative across the project's public repos ({{ metrics.repos | size }} in
scope, both the `obot-claw` org and `jwildfire` project repos), all eras.

<ul class="metric-list">
  <li><strong>{{ metrics.commits_fmt }}</strong><span>commits made</span></li>
  <li><strong>{{ metrics.prs_fmt }}</strong><span>PRs merged</span></li>
  <li><strong>{{ metrics.loc_fmt }}</strong><span>tracked text lines</span></li>
  <li><strong>{{ metrics.releases_fmt }}</strong><span>releases</span></li>
</ul>

## Data freshness

- Queue, requirements, and PR data: generated **{{ dash.generated_at }}** by
  `scripts/generate-hub-data.mjs` (hourly via the *Update hub data* workflow, and
  on issue changes in this repo).
- Delivery totals: updated **{{ metrics.updated }}** by `scripts/update_metrics.py`
  (daily via the *Update metrics* workflow).
