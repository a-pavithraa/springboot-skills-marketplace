"""Regression tests for spring-boot-team-harness/scripts/apply_harness.py.

Run from the repository root:
    python3 -m unittest discover -s tests/scripts -v
"""

import hashlib
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2] / "plugins/springboot-architecture/skills/spring-boot-team-harness"
SCRIPT = SKILL / "scripts/apply_harness.py"
NS = {"m": "http://maven.apache.org/POM/4.0.0"}


def pom(body: str) -> str:
    return textwrap.dedent("""
        <?xml version="1.0" encoding="UTF-8"?>
        <project xmlns="http://maven.apache.org/POM/4.0.0">
          <modelVersion>4.0.0</modelVersion>
          <parent>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-parent</artifactId>
            <version>4.1.1</version>
          </parent>
          <artifactId>orders</artifactId>
        """).lstrip() + textwrap.dedent(body) + "</project>\n"


STANDARD = pom("""
  <properties>
    <java.version>25</java.version>
  </properties>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-webmvc</artifactId>
    </dependency>
  </dependencies>
  <build>
    <plugins>
      <plugin>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-maven-plugin</artifactId>
      </plugin>
    </plugins>
  </build>
""")


def add_after(text: str, anchor: str, addition: str) -> str:
    """Insert addition after the first anchor; fail loudly if the anchor is missing."""
    assert anchor in text, anchor
    return text.replace(anchor, anchor + addition, 1)


class ApplyHarnessTests(unittest.TestCase):

    def project(self, pom_text: str, extra: dict[str, str] | None = None) -> Path:
        root = Path(tempfile.mkdtemp())
        (root / "pom.xml").write_text(pom_text, encoding="utf-8")
        app = root / "src/main/java/com/acme/orders/OrdersApplication.java"
        app.parent.mkdir(parents=True)
        app.write_text("package com.acme.orders;\n\n@SpringBootApplication\nclass OrdersApplication {}\n", encoding="utf-8")
        for relative, text in (extra or {}).items():
            (root / relative).parent.mkdir(parents=True, exist_ok=True)
            (root / relative).write_text(text, encoding="utf-8")
        return root

    def run_script(self, root: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPT), str(root), *args], capture_output=True, text=True,
                              encoding="utf-8")

    def model(self, root: Path) -> ET.Element:
        return ET.parse(root / "pom.xml").getroot()

    def test_adds_gates_to_the_project_level_sections(self):
        root = self.project(STANDARD)
        self.assertEqual(self.run_script(root).returncode, 0)
        project = self.model(root)
        artifacts = [a.text for a in project.findall("m:dependencies/m:dependency/m:artifactId", NS)]
        self.assertIn("spring-modulith-starter-test", artifacts)
        self.assertIn("jspecify", artifacts)
        plugins = [a.text for a in project.findall("m:build/m:plugins/m:plugin/m:artifactId", NS)]
        self.assertEqual(plugins, ["spring-boot-maven-plugin", "maven-compiler-plugin", "spotless-maven-plugin"])
        bom = project.find("m:dependencyManagement/m:dependencies/m:dependency/m:artifactId", NS)
        self.assertEqual(bom.text, "spring-modulith-bom")
        self.assertEqual(project.find("m:properties/m:harness.base-package", NS).text, "com.acme.orders")

    def test_dependencies_inside_dependency_management_are_not_mistaken_for_the_project_list(self):
        root = self.project(pom("""
  <dependencyManagement>
    <dependencies>
      <dependency>
        <groupId>org.testcontainers</groupId>
        <artifactId>testcontainers-bom</artifactId>
        <version>2.0.5</version>
        <type>pom</type>
        <scope>import</scope>
      </dependency>
    </dependencies>
  </dependencyManagement>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-webmvc</artifactId>
    </dependency>
  </dependencies>
"""))
        self.assertEqual(self.run_script(root).returncode, 0)
        project = self.model(root)
        managed = [a.text for a in project.findall("m:dependencyManagement/m:dependencies/m:dependency/m:artifactId", NS)]
        self.assertEqual(managed, ["testcontainers-bom", "spring-modulith-bom"])
        direct = [a.text for a in project.findall("m:dependencies/m:dependency/m:artifactId", NS)]
        self.assertIn("spring-modulith-starter-test", direct)
        self.assertEqual([p.text for p in project.findall("m:build/m:plugins/m:plugin/m:artifactId", NS)],
                         ["maven-compiler-plugin", "spotless-maven-plugin"])

    def test_stops_when_the_pom_already_configures_the_compiler_plugin(self):
        root = self.project(STANDARD.replace(
            "<artifactId>spring-boot-maven-plugin</artifactId>",
            "<artifactId>spring-boot-maven-plugin</artifactId>\n      </plugin>\n      <plugin>\n"
            "        <artifactId>maven-compiler-plugin</artifactId>"))
        result = self.run_script(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("maven-compiler-plugin", result.stderr)
        self.assertNotIn("harness:begin", (root / "pom.xml").read_text(encoding="utf-8"))

    def test_compiler_plugin_in_plugin_management_is_not_a_conflict(self):
        root = self.project(STANDARD.replace(
            "  <build>\n",
            "  <build>\n    <pluginManagement>\n      <plugins>\n        <plugin>\n"
            "          <artifactId>maven-compiler-plugin</artifactId>\n        </plugin>\n      </plugins>\n"
            "    </pluginManagement>\n"))
        self.assertEqual(self.run_script(root).returncode, 0)

    def test_second_run_changes_nothing(self):
        root = self.project(STANDARD)
        self.run_script(root)
        before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
        result = self.run_script(root)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(before, {p: p.read_bytes() for p in root.rglob("*") if p.is_file()})
        self.assertNotIn("added", result.stdout)

    def test_existing_instructions_are_kept_and_get_the_gate_section(self):
        root = self.project(STANDARD, {"AGENTS.md": "# Ours\n", "CLAUDE.md": "Use tabs.\n"})
        self.run_script(root)
        agents = (root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertTrue(agents.startswith("# Ours\n\n<!-- harness:begin -->\n## Done means verify passes"))
        self.assertNotIn("## Team conventions", agents)
        self.assertEqual((root / "CLAUDE.md").read_text(encoding="utf-8"), "@AGENTS.md\n\nUse tabs.\n")
        self.run_script(root)
        self.assertEqual((root / "AGENTS.md").read_text(encoding="utf-8"), agents)

    def test_progen_style_project_keeps_its_spotless_modulith_and_boundary_test(self):
        progen_pom = add_after(STANDARD, "<java.version>25</java.version>\n",
                               "    <spotless.version>3.10.0</spotless.version>\n")
        progen_pom = add_after(progen_pom, "</dependency>\n", """    <dependency>
      <groupId>org.springframework.modulith</groupId>
      <artifactId>spring-modulith-starter-test</artifactId>
      <scope>test</scope>
    </dependency>
""")
        progen_pom = add_after(progen_pom, "</plugin>\n", """      <plugin>
        <groupId>com.diffplug.spotless</groupId>
        <artifactId>spotless-maven-plugin</artifactId>
      </plugin>
""")
        root = self.project(progen_pom, {
            "src/test/java/com/acme/orders/ModularityTests.java": "class ModularityTests { void v() { ApplicationModules.of(X.class).verify(); } }\n"})
        self.assertEqual(self.run_script(root).returncode, 0)
        pom_text = (root / "pom.xml").read_text(encoding="utf-8")
        self.assertEqual(pom_text.count("<artifactId>spotless-maven-plugin</artifactId>"), 1)
        self.assertEqual(pom_text.count("<artifactId>spring-modulith-starter-test</artifactId>"), 1)
        self.assertEqual(pom_text.count("<spotless.version>"), 1)
        self.assertIn("<artifactId>maven-compiler-plugin</artifactId>", pom_text)
        self.assertFalse((root / "src/test/java/com/acme/orders/ModuleBoundariesTests.java").exists())

    def test_templates_are_rendered_with_the_application_package(self):
        root = self.project(STANDARD)
        self.run_script(root)
        boundaries = (root / "src/test/java/com/acme/orders/ModuleBoundariesTests.java").read_text(encoding="utf-8")
        self.assertIn("package com.acme.orders;", boundaries)
        self.assertIn("ApplicationModules.of(com.acme.orders.OrdersApplication.class)", boundaries)
        agents = (root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("# orders", agents)
        self.assertIn("Spring Boot 4.1.1 on Java 25", agents)
        for path in root.rglob("*"):
            if path.is_file():
                self.assertNotIn("{{", path.read_text(encoding="utf-8"), path)

    def test_project_skills_go_to_both_claude_and_codex_folders(self):
        root = self.project(STANDARD)
        self.run_script(root)
        for skills_dir in (".claude/skills", ".agents/skills"):
            skill = (root / skills_dir / "add-module/SKILL.md").read_text(encoding="utf-8")
            self.assertIn("src/test/java/com/acme/orders/<module>", skill)
            self.assertFalse((root / skills_dir / "db-migration").exists())

    def test_migration_skill_is_added_only_for_flyway_projects(self):
        root = self.project(STANDARD.replace("spring-boot-starter-webmvc", "spring-boot-starter-flyway"))
        self.run_script(root)
        self.assertTrue((root / ".claude/skills/db-migration/SKILL.md").exists())
        self.assertTrue((root / ".agents/skills/db-migration/SKILL.md").exists())

    def test_no_modules_leaves_out_modulith_for_layered_projects(self):
        root = self.project(STANDARD)
        self.assertEqual(self.run_script(root, "--no-modules").returncode, 0)
        self.assertNotIn("modulith", (root / "pom.xml").read_text(encoding="utf-8"))
        self.assertFalse((root / "src/test/java/com/acme/orders/ModuleBoundariesTests.java").exists())
        self.assertFalse((root / ".claude/skills/add-module").exists())
        agents = (root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertNotIn("ModuleBoundariesTests", agents)
        self.assertNotIn("## Modules", agents)
        self.assertNotIn("modules:", agents)

    def test_module_markers_are_removed_when_modules_are_kept(self):
        root = self.project(STANDARD)
        self.run_script(root)
        agents = (root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("ModuleBoundariesTests", agents)
        self.assertNotIn("modules:", agents)

    def test_rerun_fills_in_an_agents_file_copied_from_the_template_by_hand(self):
        root = self.project(STANDARD)
        self.run_script(root, "--no-modules")
        (root / "AGENTS.md").write_text((SKILL / "assets/project/AGENTS.md").read_text(encoding="utf-8"), encoding="utf-8")

        result = self.run_script(root, "--no-modules")
        self.assertIn("patched  AGENTS.md", result.stdout)
        agents = (root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("Code under `com.acme.orders`", agents)
        self.assertNotIn("{{", agents)
        self.assertNotIn("ModuleBoundariesTests", agents)
        self.assertNotIn("modules:", agents)

    def test_rules_test_gets_archunit_unless_taikai_or_archunit_is_declared(self):
        root = self.project(STANDARD)
        self.run_script(root)
        self.assertTrue((root / "src/test/java/com/acme/orders/CodeRulesTests.java").exists())
        artifacts = [a.text for a in self.model(root).findall("m:dependencies/m:dependency/m:artifactId", NS)]
        self.assertIn("archunit", artifacts)

        with_taikai = add_after(STANDARD, "</dependency>\n", """    <dependency>
      <groupId>com.enofex</groupId>
      <artifactId>taikai</artifactId>
      <scope>test</scope>
    </dependency>
""")
        root = self.project(with_taikai)
        self.run_script(root)
        self.assertNotIn("<artifactId>archunit</artifactId>", (root / "pom.xml").read_text(encoding="utf-8"))

    def test_rerun_on_an_older_harness_adds_only_the_new_pieces(self):
        root = self.project(STANDARD)
        self.run_script(root)
        pom_path = root / "pom.xml"
        harnessed = pom_path.read_text(encoding="utf-8")
        start = harnessed.index("    <!-- harness:begin rules-dependencies -->")
        end = harnessed.index("<!-- harness:end rules-dependencies -->\n") + len("<!-- harness:end rules-dependencies -->\n")
        pom_path.write_text(harnessed[:start] + harnessed[end:], encoding="utf-8")
        (root / "src/test/java/com/acme/orders/CodeRulesTests.java").unlink()

        self.assertEqual(self.run_script(root).returncode, 0)
        self.assertEqual(pom_path.read_text(encoding="utf-8"), harnessed)
        self.assertTrue((root / "src/test/java/com/acme/orders/CodeRulesTests.java").exists())

    def test_hooks_are_added_and_ci_workflow_only_when_no_workflow_runs_mvnw(self):
        root = self.project(STANDARD)
        self.run_script(root)
        workflow = (root / ".github/workflows/verify.yml").read_text(encoding="utf-8")
        self.assertIn('java-version: "25"', workflow)
        self.assertIn("./mvnw -B verify", workflow)

        settings = (root / ".claude/settings.json").read_text(encoding="utf-8")
        for hook in ("guard.sh", "verify-on-stop.sh"):
            self.assertTrue((root / ".claude/hooks" / hook).exists())
            self.assertIn(f".claude/hooks/{hook}", settings)
        self.assertEqual((root / ".gitattributes").read_text(encoding="utf-8"), "*.sh text eol=lf\n")

        root = self.project(STANDARD, {".github/workflows/ci.yml": "steps:\n  - run: ./mvnw -ntp verify\n"})
        result = self.run_script(root)
        self.assertIn("kept     .github/workflows/ci.yml", result.stdout)
        self.assertFalse((root / ".github/workflows/verify.yml").exists())

    def test_archunit_freeze_store_is_configured_without_dropping_existing_properties(self):
        root = self.project(STANDARD)
        self.run_script(root)
        properties = (root / "src/test/resources/archunit.properties").read_text(encoding="utf-8")
        self.assertIn("freeze.store.default.path=src/test/resources/archunit_store", properties)
        self.assertIn("freeze.store.default.allowStoreCreation=false", properties)

        root = self.project(STANDARD, {"src/test/resources/archunit.properties":
                                       "archRule.failOnEmptyShould=false\nfreeze.store.default.allowStoreCreation=false\n"})
        self.run_script(root)
        properties = (root / "src/test/resources/archunit.properties").read_text(encoding="utf-8")
        self.assertEqual(properties, "archRule.failOnEmptyShould=false\nfreeze.store.default.allowStoreCreation=false\n"
                                     "freeze.store.default.path=src/test/resources/archunit_store\n")

    def test_store_creation_left_on_is_reported_not_changed(self):
        allowed = ("freeze.store.default.path=src/test/resources/archunit_store\n"
                   "freeze.store.default.allowStoreCreation=true\n")
        root = self.project(STANDARD, {"src/test/resources/archunit.properties": allowed})
        result = self.run_script(root)
        self.assertIn("allowStoreCreation=true records every new rule's violations as accepted", result.stdout)
        self.assertEqual((root / "src/test/resources/archunit.properties").read_text(encoding="utf-8"), allowed)

    def test_rerun_updates_harness_files_nobody_edited_and_keeps_edited_ones(self):
        root = self.project(STANDARD)
        self.run_script(root)
        hook = root / ".claude/hooks/verify-on-stop.sh"
        rules = root / "src/test/java/com/acme/orders/CodeRulesTests.java"
        current_hook = hook.read_text(encoding="utf-8")

        lock = json.loads((root / ".claude/harness.lock").read_text(encoding="utf-8"))
        old_hook = "#!/usr/bin/env bash\n# an earlier version\n"
        hook.write_text(old_hook, encoding="utf-8", newline="\n")
        lock[".claude/hooks/verify-on-stop.sh"] = hashlib.sha256(old_hook.encode()).hexdigest()
        (root / ".claude/harness.lock").write_text(json.dumps(lock), encoding="utf-8")
        rules.write_text(rules.read_text(encoding="utf-8") + "// team rule\n", encoding="utf-8")

        result = self.run_script(root)
        self.assertIn("updated  .claude/hooks/verify-on-stop.sh", result.stdout)
        self.assertEqual(hook.read_text(encoding="utf-8"), current_hook)
        self.assertIn("kept     src/test/java/com/acme/orders/CodeRulesTests.java (edited", result.stdout)
        self.assertTrue(rules.read_text(encoding="utf-8").endswith("// team rule\n"))

    def test_switching_to_no_modules_removes_the_module_files_nobody_edited(self):
        root = self.project(STANDARD)
        self.run_script(root)
        boundaries = root / "src/test/java/com/acme/orders/ModuleBoundariesTests.java"
        (root / ".agents/skills/add-module/SKILL.md").write_text("team notes\n", encoding="utf-8")

        result = self.run_script(root, "--no-modules")
        self.assertIn("removed  src/test/java/com/acme/orders/ModuleBoundariesTests.java", result.stdout)
        self.assertFalse(boundaries.exists())
        self.assertFalse((root / ".claude/skills/add-module").exists())
        self.assertIn("kept     .agents/skills/add-module/SKILL.md (edited", result.stdout)
        self.assertIn("AGENTS.md", [line.split()[1] for line in result.stdout.splitlines() if line.startswith("kept")])
        self.assertIn("ModuleBoundariesTests", result.stdout.split("kept     AGENTS.md", 1)[1].splitlines()[0])
        lock = json.loads((root / ".claude/harness.lock").read_text(encoding="utf-8"))
        self.assertNotIn("src/test/java/com/acme/orders/ModuleBoundariesTests.java", lock)
        self.assertNotIn(".claude/skills/add-module/SKILL.md", lock)

    def test_switching_to_no_modules_removes_an_unedited_module_test_from_before_the_lock(self):
        root = self.project(STANDARD)
        self.run_script(root)
        (root / ".claude/harness.lock").unlink()
        self.run_script(root, "--no-modules")
        self.assertFalse((root / "src/test/java/com/acme/orders/ModuleBoundariesTests.java").exists())

    def test_a_harness_file_from_before_the_lock_is_kept_with_instructions(self):
        root = self.project(STANDARD, {".claude/hooks/guard.sh": "#!/usr/bin/env bash\n# older harness\n"})
        result = self.run_script(root)
        self.assertIn("kept     .claude/hooks/guard.sh", result.stdout)
        self.assertIn("delete it and rerun", result.stdout)
        self.assertEqual((root / ".claude/hooks/guard.sh").read_text(encoding="utf-8"),
                         "#!/usr/bin/env bash\n# older harness\n")

    def test_existing_workflow_is_never_overwritten(self):
        maven_ci = "steps:\n  - run: mvn -B verify\n"
        root = self.project(STANDARD, {".github/workflows/verify.yml": maven_ci})
        self.run_script(root)
        self.assertEqual((root / ".github/workflows/verify.yml").read_text(encoding="utf-8"), maven_ci)
        self.assertFalse((root / ".github/workflows/harness-verify.yml").exists())

        other_ci = "steps:\n  - run: npm test\n"
        root = self.project(STANDARD, {".github/workflows/verify.yml": other_ci})
        self.run_script(root)
        self.assertEqual((root / ".github/workflows/verify.yml").read_text(encoding="utf-8"), other_ci)
        self.assertIn("./mvnw -B verify", (root / ".github/workflows/harness-verify.yml").read_text(encoding="utf-8"))

    def test_existing_settings_keep_their_entries_and_get_the_hooks(self):
        own = {
            "permissions": {"allow": ["Bash(gh pr view *)"], "deny": ["Read(./secrets/**)"]},
            "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "notify-send done"}]}]},
            "model": "opus",
        }
        root = self.project(STANDARD, {".claude/settings.json": json.dumps(own, indent=2)})
        self.assertEqual(self.run_script(root).returncode, 0)
        settings = json.loads((root / ".claude/settings.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["model"], "opus")
        self.assertIn("Bash(gh pr view *)", settings["permissions"]["allow"])
        self.assertIn("Bash(./mvnw *)", settings["permissions"]["allow"])
        self.assertIn("Read(./secrets/**)", settings["permissions"]["deny"])
        self.assertIn("Read(./.env)", settings["permissions"]["deny"])
        stop_commands = [hook["command"] for group in settings["hooks"]["Stop"] for hook in group["hooks"]]
        self.assertIn("notify-send done", stop_commands)
        self.assertTrue(any("verify-on-stop.sh" in command for command in stop_commands))
        self.assertTrue(any("guard.sh" in hook["command"]
                            for group in settings["hooks"]["PreToolUse"] for hook in group["hooks"]))
        self.assertTrue(settings["enabledPlugins"]["springboot-architecture@springboot-skills-marketplace"])

        merged = (root / ".claude/settings.json").read_text(encoding="utf-8")
        self.assertIn("kept     .claude/settings.json", self.run_script(root).stdout)
        self.assertEqual((root / ".claude/settings.json").read_text(encoding="utf-8"), merged)

    def test_the_marketplace_updates_itself_and_an_older_entry_gains_auto_update(self):
        older = {"extraKnownMarketplaces": {"springboot-skills-marketplace": {
            "source": {"source": "github", "repo": "a-pavithraa/springboot-skills-marketplace"}}}}
        for extra in ({}, {".claude/settings.json": json.dumps(older)}):
            root = self.project(STANDARD, extra)
            self.run_script(root)
            settings = json.loads((root / ".claude/settings.json").read_text(encoding="utf-8"))
            self.assertIs(settings["extraKnownMarketplaces"]["springboot-skills-marketplace"]["autoUpdate"], True)

    def test_a_team_that_turned_auto_update_off_keeps_it_off(self):
        off = {"extraKnownMarketplaces": {"springboot-skills-marketplace": {
            "source": {"source": "github", "repo": "a-pavithraa/springboot-skills-marketplace"}, "autoUpdate": False}}}
        root = self.project(STANDARD, {".claude/settings.json": json.dumps(off)})
        self.run_script(root)
        settings = json.loads((root / ".claude/settings.json").read_text(encoding="utf-8"))
        self.assertIs(settings["extraKnownMarketplaces"]["springboot-skills-marketplace"]["autoUpdate"], False)

    def test_managed_dependencies_are_not_mistaken_for_declared_ones(self):
        managed_only = pom("""
  <dependencyManagement>
    <dependencies>
      <dependency>
        <groupId>com.tngtech.archunit</groupId>
        <artifactId>archunit</artifactId>
        <version>1.5.1</version>
      </dependency>
      <dependency>
        <groupId>org.jspecify</groupId>
        <artifactId>jspecify</artifactId>
        <version>1.0.1</version>
      </dependency>
    </dependencies>
  </dependencyManagement>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-webmvc</artifactId>
    </dependency>
  </dependencies>
""")
        root = self.project(managed_only)
        self.assertEqual(self.run_script(root, "--no-modules").returncode, 0)
        direct = [a.text for a in self.model(root).findall("m:dependencies/m:dependency/m:artifactId", NS)]
        self.assertIn("archunit", direct)
        self.assertIn("jspecify", direct)

    def monorepo(self, extra: dict[str, str] | None = None) -> tuple[Path, Path]:
        backend = self.project(STANDARD)
        root = Path(tempfile.mkdtemp())
        backend.rename(root / "backend")
        (root / "frontend").mkdir()
        (root / "frontend" / "package.json").write_text("{}\n", encoding="utf-8")
        for relative, text in (extra or {}).items():
            (root / relative).parent.mkdir(parents=True, exist_ok=True)
            (root / relative).write_text(text, encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        return root, root / "backend"

    def test_project_in_a_subfolder_gets_ci_settings_and_hooks_at_the_repository_root(self):
        root, backend = self.monorepo()
        self.assertEqual(self.run_script(backend).returncode, 0)

        workflow = (root / ".github/workflows/verify.yml").read_text(encoding="utf-8")
        self.assertIn("working-directory: backend", workflow)
        self.assertFalse((backend / ".github").exists())

        settings = json.loads((root / ".claude/settings.json").read_text(encoding="utf-8"))
        stop = [hook["command"] for group in settings["hooks"]["Stop"] for hook in group["hooks"]]
        self.assertTrue(any(command.endswith('verify-on-stop.sh" "backend"') for command in stop), stop)
        start = [hook["command"] for group in settings["hooks"]["SessionStart"] for hook in group["hooks"]]
        self.assertTrue(any(command.endswith('verify-on-stop.sh" --session-start "backend"') for command in start), start)
        for hook in ("guard.sh", "verify-on-stop.sh"):
            self.assertTrue((root / ".claude/hooks" / hook).exists())
        self.assertFalse((backend / ".claude/settings.json").exists())
        self.assertIn("*.sh text eol=lf", (root / ".gitattributes").read_text(encoding="utf-8"))

        self.assertIn("## Done means verify passes", (backend / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertIn("backend/AGENTS.md", (root / "AGENTS.md").read_text(encoding="utf-8"))

        before = {path: path.read_bytes() for path in root.rglob("*") if path.is_file() and ".git" not in path.parts}
        self.run_script(backend)
        after = {path: path.read_bytes() for path in root.rglob("*") if path.is_file() and ".git" not in path.parts}
        self.assertEqual(after, before)

    def test_subfolder_project_keeps_a_root_workflow_that_builds_it(self):
        ci = "jobs:\n  build:\n    steps:\n      - run: cd backend && ./mvnw -B verify\n"
        root, backend = self.monorepo({".github/workflows/ci.yml": ci, "AGENTS.md": "# Repo\n"})
        result = self.run_script(backend)
        self.assertIn("../.github/workflows/ci.yml", result.stdout)
        self.assertEqual(sorted(p.name for p in (root / ".github/workflows").iterdir()), ["ci.yml"])
        self.assertEqual((root / "AGENTS.md").read_text(encoding="utf-8"),
                         "# Repo\n\nThe rules and build gates for `backend/` are in `backend/AGENTS.md`. Read it "
                         "before you change anything there.\n")

    def test_dry_run_writes_nothing(self):
        root = self.project(STANDARD)
        result = self.run_script(root, "--dry-run")
        self.assertIn("added", result.stdout)
        self.assertFalse((root / "AGENTS.md").exists())
        self.assertEqual((root / "pom.xml").read_text(encoding="utf-8"), STANDARD)


if __name__ == "__main__":
    unittest.main()
