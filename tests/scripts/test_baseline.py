"""Regression tests for spring-boot-team-harness/scripts/baseline.py.

Run from the repository root:
    python3 -m unittest discover -s tests/scripts -v
"""

import contextlib
import importlib.util
import io
import sys
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
        with mock.patch.object(baseline, "maven", maven), mock.patch.object(sys, "argv", ["baseline.py", "."]), \
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

    def test_a_formatting_failure_stops_with_the_formatter_output(self):
        with self.assertRaises(SystemExit) as stopped:
            self.run_main(1)
        self.assertIn("spotless:apply failed", str(stopped.exception))
        self.assertIn("bad formatter config", str(stopped.exception))


if __name__ == "__main__":
    unittest.main()
