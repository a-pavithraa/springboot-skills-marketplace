---
name: creating-springboot-projects
description: Create Spring Boot projects with Java 25 and Spring Boot 4. Use when user wants to create, build, scaffold, setup, or initialize a new Spring Boot application, microservice, REST API, or backend service; asks for project structure recommendations; mentions Java 25 or Spring Boot 4 features (RestTestClient, HTTP Service Clients, API versioning, JSpecify null-safety, modularization); needs architecture guidance (layered, package-by-module, modular monolith, tomato, DDD+hexagonal); or requests Spring Initializr setup. Also triggers on discussions about Spring Boot architecture patterns, Value Objects, CQRS, or domain-driven design.
---

# Creating Spring Boot Projects

## Critical Rules

**NEVER jump to implementation. ALWAYS assess complexity first.**

**MANDATORY versions:** Java 25 + Spring Boot 4.0.x (latest stable)
**Platform baseline:** Spring Framework 7, Jakarta EE 11 (Servlet 6.1); Java 17+ required.

## Workflow

### Step 1: Assess Complexity

Ask user:
1. **Domain Complexity** - Simple CRUD or complex business rules?
2. **Team Size** - 1-3, 3-10, or 10+?
3. **Lifespan** - Months, 1-2 years, or 5+ years?
4. **Type Safety** - Basic validation or strong typing needed?
5. **Bounded Contexts** - Single domain or multiple subdomains?

### Step 2: Choose Architecture

| Pattern | When | Complexity |
|---------|------|-----------|
| **layered** | Simple CRUD, prototypes, MVPs | ⭐ |
| **package-by-module** | 3-5 distinct features, medium apps | ⭐⭐ |
| **modular-monolith** | Need module boundaries, Spring Modulith | ⭐⭐ |
| **tomato** | Rich domain, Value Objects, type safety | ⭐⭐⭐ |
| **ddd-hexagonal** | Complex domains, CQRS, infrastructure independence | ⭐⭐⭐⭐ |

**For detailed criteria, package structures, and naming conventions:** See [architecture-guide.md](references/architecture-guide.md)

### Step 3: Create Project

**Use Spring Initializr:** https://start.spring.io

**Required configuration:**
- Project: Maven or Gradle (Gradle 9 supported)
- Language: Java
- Spring Boot: 4.0.x (latest stable)
- Java: 25

**Core dependencies:**
- Spring Web MVC (`spring-boot-starter-webmvc`)
- Spring Data JPA
- Validation
- Flyway (`spring-boot-starter-flyway`) or Liquibase (`spring-boot-starter-liquibase`)
- PostgreSQL/MySQL Driver
- Testcontainers
- Spring Boot Actuator

**Starter conventions (Spring Boot 4 modularization):**
- Prefer `spring-boot-starter-<technology>` and matching `spring-boot-starter-<technology>-test`
- Avoid raw third-party deps when a Boot starter exists (for example Flyway/Liquibase)

**Additional dependencies:**
- Spring Modulith - for Modular Monolith/Tomato
- ArchUnit - for DDD+Hexagonal

**Spring Boot 4 features:** RestTestClient, HTTP Service Clients, API Versioning, modularization, JSpecify null-safety improvements, OpenTelemetry starter, Kotlin serialization, JmsClient, TaskDecorator composition

**For detailed Spring Boot 4 feature documentation:** See [spring-boot-4-features.md](references/spring-boot-4-features.md)

### Step 4: Implement Pattern

**Use templates from `assets/` directory.** All templates use placeholders:
- `{{PACKAGE}}` → `com.example`
- `{{MODULE}}` → `products`
- `{{NAME}}` → `Product`

**Core templates:**
- `value-object.java` - Type-safe Value Objects
- `rich-entity.java` - Entities with behavior
- `repository.java` - @Query examples
- `service-cqrs.java` - Write/read services
- `controller.java` - REST controllers
- `spring-converter.java` - @PathVariable binding
- `modularity-test.java` - Spring Modulith tests
- `flyway-migration.sql` - Database migrations
- `exception-handler.java` - ProblemDetail errors

**Spring Boot 4 templates:**
- `http-service-client.java` - @HttpExchange clients
- `api-versioning-config.java` - API versioning
- `resttestclient-test.java` - Modern testing
- `package-info-jspecify.java` - Null-safety
- `resilience-service.java` - Resiliency example (external reference)

**Data access:** For complex queries, DTO projections, performance optimization, use the `spring-data-jpa` skill.

### Step 5: Infrastructure Setup

**Always include:**
- Flyway/Liquibase migrations
- Testcontainers integration tests
- Docker Compose for local development
- Swagger/OpenAPI documentation
- ProblemDetail error handling
- JSpecify null-safety

**Optional (based on requirements):**
- API versioning
- HTTP Service Clients
- OpenAPI documentation (third-party, e.g., Springdoc)

**For detailed infrastructure patterns:** See `pom-additions.xml` in assets/

## Quick Reference

**Package structures:** [architecture-guide.md](references/architecture-guide.md)
**Naming conventions:** [architecture-guide.md](references/architecture-guide.md)
**Anti-patterns:** [architecture-guide.md](references/architecture-guide.md)
**Upgrade paths:** [architecture-guide.md](references/architecture-guide.md)
**Spring Boot 4 features:** [spring-boot-4-features.md](references/spring-boot-4-features.md)

## Key Principle

**Start simple. Upgrade when complexity demands it.**

## External References (Non-Official)

- https://github.com/sivaprasadreddy/spring-boot-4-features
- https://github.com/sivaprasadreddy/spring-modular-monolith
