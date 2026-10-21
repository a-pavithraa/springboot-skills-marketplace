# Architecture Patterns: Review Rules

Use this file to identify the architecture in use and check the code against it. For package layouts, naming, the decision matrix, and upgrade steps, read `../../creating-springboot-projects/references/architecture-guide.md`. For code examples, read [domain-modeling.md](domain-modeling.md) and [value-objects-patterns.md](value-objects-patterns.md).

Review against the architecture the team chose. Do not push a more complex pattern unless the "signs to evolve" below are present.

## Contents

1. [Identify the pattern](#identify-the-pattern)
2. [Per-pattern checks](#per-pattern-checks)
3. [Aggregates](#aggregates)
4. [Events and Spring Modulith](#events-and-spring-modulith)
5. [CQRS](#cqrs)
6. [Signs to evolve](#signs-to-evolve)

---

## Identify the pattern

| Pattern | Markers in the code | Domain model | Boundary enforcement |
|---------|---------------------|--------------|----------------------|
| Layered | Top-level `controller/`, `service/`, `repository/`, `domain/` | Anemic JPA entities, logic in services | None |
| Package-by-module | Top-level feature packages (`orders/`, `catalog/`), layers inside | Anemic | None |
| Modular monolith | Feature packages + Spring Modulith, `ModularityTests`, `internal/` packages, `*API` types | Anemic | `ApplicationModules.verify()` |
| Tomato | Modular monolith + value objects (`@Embeddable` records), rich entities, `StringTo*Converter` | Rich; VOs embedded in JPA entities | Modulith |
| DDD + Hexagonal | Per module `application/`, `domain/`, `infra/` (or `adapter/`), `interfaces/`; ports as interfaces; `*Handler`, `*QueryService` | Rich; domain separate from persistence | ArchUnit |

Hexagonal code appears in two common layouts: per module (`application/domain/infra/interfaces`, as in the architecture guide) or ports-and-adapters (`domain/port/in`, `domain/port/out`, `adapter/in`, `adapter/out`). Accept both. Check the dependency direction, not the folder names.

---

## Per-pattern checks

### Layered

- [ ] Controllers call services only. Flag controller-to-repository calls.
- [ ] Business rules are in services, not controllers.
- [ ] Entities are not returned from controllers. Use DTOs or records.

### Package-by-module

- [ ] Code is grouped by feature, not by technical layer.
- [ ] `shared/` is small and generic (IDs, time, errors). Flag business logic in it.
- [ ] Cross-module calls go through a service or an event, not another module's repository.

### Modular monolith

- [ ] A test calls `ApplicationModules.of(App.class).verify()` and passes.
- [ ] Other modules use only the module's public API (base package or `*API` type). Flag imports of another module's `internal` package.
- [ ] Cross-module side effects use events (`@ApplicationModuleListener`), not direct calls into other modules' services.
- [ ] If events must survive a crash: an event registry starter and the `event_publication` table exist (see below).

Note: package-private is per Java package, not per Modulith module. A package-private class in `order.internal` is not visible from `order` either. `verify()` enforces the module-level rules at test time.

### Tomato

- [ ] Core concepts use value objects (`OrderNumber`, `Money`, `Quantity`), not `String`/`BigDecimal`.
- [ ] Validation is in VO constructors (fail fast). Flag the same checks repeated in services.
- [ ] VOs used as JPA fields are `@Embeddable`, including records.
- [ ] Spring converters bind request values to VOs.
- [ ] Entities have behavior methods and no public setters. Services orchestrate only.

### DDD + Hexagonal

- [ ] The domain model has no Spring or JPA annotations. Application services and handlers may use `@Service` and `@Transactional`.
- [ ] Ports are interfaces owned by the domain or application layer. Adapters implement them.
- [ ] Dependencies point inward: `interfaces` and `infra` depend on `application`/`domain`, never the reverse.
- [ ] Persistence entities are mapped to domain objects in the adapter. Domain objects do not leak JPA types.
- [ ] Commands and queries are separate (`*Handler` vs `*QueryService`).
- [ ] ArchUnit tests enforce the layer rules.
- [ ] The domain logic can be tested without a Spring context.

---

## Aggregates

- External code references only the aggregate root.
- Changes to child entities go through the root, so invariants (for example, order totals) stay correct.
- Repositories exist only for aggregate roots.

Flag this:

```java
// Bypasses the Order root; the order total is not recalculated
OrderItem item = orderItemRepository.findById(itemId).orElseThrow();
item.setQuantity(quantity);
```

Fix: `order.updateItemQuantity(itemId, quantity)` on the loaded `Order`.

---

## Events and Spring Modulith

| Mechanism | Runs when | Transaction | Survives a crash |
|-----------|-----------|-------------|------------------|
| `@EventListener` | Immediately, inside the publisher's transaction | Publisher's | No |
| `@TransactionalEventListener(phase = AFTER_COMMIT)` | After the publisher commits | Writes need `@Transactional(propagation = REQUIRES_NEW)` | No |
| `@ApplicationModuleListener` | Asynchronously, after the publisher commits | New (`REQUIRES_NEW`) | Only with an event publication registry |

`@ApplicationModuleListener` is always `@Async` + `@Transactional(propagation = REQUIRES_NEW)` + `@TransactionalEventListener`. The Event Publication Registry adds persistence and replay. It needs one of `spring-modulith-starter-jdbc`, `-jpa`, `-mongodb`, or `-neo4j`, plus the backing storage (for JDBC/JPA, the `event_publication` table, created by Flyway or Liquibase). Without it, an event is lost if the app stops between the commit and the end of the listener. Source: [Spring Modulith events](https://docs.spring.io/spring-modulith/reference/events.html).

Check:

- [ ] Events are published inside the transaction that changes the state.
- [ ] Listeners that write data are idempotent. With the registry, events can be delivered again.
- [ ] Events are records with IDs and facts, not JPA entities.
- [ ] Event types have a versioning plan if they are stored or sent outside the app.

---

## CQRS

Recommend CQRS only when read and write needs differ (reporting, denormalized views, very different load). For simple CRUD it adds cost with no benefit.

- [ ] Command side loads aggregates and enforces invariants.
- [ ] Query side returns DTO projections and uses `@Transactional(readOnly = true)`. It does not load aggregates to build views.
- [ ] If the read model is a separate store, event handlers keep it in sync and the team accepts eventual consistency.


---

## Signs to evolve

| Current | Sign | Next |
|---------|------|------|
| Layered | Related code is hard to find; teams change the same files | Package-by-module |
| Package-by-module | Accidental cross-module dependencies; lost events | Modular monolith |
| Modular monolith | Validation repeated everywhere; bugs from mixed-up primitives | Tomato |
| Tomato | Need to swap infrastructure, CQRS, or separate read/write models | DDD + Hexagonal |

## Official documentation

- [Structuring Your Code - Spring Boot](https://docs.spring.io/spring-boot/reference/using/structuring-your-code.html)
- [Spring Modulith Reference](https://docs.spring.io/spring-modulith/reference/)
- [Hexagonal Architecture - Alistair Cockburn](https://alistair.cockburn.us/hexagonal-architecture/)
- [CQRS - Martin Fowler](https://martinfowler.com/bliki/CQRS.html), [Anemic Domain Model - Martin Fowler](https://martinfowler.com/bliki/AnemicDomainModel.html)
