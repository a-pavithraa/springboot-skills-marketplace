# Spring Boot Skills Marketplace

A collection of [Claude Code](https://claude.com/claude-code) skills for creating Spring Boot applications with proper architecture patterns.

## About

This marketplace provides battle-tested skills for building Spring Boot applications using context-appropriate architecture patterns. Instead of jumping to implementation, these skills guide you through a systematic assessment process to choose the right architecture for your project's complexity.

### Architecture Philosophy

The skills in this marketplace are based on the progressive architecture patterns documented in [spring-boot-application-architecture-patterns](https://github.com/sivaprasadreddy/spring-boot-application-architecture-patterns) repository. The core philosophy is:

> **Start simple. Add complexity only when complexity demands it.**

The skills help you choose between five progressive patterns:

| Pattern | Complexity | When to Use |
|---------|-----------|-------------|
| **Layered** | ⭐ Low | Simple CRUD, prototypes, MVPs |
| **Package-by-Module** | ⭐⭐ Low-Medium | 3-5 distinct features, medium apps |
| **Modular Monolith** | ⭐⭐ Medium | Need module boundaries, Spring Modulith |
| **Tomato** | ⭐⭐⭐ Medium-High | Rich domain, Value Objects, type safety |
| **DDD+Hexagonal** | ⭐⭐⭐⭐ High | Complex domains, CQRS, infrastructure independence |

## Installation

### 1. Add the Marketplace

```bash
/plugin marketplace add a-pavithraa/springboot-skills-marketplace
```

### 2. Enable the Marketplace

```bash
/plugin enable a-pavithraa/springboot-skills-marketplace
```

### 3. Install the Plugin

```bash
/plugin install springboot-architecture@springboot-skills-marketplace
```

## Available Skills

### 🏗️ creating-springboot-projects

**Purpose**: Creates Spring Boot projects with context-appropriate architecture patterns.

**Key Features**:
- **Assessment-First Approach**: Evaluates project complexity before choosing architecture
- **5 Progressive Patterns**: From simple Layered to full DDD+Hexagonal
- **Spring Initializr Integration**: Uses Spring Initializr for project scaffolding
- **13 Ready-to-Use Templates**: Value Objects, Rich Entities, CQRS Services, Spring Converters, etc.

**Assessment Questions**:
1. **Domain Complexity** - Simple CRUD or complex business rules?
2. **Team Size** - 1-3, 3-10, or 10+?
3. **Lifespan** - Months, 1-2 years, or 5+ years?
4. **Type Safety** - Basic validation or strong typing needed (financial/healthcare)?
5. **Bounded Contexts** - Single domain or multiple subdomains?

**What You Get**:

Depending on your assessment, the skill generates:

- **Layered Architecture**: Traditional `controller/` `service/` `repository/` structure
- **Package-by-Module**: Vertical slices like `products/` `orders/` with internal layering
- **Modular Monolith**: Package-by-Module + Spring Modulith for enforced boundaries
- **Tomato Architecture**: Package-by-Module + Value Objects + Rich Entities + CQRS
- **DDD+Hexagonal**: Full Domain-Driven Design with Hexagonal Architecture

## Usage Example

### Scenario 1: Simple Product API

```
You: I need a REST API for managing products with basic CRUD operations.

Claude: I'll use the creating-springboot-projects skill to set this up.

[Asks assessment questions]

Based on your answers (simple CRUD, small team, short lifespan),
I recommend the Layered architecture.

[Creates project via Spring Initializr]
[Sets up standard layered structure with templates]
```

**Result**: Clean Spring Boot project with standard layered structure.

### Scenario 2: Order Processing Microservice

```
You: I need an order processing service with state machines,
     payment integration, and inventory checks.

Claude: I'll use the creating-springboot-projects skill to set this up.

[Asks assessment questions]

Based on your answers (complex domain, medium team, long lifespan,
type safety needed), I recommend the Tomato architecture.

[Creates project via Spring Initializr with Modulith support]

[Creates Value Objects using templates]
- OrderId (TSID-based)
- OrderStatus (enum with state machine)
- Money (type-safe currency)
- Quantity (inventory tracking)

[Creates Rich Entity]
- OrderEntity with business logic (validate, confirm, ship, etc.)

[Creates CQRS Services]
- OrderService (write operations)
- OrderQueryService (read operations)

[Creates Spring Converters]
- String to OrderId converter for path variables
```

**Result**: Production-ready service with strong type safety and rich domain modeling.

## Templates Included

All patterns come with ready-to-use templates:

| Template | Purpose | Applies To |
|----------|---------|-----------|
| `value-object.java` | Type-safe Value Objects (SKU, Email, Price) | Tomato, DDD+Hex |
| `rich-entity.java` | Entities with business behavior | Tomato, DDD+Hex |
| `base-entity.java` | JPA auditing superclass | All patterns |
| `repository.java` | Spring Data JPA with @Query examples | All patterns |
| `service-cqrs.java` | Separate write/read services | Tomato, DDD+Hex |
| `controller.java` | REST with Value Object binding | All patterns |
| `spring-converter.java` | @PathVariable binding to VOs | Tomato, DDD+Hex |
| `exception-handler.java` | ProblemDetail (RFC 7807) | All patterns |
| `modularity-test.java` | Spring Modulith boundary tests | Modulith, Tomato |
| `flyway-migration.sql` | Database schema templates | All patterns |
| `docker-compose.yml` | PostgreSQL/MySQL for local dev | All patterns |
| `testcontainers-test.java` | Integration test setup | All patterns |
| `pom-additions.xml` | TSID, Modulith, ArchUnit deps | Tomato, DDD+Hex |

## Prerequisites

- **Claude Code CLI** installed
- **Java 25** installed
- **Maven** or **Gradle** for building projects
- **Spring Boot 4.0+** knowledge (includes TestRestClient, native resiliency, AOT support)

## Architecture Decision Guide

Still not sure which architecture to choose? Here's a quick guide:

### Choose **Layered** if:
- Building a prototype or MVP
- Simple CRUD operations
- Team of 1-3 developers
- Project lifespan < 6 months
- No complex business rules

### Choose **Package-by-Module** if:
- 3-5 distinct features
- Medium-sized application
- Team of 3-10 developers
- Project lifespan 1-2 years
- Features are relatively independent

### Choose **Modular Monolith** if:
- Everything from Package-by-Module, plus:
- Need enforced module boundaries
- Want persistent event infrastructure
- Planning potential microservice extraction

### Choose **Tomato** if:
- Complex domain with business rules
- Type confusion is a risk (SKU vs String)
- Validation scattered across layers
- Financial or healthcare domain
- Team of 5-15 developers
- Project lifespan 3-5 years

### Choose **DDD+Hexagonal** if:
- Very complex domain with multiple subdomains
- Need infrastructure independence
- CQRS pattern required
- Team of 10+ developers
- Project lifespan 5+ years
- Potential for microservices migration

## Upgrade Path

These patterns are designed to be upgradeable:

```
Layered
  → Package-by-Module (when 3+ features, team grows)
    → Modular Monolith (when need enforced boundaries)
      → Tomato (when type confusion bugs, scattered validation)
        → DDD+Hexagonal (when need infrastructure independence, CQRS)
```

**Key Principle**: Start simple. Refactor when complexity demands it.

## Reference Architecture

The patterns implemented by these skills are thoroughly documented with working examples in:

**📚 [Spring Boot Application Architecture Patterns](https://github.com/sivaprasadreddy/spring-boot-application-architecture-patterns)**

This repository contains 5 complete implementations of the same event management system (Meetup4j), each following a different pattern. It's an excellent resource for understanding the tradeoffs between patterns.

## Credits

- **Architecture Patterns Reference**: [Siva Prasad Reddy](https://github.com/sivaprasadreddy)
- **Spring Boot 4 Features**: [spring-boot-4-features](https://github.com/sivaprasadreddy/spring-boot-4-features)
- **Modular Monolith Reference**: [spring-modular-monolith](https://github.com/sivaprasadreddy/spring-modular-monolith)
- **Marketplace Inspiration**: [sivalabs-marketplace](https://github.com/sivaprasadreddy/sivalabs-marketplace)


