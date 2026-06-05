#!/usr/bin/env node
import fs from 'node:fs/promises';

const owner = process.env.ROADMAP_OWNER || 'obot-claw';
const requirementsRepo = process.env.ROADMAP_REQUIREMENTS_REPO || 'obot-claw.github.io';
const token = process.env.GITHUB_TOKEN || process.env.GH_TOKEN || '';
const apiBase = process.env.GITHUB_API_URL || 'https://api.github.com';

const headers = {
  'Accept': 'application/vnd.github+json',
  'X-GitHub-Api-Version': '2022-11-28',
  'User-Agent': 'obot-roadmap-generator'
};
if (token) headers.Authorization = `Bearer ${token}`;

async function github(path) {
  const res = await fetch(`${apiBase}${path}`, { headers });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`GitHub API ${res.status} for ${path}: ${body.slice(0, 500)}`);
  }
  return res.json();
}

async function listIssues(repo, params) {
  const out = [];
  let page = 1;
  while (true) {
    const query = new URLSearchParams({ per_page: '100', page: String(page), ...params });
    const rows = await github(`/repos/${owner}/${repo}/issues?${query}`);
    const issues = rows.filter((x) => !x.pull_request);
    out.push(...issues);
    if (rows.length < 100) return out;
    page += 1;
  }
}

function labels(issue) {
  return issue.labels.map((l) => typeof l === 'string' ? l : l.name).filter(Boolean);
}

function projectLabel(issue) {
  return labels(issue).find((l) => /^project:P\d+/i.test(l)) || 'project:unassigned';
}

function statusLabel(issue) {
  return labels(issue).find((l) => /^status:/i.test(l)) || 'status:unknown';
}

function projectNumber(label) {
  const match = label.match(/P(\d+)/i);
  return match ? `P${match[1]}` : 'Unassigned';
}

function titleWithoutPrefix(title) {
  return title.replace(/^Requirement:\s*/i, '').replace(/^Task:\s*/i, '').trim();
}

function isComplete(item) {
  if (!item) return false;
  if (item.kind === 'pull') return Boolean(item.merged_at) || item.state === 'closed';
  return item.state === 'closed' || labels(item).includes('status:complete') || labels(item).includes('status:completed');
}

function statusText(item) {
  if (!item) return 'unknown';
  if (item.kind === 'pull') {
    if (item.merged_at) return 'merged';
    return item.state;
  }
  if (item.state === 'closed') return 'closed';
  return statusLabel(item).replace(/^status:/, '');
}

function extractWorkUrls(markdown = '') {
  const urls = new Set();
  const re = /https:\/\/github\.com\/obot-claw\/[A-Za-z0-9_.-]+\/(?:issues|pull)\/\d+/g;
  for (const match of markdown.matchAll(re)) urls.add(match[0]);
  return [...urls];
}

function workKeyFromUrl(url) {
  const m = url.match(/github\.com\/([^/]+)\/([^/]+)\/(issues|pull)\/(\d+)/);
  return m ? `${m[1]}/${m[2]}/${m[3]}#${m[4]}` : url;
}

async function fetchWorkUrl(url) {
  const m = url.match(/github\.com\/([^/]+)\/([^/]+)\/(issues|pull)\/(\d+)/);
  if (!m) return null;
  const [, urlOwner, repo, kind, number] = m;
  if (urlOwner !== owner) return null;
  if (kind === 'pull') return { kind, ...(await github(`/repos/${owner}/${repo}/pulls/${number}`)) };
  return { kind, ...(await github(`/repos/${owner}/${repo}/issues/${number}`)) };
}

function summarizeProjects(requirements, tasks) {
  const projects = new Map();
  for (const issue of requirements) {
    const proj = projectNumber(projectLabel(issue));
    if (!projects.has(proj)) projects.set(proj, { requirements: [], taskItems: [] });
    const entry = projects.get(proj);
    entry.requirements.push(issue);
    for (const url of extractWorkUrls(issue.body || '')) {
      const task = tasks.get(workKeyFromUrl(url));
      entry.taskItems.push({ url, item: task });
    }
  }
  return [...projects.entries()].sort(([a], [b]) => a.localeCompare(b));
}

function countComplete(items, picker = (x) => x) {
  return items.filter((x) => isComplete(picker(x))).length;
}

function renderProjectSummary(requirements, tasks) {
  const projects = summarizeProjects(requirements, tasks);
  if (!projects.length) return 'No active projects found.\n';
  return projects.map(([proj, entry]) => {
    const reqDone = countComplete(entry.requirements);
    const taskDone = countComplete(entry.taskItems, (x) => x.item);
    const reqList = entry.requirements.map((issue) => `  - ${issue.html_url} — ${titleWithoutPrefix(issue.title)} (${statusText(issue)})`);
    return [
      `### ${proj}`,
      '',
      `- Requirements: ${reqDone}/${entry.requirements.length} complete`,
      `- Linked tasks/evidence: ${taskDone}/${entry.taskItems.length} complete`,
      '- Requirement drilldown:',
      ...(reqList.length ? reqList : ['  - None']),
      ''
    ].join('\n');
  }).join('\n');
}

function renderRequirement(issue, tasks) {
  const proj = projectNumber(projectLabel(issue));
  const status = statusText(issue);
  const bodyUrls = extractWorkUrls(issue.body || '');
  const taskLines = bodyUrls.map((url) => {
    const task = tasks.get(workKeyFromUrl(url));
    if (!task) return `  - ${url}`;
    if (task.kind === 'pull') {
      return `  - ${url} — PR: ${titleWithoutPrefix(task.title)} (${statusText(task)})`;
    }
    return `  - ${url} — ${titleWithoutPrefix(task.title)} (${statusText(task)})`;
  });
  return [
    `### ${proj} — ${titleWithoutPrefix(issue.title).replace(new RegExp(`^${proj}\\s+`, 'i'), '')}`,
    '',
    `- Requirement: ${issue.html_url}`,
    `- Status: ${status}`,
    `- Labels: ${labels(issue).join(', ') || 'none'}`,
    '- Tasks / evidence:',
    ...(taskLines.length ? taskLines : ['  - No linked task issues found in the implementation plan.']),
    ''
  ].join('\n');
}

async function main() {
  const requirements = await listIssues(requirementsRepo, {
    state: 'all',
    labels: 'type:requirement'
  });
  const activeRequirements = requirements.filter((issue) => issue.state === 'open');

  requirements.sort((a, b) => projectNumber(projectLabel(a)).localeCompare(projectNumber(projectLabel(b))) || a.number - b.number);
  activeRequirements.sort((a, b) => projectNumber(projectLabel(a)).localeCompare(projectNumber(projectLabel(b))) || a.number - b.number);

  const taskUrls = [...new Set(requirements.flatMap((issue) => extractWorkUrls(issue.body || '')))];
  const taskEntries = await Promise.all(taskUrls.map(async (url) => [workKeyFromUrl(url), await fetchWorkUrl(url)]));
  const tasks = new Map(taskEntries.filter(([, issue]) => issue));

  const generatedAt = new Date().toISOString();
  const body = [
    '---',
    'layout: default',
    'title: Roadmap',
    '---',
    '',
    '# Roadmap',
    '',
    '<!-- AUTO-GENERATED by scripts/generate-roadmap.mjs. Edit GitHub Requirement/Task issues instead of this section. -->',
    '',
    `Generated from GitHub Issues at ${generatedAt}.`,
    '',
    '## Issue conventions',
    '',
    '- **Requirement issues** live in `obot-claw/obot-claw.github.io`.',
    '- **Task issues** live in the repo closest to the implementation work.',
    '- Every Requirement should include `# Overview`, `# Design`, and `# Implementation plan` sections.',
    '- Every Requirement should have one `project:P###` label.',
    '- Requirement implementation plans should link task sub-issues or PRs.',
    '',
    '## Project rollup',
    '',
    renderProjectSummary(requirements, tasks),
    '## Active requirements',
    '',
    ...(activeRequirements.length ? activeRequirements.map((issue) => renderRequirement(issue, tasks)) : ['No open Requirement issues found.', '']),
    '## Labels',
    '',
    '- `type:requirement` — high-level requirement.',
    '- `type:task` — implementation task linked from a requirement.',
    '- `project:P###` — project rollup label.',
    '- `status:planned`, `status:in-progress`, `status:blocked`, `status:ready-review` — working status labels.',
    '',
    '## Automation',
    '',
    'This page is generated from open GitHub issues labeled `type:requirement`. Linked task issues and evidence PRs are pulled from Requirement implementation plans.',
    ''
  ].join('\n');

  await fs.writeFile(new URL('../roadmap.md', import.meta.url), body);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
