# Progen Integration

[Progen](https://github.com/sivaprasadreddy/progen) is an offline CLI that generates a Spring Boot 4 project: build file, Docker Compose, Testcontainers, security, migrations, CI, and ArchUnit/Modulith tests. Use it for the base project. Then add the architecture layer from this skill on top.

Progen has no architecture option. Its layout is always package-by-module with Spring Modulith (`config/`, `shared/`, `users/`).

Tested with progen v1.0.3 on 2026-10-21 (REST, Maven, PostgreSQL). Progen pins Spring Boot 4.1.1, Java 25 and Taikai 1.66.0.

## When to use progen

Use progen when all of these are true:

- `command -v progen` finds it, or the user agrees to install it.
- The project is a REST API, a server-rendered web app (Thymeleaf), or a Spring Boot + Angular app.
- The database is PostgreSQL, MySQL, or MariaDB.
- The user accepts Spring Security with a sample `users` module. Progen always generates it.

Otherwise, use Spring Initializr (Step 3 of `SKILL.md`).

Install: `go install github.com/sivaprasadreddy/progen@latest`, or download a binary from the releases page. On macOS the binary is unsigned. The user must allow it in Finder (Control-click, Open).

## Safety rules

- **Progen deletes `./<AppName>/` before it generates.** Never run it where that directory exists. The helper script refuses to run in that case.
- Progen does not validate most values. An invalid value becomes the default, with only a WARNING. Use the helper script. It rejects invalid values.
- **The generated project doesn't compile.** `config/WebSecurityConfig.java` imports `AntPathRequestMatcher`, which Spring Security 7 removed. The import is unused: delete that line.
- Progen runs `spotless:apply` (Maven) or `spotlessApply` (Gradle) at the end. This needs Java on `PATH` and network access on the first run. If only that step fails, progen prints "failed to format project code" and exits with 1, but the files exist; the script reports this as a warning. Any other progen failure stops the script with exit code 4. On JDK 27 the step always fails (palantir-java-format: `NoSuchFieldError ... JCCompilationUnit`), so run progen and Spotless with JDK 25.

## Step 1: Map the assessment to progen options

| Assessment answer | Script option | Progen value |
|-------------------|---------------|--------------|
| JSON API | `--app-type rest` (default) | `REST API` |
| Server-rendered UI | `--app-type web` | `Web App` (Thymeleaf is on) |
| Angular SPA | `--app-type angular` | `Spring Boot + Angular Full Stack` |
| Maven / Gradle | `--build-tool maven\|gradle` | `Maven` / `Gradle` |
| JPA (all architectures in this skill) | `--persistence jpa` (default) | `Spring Data JPA` |
| SQL-first, user asks for it | `--persistence jdbc\|jooq` | `Spring JdbcClient` / `jOOQ` |
| Database | `--db postgresql\|mysql\|mariadb` | `PostgreSQL` / `MySQL` / `MariaDB` |
| Migrations | `--migration flyway\|liquibase` | `Flyway` / `Liquibase` |
| Optional features | `--features aws,email,rabbitmq,redis,otel,k8s,htmx` | `*Support: true` |
| Java other than 25 | `--java 21` | Script edits the build file after generation |

Rules:

- Tomato and DDD+Hexagonal need `--persistence jpa`. The templates in `assets/` assume JPA.
- With `jdbc` or `jooq`, do not apply JPA templates (`assets/rich-entity.java`, `assets/repository.java`).
- `htmx` needs `--app-type web`.
- Read `java-version-policy.md` before you pass `--java` above 25.

## Step 2: Generate

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/progen_config.py" \
  --app-name shop --base-package com.acme.shop \
  --build-tool maven --db postgresql --features redis \
  --out-dir /path/to/parent --run
```

- Without `--run`, the script only writes and prints `.progen.json`. Show it to the user before you generate.
- The project goes to `<out-dir>/<app-name>/`.
- Exit codes: 0 = success (warnings may print, for example a failed formatting step), 1 = invalid input, 2 = target directory exists, 3 = progen not installed, 4 = progen failed or the project may be incomplete, 5 = generated but the Java version could not be set.

## Step 3: Add the architecture layer

| Architecture | What to do after generation |
|--------------|-----------------------------|
| `package-by-module` | Matches progen. Add feature packages next to `users/`. |
| `modular-monolith` | Matches progen. Add `*API.java` and `internal/` per module. `ModularityTests.java` exists; do not add `assets/modularity-test.java` again. Copy only extra checks from it. |
| `tomato` | Add `domain/vo/`, rich entities, and `rest/converters/` per module. Apply `assets/value-object.java`, `assets/rich-entity.java`, `assets/spring-converter.java`, `assets/service-cqrs.java`. |
| `ddd-hexagonal` | Add `application/`, `domain/`, `infra/`, `interfaces/` per module. Change `ArchUnitTests.java` as shown below, because `*Handler` services fail the name rule. |
| `layered` | Add `controller/`, `service/`, `repository/`, `domain/`. The tests pass, but Modulith treats each layer as a module, which adds no value. Keep `users/` as the one feature package, and tell the user. |

### Templates to skip (progen already has them)

| Skip this asset | Progen file |
|-----------------|-------------|
| `assets/exception-handler.java` | `config/GlobalExceptionHandler.java`. Add a `DomainException` handler there if needed. |
| `assets/base-entity.java` | `shared/BaseEntity.java` (has `@Version`) |
| `assets/docker-compose.yml` | `compose.yml` |
| `assets/testcontainers-test.java` | `TestcontainersConfig.java`, `BaseIT.java` |
| `assets/modularity-test.java` | `ModularityTests.java` |
| `assets/pom-additions.xml` | Add only entries the pom does not have: `jspecify`, `hypersistence-utils-*` (TSID IDs), `spring-modulith-starter-jpa` (event registry). |

### Rules that progen's ArchUnit test enforces

`src/test/java/<base>/ArchUnitTests.java` uses Taikai. Code that breaks these rules fails the build:

- Controllers: names end with `Controller`, classes are package-private, no controller-to-controller calls.
- `@Service` classes: names end with `Service`, no dependency on controllers.
- `@Repository` classes: names end with `Repository`, no dependency on services.
- `@Configuration` classes: names end with `Config`.
- Loggers: `private static final Logger LOG`.
- No `@Autowired` fields, no generic `throws Exception`, no deprecated APIs, no import cycles.
- No `@Disabled` tests; test classes are package-private.
- Naming: no `I` prefix on interfaces, no `List`/`Set`/`Map` suffix on fields, constants in upper case.

Add the rules marked `[beyond progen]` in `assets/architecture-rules-test.java` to this file: no self-invocation of proxied methods (with Framework 7's native `@Retryable` added), no `@Transactional` in controllers, no controller use of Spring Data repositories, no `System.out`, and the entity rules. Three changes are needed first (verified: `ArchUnitTests`, `ModularityTests` and `./mvnw verify` pass afterwards):

1. Set `<taikai.version>2.1.0</taikai.version>` in the pom. Taikai 1.66.0 has no `jpa()` rules, so the entity rules don't compile.
2. Taikai 2 takes a predicate in `classesShouldBePackagePrivate`. Replace `classesShouldBePackagePrivate(".*Test(s)")` with `classesShouldBePackagePrivate(JavaClass.Predicates.simpleNameEndingWith("Tests"))` (import `com.tngtech.archunit.core.domain.JavaClass`).
3. Make `users/UserEntity.java` package-private (`class UserEntity`). Nothing outside `users` uses it; the entity rule fails on it otherwise.

Changes needed for this skill's patterns:

```java
// DDD+Hexagonal: allow command handlers
.services(services -> services
        .shouldNotDependOnControllers()
        .namesShouldMatch(".+(Service|Handler)"))
// Spring Data custom repository fragments: allow *RepositoryImpl
.repositories(repositories ->
        repositories.shouldNotDependOnServices().namesShouldMatch(".+Repository(Impl)?"))
```

### Other differences

- Progen creates `V001__create_users_table.sql`. Start new Flyway files at `V002__`. Flyway reads `V1` and `V001` as the same version and fails.
- Progen sets `spring.modulith.events.republish-outstanding-events-on-restart=true` and `spring.modulith.events.jdbc.schema-initialization.enabled=true`. Spring Modulith advises against both for production: republishing duplicates events when several instances run, and the table should come from a Flyway migration. Tell the user before production use.
- Progen sets `spring.threads.virtual.enabled=true`. This skill enables virtual threads only with workload evidence. Tell the user, and keep or remove it based on their answer.
- Progen adds BootUI, devtools, springdoc, JWT (for REST), Spotless, JaCoCo, and git-commit-id. Remove what the user does not want.

## Step 4: Verify

```bash
./mvnw test          # or ./gradlew test; Testcontainers needs Docker
```

Run `ArchUnitTests` and `ModularityTests` first. They run without Docker and catch layout errors quickly.
