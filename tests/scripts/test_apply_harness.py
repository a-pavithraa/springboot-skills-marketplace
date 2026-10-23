"""Regression tests for spring-boot-team-harness/scripts/apply_harness.py.

Run from the repository root:
    python3 -m unittest discover -s tests/scripts -v
"""

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
        progen_pom = STANDARD.replace("    <java.version>25</java.version>\n",
                                      "    <java.version>25</java.version>\n    <spotless.version>3.10.0</spotless.version>\n")
        progen_pom = progen_pom.replace("""      <artifactId>spring-boot-starter-webmvc</artifactId>
    </dependency>""", """      <artifactId>spring-boot-starter-webmvc</artifactId>
    </dependency>
    <dependency>
      <groupId>org.springframework.modulith</groupId>
      <artifactId>spring-modulith-starter-test</artifactId>
      <scope>test</scope>
    </dependency>""").replace("""        <artifactId>spring-boot-maven-plugin</artifactId>
      </plugin>""", """        <artifactId>spring-boot-maven-plugin</artifactId>
      </plugin>
      <plugin>
        <groupId>com.diffplug.spotless</groupId>
        <artifactId>spotless-maven-plugin</artifactId>
      </plugin>""")
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

    def test_dry_run_writes_nothing(self):
        root = self.project(STANDARD)
        result = self.run_script(root, "--dry-run")
        self.assertIn("added", result.stdout)
        self.assertFalse((root / "AGENTS.md").exists())
        self.assertEqual((root / "pom.xml").read_text(encoding="utf-8"), STANDARD)


if __name__ == "__main__":
    unittest.main()
