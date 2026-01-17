---
name: springboot-migration
description: Migrate Spring Boot projects to version 4.0 with Java 25, including Spring Modulith 2.0 and Testcontainers 2.x upgrades. Use when user requests upgrading Spring Boot, migrating to Java 25, updating dependencies to Spring Boot 4, mentions Jackson 3 migration, asks about starter renames (web→webmvc, aop→aspectj), fixing test annotations (@MockBean→@MockitoBean), or needs help with Spring Modulith 2.0 or Testcontainers 2.x compatibility. Analyzes codebase for migration issues and guides through changes with specific file references.
---

# Spring Boot Migration

## Critical Rules

**NEVER migrate blindly. ALWAYS scan the codebase first to understand the current state.**

**NEVER apply all migrations at once. ALWAYS follow the phased approach.**

**MANDATORY versions:** Java 25 + Spring Boot 4.0.x + Spring Modulith 2.0.x + Testcontainers 2.x

## Workflow

### Step 1: Scan Project

Use the migration scanner to identify what needs to be migrated:

```bash
python3 scripts/scan_migration_issues.py /path/to/project
```

This will analyze:
- Spring Boot version and required changes
- Dependency issues (starter renames, version updates)
- Code issues (annotation changes, package relocations)
- Configuration issues (property renames, new defaults)
- Spring Modulith compatibility
- Testcontainers compatibility

### Step 2: Assess Migration Scope

Based on scan results, determine which migrations apply:

| Migration | Trigger | Reference |
|-----------|---------|-----------|
| **Spring Boot 4.0** | Any Spring Boot 3.x → 4.0 upgrade | `references/spring-boot-4-migration.md` |
| **Spring Modulith 2.0** | Using Spring Modulith 1.x | `references/spring-modulith-2-migration.md` |
| **Testcontainers 2.x** | Using Testcontainers 1.x | `references/testcontainers-2-migration.md` |

**Decision tree:**

```
Is project using Spring Boot 3.x?
├─ Yes → Spring Boot 4.0 migration required
│   ├─ Using Spring Modulith? → Also migrate Spring Modulith 2.0
│   ├─ Using Testcontainers? → Also migrate Testcontainers 2.x
│   └─ Read: references/spring-boot-4-migration.md
└─ No → Check individual component versions
```

### Step 3: Plan Migration Phases

**CRITICAL:** Migrations must be done in phases to ensure stability:

#### Phase 1: Dependencies (Safe)
- Update `pom.xml` / `build.gradle`
- Rename starters (web→webmvc, aop→aspectj, etc.)
- Add missing dependencies (Spring Retry, etc.)
- Update version numbers

**Reference:** Each migration guide's "Dependency Changes" section

#### Phase 2: Code Changes (Breaking)
- Update imports and package relocations
- Migrate test annotations (@MockBean→@MockitoBean)
- Fix Jackson 3 usage (if applicable)
- Update Testcontainers imports (if applicable)

**Reference:** Each migration guide's "Code Changes" section

#### Phase 3: Configuration (Optional)
- Update application.properties
- Configure new Spring Boot 4 defaults
- Add Spring Modulith event store config (if applicable)

**Reference:** Each migration guide's "Configuration Changes" section

#### Phase 4: Testing (Mandatory)
- Run unit tests
- Run integration tests
- Verify container tests
- Check for deprecation warnings

### Step 4: Execute Migration

**For each phase:**

1. **Read the relevant migration guide** (don't skip this)
2. **Apply changes to files** identified in scan
3. **Verify after each phase** with tests
4. **DO NOT continue** if tests fail - fix issues first

**Migration order for multi-component upgrades:**
1. Spring Boot 4.0 first (base framework)
2. Spring Modulith 2.0 second (depends on Boot 4)
3. Testcontainers 2.x third (test infrastructure)

### Step 5: Verification Checklist

After migration, verify:

- [ ] Build succeeds: `./mvnw clean package`
- [ ] All tests pass
- [ ] No deprecation warnings in startup logs
- [ ] Application starts successfully
- [ ] Critical endpoints respond correctly
- [ ] Database migrations run (if using Flyway/Liquibase)
- [ ] Event store initialized (if using Spring Modulith)
- [ ] Testcontainers work in tests

## Common Migration Scenarios

### Scenario 1: Spring Boot 3 → 4 Only

**Scan output shows:** Spring Boot dependency updates only

**Steps:**
1. Read `references/spring-boot-4-migration.md`
2. Follow dependency updates section
3. Apply code changes (annotations, imports)
4. Update configuration if needed
5. Test thoroughly

### Scenario 2: Full Stack Migration (Boot + Modulith + Testcontainers)

**Scan output shows:** All three components need updates

**Steps:**
1. Read all three migration guides
2. Start with Spring Boot 4 migration
3. Apply Spring Modulith 2 changes (event store schema!)
4. Apply Testcontainers 2 changes (package renames)
5. Test at each step

### Scenario 3: Fixing Broken Retry Logic

**Scan output shows:** `org.springframework.resilience` imports (non-existent)

**Critical fix:**
- Spring Retry is NO LONGER auto-managed in Spring Boot 4
- Must add explicit dependency with version
- Must add `spring-boot-starter-aspectj` for AOP support
- See `references/spring-boot-4-migration.md` → "Spring Retry" section

## Critical Migration Issues

### Issue 1: Jackson 3 Breaking Changes
- Group ID changed: `com.fasterxml.jackson` → `tools.jackson`
- Exception: `jackson-annotations` stays with old group ID
- Class renames: `Jackson2ObjectMapperBuilderCustomizer` → `JsonMapperBuilderCustomizer`

**Reference:** `references/spring-boot-4-migration.md` → "Jackson 3 Migration"

### Issue 2: Test Annotation Renames
- `@MockBean` → `@MockitoBean`
- `@SpyBean` → `@MockitoSpyBean`
- `@WebMvcTest` package relocated
- `@SpringBootTest` may need `@AutoConfigureMockMvc`

**Reference:** `references/spring-boot-4-migration.md` → "Test Changes"

### Issue 3: Spring Modulith Event Store Schema
- Spring Modulith 2.0 REQUIRES dedicated `events` schema
- Must create migration: `V0__create_events_schema.sql`
- Must enable Flyway integration
- Must configure event store properties

**Reference:** `references/spring-modulith-2-migration.md`

### Issue 4: Testcontainers Package Changes
- Artifacts renamed with `testcontainers-` prefix
- Package structure changed: `org.testcontainers.containers.postgresql` → `org.testcontainers.postgresql`
- LocalStack `.withServices()` removed
- `getEndpointOverride(Service)` → `getEndpoint()`

**Reference:** `references/testcontainers-2-migration.md`

## Migration Strategies

### Strategy A: Direct Migration (Recommended)
Update directly to new starters and APIs.

**Pros:** Clean, modern codebase
**Cons:** More changes at once
**Best for:** Small-medium projects, green field migrations

### Strategy B: Classic Starters (Gradual)
Use `spring-boot-starter-classic` and `spring-boot-starter-test-classic` temporarily.

**Pros:** Fewer breaking changes, easier rollback
**Cons:** Eventually need to migrate anyway
**Best for:** Large projects, risk-averse migrations

**Reference:** `references/spring-boot-4-migration.md` → "Migration Strategy"

## Quick Reference

### When to Load References

- **Spring Boot 4 issues** → `references/spring-boot-4-migration.md`
- **Spring Modulith 2 issues** → `references/spring-modulith-2-migration.md`
- **Testcontainers 2 issues** → `references/testcontainers-2-migration.md`

### Available Scripts

- `scripts/scan_migration_issues.py` - Analyzes project for migration issues

### Official Documentation

All migration guidance based on official documentation:
- [Spring Boot 4.0 Migration Guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide)
- [Spring Modulith 2.0 Reference](https://docs.spring.io/spring-modulith/reference/)
- [Testcontainers 2.0 Migration Guide](https://java.testcontainers.org/migrations/testcontainers-2/)
- [Vlad Mihalcea's Blog](https://vladmihalcea.com/blog/) - JPA/Hibernate best practices

## Anti-Patterns

| Don't | Do | Why |
|-------|-----|-----|
| Migrate everything at once | Migrate in phases | Easier debugging |
| Skip scanning | Scan first | Know the scope |
| Ignore test failures | Fix immediately | Prevents cascading issues |
| Use classic starters permanently | Migrate to modular eventually | Technical debt |
| Suppress type errors with `@ts-ignore` equivalent | Fix root cause | Maintainability |
| Skip reading migration guides | Read before implementing | Avoid mistakes |

## Key Principle

**Understand before changing. Verify after changing. Never skip testing.**
