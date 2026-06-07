#!/usr/bin/env python3
"""Portfolio PM audit helper for obot-claw Hub work.

The helper is read-only. It emits findings for PM review before Development
cycles start. It intentionally avoids mutating GitHub state.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass
class Finding:
    level: str
    category: str
    artifact: str
    message: str
    classification: str


def run_json(cmd: list[str]) -> Any:
    try:
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.PIPE)
    except FileNotFoundError:
        raise RuntimeError(f"Required command not found: {cmd[0]}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{e.stderr.strip()}")
    return json.loads(out or "null")


def gh_issue_list(repo: str) -> list[dict[str, Any]]:
    """Return open issues with issueType when GraphQL exposes it.

    gh issue list does not currently expose issue type in --json fields, so use
    GraphQL for issueType and fall back to labels/title when issue types have
    not been migrated yet.
    """
    owner, name = repo.split("/", 1)
    query = """
    query($owner:String!, $repo:String!) {
      repository(owner:$owner, name:$repo) {
        issues(first:100, states:OPEN) {
          nodes {
            number
            title
            body
            url
            issueType { name }
            labels(first:50) { nodes { name } }
          }
        }
      }
    }
    """
    data = run_json(["gh", "api", "graphql", "-f", f"owner={owner}", "-f", f"repo={name}", "-f", f"query={query}"])
    nodes = data["data"]["repository"]["issues"]["nodes"]
    normalized = []
    for node in nodes:
        normalized.append({
            "number": node["number"],
            "title": node["title"],
            "body": node.get("body") or "",
            "url": node["url"],
            "issueType": (node.get("issueType") or {}).get("name"),
            "labels": node.get("labels", {}).get("nodes", []),
        })
    return normalized


def gh_pr_list(repo: str) -> list[dict[str, Any]]:
    return run_json([
        "gh", "pr", "list", "--repo", repo, "--state", "open", "--limit", "100",
        "--json", "number,title,body,labels,url,reviewDecision,isDraft",
    ])


def label_names(item: dict[str, Any]) -> set[str]:
    return {label["name"] for label in item.get("labels", [])}


def has_label_prefix(labels: set[str], prefix: str) -> bool:
    return any(label.startswith(prefix) for label in labels)


def issue_kind(issue: dict[str, Any], labels: set[str]) -> str | None:
    issue_type = issue.get("issueType")
    if issue_type in {"Project", "Requirement", "Task"}:
        return issue_type.lower()
    legacy = {"type:project": "project", "type:requirement": "requirement", "type:task": "task"}
    for label, kind in legacy.items():
        if label in labels:
            return kind
    title = issue.get("title", "")
    if title.startswith("Project:"):
        return "project"
    if title.startswith("Requirement:"):
        return "requirement"
    if title.startswith("Task:"):
        return "task"
    return None


def audit_issues(repo: str, issues: list[dict[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    for issue in issues:
        labels = label_names(issue)
        artifact = f"{repo} #{issue['number']}"
        kind = issue_kind(issue, labels)
        if not kind:
            findings.append(Finding("error", "issue-metadata", artifact, "cannot determine issue kind from Issue Type, legacy label, or title", "PM-fix-now"))
        if kind in {"project", "requirement"} and issue.get("issueType") != kind.title():
            findings.append(Finding("warning", "issue-type", artifact, f"{kind.title()} should use GitHub Issue Type instead of legacy type label/title fallback", "PM-fix-now"))
        if not has_label_prefix(labels, "project:"):
            findings.append(Finding("error", "issue-metadata", artifact, "missing project:* label", "PM-fix-now"))
        if not has_label_prefix(labels, "status:"):
            findings.append(Finding("error", "issue-metadata", artifact, "missing status:* label", "PM-fix-now"))
        body = issue.get("body") or ""
        if kind == "requirement" and "Parent Project" not in body and "Project" not in body:
            findings.append(Finding("warning", "issue-linkage", artifact, "requirement may lack parent Project reference", "PM-fix-now"))
        if kind == "task" and "Parent Requirement" not in body and "Requirement" not in body:
            findings.append(Finding("warning", "issue-linkage", artifact, "task may lack parent Requirement reference", "PM-fix-now"))
    return findings


def audit_prs(repo: str, prs: list[dict[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    issue_ref = re.compile(r"#\d+|issues/\d+|pull/\d+", re.I)
    for pr in prs:
        artifact = f"{repo} PR #{pr['number']}"
        body = pr.get("body") or ""
        if not issue_ref.search(body):
            findings.append(Finding("warning", "pr-linkage", artifact, "PR body does not reference a task/requirement issue", "PM-fix-now"))
        if pr.get("isDraft") and pr.get("reviewDecision") == "CHANGES_REQUESTED":
            findings.append(Finding("info", "pr-review", artifact, "draft PR has requested changes", "Development-handoff"))
    return findings


def audit_hub(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    script = root / "scripts" / "check_hub_sync.py"
    if not script.exists():
        findings.append(Finding("error", "hub-sync", "scripts/check_hub_sync.py", "Hub sync gate helper is missing", "Development-handoff"))
        return findings
    try:
        raw = subprocess.check_output([sys.executable, str(script), "--root", str(root), "--format", "json"], text=True)
        for item in json.loads(raw):
            classification = "PM-fix-now" if item["level"] == "error" else "PM-review"
            findings.append(Finding(item["level"], "hub-sync", item["check"], item["message"], classification))
    except subprocess.CalledProcessError as e:
        try:
            for item in json.loads(e.output or "[]"):
                classification = "PM-fix-now" if item["level"] == "error" else "PM-review"
                findings.append(Finding(item["level"], "hub-sync", item["check"], item["message"], classification))
        except Exception:
            findings.append(Finding("error", "hub-sync", "scripts/check_hub_sync.py", "Hub sync helper failed", "Development-handoff"))
    return findings


def audit_worktrees(path: Path | None) -> list[Finding]:
    if not path:
        return []
    findings: list[Finding] = []
    for repo in sorted(path.glob("**/.git")):
        root = repo.parent
        try:
            status = subprocess.check_output(["git", "-C", str(root), "status", "--short", "--branch"], text=True, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            continue
        dirty = [line for line in status.splitlines() if line and not line.startswith("##")]
        if dirty:
            findings.append(Finding("warning", "worktree", str(root), f"dirty worktree has {len(dirty)} changed/untracked entries", "Development-risk"))
    return findings


def markdown(findings: list[Finding]) -> str:
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.level] = counts.get(f.level, 0) + 1
    lines = ["# Portfolio PM audit", ""]
    if counts:
        lines.append("## Summary")
        for level in ["error", "warning", "info"]:
            lines.append(f"- {level}: {counts.get(level, 0)}")
    else:
        lines.extend(["## Summary", "- No findings."])
    lines.append("")
    lines.append("## Findings")
    if not findings:
        lines.append("No findings.")
    else:
        for f in findings:
            lines.append(f"- **{f.level}** `{f.category}` {f.artifact}: {f.message} _({f.classification})_")
    lines.append("")
    lines.append("## PM guidance")
    lines.append("- Fix `error` findings before launching Development.")
    lines.append("- Review `warning` findings and classify as PM-fix-now, Development-handoff, Testing-handoff, New-agent-needed, or Jeremy-decision.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run read-only PM portfolio audit")
    parser.add_argument("--repo", action="append", default=["obot-claw/obot-claw.github.io"], help="GitHub repo to audit; repeatable")
    parser.add_argument("--root", type=Path, default=Path("."), help="Hub repo root")
    parser.add_argument("--worktree-root", type=Path, help="optional local workspace root for dirty worktree scan")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    args = parser.parse_args()

    findings: list[Finding] = []
    for repo in args.repo:
        issues = gh_issue_list(repo)
        prs = gh_pr_list(repo)
        findings.extend(audit_issues(repo, issues))
        findings.extend(audit_prs(repo, prs))
    findings.extend(audit_hub(args.root))
    findings.extend(audit_worktrees(args.worktree_root))

    if args.format == "json":
        print(json.dumps([asdict(f) for f in findings], indent=2))
    else:
        print(markdown(findings))
    return 1 if any(f.level == "error" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
