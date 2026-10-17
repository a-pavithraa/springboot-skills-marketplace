# Spring Boot 3 → 4 Migration

Official: [4.0 Migration Guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide), [4.1 Release Notes](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.1-Release-Notes). Checked against Boot 4.1.1 on 2026-10-17.

New Boot 4 features (RestTestClient, HTTP service clients, API versioning, native resilience, JSpecify) are covered in `../../creating-springboot-projects/references/spring-boot-4-features.md`. This file covers what must change.

## Contents

1. [Targets](#targets)
2. [Strategy](#strategy)
3. [Phase 1: Dependencies](#phase-1-dependencies)
4. [Phase 2: Code](#phase-2-code)
5. [Phase 3: Tests](#phase-3-tests)
6. [Phase 4: Configuration](#phase-4-configuration)
7. [Upgrading from 4.0 to 4.1](#upgrading-from-40-to-41)
8. [Verification and common failures](#verification-and-common-failures)
9. [Checklist](#checklist)

---

## Targets

| Component | Minimum | Target |
|-----------|---------|--------|
| Java | 17 | 25 (LTS). Newer releases: `../../creating-springboot-projects/references/java-version-policy.md` |
| Spring Boot | 4.0 | 4.1.x |
| Spring Framework | 7.0 | 7.0.x (Boot 4.1.1 uses 7.0.9) |
| Jakarta EE / Servlet | 11 / 6.1 | same |
| Spring Modulith | 2.0 | 2.1.x (`spring-modulith-2-migration.md`) |
| Testcontainers | 2.0 | 2.0.x (Boot 4.1.1 manages 2.0.5; `testcontainers-2-migration.md`) |

Go from 3.x straight to 4.1. Clear 4.0 deprecations on the way: 4.1 removes everything deprecated in 4.0.

## Strategy

| Option | How | Use when |
|--------|-----|----------|
| Classic starters | Replace starters with `spring-boot-starter-classic` and `spring-boot-starter-test-classic` | Large apps; you want the build green first. They provide all modules but exclude their transitive dependencies |
| Direct | Move to modular starters now (web → webmvc, and so on) | Small or medium apps |

Spring recommends moving off the classic starters eventually.

---

## Phase 1: Dependencies

| Change | Before | After |
|--------|--------|-------|
| Web MVC starter | `spring-boot-starter-web` (deprecated) | `spring-boot-starter-webmvc` |
| AOP starter | `spring-boot-starter-aop` | `spring-boot-starter-aspectj`, **only** if the app uses AspectJ (`@Aspect` from `org.aspectj.lang.annotation`, Micrometer `@Timed`/`@Counted`/`@Observed`, Resilience4j annotations). Otherwise remove it |
| RestClient / RestTemplate | included in the web starter | add `spring-boot-starter-restclient` |
| WebClient | included in webflux | add `spring-boot-starter-webclient` |
| Flyway / Liquibase | `flyway-core` / `liquibase-core` alone | `spring-boot-starter-flyway` (+ `flyway-database-<db>`) / `spring-boot-starter-liquibase` |
| Security tests | `spring-security-test` | `spring-boot-starter-security-test` (needed for `@WithMockUser` / `@WithUserDetails`) |
| Modular test starters | `spring-boot-starter-test` covered everything | add `spring-boot-starter-<module>-test` for slices you use (for example `-webmvc-test`, `-data-jpa-test`), or use `-test-classic` |
| Spring Retry | `spring-retry` + `@EnableRetry` | remove; use native resilience (Phase 2) |
| Jackson 2 | `com.fasterxml.jackson.core:jackson-databind` | `tools.jackson.core:jackson-databind` (Phase 2). Temporary bridge: `spring-boot-jackson2` (deprecated) |

`@Async`, `@Transactional`, `@Cacheable`, and native `@Retryable`/`@ConcurrencyLimit` use Spring AOP proxies. They do not need the AspectJ starter.

---

## Phase 2: Code

### Jackson 3

Group ID and packages change for `jackson-core` and `jackson-databind` only. `jackson-annotations` keeps `com.fasterxml.jackson.core` and the `com.fasterxml.jackson.annotation` package on purpose.

| Jackson 2 / Boot 3 | Jackson 3 / Boot 4 |
|--------------------|--------------------|
| `com.fasterxml.jackson.databind.*`, `com.fasterxml.jackson.core.*` | `tools.jackson.databind.*`, `tools.jackson.core.*` |
| `ObjectMapper` bean customization | `JsonMapper` (`tools.jackson.databind.json.JsonMapper`) |
| `JsonProcessingException` (checked) | `JacksonException` (unchecked). Remove `throws`/`catch` that only existed for it |
| `JsonSerializer` / `JsonDeserializer` / `SerializerProvider` | `ValueSerializer` / `ValueDeserializer` / `SerializationContext` |
| `Jackson2ObjectMapperBuilderCustomizer` | `JsonMapperBuilderCustomizer` (`org.springframework.boot.jackson.autoconfigure`) |
| `@JsonComponent` / `@JsonMixin` | `@JacksonComponent` / `@JacksonMixin` |
| `JsonObjectSerializer` / `JsonValueDeserializer` | `ObjectValueSerializer` / `ObjectValueDeserializer` |
| `builder.serializationInclusion(...)` | `builder.changeDefaultPropertyInclusion(incl -> incl.withValueInclusion(...))` |

```java
@Component
class JacksonConfig implements JsonMapperBuilderCustomizer {
    public void customize(JsonMapper.Builder builder) {
        builder.changeDefaultPropertyInclusion(
            incl -> incl.withValueInclusion(JsonInclude.Include.NON_NULL));
    }
}
```

Libraries that bring their own Jackson 2 serializers (some Redis, Kafka, or HTTP client setups) need their Jackson 3 variants. For Spring Data Redis 4, see `../../code-reviewer/references/performance-patterns.md#distributed-caching-redis`.

### Package relocations

| Old | New |
|-----|-----|
| `org.springframework.boot.BootstrapRegistry` / `BootstrapContext` | `org.springframework.boot.bootstrap.*` |
| `org.springframework.boot.autoconfigure.domain.EntityScan` | `org.springframework.boot.persistence.autoconfigure.EntityScan` |
| `org.springframework.boot.test.autoconfigure.web.servlet.*` (`@WebMvcTest`, `@AutoConfigureMockMvc`) | `org.springframework.boot.webmvc.test.autoconfigure.*` |

### Spring Retry → native resilience

1. Remove `spring-retry`.
2. Replace `@EnableRetry` with `@EnableResilientMethods` on a `@Configuration` class. It is required; Boot does not auto-enable it.
3. Imports: `org.springframework.retry.annotation.*` → `org.springframework.resilience.annotation.*`.
4. Parameters: `retryFor` → `includes`; `backoff = @Backoff(delay = 1000, multiplier = 2)` → `delay = 1000, multiplier = 2`; `maxAttempts` (total calls) → `maxRetries` (retries after the first call): `maxAttempts = 4` becomes `maxRetries = 3`.
5. `@Recover` has no native equivalent. Catch the final exception in the caller, or use `RetryTemplate`.
6. Circuit breakers stay on Resilience4j (`resilience4j-spring-boot4`, needs the AspectJ starter).

### Optional modernization

Not required for the upgrade. Do it after the build is green:

- Manual `HttpServiceProxyFactory` beans → `@ImportHttpServices`; configure groups with `spring.http.serviceclient.<group>.base-url` and shared settings with `spring.http.clients.*`.
- Custom API-versioning filters → `spring.mvc.apiversion.*` and `version = "..."` on mappings.

Details: `../../creating-springboot-projects/references/spring-boot-4-features.md`.

---

## Phase 3: Tests

| Change | Fix |
|--------|-----|
| `@MockBean` / `@SpyBean` were removed in 4.0 (deprecated since 3.4) | `@MockitoBean` / `@MockitoSpyBean` from `org.springframework.test.context.bean.override.mockito` |
| `@MockBean` fields inside a `@TestConfiguration` class | Not supported by `@MockitoBean`. Move them to the test class, or to a type-level annotation: `@MockitoBean(types = UserRepository.class)` (repeatable; works on the test class, a superclass, or a meta-annotation) |
| `@SpringBootTest` no longer provides MockMvc | Add `@AutoConfigureMockMvc` |
| `@SpringBootTest` no longer provides `TestRestTemplate` | Add `@AutoConfigureTestRestTemplate`, or move to `RestTestClient` with `@AutoConfigureRestTestClient`. `TestRestTemplate` is not deprecated |
| `@WithMockUser` / `@WithUserDetails` stop working | Add `spring-boot-starter-security-test` |

`@AutoConfigureWebTestClient` is for the reactive `WebTestClient`. It does not replace `TestRestTemplate`.

```java
@SpringBootTest(webEnvironment = WebEnvironment.RANDOM_PORT)
@AutoConfigureRestTestClient
class UserControllerTest {
    @Autowired RestTestClient client;

    @Test
    void getsUser() {
        client.get().uri("/users/1").exchange()
              .expectStatus().isOk()
              .expectBody(User.class);
    }
}
```

---

## Phase 4: Configuration

| Change | Action |
|--------|--------|
| Liveness and readiness probes are on by default | Expect `/actuator/health/liveness` and `/readiness`. Disable with `management.endpoint.health.probes.enabled=false` |
| DevTools live reload is off by default | `spring.devtools.livereload.enabled=true` to turn it on |
| Jackson properties | 4.0 moved JSON-specific `spring.jackson.read.*`/`write.*` to `spring.jackson.json.read.*`/`json.write.*`, and replaced `spring.jackson.parser.*` with `json.read.*`. In 4.1, `spring.jackson.read.*`/`write.*` exist again for stream features (`StreamReadFeature`/`StreamWriteFeature`) |

Jackson property families in 4.1:

| Family | Feature enum | Example |
|--------|--------------|---------|
| `spring.jackson.json.read.*` / `json.write.*` | `JsonReadFeature` / `JsonWriteFeature` | `spring.jackson.json.read.allow-trailing-comma=true` |
| `spring.jackson.serialization.*` / `deserialization.*` | `SerializationFeature` / `DeserializationFeature` | `spring.jackson.serialization.indent-output=true` (not `json.write`) |
| `spring.jackson.read.*` / `write.*` | `StreamReadFeature` / `StreamWriteFeature` | format-independent stream settings |

Run the app once with `spring-boot-properties-migrator` on the classpath. It reports renamed properties at startup. Remove it afterwards.

---

## Upgrading from 4.0 to 4.1

- Items deprecated in 4.0 are removed.
- `spring.data.jpa.repositories.bootstrap-mode=deferred` now fails at startup if no suitable `AsyncTaskExecutor` bean exists. With `lazy`, the auto-configured bootstrap executor is no longer set.
- jOOQ 3.20 is the minimum, and it requires Java 21.
- The Maven plugin no longer skips test AOT processing on `-DskipTests`. Use `-Dmaven.test.skip=true`.
- The layertools jar mode is removed. Use `-Djarmode=tools`.
- Tomcat's temporary base directory is deleted on shutdown. Set `server.tomcat.basedir` if you need it to persist.
- Derby is deprecated. Move to H2 or HSQLDB.

---

## Verification and common failures

After each phase: `./mvnw clean verify` (or `./gradlew build`), start the app, and check `/actuator/health`.

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `NoClassDefFoundError` / `NoSuchMethodError` for `com.fasterxml.jackson.databind.*` | A library still needs Jackson 2 | `./mvnw dependency:tree -Dincludes=com.fasterxml.jackson.core`; upgrade the library or add `spring-boot-jackson2` temporarily |
| `RestClient.Builder` bean not found | Missing `spring-boot-starter-restclient` | Add it |
| Flyway migrations do not run | Only `flyway-core` on the classpath | Add `spring-boot-starter-flyway` |
| `@Retryable` / `@ConcurrencyLimit` do nothing | Missing `@EnableResilientMethods`, old `org.springframework.retry` imports, or a self-invocation (call from the same class bypasses the proxy) | Fix the enablement, imports, or call path |
| `MockMvc` / `TestRestTemplate` bean not found in tests | No longer auto-provided | `@AutoConfigureMockMvc` / `@AutoConfigureTestRestTemplate` |
| `@WithMockUser` ignored | Missing security test starter | Add `spring-boot-starter-security-test` |

---

## Checklist

Phase 1: Dependencies
- [ ] Boot 4.1.x; webmvc, restclient/webclient, flyway/liquibase starters
- [ ] AspectJ starter kept only for real AspectJ use
- [ ] Module test starters (or `-test-classic`); `spring-boot-starter-security-test`
- [ ] `spring-retry` removed; Jackson 3 coordinates; Testcontainers 2 coordinates

Phase 2: Code
- [ ] Jackson 3 imports, classes, customizers
- [ ] Package relocations (EntityScan, BootstrapRegistry, WebMvcTest)
- [ ] Native resilience with `@EnableResilientMethods`

Phase 3: Tests
- [ ] `@MockitoBean` / `@MockitoSpyBean`; no mocks in `@TestConfiguration`
- [ ] `@AutoConfigureMockMvc` / `@AutoConfigureTestRestTemplate` or `RestTestClient`

Phase 4: Configuration
- [ ] Properties migrated (`spring-boot-properties-migrator` run once)
- [ ] Health probes and DevTools defaults reviewed

## References

- [Spring Boot 4.0 Migration Guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide), [4.1 Release Notes](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.1-Release-Notes)
- [Spring Framework 7.0 What's New](https://docs.spring.io/spring-framework/reference/7.0/whatsnew.html)
- [Jackson 3 migration](https://github.com/FasterXML/jackson/blob/main/jackson3/MIGRATING_TO_JACKSON_3.md)
- [Core Spring Resilience Features](https://spring.io/blog/2025/09/09/core-spring-resilience-features/)
