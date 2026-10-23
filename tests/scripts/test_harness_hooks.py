"""Regression tests for the Claude Code hooks that spring-boot-team-harness adds to a project.

Run from the repository root:
    python3 -m unittest discover -s tests/scripts -v

The hooks are bash scripts. On Windows they run through Git for Windows, as in Claude Code; without bash the
tests are skipped.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[2] / (
    "plugins/springboot-architecture/skills/spring-boot-team-harness/assets/project/.claude/hooks")
BASH = shutil.which("bash")
MIGRATIONS = Path("src", "main", "resources", "db", "migration")


def git(root: Path, *args: str):
    subprocess.run(["git", "-c", "user.email=t@example.com", "-c", "user.name=t", *args], cwd=root, check=True,
                   capture_output=True)


@unittest.skipUnless(BASH, "bash not found")
class GuardHookTests(unittest.TestCase):

    def guard(self, payload: dict, project: Path | None = None) -> subprocess.CompletedProcess:
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(project or Path.cwd()))
        return subprocess.run([BASH, str(HOOKS / "guard.sh")], input=json.dumps(payload), capture_output=True,
                              text=True, env=env)

    def bash(self, command: str) -> subprocess.CompletedProcess:
        return self.guard({"tool_name": "Bash", "tool_input": {"command": command}})

    def test_blocks_destructive_git_commands(self):
        for command in ("git push --force origin main", "git push -f", "git reset --hard HEAD~1", "git clean -fd"):
            result = self.bash(command)
            self.assertEqual(result.returncode, 2, command)
            self.assertIn("Blocked by the team harness", result.stderr)

    def test_blocks_destructive_git_commands_with_quoted_arguments(self):
        for command in ('git -C "/workspace/project" reset --hard HEAD~1',
                        'git -C "/workspace/project" push --force origin main'):
            self.assertEqual(self.bash(command).returncode, 2, command)

    def test_allows_safe_git_and_build_commands(self):
        for command in ("git push --force-with-lease", "git push -u origin feature", "git reset HEAD file",
                        "./mvnw -q verify"):
            self.assertEqual(self.bash(command).returncode, 0, command)

    def test_blocks_edits_only_to_migrations_already_on_main(self):
        root = Path(tempfile.mkdtemp())
        (root / MIGRATIONS).mkdir(parents=True)
        git(root, "init", "-q", "-b", "main")
        (root / MIGRATIONS / "V1__orders.sql").write_text("create table orders (id bigint);\n")
        git(root, "add", "-A")
        git(root, "commit", "-qm", "orders")
        git(root, "switch", "-qc", "feature")
        (root / MIGRATIONS / "V2__lines.sql").write_text("create table lines (id bigint);\n")
        git(root, "add", "-A")
        git(root, "commit", "-qm", "lines")
        (root / MIGRATIONS / "V3__notes.sql").write_text("create table notes (id bigint);\n")

        def edit(name: str) -> subprocess.CompletedProcess:
            return self.guard({"tool_name": "Edit", "tool_input": {"file_path": str(root / MIGRATIONS / name)}}, root)

        on_main = edit("V1__orders.sql")
        self.assertEqual(on_main.returncode, 2)
        self.assertIn("Write a new migration", on_main.stderr)
        self.assertEqual(edit("V2__lines.sql").returncode, 0)
        self.assertEqual(edit("V3__notes.sql").returncode, 0)

    def test_ignores_other_files(self):
        result = self.guard({"tool_name": "Write", "tool_input": {"file_path": str(Path("src/main/java/A.java").resolve())}})
        self.assertEqual(result.returncode, 0)


FAKE_MVNW = """#!/usr/bin/env bash
echo "$*" >> mvnw.log
case "$*" in
  *spotless:apply*) [ -f fail-format ] && { echo "[ERROR] spotless failed"; exit 1; } ;;
  *test*) [ -f fail-tests ] && { echo "[ERROR] CodeRulesTests failed"; exit 1; } ;;
esac
exit 0
"""


@unittest.skipUnless(BASH, "bash not found")
class StopHookTests(unittest.TestCase):

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "src").mkdir()
        (self.root / "src" / "A.java").write_text("class A {}\n")
        (self.root / "pom.xml").write_text("<project/>\n")
        mvnw = self.root / "mvnw"
        mvnw.write_text(FAKE_MVNW, newline="\n")
        mvnw.chmod(0o755)
        (self.root / ".gitignore").write_text("mvnw.log\nfail-*\ntarget/\n")
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "start")

    def stop(self, active: bool = False) -> subprocess.CompletedProcess:
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.root))
        return subprocess.run([BASH, str(HOOKS / "verify-on-stop.sh")], input=json.dumps({"stop_hook_active": active}),
                              capture_output=True, text=True, env=env, cwd=self.root)

    def checks_run(self) -> int:
        log = self.root / "mvnw.log"
        return log.read_text().count(" test ") if log.exists() else 0

    def change(self, text: str):
        (self.root / "src" / "A.java").write_text(text)

    def test_committed_changes_are_still_checked(self):
        self.assertEqual(self.stop().returncode, 0)
        checked = self.checks_run()
        self.assertEqual(self.stop().returncode, 0)
        self.assertEqual(self.checks_run(), checked, "unchanged code is checked again")

        self.change("class A { int b; }\n")
        git(self.root, "commit", "-qam", "change")
        self.assertEqual(self.stop().returncode, 0)
        self.assertEqual(self.checks_run(), checked + 1, "a committed change was not checked")

    def test_failing_checks_block_and_are_not_recorded_as_passed(self):
        (self.root / "fail-tests").write_text("")
        self.change("class A { int b; }\n")
        result = self.stop()
        self.assertEqual(result.returncode, 2)
        self.assertIn("CodeRulesTests failed", result.stderr)
        self.assertEqual(self.stop(active=True).returncode, 0, "a second block on the same code would loop")

    def test_formatting_failure_blocks_and_is_not_recorded_as_passed(self):
        (self.root / "fail-format").write_text("")
        self.change("class A { int b; }\n")
        result = self.stop()
        self.assertEqual(result.returncode, 2)
        self.assertIn("spotless failed", result.stderr)

        (self.root / "fail-format").unlink()
        runs = self.checks_run()
        self.assertEqual(self.stop().returncode, 0)
        self.assertEqual(self.checks_run(), runs + 1, "the failed run was cached as a pass")


if __name__ == "__main__":
    unittest.main()
