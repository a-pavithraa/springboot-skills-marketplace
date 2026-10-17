# Progen Integration

[Progen](https://github.com/sivaprasadreddy/progen) is an offline CLI that generates a Spring Boot 4 project: build file, Docker Compose, Testcontainers, security, migrations, CI, and ArchUnit/Modulith tests. Use it for the base project. Then add the architecture layer from this skill on top.

Progen has no architecture option. Its layout is always package-by-module with Spring Modulith (`config/`, `shared/`, `users/`).

Tested with progen v1.0.3 on 2026-10-17. Progen pins Spring Boot 4.1.1 and Java 25.

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
- Progen runs `spotless:apply` (Maven) or `spotlessApply` (Gradle) at the end. This needs Java on `PATH` and network access on the first run. If it fails, progen exits with code 1, but the files exist. Run the formatter later.

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

- Tomato and DDD+Hexagonal need `--persistence jpa`. The templates in `assets/` and the `spring-data-jpa` skill assume JPA.
- With `jdbc` or `jooq`, do not apply JPA templates (`rich-entity.java`, `repository.java`, `spring-data-jpa` assets).
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
- Exit codes: 0 = success (warnings may print), 1 = invalid input, 2 = target directory exists, 3 = progen not installed.

## Step 3: Add the architecture layer

| Architecture | What to do after generation |
|--------------|-----------------------------|
| `package-by-module` | Matches progen. Add feature packages next to `users/`. |
| `modular-monolith` | Matches progen. Add `*API.java` and `internal/` per module. `ModularityTests.java` exists; do not add `assets/modularity-test.java` again. Copy only extra checks from it. |
| `tomato` | Add `domain/vo/`, rich entities, and `rest/converters/` per module. Apply `value-object.java`, `rich-entity.java`, `spring-converter.java`, `service-cqrs.java`. |
| `ddd-hexagonal` | Add `application/`, `domain/`, `infra/`, `interfaces/` per module. Change `ArchUnitTests.java` as shown below, because `*Handler` services fail the name rule. |
| `layered` | Add `controller/`, `service/`, `repository/`, `domain/`. The tests pass, but Modulith treats each layer as a module, which adds no value. Keep `users/` as the one feature package, and tell the user. |

### Templates to skip (progen already has them)

| Skip this asset | Progen file |
|-----------------|-------------|
| `exception-handler.java` | `config/GlobalExceptionHandler.java`. Add a `DomainException` handler there if needed. |
| `base-entity.java` | `shared/BaseEntity.java` (has `@Version`) |
| `docker-compose.yml` | `compose.yml` |
| `testcontainers-test.java` | `TestcontainersConfig.java`, `BaseIT.java` |
| `modularity-test.java` | `ModularityTests.java` |
| `pom-additions.xml` | Add only entries the pom does not have: `jspecify`, `hypersistence-utils-*` (TSID IDs), `spring-modulith-starter-jpa` (event registry). |

### Rules that progen's ArchUnit test enforces

`src/test/java/<base>/ArchUnitTests.java` uses Taikai. Code that breaks these rules fails the build:

- Controllers: names end with `Controller`, classes are package-private, no controller-to-controller calls.
- `@Service` classes: names end with `Service`.
- `@Repository` classes: names end with `Repository`.
- `@Configuration` classes: names end with `Config`.
- Loggers: `private static final Logger LOG`.
- No `@Autowired` fields. Use constructor injection.
- No generic `throws Exception` on methods.

Changes needed for this skill's patterns:

```java
// DDD+Hexagonal: allow command handlers
.services(services -> services
        .shouldNotDependOnControllers()
        .namesShouldMatch(".+(Service|Handler)"))
// spring-data-jpa custom repositories: allow *RepositoryImpl
.repositories(repositories ->
        repositories.shouldNotDependOnServices().namesShouldMatch(".+Repository(Impl)?"))
```

### Other differences

- Progen creates `V001__create_users_table.sql`. Start new Flyway files at `V002__`. Flyway reads `V1` and `V001` as the same version and fails.
- Progen sets `spring.threads.virtual.enabled=true`. This skill enables virtual threads only with workload evidence. Tell the user, and keep or remove it based on their answer.
- Progen adds BootUI, devtools, springdoc, JWT (for REST), Spotless, JaCoCo, and git-commit-id. Remove what the user does not want.

## Step 4: Verify

```bash
./mvnw test          # or ./gradlew test; Testcontainers needs Docker
```

Run `ArchUnitTests` and `ModularityTests` first. They run without Docker and catch layout errors quickly.
