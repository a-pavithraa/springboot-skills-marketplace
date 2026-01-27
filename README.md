# Spring Boot Skills Marketplace

Claude Code skills that help you build Spring Boot apps with architecture that actually fits your needs.

## Why This Exists

Projects that start simple tend to grow messy. These skills help you pick the right architecture for where you are now—with a clear path forward when things get complex.

> **Start simple. Add complexity only when complexity demands it.**

Built on patterns from [spring-boot-application-architecture-patterns](https://github.com/sivaprasadreddy/spring-boot-application-architecture-patterns).

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

Asks a few questions about your project, then builds the right architecture from the start.

What you get: assessment-driven scaffolding, Spring Initializr setup, and templates for Value Objects, Rich Entities, CQRS patterns, converters—whatever your chosen architecture needs.

**Quick assessment covers:**
- Domain complexity (CRUD vs. business rules)
- Team size and project lifespan
- Type safety requirements
- Bounded contexts

### spring-data-jpa

Helps you write JPA code that doesn't slow down six months later.

Covers query patterns, DTO projections, custom repositories, CQRS query services, and the performance anti-patterns that bite everyone eventually (repositories for every entity, method-name query hell, blind `save()` calls).

### springboot-migration

Step-by-step migration to Spring Boot 4 + Java 25 (with Spring Modulith 2 and Testcontainers 2 support).

Scans your project first, then walks through dependencies → code → config in phases. Includes retry/resilience patterns and references for each upgrade target.

### code-reviewer

Sanity-checks your Boot 4 / Java 25 project for architecture fit and performance gotchas.

Covers all five architecture patterns (when to use, when to avoid), plus checklists for events, CQRS, Modulith boundaries. Catches N+1 queries, missing caches, virtual thread pinning, and other performance traps.

Use this when you want a second opinion or need to decide if it's time to evolve your architecture.

## Usage Examples

**"I need a REST API for products with basic CRUD."**
→ Asks about your domain, team, and timeline. Suggests Layered architecture. Generates scaffolding.

**"I need an order service with payments and inventory rules."**
→ Assesses complexity. Recommends Tomato architecture. Generates value objects, rich entities, CQRS services.

**"My product search is slow."**
→ Analyzes your queries, spots N+1 issues, refactors to DTO projections.

**"We need to migrate from Boot 3 to Boot 4."**
→ Runs migration scanner, plans phased upgrade (dependencies → code → config), applies and verifies each step.

**"Can you review our Boot 4 service for issues?"**
→ Checks architecture pattern fit, hunts for performance problems (N+1, missing caches, virtual thread pinning, entity leaks).

## Templates & Assets

**Architecture templates** (`creating-springboot-projects/assets/`)
Value Objects, Rich Entities, CQRS services, converters, REST controllers, Flyway migrations, Testcontainers, ProblemDetail handlers.

**JPA templates** (`spring-data-jpa/assets/`)
Query repositories, DTO projections, custom repos, CQRS query services, relationship patterns.

**Reviewer references** (`java25-springboot4-reviewer/references/`)
Architecture patterns, decision matrices, performance checklists.

**Reference guides** (`spring-data-jpa/references/`)
Query patterns, projections, custom repositories, relationship handling, performance tuning.

## Prerequisites

- Claude Code CLI
- Java 25
- Maven or Gradle
- Spring Boot 4.0+ familiarity

## Evolution Path

Start simple, evolve as needed:

```text
Layered → Package-by-Module → Modular Monolith → Tomato → DDD+Hexagonal
```

## Credits

- Architecture patterns: [Siva Prasad Reddy](https://github.com/sivaprasadreddy)
- Spring Boot 4 features: [spring-boot-4-features](https://github.com/sivaprasadreddy/spring-boot-4-features)
- Modular monolith reference: [spring-modular-monolith](https://github.com/sivaprasadreddy/spring-modular-monolith)
- Marketplace inspiration: [sivalabs-marketplace](https://github.com/sivaprasadreddy/sivalabs-marketplace)
- JPA/Hibernate best practices: [Vlad Mihalcea](https://vladmihalcea.com/blog/)
