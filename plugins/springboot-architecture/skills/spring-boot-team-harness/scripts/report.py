#!/usr/bin/env python3
"""Summarise what the harness hooks did in this clone: how often the Stop hook checked, passed or blocked a turn,
which gates fired, how long checks took, and what the guard refused.

Usage:
    python3 report.py <project-dir> [--days 30] [--json]

The hooks append one line per run to .git/harness/events.jsonl. The file is local to each clone and holds no paths,
commands or file contents, so each developer runs the report on their own clone, or a team ships the files to a log
store of its own.
"""

import argparse
import json
import statistics
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

CHECKED = ("passed", "blocked", "unverified")
SKIPPED = ("no-change", "already-passed", "gave-up")


def events_file(project: Path) -> Path:
    result = subprocess.run(["git", "-C", str(project), "rev-parse", "--absolute-git-dir"], capture_output=True,
                            text=True)
    if result.returncode != 0:
        sys.exit(f"ERROR: {project} is not in a git repository.")
    return Path(result.stdout.strip()) / "harness" / "events.jsonl"


def load(path: Path, days: int | None) -> list[dict]:
    if not path.exists():
        return []
    since = datetime.now(timezone.utc) - timedelta(days=days) if days else None
    events = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
            when = datetime.strptime(event["ts"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except (ValueError, KeyError, TypeError):
            continue
        if since is None or when >= since:
            events.append(event)
    return events


def summarise(events: list[dict]) -> dict:
    stop = [e for e in events if e.get("hook") == "stop"]
    guard = [e for e in events if e.get("hook") == "guard"]
    results = Counter(e.get("result") for e in stop)
    checked = [e for e in stop if e.get("result") in CHECKED]
    seconds = sorted(e.get("seconds", 0) for e in checked)
    gates = Counter(gate for e in stop if e.get("result") == "blocked"
                    for gate in (e.get("gates") or "unknown").split(","))
    unverified_gates = Counter(gate for e in stop if e.get("result") == "unverified"
                               for gate in (e.get("gates") or "unknown").split(","))

    # A block counts as fixed when the same session's next check passes.
    fixed = 0
    by_session: dict[str, list[dict]] = {}
    for event in checked:
        by_session.setdefault(event.get("session", ""), []).append(event)
    for runs in by_session.values():
        fixed += sum(1 for run, after in zip(runs, runs[1:])
                     if run["result"] == "blocked" and after["result"] == "passed")

    return {
        "sessions": len({e.get("session") for e in stop if e.get("session") not in (None, "", "unknown")}),
        "turns": sum(results[r] for r in CHECKED + SKIPPED),
        "checked": len(checked),
        "results": {r: results[r] for r in CHECKED + SKIPPED},
        "blocked_by_gate": dict(gates.most_common()),
        "fixed_after_block": fixed,
        "unverified_by_gate": dict(unverified_gates.most_common()),
        "check_seconds": {
            "median": statistics.median(seconds) if seconds else None,
            "p90": seconds[min(len(seconds) - 1, int(len(seconds) * 0.9))] if seconds else None,
            "total": sum(seconds),
        },
        "guard_refused": dict(Counter(e.get("rule", "unknown") for e in guard).most_common()),
    }


def text(summary: dict, days: int | None) -> str:
    r = summary["results"]
    window = f"last {days} days" if days else "all recorded events"
    lines = [f"Harness hooks, {window}: {summary['sessions']} sessions, {summary['turns']} turns ended"]
    if not summary["turns"] and not summary["guard_refused"]:
        return lines[0] + "\nNothing recorded yet. The hooks write events once a Claude Code session runs here."
    lines.append(f"  Stop hook checked {summary['checked']} turns: {r['passed']} passed, {r['blocked']} blocked, "
                 f"{r['unverified']} could not be fully verified (failures only in unchanged code)")
    lines.append(f"  Skipped {r['no-change'] + r['already-passed']} turns: {r['no-change']} changed no code, "
                 f"{r['already-passed']} on code that had already passed")
    if r["blocked"]:
        gates = ", ".join(f"{gate} {n}" for gate, n in summary["blocked_by_gate"].items())
        lines.append(f"  Blocks by gate: {gates}")
        lines.append(f"  Fixed by the agent after a block: {summary['fixed_after_block']} of {r['blocked']}; "
                     f"gave up after one retry: {r['gave-up']}")
    if summary["unverified_by_gate"]:
        gates = ", ".join(f"{gate} {n}" for gate, n in summary["unverified_by_gate"].items())
        lines.append(f"  Unverified turns by gate: {gates}")
    s = summary["check_seconds"]
    if s["median"] is not None:
        lines.append(f"  Check time: median {s['median']:.0f} s, p90 {s['p90']} s, {s['total'] / 60:.0f} min in total")
    if summary["guard_refused"]:
        rules = ", ".join(f"{rule} {n}" for rule, n in summary["guard_refused"].items())
        lines.append(f"  Guard refused: {rules}")
    else:
        lines.append("  Guard refused nothing")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument("--days", type=int, default=30, help="Only events from the last N days (0 for all)")
    parser.add_argument("--json", action="store_true", help="Print the summary as JSON")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    days = args.days or None
    summary = summarise(load(events_file(Path(args.project).resolve()), days))
    print(json.dumps(summary, indent=2) if args.json else text(summary, days))


if __name__ == "__main__":
    main()
