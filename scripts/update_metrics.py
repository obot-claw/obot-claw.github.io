#!/usr/bin/env python3
"""Update homepage public metrics for obot-claw repositories.

Metrics are intentionally simple and reproducible:
- commits: unique git commits authored by obot-claw across public obot-claw repos
- merged PRs: GitHub PRs authored by obot-claw and merged under the obot-claw owner
- lines of code: tracked text lines on each repo's default branch, excluding common binary/archive files
- releases: GitHub releases across public obot-claw repos
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

OWNER = "obot-claw"
AUTHOR = "obot-claw"
ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.md"
START = "<!-- metrics:start -->"
END = "<!-- metrics:end -->"
BINARY_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".pdf", ".docx",
    ".gz", ".zip", ".rds", ".rda", ".RData", ".sqlite", ".db",
}


def run(cmd: list[str], cwd: Path | None = None) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True).strip()


def gh_json(args: list[str]):
    return json.loads(run(["gh", "api", *args]))


def get_repos() -> list[str]:
    repos = []
    page = 1
    while True:
        data = gh_json([f"users/{OWNER}/repos?per_page=100&page={page}"])
        if not data:
            break
        repos.extend(repo["full_name"] for repo in data if not repo.get("fork"))
        page += 1
    return sorted(repos)


def count_merged_prs() -> int:
    out = run([
        "gh", "search", "prs",
        "--owner", OWNER,
        "--author", AUTHOR,
        "--merged",
        "--json", "url",
        "--limit", "1000",
    ])
    return len(json.loads(out))


def is_text_countable(path: Path) -> bool:
    if path.suffix in BINARY_SUFFIXES:
        return False
    return path.is_file()


def repo_metrics(repo: str, base: Path) -> tuple[int, int, int]:
    name = repo.split("/", 1)[1]
    dest = base / name
    run(["git", "clone", "--quiet", f"https://github.com/{repo}.git", str(dest)])

    commits = set(run(["git", "log", "--all", f"--author={AUTHOR}", "--format=%H"], cwd=dest).splitlines())

    files = run(["git", "ls-files"], cwd=dest).splitlines()
    loc = 0
    for filename in files:
        path = dest / filename
        if not is_text_countable(path):
            continue
        try:
            text = path.read_text(errors="ignore")
        except Exception:
            continue
        loc += text.count("\n") + (1 if text and not text.endswith("\n") else 0)

    releases = len(gh_json([f"repos/{repo}/releases"]))
    return len(commits), loc, releases


def build_metrics() -> dict[str, int | str]:
    repos = get_repos()
    total_commits = total_loc = total_releases = 0
    with tempfile.TemporaryDirectory(prefix="obot-metrics-") as tmp:
        base = Path(tmp)
        for repo in repos:
            commits, loc, releases = repo_metrics(repo, base)
            total_commits += commits
            total_loc += loc
            total_releases += releases
    return {
        "commits": total_commits,
        "prs": count_merged_prs(),
        "loc": total_loc,
        "releases": total_releases,
        "updated": datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M %Z"),
    }


def render(metrics: dict[str, int | str]) -> str:
    return f"""{START}
## Metrics

Updated nightly with the daily briefing. Scope: public `obot-claw` repositories.

<ul class="metric-list">
  <li><strong>{metrics['commits']:,}</strong><span>commits made</span></li>
  <li><strong>{metrics['prs']:,}</strong><span>PRs merged</span></li>
  <li><strong>{metrics['loc']:,}</strong><span>tracked text lines</span></li>
  <li><strong>{metrics['releases']:,}</strong><span>releases</span></li>
</ul>

<small>Last updated: {metrics['updated']}</small>
{END}"""


def main() -> None:
    metrics = build_metrics()
    text = INDEX.read_text()
    block = render(metrics)
    if START in text and END in text:
        before = text.split(START, 1)[0]
        after = text.split(END, 1)[1]
        text = before + block + after
    else:
        insert_after = "Public daily diary and project reporting for Open Source OrangeBot work.\n"
        text = text.replace(insert_after, insert_after + "\n\n" + block + "\n", 1)
    INDEX.write_text(text)


if __name__ == "__main__":
    main()
