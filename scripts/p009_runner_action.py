#!/usr/bin/env python3
"""Allowlisted P009 runner actions for OpenClaw/Telegram integration.

This wrapper intentionally exposes only safe runner actions. It never accepts an
arbitrary worker command from chat input.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_codex_cycle.py"
DEFAULT_RUNS_DIR = ROOT / ".codex-runs"


def iso_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run_cmd(args: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    return proc.returncode, proc.stdout, proc.stderr


def load_record(runs_dir: Path, run_id: str) -> dict[str, Any]:
    path = runs_dir / f"{run_id}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def safe_transcript_path(value: Any) -> Any:
    if not isinstance(value, str) or not value:
        return value
    path = Path(value)
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return path.name


def summarize_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": record.get("run_id"),
        "state": record.get("state"),
        "heartbeat_at": record.get("heartbeat_at"),
        "transcript": safe_transcript_path(record.get("transcript")),
        "exit_code": record.get("exit_code"),
        "effective_state": record.get("effective_state"),
        "status_reason": record.get("status_reason"),
    }


def summarize_records(records: list[dict[str, Any]], exit_code: int, include_records: bool = False) -> dict[str, Any]:
    alerts = [r.get("emitted_alert") for r in records if r.get("emitted_alert")]
    summary: dict[str, Any] = {
        "exit_code": exit_code,
        "records_checked": len(records),
        "newly_failed": len(alerts),
        "alerts": alerts,
    }
    if include_records:
        summary["records"] = [summarize_record(r) for r in records]
    return summary


def action_self_test(args: argparse.Namespace) -> int:
    runs_dir = args.runs_dir
    self_code, self_out, self_err = run_cmd([sys.executable, str(RUNNER), "self-test"])
    run_id = args.id or f"p009-self-test-{iso_stamp()}"
    run_code = 0
    run_out = ""
    run_err = ""
    if self_code == 0:
        run_code, run_out, run_err = run_cmd([
            sys.executable,
            str(RUNNER),
            "--runs-dir",
            str(runs_dir),
            "run",
            "--id",
            run_id,
            "--role",
            "PM",
            "--issue",
            "obot-claw/obot-claw.github.io#43",
            "--repo",
            "obot-claw/obot-claw.github.io",
            "--executor",
            "telegram-allowlisted-self-test",
            "--timeout",
            "10",
            "--heartbeat-interval",
            "1",
            "--write-scope",
            "none",
            "--artifact",
            "dry-run:allowlisted-self-test",
            "--recovery",
            "record failure and alert main obot",
            "--command",
            sys.executable,
            "-c",
            "print('allowlisted p009 self-test')",
        ])
    record = load_record(runs_dir, run_id)
    summary = {
        "action": "self-test",
        "command_status": "passed" if self_code == 0 and run_code == 0 else "failed",
        "self_test_exit_code": self_code,
        "exit_code": run_code if self_code == 0 else self_code,
        **summarize_record(record),
    }
    if args.debug:
        summary["debug_stdout"] = {"self_test": self_out, "run": run_out}
        summary["debug_stderr"] = {"self_test": self_err, "run": run_err}
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if self_code == 0 and run_code == 0 else 1


def action_status(args: argparse.Namespace) -> int:
    cmd = [sys.executable, str(RUNNER), "--runs-dir", str(args.runs_dir), "status", "--json"]
    if args.id:
        cmd.extend(["--id", args.id])
    code, out, err = run_cmd(cmd)
    records = json.loads(out or "[]") if code in (0, 1) else []
    summary = {"action": "status", **summarize_records(records, code, include_records=True)}
    if args.debug:
        summary["debug_stderr"] = err
    print(json.dumps(summary, indent=2, sort_keys=True))
    return code


def action_check(args: argparse.Namespace, mark_failed: bool) -> int:
    cmd = [sys.executable, str(RUNNER), "--runs-dir", str(args.runs_dir), "check", "--json"]
    if mark_failed:
        cmd.append("--mark-failed")
    if args.id:
        cmd.extend(["--id", args.id])
    code, out, err = run_cmd(cmd)
    records = json.loads(out or "[]") if code in (0, 1) else []
    summary = {"action": "check-mark-failed" if mark_failed else "check", **summarize_records(records, code)}
    if args.debug:
        summary["debug_stderr"] = err
    print(json.dumps(summary, indent=2, sort_keys=True))
    return code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run allowlisted P009 runner actions only")
    parser.add_argument("action", choices=["self-test", "status", "check", "check-mark-failed"])
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    parser.add_argument("--id", help="optional run id for self-test or status/check filtering")
    parser.add_argument("--debug", action="store_true", help="include captured stdout/stderr for local debugging only")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.runs_dir.mkdir(parents=True, exist_ok=True)
    if args.action == "self-test":
        return action_self_test(args)
    if args.action == "status":
        return action_status(args)
    if args.action == "check":
        return action_check(args, mark_failed=False)
    if args.action == "check-mark-failed":
        return action_check(args, mark_failed=True)
    raise AssertionError(args.action)


if __name__ == "__main__":
    raise SystemExit(main())
