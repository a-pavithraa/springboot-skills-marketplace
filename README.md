# Spring Boot Skills Marketplace

A curated set of Claude Code skills for building Spring Boot apps with the right architecture from day one.

## Why This Exists

Most projects start simple and grow. This marketplace helps you pick an architecture that fits *today* while keeping a clear upgrade path for *tomorrow*.

Core idea:

> **Start simple. Add complexity only when complexity demands it.**

The approach is based on the patterns in [spring-boot-application-architecture-patterns](https://github.com/sivaprasadreddy/spring-boot-application-architecture-patterns).

## Architecture Patterns (Progressive)

| Pattern | Complexity | When to Use |
|---------|-----------|-------------|
| **Layered** | ⭐ Low | Simple CRUD, prototypes, MVPs |
| **Package-by-Module** | ⭐⭐ Low-Medium | 3-5 distinct features, medium apps |
| **Modular Monolith** | ⭐⭐ Medium | Need module boundaries, Spring Modulith |
| **Tomato** | ⭐⭐⭐ Medium-High | Rich domain, Value Objects, type safety |
| **DDD+Hexagonal** | ⭐⭐⭐⭐ High | Complex domains, CQRS, infra independence |

## Installation

```bash
/plugin marketplace add a-pavithraa/springboot-skills-marketplace
/plugin enable a-pavithraa/springboot-skills-marketplace
/plugin install springboot-architecture@springboot-skills-marketplace
```

## Available Skills

### creating-springboot-projects

Builds a Spring Boot project after a short assessment so the architecture matches your team, domain, and lifespan.

**You get:**
- Assessment-first guidance (no guesswork)
- Architecture-specific scaffolding
- Spring Initializr setup
- Templates for Value Objects, Rich Entities, CQRS, converters, etc.

**Assessment questions:**
1. **Domain complexity** — simple CRUD or complex business rules?
2. **Team size** — 1–3, 3–10, or 10+?
3. **Lifespan** — months, 1–2 years, or 5+ years?
4. **Type safety needs** — basic validation or strong typing (finance/healthcare)?
5. **Bounded contexts** — single domain or multiple subdomains?

### spring-data-jpa

Focused guidance for repositories, queries, and mapping patterns that scale.

**You get:**
- Query patterns and DTO projections
- Custom repositories and CQRS query services
- Relationship patterns and performance tuning
- Anti-patterns you should avoid

**Critical rules:**
1. Don’t create repositories for every entity
2. Don’t use long method-name queries for complex logic
3. Don’t call `save()` blindly (understand persist vs merge)

### springboot-migration

Guided, phased upgrades for Spring Boot 4 with Java 25, plus Spring Modulith 2 and Testcontainers 2 when needed.

**You get:**
- Mandatory scan-first workflow using a migration scanner
- Dependency/code/config phases to reduce breakage
- Dedicated references for Boot 4, Modulith 2, and Testcontainers 2
- Retry/resilience guidance aligned with the sample repo

## Usage Examples

### 1) Simple Product API

```
You: I need a REST API for products with basic CRUD.
Claude: I’ll use creating-springboot-projects.

[Asks assessment questions]

Recommendation: Layered architecture.
[Generates project and templates]
```

### 2) Order Processing Service

```
You: I need an order service with payments and inventory rules.
Claude: I’ll use creating-springboot-projects.

[Asks assessment questions]

Recommendation: Tomato architecture.
[Generates value objects, rich entities, CQRS services]
```

### 3) Slow Search Queries

```
You: My product search is slow.
Claude: I’ll use spring-data-jpa.

[Analyzes and replaces N+1 queries with DTO projections]
```

### 4) Spring Boot 4 Migration

```
You: We need to migrate a Boot 3 app to Boot 4 (Modulith + Testcontainers too).
Claude: I’ll use springboot-migration.

[Runs scan_migration_issues.py]
[Plans dependency → code → config → testing phases]
[Applies changes and verifies each phase]
```

## Templates & Assets

**Architecture templates:** `creating-springboot-projects/assets/`
- Value Objects, Rich Entities, CQRS services, converters, REST controllers
- Flyway migrations, Testcontainers setup, ProblemDetail handler

**JPA templates:** `spring-data-jpa/assets/`
- Query repositories, DTO projections, custom repos, CQRS query services
- Relationship patterns with do/don’t guidance

**Reference guides:** `spring-data-jpa/references/`
- Query patterns, projections, custom repositories
- Relationships and performance tuning

## Prerequisites

- Claude Code CLI
- Java 25
- Maven or Gradle
- Spring Boot 4.0+ familiarity

## Upgrade Path

```
Layered
  → Package-by-Module
    → Modular Monolith
      → Tomato
        → DDD+Hexagonal
```

## Credits

- Architecture patterns: [Siva Prasad Reddy](https://github.com/sivaprasadreddy)
- Spring Boot 4 features: [spring-boot-4-features](https://github.com/sivaprasadreddy/spring-boot-4-features)
- Modular monolith reference: [spring-modular-monolith](https://github.com/sivaprasadreddy/spring-modular-monolith)
- Marketplace inspiration: [sivalabs-marketplace](https://github.com/sivaprasadreddy/sivalabs-marketplace)
- JPA/Hibernate best practices: [Vlad Mihalcea](https://vladmihalcea.com/blog/)
