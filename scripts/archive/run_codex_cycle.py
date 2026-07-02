#!/usr/bin/env python3
"""Supervise one Codex PM/Development/Testing work cycle.

This is the thin execution-layer scaffold for P009. It records the difference
between a triggered run, a started worker, a completed artifact, and a failed
run. It intentionally does not schedule work or choose portfolio targets.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

STATES = {"triggered", "started", "completed", "failed"}
TERMINAL_STATES = {"completed", "failed"}
DEFAULT_RUNS_DIR = Path(os.environ.get("CODEX_RUNS_DIR", ".codex-runs"))
DEFAULT_TRIGGER_GRACE_SECONDS = 60


def utcnow_dt() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def utcnow() -> str:
    return utcnow_dt().isoformat().replace("+00:00", "Z")


def run_id(role: str) -> str:
    stamp = utcnow_dt().strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{role.lower()}-{uuid.uuid4().hex[:8]}"


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name, dir=str(path.parent))
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp_name, path)


def load_json(path: Path) -> dict[str, Any]:
    with path.open() as f:
        return json.load(f)


def append_log(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(f"{utcnow()} {line}\n")


def record_path(runs_dir: Path, rid: str) -> Path:
    return runs_dir / f"{rid}.json"


def transcript_path(runs_dir: Path, rid: str) -> Path:
    return runs_dir / f"{rid}.log"


def base_record(args: argparse.Namespace, rid: str) -> dict[str, Any]:
    log_path = transcript_path(args.runs_dir, rid)
    now = utcnow()
    return {
        "version": 1,
        "run_id": rid,
        "role": args.role,
        "target_issue": args.issue,
        "repo": args.repo,
        "executor": args.executor,
        "command": None,
        "write_scope": args.write_scope,
        "prompt_template": str(args.prompt_template) if args.prompt_template else None,
        "state": "triggered",
        "triggered_at": now,
        "started_at": None,
        "completed_at": None,
        "heartbeat_at": None,
        "deadline_at": None,
        "trigger_grace_seconds": DEFAULT_TRIGGER_GRACE_SECONDS,
        "heartbeat_interval_seconds": args.heartbeat_interval,
        "timeout_seconds": args.timeout,
        "pid": None,
        "exit_code": None,
        "artifact": args.artifact,
        "transcript": str(log_path),
        "failure_reason": None,
        "recovery": args.recovery,
    }


def mark_failed(record: dict[str, Any], reason: str, exit_code: int | None = None) -> None:
    record["state"] = "failed"
    record["completed_at"] = utcnow()
    record["failure_reason"] = reason
    if exit_code is not None:
        record["exit_code"] = exit_code


def command_from_args(args: argparse.Namespace) -> list[str]:
    if args.command:
        return args.command
    if args.prompt_template:
        return ["codex", "exec", args.prompt_template.read_text()]
    return ["codex", "exec"]


def alert_text(record: dict[str, Any], reason: str) -> str:
    target = record.get("target_issue") or "unknown-target"
    run = record.get("run_id") or "unknown-run"
    role = record.get("role") or "unknown-role"
    text = f"P009 run failed: {run} {role} {target} - {reason}"
    return text[:497] + "..." if len(text) > 500 else text


def cmd_run(args: argparse.Namespace) -> int:
    rid = args.id or run_id(args.role)
    rpath = record_path(args.runs_dir, rid)
    if rpath.exists():
        raise SystemExit(f"Run record already exists: {rpath}")

    record = base_record(args, rid)
    save_json(rpath, record)
    append_log(Path(record["transcript"]), "triggered")

    command = command_from_args(args)
    record["command"] = shlex.join(command)
    save_json(rpath, record)
    append_log(Path(record["transcript"]), "launch " + shlex.join(command))
    try:
        with Path(record["transcript"]).open("a") as log:
            proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, text=True)
    except FileNotFoundError as e:
        mark_failed(record, f"executor not found: {e.filename}")
        save_json(rpath, record)
        append_log(Path(record["transcript"]), f"failed {record['failure_reason']}")
        print(str(rpath))
        return 1

    now = utcnow_dt()
    record["state"] = "started"
    record["started_at"] = now.isoformat().replace("+00:00", "Z")
    record["heartbeat_at"] = record["started_at"]
    record["deadline_at"] = (now + timedelta(seconds=args.timeout)).isoformat().replace("+00:00", "Z")
    record["pid"] = proc.pid
    save_json(rpath, record)
    append_log(Path(record["transcript"]), f"started pid={proc.pid}")

    deadline = time.monotonic() + args.timeout
    while True:
        exit_code = proc.poll()
        if exit_code is not None:
            record["exit_code"] = exit_code
            if exit_code == 0:
                record["state"] = "completed"
                record["completed_at"] = utcnow()
                record["heartbeat_at"] = record["completed_at"]
                append_log(Path(record["transcript"]), "completed")
                save_json(rpath, record)
                print(str(rpath))
                return 0
            mark_failed(record, f"worker exited with code {exit_code}", exit_code)
            append_log(Path(record["transcript"]), f"failed {record['failure_reason']}")
            save_json(rpath, record)
            print(str(rpath))
            return exit_code or 1

        if time.monotonic() > deadline:
            proc.kill()
            proc.wait()
            mark_failed(record, f"timeout after {args.timeout} seconds", proc.returncode)
            append_log(Path(record["transcript"]), f"failed {record['failure_reason']}")
            save_json(rpath, record)
            print(str(rpath))
            return 124

        record["heartbeat_at"] = utcnow()
        save_json(rpath, record)
        append_log(Path(record["transcript"]), "heartbeat")
        time.sleep(args.heartbeat_interval)


def classify_record(record: dict[str, Any], now: datetime | None = None) -> tuple[str, str]:
    state = record.get("state")
    if state not in STATES:
        return "failed", f"invalid state: {state}"
    if state in TERMINAL_STATES:
        return state, "terminal"

    current = now or utcnow_dt()
    started_at = parse_time(record.get("started_at"))
    heartbeat_at = parse_time(record.get("heartbeat_at"))
    deadline_at = parse_time(record.get("deadline_at"))
    triggered_at = parse_time(record.get("triggered_at"))

    if state == "triggered":
        if triggered_at and current - triggered_at > timedelta(seconds=record.get("trigger_grace_seconds", DEFAULT_TRIGGER_GRACE_SECONDS)):
            return "failed", "triggered run never reached started"
        return "triggered", "waiting for worker start"

    if state == "started":
        if deadline_at and current > deadline_at:
            return "failed", "started run passed deadline"
        if heartbeat_at and current - heartbeat_at > timedelta(seconds=record.get("heartbeat_interval_seconds", 30) * 2 + 5):
            return "failed", "started run heartbeat is stale"
        if not started_at or not heartbeat_at:
            return "failed", "started run lacks liveness timestamps"
        return "started", "worker live"

    return state, "ok"


def check_record(path: Path, mark: bool) -> tuple[dict[str, Any], str, str, str | None]:
    record = load_json(path)
    effective, reason = classify_record(record)
    alert = None
    if mark and effective == "failed" and record.get("state") not in TERMINAL_STATES:
        mark_failed(record, reason)
        record["alert"] = alert_text(record, reason)
        save_json(path, record)
        append_log(Path(record["transcript"]), f"watchdog failed {reason}")
        alert = record["alert"]
    return record, effective, reason, alert


def cmd_status(args: argparse.Namespace) -> int:
    paths = sorted(args.runs_dir.glob("*.json"))
    if args.id:
        paths = [record_path(args.runs_dir, args.id)]
    rows = []
    for path in paths:
        if not path.exists():
            continue
        record = load_json(path)
        effective, reason = classify_record(record)
        if args.open_only and effective in TERMINAL_STATES:
            continue
        rows.append((record, effective, reason))

    if args.json:
        print(json.dumps([dict(r, effective_state=state, status_reason=reason) for r, state, reason in rows], indent=2))
        return 0

    if not rows:
        print("No matching Codex cycle runs.")
        return 0

    for record, effective, reason in rows:
        print(f"{record['run_id']} | {effective} | {record.get('role')} | {record.get('target_issue')}")
        print(f"  heartbeat: {record.get('heartbeat_at') or 'none'} | reason: {reason}")
        print(f"  transcript: {record.get('transcript')}")
        if record.get("artifact"):
            print(f"  artifact: {record['artifact']}")
        if record.get("failure_reason"):
            print(f"  failure: {record['failure_reason']}")
        print(f"  recovery: {record.get('recovery') or 'none'}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    paths = sorted(args.runs_dir.glob("*.json"))
    if args.id:
        paths = [record_path(args.runs_dir, args.id)]

    rows = []
    failures_to_report = 0
    for path in paths:
        if not path.exists():
            continue
        record, effective, reason, alert = check_record(path, args.mark_failed)
        if effective == "failed" and (not args.mark_failed or alert):
            failures_to_report += 1
        rows.append((record, effective, reason, alert))

    if args.json:
        print(json.dumps([
            dict(record, effective_state=effective, status_reason=reason, emitted_alert=alert)
            for record, effective, reason, alert in rows
        ], indent=2))
        return 1 if failures_to_report else 0

    if not rows:
        print("No matching Codex cycle runs.")
        return 0

    for record, effective, reason, alert in rows:
        print(f"{record['run_id']} | {effective} | {record.get('role')} | {record.get('target_issue')}")
        print(f"  reason: {reason}")
        if alert:
            print(f"  alert: {alert}")
    return 1 if failures_to_report else 0


def cmd_self_test(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory() as d:
        runs_dir = Path(d) / "runs"
        run_args = argparse.Namespace(
            id="self-test-pm",
            role="PM",
            issue="obot-claw/obot-claw.github.io#38",
            repo="obot-claw/obot-claw.github.io",
            executor="self-test",
            write_scope="none",
            prompt_template=None,
            command=[sys.executable, "-c", "print('dry run artifact')"],
            timeout=10,
            heartbeat_interval=1,
            artifact="dry-run:self-test",
            recovery="record failure and alert main obot",
            runs_dir=runs_dir,
        )
        code = cmd_run(run_args)
        assert code == 0, code
        record = load_json(record_path(runs_dir, "self-test-pm"))
        assert record["state"] == "completed", record
        assert record["heartbeat_at"], record
        assert Path(record["transcript"]).exists(), record["transcript"]

        stale = dict(record)
        stale.update({
            "run_id": "self-test-stale",
            "state": "started",
            "started_at": "2000-01-01T00:00:00Z",
            "heartbeat_at": "2000-01-01T00:00:00Z",
            "deadline_at": "2000-01-01T00:00:05Z",
        })
        effective, reason = classify_record(stale)
        assert effective == "failed", (effective, reason)
    print("self-test passed")
    return 0


def cmd_failure_test(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory() as d:
        runs_dir = Path(d) / "runs"
        triggered = {
            "version": 1,
            "run_id": "failure-triggered",
            "role": "PM",
            "target_issue": "obot-claw/obot-claw.github.io#39",
            "repo": "obot-claw/obot-claw.github.io",
            "executor": "failure-test",
            "command": "not-started",
            "write_scope": "none",
            "prompt_template": None,
            "state": "triggered",
            "triggered_at": "2000-01-01T00:00:00Z",
            "started_at": None,
            "completed_at": None,
            "heartbeat_at": None,
            "deadline_at": None,
            "trigger_grace_seconds": 1,
            "heartbeat_interval_seconds": 1,
            "timeout_seconds": 10,
            "pid": None,
            "exit_code": None,
            "artifact": None,
            "transcript": str(transcript_path(runs_dir, "failure-triggered")),
            "failure_reason": None,
            "recovery": "alert main obot and do not claim active work",
        }
        stale = dict(triggered)
        stale.update({
            "run_id": "failure-stale",
            "state": "started",
            "triggered_at": "2000-01-01T00:00:00Z",
            "started_at": "2000-01-01T00:00:01Z",
            "heartbeat_at": "2000-01-01T00:00:02Z",
            "deadline_at": "2000-01-01T00:00:03Z",
            "transcript": str(transcript_path(runs_dir, "failure-stale")),
        })
        save_json(record_path(runs_dir, "failure-triggered"), triggered)
        save_json(record_path(runs_dir, "failure-stale"), stale)

        check_args = argparse.Namespace(runs_dir=runs_dir, id=None, mark_failed=True, json=True)
        code = cmd_check(check_args)
        assert code == 1, code
        checked_triggered = load_json(record_path(runs_dir, "failure-triggered"))
        checked_stale = load_json(record_path(runs_dir, "failure-stale"))
        assert checked_triggered["state"] == "failed", checked_triggered
        assert checked_triggered["failure_reason"] == "triggered run never reached started", checked_triggered
        assert checked_stale["state"] == "failed", checked_stale
        assert checked_stale["failure_reason"] == "started run passed deadline", checked_stale
        assert len(checked_triggered["alert"]) <= 500, checked_triggered["alert"]
        assert len(checked_stale["alert"]) <= 500, checked_stale["alert"]
        _, repeat_triggered_effective, _, repeat_triggered_alert = check_record(
            record_path(runs_dir, "failure-triggered"), mark=True
        )
        _, repeat_stale_effective, _, repeat_stale_alert = check_record(
            record_path(runs_dir, "failure-stale"), mark=True
        )
        assert repeat_triggered_effective == "failed", repeat_triggered_effective
        assert repeat_stale_effective == "failed", repeat_stale_effective
        assert repeat_triggered_alert is None, repeat_triggered_alert
        assert repeat_stale_alert is None, repeat_stale_alert
    print("failure-test passed")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one supervised Codex cycle")
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR, help="directory for run records and transcripts")
    sub = parser.add_subparsers(required=True)

    run = sub.add_parser("run", help="run a supervised worker process")
    run.add_argument("--id", help="optional stable run id")
    run.add_argument("--role", required=True, choices=["PM", "Development", "Testing"])
    run.add_argument("--issue", required=True, help="target issue, e.g. obot-claw/obot-claw.github.io#38")
    run.add_argument("--repo", required=True, help="repository under work")
    run.add_argument("--executor", default="codex-local", help="executor label stored in the run record")
    run.add_argument("--timeout", type=int, default=900, help="worker timeout in seconds")
    run.add_argument("--heartbeat-interval", type=int, default=30, help="heartbeat interval in seconds")
    run.add_argument("--prompt-template", type=Path, help="prompt template passed to codex exec when --command is omitted")
    run.add_argument("--write-scope", default="none", help="declared write scope, e.g. none, docs-only, public-repo")
    run.add_argument("--artifact", help="expected or produced artifact link/path")
    run.add_argument("--recovery", required=True, help="what main obot/watchdog should do on failure")
    run.add_argument("--command", nargs=argparse.REMAINDER, help="worker command for dry runs/tests; defaults to codex exec")
    run.set_defaults(func=cmd_run)

    status = sub.add_parser("status", help="show run-record status")
    status.add_argument("--id")
    status.add_argument("--open-only", action="store_true")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)

    check = sub.add_parser("check", help="watchdog check for failed/stale run records")
    check.add_argument("--id")
    check.add_argument("--mark-failed", action="store_true", help="write failed state, failure_reason, and alert for detected failures")
    check.add_argument("--json", action="store_true")
    check.set_defaults(func=cmd_check)

    self_test = sub.add_parser("self-test", help="run built-in smoke test")
    self_test.set_defaults(func=cmd_self_test)

    failure_test = sub.add_parser("failure-test", help="run triggered/stale failure-injection test")
    failure_test.set_defaults(func=cmd_failure_test)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if hasattr(args, "heartbeat_interval") and args.heartbeat_interval < 1:
        raise SystemExit("--heartbeat-interval must be >= 1")
    if hasattr(args, "timeout") and args.timeout < 1:
        raise SystemExit("--timeout must be >= 1")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
