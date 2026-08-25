---
name: creating-springboot-projects
description: Use when starting a new Spring Boot 4 project — scaffolding a service, REST API, or modular backend; picking an architecture (layered, package-by-module, modular-monolith, tomato, DDD-hexagonal); selecting Spring Boot 4 features; or applying the bundled templates and references in this skill. Not for migrating existing projects or for isolated JPA/repository work without broader project-creation context.
---

# Creating Spring Boot Projects

## Purpose

Use this skill to create new Spring Boot 4 projects or define their structure before implementation. The skill adds value when the user needs an architecture decision, Spring Boot 4 feature selection, or the bundled templates in `assets/`.

## Critical rules

- Never jump straight to implementation before assessing project complexity.
- Default to the simplest architecture that fits the domain.
- Treat Spring Boot 4 as the target. Default new projects to Java 25 (current LTS). Boot 4's official baseline is Java 17 — accept Java 21 (previous LTS) or Java 17 when the user asks for them. Java 26 is the newest feature release (GA 2026-03-17) but is non-LTS; only pick it if the project tracks non-LTS Java.
- Read the reference files before choosing a higher-complexity architecture or optional framework feature.
- Reuse the templates in `assets/` instead of rewriting the same scaffolding from scratch.

## Workflow

### Step 1: Assess project shape

Collect the project constraints first:

1. Domain complexity: simple CRUD, moderate workflow, or rich domain rules.
2. Team size: 1-3, 3-10, or 10+.
3. Expected lifespan: months, 1-2 years, or 5+ years.
4. Type-safety needs: basic validation or strong value-object-heavy modeling.
5. Bounded contexts: single domain or multiple feature areas.
6. Persistence and infrastructure needs: database choice, migration tool, local development setup.

### Step 2: Choose the architecture

Use this matrix as the default decision aid. If the choice is not obvious, read `references/architecture-guide.md` before proceeding.

| Pattern | Use when | Complexity |
|---------|----------|------------|
| `layered` | CRUD services, prototypes, MVPs | Low |
| `package-by-module` | 3-5 distinct features with moderate growth | Low-Medium |
| `modular-monolith` | Module boundaries matter and Spring Modulith is justified | Medium |
| `tomato` | Rich domain modeling, value objects, stronger type safety | Medium-High |
| `ddd-hexagonal` | Complex domains, CQRS, strong infrastructure isolation | High |

> `tomato` is a value-object-heavy modular monolith: JPA entities embed VOs, validation lives in VO constructors, and Spring converters bind VOs at the request boundary. See `references/architecture-guide.md` for the full definition.

### Step 3: Define the initial Boot 4 setup

Use Spring Initializr and capture the baseline:

- Project: Maven or Gradle
- Language: Java
- Spring Boot: 4.1.x
- Java: 25 (recommended — current LTS). Boot 4's minimum is Java 17; use 21 for the previous LTS, or 17 for stricter compatibility. Java 26 (GA 2026-03-17) is the latest feature release but is non-LTS.

Baseline dependencies for most projects:

- Spring Web MVC
- Validation
- Spring Data JPA if persistence is required
- Flyway or Liquibase
- database driver
- Spring Boot Actuator
- Testcontainers for integration tests

Optional dependencies based on architecture or features:

- Spring Modulith for modular monolith or tomato designs
- ArchUnit for stronger architecture enforcement
- Additional Spring Boot 4 features only when the use case needs them

Read `references/spring-boot-4-features.md` before selecting:

- RestTestClient
- HTTP Service Clients
- API versioning
- JSpecify null-safety
- resilience features

### Step 4: Apply the matching assets

Use the bundled templates from `assets/` and replace placeholders only after the package and module names are settled.

#### Placeholder convention

Every template uses `{{TOKEN}}` placeholders. Resolve all of them before applying — templates do not compile until every placeholder is replaced. The full set used across `assets/`:

| Placeholder | Replace with | Example |
|-------------|--------------|---------|
| `{{PACKAGE}}` | Base Java package | `com.acme.shop` |
| `{{MODULE}}` | Feature/module name (lowercase) | `orders` |
| `{{NAME}}` | Domain type name (PascalCase) | `Order`, `ProductSKU` |
| `{{TYPE}}` | Wrapped scalar type inside a value object | `String`, `Long`, `BigDecimal` |
| `{{FIELD}}` | Record field name (camelCase) | `code`, `amount` |
| `{{TABLE_NAME}}` | Database table name (used in JPA `@Table`) | `orders` |
| `{{TABLE}}` | Same meaning as `{{TABLE_NAME}}` — legacy variant kept only in `flyway-migration.sql` | `orders` |
| `{{PROJECT_NAME}}` | Project artifactId / docker prefix (used only in `docker-compose.yml`) | `shop-api` |
| `{{name}}` | HTTP service group identifier — **not** a lowercase variant of `{{NAME}}`. Appears only in commented `@ImportHttpServices(group = "...")` examples. | `orders` |

If a template uses a placeholder not listed here, treat it as a typo and confirm the intended value before applying.

Core project templates:

- `assets/controller.java`
- `assets/repository.java`
- `assets/base-entity.java`
- `assets/rich-entity.java`
- `assets/value-object.java`
- `assets/spring-converter.java`
- `assets/service-cqrs.java`
- `assets/exception-handler.java`
- `assets/flyway-migration.sql`
- `assets/docker-compose.yml`

Boot 4 and modularity templates:

- `assets/http-service-client.java`
- `assets/api-versioning-config.java`
- `assets/resttestclient-test.java`
- `assets/package-info-jspecify.java`
- `assets/modularity-test.java`
- `assets/resilience-service.java`
- `assets/pom-additions.xml`
- `assets/testcontainers-test.java`

### Step 5: Fill in architecture-specific pieces

Read `references/architecture-guide.md` for package structure and apply the matching templates:

- `layered`: keep modules simple and avoid premature DDD abstractions
- `package-by-module`: group by feature and keep shared code minimal
- `modular-monolith`: add Modulith verification and explicit module APIs
- `tomato`: add value objects and rich domain entities where they protect important invariants
- `ddd-hexagonal`: separate application, domain, and infrastructure explicitly

### Step 6: Hand off specialized concerns when needed

- Use `spring-data-jpa` when the user needs deeper query, projection, repository, or relationship decisions.
- Use `springboot-migration` for upgrades of existing applications rather than new-project setup.

## Reference loading guide

- Package structures, anti-patterns, and upgrade paths: `references/architecture-guide.md`
- Spring Boot 4 feature-specific guidance: `references/spring-boot-4-features.md`

## Output format

When the user asks for a plan or scaffold recommendation, return:

```markdown
## Recommended architecture
- Pattern:
- Why:

## Initial setup
- Build tool:
- Java version:
- Spring Boot version:
- Core dependencies:

## Assets to apply
- `assets/...`

## Next implementation steps
1. ...
2. ...
3. ...
```

## When not to use this skill

- Migrating an existing Boot project
- Deep repository and query tuning without broader project-creation work
- Generic Spring Boot feature Q&A with no need for the bundled templates
