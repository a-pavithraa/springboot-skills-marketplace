"""Regression tests for spring-boot-team-harness/scripts/report.py.

Run from the repository root:
    python3 -m unittest discover -s tests/scripts -v
"""

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / (
    "plugins/springboot-architecture/skills/spring-boot-team-harness/scripts/report.py")


def stop(result: str, session: str = "s1", gates: str = "", seconds: int = 0, ago_days: int = 0) -> dict:
    ts = (datetime.now(timezone.utc) - timedelta(days=ago_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"ts": ts, "hook": "stop", "session": session, "result": result, "gates": gates, "seconds": seconds,
            "files": 1}


class ReportTests(unittest.TestCase):

    def project(self, events: list[dict], extra: str = "") -> Path:
        root = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        log = root / ".git/harness/events.jsonl"
        log.parent.mkdir(parents=True)
        log.write_text("".join(json.dumps(e) + "\n" for e in events) + extra)
        return root

    def report(self, root: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPT), str(root), *args], capture_output=True, text=True,
                              encoding="utf-8")

    def summary(self, root: Path, *args: str) -> dict:
        return json.loads(self.report(root, "--json", *args).stdout)

    def test_counts_checks_blocks_by_gate_and_fixes(self):
        root = self.project([
            stop("started"), stop("no-change"), stop("blocked", gates="nullaway,rules", seconds=40),
            stop("passed", seconds=30), stop("already-passed"),
            stop("started", "s2"), stop("blocked", "s2", "nullaway", 50), stop("gave-up", "s2"),
            stop("unverified", "s2", "compile", 20),
            {"ts": stop("x")["ts"], "hook": "guard", "session": "s2", "result": "refused", "rule": "force-push"},
        ])
        summary = self.summary(root)
        self.assertEqual(summary["sessions"], 2)
        self.assertEqual(summary["checked"], 4)
        self.assertEqual(summary["turns"], 7)
        self.assertEqual(summary["blocked_by_gate"], {"nullaway": 2, "rules": 1})
        self.assertEqual(summary["fixed_after_block"], 1)
        self.assertEqual(summary["unverified_by_gate"], {"compile": 1})
        self.assertEqual(summary["check_seconds"]["median"], 35)
        self.assertEqual(summary["guard_refused"], {"force-push": 1})
        text = self.report(root).stdout
        self.assertIn("4 turns: 1 passed, 2 blocked, 1 could not be fully verified", text)
        self.assertIn("Fixed by the agent after a block: 1 of 2", text)

    def test_old_events_are_left_out_unless_asked_for(self):
        root = self.project([stop("passed", ago_days=40), stop("passed")])
        self.assertEqual(self.summary(root)["checked"], 1)
        self.assertEqual(self.summary(root, "--days", "0")["checked"], 2)

    def test_damaged_lines_are_skipped(self):
        root = self.project([stop("passed")], extra='{"ts": "not a time"}\nnot json\n')
        self.assertEqual(self.summary(root)["checked"], 1)

    def test_says_so_when_nothing_is_recorded(self):
        root = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        result = self.report(root)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Nothing recorded yet", result.stdout)


if __name__ == "__main__":
    unittest.main()
