# Spring Boot 4: Review Rules

This file lists what to flag in a Boot 4 code review. For full before/after code, read:

- Boot 3 → 4 changes (starters, Jackson 3, tests): `../../springboot-migration/references/spring-boot-4-migration.md`
- New Boot 4 features (RestTestClient, native resilience, HTTP service clients, API versioning, JSpecify): `../../creating-springboot-projects/references/spring-boot-4-features.md`
- Virtual threads: `java-25-features.md#virtual-threads`

## Contents

1. [Build and starters](#build-and-starters)
2. [Jackson 3](#jackson-3)
3. [Tests](#tests)
4. [Resilience](#resilience)
5. [HTTP clients and API versioning](#http-clients-and-api-versioning)
6. [Errors, configuration, observability](#errors-configuration-observability)
7. [Virtual threads](#virtual-threads)
8. [Review checklist](#review-checklist)

---

## Build and starters

Use the Spring Boot BOM: `spring-boot-starter-parent` or an imported `spring-boot-dependencies` (4.1.x).

| Flag | Fix |
|------|-----|
| `spring-boot-starter-web` (deprecated) | `spring-boot-starter-webmvc` |
| `spring-boot-starter-aop` | `spring-boot-starter-aspectj` |
| `RestClient` / `RestTemplate` used, no `spring-boot-starter-restclient` | Add it. `spring-boot-starter-webmvc` no longer includes RestClient auto-configuration |
| `WebClient` used, no `spring-boot-starter-webclient` | Add it |
| `spring-boot-starter-test` alone, but tests use MockMvc, security, or JPA test slices | Add the matching `*-test` starters (for example `spring-boot-starter-webmvc-test`), or use `spring-boot-starter-test-classic` |
| `spring-boot-starter-classic` / `-test-classic` in a finished migration | Acceptable as a temporary step. Suggest moving to modular starters later |

Source: [Spring Boot 4.0 Migration Guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide), [Modularizing Spring Boot](https://spring.io/blog/2025/10/28/modularizing-spring-boot/)

---

## Jackson 3

Boot 4 uses Jackson 3 by default. Jackson 2 works only through the deprecated `spring-boot-jackson2` module.

| Flag | Fix |
|------|-----|
| `com.fasterxml.jackson.core:jackson-core` / `jackson-databind` | `tools.jackson.core:*` |
| `import com.fasterxml.jackson.databind.*` / `com.fasterxml.jackson.core.*` | `tools.jackson.databind.*` / `tools.jackson.core.*` |
| `Jackson2ObjectMapperBuilderCustomizer` | `JsonMapperBuilderCustomizer` (customizes `JsonMapper.Builder`) |
| `builder.serializationInclusion(...)` | `changeDefaultPropertyInclusion(incl -> incl.withValueInclusion(...))` |
| `@JsonComponent` | `@JacksonComponent` |
| `JsonProcessingException` (catch or `throws`) | `tools.jackson.core.JacksonException`. It is unchecked, so `throws` clauses and forced `try/catch` blocks can go |

Do NOT flag `com.fasterxml.jackson.core:jackson-annotations` or `com.fasterxml.jackson.annotation.*` imports. Annotations keep the old group ID and package on purpose, so Jackson 2 and 3 can coexist.

Source: [Introducing Jackson 3 support in Spring](https://spring.io/blog/2025/10/07/introducing-jackson-3-support-in-spring/), [Migrating to Jackson 3](https://github.com/FasterXML/jackson/blob/main/jackson3/MIGRATING_TO_JACKSON_3.md)

---

## Tests

| Flag | Fix |
|------|-----|
| `@MockBean` / `@SpyBean` | `@MockitoBean` / `@MockitoSpyBean` (`org.springframework.test.context.bean.override.mockito`) |
| `org.springframework.boot.test.autoconfigure.web.servlet.*` | `org.springframework.boot.webmvc.test.autoconfigure.*` |
| `@SpringBootTest` that autowires `MockMvc` without `@AutoConfigureMockMvc` | Add `@AutoConfigureMockMvc` |
| `@SpringBootTest` that autowires `TestRestTemplate` without `@AutoConfigureTestRestTemplate` | Add the annotation, or move to `RestTestClient` with `@AutoConfigureRestTestClient`. `TestRestTemplate` is NOT deprecated, only no longer auto-provided |

Source: [RestTestClient](https://docs.spring.io/spring-framework/reference/testing/resttestclient.html)

---

## Resilience

Spring Framework 7 has native `@Retryable` and `@ConcurrencyLimit` (`org.springframework.resilience.annotation`). Spring Retry is maintenance-only.

| Flag | Fix |
|------|-----|
| `@Retryable` or `@ConcurrencyLimit` without `@EnableResilientMethods` on a `@Configuration` class | Add `@EnableResilientMethods`. Without it, the annotations do nothing |
| Annotation-based resilience (native or Resilience4j) without `spring-boot-starter-aspectj` | Add the starter |
| `spring-retry` dependency or `@EnableRetry` | Move to native annotations. `maxRetries` counts retries, not attempts (`maxRetries = 2` means up to 3 calls) |
| Circuit breaker built by hand | Use Resilience4j (`resilience4j-spring-boot4`). Circuit breakers are NOT native in Spring 7 |
| Retries on non-idempotent calls, or no backoff | Check `includes`, `delay`, `multiplier` against the call's semantics |

Source: [Core Spring Resilience Features](https://spring.io/blog/2025/09/09/core-spring-resilience-features/)

---

## HTTP clients and API versioning

| Flag | Fix |
|------|-----|
| Manual `HttpServiceProxyFactory` beans for `@HttpExchange` interfaces | `@ImportHttpServices(group = "...", types = ...)` (Framework 7, package `org.springframework.web.service.registry`). `@HttpExchange` itself exists since Framework 6 |
| Custom versioning filters, interceptors, or libraries | Native `spring.mvc.apiversion.*` properties and `version = "2.0"` on `@GetMapping` etc., or `WebMvcConfigurer.configureApiVersioning(ApiVersionConfigurer)` |
| `WebClient...block()` in blocking MVC code | `RestClient`. Blocking on a reactive client adds overhead with no benefit |

Source: [HTTP Service Client Enhancements](https://spring.io/blog/2025/09/23/http-service-client-enhancements/), [API Versioning in Spring](https://spring.io/blog/2025/09/16/api-versioning-in-spring/)

---

## Errors, configuration, observability

| Flag | Fix |
|------|-----|
| Custom `ErrorResponse` classes in `@RestControllerAdvice` | Return `ProblemDetail` (RFC 9457, which replaces RFC 7807). Set `spring.mvc.problemdetails.enabled=true` for framework exceptions |
| Many `@Value` fields for one config area | `@ConfigurationProperties(prefix = "app")` on a record, with nested records |
| Secrets in `application.properties` | Environment variables or a secret store (`${SECRET_KEY}`) |
| No metrics or health endpoints exposed in a service that runs in production | Expose `health,metrics,prometheus` with `management.endpoints.web.exposure.include`. Prometheus export: `management.prometheus.metrics.export.enabled` |
| Tracing sampled at `1.0` in production config | Lower `management.tracing.sampling.probability` |
| Hand-rolled OpenTelemetry setup | `spring-boot-starter-opentelemetry` |

---

## Virtual threads

Recommend `spring.threads.virtual.enabled=true` only with evidence: 10,000+ concurrent I/O-bound tasks and measured thread-pool exhaustion. Full rules and sources: `java-25-features.md#virtual-threads`.

Do not replace small thread pools that exist on purpose, for example a pool of 5 that protects an external API. Virtual threads would remove that limit. Use `@ConcurrencyLimit` if a limit must stay.

Example of a wrong recommendation: a service with 100 requests per day and a pool of 2-5 threads. Keep the pool.

---

## Review checklist

- [ ] Starters use Boot 4 names (webmvc, aspectj, restclient, webclient)
- [ ] Jackson uses `tools.jackson.*`, except `jackson-annotations`
- [ ] `@MockitoBean` / `@MockitoSpyBean`; MockMvc and TestRestTemplate auto-configuration is explicit
- [ ] Native `@Retryable` / `@ConcurrencyLimit` have `@EnableResilientMethods` and `spring-boot-starter-aspectj`
- [ ] HTTP service clients use `@ImportHttpServices`
- [ ] API versioning uses native `spring.mvc.apiversion.*`
- [ ] Errors use `ProblemDetail`; configuration uses `@ConfigurationProperties`
- [ ] Virtual threads only with workload evidence; intentional pool limits kept

## Official documentation

- [Spring Boot 4.0 Release Notes](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Release-Notes), [Migration Guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide)
- [Spring Boot Reference](https://docs.spring.io/spring-boot/reference/), [Upgrading Spring Boot](https://docs.spring.io/spring-boot/upgrading.html)
- [Resilience4j Spring Boot](https://resilience4j.readme.io/docs/getting-started-3)
