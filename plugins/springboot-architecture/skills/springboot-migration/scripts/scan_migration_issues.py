#!/usr/bin/env python3
"""
Spring Boot Migration Scanner

Scans a Spring Boot project for migration issues related to:
- Spring Boot 4.0
- Spring Modulith 2.0
- Testcontainers 2.x

Usage:
    python3 scan_migration_issues.py /path/to/project
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Set
from dataclasses import dataclass, field


@dataclass
class Issue:
    """Represents a migration issue"""
    category: str
    severity: str  # CRITICAL, WARNING, INFO
    file_path: str
    line_number: int
    issue: str
    suggestion: str


@dataclass
class ScanResult:
    """Results from migration scan"""
    spring_boot_version: str = "Unknown"
    spring_modulith_version: str = "Unknown"
    testcontainers_version: str = "Unknown"
    issues: List[Issue] = field(default_factory=list)

    def add_issue(self, category: str, severity: str, file_path: str,
                  line_number: int, issue: str, suggestion: str):
        self.issues.append(Issue(category, severity, file_path, line_number, issue, suggestion))


class MigrationScanner:
    """Scans project for migration issues"""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.result = ScanResult()
        self.modulith_schema_configured = False
        self.modulith_in_use = False
        self.has_restclient_starter = False
        self.has_webclient_starter = False
        self.uses_restclient = False
        self.uses_webclient = False

    def scan(self) -> ScanResult:
        """Run full migration scan"""
        print(f"Scanning project: {self.project_path}")
        print("=" * 80)

        # Scan build files — Maven and/or Gradle. Projects occasionally have both
        # (e.g. mid-migration); scan whichever are present.
        pom_path = self.project_path / "pom.xml"
        gradle_groovy = self.project_path / "build.gradle"
        gradle_kotlin = self.project_path / "build.gradle.kts"

        # Multi-module Maven: the root pom usually only declares <modules> and
        # the actual Spring Boot version sits in submodule poms. Discover and
        # scan every pom.xml in the tree (root first so its outputs print
        # first), skipping `target/` and `.git/` to avoid noise. The first
        # match wins for version detection because `_scan_pom` only assigns
        # when the field is still default.
        if pom_path.exists():
            poms = [pom_path]
            for child in sorted(self.project_path.rglob("pom.xml")):
                if child == pom_path:
                    continue
                parts = set(child.relative_to(self.project_path).parts)
                if parts & {"target", ".git", "node_modules", "build"}:
                    continue
                poms.append(child)
            for pom in poms:
                self._scan_pom(pom)
            # Single summary after walking every pom — first detection wins.
            print(f"   Spring Boot: {self.result.spring_boot_version}")
            print(f"   Spring Modulith: {self.result.spring_modulith_version}")
            print(f"   Testcontainers: {self.result.testcontainers_version}")
        if gradle_groovy.exists():
            self._scan_gradle(gradle_groovy)
        if gradle_kotlin.exists():
            self._scan_gradle(gradle_kotlin)

        if not (pom_path.exists() or gradle_groovy.exists() or gradle_kotlin.exists()):
            print("⚠️  Warning: no pom.xml, build.gradle, or build.gradle.kts found")

        # Scan Java files
        self._scan_java_files()

        # Scan properties files
        self._scan_properties()

        # Scan Flyway migrations
        self._scan_flyway_migrations()

        # Resolve build-file label for post-scan warnings
        if pom_path.exists():
            build_file_ref = "pom.xml"
        elif gradle_groovy.exists():
            build_file_ref = "build.gradle"
        elif gradle_kotlin.exists():
            build_file_ref = "build.gradle.kts"
        else:
            build_file_ref = "build file"

        # Post-scan: check for missing modular HTTP client starters
        if self.uses_restclient and not self.has_restclient_starter:
            self.result.add_issue(
                "Spring Boot 4 - Dependencies",
                "WARNING",
                build_file_ref,
                0,
                "RestClient used but spring-boot-starter-restclient not found",
                "Boot 4 modular starters require spring-boot-starter-restclient for RestClient auto-configuration"
            )
        if self.uses_webclient and not self.has_webclient_starter:
            self.result.add_issue(
                "Spring Boot 4 - Dependencies",
                "WARNING",
                build_file_ref,
                0,
                "WebClient used but spring-boot-starter-webclient not found",
                "Boot 4 modular starters require spring-boot-starter-webclient for WebClient auto-configuration"
            )

        return self.result

    def _scan_pom(self, pom_path: Path):
        """Scan pom.xml for dependency issues"""
        try:
            rel = pom_path.relative_to(self.project_path)
        except ValueError:
            rel = pom_path
        print(f"\n📦 Scanning {rel}...")

        with open(pom_path, 'r') as f:
            content = f.read()

        # Strip <!-- ... --> XML comments before parsing so commented-out
        # dependencies aren't flagged as real issues. Replace each comment with
        # the same number of newlines it spanned, so reported line numbers
        # stay accurate.
        content = re.sub(
            r'<!--.*?-->',
            lambda m: '\n' * m.group(0).count('\n'),
            content,
            flags=re.DOTALL,
        )
        lines = content.split('\n')

        # Version patterns intentionally accept pre-release/snapshot suffixes
        # (e.g. 4.0.0-RC1, 2.0.0-SNAPSHOT, 2.0.0-M3) instead of truncating to
        # the leading digits.
        version_value = r'([\d.]+(?:[-.\w]*)?)'

        # Spring Boot version detection — try three idiomatic styles in order:
        #   (1) <spring-boot.version>X</spring-boot.version> property style
        #   (2) <parent>...<artifactId>spring-boot-starter-parent</artifactId>
        #       <version>X</version></parent>     (Spring Initializr default)
        #   (3) <dependencyManagement> BOM import of spring-boot-dependencies
        spring_boot_match = re.search(r'<spring-boot\.version>' + version_value, content)
        if not spring_boot_match:
            # <parent> style: capture the version that sits inside the same
            # <parent>...</parent> block as spring-boot-starter-parent. Block
            # is non-greedy and anchored on both tags so the regex doesn't
            # roam across unrelated <parent> declarations (e.g. a multi-module
            # build with its own parent above the spring-boot one).
            spring_boot_match = re.search(
                r'<parent>[\s\S]*?<artifactId>\s*spring-boot-starter-parent\s*</artifactId>'
                r'[\s\S]*?<version>\s*' + version_value + r'\s*</version>'
                r'[\s\S]*?</parent>',
                content,
            )
        if not spring_boot_match:
            # <dependencyManagement> BOM-import style.
            spring_boot_match = re.search(
                r'<artifactId>\s*spring-boot-dependencies\s*</artifactId>'
                r'[\s\S]{0,400}?<version>\s*' + version_value + r'\s*</version>',
                content,
            )
        # In multi-module scans the root pom may not declare a version while
        # submodule poms do. First match wins — don't overwrite a value found
        # in an earlier (e.g. root or sibling) pom.
        if spring_boot_match and self.result.spring_boot_version == "Unknown":
            self.result.spring_boot_version = spring_boot_match.group(1)

        spring_modulith_match = re.search(r'<spring-modulith\.version>' + version_value, content)
        if not spring_modulith_match:
            # spring-modulith-bom import style.
            spring_modulith_match = re.search(
                r'<artifactId>\s*spring-modulith-bom\s*</artifactId>'
                r'[\s\S]{0,400}?<version>\s*' + version_value + r'\s*</version>',
                content,
            )
        if spring_modulith_match:
            if self.result.spring_modulith_version == "Unknown":
                self.result.spring_modulith_version = spring_modulith_match.group(1)
            self.modulith_in_use = True

        testcontainers_match = re.search(r'<testcontainers\.version>' + version_value, content)
        if not testcontainers_match:
            # testcontainers-bom import style.
            testcontainers_match = re.search(
                r'<artifactId>\s*testcontainers-bom\s*</artifactId>'
                r'[\s\S]{0,400}?<version>\s*' + version_value + r'\s*</version>',
                content,
            )
        if testcontainers_match and self.result.testcontainers_version == "Unknown":
            self.result.testcontainers_version = testcontainers_match.group(1)

        if re.search(r'<artifactId>spring-modulith', content) or re.search(
            r'<groupId>org\.springframework\.modulith</groupId>', content
        ):
            self.modulith_in_use = True

        # Check for old starters — verify the surrounding <dependency> block
        # carries <groupId>org.springframework.boot</groupId> so a third-party
        # artifact reusing the same name isn't misflagged.
        old_starters = {
            'spring-boot-starter-web': 'spring-boot-starter-webmvc',
            'spring-boot-starter-aop': 'spring-boot-starter-aspectj',
        }

        for i, line in enumerate(lines, 1):
            for old, new in old_starters.items():
                if f'<artifactId>{old}</artifactId>' in line:
                    context = '\n'.join(lines[max(0, i-3):min(len(lines), i+2)])
                    if '<groupId>org.springframework.boot</groupId>' not in context:
                        continue
                    self.result.add_issue(
                        "Spring Boot 4 - Dependencies",
                        "CRITICAL",
                        str(pom_path),
                        i,
                        f"Old starter: {old}",
                        f"Change to: {new} (or use spring-boot-starter-classic for gradual migration)"
                    )

        # Check for spring-security-test
        for i, line in enumerate(lines, 1):
            if '<artifactId>spring-security-test</artifactId>' in line:
                # Check if it's the old spring-security version
                context = '\n'.join(lines[max(0, i-3):min(len(lines), i+2)])
                if '<groupId>org.springframework.security</groupId>' in context:
                    self.result.add_issue(
                        "Spring Boot 4 - Dependencies",
                        "CRITICAL",
                        str(pom_path),
                        i,
                        "Old spring-security-test dependency",
                        "Change to: spring-boot-starter-security-test"
                    )

        # Check for Testcontainers 1.x artifacts
        tc_old_artifacts = ['junit-jupiter', 'postgresql', 'mysql', 'localstack', 'mongodb']
        for i, line in enumerate(lines, 1):
            for artifact in tc_old_artifacts:
                if f'<artifactId>{artifact}</artifactId>' in line:
                    # Check if it's under org.testcontainers
                    context = '\n'.join(lines[max(0, i-3):min(len(lines), i+2)])
                    if '<groupId>org.testcontainers</groupId>' in context:
                        self.result.add_issue(
                            "Testcontainers 2.x - Dependencies",
                            "WARNING",
                            str(pom_path),
                            i,
                            f"Old Testcontainers artifact: {artifact}",
                            f"Change to: testcontainers-{artifact}"
                        )

        # Track modular HTTP client starters
        self.has_restclient_starter = 'spring-boot-starter-restclient' in content
        self.has_webclient_starter = 'spring-boot-starter-webclient' in content

        # Check for legacy spring-retry dependency — require the real coordinate
        # so incidental mentions in <description> / text don't fire.
        for i, line in enumerate(lines, 1):
            if '<artifactId>spring-retry</artifactId>' in line:
                context = '\n'.join(lines[max(0, i-3):min(len(lines), i+2)])
                if '<groupId>org.springframework.retry</groupId>' in context:
                    self.result.add_issue(
                        "Spring Boot 4 - Legacy Spring Retry",
                        "WARNING",
                        str(pom_path),
                        i,
                        "Legacy spring-retry dependency found",
                        "Remove spring-retry dependency — Spring Framework 7 provides native @Retryable via org.springframework.resilience.annotation.*"
                    )
                    break

    def _scan_gradle(self, gradle_path: Path):
        """Scan build.gradle or build.gradle.kts for dependency issues.

        Handles both the Groovy DSL (single quotes, ``id 'foo' version 'x'``)
        and the Kotlin DSL (double quotes, ``id("foo") version "x"``).
        """
        flavor = gradle_path.name
        print(f"\n📦 Scanning {flavor}...")

        try:
            with open(gradle_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"   Error reading {gradle_path}: {e}")
            return

        # Strip /* ... */ block comments before parsing so deps inside disabled
        # blocks don't surface as real issues. Replace each comment with the same
        # number of newlines it spanned, so reported line numbers stay accurate.
        content = re.sub(
            r'/\*.*?\*/',
            lambda m: '\n' * m.group(0).count('\n'),
            content,
            flags=re.DOTALL,
        )
        lines = content.split('\n')

        # Build a code-only view of the content with `//` line comments stripped
        # (same rule the per-line loop uses below: `//` at start-of-line or
        # preceded by whitespace, leaving `://` inside URL string literals
        # alone). Commented portions are blanked rather than removed so line
        # numbers in `lines` still match. All content-level substring/regex
        # checks below run against `code_content` so a commented-out dep like
        #   // implementation("org.springframework.boot:spring-boot-starter-restclient")
        # cannot satisfy a presence flag.
        def _strip_line_comment(line: str) -> str:
            comment_match = re.search(r'(^//|\s//)', line)
            return line[:comment_match.end(0) - 2] if comment_match else line

        code_content = '\n'.join(_strip_line_comment(line) for line in lines)

        # Spring Boot plugin version — works for both DSLs:
        #   id 'org.springframework.boot' version '4.0.0'
        #   id("org.springframework.boot") version "4.0.0"
        sb_plugin = re.search(
            r"""id\s*[\(\s]+\s*['"]org\.springframework\.boot['"]\s*\)?\s*version\s*['"]([\d.]+(?:[-.\w]*)?)['"]""",
            code_content,
        )
        if sb_plugin:
            self.result.spring_boot_version = sb_plugin.group(1)

        # Common property style for Modulith / Testcontainers versions:
        #   ext { set('springModulithVersion', '2.0.0') }   (Groovy)
        #   springModulithVersion = '2.0.0'                  (Groovy ext)
        #   extra["springModulithVersion"] = "2.0.0"         (Kotlin)
        for prop_pattern, target_attr, marks_modulith in [
            (r"""springModulithVersion['"\]]*\s*[=,]\s*['"]([\d.]+(?:[-.\w]*)?)['"]""",
             "spring_modulith_version", True),
            (r"""testcontainersVersion['"\]]*\s*[=,]\s*['"]([\d.]+(?:[-.\w]*)?)['"]""",
             "testcontainers_version", False),
        ]:
            m = re.search(prop_pattern, code_content)
            if m:
                setattr(self.result, target_attr, m.group(1))
                if marks_modulith:
                    self.modulith_in_use = True

        # Spring Modulith presence by groupId/artifactId
        if 'org.springframework.modulith' in code_content or 'spring-modulith' in code_content:
            self.modulith_in_use = True

        print(f"   Spring Boot: {self.result.spring_boot_version}")
        print(f"   Spring Modulith: {self.result.spring_modulith_version}")
        print(f"   Testcontainers: {self.result.testcontainers_version}")

        # Dependency notation: 'group:artifact[:version]' or "group:artifact[:version]"
        # Both DSLs use the same string form for the GAV coordinate.
        dep_re = re.compile(
            r"""['"]([A-Za-z0-9_.\-]+):([A-Za-z0-9_.\-]+)(?::([\w.+\-]+))?['"]"""
        )

        # Map-style notation, same line:
        #   Groovy: implementation group: 'g', name: 'a' [, version: 'v']
        #   Kotlin: implementation(group = "g", name = "a" [, version = "v"])
        # Keys may appear in any order on the line. We only need group + name
        # to identify the artifact; version is ignored. Multi-line map-style
        # is uncommon and intentionally not handled — a separate pass over
        # logical statements would be required.
        map_kv_re = re.compile(
            r"""\b(group|name)\s*[:=]\s*['"]([A-Za-z0-9_.\-]+)['"]"""
        )

        def _gradle_gav_pairs(code_line):
            """Yield (group_id, artifact_id) for every dependency on this line.

            Covers both the string-form GAV coordinate and the map-style
            notation. For map-style, only the first occurrence of each key on
            the line is taken — pairing multiple group/name kv-pairs on the
            same line is ambiguous and not idiomatic Gradle.
            """
            for m in dep_re.finditer(code_line):
                yield m.group(1), m.group(2)
            kv = {}
            for m in map_kv_re.finditer(code_line):
                kv.setdefault(m.group(1), m.group(2))
            if 'group' in kv and 'name' in kv:
                yield kv['group'], kv['name']

        old_starters = {
            'spring-boot-starter-web': 'spring-boot-starter-webmvc',
            'spring-boot-starter-aop': 'spring-boot-starter-aspectj',
        }
        tc_old_artifacts = {'junit-jupiter', 'postgresql', 'mysql', 'localstack', 'mongodb'}

        spring_retry_reported = False
        for i, line in enumerate(lines, 1):
            # Drop trailing line comments so `impl 'group:art' // note` still
            # parses the dep, while fully-commented lines fall through below.
            code = _strip_line_comment(line)
            stripped = code.strip()
            if not stripped or stripped.startswith('#'):
                continue
            for group_id, artifact_id in _gradle_gav_pairs(code):
                if group_id == 'org.springframework.boot' and artifact_id in old_starters:
                    self.result.add_issue(
                        "Spring Boot 4 - Dependencies",
                        "CRITICAL",
                        str(gradle_path),
                        i,
                        f"Old starter: {artifact_id}",
                        f"Change to: {old_starters[artifact_id]} (or use spring-boot-starter-classic for gradual migration)"
                    )

                if group_id == 'org.springframework.security' and artifact_id == 'spring-security-test':
                    self.result.add_issue(
                        "Spring Boot 4 - Dependencies",
                        "CRITICAL",
                        str(gradle_path),
                        i,
                        "Old spring-security-test dependency",
                        "Change to: spring-boot-starter-security-test"
                    )

                if group_id == 'org.testcontainers' and artifact_id in tc_old_artifacts:
                    self.result.add_issue(
                        "Testcontainers 2.x - Dependencies",
                        "WARNING",
                        str(gradle_path),
                        i,
                        f"Old Testcontainers artifact: {artifact_id}",
                        f"Change to: testcontainers-{artifact_id}"
                    )

                # Legacy spring-retry — coordinate-based, not substring, so
                # incidental mentions in strings/comments don't fire.
                if (
                    not spring_retry_reported
                    and group_id == 'org.springframework.retry'
                    and artifact_id == 'spring-retry'
                ):
                    self.result.add_issue(
                        "Spring Boot 4 - Legacy Spring Retry",
                        "WARNING",
                        str(gradle_path),
                        i,
                        "Legacy spring-retry dependency found",
                        "Remove spring-retry dependency — Spring Framework 7 provides native @Retryable via org.springframework.resilience.annotation.*"
                    )
                    spring_retry_reported = True

        # Track modular HTTP client starters (use code_content so a commented
        # `// implementation("...spring-boot-starter-restclient")` cannot flip
        # the presence flag and suppress the missing-starter warning).
        if 'spring-boot-starter-restclient' in code_content:
            self.has_restclient_starter = True
        if 'spring-boot-starter-webclient' in code_content:
            self.has_webclient_starter = True

    def _scan_java_files(self):
        """Scan Java files for code issues"""
        print("\n☕ Scanning Java files...")

        java_files = list(self.project_path.rglob("*.java"))
        print(f"   Found {len(java_files)} Java files")

        for java_file in java_files:
            self._scan_java_file(java_file)

    def _scan_java_file(self, file_path: Path):
        """Scan individual Java file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"   Error reading {file_path}: {e}")
            return

        content = ''.join(lines)
        rel_path = file_path.relative_to(self.project_path)
        imports = [
            line.strip().replace("import ", "").replace(";", "")
            for line in lines
            if line.strip().startswith("import ")
        ]
        if any(i.startswith("org.springframework.modulith") for i in imports):
            self.modulith_in_use = True

        # Track RestClient/WebClient usage for modular starter check
        if 'RestClient' in content and not self.uses_restclient:
            for line in lines:
                stripped = line.strip()
                if ('RestClient' in stripped and not stripped.startswith('//')
                        and 'RestTestClient' not in stripped
                        and 'import' not in stripped.lower()):
                    self.uses_restclient = True
                    break
        if 'WebClient' in content and not self.uses_webclient:
            for line in lines:
                stripped = line.strip()
                if ('WebClient' in stripped and not stripped.startswith('//')
                        and 'import' not in stripped.lower()):
                    self.uses_webclient = True
                    break

        # Check for old test annotations
        test_annotation_patterns = {
            '@MockBean': '@MockitoBean',
            '@SpyBean': '@MockitoSpyBean',
        }

        for i, line in enumerate(lines, 1):
            for old, new in test_annotation_patterns.items():
                if old in line and not line.strip().startswith('//'):
                    self.result.add_issue(
                        "Spring Boot 4 - Test Annotations",
                        "CRITICAL",
                        str(rel_path),
                        i,
                        f"Old test annotation: {old}",
                        f"Change to: {new}"
                    )

        # Check for old imports
        old_imports = {
            'org.springframework.boot.test.mock.mockito.MockBean':
                'org.springframework.test.context.bean.override.mockito.MockitoBean',
            'org.springframework.boot.test.mock.mockito.SpyBean':
                'org.springframework.test.context.bean.override.mockito.MockitoSpyBean',
            'org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest':
                'org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest',
            'org.springframework.boot.autoconfigure.domain.EntityScan':
                'org.springframework.boot.persistence.autoconfigure.EntityScan',
            'org.springframework.boot.BootstrapRegistry':
                'org.springframework.boot.bootstrap.BootstrapRegistry',
            'org.springframework.boot.BootstrapContext':
                'org.springframework.boot.bootstrap.BootstrapContext',
        }

        for i, line in enumerate(lines, 1):
            if line.strip().startswith('//'):
                continue
            for old_import, new_import in old_imports.items():
                if f'import {old_import}' in line:
                    self.result.add_issue(
                        "Spring Boot 4 - Package Relocations",
                        "CRITICAL",
                        str(rel_path),
                        i,
                        f"Old import: {old_import}",
                        f"Change to: {new_import}"
                    )

        # Check for Testcontainers old imports
        tc_old_imports = {
            'org.testcontainers.containers.PostgreSQLContainer':
                'org.testcontainers.postgresql.PostgreSQLContainer',
            'org.testcontainers.containers.MySQLContainer':
                'org.testcontainers.mysql.MySQLContainer',
            'org.testcontainers.containers.MongoDBContainer':
                'org.testcontainers.mongodb.MongoDBContainer',
            'org.testcontainers.containers.localstack.LocalStackContainer':
                'org.testcontainers.localstack.LocalStackContainer',
        }

        for i, line in enumerate(lines, 1):
            if line.strip().startswith('//'):
                continue
            for old_import, new_import in tc_old_imports.items():
                if f'import {old_import}' in line:
                    self.result.add_issue(
                        "Testcontainers 2.x - Package Changes",
                        "CRITICAL",
                        str(rel_path),
                        i,
                        f"Old Testcontainers import: {old_import}",
                        f"Change to: {new_import}"
                    )

        # Check for LocalStack Service enum usage
        if 'LocalStackContainer.Service' in content:
            for i, line in enumerate(lines, 1):
                if 'LocalStackContainer.Service' in line and not line.strip().startswith('//'):
                    self.result.add_issue(
                        "Testcontainers 2.x - API Changes",
                        "CRITICAL",
                        str(rel_path),
                        i,
                        "LocalStackContainer.Service enum removed in Testcontainers 2.x",
                        "Replace enum constants with string service names: .withServices(LocalStackContainer.Service.S3) -> .withServices(\"s3\"). The withServices(String...) method itself still exists."
                    )

        # Note: org.springframework.resilience.* is used in the external sample repo.
        # Keep this as informational instead of treating it as invalid.
        if 'org.springframework.resilience' in content:
            for i, line in enumerate(lines, 1):
                if 'org.springframework.resilience' in line and not line.strip().startswith('//'):
                    self.result.add_issue(
                        "Spring Boot 4 - Retry/Resilience",
                        "INFO",
                        str(rel_path),
                        i,
                        "Using org.springframework.resilience annotations",
                        "Native retry detected; ensure @EnableResilientMethods + spring-boot-starter-aspectj"
                    )

        # Check for @Retryable usage and align suggestion with imports
        if '@Retryable' in content:
            uses_spring_retry = any(i.startswith("org.springframework.retry.annotation") for i in imports)
            uses_resilience = any(i.startswith("org.springframework.resilience.annotation") for i in imports)

            for i, line in enumerate(lines, 1):
                if '@Retryable' in line and not line.strip().startswith('//'):
                    if uses_resilience:
                        suggestion = "Ensure @EnableResilientMethods + spring-boot-starter-aspectj"
                        category = "Spring Boot 4 - Retry/Resilience"
                    elif uses_spring_retry:
                        suggestion = "Migrate to native org.springframework.resilience.annotation.* — Spring Retry is maintenance-only"
                        category = "Spring Boot 4 - Legacy Spring Retry"
                    else:
                        suggestion = "Add imports from org.springframework.resilience.annotation.* + @EnableResilientMethods + aspectj starter"
                        category = "Spring Boot 4 - Retry/Resilience"

                    self.result.add_issue(
                        category,
                        "INFO",
                        str(rel_path),
                        i,
                        "Using @Retryable",
                        suggestion
                    )

        # Check for TestRestTemplate usage
        if 'TestRestTemplate' in content:
            for i, line in enumerate(lines, 1):
                if 'TestRestTemplate' in line and not line.strip().startswith('//'):
                    self.result.add_issue(
                        "Spring Boot 4 - Testing",
                        "WARNING",
                        str(rel_path),
                        i,
                        "TestRestTemplate is no longer auto-provided by @SpringBootTest in Spring Boot 4 (class itself still supported, not deprecated)",
                        "Opt in via @AutoConfigureTestRestTemplate + spring-boot-resttestclient dep, or migrate to RestTestClient (org.springframework.test.web.servlet.client.RestTestClient)"
                    )

        # Check for manual HttpServiceProxyFactory setup
        if 'HttpServiceProxyFactory' in content:
            for i, line in enumerate(lines, 1):
                if 'HttpServiceProxyFactory' in line and not line.strip().startswith('//'):
                    self.result.add_issue(
                        "Spring Boot 4 - HTTP Service Client",
                        "WARNING",
                        str(rel_path),
                        i,
                        "Manual HttpServiceProxyFactory setup is unnecessary in Boot 4",
                        "Replace with @ImportHttpServices auto-configuration (org.springframework.web.service.registry.ImportHttpServices)"
                    )

        # Check for Jackson 2 classes
        jackson2_classes = {
            'Jackson2ObjectMapperBuilderCustomizer': 'JsonMapperBuilderCustomizer',
            '@JsonComponent': '@JacksonComponent',
        }

        for i, line in enumerate(lines, 1):
            for old_class, new_class in jackson2_classes.items():
                if old_class in line and not line.strip().startswith('//'):
                    self.result.add_issue(
                        "Spring Boot 4 - Jackson 3",
                        "CRITICAL",
                        str(rel_path),
                        i,
                        f"Old Jackson 2 class: {old_class}",
                        f"Change to Jackson 3: {new_class}"
                    )

        # Check for generic Testcontainers types
        if 'PostgreSQLContainer<?>' in content or 'MySQLContainer<?>' in content:
            for i, line in enumerate(lines, 1):
                if ('PostgreSQLContainer<?>' in line or 'MySQLContainer<?>' in line) \
                        and not line.strip().startswith('//'):
                    self.result.add_issue(
                        "Testcontainers 2.x - Generic Types",
                        "WARNING",
                        str(rel_path),
                        i,
                        "Generic type in Testcontainers container",
                        "Remove generic type: PostgreSQLContainer<?> → PostgreSQLContainer"
                    )

        # Check for getEndpointOverride with Service parameter
        if 'getEndpointOverride(' in content:
            for i, line in enumerate(lines, 1):
                if 'getEndpointOverride(' in line and 'Service' in line \
                        and not line.strip().startswith('//'):
                    self.result.add_issue(
                        "Testcontainers 2.x - LocalStack API",
                        "CRITICAL",
                        str(rel_path),
                        i,
                        "getEndpointOverride(Service) deprecated",
                        "Change to: getEndpoint()"
                    )

    def _scan_properties(self):
        """Scan application.properties for configuration issues"""
        print("\n⚙️  Scanning application.properties...")

        props_paths = [
            self.project_path / "src/main/resources/application.properties",
            self.project_path / "src/main/resources/application.yml",
        ]

        for props_path in props_paths:
            if props_path.exists():
                has_modulith_schema = self._scan_properties_file(props_path)
                self.modulith_schema_configured = (
                    self.modulith_schema_configured or has_modulith_schema
                )

    def _scan_properties_file(self, file_path: Path) -> bool:
        """Scan properties file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"   Error reading {file_path}: {e}")
            return False

        content = ''.join(lines)

        # Check for Spring Modulith event store config
        has_modulith_jdbc = 'spring.modulith.events.jdbc.schema' in content
        return has_modulith_jdbc

    def _scan_flyway_migrations(self):
        """Scan Flyway migrations for Spring Modulith event schema"""
        print("\n🗄️  Scanning Flyway migrations...")

        migration_dir = self.project_path / "src/main/resources/db/migration"
        if not migration_dir.exists():
            print("   No Flyway migrations found")
            return

        # Check for events schema migration only if configured
        if self.modulith_in_use and self.modulith_schema_configured:
            events_schema_files = list(migration_dir.glob("V*__*events*.sql"))
            root_migrations = migration_dir / "__root"
            if root_migrations.exists():
                events_schema_files += list(root_migrations.glob("V*__*events*.sql"))

            if not events_schema_files:
                self.result.add_issue(
                    "Spring Modulith 2.0 - Database",
                    "CRITICAL",
                    "src/main/resources/db/migration/",
                    0,
                    "Missing events schema migration",
                    "Create: V1__create_events_schema.sql with 'CREATE SCHEMA events;'"
                )

    def print_report(self):
        """Print scan report"""
        print("\n")
        print("=" * 80)
        print("MIGRATION SCAN REPORT")
        print("=" * 80)

        # Group issues by category and severity
        issues_by_category = {}
        for issue in self.result.issues:
            key = f"{issue.category} - {issue.severity}"
            if key not in issues_by_category:
                issues_by_category[key] = []
            issues_by_category[key].append(issue)

        if not self.result.issues:
            print("\n✅ No migration issues found!")
            return

        # Print summary
        critical_count = sum(1 for i in self.result.issues if i.severity == "CRITICAL")
        warning_count = sum(1 for i in self.result.issues if i.severity == "WARNING")
        info_count = sum(1 for i in self.result.issues if i.severity == "INFO")

        print(f"\n📊 Summary:")
        print(f"   🔴 Critical: {critical_count}")
        print(f"   🟡 Warnings: {warning_count}")
        print(f"   ℹ️  Info: {info_count}")
        print(f"   Total: {len(self.result.issues)}")

        # Print detailed issues
        for category_severity in sorted(issues_by_category.keys()):
            issues = issues_by_category[category_severity]
            category, severity = category_severity.rsplit(' - ', 1)

            severity_icon = {
                "CRITICAL": "🔴",
                "WARNING": "🟡",
                "INFO": "ℹ️"
            }[severity]

            print(f"\n{severity_icon} {category} ({len(issues)} issues)")
            print("-" * 80)

            for issue in issues:
                print(f"\n  File: {issue.file_path}:{issue.line_number}")
                print(f"  Issue: {issue.issue}")
                print(f"  Fix: {issue.suggestion}")

        print("\n" + "=" * 80)
        print("\n📚 Next Steps:")
        print("   1. Read the relevant migration guides in references/")
        print("   2. Start with CRITICAL issues first")
        print("   3. Apply fixes in phases: Dependencies → Code → Configuration → Testing")
        print("   4. Test thoroughly after each phase")
        print("\n" + "=" * 80)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scan_migration_issues.py /path/to/project")
        sys.exit(1)

    project_path = sys.argv[1]

    if not os.path.exists(project_path):
        print(f"Error: Path does not exist: {project_path}")
        sys.exit(1)

    scanner = MigrationScanner(project_path)
    result = scanner.scan()
    scanner.print_report()


if __name__ == "__main__":
    main()
