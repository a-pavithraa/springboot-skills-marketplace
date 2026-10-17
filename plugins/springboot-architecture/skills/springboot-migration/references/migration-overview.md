# Migration Overview

Use this file to route scanner findings to the right guide. The guides hold the details.

## Order

1. Spring Boot 4 (`spring-boot-4-migration.md`)
2. Spring Modulith 2 (`spring-modulith-2-migration.md`). Boot 4 needs Modulith 2; Modulith 1.x does not run on it.
3. Testcontainers 2 (`testcontainers-2-migration.md`). Boot 4 manages Testcontainers 2 versions, so test code must move too.

Steps 2 and 3 are part of the same upgrade when the project uses them. Build and test after each step.

## Scanner finding → where to look

| Finding | Guide section |
|---------|---------------|
| Starter renames, missing restclient/flyway starters | `spring-boot-4-migration.md#phase-1-dependencies` |
| `com.fasterxml.jackson.databind` imports, Jackson 2 customizers | `spring-boot-4-migration.md#jackson-3` |
| `@MockBean` / `@SpyBean`, old `WebMvcTest` package, `TestRestTemplate` | `spring-boot-4-migration.md#phase-3-tests` |
| `spring-retry`, `@EnableRetry`, `org.springframework.retry` imports | `spring-boot-4-migration.md#spring-retry--native-resilience` |
| Manual `HttpServiceProxyFactory` | `spring-boot-4-migration.md#optional-modernization` |
| Renamed properties | `spring-boot-4-migration.md#phase-4-configuration` |
| Modulith 1.x dependencies, `event_publication` table | `spring-modulith-2-migration.md` |
| Testcontainers 1.x artifacts, `org.testcontainers.containers.*` imports, `<?>` generics | `testcontainers-2-migration.md` |
| `StableValue` / `StructuredTaskScope` preview APIs | `../../creating-springboot-projects/references/java-version-policy.md` |

## Strategy

- **Direct** (small and medium apps): move to modular starters and new APIs in one pass.
- **Classic starters** (large apps): `spring-boot-starter-classic` + `spring-boot-starter-test-classic` first, then modular starters later.

## Automated help (optional)

- OpenRewrite has `org.openrewrite.java.spring.boot4.UpgradeSpringBoot_4_0` in `org.openrewrite.recipe:rewrite-spring`. It is under the Moderne Source Available License and needs extra Maven repository setup. Ask the user before using it, and review its changes like any other diff.
- OpenRewrite also has a [Testcontainers 2 recipe](https://docs.openrewrite.org/recipes/java/testing/testcontainers/testcontainers2migration).
- `spring-boot-properties-migrator` reports renamed properties at startup. Remove it after the upgrade.

## References

- [Spring Boot 4.0 Migration Guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide)
- [Spring Modulith Reference](https://docs.spring.io/spring-modulith/reference/)
- [Testcontainers 2.0.0 release notes](https://github.com/testcontainers/testcontainers-java/releases/tag/2.0.0)
- [spring-boot-4-features sample repo](https://github.com/sivaprasadreddy/spring-boot-4-features)
