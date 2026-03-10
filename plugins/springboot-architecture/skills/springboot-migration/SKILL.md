---
name: springboot-migration
description: Migrates Spring Boot applications to Boot 4 with Java 25, including related Spring Modulith 2 and Testcontainers 2 upgrade work. Use when the task is a concrete upgrade, dependency transition, starter rename, test-annotation migration, or phased migration plan. Do not use for greenfield project creation or for isolated repository design questions.
---

# Spring Boot Migration

## Purpose

Use this skill for phased upgrade work on existing Spring Boot applications. This skill adds value through the migration scanner, the Boot 4 / Modulith 2 / Testcontainers 2 reference guides, and a strict migration order that avoids mixing too many changes at once.

## Critical rules

- Never migrate blindly. Scan the codebase first.
- Never apply every migration at once. Follow phased upgrades.
- Treat Java 25, Spring Boot 4, Spring Modulith 2, and Testcontainers 2 as the intended target stack for this skill unless the user asks for a narrower target.
- Verify after each phase and stop when failures appear.

## Workflow

### Step 1: Scan the project

Use the migration scanner before planning or editing:

```bash
python3 <SKILL_DIR>/scripts/scan_migration_issues.py /path/to/project
```

Use the scan output to identify:

- current Spring Boot version
- starter rename work
- annotation and import migrations
- configuration changes
- Spring Modulith compatibility
- Testcontainers compatibility

### Step 2: Identify which migrations apply

Load only the references that match the codebase:

| Migration | Trigger | Read |
|-----------|---------|------|
| Spring Boot 4.0 | Boot 3.x to 4.x upgrade | `references/spring-boot-4-migration.md` |
| Spring Modulith 2.0 | Existing Modulith 1.x usage | `references/spring-modulith-2-migration.md` |
| Testcontainers 2.x | Existing Testcontainers 1.x usage | `references/testcontainers-2-migration.md` |
| Cross-cutting scenarios and pitfalls | Mixed upgrade planning | `references/migration-overview.md` |

### Step 3: Plan the migration in phases

Use the reference guides to plan and execute in this order.

#### Phase 1: Dependencies

- update `pom.xml` or `build.gradle`
- rename starters where required
- add or remove dependencies needed by the target stack
- align version properties

#### Phase 2: Source-code changes

- update imports and package names
- migrate test annotations
- fix Jackson 3 issues
- fix Testcontainers API changes where relevant

#### Phase 3: Configuration

- update `application.properties` or `application.yml`
- apply Boot 4 defaults intentionally
- update Spring Modulith event-store configuration if relevant

#### Phase 4: Verification

- run unit tests
- run integration tests
- run container-based tests where present
- check for deprecations and startup failures

### Step 4: Use the right migration order for mixed upgrades

When multiple ecosystems are involved, use this order:

1. Spring Boot 4
2. Spring Modulith 2
3. Testcontainers 2

Read `references/migration-overview.md` before deviating from this sequence.

### Step 5: Report progress after each phase

After each phase, report:

- what changed
- what remains
- what failed, if anything
- whether it is safe to continue

## Reference loading guide

- Spring Boot 4 migration details: `references/spring-boot-4-migration.md`
- Spring Modulith 2 migration details: `references/spring-modulith-2-migration.md`
- Testcontainers 2 migration details: `references/testcontainers-2-migration.md`
- Mixed scenarios and common issues: `references/migration-overview.md`

## Available script

- `scripts/scan_migration_issues.py`

## Output format

When planning or reporting the migration, return:

```markdown
## Migration scope
- Current versions:
- Target versions:

## Planned phases
1. ...
2. ...
3. ...

## Files expected to change
- `path/to/file`

## Verification
- Tests or checks to run
```

## When not to use this skill

- Creating a new Spring Boot project from scratch
- Broad architecture advice without an actual migration task
- JPA-specific implementation work that belongs in `spring-data-jpa`
