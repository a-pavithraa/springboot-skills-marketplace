# Spring Boot Architecture Patterns Guide

## Architecture Decision Matrix

| Criteria | Layered | Package-by-Module | Modulith | Tomato | DDD+Hex |
|----------|---------|-------------------|----------|--------|---------|
| Team Size | 1-3 | 3-10 | 5-15 | 5-15 | 10+ |
| Lifespan | Months | 1-2 yrs | 2-5 yrs | 3-5 yrs | 5+ yrs |
| Type Safety | Low | Low | Low | High | High |
| Learning Curve | ⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |

## Package Structures

### Layered Architecture
```
com.example.app/
├── controller/
├── service/
├── repository/
└── domain/
```

**When to use:** Simple CRUD applications, prototypes, MVPs, single developer projects.

### Package-by-Module
```
com.example.app/
├── products/
│   ├── domain/
│   └── rest/
├── orders/
│   ├── domain/
│   └── rest/
└── shared/
```

**When to use:** 3-5 distinct features, medium-sized applications, need feature isolation.

### Modular Monolith (Spring Modulith)
```
com.example.app/
├── products/
│   ├── internal/      ← Package-private implementations
│   ├── ProductsAPI.java  ← Public module API
│   └── domain/
├── orders/
│   ├── internal/
│   ├── OrdersAPI.java
│   └── domain/
└── shared/
```

**When to use:** Need enforced module boundaries, want to test module independence, planning potential microservices extraction.

### Tomato Architecture
```
com.example.app/
├── products/
│   ├── domain/
│   │   ├── vo/
│   │   │   ├── ProductSKU.java
│   │   │   ├── Price.java
│   │   │   └── Quantity.java
│   │   ├── ProductEntity.java
│   │   ├── ProductService.java
│   │   └── ProductQueryService.java
│   └── rest/
│       ├── ProductController.java
│       └── converters/
│           └── StringToProductSKUConverter.java
└── shared/
    └── vo/
        ├── Money.java
        └── Email.java
```

**When to use:** Rich domain models, need type safety, financial/healthcare domains, experiencing validation bugs from primitive types.

### DDD+Hexagonal Architecture
```
com.example.app/
├── products/
│   ├── application/
│   │   ├── command/
│   │   │   ├── CreateProductHandler.java
│   │   │   └── UpdateProductHandler.java
│   │   └── query/
│   │       └── ProductQueryService.java
│   ├── domain/
│   │   ├── model/
│   │   │   ├── ProductAggregate.java
│   │   │   └── ProductFactory.java
│   │   ├── vo/
│   │   │   ├── ProductSKU.java
│   │   │   └── Price.java
│   │   └── ports/
│   │       └── ProductRepository.java (interface)
│   ├── infra/
│   │   └── persistence/
│   │       └── JpaProductRepository.java (impl)
│   └── interfaces/
│       └── rest/
│           └── ProductController.java
└── shared/
    └── domain/
```

**When to use:** Complex business domains, CQRS needed, infrastructure independence required, 10+ team members, 5+ year lifespan.

## Naming Conventions

### Tomato/DDD Patterns

| Type | Pattern | Example | Package |
|------|---------|---------|---------|
| Entity | `*Entity` | `ProductEntity` | `domain/model/` |
| Aggregate Root | `*Aggregate` | `OrderAggregate` | `domain/model/` |
| Value Object | Domain name | `ProductSKU`, `Price`, `Email` | `domain/vo/` |
| Command | `*Cmd` | `CreateProductCmd` | `application/command/` |
| Command Handler | `*Handler` | `CreateProductHandler` | `application/command/` |
| View Model | `*VM` | `ProductVM` | `domain/models/` or `interfaces/rest/dto/` |
| Write Service | `*Service` | `ProductService` | `domain/` |
| Read Service | `*QueryService` | `ProductQueryService` | `application/query/` |
| Repository Interface | `*Repository` | `ProductRepository` | `domain/ports/` (DDD) or `domain/` |
| Repository Impl | `Jpa*Repository` | `JpaProductRepository` | `infra/persistence/` |
| Module API | `*API` | `ProductsAPI` | Package root |
| Converter | `StringTo*Converter` | `StringToProductSKUConverter` | `rest/converters/` |

### General Conventions

- Use singular names for packages: `product/` not `products/`
- Value Objects are immutable and use `of()` factory method
- Commands are immutable records
- View Models are immutable records for API responses
- Aggregates encapsulate business logic and invariants

## Anti-Patterns to Avoid

| Don't | Do | Why |
|-------|-----|-----|
| Jump to implementation | Ask assessment questions first | Prevents over-engineering or under-engineering |
| Use DDD for simple CRUD | Use Layered or Package-by-Module | DDD adds complexity without benefit for simple cases |
| Use Layered for complex domain | Use Tomato or DDD+Hexagonal | Layered architecture leads to anemic domain models |
| Skip infrastructure | Always include Flyway, Testcontainers, Docker | Production readiness requires proper infrastructure |
| Copy templates blindly | Read template comments, adapt to domain | Templates are starting points, not solutions |
| Primitive obsession | Use Value Objects for domain concepts | Type safety prevents bugs, makes intent explicit |
| Anemic domain model | Put business logic in entities/aggregates | Domain-Driven Design principle |
| God services | Split by command/query responsibility | CQRS improves maintainability |
| Shared mutable state | Use immutable Value Objects | Thread-safety and predictability |

## Architecture Upgrade Path

### When to Upgrade

| From | To | Trigger | Effort |
|------|-----|---------|--------|
| Layered | Package-by-Module | 3+ features, team grows to 3+ | Low |
| Package-by-Module | Modular Monolith | Need enforced boundaries, testing independence | Medium |
| Modular Monolith | Tomato | Type confusion bugs, validation scattered across layers | Medium |
| Tomato | DDD+Hexagonal | Need infrastructure independence, CQRS, complex business rules | High |

### Migration Strategies

**Layered → Package-by-Module:**
1. Create module packages (products/, orders/)
2. Move related controllers, services, repos into modules
3. Extract shared utilities to shared/
4. Refactor cross-module dependencies

**Package-by-Module → Modular Monolith:**
1. Add Spring Modulith dependency
2. Create `*API.java` interfaces for each module
3. Make internal classes package-private
4. Add `@ApplicationModuleTest` for module verification
5. Use `modularity-test.java` template

**Modular Monolith → Tomato:**
1. Identify domain concepts currently using primitives
2. Create Value Objects for each concept (SKU, Price, Email, etc.)
3. Replace primitives in entities with VOs
4. Add Spring Converters for @PathVariable binding
5. Update tests to use VOs

**Tomato → DDD+Hexagonal:**
1. Separate commands from queries (CQRS)
2. Create application layer with handlers
3. Define domain ports (repository interfaces in domain/)
4. Move infrastructure implementations to infra/
5. Extract aggregates from entities
6. Add ArchUnit tests for hexagonal verification

### Signs You've Outgrown Your Architecture

**Layered:**
- Features span multiple unrelated domains
- Service classes exceed 500 lines
- Difficult to understand feature scope
- Changes affect multiple unrelated features

**Package-by-Module:**
- Modules have circular dependencies
- Difficult to test modules in isolation
- Unclear module boundaries
- Need to extract microservices

**Modular Monolith:**
- Type confusion bugs (mixing IDs, codes, values)
- Validation logic scattered everywhere
- Primitive parameters causing bugs
- Financial/healthcare domain (needs type safety)

**Tomato:**
- Complex business rules in multiple aggregates
- Need to swap infrastructure (database, message queue)
- Multiple teams working on same codebase
- Planning microservices extraction

## Best Practices

### Start Simple
- Begin with Layered or Package-by-Module
- Don't prematurely optimize for scale
- Upgrade architecture when complexity demands it
- Measure complexity by team size, lifespan, and domain complexity

### Type Safety
- Use Value Objects for domain concepts (not just primitives)
- Leverage Java records for immutability
- Enable JSpecify null-safety (@NullMarked)
- Use sealed classes for states/enums when appropriate

### Module Boundaries
- Each module should have clear responsibility
- Minimize dependencies between modules
- Use events for cross-module communication
- Test modules independently

### Infrastructure
- Always use migrations (Flyway/Liquibase)
- Always use Testcontainers for integration tests
- Always use Docker Compose for local development
- Always use ProblemDetail for REST error responses
