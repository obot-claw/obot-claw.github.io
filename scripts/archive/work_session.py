#!/usr/bin/env python3
"""Durable work-session ledger for PM/Development/Testing cycles.

The ledger is intentionally simple JSON so it can be used from OpenClaw,
cron, TaskFlow-style jobs, or a main-session fallback without depending on a
specific subagent runtime.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TERMINAL_STATES = {"completed", "failed", "stalled", "cancelled"}
NON_TERMINAL_STATES = {"planned", "active"}
ALL_STATES = TERMINAL_STATES | NON_TERMINAL_STATES
DEFAULT_LEDGER = Path(os.environ.get("WORK_SESSION_LEDGER", ".work-sessions/ledger.json"))


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def load_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "sessions": []}
    with path.open() as f:
        data = json.load(f)
    data.setdefault("version", 1)
    data.setdefault("sessions", [])
    return data


def save_ledger(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name, dir=str(path.parent))
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp_name, path)


def session_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def find_session(data: dict[str, Any], sid: str) -> dict[str, Any]:
    for session in data["sessions"]:
        if session["id"] == sid:
            return session
    raise SystemExit(f"No session found with id: {sid}")


def add_event(session: dict[str, Any], kind: str, note: str, evidence: list[str] | None = None) -> None:
    session.setdefault("events", []).append(
        {"time": utcnow(), "kind": kind, "note": note, "evidence": evidence or []}
    )
    session["updated_at"] = utcnow()


def classify(session: dict[str, Any], now: datetime | None = None) -> tuple[str, str]:
    state = session.get("state", "planned")
    if state in TERMINAL_STATES:
        return state, "terminal"
    checkpoint = parse_time(session.get("checkpoint_at"))
    if checkpoint and (now or datetime.now(timezone.utc)) > checkpoint:
        evidence = session.get("evidence", []) or []
        if not evidence:
            return "stalled", "checkpoint passed with no evidence"
        return state, "checkpoint passed; evidence exists but liveness must be rechecked"
    return state, "within checkpoint"


def cmd_start(args: argparse.Namespace) -> int:
    data = load_ledger(args.ledger)
    sid = args.id or session_id(args.role.lower())
    if any(s.get("id") == sid for s in data["sessions"]):
        raise SystemExit(f"Session already exists: {sid}")
    record = {
        "id": sid,
        "cycle": args.cycle,
        "role": args.role,
        "target": args.target,
        "state": args.state,
        "session_ref": args.session_ref,
        "started_at": utcnow(),
        "updated_at": utcnow(),
        "checkpoint_at": args.checkpoint,
        "liveness_method": args.liveness_method,
        "recovery_plan": args.recovery_plan,
        "evidence": args.evidence or [],
        "events": [],
    }
    add_event(record, "start", args.note or "session recorded", args.evidence)
    data["sessions"].append(record)
    save_ledger(args.ledger, data)
    print(sid)
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    data = load_ledger(args.ledger)
    session = find_session(data, args.id)
    if args.state:
        if args.state not in ALL_STATES:
            raise SystemExit(f"Invalid state: {args.state}")
        session["state"] = args.state
    if args.checkpoint:
        session["checkpoint_at"] = args.checkpoint
    if args.session_ref:
        session["session_ref"] = args.session_ref
    if args.evidence:
        session.setdefault("evidence", []).extend(args.evidence)
    add_event(session, args.event, args.note, args.evidence)
    save_ledger(args.ledger, data)
    print(f"{session['id']}: {session['state']}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    data = load_ledger(args.ledger)
    rows = []
    for session in data["sessions"]:
        effective, reason = classify(session)
        if args.open_only and effective in TERMINAL_STATES:
            continue
        rows.append((session, effective, reason))
    rows.sort(key=lambda row: row[0].get("updated_at", ""), reverse=True)
    if args.json:
        print(json.dumps([dict(r[0], effective_state=r[1], status_reason=r[2]) for r in rows], indent=2))
        return 0
    if not rows:
        print("No matching work sessions.")
        return 0
    for session, effective, reason in rows:
        print(f"{session['id']} | {effective} | {session.get('role')} | {session.get('target')}")
        print(f"  checkpoint: {session.get('checkpoint_at') or 'none'} | reason: {reason}")
        if session.get("session_ref"):
            print(f"  session_ref: {session['session_ref']}")
        if session.get("evidence"):
            print("  evidence: " + "; ".join(session["evidence"][-3:]))
        print(f"  recovery: {session.get('recovery_plan') or 'none'}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    data = load_ledger(args.ledger)
    groups: dict[str, list[dict[str, Any]]] = {state: [] for state in ["planned", "active", "stalled", "failed", "completed", "cancelled"]}
    for session in data["sessions"]:
        effective, reason = classify(session)
        item = dict(session)
        item["effective_state"] = effective
        item["status_reason"] = reason
        groups.setdefault(effective, []).append(item)
    print("# Work-session status\n")
    print(f"Generated: {utcnow()}\n")
    for state in ["active", "planned", "stalled", "failed", "completed", "cancelled"]:
        items = groups.get(state, [])
        print(f"## {state.title()} ({len(items)})")
        if not items:
            print("\nNone.\n")
            continue
        for item in items:
            print(f"- {item['id']} — {item.get('role')} — {item.get('target')}")
            print(f"  - reason: {item['status_reason']}")
            if item.get("evidence"):
                print(f"  - evidence: {'; '.join(item['evidence'][-3:])}")
            print(f"  - recovery: {item.get('recovery_plan') or 'none'}")
        print()
    return 0


def cmd_self_test(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory() as d:
        ledger = Path(d) / "ledger.json"
        start_args = argparse.Namespace(
            ledger=ledger,
            id="dev-test",
            cycle="self-test",
            role="Development",
            target="obot-claw.github.io #25",
            state="active",
            session_ref="main-session",
            checkpoint="2000-01-01T00:00:00Z",
            liveness_method="manual",
            recovery_plan="mark stalled and restart safely",
            evidence=[],
            note="self-test start",
        )
        cmd_start(start_args)
        data = load_ledger(ledger)
        effective, reason = classify(data["sessions"][0])
        assert effective == "stalled", (effective, reason)
        update_args = argparse.Namespace(
            ledger=ledger,
            id="dev-test",
            state="completed",
            checkpoint=None,
            session_ref=None,
            evidence=["self-test evidence"],
            event="complete",
            note="self-test complete",
        )
        cmd_update(update_args)
        data = load_ledger(ledger)
        effective, _ = classify(data["sessions"][0])
        assert effective == "completed", effective
    print("self-test passed")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage durable autonomous work-session ledger")
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER, help="ledger JSON path")
    sub = parser.add_subparsers(required=True)

    start = sub.add_parser("start", help="record a new work session")
    start.add_argument("--id")
    start.add_argument("--cycle", required=True)
    start.add_argument("--role", required=True, choices=["PM", "Development", "Testing", "Main", "Cron", "TaskFlow"])
    start.add_argument("--target", required=True)
    start.add_argument("--state", default="active", choices=sorted(NON_TERMINAL_STATES))
    start.add_argument("--session-ref", required=True, help="tool session id, cron id, main-session, or explicit fallback")
    start.add_argument("--checkpoint", required=True, help="ISO timestamp for first liveness check")
    start.add_argument("--liveness-method", required=True)
    start.add_argument("--recovery-plan", required=True)
    start.add_argument("--evidence", action="append")
    start.add_argument("--note")
    start.set_defaults(func=cmd_start)

    update = sub.add_parser("update", help="add evidence/event and optionally change state")
    update.add_argument("id")
    update.add_argument("--state", choices=sorted(ALL_STATES))
    update.add_argument("--checkpoint")
    update.add_argument("--session-ref")
    update.add_argument("--evidence", action="append")
    update.add_argument("--event", default="update")
    update.add_argument("--note", required=True)
    update.set_defaults(func=cmd_update)

    status = sub.add_parser("status", help="list current work sessions")
    status.add_argument("--open-only", action="store_true")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)

    report = sub.add_parser("report", help="print markdown status report")
    report.set_defaults(func=cmd_report)

    self_test = sub.add_parser("self-test", help="run built-in smoke test")
    self_test.set_defaults(func=cmd_self_test)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
