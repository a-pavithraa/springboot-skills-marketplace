#!/usr/bin/env python3
"""
New Project Check

Checks a newly created Spring Boot project against what this skill promises,
so the result doesn't depend on what the agent remembered to do:

- no unresolved {{PLACEHOLDER}} from the templates in assets/
- Spring Boot on the current 4.x line
- the Taikai architecture test (Step 6) and its test dependency
- no in-memory H2 in place of Testcontainers
- Boot 4 starter and Testcontainers 2 names, via the springboot-migration
  scanner when it is installed next to this skill

Usage:
    python3 check_new_project.py /path/to/project

Exit codes: 0 = no failures (warnings may print), 1 = at least one failure,
2 = no pom.xml or build.gradle(.kts) found.
"""

import argparse
import contextlib
import importlib.util
import io
import re
import sys
from pathlib import Path

# Newest Spring Boot minor line (checked 2026-10-21)
CURRENT_BOOT = (4, 1)
# The placeholders used in assets/ (SKILL.md, "Placeholder convention"). Only these
# count: progen's Taskfile.yml, for one, has Go template syntax such as {{else}}.
PLACEHOLDER_RE = re.compile(r"\{\{(PACKAGE|MODULE|NAME|TYPE|FIELD|TABLE_NAME|TABLE|PROJECT_NAME|name)\}\}")
SKIP_DIRS = {"target", "build", "node_modules", "out", "bin"}
SCANNER = (Path(__file__).resolve().parents[2] / "springboot-migration"
           / "scripts" / "scan_migration_issues.py")


def project_files(root: Path, pattern: str):
    """Files under root, skipping build output and hidden directories (.git, .claude/skills, ...)."""
    for path in root.rglob(pattern):
        parts = path.relative_to(root).parts[:-1]
        if path.is_file() and not any(p in SKIP_DIRS or p.startswith(".") for p in parts):
            yield path


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def boot_version(build_text: str):
    patterns = [
        r"<artifactId>\s*spring-boot-starter-parent\s*</artifactId>\s*<version>\s*([\w.-]+)\s*</version>",
        r"<artifactId>\s*spring-boot-dependencies\s*</artifactId>\s*<version>\s*([\w.-]+)\s*</version>",
        r"""id\s*\(?\s*['"]org\.springframework\.boot['"]\s*\)?\s*version\s*['"]([\w.-]+)['"]""",
    ]
    for pattern in patterns:
        match = re.search(pattern, build_text)
        if match:
            return match.group(1)
    return None


class Report:
    def __init__(self):
        self.failures = []
        self.warnings = []

    def fail(self, message: str):
        self.failures.append(message)

    def warn(self, message: str):
        self.warnings.append(message)


def check_placeholders(root: Path, report: Report):
    found = []
    for pattern in ("*.java", "*.xml", "*.gradle", "*.kts", "*.sql", "*.properties", "*.yml", "*.yaml"):
        for path in project_files(root, pattern):
            for number, line in enumerate(read(path).splitlines(), 1):
                for match in PLACEHOLDER_RE.finditer(line):
                    found.append(f"{path.relative_to(root)}:{number} {match.group(0)}")
    if found:
        report.fail("Unresolved template placeholders (replace every one; see the placeholder table in SKILL.md):\n"
                    + "\n".join(f"    {item}" for item in found[:20])
                    + (f"\n    ... and {len(found) - 20} more" if len(found) > 20 else ""))


def check_boot_version(build_text: str, report: Report):
    version = boot_version(build_text)
    if version is None:
        report.warn("Spring Boot version not found in the build file; check it by hand.")
        return
    match = re.match(r"(\d+)\.(\d+)", version)
    if not match:
        report.warn(f"Spring Boot version '{version}' is not a literal version; check it by hand.")
        return
    line = (int(match.group(1)), int(match.group(2)))
    current = f"{CURRENT_BOOT[0]}.{CURRENT_BOOT[1]}"
    if line[0] < CURRENT_BOOT[0]:
        report.fail(f"Spring Boot {version}: new projects start on the current {current}.x line, "
                    "not the previous major version.")
    elif line < CURRENT_BOOT:
        report.warn(f"Spring Boot {version} is not on the current {current}.x line.")
    else:
        print(f"OK   Spring Boot {version}")


def check_architecture_test(root: Path, build_text: str, report: Report):
    has_dependency = "com.enofex" in build_text and "taikai" in build_text
    tests = [p for p in project_files(root / "src" / "test", "*.java")
             if "com.enofex.taikai" in read(p)] if (root / "src" / "test").is_dir() else []
    if not tests:
        report.fail("No Taikai architecture test in src/test. Add assets/architecture-rules-test.java "
                    "(Step 6 of SKILL.md).")
    elif not has_dependency:
        report.fail("A Taikai test exists, but the build file has no com.enofex:taikai test dependency.")
    else:
        print(f"OK   architecture test: {', '.join(str(p.relative_to(root)) for p in tests)}")


def check_no_h2(build_text: str, report: Report):
    if "com.h2database" in build_text:
        report.warn("H2 dependency found. Tests here use the real database through Testcontainers; "
                    "remove H2 unless the user asked for it.")


def check_boot4_names(root: Path, report: Report):
    if not SCANNER.exists():
        report.warn("springboot-migration scanner not installed next to this skill; "
                    "Boot 4 starter and Testcontainers 2 names were not checked.")
        return
    spec = importlib.util.spec_from_file_location("scan_migration_issues", SCANNER)
    scanner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scanner)
    with contextlib.redirect_stdout(io.StringIO()):
        result = scanner.MigrationScanner(str(root)).scan()
    critical = [i for i in result.issues if i.severity == "CRITICAL"]
    for issue in critical:
        report.fail(f"{issue.file_path}:{issue.line_number} {issue.issue}. Fix: {issue.suggestion}")
    if not critical:
        print("OK   Boot 4 starters and Testcontainers 2 names (migration scanner: no critical issues)")


def main():
    parser = argparse.ArgumentParser(description="Check a new Spring Boot project against this skill")
    parser.add_argument("project_path")
    args = parser.parse_args()

    root = Path(args.project_path).resolve()
    build_files = [root / name for name in ("pom.xml", "build.gradle", "build.gradle.kts")
                   if (root / name).exists()]
    if not build_files:
        print(f"ERROR: no pom.xml or build.gradle(.kts) in {root}", file=sys.stderr)
        sys.exit(2)
    build_text = "\n".join(read(path) for path in build_files)

    report = Report()
    check_placeholders(root, report)
    check_boot_version(build_text, report)
    check_architecture_test(root, build_text, report)
    check_no_h2(build_text, report)
    check_boot4_names(root, report)

    for warning in report.warnings:
        print(f"WARN {warning}")
    for failure in report.failures:
        print(f"FAIL {failure}")
    if report.failures:
        print(f"\nCHECK FAILED: {len(report.failures)} failure(s)")
        sys.exit(1)
    print("\nCHECK PASSED")


if __name__ == "__main__":
    main()
