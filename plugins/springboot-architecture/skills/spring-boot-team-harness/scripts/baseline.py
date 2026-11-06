#!/usr/bin/env python3
"""Make an existing project's build pass under the harness without hiding new problems.

Usage:
    python3 baseline.py <project-dir> [--dry-run]

Run it after apply_harness.py and the one-time formatting commit. It runs ./mvnw, or ./gradlew on a Gradle build. It holds new code to the gates and records what
already fails:

- NullAway: each class that fails today gets @NullUnmarked, so NullAway skips it while new and clean classes are checked.
  The opt-out is visible in the code; remove it from a class once that class is fixed.
- ArchUnit: CodeRulesTests and UnusedCodeTests run once and record today's violations in src/test/resources/archunit_store. New
  violations fail; fixed ones drop out of the record. Only this script creates the record: without it, every violation
  fails, so a fresh checkout or CI never records violations by itself. A rule the record doesn't list fails in full
  too; after a harness update adds rules, run this again to record theirs.
- Spring Modulith: when the project has ModuleBoundariesTests, it runs once in record mode and writes today's
  module-boundary violations to src/test/resources/modulith_store, one per line. Each is keyed by what it is, not
  where: a cycle by its modules, a disallowed dependency by its two modules, an internal-type access by caller and
  callee. New violations fail; a fixed one drops out the next time the test runs. Without the record, every
  violation fails. A rerun records only the violations still present.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ANNOTATION = "@org.jspecify.annotations.NullUnmarked"
# Maven prints "[ERROR] path:[line,column] [NullAway]", Gradle "path:line: error: [NullAway]".
NULLAWAY_ERROR = re.compile(r"^(?:\[ERROR\] (?P<maven>.+?\.java):\[\d+,\d+\]|(?P<gradle>\S.*?\.java):\d+: error:) \[NullAway\]",
                            re.M)
TYPE_DECLARATION = re.compile(
    r"^(?:(?:public|protected|private|abstract|final|sealed|non-sealed|static|strictfp)\s+)*"
    r"(?:class|interface|enum|record)\s+\w", re.M)
MAX_ROUNDS = 10
BOUNDARY_TEST = "ModuleBoundariesTests.java"
RECORD_FLAG = "modulith.store.record=true"
MODULITH_STORE = "src/test/resources/modulith_store"


def gradle_build_file(project: Path) -> Path | None:
    """The Gradle build file of a project without a pom, which apply_harness.py treats as a Gradle build."""
    if (project / "pom.xml").exists():
        return None
    return next((project / name for name in ("build.gradle.kts", "build.gradle") if (project / name).exists()), None)


def format_goal(project: Path) -> str:
    """The goal that formats the project: apply_harness.py keeps Spring Java Format where the build uses it."""
    if gradle_build_file(project):
        # apply_harness.py resolved the formatter, catalog aliases included, and configured Spotless only for it.
        script = project / "gradle" / "harness.gradle"
        text = script.read_text(encoding="utf-8") if script.exists() else ""
        return "spotlessApply" if re.search(r"^\s*spotless\s*\{", text, re.M) else "format"
    pom = project / "pom.xml"
    text = re.sub(r"<!--.*?-->", "", pom.read_text(encoding="utf-8"), flags=re.S) if pom.exists() else ""
    if re.search(r"<artifactId>\s*spring-javaformat-maven-plugin\s*</artifactId>", text):
        return "spring-javaformat:apply"
    return "spotless:apply"


def failing_files(output: str) -> set[Path]:
    """Source files with NullAway errors in the build's output. Maven prints Windows paths as /D:/..."""
    paths = set()
    for match in NULLAWAY_ERROR.finditer(output):
        path = match.group("maven") or match.group("gradle")
        paths.add(Path(path[1:] if re.match(r"/[A-Za-z]:/", path) else path))
    return paths


def mark(source: str) -> str | None:
    """The source with its top-level type marked @NullUnmarked, or None if it's already marked or has no type."""
    if re.search(r"@(org\.jspecify\.annotations\.)?NullUnmarked\b", source):
        return None
    declaration = TYPE_DECLARATION.search(source)
    if declaration is None:
        return None
    line_end = "\r\n" if "\r\n" in source else "\n"
    return source[:declaration.start()] + ANNOTATION + line_end + source[declaration.start():]


def build(project: Path, *args: str) -> tuple[int, str]:
    if gradle_build_file(project):
        command = [str(project / "gradlew.bat")] if os.name == "nt" else ["./gradlew"]
        command.append("-q")
    else:
        command = [str(project / "mvnw.cmd")] if os.name == "nt" else ["./mvnw"]
        command += ["-q", "-B"]
    result = subprocess.run([*command, *args], cwd=project, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    return result.returncode, result.stdout + result.stderr


def steps(project: Path) -> dict[str, tuple[str, ...]]:
    """The build arguments for each step. gradle/harness.gradle turns -Pharness.record=true into both record flags,
    since Gradle passes no -D to the test JVM; --rerun stops Gradle skipping a test run it thinks is up to date."""
    if gradle_build_file(project):
        return {"compile": ("compileJava",),
                "rules": ("test", "--rerun", "--tests", "*.CodeRulesTests", "--tests", "*.UnusedCodeTests",
                          "-Pharness.record=true"),
                "modules": ("test", "--rerun", "--tests", "*.ModuleBoundariesTests", "-Pharness.record=true")}
    return {"compile": ("compile",),
            "rules": ("test", "-Dtest=CodeRulesTests,UnusedCodeTests",
                      "-Darchunit.freeze.store.default.allowStoreCreation=true", "-Dsurefire.failIfNoSpecifiedTests=false"),
            "modules": ("test", "-Dtest=ModuleBoundariesTests", f"-D{RECORD_FLAG}",
                        "-Dsurefire.failIfNoSpecifiedTests=false")}


def wrapper_and_verify(project: Path) -> tuple[str, str]:
    return ("./gradlew", "./gradlew build") if gradle_build_file(project) else ("./mvnw", "./mvnw verify")


def record_module_violations(project: Path):
    if not any((project / "src" / "test").rglob(BOUNDARY_TEST)):
        return
    code, output = build(project, *steps(project)["modules"])
    if code != 0:
        sys.exit("ERROR: ModuleBoundariesTests failed while recording today's module-boundary violations:\n"
                 + output[-3000:])
    store = project / MODULITH_STORE
    count = len(store.read_text(encoding="utf-8").splitlines()) if store.exists() else 0
    print(f"Spring Modulith: recorded {count} module-boundary violations in {MODULITH_STORE}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("project")
    parser.add_argument("--dry-run", action="store_true", help="Report the classes NullAway rejects without changing them")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    project = Path(args.project).resolve()

    marked: list[Path] = []
    for _ in range(MAX_ROUNDS):
        code, output = build(project, *steps(project)["compile"])
        files = failing_files(output)
        if code == 0 or not files:
            break
        if args.dry_run:
            marked = sorted(files)
            break
        progress = False
        for path in sorted(files):
            with path.open(encoding="utf-8", newline="") as source:
                updated = mark(source.read())
            if updated is not None:
                path.write_text(updated, encoding="utf-8", newline="")
                marked.append(path)
                progress = True
        if not progress:
            sys.exit("ERROR: NullAway still fails in classes that are already marked:\n"
                     + "\n".join(f"  {path}" for path in sorted(files)))

    verb = "would mark" if args.dry_run else "marked"
    print(f"NullAway: {verb} {len(marked)} classes @NullUnmarked")
    for path in marked:
        print(f"  {path.relative_to(project).as_posix() if path.is_relative_to(project) else path}")
    if args.dry_run:
        return
    if code != 0:
        sys.exit("ERROR: the project still doesn't compile, for reasons other than NullAway:\n" + output[-3000:])

    code, output = build(project, *steps(project)["rules"])
    if code != 0:
        sys.exit("ERROR: the ArchUnit rule tests failed while recording today's violations:\n" + output[-3000:])
    print("ArchUnit: recorded today's violations in src/test/resources/archunit_store")
    record_module_violations(project)
    goal = format_goal(project)
    wrapper, verify = wrapper_and_verify(project)
    code, output = build(project, goal)
    if code != 0:
        sys.exit(f"ERROR: {goal} failed, so the marked classes may not be formatted. The NullAway marks and the "
                 f"ArchUnit record are in place; fix the formatter error, rerun {wrapper} {goal}, then commit:\n"
                 + output[-3000:])
    print(f"\nNext: {verify}, then commit the marked classes, archunit_store and modulith_store.")


if __name__ == "__main__":
    main()
