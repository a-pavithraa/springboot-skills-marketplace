"""Regression tests for springboot-migration/scripts/scan_migration_issues.py.

Run from the repository root:
    python3 -m unittest discover -s tests/scripts -v
"""

import contextlib
import importlib.util
import io
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPT = (Path(__file__).resolve().parents[2] / "plugins/springboot-architecture/skills"
          / "springboot-migration/scripts/scan_migration_issues.py")
spec = importlib.util.spec_from_file_location("scan_migration_issues", SCRIPT)
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)

BOOT4_PARENT = """
<parent>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-starter-parent</artifactId>
  <version>4.1.1</version>
</parent>
"""
MODULITH_DEP = """
<dependency>
  <groupId>org.springframework.modulith</groupId>
  <artifactId>spring-modulith-starter-jdbc</artifactId>
</dependency>
"""


def pom(dependencies: str, namespace: str = "") -> str:
    return f"<project{namespace}>{BOOT4_PARENT}<dependencies>{dependencies}</dependencies></project>\n"


class ScannerTestCase(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, relative: str, content: str):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content), encoding="utf-8")

    def issues(self):
        with contextlib.redirect_stdout(io.StringIO()):
            result = scanner.MigrationScanner(str(self.root)).scan()
        return [issue.issue for issue in result.issues]

    def assertIssue(self, text):
        self.assertTrue(any(text in i for i in self.issues()), f"expected issue containing {text!r}")

    def assertNoIssue(self, text):
        found = [i for i in self.issues() if text in i]
        self.assertEqual(found, [], f"unexpected issue(s) containing {text!r}")


class MavenDependencyBoundaries(ScannerTestCase):

    def test_neighbouring_dependency_group_is_not_borrowed(self):
        self.write("pom.xml", pom("""
            <dependency>
            <groupId>org.example</groupId>
            <artifactId>utilities</artifactId>
            </dependency><dependency>
            <groupId>org.testcontainers</groupId>
            <artifactId>testcontainers-postgresql</artifactId>
            </dependency>"""))
        self.assertNoIssue("Old Testcontainers artifact")

    def test_old_testcontainers_artifact_is_reported_with_its_line(self):
        self.write("pom.xml", pom("""
            <dependency>
              <groupId>org.testcontainers</groupId>
              <artifactId>postgresql</artifactId>
            </dependency>"""))
        with contextlib.redirect_stdout(io.StringIO()):
            result = scanner.MigrationScanner(str(self.root)).scan()
        found = [i for i in result.issues if i.issue == "Old Testcontainers artifact: postgresql"]
        self.assertEqual(len(found), 1)
        line = (self.root / "pom.xml").read_text().splitlines()[found[0].line_number - 1]
        self.assertIn("<artifactId>postgresql</artifactId>", line)

    def test_exclusion_coordinates_are_ignored(self):
        self.write("pom.xml", pom("""
            <dependency>
              <groupId>com.example</groupId>
              <artifactId>client</artifactId>
              <exclusions>
                <exclusion>
                  <groupId>org.testcontainers</groupId>
                  <artifactId>junit-jupiter</artifactId>
                </exclusion>
              </exclusions>
            </dependency>"""))
        self.assertNoIssue("Old Testcontainers artifact")

    def test_namespace_prefixed_elements_are_parsed(self):
        self.write("pom.xml", f"""<pom:project xmlns:pom="http://maven.apache.org/POM/4.0.0">
            <pom:dependencies><pom:dependency>
              <pom:groupId>org.springframework.boot</pom:groupId>
              <pom:artifactId>spring-boot-starter-web</pom:artifactId>
            </pom:dependency></pom:dependencies></pom:project>""")
        self.assertIssue("Old starter: spring-boot-starter-web")

    def test_third_party_artifact_with_starter_name_is_ignored(self):
        self.write("pom.xml", pom("""
            <dependency>
              <groupId>com.thirdparty</groupId>
              <artifactId>spring-boot-starter-web</artifactId>
            </dependency>"""))
        self.assertNoIssue("Old starter")

    def test_commented_out_dependency_is_ignored(self):
        self.write("pom.xml", pom("""
            <!--
            <dependency>
              <groupId>org.springframework.retry</groupId>
              <artifactId>spring-retry</artifactId>
            </dependency>
            -->"""))
        self.assertNoIssue("spring-retry")


class ModulithSchemaDetection(ScannerTestCase):

    def setUp(self):
        super().setUp()
        self.write("pom.xml", pom(MODULITH_DEP))
        self.write("src/main/resources/db/migration/V1__init.sql", "SELECT 1;\n")

    def test_unrelated_yaml_jdbc_schema_is_ignored(self):
        self.write("src/main/resources/application.yml", """
            custom:
              jdbc:
                schema: unrelated
            """)
        self.assertNoIssue("schema")

    def test_nested_yaml_schema_is_detected(self):
        self.write("src/main/resources/application.yml", """
            spring:
              modulith:
                events:
                  jdbc:
                    schema-initialization:
                      enabled: false
                    schema: evts   # dedicated schema
            """)
        self.assertIssue("'evts' schema")

    def test_dotted_yaml_key_is_detected(self):
        self.write("src/main/resources/application.yaml", """
            spring.modulith.events:
              jdbc.schema: "evts"
            """)
        self.assertIssue("'evts' schema")

    def test_schema_initialization_property_is_not_a_schema(self):
        self.write("src/main/resources/application.properties",
                   "spring.modulith.events.jdbc.schema-initialization.enabled=true\n")
        self.assertNoIssue("schema")

    def test_commented_create_schema_does_not_count(self):
        self.write("src/main/resources/application.properties", "spring.modulith.events.jdbc.schema=events\n")
        self.write("src/main/resources/db/migration/V2__schema.sql", """
            -- CREATE SCHEMA events;
            /* CREATE SCHEMA IF NOT EXISTS events; */
            SELECT '-- not a comment';
            """)
        self.assertIssue("'events' schema")

    def test_real_create_schema_after_string_with_dashes_counts(self):
        self.write("src/main/resources/application.properties", "spring.modulith.events.jdbc.schema=events\n")
        self.write("src/main/resources/db/migration/V2__schema.sql", """
            SELECT 'it''s -- fine';
            CREATE SCHEMA IF NOT EXISTS events;
            """)
        self.assertNoIssue("'events' schema")


class HelperFunctions(unittest.TestCase):

    def test_strip_sql_comments_keeps_quoted_text(self):
        sql = "SELECT '/* keep */ -- keep' AS x; -- drop\n/* drop */ SELECT 1;"
        self.assertEqual(scanner._strip_sql_comments(sql), "SELECT '/* keep */ -- keep' AS x; \n  SELECT 1;")

    def test_yaml_values_resets_paths_between_documents(self):
        values = scanner._yaml_values("a:\n  b: 1\n---\nb: 2\n")
        self.assertEqual(values, {"a.b": "1", "b": "2"})


if __name__ == "__main__":
    unittest.main()
