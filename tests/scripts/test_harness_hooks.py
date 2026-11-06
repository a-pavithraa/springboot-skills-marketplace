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
from types import SimpleNamespace

HOOKS = Path(__file__).resolve().parents[2] / (
    "plugins/springboot-architecture/skills/spring-boot-team-harness/assets/project/.claude/hooks")
BASH = shutil.which("bash")
MIGRATIONS = Path("src", "main", "resources", "db", "migration")


def git(root: Path, *args: str):
    subprocess.run(["git", "-c", "user.email=t@example.com", "-c", "user.name=t", *args], cwd=root, check=True,
                   capture_output=True)


@unittest.skipUnless(BASH, "bash not found")
class GuardHookTests(unittest.TestCase):

    def guard(self, payload: dict, project: Path | None = None, env: dict | None = None,
              cwd: Path | None = None) -> SimpleNamespace:
        """Runs the hook; it refuses with a deny decision on stdout and exit 0, the form Claude Code and Codex share."""
        env = env or dict(os.environ, CLAUDE_PROJECT_DIR=str(project or Path.cwd()))
        result = subprocess.run([BASH, str(HOOKS / "guard.sh")], input=json.dumps(payload), capture_output=True,
                                text=True, env=env, cwd=cwd)
        self.assertEqual(result.returncode, 0, result.stderr)
        decision = json.loads(result.stdout)["hookSpecificOutput"] if result.stdout.strip() else {}
        if decision:
            self.assertEqual((decision["hookEventName"], decision["permissionDecision"]), ("PreToolUse", "deny"))
        return SimpleNamespace(refused=bool(decision), reason=decision.get("permissionDecisionReason", ""))

    def bash(self, command: str) -> subprocess.CompletedProcess:
        return self.guard({"tool_name": "Bash", "tool_input": {"command": command}})

    def test_blocks_destructive_git_commands(self):
        for command in ("git push --force origin main", "git push -f", "git reset --hard HEAD~1", "git clean -fd"):
            result = self.bash(command)
            self.assertEqual(result.refused, True, command)
            self.assertIn("Blocked by the team harness", result.reason)

    def test_blocks_destructive_git_commands_with_quoted_arguments(self):
        for command in ('git -C "/workspace/project" reset --hard HEAD~1',
                        'git -C "/workspace/project" push --force origin main'):
            self.assertEqual(self.bash(command).refused, True, command)

    def test_allows_safe_git_and_build_commands(self):
        for command in ("git push --force-with-lease", "git push -u origin feature", "git reset HEAD file",
                        "./mvnw -q verify"):
            self.assertEqual(self.bash(command).refused, False, command)

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
        self.assertEqual(on_main.refused, True)
        self.assertIn("Write a new migration", on_main.reason)
        self.assertEqual(edit("V2__lines.sql").refused, False)
        self.assertEqual(edit("V3__notes.sql").refused, False)

    def test_blocks_edits_to_the_archunit_freeze_record(self):
        record = Path("src/test/resources/archunit_store/stored.rules").resolve()
        for tool in ("Edit", "Write"):
            result = self.guard({"tool_name": tool, "tool_input": {"file_path": str(record)}})
            self.assertEqual(result.refused, True, tool)
            self.assertIn("frozen", result.reason)

    def test_blocks_edits_to_the_module_boundary_record(self):
        record = Path("src/test/resources/modulith_store").resolve()
        for tool in ("Edit", "Write"):
            result = self.guard({"tool_name": tool, "tool_input": {"file_path": str(record)}})
            self.assertEqual(result.refused, True, tool)
            self.assertIn("module-boundary violations", result.reason)

    def test_blocks_every_edit_to_a_modules_package_info_but_not_creating_one(self):
        root = Path(tempfile.mkdtemp())
        info = root / "src/main/java/com/acme/orders/package-info.java"
        info.parent.mkdir(parents=True)

        def edit(old: str, new: str) -> subprocess.CompletedProcess:
            return self.guard({"tool_name": "Edit",
                               "tool_input": {"file_path": str(info), "old_string": old, "new_string": new}}, root)

        self.assertEqual(self.guard({"tool_name": "Write", "tool_input": {
            "file_path": str(info), "content": '@ApplicationModule(allowedDependencies = "catalog")\npackage x;\n'}},
            root).refused, False)
        info.write_text('@ApplicationModule(allowedDependencies = {"catalog", "shared"})\npackage com.acme.orders;\n')
        widened = edit('"catalog"', '"catalog", "billing"')
        self.assertEqual(widened.refused, True)
        self.assertIn("boundary rules", widened.reason)
        for old, new in (("@ApplicationModule(", "@ApplicationModule(type = Type.OPEN, "),
                         ("shared", "billing"),
                         ("})", ", Deps.BILLING})"),
                         ("package com.acme.orders;", "@NullMarked\npackage com.acme.orders;")):
            with self.subTest(old=old, new=new):
                self.assertEqual(edit(old, new).refused, True)
        self.assertEqual(self.bash(f"sed -i s/shared/billing/ {info.as_posix()}").refused, True)
        info.write_text("@NullMarked\npackage com.acme.orders;\n")
        self.assertEqual(edit("@NullMarked\n", "").refused, False)

    def test_blocks_edits_to_the_archunit_freeze_settings(self):
        settings = Path("src/test/resources/archunit.properties").resolve()
        result = self.guard({"tool_name": "Edit", "tool_input": {"file_path": str(settings)}})
        self.assertEqual(result.refused, True)
        self.assertIn("store creation allowed", result.reason)

    def test_blocks_edits_to_existing_rule_tests_but_not_new_ones(self):
        root = Path(tempfile.mkdtemp())
        rules = root / "src/test/java/com/acme/CodeRulesTests.java"
        result = self.guard({"tool_name": "Write", "tool_input": {"file_path": str(rules)}}, root)
        self.assertEqual(result.refused, False)
        rules.parent.mkdir(parents=True)
        rules.write_text("class CodeRulesTests {}\n")
        for name in ("CodeRulesTests", "BuildSetupTests", "UnusedCodeTests", "ArchUnitTests", "LogLeakCheck"):
            path = rules.with_name(f"{name}.java")
            path.write_text("")
            result = self.guard({"tool_name": "Edit", "tool_input": {"file_path": str(path)}}, root)
            self.assertEqual(result.refused, True, name)
            self.assertIn(f"{name}.java holds the team's build rules", result.reason)

    def test_a_refusal_is_recorded_without_the_command(self):
        root = Path(tempfile.mkdtemp())
        git(root, "init", "-q")
        payload = {"session_id": "s9", "tool_name": "Bash", "tool_input": {"command": "git push --force origin secret-branch"}}
        self.assertEqual(self.guard(payload, root).refused, True)
        lines = (root / ".git/harness/events.jsonl").read_text().splitlines()
        event = json.loads(lines[-1])
        self.assertEqual((event["hook"], event["session"], event["result"], event["rule"]),
                         ("guard", "s9", "refused", "force-push"))
        self.assertNotIn("secret-branch", lines[-1])

    def test_allowed_actions_record_nothing(self):
        root = Path(tempfile.mkdtemp())
        git(root, "init", "-q")
        self.assertEqual(self.guard({"tool_name": "Bash", "tool_input": {"command": "./mvnw verify"}}, root).refused, False)
        self.assertFalse((root / ".git/harness/events.jsonl").exists())

    def test_blocks_bash_commands_that_write_protected_files(self):
        for command in ("sed -i 's/x//' src/test/resources/archunit_store/stored.rules",
                        "sed -E -i 's/rule//' src/test/java/com/acme/CodeRulesTests.java",
                        "echo x >> src/test/resources/archunit_store/abc",
                        "python3 -c \"open('src/test/resources/archunit.properties', 'w')\"",
                        "rm -rf src/test/resources/archunit_store",
                        "echo 'cycle|a,b' >> src/test/resources/modulith_store"):
            result = self.bash(command)
            self.assertEqual(result.refused, True, command)
            self.assertIn("Blocked by the team harness", result.reason)

    def test_allows_bash_commands_that_only_read_protected_files(self):
        for command in ("cat src/test/resources/archunit_store/stored.rules 2>/dev/null",
                        "sed -n 1,40p src/test/java/com/acme/CodeRulesTests.java | grep -i transactional",
                        "git diff src/test/resources/archunit_store"):
            self.assertEqual(self.bash(command).refused, False, command)

    def test_blocks_maven_flags_that_record_violations_as_accepted(self):
        for command in ("./mvnw test -Darchunit.freeze.store.default.allowStoreCreation=true",
                        "./mvnw verify -Darchunit.freeze.refreeze=true",
                        "./mvnw test -Dtest=ModuleBoundariesTests -Dmodulith.store.record=true",
                        "./gradlew harnessCheck -Pharness.record=true"):
            self.assertEqual(self.bash(command).refused, True, command)

    def patch(self, body: str, project: Path) -> subprocess.CompletedProcess:
        return self.guard({"tool_name": "apply_patch",
                           "tool_input": {"command": f"*** Begin Patch\n{body}*** End Patch\n"}}, project)

    def test_blocks_codex_patches_that_change_protected_files(self):
        root = Path(tempfile.mkdtemp())
        rules = root / "src/test/java/com/acme/CodeRulesTests.java"
        rules.parent.mkdir(parents=True)
        rules.write_text("class CodeRulesTests {}\n")
        info = root / "src/main/java/com/acme/orders/package-info.java"
        info.parent.mkdir(parents=True)
        info.write_text('@ApplicationModule(allowedDependencies = "catalog")\npackage com.acme.orders;\n')
        cases = {"update rule test": f"*** Update File: {rules.as_posix()}\n@@\n-class CodeRulesTests {{}}\n+x\n",
                 "delete rule test": f"*** Delete File: {rules.as_posix()}\n",
                 "update module rules": f"*** Update File: {info.as_posix()}\n@@\n-x\n+y\n",
                 "move onto the record": "*** Update File: src/A.java\n*** Move to: src/test/resources/modulith_store\n",
                 "update freeze record": "*** Update File: src/test/resources/archunit_store/stored.rules\n@@\n+x\n",
                 "second file in the patch": "*** Add File: src/main/java/B.java\n+class B {}\n"
                                             "*** Update File: src/test/resources/archunit.properties\n@@\n+x\n"}
        for name, body in cases.items():
            with self.subTest(name):
                result = self.patch(body, root)
                self.assertEqual(result.refused, True, result.reason)
                self.assertIn("Blocked by the team harness", result.reason)

    def test_allows_codex_patches_that_add_files_or_change_other_code(self):
        root = Path(tempfile.mkdtemp())
        for body in ("*** Add File: src/test/java/com/acme/billing/CodeRulesTests.java\n+class CodeRulesTests {}\n",
                     "*** Add File: src/main/java/com/acme/orders/package-info.java\n+package com.acme.orders;\n",
                     "*** Update File: src/main/java/com/acme/A.java\n@@\n-a\n+b\n"):
            with self.subTest(body):
                self.assertEqual(self.patch(body, root).refused, False)

    def test_without_a_project_variable_a_session_in_a_subfolder_finds_the_repository(self):
        root = Path(tempfile.mkdtemp())
        backend = root / "backend"
        (backend / MIGRATIONS).mkdir(parents=True)
        git(root, "init", "-q", "-b", "main")
        (backend / MIGRATIONS / "V1__orders.sql").write_text("create table orders (id bigint);\n")
        git(root, "add", "-A")
        git(root, "commit", "-qm", "orders")
        env = {key: value for key, value in os.environ.items() if key != "CLAUDE_PROJECT_DIR"}
        patch = f"*** Begin Patch\n*** Update File: {MIGRATIONS.as_posix()}/V1__orders.sql\n@@\n+x\n*** End Patch\n"
        result = self.guard({"session_id": "c1", "tool_name": "apply_patch", "tool_input": {"command": patch}},
                            env=env, cwd=backend)
        self.assertEqual(result.refused, True, result.reason)
        self.assertIn("Write a new migration", result.reason)
        self.assertTrue((root / ".git/harness/events.jsonl").exists())

    def test_ignores_other_files(self):
        result = self.guard({"tool_name": "Write", "tool_input": {"file_path": str(Path("src/main/java/A.java").resolve())}})
        self.assertEqual(result.refused, False)


CHECK = HOOKS.parents[1] / ".github" / "harness" / "check-protected.sh"
EXTENSIONS = "src/test/resources/META-INF/services/org.junit.jupiter.api.extension.Extension"
JUNIT = "src/test/resources/junit-platform.properties"
AUTODETECTION = "junit.jupiter.extensions.autodetection.enabled"


@unittest.skipUnless(BASH, "bash not found")
class IntegrityCheckTests(unittest.TestCase):
    """The CI backstop for the guard hook: what a pull request may change, whichever tool changed it."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.write({"src/test/resources/archunit_store/stored.rules": "rule-1=abc\n",
                    "src/test/resources/archunit_store/abc": "A uses B\nC uses D\n",
                    "src/test/resources/archunit.properties": "freeze.store.default.allowStoreCreation=false\n",
                    "src/test/resources/modulith_store": "cycle|catalog,orders\ndependency|inventory|catalog\n",
                    "src/test/java/com/acme/CodeRulesTests.java": "class CodeRulesTests {}\n",
                    str(MIGRATIONS / "V1__orders.sql"): "create table orders (id bigint);\n",
                    ".claude/hooks/guard.sh": "#!/usr/bin/env bash\n",
                    "src/main/java/com/acme/A.java": "class A {}\n"})
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "base")
        self.base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root, capture_output=True, text=True,
                                   check=True).stdout.strip()
        git(self.root, "switch", "-qc", "feature")

    def write(self, files: dict[str, str]):
        for name, text in files.items():
            (self.root / name).parent.mkdir(parents=True, exist_ok=True)
            (self.root / name).write_text(text, encoding="utf-8", newline="\n")

    def check(self, files: dict[str, str | None], label: bool = False) -> subprocess.CompletedProcess:
        for name, text in files.items():
            if text is None:
                (self.root / name).unlink()
            else:
                self.write({name: text})
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "change", "--allow-empty")
        env = dict(os.environ, HARNESS_RULE_CHANGE="true" if label else "false")
        return subprocess.run([BASH, str(CHECK), self.base], cwd=self.root, capture_output=True, text=True, env=env)

    def test_ordinary_changes_and_new_migrations_and_rule_tests_pass(self):
        result = self.check({"src/main/java/com/acme/A.java": "class A { int x; }\n",
                             str(MIGRATIONS / "V2__lines.sql"): "create table lines (id bigint);\n",
                             "src/test/java/com/acme/billing/ModularityTests.java": "class ModularityTests {}\n"})
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_removing_fixed_violations_from_the_record_passes(self):
        result = self.check({"src/test/resources/archunit_store/abc": "A uses B\n"})
        self.assertEqual(result.returncode, 0, result.stdout)

    MODULE_INFO = "src/main/java/com/acme/orders/package-info.java"

    def module_info(self, annotation: str) -> str:
        return f"/** Orders. */\n{annotation}\npackage com.acme.orders;\n\nimport org.springframework.modulith.ApplicationModule;\n"

    def test_narrowing_a_modules_allowed_dependencies_passes_and_widening_fails(self):
        base = self.module_info('@ApplicationModule(\n        allowedDependencies = {"catalog", "shared"})')
        passing = {"narrowed": '@ApplicationModule(allowedDependencies = {"catalog"})',
                   "reformatted": '@ApplicationModule(allowedDependencies = {"catalog",\n    "shared"})',
                   "another annotation": '@ApplicationModule(allowedDependencies = {"catalog", "shared"})\n@NullMarked'}
        failing = {"widened": '@ApplicationModule(allowedDependencies = {"catalog", "shared", "billing"})',
                   "removed": "@ApplicationModule",
                   "opened": '@ApplicationModule(allowedDependencies = {"catalog"}, type = ApplicationModule.Type.OPEN)',
                   "widened by a constant": '@ApplicationModule(allowedDependencies = {"catalog", Deps.BILLING})',
                   "widened by a unicode escape":
                       '@ApplicationModule(allowedDependencies = {"catalog", \\u0022billing\\u0022})'}
        for name, annotation in {**passing, **failing}.items():
            with self.subTest(name):
                self.setUp()
                self.move_base({self.MODULE_INFO: base})
                result = self.check({self.MODULE_INFO: self.module_info(annotation)})
                self.assertEqual(result.returncode, 1 if name in failing else 0, result.stdout)

    def test_a_new_module_passes_and_deleting_a_modules_rules_fails(self):
        open_module = self.module_info("@ApplicationModule(type = ApplicationModule.Type.OPEN)")
        self.assertEqual(self.check({self.MODULE_INFO: open_module}).returncode, 0)
        self.setUp()
        self.move_base({self.MODULE_INFO: open_module})
        result = self.check({self.MODULE_INFO: None})
        self.assertEqual(result.returncode, 1, result.stdout)

    def move_base(self, files: dict[str, str]):
        """Adds the files to the base commit the check compares against."""
        self.write(files)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "base files")
        self.base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root, capture_output=True, text=True,
                                   check=True).stdout.strip()

    def test_removing_fixed_violations_from_the_module_boundary_record_passes(self):
        self.assertEqual(self.check({"src/test/resources/modulith_store": "cycle|catalog,orders\n"}).returncode, 0)
        self.assertEqual(self.check({"src/test/resources/modulith_store": None}).returncode, 0)

    def test_each_protected_change_fails(self):
        cases = {"src/test/resources/archunit_store/abc": "A uses B\nC uses D\nE uses F\n",
                 "src/test/resources/archunit_store/new": "X uses Y\n",
                 "src/test/resources/modulith_store": "cycle|catalog,orders\ncycle|billing,orders\ndependency|inventory|catalog\n",
                 "backend/src/test/resources/modulith_store": "cycle|a,b\n",
                 "src/test/resources/archunit.properties": "freeze.store.default.allowStoreCreation=true\n",
                 "src/test/java/com/acme/CodeRulesTests.java": "class CodeRulesTests { /* weaker */ }\n",
                 str(MIGRATIONS / "V1__orders.sql"): "create table orders (id bigint, x int);\n",
                 ".claude/hooks/guard.sh": "#!/usr/bin/env bash\nexit 0\n"}
        for name, text in cases.items():
            with self.subTest(name):
                self.setUp()
                result = self.check({name: text})
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn(f"::error file={Path(name).as_posix()}::", result.stdout)

    def test_deleting_an_applied_migration_or_a_rule_test_fails(self):
        result = self.check({str(MIGRATIONS / "V1__orders.sql"): None,
                             "src/test/java/com/acme/CodeRulesTests.java": None})
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertEqual(result.stdout.count("::error"), 2)

    def test_the_label_accepts_the_change_but_still_lists_it(self):
        result = self.check({"src/test/java/com/acme/CodeRulesTests.java": "class CodeRulesTests { /* new rule */ }\n"},
                            label=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("::warning file=src/test/java/com/acme/CodeRulesTests.java::", result.stdout)

    def commit_as_base(self, files: dict[str, str | None]):
        self.check(files)
        self.base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root, capture_output=True, text=True,
                                   check=True).stdout.strip()

    HOOKS_REGISTERED = {"hooks": {
        "PreToolUse": [{"matcher": "Bash|Edit|Write|MultiEdit", "hooks": [
            {"type": "command", "command": 'bash "$CLAUDE_PROJECT_DIR/.claude/hooks/guard.sh"'}]}],
        "Stop": [{"hooks": [{"type": "command", "command": 'bash "$CLAUDE_PROJECT_DIR/.claude/hooks/verify-on-stop.sh"'}]}]}}
    POM = ("<project>\n<!-- harness:begin plugins -->\n<arg>-Xep:NullAway:ERROR</arg>\n<!-- harness:end plugins -->\n"
           "<version>1</version>\n</project>\n")
    JVM_CONFIG = "--add-exports=jdk.compiler/com.sun.tools.javac.api=ALL-UNNAMED\n-Xmx1g\n"

    def install_harness_files(self):
        self.commit_as_base({".claude/settings.json": json.dumps(self.HOOKS_REGISTERED, indent=2),
                             ".codex/hooks.json": json.dumps(self.HOOKS_REGISTERED, indent=2),
                             ".claude/harness.lock": json.dumps({".github/workflows/verify.yml": "abc"}),
                             ".github/workflows/verify.yml": "run: ./mvnw -B verify\n",
                             ".github/workflows/ci.yml": "run: npm test\n",
                             "pom.xml": self.POM,
                             ".mvn/jvm.config": self.JVM_CONFIG})

    def test_weakening_what_the_hooks_and_the_build_depend_on_fails(self):
        narrowed = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
            {"type": "command", "command": 'bash "$CLAUDE_PROJECT_DIR/.claude/hooks/guard.sh"'}]}]}}
        cases = {"settings without the Stop hook": {".claude/settings.json": json.dumps(narrowed)},
                 "codex hooks deleted": {".codex/hooks.json": None},
                 "codex hooks not JSON": {".codex/hooks.json": "{"},
                 "verify workflow deleted": {".github/workflows/verify.yml": None},
                 "verify workflow changed": {".github/workflows/verify.yml": "run: echo skipped\n"},
                 "NullAway removed": {"pom.xml": self.POM.replace("<arg>-Xep:NullAway:ERROR</arg>\n", "")},
                 "markers removed": {"pom.xml": "<project>\n<version>1</version>\n</project>\n"},
                 "jvm option removed": {".mvn/jvm.config": "-Xmx1g\n"}}
        for name, files in cases.items():
            with self.subTest(name):
                self.setUp()
                self.install_harness_files()
                result = self.check(files)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn(f"::error file={next(iter(files))}::", result.stdout)

    def test_ordinary_changes_to_settings_pom_and_workflows_pass(self):
        self.install_harness_files()
        own = json.loads(json.dumps(self.HOOKS_REGISTERED))
        own["model"] = "opus"
        own["hooks"]["PostToolUse"] = [{"hooks": [{"type": "command", "command": "python3 notify.py"}]}]
        result = self.check({".claude/settings.json": json.dumps(own),
                             ".codex/hooks.json": json.dumps(own),
                             ".github/workflows/ci.yml": None,
                             "pom.xml": self.POM.replace("<version>1</version>", "<version>2</version>"),
                             ".mvn/jvm.config": self.JVM_CONFIG + "-Xss4m\n"})
        self.assertEqual(result.returncode, 0, result.stdout)

    GRADLE_BUILD = "plugins { id 'java' }\n\napply from: \"gradle/harness.gradle\"\n"
    KOTLIN_BUILD = "plugins { java }\n\napply(from = \"gradle/harness.gradle\")\n"

    def test_weakening_the_gradle_gates_fails(self):
        cases = {"script changed": {"gradle/harness.gradle": "// NullAway off\n"},
                 "script deleted": {"gradle/harness.gradle": None},
                 "groovy build stops applying it": {"build.gradle": "plugins { id 'java' }\n"},
                 "kotlin build stops applying it": {"build.gradle.kts": "plugins { java }\n"}}
        for name, files in cases.items():
            with self.subTest(name):
                self.setUp()
                self.commit_as_base({"gradle/harness.gradle": "// gates\n", "build.gradle": self.GRADLE_BUILD,
                                     "build.gradle.kts": self.KOTLIN_BUILD})
                result = self.check(files)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn(f"::error file={next(iter(files))}::", result.stdout)

    def test_ordinary_changes_to_a_gradle_build_pass(self):
        self.commit_as_base({"build.gradle": self.GRADLE_BUILD})
        result = self.check({"build.gradle": self.GRADLE_BUILD.replace("plugins { id 'java' }",
                                                                       "plugins { id 'java'; id 'jacoco' }"),
                             "gradle/harness.gradle": "// gates\n"})
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_a_verify_workflow_the_harness_did_not_write_is_the_teams(self):
        self.commit_as_base({".github/workflows/verify.yml": "run: ./mvnw -B verify\n"})
        result = self.check({".github/workflows/verify.yml": "run: ./mvnw verify\n"})
        self.assertEqual(result.returncode, 0, result.stdout)

    def install_log_leak_check(self):
        self.commit_as_base({"src/test/java/com/acme/LogLeakCheck.java": "class LogLeakCheck {}\n",
                             EXTENSIONS: "com.acme.Other\ncom.acme.LogLeakCheck\n",
                             JUNIT: f"{AUTODETECTION}=true\n"})

    def test_each_way_of_switching_off_log_leak_check_fails(self):
        cases = {"changed": {"src/test/java/com/acme/LogLeakCheck.java": "class LogLeakCheck { /* weaker */ }\n"},
                 "deleted": {"src/test/java/com/acme/LogLeakCheck.java": None},
                 "unregistered": {EXTENSIONS: "com.acme.Other\n"},
                 "commented out": {EXTENSIONS: "com.acme.Other\n# com.acme.LogLeakCheck\n"},
                 "services file deleted": {EXTENSIONS: None},
                 "autodetection off": {JUNIT: f"{AUTODETECTION}=false\n"},
                 "autodetection overridden": {JUNIT: f"{AUTODETECTION}=true\n{AUTODETECTION}=false\n"},
                 "autodetection line removed": {JUNIT: "junit.jupiter.execution.parallel.enabled=true\n"},
                 "properties file deleted": {JUNIT: None}}
        for name, change in cases.items():
            with self.subTest(name):
                self.setUp()
                self.install_log_leak_check()
                result = self.check(change)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn(f"::error file={next(iter(change))}::", result.stdout)

    def test_other_edits_to_the_junit_files_pass(self):
        self.install_log_leak_check()
        result = self.check({EXTENSIONS: "com.acme.LogLeakCheck\ncom.acme.Another\n",
                             JUNIT: f"{AUTODETECTION} = true\njunit.jupiter.execution.parallel.enabled=true\n"})
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_the_junit_files_are_free_without_log_leak_check(self):
        self.commit_as_base({EXTENSIONS: "com.acme.Other\n", JUNIT: f"{AUTODETECTION}=true\n"})
        result = self.check({EXTENSIONS: "com.acme.Another\n", JUNIT: f"{AUTODETECTION}=false\n"})
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_the_label_accepts_switching_off_log_leak_check(self):
        self.install_log_leak_check()
        result = self.check({JUNIT: f"{AUTODETECTION}=false\n"}, label=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn(f"::warning file={JUNIT}::", result.stdout)


FAKE_MVNW = """#!/usr/bin/env bash
echo "$*" >> mvnw.log
case "$*" in
  *spotless:apply*)
    [ -f fail-format ] && { echo "[ERROR] spotless failed"; exit 1; }
    [ -f reformat-two ] && echo "// formatted" >> src/main/java/two/B.java ;;
  *spring-javaformat:validate*)
    [ -f unformatted ] && { echo "[ERROR] Formatting violations found in the following files:"; sed 's|^|[ERROR]  * /x/|' unformatted; exit 1; } ;;
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
        (self.root / ".gitignore").write_text("mvnw.log\nfail-*\nreformat-*\nunformatted\ntarget/\n")
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "start")

    def hook(self, *args: str, active: bool = False, env: dict | None = None,
             cwd: Path | None = None, session: str = "s1") -> SimpleNamespace:
        """Runs the hook; it blocks with a block decision on stdout and exit 0, the form Claude Code and Codex share."""
        env = env or dict(os.environ, CLAUDE_PROJECT_DIR=str(self.root))
        folder = [self.folder] if self.folder else []
        payload = {"session_id": session, "stop_hook_active": active}
        result = subprocess.run([BASH, str(HOOKS / "verify-on-stop.sh"), *args, *folder], input=json.dumps(payload),
                                capture_output=True, text=True, env=env, cwd=cwd)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout) if result.stdout.strip() else {}
        blocked = output.get("decision") == "block"
        return SimpleNamespace(blocked=blocked, reason=output.get("reason", ""), stdout=result.stdout)

    def start_session(self):
        self.assertEqual(self.hook("--session-start").blocked, False)

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

    def events(self) -> list[dict]:
        path = self.root / ".git/harness/events.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def results(self) -> list[str]:
        return [event["result"] for event in self.events()]


@unittest.skipUnless(BASH, "bash not found")
class StopHookTests(StopHookFixture, unittest.TestCase):

    def test_a_session_that_changes_no_code_is_not_checked(self):
        self.fail_with(self.error_in("B"))
        self.start_session()
        self.assertEqual(self.stop().blocked, False)
        self.assertEqual(self.checks_run(), 0)

    def test_without_a_recorded_session_start_the_first_stop_says_the_turn_was_not_checked(self):
        self.edit("A")
        result = self.stop()
        self.assertEqual(result.blocked, False)
        self.assertIn("this turn's changes were not checked", json.loads(result.stdout)["systemMessage"])
        self.assertEqual(self.checks_run(), 0)
        self.assertEqual(self.results(), ["no-baseline"])
        self.edit("B")
        self.stop()
        self.assertEqual(self.checks_run(), 1)

    def test_a_session_in_use_outlives_sessions_that_started_after_it(self):
        self.start_session()
        for n in range(19):
            self.hook("--session-start", session=f"older{n}")
        stamps = self.root / ".git/harness"
        os.utime(stamps / "session-s1", (1000, 1000))
        for n in range(19):
            os.utime(stamps / f"session-older{n}", (2000 + n, 2000 + n))
        self.stop()
        for n in range(5):
            self.hook("--session-start", session=f"newer{n}")
        self.assertTrue((stamps / "session-s1").exists(), "a session still in use was pruned")
        self.assertEqual(len(list(stamps.glob("session-*"))), 20)

    def test_committed_changes_are_checked_and_a_pass_is_remembered(self):
        self.start_session()
        self.edit("A")
        git(self.root, "commit", "-qam", "change")
        self.assertEqual(self.stop().blocked, False)
        self.assertEqual(self.checks_run(), 1, "a committed change was not checked")
        self.assertEqual(self.stop().blocked, False)
        self.assertEqual(self.checks_run(), 1, "code that passed was checked again")

    def test_blocks_on_errors_in_files_changed_in_this_session(self):
        self.start_session()
        self.edit("A")
        self.fail_with(self.error_in("A") + self.error_in("B", "[NullAway] already broken"))
        result = self.stop()
        self.assertEqual(result.blocked, True)
        self.assertIn("one/A.java:[3,9]", result.reason)
        self.assertNotIn("already broken", result.reason)
        self.assertEqual(self.stop(active=True).blocked, False, "a second block on the same code would loop")

    def test_blocks_on_archunit_violations_in_classes_changed_in_this_session(self):
        self.start_session()
        self.edit("A")
        self.fail_with("Rule 'no classes should access standard streams' was violated (1 times):\n"
                       "Method <one.A.print()> gets field <java.lang.System.out> in (A.java:3)\n"
                       "[ERROR]   CodeRulesTests.codeLogsInsteadOfPrinting:123 Architecture Violation - Rule "
                       "'no classes should access standard streams' was violated (1 times):\n")
        result = self.stop()
        self.assertEqual(result.blocked, True)
        self.assertIn("Method <one.A.print()>", result.reason)
        self.assertNotIn("codeLogsInsteadOfPrinting:123", result.reason, "Surefire's summary repeats the violation")

    def test_does_not_block_on_errors_only_in_code_the_session_did_not_change(self):
        self.start_session()
        self.edit("A")
        self.fail_with(self.error_in("B", "[NullAway] already broken"))
        result = self.stop()
        self.assertEqual(result.blocked, False)
        self.assertIn("could not be fully verified", json.loads(result.stdout)["systemMessage"])

    def test_a_file_with_the_same_name_in_another_package_is_not_the_sessions(self):
        self.start_session()
        self.edit("A")
        self.fail_with(self.error_in("A2", "[NullAway] already broken")
                       + "Method <two.A.print()> gets field <java.lang.System.out> in (A.java:3)\n")
        self.assertEqual(self.stop().blocked, False)

    def test_a_pom_change_does_not_make_every_failure_the_sessions(self):
        self.start_session()
        (self.project / "pom.xml").write_text("<project><!-- note --></project>\n")
        self.fail_with(self.error_in("B", "[NullAway] already broken"))
        result = self.stop()
        self.assertEqual(result.blocked, False)
        self.assertIn("pom.xml", json.loads(result.stdout)["systemMessage"])

    def test_a_build_setup_failure_after_a_pom_change_is_the_sessions(self):
        self.start_session()
        (self.project / "pom.xml").write_text("<project><!-- flyway in test scope --></project>\n")
        self.fail_with("[ERROR]   BuildSetupTests.bootDependenciesAreNotTestOnly:44\n"
                       "Expecting empty but was: [\"pom.xml: spring-boot-starter-flyway is on the test classpath "
                       "only, so the tests pass with it and the application runs without it\"]\n")
        result = self.stop()
        self.assertEqual(result.blocked, True)
        self.assertIn("spring-boot-starter-flyway is on the test classpath only", result.reason)
        self.assertEqual(self.events()[-1]["gates"], "build-setup")

    def test_formats_only_the_files_the_session_changed(self):
        self.start_session()
        self.edit("A")
        self.stop()
        spotless = next(line for line in self.log().splitlines() if "spotless:apply" in line)
        self.assertIn(r"-DspotlessFiles=.*src[\\/]main[\\/]java[\\/]one[\\/]A\.java", spotless)
        self.assertNotIn("two", spotless)

    def test_on_spring_java_format_the_sessions_files_are_checked_not_formatted(self):
        (self.project / "pom.xml").write_text(
            "<project><build><plugins><plugin><artifactId>spring-javaformat-maven-plugin</artifactId></plugin>"
            "</plugins></build></project>\n")
        self.start_session()
        self.edit("A")
        (self.project / "unformatted").write_text(SOURCES["A"] + "\n")
        result = self.stop()
        self.assertEqual(result.blocked, True)
        self.assertIn("Run ./mvnw spring-javaformat:apply", result.reason)
        self.assertIn(SOURCES["A"], result.reason)
        self.assertNotIn("spotless", self.log())

        (self.project / "unformatted").write_text(SOURCES["B"] + "\n")
        self.assertEqual(self.stop().blocked, False, "a file the session didn't change blocked the turn")

    def test_a_file_reformatted_by_the_check_is_not_the_sessions(self):
        self.start_session()
        self.edit("A")
        (self.project / "reformat-two").write_text("")
        self.fail_with(self.error_in("B", "[NullAway] already broken"))
        self.assertEqual(self.stop().blocked, False)

    def test_formatting_failure_blocks_and_is_not_recorded_as_passed(self):
        self.start_session()
        (self.project / "fail-format").write_text("")
        self.edit("A")
        result = self.stop()
        self.assertEqual(result.blocked, True)
        self.assertIn("spotless failed", result.reason)

        (self.project / "fail-format").unlink()
        runs = self.checks_run()
        self.assertEqual(self.stop().blocked, False)
        self.assertEqual(self.checks_run(), runs + 1, "the failed run was cached as a pass")

    def test_each_stop_is_recorded_with_its_result(self):
        self.start_session()
        self.stop()
        self.edit("A")
        self.stop()
        self.stop()
        self.assertEqual(self.results(), ["started", "no-change", "passed", "already-passed"])
        passed = self.events()[2]
        self.assertEqual((passed["hook"], passed["session"], passed["files"]), ("stop", "s1", 1))
        self.assertIsInstance(passed["seconds"], int)

    def test_a_block_records_the_gate_and_no_paths(self):
        self.start_session()
        self.edit("A")
        self.fail_with(self.error_in("A"))
        self.stop()
        self.stop(active=True)
        blocked, gave_up = self.events()[-2:]
        self.assertEqual((blocked["result"], blocked["gates"]), ("blocked", "nullaway"))
        self.assertEqual(gave_up["result"], "gave-up")
        log = (self.root / ".git/harness/events.jsonl").read_text()
        self.assertNotIn("A.java", log)
        self.assertNotIn("one/", log)

    def test_rule_and_format_blocks_and_unverified_turns_name_their_gate(self):
        self.start_session()
        self.edit("A")
        self.fail_with("Method <one.A.print()> gets field <java.lang.System.out> in (A.java:3)\n")
        self.stop()
        self.assertEqual(self.events()[-1]["gates"], "rules")

        self.fail_with(self.error_in("B", "[NullAway] already broken"))
        self.stop()
        self.assertEqual((self.events()[-1]["result"], self.events()[-1]["gates"]), ("unverified", "nullaway"))

        (self.project / "fail-format").write_text("")
        self.edit("B")
        self.stop()
        self.assertEqual((self.events()[-1]["result"], self.events()[-1]["gates"]), ("blocked", "format"))

    def test_the_event_log_is_capped(self):
        path = self.root / ".git/harness/events.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        line = '{"ts":"2026-01-01T00:00:00Z","hook":"stop","session":"old","result":"no-change","gates":"","seconds":0,"files":0}\n'
        path.write_text(line * 2500)
        self.start_session()
        self.assertEqual(len(path.read_text().splitlines()), 2000)
        self.assertEqual(self.results()[-1], "started")


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
        self.assertEqual(self.stop().blocked, True)

    def test_without_a_project_variable_a_session_started_in_the_subfolder_is_checked(self):
        env = {key: value for key, value in os.environ.items() if key != "CLAUDE_PROJECT_DIR"}
        self.assertEqual(self.hook("--session-start", env=env, cwd=self.project / "src").blocked, False)
        self.edit("A")
        self.fail_with(self.error_in("A"))
        self.assertEqual(self.hook(env=env, cwd=self.project / "src").blocked, True)


FAKE_GRADLEW = """#!/usr/bin/env bash
echo "$*" >> mvnw.log
case "$*" in
  *spotlessApply*) [ -f fail-format ] && { echo "spotless failed"; exit 1; } ;;
  *checkFormat*)
    [ -f unformatted ] && { echo "Formatting violations found in the following files:"; sed 's|^| * /x/|' unformatted; exit 1; } ;;
  *harnessCheck*) [ -f fail-tests ] && { cat fail-tests; exit 1; } ;;
esac
exit 0
"""


@unittest.skipUnless(BASH, "bash not found")
class GradleStopHookTests(StopHookFixture, unittest.TestCase):
    """The same hook on a Gradle build: gradle/harness.gradle's tasks, and Gradle's way of printing failures."""

    def setUp(self):
        super().setUp()
        (self.project / "pom.xml").unlink()
        (self.project / "mvnw").unlink()
        (self.project / "build.gradle").write_text("plugins { id 'java' }\n")
        (self.project / "gradle").mkdir()
        (self.project / "gradle/harness.gradle").write_text("spotless {\n    java {}\n}\n")
        gradlew = self.project / "gradlew"
        gradlew.write_text(FAKE_GRADLEW, newline="\n")
        gradlew.chmod(0o755)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "gradle")

    def checks_run(self) -> int:
        return self.log().count("harnessCheck")

    def error_in(self, key: str, message: str = "[NullAway] returning @Nullable") -> str:
        prefix = f"{self.folder}/" if self.folder else ""
        return f"/x/{prefix}{SOURCES[key]}:3: error: {message}\n"

    def test_formats_the_sessions_files_by_path_then_runs_the_fast_gates(self):
        self.start_session()
        self.edit("A")
        self.assertEqual(self.stop().blocked, False)
        calls = self.log().splitlines()
        self.assertEqual(calls, [f"-q spotlessApply -PharnessFiles={SOURCES['A']}", "-q harnessCheck"])

    def test_blocks_on_compiler_errors_in_files_changed_in_this_session(self):
        self.start_session()
        self.edit("A")
        self.fail_with(self.error_in("A") + self.error_in("B", "[NullAway] already broken")
                       + "\n* What went wrong:\nExecution failed for task ':compileJava'.\n"
                       + "  " + self.error_in("A"))
        result = self.stop()
        self.assertEqual(result.blocked, True)
        self.assertEqual(result.reason.count("one/A.java:3: error: [NullAway]"), 1, result.reason)
        self.assertNotIn("already broken", result.reason)
        self.assertEqual(self.events()[-1]["gates"], "nullaway")

    def test_blocks_on_indented_archunit_violations_in_classes_changed_in_this_session(self):
        self.start_session()
        self.edit("A")
        self.fail_with("CodeRulesTests > codeLogsInsteadOfPrinting() FAILED\n"
                       "    java.lang.AssertionError: Architecture Violation [Priority: MEDIUM] - Rule 'no classes "
                       "should access standard streams' was violated (1 times):\n"
                       "    Method <one.A.print()> gets field <java.lang.System.out> in (A.java:3)\n")
        result = self.stop()
        self.assertEqual(result.blocked, True)
        self.assertIn("Method <one.A.print()>", result.reason)

    def test_a_build_setup_failure_after_a_build_file_change_is_the_sessions(self):
        self.start_session()
        (self.project / "build.gradle").write_text("plugins { id 'java' }\n// flyway in test scope\n")
        self.fail_with("BuildSetupTests > bootDependenciesAreNotTestOnly() FAILED\n"
                       "    Expecting empty but was: [\"build.gradle: spring-boot-starter-flyway is on the test "
                       "classpath only, so the tests pass with it and the application runs without it\"]\n")
        result = self.stop()
        self.assertEqual(result.blocked, True)
        self.assertIn("spring-boot-starter-flyway is on the test classpath only", result.reason)
        self.assertEqual(self.events()[-1]["gates"], "build-setup")

    def test_failures_elsewhere_name_the_gradle_build(self):
        self.start_session()
        (self.project / "build.gradle").write_text("plugins { id 'java'; id 'jacoco' }\n")
        self.fail_with(self.error_in("B", "[NullAway] already broken"))
        message = json.loads(self.stop().stdout)["systemMessage"]
        self.assertIn("changed build.gradle", message)
        self.assertIn("./gradlew build", message)

    def test_on_spring_java_format_the_sessions_files_are_checked_not_formatted(self):
        # Applied through a catalog alias: the harness's script, which leaves Spotless out, says which formatter.
        (self.project / "build.gradle").write_text("plugins { alias(libs.plugins.spring.javaformat) }\n")
        (self.project / "gradle/harness.gradle").write_text("apply plugin: net.ltgt.gradle.errorprone.ErrorPronePlugin\n")
        self.start_session()
        self.edit("A")
        (self.project / "unformatted").write_text(SOURCES["A"] + "\n")
        result = self.stop()
        self.assertEqual(result.blocked, True)
        self.assertIn("Run ./gradlew format", result.reason)
        self.assertNotIn("spotless", self.log())


if __name__ == "__main__":
    unittest.main()
