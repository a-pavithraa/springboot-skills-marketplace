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

    def scan(self) -> ScanResult:
        """Run full migration scan"""
        print(f"Scanning project: {self.project_path}")
        print("=" * 80)

        # Scan pom.xml for versions and dependencies
        pom_path = self.project_path / "pom.xml"
        if pom_path.exists():
            self._scan_pom(pom_path)
        else:
            print("⚠️  Warning: pom.xml not found (Maven project expected)")

        # Scan Java files
        self._scan_java_files()

        # Scan properties files
        self._scan_properties()

        # Scan Flyway migrations
        self._scan_flyway_migrations()

        return self.result

    def _scan_pom(self, pom_path: Path):
        """Scan pom.xml for dependency issues"""
        print("\n📦 Scanning pom.xml...")

        with open(pom_path, 'r') as f:
            content = f.read()
            lines = content.split('\n')

        # Extract versions
        spring_boot_match = re.search(r'<spring-boot\.version>([\d.]+)', content)
        if spring_boot_match:
            self.result.spring_boot_version = spring_boot_match.group(1)

        spring_modulith_match = re.search(r'<spring-modulith\.version>([\d.]+)', content)
        if spring_modulith_match:
            self.result.spring_modulith_version = spring_modulith_match.group(1)

        testcontainers_match = re.search(r'<testcontainers\.version>([\d.]+)', content)
        if testcontainers_match:
            self.result.testcontainers_version = testcontainers_match.group(1)

        print(f"   Spring Boot: {self.result.spring_boot_version}")
        print(f"   Spring Modulith: {self.result.spring_modulith_version}")
        print(f"   Testcontainers: {self.result.testcontainers_version}")

        # Check for old starters
        old_starters = {
            'spring-boot-starter-web': 'spring-boot-starter-webmvc',
            'spring-boot-starter-aop': 'spring-boot-starter-aspectj',
        }

        for i, line in enumerate(lines, 1):
            for old, new in old_starters.items():
                if f'<artifactId>{old}</artifactId>' in line:
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

        # Check for missing Spring Retry dependency (if using @Retryable)
        has_retry = 'spring-retry' in content
        if not has_retry:
            # We'll check Java files for @Retryable usage
            pass

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
                'org.springframework.boot.test.mock.mockito.MockitoBean',
            'org.springframework.boot.test.mock.mockito.SpyBean':
                'org.springframework.boot.test.mock.mockito.MockitoSpyBean',
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
                if 'LocalStackContainer.Service' in line:
                    self.result.add_issue(
                        "Testcontainers 2.x - API Changes",
                        "CRITICAL",
                        str(rel_path),
                        i,
                        "LocalStackContainer.Service enum removed",
                        "Remove .withServices() - services are now auto-detected"
                    )

        # Note: org.springframework.resilience.* is used in the external sample repo.
        # Keep this as informational instead of treating it as invalid.
        if 'org.springframework.resilience' in content:
            for i, line in enumerate(lines, 1):
                if 'org.springframework.resilience' in line:
                    self.result.add_issue(
                        "Spring Boot 4 - Retry/Resilience",
                        "INFO",
                        str(rel_path),
                        i,
                        "Using org.springframework.resilience annotations",
                        "Ensure AOP support; if using Spring Retry directly, use org.springframework.retry + explicit version"
                    )

        # Check for @Retryable usage (need Spring Retry dependency)
        if '@Retryable' in content:
            # Note: We'll need to check if dependency exists in pom
            for i, line in enumerate(lines, 1):
                if '@Retryable' in line and not line.strip().startswith('//'):
                    self.result.add_issue(
                        "Spring Boot 4 - Spring Retry",
                        "INFO",
                        str(rel_path),
                        i,
                        "Using @Retryable",
                        "Ensure spring-retry dependency with explicit version + spring-boot-starter-aspectj"
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
                if 'PostgreSQLContainer<?>' in line or 'MySQLContainer<?>' in line:
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
                if 'getEndpointOverride(' in line and 'Service' in line:
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
                self._scan_properties_file(props_path)

    def _scan_properties_file(self, file_path: Path):
        """Scan properties file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"   Error reading {file_path}: {e}")
            return

        content = ''.join(lines)
        rel_path = file_path.relative_to(self.project_path)

        # Check for old Jackson properties
        old_jackson_props = [
            'spring.jackson.read.',
            'spring.jackson.write.',
        ]

        for i, line in enumerate(lines, 1):
            for old_prop in old_jackson_props:
                if old_prop in line and not line.strip().startswith('#'):
                    self.result.add_issue(
                        "Spring Boot 4 - Configuration",
                        "WARNING",
                        str(rel_path),
                        i,
                        f"Old Jackson property: {line.strip()}",
                        "Change spring.jackson.* to spring.jackson.json.*"
                    )

        # Check for Spring Modulith event store config
        has_modulith_jdbc = 'spring.modulith.events.jdbc.schema' in content
        if self.result.spring_modulith_version != "Unknown" and not has_modulith_jdbc:
            self.result.add_issue(
                "Spring Modulith 2.0 - Configuration",
                "CRITICAL",
                str(rel_path),
                0,
                "Missing Spring Modulith event store configuration",
                "Add: spring.modulith.events.jdbc.schema=events"
            )

    def _scan_flyway_migrations(self):
        """Scan Flyway migrations for Spring Modulith event schema"""
        print("\n🗄️  Scanning Flyway migrations...")

        migration_dir = self.project_path / "src/main/resources/db/migration"
        if not migration_dir.exists():
            print("   No Flyway migrations found")
            return

        # Check for events schema migration
        root_migrations = migration_dir / "__root"
        if root_migrations.exists():
            events_schema_files = list(root_migrations.glob("V0__*events*.sql"))
            if not events_schema_files and self.result.spring_modulith_version != "Unknown":
                self.result.add_issue(
                    "Spring Modulith 2.0 - Database",
                    "CRITICAL",
                    "src/main/resources/db/migration/__root/",
                    0,
                    "Missing events schema migration",
                    "Create: V0__create_events_schema.sql with 'CREATE SCHEMA events;'"
                )
        elif self.result.spring_modulith_version != "Unknown":
            self.result.add_issue(
                "Spring Modulith 2.0 - Database",
                "CRITICAL",
                "src/main/resources/db/migration/",
                0,
                "Missing __root directory for events schema migration",
                "Create: __root/V0__create_events_schema.sql"
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
