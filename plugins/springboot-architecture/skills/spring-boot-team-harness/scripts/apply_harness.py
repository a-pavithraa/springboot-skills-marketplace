#!/usr/bin/env python3
"""Add the team harness to a Maven Spring Boot project: AGENTS.md, Claude Code settings, and ./mvnw verify gates.

Usage:
    python3 apply_harness.py <project-dir> [--base-package com.example.app] [--nullaway all|marked] [--dry-run]

The pom gets NullAway (JSpecify mode, main code only; every class under the base package, or with --nullaway marked
only @NullMarked packages) through Error Prone, Spotless with palantir-java-format,
Spring Modulith's test starter, and ArchUnit. Four tests are added: ConfigurationKeysTests, CodeRulesTests,
BuildSetupTests and ModuleBoundariesTests. A GitHub Actions workflow that runs ./mvnw verify is added when no
workflow runs mvnw. Claude Code hooks run the fast gates when a turn ends, and block destructive git commands, edits
to migrations already on main, and edits to the rule tests.
Files that already exist are left alone and reported, except CLAUDE.md, which gets an `@AGENTS.md` import as its
first line, and the files the harness owns (hooks, tests, project skills, its workflow): .claude/harness.lock records
what was written, and a rerun updates each one nobody has edited since. Running it twice changes nothing.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"
MARKER = "harness:begin"
TAG = re.compile(r"<!--.*?-->|<(/?)([\w.:-]+)[^>]*?(/?)>", re.S)
ITEM = re.compile(r"^ *<(?P<kind>dependency|plugin)>.*?^ *</(?P=kind)>\n|^ *<(?P<property>[\w.-]+)>[^<]*</(?P=property)>\n",
                  re.S | re.M)
MODULE_BLOCK = re.compile(r"<!-- modules:begin -->\n(.*?)<!-- modules:end -->\n", re.S)
SKILL_DIRS = (".claude/skills", ".agents/skills")
ARCHUNIT = re.compile(r"<artifactId>\s*(taikai|archunit[\w-]*)\s*</artifactId>")
WORKFLOW = ".github/workflows/verify.yml"
HOOKS = (".claude/hooks/guard.sh", ".claude/hooks/verify-on-stop.sh")
LOCK = ".claude/harness.lock"
HARNESS_PLUGINS = re.compile(r"<!-- harness:begin plugins -->.*?<!-- harness:end plugins -->", re.S)
NULLAWAY_OPTION = re.compile(r"-XepOpt:NullAway:(?:AnnotatedPackages=\S+?|OnlyNullMarked=true)(?=\s|<)")
NULL_MARKED = re.compile(r"^\s*@(?:org\.jspecify\.annotations\.)?NullMarked\b", re.M)
# Hooks released before the lock file existed, by SHA-256 of their LF content: safe to replace on a rerun.
RELEASED = {
    ".claude/hooks/guard.sh": {"0eca37c90909f462612b1394097b51ee6fc9d3996b142bebd7e8ef6766f180e3"},
    ".claude/hooks/verify-on-stop.sh": {"88ded00535a3c13dd5e1df5e8545c31fa1989b0c6cc37d21478fa87e96aa9448",
                                        "286d721ca822c4ee6c36e4535d4d0014d248764e8d11f42daa24623920290b4f"},
}


def digest(text: str) -> str:
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def fingerprint(relative: str, text: str) -> str:
    """For a Java file, ignores layout and import order, so running the project's formatter doesn't count as an edit."""
    if not relative.endswith(".java"):
        return digest(text)
    lines = text.replace("\r\n", "\n").split("\n")
    imports = sorted(line.strip() for line in lines if line.strip().startswith("import "))
    body = "".join(line for line in lines if not line.strip().startswith("import "))
    return digest("\n".join(imports) + re.sub(r"\s+", "", body))


def element_spans(pom: str) -> dict[tuple[str, ...], list[tuple[int, int]]]:
    """Map each element path, such as ('project', 'dependencies'), to the (start, end) offsets of its closing tags."""
    stack: list[str] = []
    spans: dict[tuple[str, ...], list[tuple[int, int]]] = {}
    for match in TAG.finditer(pom):
        closing, name, self_closing = match.group(1), match.group(2), match.group(3)
        if name is None or self_closing or name.startswith("?"):
            continue
        if closing:
            if stack and stack[-1] == name:
                spans.setdefault(tuple(stack), []).append((match.start(), match.end()))
                stack.pop()
        else:
            stack.append(name)
    return spans


def insert_before_close(pom: str, path: tuple[str, ...], fragment: str) -> str | None:
    closes = element_spans(pom).get(path)
    if not closes:
        return None
    start = closes[0][0]
    line_start = pom.rfind("\n", 0, start) + 1
    return pom[:line_start] + fragment + pom[line_start:]


def wrap(fragment: str, *tags: str, indent: str) -> str:
    opening = "".join(f"{indent}{'  ' * i}<{tag}>\n" for i, tag in enumerate(tags))
    closing = "".join(f"{indent}{'  ' * i}</{tag}>\n" for i, tag in reversed(list(enumerate(tags))))
    return opening + fragment + closing


def missing_items(fragment: str, pom: str) -> str:
    """Keep only the fragment's properties, dependencies and plugins that the pom doesn't declare yet."""
    kept = []
    for item in ITEM.finditer(fragment):
        block = item.group(0)
        artifact = re.search(r"<artifactId>([^<]+)</artifactId>", block)
        if artifact:
            present = re.search(rf"<artifactId>\s*{re.escape(artifact.group(1))}\s*</artifactId>", pom)
        else:
            present = re.search(rf"<{re.escape(item.group('property'))}>", pom)
        if not present:
            kept.append(block)
    if not kept:
        return ""
    begin, end = fragment.splitlines(keepends=True)[0], fragment.splitlines(keepends=True)[-1]
    return begin + "".join(kept) + end


def nullaway_scope(nullaway: str) -> str:
    """The Error Prone option that says which code NullAway checks. NullAway takes exactly one of the two."""
    return "-XepOpt:NullAway:OnlyNullMarked=true" if nullaway == "marked" \
        else "-XepOpt:NullAway:AnnotatedPackages=${harness.base-package}"


def nullaway_mode(pom: str) -> str:
    """The mode a pom the harness already patched uses; 'all' for a pom without the harness."""
    block = HARNESS_PLUGINS.search(pom)
    option = NULLAWAY_OPTION.search(block.group(0)) if block else None
    return "marked" if option and option.group(0).endswith("OnlyNullMarked=true") else "all"


def nullaway_checked(nullaway: str, base_package: str) -> str:
    """What AGENTS.md says NullAway checks."""
    return ("Code in a `@NullMarked` package (give each new package a `package-info.java` annotated "
            "`@org.jspecify.annotations.NullMarked`)") if nullaway == "marked" else f"Code under `{base_package}`"


def patch_pom(pom: str, base_package: str, modules: bool, nullaway: str = "all") -> str:
    # What the build actually uses: managed versions and inactive profiles add nothing to the classpath.
    declared = re.sub(r"<!--.*?-->|<dependencyManagement>.*?</dependencyManagement>|"
                      r"<pluginManagement>.*?</pluginManagement>|<profiles>.*?</profiles>", "", pom, flags=re.S)
    if MARKER not in pom and re.search(r"<artifactId>\s*maven-compiler-plugin\s*</artifactId>", declared):
        sys.exit(f"ERROR: pom.xml already configures maven-compiler-plugin. Merge its part of "
                 f"{ASSETS / 'pom' / 'plugins.xml'} by hand.")
    # A rerun with another --nullaway switches the scope in place, in the harness's own plugins block only;
    # missing_items would skip the compiler plugin.
    pom = HARNESS_PLUGINS.sub(lambda block: NULLAWAY_OPTION.sub(lambda _: nullaway_scope(nullaway), block.group(0),
                                                                count=1), pom, count=1)

    fragments = {name: (ASSETS / "pom" / f"{name}.xml").read_text(encoding="utf-8")
                 .replace("{{NULLAWAY_SCOPE}}", nullaway_scope(nullaway)).replace("{{BASE_PACKAGE}}", base_package)
                 for name in ("properties", "dependencies", "modules-dependencies", "managed-dependencies", "plugins",
                              "rules-dependencies")}
    if not modules:
        fragments["properties"] = re.sub(r".*spring-modulith\.version.*\n", "", fragments["properties"])
    properties = missing_items(fragments["properties"], pom)
    dependencies = missing_items(fragments["dependencies"], declared)
    if modules:
        dependencies += missing_items(fragments["modules-dependencies"], declared)
    if not ARCHUNIT.search(declared):
        dependencies += fragments["rules-dependencies"]
    managed = missing_items(fragments["managed-dependencies"], pom) if modules else ""
    plugins = missing_items(fragments["plugins"], declared)

    if properties:
        patched = insert_before_close(pom, ("project", "properties"), properties)
        pom = patched or insert_before_close(pom, ("project",), wrap(properties, "properties", indent="  "))
    if dependencies:
        patched = insert_before_close(pom, ("project", "dependencies"), dependencies)
        pom = patched or insert_before_close(pom, ("project",), wrap(dependencies, "dependencies", indent="  "))
    if managed:
        patched = insert_before_close(pom, ("project", "dependencyManagement", "dependencies"), managed)
        if patched is None:
            patched = insert_before_close(pom, ("project",), wrap(managed, "dependencyManagement", "dependencies", indent="  "))
        pom = patched
    if plugins:
        patched = insert_before_close(pom, ("project", "build", "plugins"), plugins)
        if patched is None:
            patched = insert_before_close(pom, ("project", "build"), wrap(plugins, "plugins", indent="    "))
        if patched is None:
            patched = insert_before_close(pom, ("project",), wrap(plugins, "build", "plugins", indent="  "))
        pom = patched
    return pom


def merge_settings(current: dict, wanted: dict) -> dict:
    """Add the harness's permissions, hooks, marketplace and plugin to existing settings, changing nothing else."""
    merged = json.loads(json.dumps(current))
    for kind, rules in wanted.get("permissions", {}).items():
        present = merged.setdefault("permissions", {}).setdefault(kind, [])
        present.extend(rule for rule in rules if rule not in present)
    for event, groups in wanted.get("hooks", {}).items():
        present = merged.setdefault("hooks", {}).setdefault(event, [])
        commands = {hook.get("command") for group in present for hook in group.get("hooks", [])}
        present.extend(group for group in groups
                       if not all(hook["command"] in commands for hook in group["hooks"]))
    for name, entry in wanted.get("extraKnownMarketplaces", {}).items():
        present = merged.setdefault("extraKnownMarketplaces", {}).setdefault(name, {})
        for field, value in entry.items():
            present.setdefault(field, value)
    for name, value in wanted.get("enabledPlugins", {}).items():
        merged.setdefault("enabledPlugins", {}).setdefault(name, value)
    return merged


def repository_root(project: Path) -> Path:
    result = subprocess.run(["git", "-C", str(project), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    root = Path(result.stdout.strip()).resolve() if result.returncode == 0 and result.stdout.strip() else project
    return root if project.is_relative_to(root) else project


def find_application(project: Path) -> tuple[str, str]:
    for source in sorted((project / "src" / "main" / "java").rglob("*.java")):
        text = source.read_text(encoding="utf-8", errors="replace")
        if "@SpringBootApplication" in text:
            package = re.search(r"^\s*package\s+([\w.]+)\s*;", text, re.M)
            if package:
                return package.group(1), source.stem
    sys.exit("ERROR: no @SpringBootApplication class under src/main/java. Pass --base-package and add the "
             "boundary test by hand.")


def pom_value(pom: str, pattern: str, default: str) -> str:
    match = re.search(pattern, pom, re.S)
    return match.group(1).strip() if match else default


class Changes:
    def __init__(self, project: Path, root: Path, dry_run: bool):
        self.project, self.root, self.dry_run, self.lines = project, root, dry_run, []
        lock = root / LOCK
        try:
            self.lock = json.loads(lock.read_text(encoding="utf-8")) if lock.exists() else {}
        except json.JSONDecodeError:
            self.lock = {}
        self.locked = dict(self.lock)

    def own(self, relative: str, text: str, source: Path):
        """Write a file the harness owns: add it, or update it while nobody has edited the copy the harness wrote."""
        target = self.project / relative
        key = Path(os.path.relpath(target, self.root)).as_posix()
        if not target.exists():
            self.write(relative, text, "added")
        else:
            content = target.read_text(encoding="utf-8")
            present, printed = digest(content), fingerprint(relative, content)
            if printed == fingerprint(relative, text):
                self.keep(relative, "up to date")
            elif self.lock.get(key) in (present, printed) or present in RELEASED.get(key, ()):
                self.write(relative, text, "updated")
            elif key in self.lock:
                self.keep(relative, f"edited since the harness wrote it; merge {source} by hand")
                return
            else:
                self.keep(relative, f"not written by this harness; to take {source}, delete it and rerun")
                return
        self.locked[key] = fingerprint(relative, text)

    def disown(self, relative: str, text: str, reason: str):
        """Remove a file the harness wrote and no longer wants, unless someone has edited it."""
        target = self.project / relative
        key = Path(os.path.relpath(target, self.root)).as_posix()
        if target.exists():
            content = target.read_text(encoding="utf-8")
            present, printed = digest(content), fingerprint(relative, content)
            if self.lock.get(key) not in (present, printed) and printed != fingerprint(relative, text):
                self.keep(relative, f"edited since the harness wrote it; {reason}, so delete it by hand")
                return
            if not self.dry_run:
                target.unlink()
                if not any(target.parent.iterdir()):
                    target.parent.rmdir()
            self.lines.append(f"{'removed':8} {relative}")
        self.locked.pop(key, None)

    def save_lock(self):
        if self.locked != self.lock:
            text = json.dumps(dict(sorted(self.locked.items())), indent=2) + "\n"
            self.write(Path(os.path.relpath(self.root / LOCK, self.project)).as_posix(), text,
                       "patched" if self.lock else "added")

    def write(self, relative: str, text: str, note: str):
        target = self.project / relative
        if not self.dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8", newline="\n")
        self.lines.append(f"{note:8} {relative}")

    def keep(self, relative: str, reason: str):
        self.lines.append(f"{'kept':8} {relative} ({reason})")


def null_marked_packages(project: Path, base_package: str) -> tuple[int, int]:
    """(packages with @NullMarked in package-info.java, packages with Java sources) under the base package."""
    base = project / "src" / "main" / "java" / Path(*base_package.split("."))
    packages = {source.parent for source in base.rglob("*.java")} if base.is_dir() else set()
    marked = {package for package in packages if (package / "package-info.java").exists()
              and NULL_MARKED.search((package / "package-info.java").read_text(encoding="utf-8", errors="replace"))}
    return len(marked), len(packages)


def apply(project: Path, base_package: str | None, dry_run: bool, modules: bool = True,
          nullaway: str | None = None) -> list[str]:
    pom_path = project / "pom.xml"
    if not pom_path.exists():
        sys.exit("ERROR: no pom.xml. The harness supports Maven projects only.")
    app_package, app_class = find_application(project)
    base_package = base_package or app_package
    pom = pom_path.read_text(encoding="utf-8")
    nullaway = nullaway or nullaway_mode(pom)
    # CI, Claude Code settings and hooks only work at the repository root, which can be above the Maven project.
    root = repository_root(project)
    changes = Changes(project, root, dry_run)
    folder = project.relative_to(root).as_posix() if root != project else ""

    def at_root(relative: str | Path) -> str:
        return Path(os.path.relpath(root / relative, project)).as_posix()

    patched = patch_pom(pom, base_package, modules, nullaway)
    if patched == pom:
        changes.keep("pom.xml", "harness already present")
    else:
        changes.write("pom.xml", patched, "patched")
    if nullaway == "marked":
        marked, total = null_marked_packages(project, base_package)
        changes.lines.append(f"{'note':8} NullAway checks only @NullMarked packages: {marked} of {total} under "
                             f"{base_package} are marked" + ("; nothing is checked until one is" if not marked else ""))

    existing_boundary_test = next((path for path in (project / "src" / "test").rglob("*.java")
                                   if path.name != "ModuleBoundariesTests.java"
                                   and "ApplicationModules.of(" in path.read_text(encoding="utf-8", errors="replace")),
                                  None)
    values = {
        "{{BOUNDARY_TEST}}": (existing_boundary_test.stem if modules and existing_boundary_test
                              else "ModuleBoundariesTests"),
        "{{PROJECT_NAME}}": pom_value(pom, r"</parent>.*?<artifactId>([^<]+)</artifactId>", project.name),
        "{{BOOT_VERSION}}": pom_value(pom, r"<parent>.*?<version>([^<]+)</version>", "4"),
        "{{JAVA_VERSION}}": pom_value(pom, r"<java.version>([^<]+)</java.version>", "25"),
        "{{BASE_PACKAGE}}": base_package,
        "{{TEST_PACKAGE}}": base_package,
        "{{APP_CLASS}}": f"{app_package}.{app_class}",
        "{{BASE_PATH}}": base_package.replace(".", "/"),
        "{{MAVEN_DIR}}": folder or ".",
        "{{NULLAWAY_CHECKED}}": nullaway_checked(nullaway, base_package),
    }
    other_mode = nullaway_checked("all" if nullaway == "marked" else "marked", base_package)

    def render(text: str, with_modules: bool = modules) -> str:
        text = MODULE_BLOCK.sub(lambda match: match.group(1) if with_modules else "", text)
        for placeholder, value in values.items():
            text = text.replace(placeholder, value)
        return text

    agents_template = render((ASSETS / "project" / "AGENTS.md").read_text(encoding="utf-8"))
    agents = project / "AGENTS.md"
    if not agents.exists():
        changes.write("AGENTS.md", agents_template, "added")
    elif "## Done means verify passes" in (current := agents.read_text(encoding="utf-8")):
        # The NullAway row of a rerun with another --nullaway still names the old scope.
        updated = render(current).replace(f"| NullAway, at compile | {other_mode} ",
                                          f"| NullAway, at compile | {nullaway_checked(nullaway, base_package)} ")
        # A harness from before October 2026 named its own boundary test even when it kept the project's.
        updated = updated.replace("| `ModuleBoundariesTests` |", f"| `{values['{{BOUNDARY_TEST}}']}` |")
        if updated != current:
            changes.write("AGENTS.md", updated, "patched")
        elif not modules and "ModuleBoundariesTests" in current:
            changes.keep("AGENTS.md", "has the harness section; remove its ModuleBoundariesTests row and Modules "
                                      "section by hand")
        else:
            changes.keep("AGENTS.md", "has the harness section")
    else:
        section = agents_template[agents_template.index("## Done means"):agents_template.index("## Team conventions")]
        existing = agents.read_text(encoding="utf-8").rstrip("\n")
        changes.write("AGENTS.md", f"{existing}\n\n<!-- harness:begin -->\n{section.rstrip()}\n<!-- harness:end -->\n",
                      "patched")

    if folder:
        pointer = (f"The rules and build gates for `{folder}/` are in `{folder}/AGENTS.md`. Read it before you change "
                   "anything there.\n")
        root_agents = root / "AGENTS.md"
        present = root_agents.read_text(encoding="utf-8") if root_agents.exists() else ""
        if f"{folder}/AGENTS.md" in present:
            changes.keep(at_root("AGENTS.md"), f"points to {folder}/AGENTS.md")
        else:
            lead = present.rstrip("\n") + "\n\n" if present else ""
            changes.write(at_root("AGENTS.md"), lead + pointer, "patched" if present else "added")

    template = ASSETS / "project" / ".claude" / "settings.json"
    wanted_settings = json.loads(render(template.read_text(encoding="utf-8")))
    if folder:
        for event in ("SessionStart", "Stop"):
            for group in wanted_settings["hooks"][event]:
                for hook in group["hooks"]:
                    hook["command"] += f' "{folder}"'
    settings = at_root(".claude/settings.json")
    if not (project / settings).exists():
        changes.write(settings, json.dumps(wanted_settings, indent=2) + "\n", "added")
    else:
        try:
            current = json.loads((project / settings).read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            current = None
        if not isinstance(current, dict):
            changes.keep(settings, f"not valid JSON; merge {template} by hand")
        else:
            merged = merge_settings(current, wanted_settings)
            if merged == current:
                changes.keep(settings, "has the harness entries")
            else:
                changes.write(settings, json.dumps(merged, indent=2) + "\n", "patched")
    for hook in HOOKS:
        changes.own(at_root(hook), (ASSETS / "project" / hook).read_text(encoding="utf-8"), ASSETS / "project" / hook)

    attributes = root / ".gitattributes"
    present = attributes.read_text(encoding="utf-8") if attributes.exists() else ""
    if re.search(r"^\*\.sh\s.*eol=lf", present, re.M):
        changes.keep(at_root(".gitattributes"), "keeps shell scripts LF")
    else:
        lead = "" if not present or present.endswith("\n") else "\n"
        changes.write(at_root(".gitattributes"), present + lead + "*.sh text eol=lf\n", "patched" if present else "added")

    claude_md = project / "CLAUDE.md"
    if not claude_md.exists():
        changes.write("CLAUDE.md", "@AGENTS.md\n", "added")
    elif "@AGENTS.md" in claude_md.read_text(encoding="utf-8"):
        changes.keep("CLAUDE.md", "already imports AGENTS.md")
    else:
        changes.write("CLAUDE.md", "@AGENTS.md\n\n" + claude_md.read_text(encoding="utf-8"), "patched")

    jvm_config = project / ".mvn" / "jvm.config"
    wanted = (ASSETS / "project" / ".mvn" / "jvm.config").read_text(encoding="utf-8").splitlines()
    present = jvm_config.read_text(encoding="utf-8").splitlines() if jvm_config.exists() else []
    missing = [line for line in wanted if line not in present]
    if missing:
        changes.write(".mvn/jvm.config", "\n".join(present + missing) + "\n", "patched" if present else "added")
    else:
        changes.keep(".mvn/jvm.config", "has the Error Prone flags")

    test_dir = Path("src/test/java", *base_package.split("."))
    tests = ["ConfigurationKeysTests.java", "CodeRulesTests.java", "BuildSetupTests.java"]
    if modules and existing_boundary_test:
        changes.keep(existing_boundary_test.relative_to(project).as_posix(), "already verifies module boundaries")
    elif modules:
        tests.append("ModuleBoundariesTests.java")
    else:
        changes.disown((test_dir / "ModuleBoundariesTests.java").as_posix(),
                       render((ASSETS / "tests" / "ModuleBoundariesTests.java").read_text(encoding="utf-8"), True),
                       "--no-modules doesn't use it")
    for test in tests:
        changes.own((test_dir / test).as_posix(), render((ASSETS / "tests" / test).read_text(encoding="utf-8")),
                    ASSETS / "tests" / test)

    properties = Path("src/test/resources/archunit.properties")
    wanted = (ASSETS / "tests" / "archunit.properties").read_text(encoding="utf-8").splitlines()
    present = (project / properties).read_text(encoding="utf-8").splitlines() if (project / properties).exists() else []
    keys = {line.split("=", 1)[0].strip() for line in present if "=" in line}
    missing = [line for line in wanted if line.split("=", 1)[0] not in keys]
    if missing:
        changes.write(properties.as_posix(), "\n".join(present + missing) + "\n", "patched" if present else "added")
    elif any(line.replace(" ", "") == "freeze.store.default.allowStoreCreation=true" for line in present):
        changes.keep(properties.as_posix(), "allowStoreCreation=true records every new rule's violations as accepted; "
                                            "set it to false and record a baseline with baseline.py")
    else:
        changes.keep(properties.as_posix(), "configures the ArchUnit freeze store")

    workflows = root / ".github" / "workflows"
    ours = next((name for name in (WORKFLOW, ".github/workflows/harness-verify.yml") if name in changes.lock), None)
    runs_maven = next((path for path in sorted(workflows.glob("*.y*ml")) if workflows.is_dir()
                       and re.search(r"\bmvnw?\b", path.read_text(encoding="utf-8", errors="replace"))), None)
    if ours:
        changes.own(at_root(ours), render((ASSETS / "project" / WORKFLOW).read_text(encoding="utf-8")),
                    ASSETS / "project" / WORKFLOW)
    elif runs_maven:
        changes.keep(at_root(runs_maven.relative_to(root)), "already runs Maven in CI")
    else:
        target = WORKFLOW if not (root / WORKFLOW).exists() else ".github/workflows/harness-verify.yml"
        changes.own(at_root(target), render((ASSETS / "project" / WORKFLOW).read_text(encoding="utf-8")),
                    ASSETS / "project" / WORKFLOW)

    if not modules:
        text = render((ASSETS / "project-skills" / "add-module" / "SKILL.md").read_text(encoding="utf-8"), True)
        for skills_dir in SKILL_DIRS:
            changes.disown(f"{skills_dir}/add-module/SKILL.md", text, "--no-modules doesn't use it")
    skills = (["add-module"] if modules else []) + (["db-migration"] if "flyway" in pom.lower() else [])
    for skill in skills:
        text = render((ASSETS / "project-skills" / skill / "SKILL.md").read_text(encoding="utf-8"))
        for skills_dir in SKILL_DIRS:
            changes.own(f"{skills_dir}/{skill}/SKILL.md", text, ASSETS / "project-skills" / skill / "SKILL.md")
    changes.save_lock()
    return changes.lines


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("project")
    parser.add_argument("--base-package", help="Package NullAway checks; defaults to the @SpringBootApplication package")
    parser.add_argument("--dry-run", action="store_true", help="Report what would change without writing")
    parser.add_argument("--no-modules", action="store_true",
                        help="Skip Spring Modulith boundaries, for layered or hexagonal projects whose subpackages are layers")
    parser.add_argument("--nullaway", choices=("all", "marked"),
                        help="'all' (default for a new install) checks every class under the base package; 'marked' "
                             "checks only packages with @NullMarked, so an existing codebase adopts it package by "
                             "package. A rerun without the flag keeps the pom's current mode")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    for line in apply(Path(args.project).resolve(), args.base_package, args.dry_run, not args.no_modules,
                      args.nullaway):
        print(line)
    if not (Path(args.project) / "mvnw").exists():
        print("\nWARNING: no Maven wrapper here, and AGENTS.md, the Stop hook and CI all call ./mvnw. Add it with: "
              "mvn wrapper:wrapper")
    if not args.dry_run:
        print("\nNext: ./mvnw spotless:apply, then ./mvnw verify, and fix what NullAway reports.")


if __name__ == "__main__":
    main()
