# Migration Overview

## Table of Contents

1. [Common Migration Scenarios](#common-migration-scenarios)
2. [Critical Migration Issues](#critical-migration-issues)
3. [Migration Strategies](#migration-strategies)
4. [References](#references)

---

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

### Scenario 3: TestRestTemplate → RestTestClient

**Scan output shows:** `TestRestTemplate` usage

**Steps:**
1. Replace `TestRestTemplate` with `RestTestClient` in test classes
2. Add `@AutoConfigureRestTestClient` annotation
3. Rewrite assertions to use fluent API (`.expectStatus()`, `.expectBody()`)
4. See `spring-boot-4-migration.md` → "TestRestTemplate → RestTestClient" section

### Scenario 4: HTTP Service Client Migration

**Scan output shows:** Manual `HttpServiceProxyFactory` setup

**Steps:**
1. Keep existing `@HttpExchange` interfaces unchanged
2. Replace manual `HttpServiceProxyFactory` bean with `@ImportHttpServices`
3. Move base URL and timeout config to `spring.http.serviceclient.<group>.*` properties
4. See `spring-boot-4-migration.md` → "HTTP Service Client" section

### Scenario 5: Fixing Retry/Resilience Logic

**Scan output shows:** `@Retryable` / `@ConcurrencyLimit` usage

**Critical fix:**
- Ensure AOP support via `spring-boot-starter-aspectj`
- Migrate from Spring Retry (`spring-retry`) to native `org.springframework.resilience.annotation.*` — Spring Retry is maintenance-only
- Replace `@EnableRetry` with `@EnableResilientMethods`
- Remove `spring-retry` dependency from pom.xml
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

### Issue 4: TestRestTemplate no longer auto-provided
- `TestRestTemplate` is **not deprecated** in Boot 4, but `@SpringBootTest` no longer auto-configures it.
- Opt in with `@AutoConfigureTestRestTemplate` to keep existing tests working.
- For new tests, prefer `RestTestClient` (Spring Framework 7.0) with `@AutoConfigureRestTestClient`.

**Reference:** `spring-boot-4-migration.md` → "TestRestTemplate → RestTestClient"

### Issue 5: Manual HttpServiceProxyFactory Unnecessary
- `@ImportHttpServices` replaces manual proxy factory wiring (Framework 7.0)
- `@HttpExchange` interfaces remain unchanged (existed since Framework 6.0)

**Reference:** `spring-boot-4-migration.md` → "HTTP Service Client"

### Issue 6: RestClient/WebClient Modular Starters
- `spring-boot-starter-webmvc` no longer includes RestClient auto-configuration
- Add `spring-boot-starter-restclient` for RestClient/RestTemplate
- Add `spring-boot-starter-webclient` for WebClient

**Reference:** `spring-boot-4-migration.md` → "RestClient / WebClient Modular Starters"

### Issue 7: Testcontainers Package Changes
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
- [Testcontainers 2.0.0 release notes](https://github.com/testcontainers/testcontainers-java/releases/tag/2.0.0) and [OpenRewrite Testcontainers 2.x migration recipe](https://docs.openrewrite.org/recipes/java/testing/testcontainers/testcontainers2migration)
- [spring-boot-4-features (sample repo)](https://github.com/sivaprasadreddy/spring-boot-4-features)
- [Vlad Mihalcea's Blog](https://vladmihalcea.com/blog/) - JPA/Hibernate best practices
