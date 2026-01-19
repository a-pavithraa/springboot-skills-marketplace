# Migration Overview

## Common Migration Scenarios

### Scenario 1: Spring Boot 3 → 4 Only

**Scan output shows:** Spring Boot dependency updates only

**Steps:**
1. Read `spring-boot-4-migration.md`
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

### Scenario 3: Fixing Retry/Resilience Logic

**Scan output shows:** `@Retryable` / `@ConcurrencyLimit` usage

**Critical fix:**
- Ensure AOP support via `spring-boot-starter-aspectj`
- Ask whether to keep Spring Retry or migrate to native `org.springframework.resilience.annotation.*`
- If using Spring Retry directly, add explicit `spring-retry` dependency/version
- See `spring-boot-4-migration.md` → "Retry/Resilience Annotations" section

## Critical Migration Issues

### Issue 1: Jackson 3 Breaking Changes
- Group ID changed: `com.fasterxml.jackson` → `tools.jackson`
- Exception: `jackson-annotations` stays with old group ID
- Class renames: `Jackson2ObjectMapperBuilderCustomizer` → `JsonMapperBuilderCustomizer`

**Reference:** `spring-boot-4-migration.md` → "Jackson 3 Migration"

### Issue 2: Test Annotation Renames
- `@MockBean` → `@MockitoBean`
- `@SpyBean` → `@MockitoSpyBean`
- `@WebMvcTest` package relocated
- `@SpringBootTest` may need `@AutoConfigureMockMvc`

**Reference:** `spring-boot-4-migration.md` → "Test Changes"

### Issue 3: Spring Modulith Event Store Schema
- Spring Modulith 2.0 REQUIRES updating the `event_publication` table schema
- Dedicated `events` schema is optional (use for larger apps if desired)
- For a dedicated schema, create a Flyway migration like `V1__create_events_schema.sql`
- Configure `spring.modulith.events.jdbc.schema=events` only if using a dedicated schema

**Reference:** `spring-modulith-2-migration.md`

### Issue 4: Testcontainers Package Changes
- Artifacts renamed with `testcontainers-` prefix
- Container classes relocated to `org.testcontainers.<module>` packages (e.g., `org.testcontainers.postgresql`)
- JUnit 4 support removed

**Reference:** `testcontainers-2-migration.md` (module-specific changes like LocalStack)

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

**Reference:** `spring-boot-4-migration.md` → "Migration Strategy"

## References

- [Spring Boot 4.0 Migration Guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide)
- [Spring Modulith 2.0 Reference](https://docs.spring.io/spring-modulith/reference/)
- [Testcontainers 2.0 Migration Guide](https://java.testcontainers.org/migrations/testcontainers-2/)
- [spring-boot-4-features (sample repo)](https://github.com/sivaprasadreddy/spring-boot-4-features)
- [Vlad Mihalcea's Blog](https://vladmihalcea.com/blog/) - JPA/Hibernate best practices
