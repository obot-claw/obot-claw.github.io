#!/usr/bin/env python3
"""Update public metrics for the hub dashboard.

Writes `_data/metrics.json`, rendered on /dashboard/ via Liquid. Metrics are
intentionally simple and reproducible:
- commits: unique git commits by project authors across in-scope public repos
- merged PRs: GitHub PRs by project authors merged in in-scope public repos
- lines of code: tracked text lines on each repo's default branch, excluding common binary/archive files
- releases: GitHub releases across in-scope public repos

Scope: public non-fork repos under OWNER plus EXTRA_REPOS (project repos that
live under other owners, e.g. jwildfire/safety.viz). Known undercount: work
inside the renderer staging forks is excluded by the non-fork filter.

Owner/authors are parameterized so the script survives the planned move to
jwildfire/obot.roadmap (set HUB_OWNER / HUB_AUTHORS / HUB_EXTRA_REPOS).
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

OWNER = os.environ.get("HUB_OWNER", "obot-claw")
# obot era commits/PRs are authored by obot-claw; Claude era work is authored by jwildfire
AUTHORS = [a for a in os.environ.get("HUB_AUTHORS", "obot-claw,jwildfire").split(",") if a]
EXTRA_REPOS = [r for r in os.environ.get("HUB_EXTRA_REPOS", "jwildfire/safety.viz").split(",") if r]
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "_data" / "metrics.json"
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
    return sorted(set(repos) | set(EXTRA_REPOS))


def count_merged_prs() -> int:
    total = 0
    owners = [OWNER] + sorted({r.split("/", 1)[0] for r in EXTRA_REPOS} - {OWNER})
    for repo_owner in owners:
        for author in AUTHORS:
            out = run([
                "gh", "search", "prs",
                "--owner", repo_owner,
                "--author", author,
                "--merged",
                "--json", "url",
                "--limit", "1000",
            ])
            prs = json.loads(out)
            if repo_owner == OWNER:
                total += len(prs)
            else:
                # Outside the hub owner, only count the explicitly in-scope repos.
                total += sum(1 for pr in prs if any(f"/{r}/" in pr["url"] for r in EXTRA_REPOS))
    return total


def is_text_countable(path: Path) -> bool:
    if path.suffix in BINARY_SUFFIXES:
        return False
    return path.is_file()


def repo_metrics(repo: str, base: Path) -> tuple[int, int, int]:
    dest = base / repo.replace("/", "__")
    run(["git", "clone", "--quiet", f"https://github.com/{repo}.git", str(dest)])

    commits = set()
    for author in AUTHORS:
        commits.update(run(["git", "log", "--all", f"--author={author}", "--format=%H"], cwd=dest).splitlines())

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


def build_metrics() -> dict[str, int | str | list[str]]:
    repos = get_repos()
    total_commits = total_loc = total_releases = 0
    with tempfile.TemporaryDirectory(prefix="obot-metrics-") as tmp:
        base = Path(tmp)
        for repo in repos:
            commits, loc, releases = repo_metrics(repo, base)
            total_commits += commits
            total_loc += loc
            total_releases += releases
    prs = count_merged_prs()
    return {
        "commits": total_commits,
        "prs": prs,
        "loc": total_loc,
        "releases": total_releases,
        # Pre-formatted for Liquid, which has no thousands-separator filter.
        "commits_fmt": f"{total_commits:,}",
        "prs_fmt": f"{prs:,}",
        "loc_fmt": f"{total_loc:,}",
        "releases_fmt": f"{total_releases:,}",
        "repos": repos,
        "updated": datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M %Z"),
    }


def main() -> None:
    metrics = build_metrics()
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(metrics, indent=2) + "\n")
    print(f"Wrote {OUT.relative_to(ROOT)}: {metrics['commits']} commits, "
          f"{metrics['prs']} merged PRs, {metrics['loc']} lines, {metrics['releases']} releases "
          f"across {len(metrics['repos'])} repos.")


if __name__ == "__main__":
    main()
