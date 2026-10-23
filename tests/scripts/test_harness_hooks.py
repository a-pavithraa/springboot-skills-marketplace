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

    def test_blocks_edits_to_the_archunit_freeze_record(self):
        record = Path("src/test/resources/archunit_store/stored.rules").resolve()
        for tool in ("Edit", "Write"):
            result = self.guard({"tool_name": tool, "tool_input": {"file_path": str(record)}})
            self.assertEqual(result.returncode, 2, tool)
            self.assertIn("frozen", result.stderr)

    def test_ignores_other_files(self):
        result = self.guard({"tool_name": "Write", "tool_input": {"file_path": str(Path("src/main/java/A.java").resolve())}})
        self.assertEqual(result.returncode, 0)


FAKE_MVNW = """#!/usr/bin/env bash
echo "$*" >> mvnw.log
case "$*" in
  *spotless:apply*)
    [ -f fail-format ] && { echo "[ERROR] spotless failed"; exit 1; }
    [ -f reformat-two ] && echo "// formatted" >> src/main/java/two/B.java ;;
  *test*) [ -f fail-tests ] && { cat fail-tests; exit 1; } ;;
esac
exit 0
"""

SOURCES = {"A": "src/main/java/one/A.java", "B": "src/main/java/two/B.java", "A2": "src/main/java/two/A.java"}


class StopHookFixture:
    """A git repository with a Maven project in `folder` and a fake mvnw that logs its calls."""

    folder = ""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.project = self.root / self.folder if self.folder else self.root
        for relative in SOURCES.values():
            path = self.project / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"package {path.parent.name};\n\nclass {path.stem} {{}}\n")
        (self.project / "pom.xml").write_text("<project/>\n")
        mvnw = self.project / "mvnw"
        mvnw.write_text(FAKE_MVNW, newline="\n")
        mvnw.chmod(0o755)
        (self.root / "frontend").mkdir()
        (self.root / "frontend" / "app.js").write_text("1\n")
        (self.root / ".gitignore").write_text("mvnw.log\nfail-*\nreformat-*\ntarget/\n")
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "start")

    def hook(self, *args: str, active: bool = False) -> subprocess.CompletedProcess:
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.root))
        folder = [self.folder] if self.folder else []
        payload = {"session_id": "s1", "stop_hook_active": active}
        return subprocess.run([BASH, str(HOOKS / "verify-on-stop.sh"), *args, *folder], input=json.dumps(payload),
                              capture_output=True, text=True, env=env)

    def start_session(self):
        self.assertEqual(self.hook("--session-start").returncode, 0)

    def stop(self, active: bool = False) -> subprocess.CompletedProcess:
        return self.hook(active=active)

    def log(self) -> str:
        log = self.project / "mvnw.log"
        return log.read_text() if log.exists() else ""

    def checks_run(self) -> int:
        return self.log().count(" test ")

    def edit(self, key: str):
        path = self.project / SOURCES[key]
        path.write_text(path.read_text().replace("{}", "{ int x; }"))

    def error_in(self, key: str, message: str = "[NullAway] returning @Nullable") -> str:
        prefix = f"{self.folder}/" if self.folder else ""
        return f"[ERROR] /x/{prefix}{SOURCES[key]}:[3,9] {message}\n"

    def fail_with(self, text: str):
        (self.project / "fail-tests").write_text(text)


@unittest.skipUnless(BASH, "bash not found")
class StopHookTests(StopHookFixture, unittest.TestCase):

    def test_a_session_that_changes_no_code_is_not_checked(self):
        self.fail_with(self.error_in("B"))
        self.start_session()
        self.assertEqual(self.stop().returncode, 0)
        self.assertEqual(self.checks_run(), 0)

    def test_without_a_recorded_session_start_the_first_stop_only_records_the_code(self):
        self.assertEqual(self.stop().returncode, 0)
        self.assertEqual(self.checks_run(), 0)
        self.edit("A")
        self.stop()
        self.assertEqual(self.checks_run(), 1)

    def test_committed_changes_are_checked_and_a_pass_is_remembered(self):
        self.start_session()
        self.edit("A")
        git(self.root, "commit", "-qam", "change")
        self.assertEqual(self.stop().returncode, 0)
        self.assertEqual(self.checks_run(), 1, "a committed change was not checked")
        self.assertEqual(self.stop().returncode, 0)
        self.assertEqual(self.checks_run(), 1, "code that passed was checked again")

    def test_blocks_on_errors_in_files_changed_in_this_session(self):
        self.start_session()
        self.edit("A")
        self.fail_with(self.error_in("A") + self.error_in("B", "[NullAway] already broken"))
        result = self.stop()
        self.assertEqual(result.returncode, 2)
        self.assertIn("one/A.java:[3,9]", result.stderr)
        self.assertNotIn("already broken", result.stderr)
        self.assertEqual(self.stop(active=True).returncode, 0, "a second block on the same code would loop")

    def test_blocks_on_archunit_violations_in_classes_changed_in_this_session(self):
        self.start_session()
        self.edit("A")
        self.fail_with("Rule 'no classes should access standard streams' was violated (1 times):\n"
                       "Method <one.A.print()> gets field <java.lang.System.out> in (A.java:3)\n")
        result = self.stop()
        self.assertEqual(result.returncode, 2)
        self.assertIn("Method <one.A.print()>", result.stderr)

    def test_does_not_block_on_errors_only_in_code_the_session_did_not_change(self):
        self.start_session()
        self.edit("A")
        self.fail_with(self.error_in("B", "[NullAway] already broken"))
        result = self.stop()
        self.assertEqual(result.returncode, 0)
        self.assertIn("could not be fully verified", json.loads(result.stdout)["systemMessage"])

    def test_a_file_with_the_same_name_in_another_package_is_not_the_sessions(self):
        self.start_session()
        self.edit("A")
        self.fail_with(self.error_in("A2", "[NullAway] already broken")
                       + "Method <two.A.print()> gets field <java.lang.System.out> in (A.java:3)\n")
        self.assertEqual(self.stop().returncode, 0)

    def test_a_pom_change_does_not_make_every_failure_the_sessions(self):
        self.start_session()
        (self.project / "pom.xml").write_text("<project><!-- note --></project>\n")
        self.fail_with(self.error_in("B", "[NullAway] already broken"))
        result = self.stop()
        self.assertEqual(result.returncode, 0)
        self.assertIn("pom.xml", json.loads(result.stdout)["systemMessage"])

    def test_formats_only_the_files_the_session_changed(self):
        self.start_session()
        self.edit("A")
        self.stop()
        spotless = next(line for line in self.log().splitlines() if "spotless:apply" in line)
        self.assertIn(r"-DspotlessFiles=.*src[\\/]main[\\/]java[\\/]one[\\/]A\.java", spotless)
        self.assertNotIn("two", spotless)

    def test_a_file_reformatted_by_the_check_is_not_the_sessions(self):
        self.start_session()
        self.edit("A")
        (self.project / "reformat-two").write_text("")
        self.fail_with(self.error_in("B", "[NullAway] already broken"))
        self.assertEqual(self.stop().returncode, 0)

    def test_formatting_failure_blocks_and_is_not_recorded_as_passed(self):
        self.start_session()
        (self.project / "fail-format").write_text("")
        self.edit("A")
        result = self.stop()
        self.assertEqual(result.returncode, 2)
        self.assertIn("spotless failed", result.stderr)

        (self.project / "fail-format").unlink()
        runs = self.checks_run()
        self.assertEqual(self.stop().returncode, 0)
        self.assertEqual(self.checks_run(), runs + 1, "the failed run was cached as a pass")


@unittest.skipUnless(BASH, "bash not found")
class StopHookInSubfolderTests(StopHookFixture, unittest.TestCase):

    folder = "backend"

    def test_checks_only_changes_to_the_maven_project(self):
        self.start_session()
        (self.root / "frontend" / "app.js").write_text("2\n")
        git(self.root, "commit", "-qam", "frontend")
        self.stop()
        self.assertEqual(self.checks_run(), 0, "a frontend change ran the backend checks")

        self.edit("A")
        git(self.root, "commit", "-qam", "backend")
        self.stop()
        self.assertEqual(self.checks_run(), 1, "a committed backend change was not checked")

    def test_blocks_on_errors_in_changed_files_inside_the_subfolder(self):
        self.start_session()
        self.edit("A")
        self.fail_with(self.error_in("A"))
        self.assertEqual(self.stop().returncode, 2)


if __name__ == "__main__":
    unittest.main()
