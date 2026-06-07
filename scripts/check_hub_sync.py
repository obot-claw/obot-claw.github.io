#!/usr/bin/env python3
"""Validate Hub-facing project tracking conventions.

This is intentionally lightweight: it catches drift that is visible in the
public Hub before PM/Development cycles start.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Finding:
    level: str
    check: str
    message: str


def section(text: str, heading: str, next_heading: str) -> str:
    start = text.find(heading)
    if start == -1:
        return ""
    end = text.find(next_heading, start + len(heading))
    return text[start:] if end == -1 else text[start:end]


def check_hub(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    index = root / "index.md"
    agents = root / "agents.md"
    roadmap = root / "roadmap.md"

    if not index.exists():
        return [Finding("error", "homepage", "index.md is missing")]
    index_text = index.read_text()

    if not agents.exists():
        findings.append(Finding("error", "agent-overview", "agents.md is missing"))
    if '/agents/' not in index_text:
        findings.append(Finding("error", "agent-overview", "homepage does not link to /agents/"))
    if not roadmap.exists():
        findings.append(Finding("error", "roadmap", "roadmap.md is missing"))
    if 'roadmap' not in index_text.lower():
        findings.append(Finding("warning", "roadmap", "homepage does not visibly reference roadmap"))

    todo = section(index_text, "## 🙋 ToDo", "## Agents")
    if not todo:
        findings.append(Finding("warning", "human-todo", "homepage has no 🙋 ToDo section"))
    items = re.findall(r"<li>(.*?)</li>", todo, flags=re.S)
    for i, item in enumerate(items, start=1):
        compact = re.sub(r"\s+", " ", item).strip()
        repo_link = re.search(r'href="https://github\.com/obot-claw/[^"/]+"', item)
        issue_link = re.search(r'href="https://github\.com/obot-claw/[^" ]+/(?:issues|pull)/\d+"', item)
        issue_text = re.search(r">#\d+</a>", item)
        if not repo_link:
            findings.append(Finding("error", "human-todo", f"ToDo {i} is missing linked obot-claw repo: {compact}"))
        if not issue_link or not issue_text:
            findings.append(Finding("error", "human-todo", f"ToDo {i} is missing linked issue/PR number: {compact}"))
        if "@jwildfire" not in item:
            findings.append(Finding("error", "human-todo", f"ToDo {i} lacks explicit @jwildfire instruction: {compact}"))

    human_todo = os.environ.get("HUMAN_TODO_PATH")
    if human_todo:
        path = Path(human_todo)
        if not path.exists():
            findings.append(Finding("warning", "human-todo-file", f"HUMAN_TODO_PATH not found: {path}"))
        else:
            bad = []
            for line in path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "github.com/obot-claw/" not in line or " - " not in line:
                    bad.append(line)
            if bad:
                findings.append(Finding("warning", "human-todo-file", f"HUMAN_TODO.md has {len(bad)} lines not in linked repo/issue format"))

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Hub sync conventions")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    findings = check_hub(args.root)
    if args.format == "json":
        print(json.dumps([asdict(f) for f in findings], indent=2))
    elif findings:
        for f in findings:
            print(f"{f.level.upper()} [{f.check}] {f.message}")
    else:
        print("Hub sync gate passed")

    return 1 if any(f.level == "error" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
