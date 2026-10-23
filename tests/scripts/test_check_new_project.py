"""Regression tests for creating-springboot-projects/scripts/check_new_project.py.

Run from the repository root:
    python3 -m unittest discover -s tests/scripts -v
"""

import re
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2] / "plugins/springboot-architecture/skills/creating-springboot-projects"
SCRIPT = SKILL / "scripts/check_new_project.py"


def pom(boot: str = "4.1.1", dependencies: str = "") -> str:
    return textwrap.dedent(f"""
        <project>
          <parent>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-parent</artifactId>
            <version>{boot}</version>
          </parent>
          <dependencies>
            <dependency>
              <groupId>org.springframework.boot</groupId>
              <artifactId>spring-boot-starter-webmvc</artifactId>
            </dependency>
            <dependency>
              <groupId>com.enofex</groupId>
              <artifactId>taikai</artifactId>
              <version>2.1.0</version>
              <scope>test</scope>
            </dependency>
            {dependencies}
          </dependencies>
        </project>
        """)


ARCH_TEST = """
    package com.acme.shop;
    import com.enofex.taikai.Taikai;
    class ArchitectureRulesTest {}
    """


class CheckNewProjectTestCase(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.write("pom.xml", pom())
        self.write("src/test/java/com/acme/shop/ArchitectureRulesTest.java", ARCH_TEST)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, relative: str, content: str):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content), encoding="utf-8")

    def check(self):
        return subprocess.run([sys.executable, str(SCRIPT), str(self.root)], capture_output=True, text=True)

    def assertFails(self, text):
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn(text, result.stdout)


class Checks(CheckNewProjectTestCase):

    def test_complete_project_passes(self):
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("CHECK PASSED", result.stdout)

    def test_previous_major_version_fails(self):
        self.write("pom.xml", pom(boot="3.5.7"))
        self.assertFails("not the previous major version")

    def test_older_boot4_line_is_a_warning(self):
        self.write("pom.xml", pom(boot="4.0.3"))
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("not on the current 4.1.x line", result.stdout)

    def test_missing_architecture_test_fails(self):
        (self.root / "src/test/java/com/acme/shop/ArchitectureRulesTest.java").unlink()
        self.assertFails("No Taikai architecture test")

    def test_architecture_test_without_dependency_fails(self):
        self.write("pom.xml", pom().replace("com.enofex", "org.example"))
        self.assertFails("no com.enofex:taikai test dependency")

    def test_unresolved_placeholder_fails(self):
        self.write("src/main/java/com/acme/shop/Order.java", "package {{PACKAGE}};\nclass Order {}\n")
        self.assertFails("src/main/java/com/acme/shop/Order.java:1 {{PACKAGE}}")

    def test_go_template_syntax_is_not_a_placeholder(self):
        self.write("Taskfile.yml", "cmds:\n  - '{{if .X}}a{{else}}b{{end}}'\n")
        self.assertEqual(self.check().returncode, 0)

    def test_templates_in_a_project_skill_install_are_ignored(self):
        self.write(".claude/skills/creating-springboot-projects/assets/controller.java", "package {{PACKAGE}};\n")
        self.assertEqual(self.check().returncode, 0)

    def test_h2_is_a_warning(self):
        self.write("pom.xml", pom(dependencies="""
            <dependency><groupId>com.h2database</groupId><artifactId>h2</artifactId></dependency>"""))
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("H2 dependency found", result.stdout)

    def test_old_starter_name_fails_through_migration_scanner(self):
        self.write("pom.xml", pom().replace("spring-boot-starter-webmvc", "spring-boot-starter-web"))
        self.assertFails("Old starter: spring-boot-starter-web")

    def test_gradle_boot_version_is_read(self):
        (self.root / "pom.xml").unlink()
        self.write("build.gradle", """
            plugins { id 'org.springframework.boot' version '3.5.7' }
            dependencies { testImplementation 'com.enofex:taikai:2.1.0' }
            """)
        self.assertFails("Spring Boot 3.5.7")

    def test_no_build_file_exits_2(self):
        (self.root / "pom.xml").unlink()
        self.assertEqual(self.check().returncode, 2)


class PlaceholderSet(unittest.TestCase):

    def test_checked_placeholders_match_the_templates(self):
        used = set()
        for path in (SKILL / "assets").iterdir():
            used.update(re.findall(r"\{\{([A-Za-z_]+)\}\}", path.read_text(encoding="utf-8")))
        checked = re.search(r"PLACEHOLDER_RE = re\.compile\(r\"\\\{\\\{\(([^)]*)\)", SCRIPT.read_text()).group(1)
        self.assertEqual(set(checked.split("|")), used)


if __name__ == "__main__":
    unittest.main()
