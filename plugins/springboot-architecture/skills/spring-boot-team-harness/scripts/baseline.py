#!/usr/bin/env python3
"""Make an existing project's build pass under the harness without hiding new problems.

Usage:
    python3 baseline.py <project-dir> [--dry-run]

Run it after apply_harness.py and the one-time formatting commit. It holds new code to the gates and records what
already fails:

- NullAway: each class that fails today gets @NullUnmarked, so NullAway skips it while new and clean code is checked.
  The opt-out is visible in the code; remove it from a class once that class is fixed.
- ArchUnit: CodeRulesTests and UnusedCodeTests run once and record today's violations in src/test/resources/archunit_store. New
  violations fail; fixed ones drop out of the record. Only this script creates the record: without it, every violation
  fails, so a fresh checkout or CI never records violations by itself. A rule the record doesn't list fails in full
  too; after a harness update adds rules, run this again to record theirs.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ANNOTATION = "@org.jspecify.annotations.NullUnmarked"
NULLAWAY_ERROR = re.compile(r"^\[ERROR\] (?P<path>.+?\.java):\[\d+,\d+\] \[NullAway\]", re.M)
TYPE_DECLARATION = re.compile(
    r"^(?:(?:public|protected|private|abstract|final|sealed|non-sealed|static|strictfp)\s+)*"
    r"(?:class|interface|enum|record)\s+\w", re.M)
MAX_ROUNDS = 10


def failing_files(output: str) -> set[Path]:
    """Source files with NullAway errors in Maven's output. Windows paths arrive as /D:/..."""
    paths = set()
    for match in NULLAWAY_ERROR.finditer(output):
        path = match.group("path")
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


def maven(project: Path, *args: str) -> tuple[int, str]:
    command = [str(project / "mvnw.cmd")] if os.name == "nt" else ["./mvnw"]
    result = subprocess.run([*command, "-q", "-B", *args], cwd=project, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    return result.returncode, result.stdout + result.stderr


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("project")
    parser.add_argument("--dry-run", action="store_true", help="Report the classes NullAway rejects without changing them")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    project = Path(args.project).resolve()

    marked: list[Path] = []
    for _ in range(MAX_ROUNDS):
        code, output = maven(project, "compile")
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

    code, output = maven(project, "test", "-Dtest=CodeRulesTests,UnusedCodeTests",
                         "-Darchunit.freeze.store.default.allowStoreCreation=true", "-Dsurefire.failIfNoSpecifiedTests=false")
    if code != 0:
        sys.exit("ERROR: the ArchUnit rule tests failed while recording today's violations:\n" + output[-3000:])
    print("ArchUnit: recorded today's violations in src/test/resources/archunit_store")
    code, output = maven(project, "spotless:apply")
    if code != 0:
        sys.exit("ERROR: spotless:apply failed, so the marked classes may not be formatted. The NullAway marks and the "
                 "ArchUnit record are in place; fix the formatter error, rerun ./mvnw spotless:apply, then commit:\n"
                 + output[-3000:])
    print("\nNext: ./mvnw verify, then commit the marked classes and archunit_store.")


if __name__ == "__main__":
    main()
