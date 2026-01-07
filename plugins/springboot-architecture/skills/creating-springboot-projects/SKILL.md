---
name: creating-springboot-projects
description: Use when creating new Spring Boot projects - assess complexity first, choose appropriate architecture (Layered to DDD+Hexagonal), then implement using templates
---

# Creating Spring Boot Projects

## Critical Rule

**NEVER jump to implementation. ALWAYS assess complexity first.**

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

**Spring Boot 4 New Features:**
- **TestRestClient** - Modern REST testing API (replaces TestRestTemplate)
- **Native Resiliency** - Built-in circuit breakers, retries without external libs
- **HTTP Service Client** - Simplified @HttpExchange for external APIs
- **Spring Data AOT** - Faster startup with GraalVM native images
- **jSpecify NullSafety** - Better compile-time null checking

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

### Use Templates

Templates in `templates/` directory have `{{PLACEHOLDER}}` markers:
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

**See all templates:** `ls templates/`

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
- Swagger/OpenAPI (Springdoc)
- ProblemDetail errors (template: `exception-handler.java`)

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
