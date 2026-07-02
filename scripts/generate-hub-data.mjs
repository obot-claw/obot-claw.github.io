#!/usr/bin/env node
// Generate the requirements roadmap page and the dashboard data file from GitHub.
//
// Outputs:
//   roadmap.md            — requirements-first roadmap (rendered by Jekyll)
//   _data/dashboard.json  — dashboard tiles + Jeremy's queue (rendered via Liquid)
//
// Owner/repo are parameterized so the automation survives the planned move to
// jwildfire/obot.roadmap unchanged (set HUB_OWNER / HUB_REPO / HUB_EXTRA_REPOS).
import fs from 'node:fs';
import fsp from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const owner = process.env.HUB_OWNER || process.env.ROADMAP_OWNER || 'obot-claw';
const hubRepo = process.env.HUB_REPO || process.env.ROADMAP_REQUIREMENTS_REPO || 'obot-claw.github.io';
// Project repos that live outside the hub owner (e.g. safety.viz under jwildfire).
const extraRepos = (process.env.HUB_EXTRA_REPOS || 'jwildfire/safety.viz')
  .split(',').map((s) => s.trim()).filter(Boolean);
const reviewer = process.env.HUB_REVIEWER || 'jwildfire';
const token = process.env.GITHUB_TOKEN || process.env.GH_TOKEN || '';
const apiBase = process.env.GITHUB_API_URL || 'https://api.github.com';
const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

// Projects without their own GitHub artifacts yet still get a roadmap section.
const ACTIVE_PROJECTS = ['P004', 'P005', 'P006'];
const LEGACY_PROJECTS = [
  ['P001', 'OpenClaw setup', 'Completed May 2026', '/projects/#openclaw-setup'],
  ['P002', 'Initialize gsm.safety with safetyCharts widgets', 'Completed May 2026', '/projects/#initialize-gsmsafety-with-safetycharts-widgets'],
  ['P003', 'Initialize obot home page and diary', 'Completed May 2026', '/projects/#initialize-obot-home-page-and-diary'],
  ['P007', 'Refactor development framework for increased autonomy', 'Superseded July 2026 (Claude Code migration)', 'https://github.com/obot-claw/obot-claw.github.io/issues/17'],
  ['P008', 'Paperclip autonomous agent orchestration pilot', 'Superseded July 2026 (Claude Code migration)', 'https://github.com/obot-claw/obot-claw.github.io/issues/30'],
  ['P009', 'Execution-first reliable autonomous cycle', 'Superseded July 2026 (Claude Code migration)', 'https://github.com/obot-claw/obot-claw.github.io/issues/36'],
];

const headers = {
  'Accept': 'application/vnd.github+json',
  'X-GitHub-Api-Version': '2022-11-28',
  'User-Agent': 'obot-hub-data-generator'
};
if (token) headers.Authorization = `Bearer ${token}`;

async function github(pathname) {
  const res = await fetch(`${apiBase}${pathname}`, { headers });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`GitHub API ${res.status} for ${pathname}: ${body.slice(0, 500)}`);
  }
  return res.json();
}

async function searchIssues(q) {
  const out = [];
  let page = 1;
  while (true) {
    const query = new URLSearchParams({ q, per_page: '100', page: String(page) });
    const data = await github(`/search/issues?${query}`);
    out.push(...data.items);
    if (out.length >= data.total_count || data.items.length === 0) return out;
    page += 1;
  }
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
  return (issue.labels || []).map((l) => typeof l === 'string' ? l : l.name).filter(Boolean);
}

function projectCode(issue) {
  const label = labels(issue).find((l) => /^project:P\d+/i.test(l));
  const match = label ? label.match(/P(\d+)/i) : null;
  return match ? `P${match[1]}` : null;
}

function statusText(item) {
  if (!item) return 'unknown';
  if (item.kind === 'pull') return item.merged_at ? 'merged' : item.state;
  if (item.state === 'closed') return 'done';
  const status = labels(item).find((l) => /^status:/i.test(l));
  return status ? status.replace(/^status:/, '') : 'unlabeled';
}

function titleWithoutPrefix(title) {
  return title.replace(/^(Project|Requirement|Task):\s*/i, '').trim();
}

function repoFromUrl(url) {
  const m = (url || '').match(/github\.com\/([^/]+\/[^/]+)/);
  return m ? m[1] : '';
}

function extractWorkUrls(markdown = '') {
  const urls = new Set();
  const re = /https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/(?:issues|pull)\/\d+/g;
  for (const match of (markdown || '').matchAll(re)) urls.add(match[0]);
  return [...urls];
}

async function fetchWorkUrl(url) {
  const m = url.match(/github\.com\/([^/]+)\/([^/]+)\/(issues|pull)\/(\d+)/);
  if (!m) return null;
  const [, urlOwner, repo, kind, number] = m;
  const known = urlOwner === owner || extraRepos.includes(`${urlOwner}/${repo}`);
  if (!known) return null;
  try {
    if (kind === 'pull') return { kind, ...(await github(`/repos/${urlOwner}/${repo}/pulls/${number}`)) };
    return { kind, ...(await github(`/repos/${urlOwner}/${repo}/issues/${number}`)) };
  } catch {
    return null;
  }
}

function isComplete(item) {
  if (!item) return false;
  if (item.kind === 'pull') return Boolean(item.merged_at) || item.state === 'closed';
  return item.state === 'closed';
}

// Design docs are self-contained HTML pages (see requirements/design/README.md).
function designDocPath(number) {
  const file = path.join(root, 'requirements', 'design', `${number}_design.html`);
  return fs.existsSync(file) ? `/requirements/design/${number}_design.html` : null;
}

function requirementRecord(issue, tasks) {
  const urls = extractWorkUrls(issue.body || '');
  const items = urls
    .map((url) => ({ url, item: tasks.get(url) }))
    .filter(({ item, url }) => !repoOrSelfIsProject(item) && !url.includes(`/${hubRepo}/issues/${issue.number}`));
  return {
    number: issue.number,
    title: titleWithoutPrefix(issue.title),
    url: issue.html_url,
    state: issue.state,
    status: statusText(issue),
    project: projectCode(issue) || 'unassigned',
    assignees: (issue.assignees || []).map((a) => a.login),
    design_doc: designDocPath(issue.number),
    subitems: items.map(({ url, item }) => ({
      url,
      repo: repoFromUrl(url),
      kind: item?.kind === 'pull' ? 'pr' : 'issue',
      title: item ? titleWithoutPrefix(item.title) : url,
      status: statusText(item),
      complete: isComplete(item),
    })),
  };
}

function repoOrSelfIsProject(item) {
  return Boolean(item && item.kind !== 'pull' && labels(item).includes('type:project'));
}

// --- Jeremy's queue -------------------------------------------------------

function queueScopes() {
  return [`org:${owner}`, ...extraRepos.map((r) => `repo:${r}`)];
}

async function buildQueue() {
  const buckets = [];
  for (const scope of queueScopes()) {
    buckets.push(
      (await searchIssues(`${scope} is:open label:"needs:jeremy"`))
        .map((x) => ({ x, reason: 'Flagged for Jeremy', rank: 0 })),
      (await searchIssues(`${scope} is:open label:"status:ready-review"`))
        .map((x) => ({ x, reason: 'Ready for review', rank: 1 })),
      (await searchIssues(`${scope} is:pr is:open draft:false`))
        .map((x) => ({ x, reason: 'Open PR — review and merge gate', rank: 2 })),
    );
  }
  const seen = new Map();
  for (const { x, reason, rank } of buckets.flat().sort((a, b) => a.rank - b.rank)) {
    if (seen.has(x.html_url)) continue;
    seen.set(x.html_url, {
      kind: x.pull_request ? 'pr' : 'issue',
      repo: repoFromUrl(x.html_url),
      number: x.number,
      title: titleWithoutPrefix(x.title),
      url: x.html_url,
      reason,
      rank,
      updated_at: x.updated_at,
    });
  }
  return [...seen.values()].sort((a, b) => a.rank - b.rank || b.updated_at.localeCompare(a.updated_at));
}

async function buildOpenPrs() {
  const prs = [];
  for (const scope of queueScopes()) {
    prs.push(...await searchIssues(`${scope} is:pr is:open`));
  }
  return prs.map((x) => ({
    repo: repoFromUrl(x.html_url),
    number: x.number,
    title: titleWithoutPrefix(x.title),
    url: x.html_url,
    draft: Boolean(x.draft),
    updated_at: x.updated_at,
  })).sort((a, b) => b.updated_at.localeCompare(a.updated_at));
}

// --- Roadmap rendering ------------------------------------------------------

async function projectNames() {
  const names = new Map();
  const rows = await github(`/repos/${owner}/${hubRepo}/labels?per_page=100`);
  for (const l of rows) {
    const m = l.name.match(/^project:(P\d+)$/i);
    if (m) names.set(m[1].toUpperCase(), (l.description || '').replace(/^P\d+\s*/, '') || m[1]);
  }
  return names;
}

function statusIcon(status) {
  return { 'done': '✅', 'merged': '✅', 'in-progress': '🚧', 'ready-review': '🙋', 'blocked': '⛔', 'planned': '🕒' }[status] || '▫️';
}

function renderRequirementSection(req) {
  const lines = [
    `#### [#${req.number} — ${req.title}](${req.url})`,
    '',
    `- Status: ${statusIcon(req.status)} \`${req.status}\`` + (req.state === 'closed' ? ' (closed)' : ''),
  ];
  if (req.design_doc) lines.push(`- Design doc: [${req.number}_design]({{ '${req.design_doc}' | relative_url }})`);
  if (req.subitems.length) {
    const done = req.subitems.filter((s) => s.complete).length;
    lines.push(`- Sub-issues / evidence (${done}/${req.subitems.length} complete):`);
    for (const s of req.subitems) {
      lines.push(`  - ${s.complete ? '✅' : '⬜'} [${s.repo}#${s.url.split('/').pop()}](${s.url}) — ${s.title} (\`${s.status}\`)`);
    }
  } else {
    lines.push('- Sub-issues / evidence: none linked yet.');
  }
  lines.push('');
  return lines.join('\n');
}

function renderRoadmap({ requirements, projectIssues, names, generatedAt }) {
  const byProject = new Map();
  for (const req of requirements) {
    if (!byProject.has(req.project)) byProject.set(req.project, []);
    byProject.get(req.project).push(req);
  }
  const projectIssueByCode = new Map(projectIssues.map((i) => [projectCode(i), i]));
  const allCodes = [...new Set([...ACTIVE_PROJECTS, ...byProject.keys()])]
    .filter((c) => c !== 'unassigned').sort();
  const activeCodes = allCodes.filter((c) =>
    ACTIVE_PROJECTS.includes(c) || (byProject.get(c) || []).some((r) => r.state === 'open'));

  function renderProjectGroup(code, headingLevel) {
    const lines = [];
    const reqs = byProject.get(code) || [];
    const open = reqs.filter((r) => r.state === 'open');
    const closed = reqs.filter((r) => r.state === 'closed');
    const projIssue = projectIssueByCode.get(code);
    lines.push(`${headingLevel} ${code} — ${names.get(code) || code}`, '');
    if (projIssue) {
      lines.push(`Parent project issue: [#${projIssue.number}](${projIssue.html_url}) (${projIssue.state}).`, '');
    }
    if (!reqs.length) {
      lines.push('_No Requirement issues yet — a draft is prepared and pending review before posting._', '');
      return lines;
    }
    for (const req of open) lines.push(renderRequirementSection(req));
    if (closed.length) {
      lines.push('<details markdown="1"><summary>Completed requirements</summary>', '');
      for (const req of closed) lines.push(renderRequirementSection(req));
      lines.push('</details>', '');
    }
    return lines;
  }

  const sections = [];
  for (const code of activeCodes) sections.push(...renderProjectGroup(code, '###'));

  const unassigned = byProject.get('unassigned') || [];
  if (unassigned.length) {
    sections.push('### Unassigned requirements', '');
    for (const req of unassigned) sections.push(renderRequirementSection(req));
  }

  const legacyCodes = allCodes.filter((c) => !activeCodes.includes(c));
  const legacySections = [];
  if (legacyCodes.length) {
    legacySections.push('<details markdown="1"><summary>Requirement history for retired projects</summary>', '');
    for (const code of legacyCodes) legacySections.push(...renderProjectGroup(code, '####'));
    legacySections.push('</details>', '');
  }

  return [
    '---',
    'layout: default',
    'title: Roadmap',
    '---',
    '',
    '# Roadmap',
    '',
    '<!-- AUTO-GENERATED by scripts/generate-hub-data.mjs. Edit GitHub Requirement issues instead of this file. -->',
    '',
    'Requirement issues are the unit of planning: each one moves through the',
    '[requirement lifecycle](https://github.com/' + owner + '/' + hubRepo + '#requirement-lifecycle)',
    '(Business Requirement + Overview → Data Requirement → Design → cross-repo sub-issues).',
    'This page regenerates from GitHub hourly.',
    '',
    '## Active work',
    '',
    ...sections,
    '## Legacy obot-era projects',
    '',
    'The original project catalog (P001–P009) predates the requirement lifecycle.',
    'Active workstreams above carry their `project:P###` labels forward; the rest are',
    'archived below and on the [Projects archive]({{ \'/projects/\' | relative_url }}).',
    '',
    '| Code | Project | Outcome |',
    '| --- | --- | --- |',
    ...LEGACY_PROJECTS.map(([code, name, outcome, link]) =>
      `| ${code} | [${name}](${link.startsWith('http') ? link : `{{ '${link}' | relative_url }}`}) | ${outcome} |`),
    '',
    ...legacySections,
    '## Conventions',
    '',
    '- `type:requirement` — high-level requirement; `type:task` — implementation task; `type:project` — legacy parent (P004 only).',
    '- `project:P###` — workstream rollup label. `status:planned` / `status:in-progress` / `status:blocked` / `status:ready-review` — working status.',
    '- `needs:jeremy` — blocks on a Jeremy decision; surfaces on the [Dashboard]({{ \'/dashboard/\' | relative_url }}).',
    '- Sub-issues live in the implementation repo and are mirrored in the Requirement body\'s Sub-issues section.',
    '',
    `<small>Generated ${generatedAt} by \`scripts/generate-hub-data.mjs\`.</small>`,
    ''
  ].join('\n');
}

// --- Main -------------------------------------------------------------------

async function main() {
  const generatedAt = new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
  const [requirementIssues, projectIssues, names, queue, openPrs] = await Promise.all([
    listIssues(hubRepo, { state: 'all', labels: 'type:requirement' }),
    listIssues(hubRepo, { state: 'all', labels: 'type:project' }),
    projectNames(),
    buildQueue(),
    buildOpenPrs(),
  ]);

  const taskUrls = [...new Set(requirementIssues.flatMap((i) => extractWorkUrls(i.body || '')))];
  const taskEntries = await Promise.all(taskUrls.map(async (url) => [url, await fetchWorkUrl(url)]));
  const tasks = new Map(taskEntries.filter(([, v]) => v));

  const requirements = requirementIssues
    .sort((a, b) => (projectCode(a) || 'Pzzz').localeCompare(projectCode(b) || 'Pzzz') || a.number - b.number)
    .map((issue) => requirementRecord(issue, tasks));

  const openReqs = requirements.filter((r) => r.state === 'open');
  const byStatus = {};
  for (const r of openReqs) byStatus[r.status] = (byStatus[r.status] || 0) + 1;
  const statusTiles = [
    ['planned', '🕒'], ['in-progress', '🚧'], ['ready-review', '🙋'], ['blocked', '⛔'],
  ].map(([status, icon]) => ({ status, icon, count: byStatus[status] || 0 }));

  const dashboard = {
    generated_at: generatedAt,
    owner,
    hub_repo: hubRepo,
    extra_repos: extraRepos,
    reviewer,
    queue: queue.map(({ rank, ...rest }) => rest),
    open_prs: openPrs,
    requirements,
    counts: {
      queue: queue.length,
      open_prs: openPrs.filter((p) => !p.draft).length,
      draft_prs: openPrs.filter((p) => p.draft).length,
      open_requirements: openReqs.length,
      completed_requirements: requirements.length - openReqs.length,
      requirements_by_status: byStatus,
      status_tiles: statusTiles,
    },
  };

  await fsp.mkdir(path.join(root, '_data'), { recursive: true });
  await fsp.writeFile(path.join(root, '_data', 'dashboard.json'), JSON.stringify(dashboard, null, 2) + '\n');
  await fsp.writeFile(path.join(root, 'roadmap.md'), renderRoadmap({ requirements, projectIssues, names, generatedAt }));
  console.log(`Wrote roadmap.md and _data/dashboard.json (${requirements.length} requirements, queue ${queue.length}).`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
