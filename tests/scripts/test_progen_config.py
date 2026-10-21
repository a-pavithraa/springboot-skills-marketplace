"""Regression tests for creating-springboot-projects/scripts/progen_config.py.

A fake `progen` executable on PATH stands in for the real binary.

Run from the repository root:
    python3 -m unittest discover -s tests/scripts -v
"""

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPT = (Path(__file__).resolve().parents[2] / "plugins/springboot-architecture/skills"
          / "creating-springboot-projects/scripts/progen_config.py")

POM = "<project><properties>\n    <java.version>25</java.version>\n</properties></project>\n"


class ProgenConfigTestCase(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.out = self.root / "out"
        self.out.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.fake_java('openjdk version "25.0.4.1" 2026-08-18 LTS')

    def tearDown(self):
        self._tmp.cleanup()

    def fake_progen(self, body: str):
        """Install a fake progen; its working directory is --out-dir."""
        script = self.bin / "progen"
        script.write_text("#!/bin/sh\n" + textwrap.dedent(body), encoding="utf-8")
        script.chmod(0o755)

    def fake_java(self, version_line: str):
        """Install a fake java that prints version_line the way java -version does (to stderr)."""
        script = self.bin / "java"
        script.write_text(f"#!/bin/sh\necho '{version_line}' >&2\n", encoding="utf-8")
        script.chmod(0o755)

    def run_script(self, *args, use_fake=True):
        env = dict(os.environ)
        env.pop("JAVA_HOME", None)
        if use_fake:
            env["PATH"] = f"{self.bin}{os.pathsep}{env['PATH']}"
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--out-dir", str(self.out), *args],
            capture_output=True, text=True, env=env)


class Validation(ProgenConfigTestCase):

    def test_valid_config_is_written(self):
        result = self.run_script("--app-name", "shop", "--base-package", "com.acme.shop", "--features", "redis")
        self.assertEqual(result.returncode, 0, result.stderr)
        config = json.loads((self.out / ".progen.json").read_text())
        self.assertEqual(config["PersistenceType"], "Spring Data JPA")
        self.assertTrue(config["RedisCachingSupport"])
        self.assertEqual(config["GroupID"], "com.acme")

    def test_java_keyword_in_package_is_rejected(self):
        for package in ("com.class.demo", "com.acme.new", "true.acme", "com._.x"):
            with self.subTest(package=package):
                result = self.run_script("--app-name", "shop", "--base-package", package)
                self.assertEqual(result.returncode, 1)
                self.assertIn("not a valid Java package", result.stderr)

    def test_invalid_package_shapes_are_rejected(self):
        for package in ("com..acme", "1com.acme", "com.Acme", "com.acme."):
            with self.subTest(package=package):
                self.assertEqual(self.run_script("--app-name", "shop", "--base-package", package).returncode, 1)

    def test_path_like_app_name_is_rejected(self):
        for name in ("..", ".", "../x", "Shop"):
            with self.subTest(name=name):
                self.assertEqual(self.run_script("--app-name", name, "--base-package", "com.acme").returncode, 1)

    def test_existing_target_directory_is_never_replaced(self):
        (self.out / "shop").mkdir()
        (self.out / "shop" / "keep.txt").write_text("data")
        self.fake_progen("rm -rf shop\n")
        result = self.run_script("--app-name", "shop", "--base-package", "com.acme.shop", "--run")
        self.assertEqual(result.returncode, 2)
        self.assertTrue((self.out / "shop" / "keep.txt").exists())

    def test_htmx_requires_web_app(self):
        result = self.run_script("--app-name", "shop", "--base-package", "com.acme", "--features", "htmx")
        self.assertEqual(result.returncode, 1)


class RunningProgen(ProgenConfigTestCase):

    def test_success_sets_java_version(self):
        self.fake_progen(f"mkdir -p shop && printf '%s' '{POM}' > shop/pom.xml\n")
        result = self.run_script("--app-name", "shop", "--base-package", "com.acme.shop", "--run", "--java", "27")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("<java.version>27</java.version>", (self.out / "shop" / "pom.xml").read_text())

    def test_formatting_failure_is_a_warning(self):
        self.fake_progen(f"""
            mkdir -p shop && printf '%s' '{POM}' > shop/pom.xml
            echo "failed to format project code: exit status 1"
            exit 1
            """)
        result = self.run_script("--app-name", "shop", "--base-package", "com.acme.shop", "--run")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("formatting step failed", result.stdout)

    def test_unexpected_failure_with_build_file_is_an_error(self):
        self.fake_progen(f"""
            mkdir -p shop && printf '%s' '{POM}' > shop/pom.xml
            echo "panic: template error"
            exit 1
            """)
        result = self.run_script("--app-name", "shop", "--base-package", "com.acme.shop", "--run")
        self.assertEqual(result.returncode, 4)
        self.assertIn("may be incomplete", result.stderr)

    def test_missing_build_file_is_an_error(self):
        self.fake_progen("exit 0\n")
        result = self.run_script("--app-name", "shop", "--base-package", "com.acme.shop", "--run")
        self.assertEqual(result.returncode, 4)

    def test_java_version_not_found_is_reported(self):
        self.fake_progen("mkdir -p shop && echo '<project/>' > shop/pom.xml\n")
        result = self.run_script("--app-name", "shop", "--base-package", "com.acme.shop", "--run", "--java", "21")
        self.assertEqual(result.returncode, 5)
        self.assertNotIn("Set Java version", result.stdout)

    def test_gradle_java_version_is_set(self):
        self.fake_progen("""
            mkdir -p shop
            echo 'java { toolchain { languageVersion = JavaLanguageVersion.of(25) } }' > shop/build.gradle
            """)
        result = self.run_script("--app-name", "shop", "--base-package", "com.acme.shop",
                                 "--build-tool", "gradle", "--run", "--java", "21")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("JavaLanguageVersion.of(21)", (self.out / "shop" / "build.gradle").read_text())


class JdkCheck(ProgenConfigTestCase):

    def setUp(self):
        super().setUp()
        self.fake_progen(f"mkdir -p shop && printf '%s' '{POM}' > shop/pom.xml\n")

    def test_newer_jdk_is_refused_before_progen_runs(self):
        self.fake_java('openjdk version "27" 2026-09-15')
        result = self.run_script("--app-name", "shop", "--base-package", "com.acme.shop", "--run")
        self.assertEqual(result.returncode, 6)
        self.assertIn("JDK 25", result.stderr)
        self.assertFalse((self.out / "shop").exists())

    def test_newer_jdk_runs_with_override(self):
        self.fake_java('openjdk version "27" 2026-09-15')
        result = self.run_script("--app-name", "shop", "--base-package", "com.acme.shop", "--run",
                                 "--ignore-jdk-check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_java_home_wins_over_path(self):
        self.fake_java('openjdk version "27" 2026-09-15')
        jdk25 = self.root / "jdk25"
        (jdk25 / "bin").mkdir(parents=True)
        java = jdk25 / "bin" / "java"
        java.write_text("#!/bin/sh\necho 'openjdk version \"25.0.4.1\" 2026-08-18 LTS' >&2\n", encoding="utf-8")
        java.chmod(0o755)
        env = dict(os.environ, PATH=f"{self.bin}{os.pathsep}{os.environ['PATH']}", JAVA_HOME=str(jdk25))
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--out-dir", str(self.out),
             "--app-name", "shop", "--base-package", "com.acme.shop", "--run"],
            capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_older_jdk_than_target_is_a_warning(self):
        self.fake_java('openjdk version "21.0.5" 2024-10-15')
        result = self.run_script("--app-name", "shop", "--base-package", "com.acme.shop", "--run")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("targets Java 25", result.stdout)

    def test_legacy_version_string_is_parsed(self):
        self.fake_java('java version "1.8.0_402"')
        result = self.run_script("--app-name", "shop", "--base-package", "com.acme.shop", "--run")
        self.assertIn("JDK in use is 8", result.stdout)


if __name__ == "__main__":
    unittest.main()
