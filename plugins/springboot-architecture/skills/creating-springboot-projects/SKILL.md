---
name: creating-springboot-projects
description: Use when creating new Spring Boot projects - assess complexity first, choose appropriate architecture (Layered to DDD+Hexagonal), then implement using templates. Triggers include when user wants to create, build, scaffold, setup, or initialize a new Spring Boot application, microservice, REST API, or backend service; asks for project structure or architecture recommendations; mentions starting a Spring Boot project from scratch; needs guidance on choosing between architecture patterns (layered, package-by-module, modular monolith, tomato, DDD+hexagonal); or requests Spring Boot project setup with Spring Initializr.
---

# Creating Spring Boot Projects

## Critical Rules

**NEVER jump to implementation. ALWAYS assess complexity first.**

**ALWAYS use Java 25 and Spring Boot 4.0.x (latest stable). These versions are MANDATORY.**
- Java 25 provides modern language features and performance improvements
- Spring Boot 4 includes jSpecify null safety, native resiliency, and improved testing
- Older versions are not supported by this skill

## Step 1: Assess Complexity

Ask user:
1. **Domain Complexity** - Simple CRUD or complex business rules?
2. **Team Size** - 1-3, 3-10, or 10+?
3. **Lifespan** - Months, 1-2 years, or 5+ years?
4. **Type Safety** - Basic validation or strong typing needed (financial/healthcare)?
5. **Bounded Contexts** - Single domain or multiple subdomains?

## Step 2: Choose Architecture

| Pattern | When | Complexity |
|---------|------|-----------|
| **layered** | Simple CRUD, prototypes, MVPs | ⭐ |
| **package-by-module** | 3-5 distinct features, medium apps | ⭐⭐ |
| **modular-monolith** | Need module boundaries, Spring Modulith | ⭐⭐ |
| **tomato** | Rich domain, Value Objects, type safety | ⭐⭐⭐ |
| **ddd-hexagonal** | Complex domains, CQRS, infrastructure independence | ⭐⭐⭐⭐ |

**Decision criteria:**

| Criteria | Layered | Package-by-Module | Modulith | Tomato | DDD+Hex |
|----------|---------|-------------------|----------|--------|---------|
| Team Size | 1-3 | 3-10 | 5-15 | 5-15 | 10+ |
| Lifespan | Months | 1-2 yrs | 2-5 yrs | 3-5 yrs | 5+ yrs |
| Type Safety | Low | Low | Low | High | High |
| Learning Curve | ⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |

## Step 3: Create Project Structure

**Create Spring Boot project using Spring Initializr:**

```
Visit: https://start.spring.io

Configure:
- Project: Maven
- Language: Java
- Spring Boot: 4.0.x (latest stable)
- Packaging: Jar
- Java: 25

Add Dependencies:
- Spring Web
- Spring Data JPA
- Validation
- Flyway Migration
- PostgreSQL/MySQL Driver
- Testcontainers
- Docker Compose Support (for local dev environment)
- Springdoc OpenAPI (v3.0.0 for Spring Boot 4)
- Spring Boot Actuator

Additional for Modular Monolith/Tomato:
- Spring Modulith (v2.0.1)

Additional for DDD+Hexagonal:
- ArchUnit (v1.2.1)
```

**Spring Boot 4 New Features (Detailed):**

1. **TestRestClient** - Modern REST testing (replaces TestRestTemplate)
   - Fluent, readable API for integration tests
   - Built-in API versioning support with `.apiVersion("2.0")`
   - Better type safety with ParameterizedTypeReference
   - Template: `testrestclient-test.java`

2. **Native Resiliency** - Built-in fault tolerance (no Resilience4j needed)
   - `@Retryable` - Automatic retries with configurable delays
   - `@CircuitBreaker` - Prevent cascading failures, fail fast
   - `@ConcurrencyLimit` - Rate limiting and bulkhead pattern
   - Template: `resilience-service.java`

3. **HTTP Service Client Simplification** - Declarative REST clients
   - Define interface with `@HttpExchange`
   - Use `@GetExchange`, `@PostExchange`, etc.
   - Auto-configured with `@ImportHttpServices(YourClient.class)`
   - No manual HttpServiceProxyFactory setup!
   - Template: `http-service-client.java`

4. **API Versioning** - Native versioning without external libs
   - Configure via `ApiVersionConfigurer` in WebMvcConfigurer
   - Three strategies: Header (recommended), Query param, Media type
   - Controller methods: `@GetMapping(value = "/search", version = "2.0")`
   - Works with TestRestClient and HTTP Service Clients
   - Template: `api-versioning-config.java`

5. **Spring Data AOT** - Ahead-of-time compilation
   - Faster startup with GraalVM native images
   - Enable with `process-aot` goal in pom.xml
   - Better performance for cloud/serverless deployments

6. **jSpecify NullSafety** - Compile-time null checking
   - Package-level `@NullMarked` annotation
   - All types non-null by default
   - Use `@Nullable` for optional fields
   - IDE integration for warnings
   - Template: `package-info-jspecify.java`

## Step 4: Implement Pattern

### Package Structures

**Layered:** `controller/` `service/` `repository/` `domain/`

**Package-by-Module:**
```
products/domain/  products/rest/
orders/domain/    orders/rest/
shared/
```

**Tomato** (adds Value Objects to Package-by-Module):
```
products/
  domain/
    vo/             ← ProductSKU, Price, Quantity
    ProductEntity.java
    ProductService.java
    ProductQueryService.java
  rest/
    converters/     ← StringToProductSKUConverter
```

**DDD+Hexagonal:**
```
products/
  application/command/  application/query/
  domain/model/  domain/vo/
  infra/persistence/
  interfaces/rest/
```

### Use Assets

Template files in `assets/` directory have `{{PLACEHOLDER}}` markers:
- `{{PACKAGE}}` → `com.example`
- `{{MODULE}}` → `products`
- `{{NAME}}` → `Product`

**Core templates:**
- `value-object.java` - Type-safe VOs (SKU, Email, Price)
- `rich-entity.java` - Entities with behavior
- `repository.java` - @Query examples
- `service-cqrs.java` - Write/read services
- `controller.java` - REST with VOs
- `spring-converter.java` - Path variable binding
- `modularity-test.java` - Spring Modulith tests
- `flyway-migration.sql` - Database schema
- `exception-handler.java` - ProblemDetail (RFC 7807)

**Spring Boot 4 templates:**
- `http-service-client.java` - Declarative REST clients with @HttpExchange
- `api-versioning-config.java` - Native API versioning setup
- `resilience-service.java` - @Retryable, @CircuitBreaker, @ConcurrencyLimit
- `testrestclient-test.java` - Modern integration testing
- `package-info-jspecify.java` - Null-safety with @NullMarked

**See all templates:** `ls assets/`

### Data Access Implementation

For detailed repository implementation patterns beyond basic templates:

**Use the `spring-data-jpa` skill** for:
- Complex queries with @Query, pagination, sorting
- DTO projections for read-only, performance-critical queries
- Custom repositories with Criteria API for dynamic filtering
- CQRS query services (JdbcTemplate-based reads)
- Entity relationship patterns (ManyToOne, OneToMany, avoiding ManyToMany)
- Performance optimization (N+1 prevention, batch operations)

The `repository.java` template provides basic structure. For production-grade implementations with performance optimization, consult the `spring-data-jpa` skill.

### Naming Conventions (Tomato/DDD)

| Type | Pattern | Example |
|------|---------|---------|
| Entity | `*Entity` | `ProductEntity` |
| Value Object | Domain name | `ProductSKU`, `Price` |
| Command | `*Cmd` | `CreateProductCmd` |
| View Model | `*VM` | `ProductVM` |
| Write Service | `*Service` | `ProductService` |
| Read Service | `*QueryService` | `ProductQueryService` |
| Module API | `*API` | `ProductsAPI` |

## Step 5: Required Infrastructure

**All patterns need:**
- Flyway/Liquibase migrations (template: `flyway-migration.sql`)
- Testcontainers (template: `testcontainers-test.java`)
- Docker Compose (template: `docker-compose.yml`)
- Swagger/OpenAPI (Springdoc v3.0.0+)
- ProblemDetail errors (template: `exception-handler.java`)
- JSpecify null-safety (template: `package-info-jspecify.java`)

**Consider adding:**
- API Versioning (template: `api-versioning-config.java`) if planning multiple API versions
- HTTP Service Clients (template: `http-service-client.java`) for external API integration
- Resiliency features (template: `resilience-service.java`) for production-grade fault tolerance
- TestRestClient tests (template: `testrestclient-test.java`) for modern integration testing

**Tomato/DDD add:**
- TSID dependency (see `pom-additions.xml`)
- BaseEntity (template: `base-entity.java`)
- Spring Converters (template: `spring-converter.java`)
- ModularityTest (template: `modularity-test.java`)

## Anti-Patterns

| Don't | Do |
|-------|-----|
| Jump to implementation | Ask assessment questions first |
| Use DDD for simple CRUD | Use Layered or Package-by-Module |
| Use Layered for complex domain | Use Tomato or DDD+Hexagonal |
| Skip infrastructure | Always include Flyway, Testcontainers, Docker |
| Copy code without understanding | Read template comments, adapt to your domain |

## Upgrade Path

| From | To | When |
|------|-----|------|
| Layered | Package-by-Module | 3+ features, team grows |
| Package-by-Module | Modular Monolith | Need enforced boundaries |
| Modular Monolith | Tomato | Type confusion bugs, validation scattered |
| Tomato | DDD+Hexagonal | Need infrastructure independence, CQRS |

**Start simple. Upgrade when complexity demands it.**
