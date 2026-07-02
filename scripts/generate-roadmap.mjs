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
  return title
    .replace(/^Project:\s*/i, '')
    .replace(/^Requirement:\s*/i, '')
    .replace(/^Task:\s*/i, '')
    .trim();
}

function isProjectIssue(item) {
  return Boolean(item && item.kind !== 'pull' && labels(item).includes('type:project'));
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

function assigneeText(item) {
  const assignees = item?.assignees || [];
  return assignees.length ? assignees.map((a) => `@${a.login}`).join(', ') : 'unassigned';
}

function milestoneText(item) {
  return item?.milestone?.title || 'no milestone';
}

function hasParentLink(task, requirementUrl) {
  return Boolean((task?.body || '').includes(requirementUrl));
}

function linkedPullUrls(markdown = '') {
  const re = /https:\/\/github\.com\/obot-claw\/[A-Za-z0-9_.-]+\/pull\/\d+/g;
  return [...new Set([...(markdown || '').matchAll(re)].map((m) => m[0]))];
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

function summarizeProjects(projectIssues, requirements, tasks) {
  const projects = new Map();
  for (const issue of projectIssues) {
    const proj = projectNumber(projectLabel(issue));
    if (!projects.has(proj)) projects.set(proj, { projectIssue: null, requirements: [], taskItems: [] });
    projects.get(proj).projectIssue = issue;
  }
  for (const issue of requirements) {
    const proj = projectNumber(projectLabel(issue));
    if (!projects.has(proj)) projects.set(proj, { projectIssue: null, requirements: [], taskItems: [] });
    const entry = projects.get(proj);
    entry.requirements.push(issue);
    for (const url of extractWorkUrls(issue.body || '')) {
      const task = tasks.get(workKeyFromUrl(url));
      if (!isProjectIssue(task)) entry.taskItems.push({ url, item: task });
    }
  }
  return [...projects.entries()].sort(([a], [b]) => a.localeCompare(b));
}

function countComplete(items, picker = (x) => x) {
  return items.filter((x) => isComplete(picker(x))).length;
}

function renderProjectSummary(projectIssues, requirements, tasks) {
  const projects = summarizeProjects(projectIssues, requirements, tasks);
  if (!projects.length) return 'No active projects found.\n';
  return projects.map(([proj, entry]) => {
    const reqDone = countComplete(entry.requirements);
    const taskDone = countComplete(entry.taskItems, (x) => x.item);
    const reqList = entry.requirements.map((issue) => {
      const linked = extractWorkUrls(issue.body || '').map((url) => tasks.get(workKeyFromUrl(url))).filter((item) => item && !isProjectIssue(item));
      const done = countComplete(linked);
      return `  - ${issue.html_url} — ${titleWithoutPrefix(issue.title)} (${statusText(issue)}; tasks/evidence ${done}/${linked.length} complete)`;
    });
    return [
      `### ${proj}`,
      '',
      entry.projectIssue ? `- Project issue: ${entry.projectIssue.html_url} — ${titleWithoutPrefix(entry.projectIssue.title)} (${statusText(entry.projectIssue)})` : '- Project issue: not created',
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
  const taskLines = bodyUrls.filter((url) => !isProjectIssue(tasks.get(workKeyFromUrl(url)))).map((url) => {
    const task = tasks.get(workKeyFromUrl(url));
    if (!task) return `  - ${url}`;
    if (task.kind === 'pull') {
      return `  - ${url} — PR: ${titleWithoutPrefix(task.title)} (${statusText(task)}; assignee: ${assigneeText(task)}; milestone: ${milestoneText(task)})`;
    }
    return `  - ${url} — ${titleWithoutPrefix(task.title)} (${statusText(task)}; assignee: ${assigneeText(task)}; milestone: ${milestoneText(task)})`;
  });
  return [
    `### ${proj} — ${titleWithoutPrefix(issue.title).replace(new RegExp(`^${proj}\\s+`, 'i'), '')}`,
    '',
    `- Requirement: ${issue.html_url}`,
    `- Status: ${status}`,
    `- Labels: ${labels(issue).join(', ') || 'none'}`,
    '- Tasks / evidence:',
    ...(taskLines.length ? taskLines : ['  - No linked sub-issues found in the Requirement body.']),
    ''
  ].join('\n');
}

function renderMetadataWarnings(projectIssues, requirements, tasks) {
  const warnings = [];
  const projectByLabel = new Map(projectIssues.map((issue) => [projectNumber(projectLabel(issue)), issue]));
  for (const req of requirements) {
    if (!req.assignees?.length) warnings.push(`${req.html_url} is missing an assignee.`);
    if (!req.milestone) warnings.push(`${req.html_url} is missing a milestone.`);
    const parentProject = projectByLabel.get(projectNumber(projectLabel(req)));
    if (parentProject && !(req.body || '').includes(parentProject.html_url)) {
      warnings.push(`${req.html_url} does not link back to parent project ${parentProject.html_url}.`);
    }
    for (const url of extractWorkUrls(req.body || '')) {
      const item = tasks.get(workKeyFromUrl(url));
      if (!item || item.kind === 'pull' || isProjectIssue(item)) continue;
      if (!item.assignees?.length) warnings.push(`${url} is missing an assignee.`);
      if (!item.milestone) warnings.push(`${url} is missing a milestone.`);
      if (!hasParentLink(item, req.html_url)) warnings.push(`${url} does not link back to parent requirement ${req.html_url}.`);
      if (statusText(item) === 'ready-review' && linkedPullUrls(item.body).length === 0) {
        warnings.push(`${url} is ready for review but has no linked PR.`);
      }
    }
  }
  if (!warnings.length) return 'No metadata gaps found.\n';
  return warnings.map((w) => `- ${w}`).join('\n') + '\n';
}

async function main() {
  const projectIssues = await listIssues(requirementsRepo, {
    state: 'all',
    labels: 'type:project'
  });
  const requirements = await listIssues(requirementsRepo, {
    state: 'all',
    labels: 'type:requirement'
  });
  const activeRequirements = requirements.filter((issue) => issue.state === 'open');

  projectIssues.sort((a, b) => projectNumber(projectLabel(a)).localeCompare(projectNumber(projectLabel(b))) || a.number - b.number);
  requirements.sort((a, b) => projectNumber(projectLabel(a)).localeCompare(projectNumber(projectLabel(b))) || a.number - b.number);
  activeRequirements.sort((a, b) => projectNumber(projectLabel(a)).localeCompare(projectNumber(projectLabel(b))) || a.number - b.number);

  const taskUrls = [...new Set(requirements.flatMap((issue) => extractWorkUrls(issue.body || '')))];
  const taskEntries = await Promise.all(taskUrls.map(async (url) => [workKeyFromUrl(url), await fetchWorkUrl(url)]));
  const tasks = new Map(taskEntries.filter(([, issue]) => issue));

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
    'Generated from GitHub Issues. Counts update when the roadmap workflow runs.',
    '',
    '## Issue conventions',
    '',
    '- **Project issues** live in `obot-claw/obot-claw.github.io` and use `type:project`.',
    '- **Requirement issues** live in `obot-claw/obot-claw.github.io` and link back to a parent Project issue when one exists.',
    '- **Sub-issues** live in the repo closest to the implementation work and are linked to their Requirement via the GitHub sub-issue relationship.',
    '- Every Requirement follows the [Requirement lifecycle](README.md#requirement-lifecycle): `Business Requirement` + `Overview` at creation, then `Data Requirement`, `Design`, and a `Sub-issues` list mirroring the linked sub-issue URLs.',
    '- Every Requirement should have one `project:P###` label.',
    '- Project issues should link child Requirement issues.',
    '',
    '## Project rollup',
    '',
    renderProjectSummary(projectIssues, requirements, tasks),
    '## Active requirements',
    '',
    ...(activeRequirements.length ? activeRequirements.map((issue) => renderRequirement(issue, tasks)) : ['No open Requirement issues found.', '']),
    '## Metadata checks',
    '',
    renderMetadataWarnings(projectIssues, requirements, tasks),
    '## Labels',
    '',
    '- `type:project` — top-level project that parents requirements.',
    '- `type:requirement` — high-level requirement linked to a parent project when one exists.',
    '- `type:task` — implementation task linked from a requirement.',
    '- `project:P###` — project rollup label.',
    '- `status:planned`, `status:in-progress`, `status:blocked`, `status:ready-review` — working status labels.',
    '',
    '## Automation',
    '',
    'This page is generated from GitHub issues labeled `type:project` and `type:requirement`. Project issues parent Requirements; linked sub-issues and evidence PRs are pulled from the issue/PR URLs in each Requirement body (the Sub-issues section).',
    ''
  ].join('\n');

  await fs.writeFile(new URL('../roadmap.md', import.meta.url), body);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
