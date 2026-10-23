# Domain Modeling: Review Rules

Use this file to judge whether the domain model fits the domain. Full rich-entity template: `../../creating-springboot-projects/assets/rich-entity.java`. Value objects: [value-objects-patterns.md](value-objects-patterns.md).

## Anemic vs rich

| Aspect | Anemic + primitives | Rich + value objects |
|--------|---------------------|----------------------|
| Entity | Fields, getters, setters; no rules | Private state, behavior methods, factory methods |
| Business rules | In services (transaction scripts) | In entities and VOs; services orchestrate |
| Validation | Repeated in services | Once, at creation |
| Types | `String`, `Long`, `BigDecimal` | `OrderNumber`, `OrderId`, `Money` |
| Tests | Through services | Unit tests on the domain |
| Cost | Low at first, grows with rules | Higher at first |
| Fits | Simple CRUD, prototypes, admin tools | Complex rules, state transitions, money, long-lived systems |

An anemic model is acceptable for simple CRUD. Do not flag it there. Flag it when services contain state-transition rules, repeated validation, or bugs from mixed-up primitives.

## What to flag

**Primitive obsession.** Several parameters of the same primitive type that can be swapped without a compile error:

```java
void processOrder(String orderNumber, String email, String productCode)  // swappable
void processOrder(OrderNumber orderNumber, EmailAddress email, ProductCode code)  // compiler catches swaps
```

**Rules in services that belong to the entity.** Status checks followed by setters:

```java
// Flag: the service enforces the rule; any other caller can skip it
if (order.getStatus() != OrderStatus.PENDING) throw new IllegalStateException();
order.setStatus(OrderStatus.CANCELLED);

// Fix: the entity enforces it
order.cancel();   // throws if the status does not allow cancelling
```

**Public setters on a rich entity.** Replace them with intent methods (`cancel()`, `confirm()`, `adjustPrice(Money)`).

**Constructors with many parameters.** Use named factory methods (`Order.createNew(quantity, unitPrice)`) that build a valid object.

**Invalid states.** Fields that can contradict each other (`endDate` before `startDate`, `total` that does not match the items). Enforce the invariant in the entity or a VO.

## Rich entity rules (JPA)

- JPA needs a no-argument constructor. Make it `protected`, not `public`.
- Keep the setters out. Hibernate uses field access when `@Id` is on a field.
- Value objects are `@Embeddable` (records allowed on Hibernate 6.2+).
- A service method loads the aggregate, calls one behavior method, saves, and publishes events. Nothing more:

```java
@Transactional
public void cancelOrder(OrderId id) {
    Order order = repository.findById(id).orElseThrow();
    order.cancel();
    eventPublisher.publishEvent(new OrderCancelled(id));
}
```

Inside a transaction, a managed entity is saved at commit. An explicit `save()` is not needed.

## Moving from anemic to rich

Do it step by step, starting with the riskiest concepts:

1. Wrap high-risk primitives in VOs (money, quantities, IDs).
2. Move validation into the VO constructors.
3. Move state-transition rules from services into entity methods.
4. Replace setters with those methods.
5. Add factory methods.
6. Leave simple CRUD entities anemic.

Do not convert everything at once, and do not apply rich models to trivial entities.

## Sources

- [Anemic Domain Model - Martin Fowler](https://martinfowler.com/bliki/AnemicDomainModel.html)
- [Value Object - Martin Fowler](https://martinfowler.com/bliki/ValueObject.html)
- [Domain-Driven Design - Eric Evans](https://www.domainlanguage.com/ddd/)
