"""Regression tests for spring-boot-team-harness/scripts/baseline.py.

Run from the repository root:
    python3 -m unittest discover -s tests/scripts -v
"""

import contextlib
import importlib.util
import io
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[2] / (
    "plugins/springboot-architecture/skills/spring-boot-team-harness/scripts/baseline.py")
spec = importlib.util.spec_from_file_location("baseline", SCRIPT)
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)


class FailingFilesTests(unittest.TestCase):

    def test_reads_nullaway_errors_with_windows_and_posix_paths(self):
        output = textwrap.dedent("""\
            [ERROR] COMPILATION ERROR :
            [ERROR] /D:/pills/app/src/main/java/com/acme/Users.java:[22,44] [NullAway] passing @Nullable parameter
            [ERROR] /D:/pills/app/src/main/java/com/acme/Users.java:[32,9] [NullAway] returning @Nullable expression
            [ERROR] /home/ci/app/src/main/java/com/acme/Orders.java:[7,5] [NullAway] dereferenced expression
            [ERROR] /home/ci/app/src/main/java/com/acme/Other.java:[3,1] cannot find symbol
            """)
        self.assertEqual(baseline.failing_files(output),
                         {Path("D:/pills/app/src/main/java/com/acme/Users.java"),
                          Path("/home/ci/app/src/main/java/com/acme/Orders.java")})


class MarkTests(unittest.TestCase):

    def test_annotates_the_top_level_type_after_its_other_annotations(self):
        source = textwrap.dedent("""\
            package com.acme;

            import org.springframework.stereotype.Service;

            /** Users. */
            @Service
            public class Users {
                static class Nested {}
            }
            """)
        marked = baseline.mark(source)
        self.assertIn("@Service\n@org.jspecify.annotations.NullUnmarked\npublic class Users {", marked)
        self.assertEqual(marked.count("NullUnmarked"), 1)

    def test_handles_records_and_modifiers(self):
        marked = baseline.mark("package a;\n\npublic sealed interface Shape permits Circle {}\n")
        self.assertIn("@org.jspecify.annotations.NullUnmarked\npublic sealed interface Shape", marked)
        marked = baseline.mark("package a;\n\nrecord Point(int x) {}\n")
        self.assertIn("@org.jspecify.annotations.NullUnmarked\nrecord Point", marked)

    def test_keeps_windows_line_endings(self):
        marked = baseline.mark("package a;\r\n\r\nclass A {}\r\n")
        self.assertEqual(marked, "package a;\r\n\r\n@org.jspecify.annotations.NullUnmarked\r\nclass A {}\r\n")

    def test_leaves_a_class_that_is_already_marked(self):
        self.assertIsNone(baseline.mark("package a;\n\n@NullUnmarked\nclass A {}\n"))
        self.assertIsNone(baseline.mark("package a;\n\n@org.jspecify.annotations.NullUnmarked\nclass A {}\n"))


class MainTests(unittest.TestCase):

    def run_main(self, spotless_code: int) -> tuple[list[tuple[str, ...]], str]:
        calls: list[tuple[str, ...]] = []

        def maven(project, *args):
            calls.append(args)
            if args[0] == "spotless:apply":
                return spotless_code, "[ERROR] spotless: bad formatter config"
            return 0, ""

        out = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")  # main() calls reconfigure, which StringIO lacks
        with mock.patch.object(baseline, "build", maven), mock.patch.object(sys, "argv", ["baseline.py", "."]), \
                contextlib.redirect_stdout(out):
            try:
                baseline.main()
            finally:
                out.flush()
        return calls, out.buffer.getvalue().decode("utf-8")

    def test_a_clean_run_formats_and_prints_the_next_step(self):
        calls, printed = self.run_main(0)
        self.assertEqual(calls[-1], ("spotless:apply",))
        self.assertIn("Next: ./mvnw verify", printed)

    def test_records_module_violations_only_when_the_project_has_the_boundary_test(self):
        calls, printed = self.run_main(0)
        self.assertNotIn("-Dmodulith.store.record=true", [arg for call in calls for arg in call])
        self.assertNotIn("Spring Modulith", printed)

        project = Path(tempfile.mkdtemp())
        test = project / "src/test/java/com/acme/ModuleBoundariesTests.java"
        test.parent.mkdir(parents=True)
        test.write_text("class ModuleBoundariesTests {}\n")
        (project / "src/test/resources").mkdir(parents=True)
        (project / baseline.MODULITH_STORE).write_text("cycle|a,b\ndependency|c|a\n")
        with mock.patch.object(baseline.Path, "resolve", lambda self: project):
            calls, printed = self.run_main(0)
        self.assertIn(("test", "-Dtest=ModuleBoundariesTests", "-Dmodulith.store.record=true",
                       "-Dsurefire.failIfNoSpecifiedTests=false"), calls)
        self.assertIn("recorded 2 module-boundary violations", printed)

    def test_formats_with_spring_java_format_when_the_pom_uses_it(self):
        project = Path(tempfile.mkdtemp())
        (project / "pom.xml").write_text("<project><build><plugins><plugin>"
                                         "<artifactId>spring-javaformat-maven-plugin</artifactId>"
                                         "</plugin></plugins></build></project>\n")
        with mock.patch.object(baseline.Path, "resolve", lambda self: project):
            calls, _ = self.run_main(0)
        self.assertEqual(calls[-1], ("spring-javaformat:apply",))

    def test_a_formatting_failure_stops_with_the_formatter_output(self):
        with self.assertRaises(SystemExit) as stopped:
            self.run_main(1)
        self.assertIn("spotless:apply failed", str(stopped.exception))
        self.assertIn("bad formatter config", str(stopped.exception))

    def gradle_project(self, build: str = "plugins { id 'java' }\n", script: str = "spotless {\n}\n") -> Path:
        project = Path(tempfile.mkdtemp())
        (project / "build.gradle").write_text(build)
        (project / "gradle").mkdir()
        (project / "gradle/harness.gradle").write_text(script)
        test = project / "src/test/java/com/acme/ModuleBoundariesTests.java"
        test.parent.mkdir(parents=True)
        test.write_text("class ModuleBoundariesTests {}\n")
        return project

    def test_on_gradle_it_runs_the_harness_tasks_and_records_through_the_harness_property(self):
        with mock.patch.object(baseline.Path, "resolve", lambda self, project=self.gradle_project(): project):
            calls, printed = self.run_main(0)
        self.assertEqual(calls, [("compileJava",),
                                 ("test", "--rerun", "--tests", "*.CodeRulesTests", "--tests", "*.UnusedCodeTests",
                                  "-Pharness.record=true"),
                                 ("test", "--rerun", "--tests", "*.ModuleBoundariesTests", "-Pharness.record=true"),
                                 ("spotlessApply",)])
        self.assertIn("Next: ./gradlew build", printed)

    def test_on_gradle_with_spring_java_format_it_formats_with_its_task(self):
        project = self.gradle_project("plugins { alias(libs.plugins.spring.javaformat) }\n",
                                      script="dependencies {}\n")
        with mock.patch.object(baseline.Path, "resolve", lambda self: project):
            calls, _ = self.run_main(0)
        self.assertEqual(calls[-1], ("format",))

    def test_reads_gradle_nullaway_errors(self):
        output = textwrap.dedent("""\
            /home/ci/app/src/main/java/com/acme/Orders.java:7: error: [NullAway] dereferenced expression
            D:\\app\\src\\main\\java\\com\\acme\\Users.java:22: error: [NullAway] passing @Nullable parameter
            /home/ci/app/src/main/java/com/acme/Other.java:3: error: cannot find symbol

            * What went wrong:
              /home/ci/app/src/main/java/com/acme/Orders.java:7: error: [NullAway] dereferenced expression
            """)
        self.assertEqual(baseline.failing_files(output),
                         {Path("/home/ci/app/src/main/java/com/acme/Orders.java"),
                          Path("D:\\app\\src\\main\\java\\com\\acme\\Users.java")})


if __name__ == "__main__":
    unittest.main()
