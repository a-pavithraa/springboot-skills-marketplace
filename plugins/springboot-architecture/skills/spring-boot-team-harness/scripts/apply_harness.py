#!/usr/bin/env python3
"""Add the team harness to a Maven or Gradle Spring Boot project: AGENTS.md, Claude Code and Codex hooks, and build gates.

Usage:
    python3 apply_harness.py <project-dir> [--base-package com.example.app] [--nullaway all|marked] [--no-observability]
        [--dry-run]

The pom gets NullAway (JSpecify mode, main code only; every class under the base package, or with --nullaway marked
only @NullMarked packages) through Error Prone, Spotless with palantir-java-format,
Spring Modulith's test starter, and ArchUnit. Four tests are added: ConfigurationKeysTests, CodeRulesTests,
BuildSetupTests and ModuleBoundariesTests. A GitHub Actions workflow that runs ./mvnw verify is added when no
workflow runs mvnw. Claude Code and Codex hooks run the fast gates when a turn ends, and block destructive git
commands, edits to migrations already on main, and edits to the rule tests.
A REVIEW.md template tells reviewers what the code doesn't show; the team fills it in.
Files that already exist are left alone and reported, except CLAUDE.md, which gets an `@AGENTS.md` import as its
first line, and the files the harness owns (hooks, tests, project skills, its workflow): .claude/harness.lock records
what was written, and a rerun updates each one nobody has edited since. Running it twice changes nothing.
It also adds the observability pack: dependencies, safe defaults, a local Grafana stack and dashboards. Telemetry
stays off in deployments until OTLP_EXPORT_ENABLED is set. --no-observability skips it.

On a single-project Gradle build (Groovy or Kotlin DSL), the same gates live in gradle/harness.gradle, which the
harness owns like its tests, and the build file gets one line that applies it. ./gradlew build runs them.
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
PACK_BLOCK = re.compile(r"<!-- (observability|failure-filter):begin -->(\n)?(.*?)<!-- \1:end -->(?(2)\n)", re.S)
BUILD_BLOCK = re.compile(r"<!-- (maven|gradle):begin -->\n(.*?)<!-- \1:end -->\n", re.S)
GRADLE_BLOCK = re.compile(r"^ *// ([\w-]+):begin\n(.*?)^ *// \1:end\n", re.S | re.M)
SKILL_DIRS = (".claude/skills", ".agents/skills")


def declares(artifacts: str) -> re.Pattern:
    """An artifact as a pom's <artifactId>, or in a Gradle coordinate or version catalog entry ("group:artifact")."""
    return re.compile(rf"<artifactId>\s*(?:{artifacts})\s*</artifactId>|[:\"'](?:{artifacts})[:\"']")


ARCHUNIT = declares(r"taikai|archunit[\w-]*")
WORKFLOW = ".github/workflows/verify.yml"
HOOKS = (".claude/hooks/guard.sh", ".claude/hooks/verify-on-stop.sh")
# The CI backstop for the guard hook: it runs for every tool, and its files don't depend on the project.
INTEGRITY = (".github/workflows/harness-integrity.yml", ".github/harness/check-protected.sh")
LOCK = ".claude/harness.lock"
USES_JDBC = declares(r"spring-boot-starter-(?:jdbc|data-jpa|data-jdbc|jooq)")
USES_TOMCAT = declares(r"spring-boot-starter-(?:web|webmvc)")
OTEL_APPENDER = re.compile(r"<appender\b[^>]*OpenTelemetryAppender[^>]*?(?:/>|[^/]>.*?</appender>)", re.S)
OTEL_APPENDER_OPEN = re.compile(r"<appender\b[^>]*>\s*")
OTEL_APPENDER_BODY = re.compile(r"<appender\b[^>]*>(.*)</appender>", re.S)
CONDITIONAL_DEFAULTS = (
    (declares(r"spring-boot-starter-webflux"),
     "  reactor:\n    context-propagation: auto\n"),
    (declares(r"spring-boot-starter-kafka"),
     "  kafka:\n    listener:\n      observation-enabled: true\n    template:\n      observation-enabled: true\n"),
    (declares(r"spring-boot-starter-(?:amqp|rabbitmq)"),
     "  rabbitmq:\n    listener:\n      simple:\n        observation-enabled: true\n"
     "    template:\n      observation-enabled: true\n"),
)
OBSERVABILITY_IMPORT = "application-observability-defaults.yml"
YAML_KEY = re.compile(r"^( *)([\w.-]+):(?:[ \t]+(.*?))?[ \t]*$", re.M)
YAML_IMPORT_SCALAR = re.compile(r"""(?:(?P<quote>["'])(?P<quoted>[^"'\\]*)(?P=quote)|(?P<plain>[^\s"'\[\]{}|>&*!#][^#]*?))"""
                                r"""(?P<comment>[ \t]+#.*)?""")
YAML_IMPORT_LIST = re.compile(r"\[(?P<items>[^\[\]#]*[^\[\]#\s])\s*\](?P<comment>[ \t]+#.*)?")
PROPERTIES_IMPORT = re.compile(r"^(\s*spring\.config\.import\s*[=:][ \t]*)(\S.*)$", re.M)
SAFE_EXPORT_LEVELS = {"INFO", "WARN", "ERROR", "OFF"}
OTEL_THRESHOLD = re.compile(r"<filter\b[^>]*ThresholdFilter[^>]*>.*?<level>\s*(.*?)\s*</level>", re.S)
AUTODETECTION = re.compile(r"^\s*junit\.jupiter\.extensions\.autodetection\.enabled\s*[=:]\s*(\S*)", re.M)
EXPOSED_RISKS = {"*", "env", "configprops", "beans", "heapdump", "threaddump", "logfile", "loggers", "shutdown"}
HARNESS_PLUGINS = re.compile(r"<!-- harness:begin plugins -->.*?<!-- harness:end plugins -->", re.S)
NULLAWAY_OPTION = re.compile(r"-XepOpt:NullAway:(?:AnnotatedPackages=\S+?|OnlyNullMarked=true)(?=\s|<)")
NULL_MARKED = re.compile(r"^\s*@(?:org\.jspecify\.annotations\.)?NullMarked\b", re.M)
# Hooks released before the lock file existed, by SHA-256 of their LF content: safe to replace on a rerun.
RELEASED = {
    ".claude/hooks/guard.sh": {"0eca37c90909f462612b1394097b51ee6fc9d3996b142bebd7e8ef6766f180e3",
                               "f47c311d55ed31b41cf3b3775ab6a6388a885b72a66cff05b3ae2b5cc836f597"},
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


SPRING_JAVAFORMAT = re.compile(r"<artifactId>\s*spring-javaformat-maven-plugin\s*</artifactId>")


def formatter(pom: str) -> tuple[str, str]:
    """The project's formatter and the goal that applies it. A project on Spring Java Format keeps it, since two
    formatters disagree on every file."""
    if SPRING_JAVAFORMAT.search(re.sub(r"<!--.*?-->", "", pom, flags=re.S)):
        return "Spring Java Format", "spring-javaformat:apply"
    return "Spotless", "spotless:apply"


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


GRADLE_BUILD_FILES = ("build.gradle.kts", "build.gradle")
GRADLE_SCRIPT = "gradle/harness.gradle"
GRADLE_INCLUDE = re.compile(r"^\s*include(?:Build)?\b", re.M)
GRADLE_COMMENT = re.compile(r"/\*.*?\*/|(?<![:\"'])//[^\n]*|^\s*#[^\n]*", re.S | re.M)
GRADLE_ERROR_PRONE = re.compile(r"net\.ltgt\.errorprone|gradle-errorprone-plugin")
GRADLE_SPOTLESS = re.compile(r"com\.diffplug\.spotless|spotless-plugin-gradle")


def build_of(project: Path) -> tuple[str, Path]:
    """The project's build tool and build file."""
    pom = project / "pom.xml"
    gradle = next((project / name for name in GRADLE_BUILD_FILES if (project / name).exists()), None)
    if pom.exists() and gradle:
        sys.exit(f"ERROR: both pom.xml and {gradle.name}. Remove the one the team doesn't build with, and rerun.")
    if pom.exists():
        return "maven", pom
    if gradle:
        return "gradle", gradle
    sys.exit("ERROR: no pom.xml, build.gradle or build.gradle.kts. The harness supports Maven and Gradle projects.")


def used_catalog_entries(catalog: str, build: str) -> str:
    """The version catalog's versions, and the libraries and plugins the build refers to (libs.x.y, libs.plugins.x,
    or through libs.bundles.x). An entry the build never refers to isn't on its classpath."""
    sections = dict(re.findall(r"^\s*\[(\w+)\]\s*$(.*?)(?=^\s*\[\w+\]\s*$|\Z)", catalog, re.M | re.S))

    def entries(section: str) -> list[tuple[str, str]]:
        return re.findall(r"^\s*([\w.-]+)\s*=(.*)$", sections.get(section, ""), re.M)

    def referenced(accessor: str) -> bool:
        return bool(re.search(re.escape(accessor) + r"(?![\w-]|\.(?!get\b)\w)", build))

    def accessor(prefix: str, alias: str) -> str:
        return prefix + re.sub(r"[-_.]", ".", alias)

    bundled = {name for alias, members in entries("bundles") if referenced(accessor("libs.bundles.", alias))
               for name in re.findall(r"[\"']([\w.-]+)[\"']", members)}
    used = [line for alias, line in entries("libraries")
            if alias in bundled or referenced(accessor("libs.", alias))]
    used += [line for alias, line in entries("plugins") if referenced(accessor("libs.plugins.", alias))]
    return sections.get("versions", "") + "\n" + "\n".join(used)


def gradle_declared(project: Path, build_file: Path) -> str:
    """The build file without comments, and what it uses from the version catalog: where the dependencies and
    plugins are declared."""
    build = GRADLE_COMMENT.sub("", build_file.read_text(encoding="utf-8"))
    catalog = project / "gradle" / "libs.versions.toml"
    if not catalog.exists():
        return build
    return build + "\n" + used_catalog_entries(GRADLE_COMMENT.sub("", catalog.read_text(encoding="utf-8")), build)


def gradle_formatter(declared: str) -> tuple[str, str]:
    """The project's formatter and the task that applies it."""
    if "io.spring.javaformat" in declared or "spring-javaformat-gradle-plugin" in declared:
        return "Spring Java Format", "format"
    return "Spotless", "spotlessApply"


def gradle_nullaway_mode(script: str) -> str:
    """The mode a harness script already written uses; 'all' for a project without one."""
    return "marked" if '"NullAway:OnlyNullMarked"' in script else "all"


def gradle_script(template: str, base_package: str, modules: bool, nullaway: str, observability: bool,
                  declared: str, build_file: str) -> str:
    # A build with its own Spotless keeps it, as on Maven: loading the plugin twice fails at configuration time.
    spotless = gradle_formatter(declared)[0] == "Spotless"
    own_spotless = bool(GRADLE_SPOTLESS.search(declared))
    wanted = {"spotless": spotless and not own_spotless, "own-spotless": spotless and own_spotless, "modules": modules,
              "archunit": not ARCHUNIT.search(declared), "observability": observability,
              "datasource-observation": observability and bool(USES_JDBC.search(declared))}
    option, value = (("NullAway:OnlyNullMarked", "true") if nullaway == "marked"
                     else ("NullAway:AnnotatedPackages", base_package))
    script = GRADLE_BLOCK.sub(lambda block: block.group(2) if wanted[block.group(1)] else "", template)
    return (script.replace("{{NULLAWAY_OPTION}}", option).replace("{{NULLAWAY_VALUE}}", value)
            .replace("{{BUILD_FILE}}", build_file))


def gradle_apply_line(build_file: Path) -> str:
    return (f'apply(from = "{GRADLE_SCRIPT}")' if build_file.suffix == ".kts" else f'apply from: "{GRADLE_SCRIPT}"')


def check_gradle_build(project: Path, declared: str):
    """Stop on the builds the script can't join: more than one project, or Error Prone already applied."""
    settings = next((project / name for name in ("settings.gradle.kts", "settings.gradle") if (project / name).exists()),
                    None)
    if settings and GRADLE_INCLUDE.search(GRADLE_COMMENT.sub("", settings.read_text(encoding="utf-8"))):
        sys.exit(f"ERROR: {settings.name} includes other projects. The harness supports single-project Gradle builds "
                 "only.")
    if GRADLE_ERROR_PRONE.search(declared):
        sys.exit(f"ERROR: the build already applies Error Prone, which {GRADLE_SCRIPT} brings with NullAway; two "
                 f"copies fail at configuration time. Remove it from the build and rerun, or merge "
                 f"{ASSETS / 'gradle' / 'harness.gradle'} by hand.")


def gradle_value(text: str, patterns: tuple[str, ...], default: str) -> str:
    for pattern in patterns:
        if match := re.search(pattern, text):
            return match.group(1).strip()
    return default


def patch_pom(pom: str, base_package: str, modules: bool, nullaway: str = "all", observability: bool = True) -> str:
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
                              "rules-dependencies", "observability-dependencies")}
    if not modules:
        fragments["properties"] = re.sub(r".*spring-modulith\.version.*\n", "", fragments["properties"])
    if formatter(pom)[0] != "Spotless":
        fragments["plugins"] = re.sub(r" *<plugin>\n *<groupId>com\.diffplug\.spotless</groupId>.*?</plugin>\n", "",
                                      fragments["plugins"], flags=re.S)
        fragments["properties"] = re.sub(r".*(spotless|palantir-java-format)\.version.*\n", "", fragments["properties"])
    dependencies =missing_items(fragments["dependencies"], declared)
    if modules:
        dependencies += missing_items(fragments["modules-dependencies"], declared)
    if observability:
        wanted = fragments["observability-dependencies"]
        if not USES_JDBC.search(declared):
            wanted = re.sub(r" *<dependency>\n *<groupId>net\.ttddyy\.observation.*?</dependency>\n", "", wanted, flags=re.S)
            fragments["properties"] = re.sub(r".*datasource-micrometer\.version.*\n", "", fragments["properties"])
        dependencies += missing_items(wanted, declared)
    else:
        fragments["properties"] = re.sub(r".*(datasource-micrometer|opentelemetry-logback-appender)\.version.*\n", "",
                                         fragments["properties"])
    properties = missing_items(fragments["properties"], pom)
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


VERSIONED = (("properties", re.compile(r"(<(?P<name>[\w.-]+\.version)>)(?P<version>[^<$]+)(</(?P=name)>)")),
             ("rules-dependencies", re.compile(r"(<artifactId>(?P<name>[^<]+)</artifactId>\s*<version>)(?P<version>[^<$]+)"
                                               r"(</version>)")))


def version_key(version: str) -> tuple[int, ...]:
    return tuple(int(number) for number in re.findall(r"\d+", version.split("-")[0]))


def raised_versions(pom: str) -> tuple[str, list[str]]:
    """Raise the versions the harness pinned in its own pom blocks to this release's, and name each one it raised.
    A version the team raised past the harness's is kept."""
    notes = []
    for block, pattern in VERSIONED:
        shipped = {match["name"]: match["version"]
                   for match in pattern.finditer((ASSETS / "pom" / f"{block}.xml").read_text(encoding="utf-8"))}

        def raise_one(match: re.Match) -> str:
            wanted = shipped.get(match["name"])
            if not wanted or not version_key(match["version"]) or version_key(match["version"]) >= version_key(wanted):
                return match.group(0)
            notes.append(f"{match['name']} {match['version']} -> {wanted}")
            return match.group(1) + wanted + match.group(4)

        pom = re.sub(rf"<!-- harness:begin {block} -->.*?<!-- harness:end {block} -->",
                     lambda found: pattern.sub(raise_one, found.group(0)), pom, flags=re.S)
    return pom, notes


def owned_hook(hook: dict) -> bool:
    return ".claude/hooks/" in str(hook.get("command", ""))


def merge_settings(current: dict, wanted: dict) -> dict:
    """Add the harness's permissions, marketplace and plugin to existing settings, and replace its hooks (the ones that
    run a script under .claude/hooks/) with the template's, in place. The team's own entries stay as they are."""
    merged = json.loads(json.dumps(current))
    for kind, rules in wanted.get("permissions", {}).items():
        present = merged.setdefault("permissions", {}).setdefault(kind, [])
        present.extend(rule for rule in rules if rule not in present)
    hooks = merged.setdefault("hooks", {})
    for event in list(hooks) + [event for event in wanted.get("hooks", {}) if event not in hooks]:
        groups = hooks.get(event, [])
        first_owned = next((i for i, group in enumerate(groups)
                            if any(owned_hook(hook) for hook in group.get("hooks", []))), len(groups))
        kept = []
        for group in groups:
            own = [hook for hook in group.get("hooks", []) if not owned_hook(hook)]
            if len(own) == len(group.get("hooks", [])):
                kept.append(group)
            elif own:
                kept.append({**group, "hooks": own})
        # Every group before the first harness one is the team's and kept whole, so the harness's go back there.
        kept[first_owned:first_owned] = wanted.get("hooks", {}).get(event, [])
        if kept:
            hooks[event] = kept
        else:
            hooks.pop(event, None)
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


# Error Prone needs JDK 21.0.8 or later, whatever release the sources target.
BUILD_JDK = 25


def build_jdk(release: str) -> str:
    """The JDK CI builds on: the source release, raised to one Error Prone runs on."""
    return release if release.isdigit() and int(release) > BUILD_JDK else str(BUILD_JDK)


def old_jdks(workflow: str) -> list[str]:
    """The Java versions below 21 that a workflow sets up, from java-version or a java matrix."""
    values = re.findall(r"^\s*(?:java-version|java)\s*:\s*(.+)$", workflow, re.M)
    majors = re.findall(r"(?<![\d.])(\d+)(?:\.\d+)*", re.sub(r"\$\{\{.*?\}\}", "", " ".join(values)))
    return sorted({major for major in majors if int(major) < 21}, key=int)


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


def upgraded_otel_appender(text: str, shipped: str) -> str | None:
    """Add what a project's OTEL appender lacks: the INFO cap, without which DEBUG lines are exported, and key-values."""
    found = OTEL_APPENDER.search(text)
    if not found or "ThresholdFilter" in found[0]:
        return None
    settings = OTEL_APPENDER_BODY.search(OTEL_APPENDER.search(shipped)[0])[1]
    if found[0].endswith("/>"):
        block = found[0][:-2].rstrip() + ">" + settings + "    </appender>"
    else:
        block = OTEL_APPENDER_OPEN.sub(lambda opening: opening[0].rstrip() + settings.rstrip(), found[0], count=1)
        if "captureKeyValuePairAttributes" in found[0]:
            block = block.replace("        <captureKeyValuePairAttributes>true</captureKeyValuePairAttributes>\n", "", 1)
    return text[:found.start()] + block + text[found.end():]


def otel_cap_note(text: str) -> str:
    """What the export cap of an appender that needs no patch is; upgraded_otel_appender leaves such a file alone."""
    threshold = OTEL_THRESHOLD.search(found[0]) if (found := OTEL_APPENDER.search(text)) else None
    if threshold and threshold[1].upper() in SAFE_EXPORT_LEVELS:
        return f"the OTEL appender already stops at {threshold[1].upper()}"
    level = threshold[1] if threshold else "not readable here"
    return f"the OTEL appender's ThresholdFilter level is {level}: set it to INFO by hand, or DEBUG lines can be exported"


def line_added(text: str, line: str) -> str:
    return text + ("" if not text or text.endswith("\n") else "\n") + line + "\n"


def main_config(project: Path) -> Path | None:
    resources = project / "src" / "main" / "resources"
    return next((path for path in (resources / name for name in
                                   ("application.properties", "application.yml", "application.yaml")) if path.exists()),
                None)


def yaml_import_values(text: str) -> list[re.Match]:
    """The value of every spring.config.import key, in nested or dotted form; a multi-document file can hold several."""
    path: list[tuple[int, str]] = []
    values = []
    for line in YAML_KEY.finditer(text):
        indent = len(line[1])
        while path and path[-1][0] >= indent:
            path.pop()
        path.append((indent, line[2]))
        if ".".join(key for _, key in path) == "spring.config.import":
            values.append(line)
    return values


def joined_yaml_import(text: str, value: re.Match, location: str) -> str | None:
    """Add the location inside the YAML form the import uses, or None for a form this can't edit safely."""
    scalar = YAML_IMPORT_SCALAR.fullmatch(value[3] or "")
    items = YAML_IMPORT_LIST.fullmatch(value[3] or "")
    if scalar and scalar["quote"]:
        edited = f"{scalar['quote']}{scalar['quoted']},{location}{scalar['quote']}{scalar['comment'] or ''}"
    elif scalar:
        edited = f"{scalar['plain']},{location}{scalar['comment'] or ''}"
    elif items:
        edited = f"[{items['items']}, {location}]{items['comment'] or ''}"
    else:
        return None
    return text[:value.start(3)] + edited + text[value.end(3):]


def import_observability_defaults(text: str, yaml: bool) -> str | None:
    """Add the import to the main config, joining any import already there, or None when it needs merging by hand."""
    location = f"optional:classpath:{OBSERVABILITY_IMPORT}"
    if not yaml:
        if "spring.config.import[" in text:
            return None
        found = PROPERTIES_IMPORT.findall(text)
        if len(found) > 1 or (found and found[0][1].endswith("\\")):
            return None
        if found:
            return PROPERTIES_IMPORT.sub(lambda match: f"{match[1]}{match[2]},{location}", text, count=1)
        return f"spring.config.import={location}\n" + text
    values = yaml_import_values(text)
    if len(values) > 1:
        return None
    if values:
        return joined_yaml_import(text, values[0], location)
    if re.search(r"^  config:", text, re.M):
        return None
    line = f"  config:\n    import: {location}\n"
    spring = re.search(r"^spring:.*\n?", text, re.M)
    if not spring:
        return f"spring:\n{line}\n" + text
    # The new lines use two spaces, so a block indented any other way, or with a comment on its key, needs a person.
    if not re.match(r"spring:\n {2}\S", text[spring.start():]):
        return None
    return text[:spring.end()] + line + text[spring.end():]


def narrowed_exposure(text: str) -> str:
    """Generators often expose env and friends on the public port; keep only what is safe there."""
    if "management.server.port" in text:
        return text
    def narrow(match: re.Match) -> str:
        kept = [item for item in re.split(r"\s*,\s*", match.group(2).strip()) if item not in EXPOSED_RISKS]
        return match.group(1) + (",".join(kept) or "health")
    return re.sub(r"(management\.endpoints\.web\.exposure\.include\s*[=:]\s*)(.+)", narrow, text)


def apply_observability(project: Path, changes: "Changes", render, pom: str):
    source = ASSETS / "observability"
    for relative, asset in (("src/main/resources/application-observability-defaults.yml",
                             "application-observability-defaults.yml"),
                            ("src/main/resources/application-observability.yml", "application-observability.yml"),
                            ("compose.observability.yml", "compose.observability.yml"),
                            ("observability/grafana-provider.yaml", "grafana-provider.yaml"),
                            ("observability/check_dashboards.py", "check_dashboards.py"),
                            ("observability/check_request.py", "check_request.py"),
                            ("observability/dashboards/service-health.json", "dashboards/service-health.json"),
                            ("observability/dashboards/jvm-resources.json", "dashboards/jvm-resources.json"),
                            ("docs/observability.md", "observability.md")):
        text = render((source / asset).read_text(encoding="utf-8"))
        if asset == "application-observability-defaults.yml" and not USES_TOMCAT.search(pom):
            text = re.sub(r"^server:\n(?:  .*\n)+\n", "", text, flags=re.M)
        if asset == "application-observability-defaults.yml":
            extras = "".join(keys for starter, keys in CONDITIONAL_DEFAULTS if starter.search(pom))
            text = text.replace("spring:\n  task:", f"spring:\n{extras}  task:")
        changes.own(relative, text, source / asset)

    appender = Path("src/main/java", *render("{{BASE_PACKAGE}}").split("."), "InstallOpenTelemetryAppender.java")
    existing = next((path for path in (project / "src" / "main").rglob("InstallOpenTelemetryAppender.java")), None)
    if existing and existing != project / appender:
        changes.keep(existing.relative_to(project).as_posix(), "already installs the log appender; it needs "
                     "@Lazy(false), or spring.main.lazy-initialization stops logs reaching OTLP")
    else:
        changes.own(appender.as_posix(), render((source / "InstallOpenTelemetryAppender.java").read_text(encoding="utf-8")),
                    source / "InstallOpenTelemetryAppender.java")
    if USES_TOMCAT.search(pom):
        changes.own(appender.with_name("HandledFailureFilter.java").as_posix(),
                    render((source / "HandledFailureFilter.java").read_text(encoding="utf-8")),
                    source / "HandledFailureFilter.java")
    check = Path("src/test/java", *render("{{BASE_PACKAGE}}").split("."), "LogLeakCheck.java")
    changes.own(check.as_posix(), render((source / "LogLeakCheck.java").read_text(encoding="utf-8")),
                source / "LogLeakCheck.java")
    extension = "src/test/resources/META-INF/services/org.junit.jupiter.api.extension.Extension"
    registered = (project / extension).read_text(encoding="utf-8") if (project / extension).exists() else ""
    leak_check = render("{{BASE_PACKAGE}}.LogLeakCheck")
    if leak_check not in (line.strip() for line in registered.splitlines()):
        changes.write(extension, line_added(registered, leak_check), "patched" if registered else "added")
    junit = project / "src" / "test" / "resources" / "junit-platform.properties"
    current = junit.read_text(encoding="utf-8") if junit.exists() else ""
    autodetection = AUTODETECTION.search(current)
    if not autodetection:
        changes.write("src/test/resources/junit-platform.properties",
                      line_added(current, "junit.jupiter.extensions.autodetection.enabled=true"), "added")
    elif autodetection[1].lower() != "true":
        changes.keep("src/test/resources/junit-platform.properties",
                     "extension autodetection is off, so LogLeakCheck doesn't run; set it to true")
    logback = project / "src" / "main" / "resources" / "logback-spring.xml"
    if logback.exists():
        text = logback.read_text(encoding="utf-8")
        upgraded = upgraded_otel_appender(text, (source / "logback-spring.xml").read_text(encoding="utf-8"))
        if "OpenTelemetryAppender" not in text:
            changes.keep("src/main/resources/logback-spring.xml",
                         f"add the OTEL appender from {source / 'logback-spring.xml'}")
        elif upgraded is None:
            changes.keep("src/main/resources/logback-spring.xml", otel_cap_note(text))
        else:
            changes.write("src/main/resources/logback-spring.xml", upgraded, "patched")
    else:
        changes.write("src/main/resources/logback-spring.xml", (source / "logback-spring.xml").read_text(encoding="utf-8"),
                      "added")

    config = main_config(project)
    if config is None:
        changes.write("src/main/resources/application.properties",
                      import_observability_defaults("", False) + f"spring.application.name={project.name}\n", "added")
        return
    relative = config.relative_to(project).as_posix()
    text = config.read_text(encoding="utf-8")
    if not re.search(r"spring\.application\.name|^\s+application:\s*\n\s+name:", text, re.M):
        changes.lines.append(f"{'note':8} {relative} has no spring.application.name, which names the service on every "
                             "dashboard; add it")
    updated = text if OBSERVABILITY_IMPORT in text else import_observability_defaults(text, config.suffix != ".properties")
    if updated is None:
        changes.keep(relative, f"add optional:classpath:{OBSERVABILITY_IMPORT} to spring.config.import by hand")
        updated = text
    updated = narrowed_exposure(updated)
    if updated != text:
        changes.write(relative, updated, "patched")
    else:
        changes.keep(relative, "imports the observability defaults")
    if re.search(r"grafana/otel-lgtm", (project / "compose.yml").read_text(encoding="utf-8")
                 if (project / "compose.yml").exists() else ""):
        changes.lines.append(f"{'note':8} compose.yml already runs otel-lgtm, on the ports compose.observability.yml uses; "
                             "remove that service")


def null_marked_packages(project: Path, base_package: str) -> tuple[int, int]:
    """(packages with @NullMarked in package-info.java, packages with Java sources) under the base package."""
    base = project / "src" / "main" / "java" / Path(*base_package.split("."))
    packages = {source.parent for source in base.rglob("*.java")} if base.is_dir() else set()
    marked = {package for package in packages if (package / "package-info.java").exists()
              and NULL_MARKED.search((package / "package-info.java").read_text(encoding="utf-8", errors="replace"))}
    return len(marked), len(packages)


def apply(project: Path, base_package: str | None, dry_run: bool, modules: bool = True,
          nullaway: str | None = None, observability: bool = True) -> list[str]:
    tool, build_file = build_of(project)
    gradle = tool == "gradle"
    app_package, app_class = find_application(project)
    base_package = base_package or app_package
    pom = "" if gradle else build_file.read_text(encoding="utf-8")
    declared = gradle_declared(project, build_file) if gradle else pom
    script_path = project / GRADLE_SCRIPT
    # A rerun with --no-observability leaves an installed pack in place, so its dependencies and docs stay.
    has_pack = observability or (project / "docs" / "observability.md").exists()
    if gradle:
        check_gradle_build(project, declared)
        nullaway = nullaway or gradle_nullaway_mode(script_path.read_text(encoding="utf-8")
                                                    if script_path.exists() else "")
    else:
        nullaway = nullaway or nullaway_mode(pom)
    # CI, Claude Code settings and hooks only work at the repository root, which can be above the build's folder.
    root = repository_root(project)
    changes = Changes(project, root, dry_run)
    folder = project.relative_to(root).as_posix() if root != project else ""

    def at_root(relative: str | Path) -> str:
        return Path(os.path.relpath(root / relative, project)).as_posix()

    if gradle:
        template = ASSETS / "gradle" / "harness.gradle"
        changes.own(GRADLE_SCRIPT, gradle_script(template.read_text(encoding="utf-8"), base_package, modules, nullaway,
                                                 has_pack, declared, build_file.name), template)
        build_text = build_file.read_text(encoding="utf-8")
        if GRADLE_SCRIPT in GRADLE_COMMENT.sub("", build_text):
            changes.keep(build_file.name, f"applies {GRADLE_SCRIPT}")
        else:
            changes.write(build_file.name, line_added(build_text, "\n" + gradle_apply_line(build_file)), "patched")
        format_name, format_apply = gradle_formatter(declared)
    else:
        patched, raised = raised_versions(patch_pom(pom, base_package, modules, nullaway, observability))
        if patched == pom:
            changes.keep("pom.xml", "harness already present")
        else:
            changes.write("pom.xml", patched, "patched")
        if raised:
            changes.lines.append(f"{'note':8} raised {', '.join(raised)}; run ./mvnw verify, since a newer checker "
                                 "can find new errors")
        format_name, format_apply = formatter(patched)
    if nullaway == "marked":
        marked, total = null_marked_packages(project, base_package)
        changes.lines.append(f"{'note':8} NullAway checks only @NullMarked packages: {marked} of {total} under "
                             f"{base_package} are marked" + ("; nothing is checked until one is" if not marked else ""))

    existing_boundary_test = next((path for path in (project / "src" / "test").rglob("*.java")
                                   if path.name != "ModuleBoundariesTests.java"
                                   and "ApplicationModules.of(" in path.read_text(encoding="utf-8", errors="replace")),
                                  None)
    if gradle:
        settings = "\n".join((project / name).read_text(encoding="utf-8")
                             for name in ("settings.gradle.kts", "settings.gradle") if (project / name).exists())
        project_name = gradle_value(settings, (r"rootProject\.name\s*=\s*[\"']([^\"']+)",), project.name)
        boot_version = gradle_value(declared, (r"org\.springframework\.boot[\"')]*\s+version\s*\(?\s*[\"']([^\"']+)",
                                               r"^\s*spring-?boot\s*=\s*\"([^\"]+)\""), "4")
        java_version = gradle_value(declared, (r"JavaLanguageVersion\.of\(\s*(\d+)\s*\)",
                                               r"sourceCompatibility\s*=\s*(?:JavaVersion\.VERSION_)?[\"']?(\d+)"), "25")
    else:
        project_name = pom_value(pom, r"</parent>.*?<artifactId>([^<]+)</artifactId>", project.name)
        boot_version = pom_value(pom, r"<parent>.*?<version>([^<]+)</version>", "4")
        java_version = pom_value(pom, r"<java.version>([^<]+)</java.version>", "25")
    values = {
        "{{BOUNDARY_TEST}}": (existing_boundary_test.stem if modules and existing_boundary_test
                              else "ModuleBoundariesTests"),
        "{{PROJECT_NAME}}": project_name,
        "{{BOOT_VERSION}}": boot_version,
        "{{JAVA_VERSION}}": java_version,
        "{{BUILD_JDK}}": build_jdk(java_version),
        "{{BASE_PACKAGE}}": base_package,
        "{{TEST_PACKAGE}}": base_package,
        "{{APP_CLASS}}": f"{app_package}.{app_class}",
        "{{BASE_PATH}}": base_package.replace(".", "/"),
        "{{PROJECT_DIR}}": folder or ".",
        "{{NULLAWAY_CHECKED}}": nullaway_checked(nullaway, base_package),
        "{{FORMATTER}}": format_name,
        "{{FORMAT_APPLY}}": format_apply,
        "{{BUILD_TOOL}}": tool,
        "{{BUILD_FILE}}": build_file.name,
        "{{WRAPPER}}": "./gradlew" if gradle else "./mvnw",
        "{{WRAPPER_WINDOWS}}": "./gradlew.bat" if gradle else "./mvnw.cmd",
        "{{VERIFY}}": "./gradlew build" if gradle else "./mvnw verify",
        "{{VERIFY_WINDOWS}}": "gradlew.bat build" if gradle else "mvnw.cmd verify",
        "{{CI_VERIFY}}": "./gradlew build" if gradle else "./mvnw -B verify",
        "{{RUN_WITH_PROFILE}}": ("./gradlew bootRun --args='--spring.profiles.active=observability'" if gradle
                                 else "./mvnw spring-boot:run -Dspring-boot.run.profiles=observability"),
    }
    other_mode = nullaway_checked("all" if nullaway == "marked" else "marked", base_package)
    installed = {"observability": has_pack, "failure-filter": bool(has_pack and USES_TOMCAT.search(declared))}

    def render(text: str, with_modules: bool = modules) -> str:
        text = MODULE_BLOCK.sub(lambda match: match.group(1) if with_modules else "", text)
        text = PACK_BLOCK.sub(lambda match: match.group(3) if installed[match.group(1)] else "", text)
        text = BUILD_BLOCK.sub(lambda match: match.group(2) if match.group(1) == tool else "", text)
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
        if has_pack and "docs/observability.md" not in current:
            changes.lines.append(f"{'note':8} AGENTS.md doesn't mention the observability pack; add its lines "
                                 "from the template by hand")
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

    # Claude Code's settings and Codex's hooks file register the same two scripts, merged into what the team has.
    for template in (ASSETS / "project" / ".claude" / "settings.json", ASSETS / "project" / ".codex" / "hooks.json"):
        wanted_settings = json.loads(render(template.read_text(encoding="utf-8")))
        if folder:
            for event in ("SessionStart", "Stop"):
                for group in wanted_settings["hooks"][event]:
                    for hook in group["hooks"]:
                        hook["command"] += f' "{folder}"'
        settings = at_root(template.relative_to(ASSETS / "project"))
        if not (project / settings).exists():
            changes.write(settings, json.dumps(wanted_settings, indent=2) + "\n", "added")
            continue
        try:
            current = json.loads((project / settings).read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            current = None
        if not isinstance(current, dict):
            changes.keep(settings, f"not valid JSON; merge {template} by hand")
            continue
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

    if (root / "REVIEW.md").exists():
        changes.keep(at_root("REVIEW.md"), "the team's review guide")
    else:
        changes.write(at_root("REVIEW.md"), render((ASSETS / "project" / "REVIEW.md").read_text(encoding="utf-8")), "added")

    claude_md = project / "CLAUDE.md"
    if not claude_md.exists():
        changes.write("CLAUDE.md", "@AGENTS.md\n", "added")
    elif "@AGENTS.md" in claude_md.read_text(encoding="utf-8"):
        changes.keep("CLAUDE.md", "already imports AGENTS.md")
    else:
        changes.write("CLAUDE.md", "@AGENTS.md\n\n" + claude_md.read_text(encoding="utf-8"), "patched")

    # Gradle's Error Prone plugin forks the compiler with these flags itself.
    if not gradle:
        jvm_config = project / ".mvn" / "jvm.config"
        wanted = (ASSETS / "project" / ".mvn" / "jvm.config").read_text(encoding="utf-8").splitlines()
        present = jvm_config.read_text(encoding="utf-8").splitlines() if jvm_config.exists() else []
        missing = [line for line in wanted if line not in present]
        if missing:
            changes.write(".mvn/jvm.config", "\n".join(present + missing) + "\n", "patched" if present else "added")
        else:
            changes.keep(".mvn/jvm.config", "has the Error Prone flags")

    test_dir = Path("src/test/java", *base_package.split("."))
    tests = ["ConfigurationKeysTests.java", "CodeRulesTests.java", "BuildSetupTests.java", "UnusedCodeTests.java"]
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
    runs_build = next((path for path in sorted(workflows.glob("*.y*ml")) if workflows.is_dir()
                       and re.search(r"\bgradlew?\b" if gradle else r"\bmvnw?\b",
                                     path.read_text(encoding="utf-8", errors="replace"))), None)
    for integrity in INTEGRITY:
        changes.own(at_root(integrity), (ASSETS / "project" / integrity).read_text(encoding="utf-8"),
                    ASSETS / "project" / integrity)
    if ours:
        changes.own(at_root(ours), render((ASSETS / "project" / WORKFLOW).read_text(encoding="utf-8")),
                    ASSETS / "project" / WORKFLOW)
    elif runs_build:
        old = old_jdks(runs_build.read_text(encoding="utf-8", errors="replace"))
        changes.keep(at_root(runs_build.relative_to(root)), f"already runs {tool.capitalize()} in CI" + (
            f", but on JDK {', '.join(old)}; Error Prone needs 21.0.8 or later, so set java-version to {BUILD_JDK}"
            if old else ""))
    else:
        target = WORKFLOW if not (root / WORKFLOW).exists() else ".github/workflows/harness-verify.yml"
        changes.own(at_root(target), render((ASSETS / "project" / WORKFLOW).read_text(encoding="utf-8")),
                    ASSETS / "project" / WORKFLOW)

    if not modules:
        text = render((ASSETS / "project-skills" / "add-module" / "SKILL.md").read_text(encoding="utf-8"), True)
        for skills_dir in SKILL_DIRS:
            changes.disown(f"{skills_dir}/add-module/SKILL.md", text, "--no-modules doesn't use it")
    skills = ((["add-module"] if modules else []) + ["move-code"]
              + (["db-migration"] if "flyway" in declared.lower() else []))
    for skill in skills:
        text = render((ASSETS / "project-skills" / skill / "SKILL.md").read_text(encoding="utf-8"))
        for skills_dir in SKILL_DIRS:
            changes.own(f"{skills_dir}/{skill}/SKILL.md", text, ASSETS / "project-skills" / skill / "SKILL.md")
    if observability:
        apply_observability(project, changes, render, declared)
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
    parser.add_argument("--no-observability", action="store_true",
                        help="Skip the observability pack. A rerun with this flag leaves an installed pack in place")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    for line in apply(Path(args.project).resolve(), args.base_package, args.dry_run, not args.no_modules,
                      args.nullaway, not args.no_observability):
        print(line)
    project = Path(args.project).resolve()
    tool, build_file = build_of(project)
    if tool == "gradle":
        wrapper, verify, add_wrapper = "./gradlew", "./gradlew build", "gradle wrapper"
        goal = gradle_formatter(gradle_declared(project, build_file))[1]
    else:
        wrapper, verify, add_wrapper = "./mvnw", "./mvnw verify", "mvn wrapper:wrapper"
        goal = formatter(build_file.read_text(encoding="utf-8"))[1]
    if not (project / wrapper[2:]).exists():
        print(f"\nWARNING: no {tool.capitalize()} wrapper here, and AGENTS.md, the Stop hook and CI all call {wrapper}. "
              f"Add it with: {add_wrapper}")
    if not args.dry_run:
        print(f"\nNext: {wrapper} {goal}, then {verify}, and fix what NullAway reports.")


if __name__ == "__main__":
    main()
