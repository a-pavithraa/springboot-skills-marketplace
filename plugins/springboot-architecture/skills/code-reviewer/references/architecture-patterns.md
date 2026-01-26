# Architecture Patterns

## Table of Contents

1. [Architecture Patterns Overview](#architecture-patterns-overview)
2. [Detailed Comparison Table](#detailed-comparison-table)
3. [Progressive Evolution Path](#progressive-evolution-path)
4. [Layered Architecture](#layered-architecture)
5. [Package-By-Module Architecture](#package-by-module-architecture)
6. [Simple Modular Monolith](#simple-modular-monolith)
7. [Tomato Architecture](#tomato-architecture)
8. [Domain-Driven Design (DDD)](#domain-driven-design)
9. [Hexagonal Architecture](#hexagonal-architecture)
10. [Spring Modulith](#spring-modulith)
11. [CQRS](#cqrs)
12. [Event-Driven Architecture](#event-driven-architecture)
13. [Decision Guide](#decision-guide)

---

## Architecture Patterns Overview

This guide demonstrates five architectural approaches, progressively increasing in sophistication:

1. **Layered Architecture** - Traditional package-by-layer approach (controller, service, repository)
2. **Package-By-Module Architecture** - Organized by business features/modules
3. **Simple Modular Monolith** - Module boundaries enforced with Spring Modulith
4. **Tomato Architecture** - Rich domain types with Value Objects
5. **DDD + Hexagonal Architecture** - Full domain-driven design with ports & adapters

**Guiding Principle:** Start with the simplest architecture that meets your needs, and evolve as complexity demands it. It's easier to fix an under-engineered system than an over-engineered one.

**Related Guides:**
- See [domain-modeling.md](domain-modeling.md) for Anemic vs Rich domain models
- See [value-objects-patterns.md](value-objects-patterns.md) for Value Object patterns

---

## Detailed Comparison Table

| Aspect | Layered | Package-By-Module | Simple Modulith | Tomato | DDD + Hexagonal |
|--------|---------|-------------------|----------------|---------|-----------------|
| **Code Organization** | By layer (controller, service, repository, domain) | By feature/module (orders, catalog, users) | By module | By module | By module with layers inside |
| **Domain Model Type** | **Anemic** (getters/setters only) | **Anemic** | **Anemic** | **Rich** (with behavior) | **Rich** (with behavior) |
| **Data Types** | Primitives (`String`, `Integer`, `BigDecimal`) | Primitives | Primitives | **Value Objects** (`OrderCode`, `Money`, `Quantity`) | **Value Objects** |
| **Domain/Persistence Separation** | ❌ JPA entities = Domain models | ❌ JPA entities = Domain models | ❌ JPA entities = Domain models | ❌ JPA entities (with embedded VOs) | ✅ Separate domain & persistence models |
| **Business Logic Pattern** | Transaction Script (in Services) | Transaction Script | Transaction Script | Behavior in entities + Services | Rich domain models + Use Cases |
| **Cross-Module Communication** | Spring Events (`@EventListener`) | Spring Events | **Spring Modulith Persistent Events** | Spring Modulith Persistent Events | Spring Events |
| **Module Boundary Enforcement** | ❌ None | ❌ None | ✅ `modules.verify()` | ✅ Spring Modulith | ✅ ArchUnit for Hexagonal |
| **CQRS Support** | ❌ No | ❌ No | ❌ No | ❌ No | ✅ Separate Command & Query |
| **Validation** | In services (defensive coding everywhere) | In services | In services | **In Value Object constructors** (fail-fast) | In Value Object constructors |
| **Testing Strategy** | Integration tests | Integration tests | Integration tests + **Modularity tests** | Integration tests + Modularity tests | Integration tests + **ArchUnit tests** |
| **Complexity** | ⭐ Low | ⭐⭐ Low-Medium | ⭐⭐ Medium | ⭐⭐⭐ Medium-High | ⭐⭐⭐⭐ High |
| **Learning Curve** | Easy | Easy | Moderate | Moderate | Steep |
| **Maintenance Effort** | Low (for simple apps) | Medium | Medium | Medium-High | High |
| **Best For** | Simple microservices, CRUD apps | Simple-to-medium apps with features | Apps needing module boundaries | Apps needing type safety & rich domain | Complex apps with subdomains |
| **Team Size** | 1-3 | 3-10 | 5-15 | 5-15 | 10+ |
| **Expected Lifespan** | Months | 1-2 years | 2-5 years | 3-5 years | 5+ years |

---

## Progressive Evolution Path

The most successful approach is to start simple and evolve:

```
Layered Architecture
    ↓ (reorganize by feature - Easy)
Package-By-Module
    ↓ (add Spring Modulith - Moderate)
Simple Modular Monolith
    ↓ (add Value Objects, rich entities - Moderate-Hard)
Tomato Architecture
    ↓ (separate domain/infra, add CQRS - Hard)
DDD + Hexagonal Architecture
```

### Level 1: Layered → Package-By-Module

**Key Improvements:**
- ✅ Better modularity by feature
- ✅ Easier to find related code
- ✅ Better team alignment

**Migration:** Reorganize from `domain/entities/Order.java` to `orders/domain/Order.java`

### Level 2: Package-By-Module → Simple Modular Monolith

**Key Improvements:**
- ✅ Automated module boundary verification
- ✅ Persistent events for reliable communication
- ✅ Event replay capabilities

**New Additions:** `@ApplicationModuleListener`, `ModularityTest.java`

### Level 3: Simple Modular Monolith → Tomato Architecture

**Key Improvements:**
- ✅ Type safety with Value Objects
- ✅ Fail-fast validation
- ✅ Rich domain behavior
- ✅ Less defensive coding

**See:** [value-objects-patterns.md](value-objects-patterns.md) for VO examples

### Level 4: Tomato Architecture → DDD + Hexagonal Architecture

**Key Improvements:**
- ✅ Complete domain/infrastructure separation
- ✅ CQRS-ready architecture
- ✅ Ports & Adapters pattern
- ✅ ArchUnit tests for compliance

---

## Layered Architecture

The simplest pattern and a good starting point for small CRUD-style services.

### Structure

```
com.example.app
├── controller/           # REST endpoints
├── service/              # Transaction scripts / orchestration
├── repository/           # Data access
└── domain/
    ├── entities/         # JPA entities (typically anemic)
    ├── models/           # DTOs / view models
    ├── exceptions/
    └── events/
```

### When to Use
- Small teams (1–3 devs), short-lived apps, or simple microservices
- Domain complexity is low; rich domain model not needed yet
- Rapid prototyping or proof-of-concept
- Simple CRUD operations with minimal business logic

### Avoid When
- Application will grow complex over time
- Multiple teams working on different features
- Domain logic is significant and evolving

### Example

✅ **Proper layering**
```java
@RestController
@RequestMapping("/users")
public class UserController {
    private final UserService userService;  // Controller → Service

    @GetMapping("/{id}")
    public UserDTO getUser(@PathVariable Long id) {
        return userService.findById(id);
    }
}

@Service
public class UserService {
    private final UserRepository userRepository;  // Service → Repository

    public UserDTO findById(Long id) {
        User user = userRepository.findById(id)
            .orElseThrow(() -> new UserNotFoundException(id));
        return UserMapper.toDTO(user);
    }
}
```

❌ **Layer violations**
```java
@RestController
public class OrderController {
    private final OrderRepository orderRepository;  // Controller → Repository (BAD!)

    @GetMapping("/orders/{id}")
    public Order getOrder(@PathVariable Long id) {
        return orderRepository.findById(id).orElseThrow();  // No business logic!
    }
}
```

### Common Pitfalls

**See:** [domain-modeling.md](domain-modeling.md) for detailed explanations of:
- Anemic domain models (entities are just data bags)
- Primitive obsession (using `String`, `int` for domain concepts)
- Invalid states (no invariants enforced)
- Cross-layer leakage (controllers bypassing services)

**Review Checklist:**
- [ ] Controllers → Services only; no direct repository access
- [ ] Services own business rules; controllers only orchestrate I/O
- [ ] Entities never returned in API; DTOs/view models used
- [ ] Validate invariants somewhere (service or emerging value objects)

---

## Package-By-Module Architecture

Feature-first structure; same layers as Layered Architecture, but grouped per business module/feature.

### Structure
```
com.example.app
├── config/
├── orders/                    # Order module
│   ├── domain/
│   │   ├── Order.java
│   │   ├── OrderService.java
│   │   ├── OrderRepository.java
│   │   ├── events/
│   │   └── models/
│   └── rest/
│       └── OrderController.java
├── catalog/                   # Catalog module
│   ├── domain/
│   └── rest/
├── payments/                  # Payment module
└── shared/                    # Cross-cutting only (logging, time, ids)
```

### Choose When
- 3–10 person teams with clear feature ownership
- Medium complexity; want easier navigation
- Need clearer bounded contexts than layered
- May extract to microservices later

### Avoid When
- App is tiny (layered is simpler)
- Need hard module boundaries (go Modulith)

**Review Checklist:**
- [ ] Code grouped by feature/module, not technical layer
- [ ] Shared package is minimal and generic; no business logic
- [ ] Cross-module calls go through services or events
- [ ] Controllers stay inside their module

---

## Simple Modular Monolith

Package-by-module architecture plus Spring Modulith boundary enforcement and persistent events.

### What's Added
- `ApplicationModules.of(App.class).verify()` tests to prevent forbidden dependencies
- `@ApplicationModuleListener` for transactional, persistent cross-module events (replayable, retried)
- Module metadata for visualization (optional)

### Choose When
- Need reliable module isolation but still a monolith
- Require durable cross-module messaging without a broker
- Want an easy migration path toward microservices later

### Avoid When
- Overhead isn't justified (very small apps)
- Need full domain/persistence separation (go Tomato or DDD/Hex)

### Example: Module Events

```java
// Publishing events
@Service
public class OrderService {
    private final ApplicationEventPublisher eventPublisher;

    public Order createOrder(CreateOrderRequest request) {
        Order order = orderRepository.save(new Order(request));
        eventPublisher.publishEvent(new OrderCreatedEvent(order.getId()));
        return order;
    }
}

// Listening to events (in different module)
@Service
public class PaymentService {
    @ApplicationModuleListener  // Spring Modulith annotation
    public void onOrderCreated(OrderCreatedEvent event) {
        processPayment(event.orderId());
    }
}
```

### Module Verification Test

```java
@SpringBootTest
class ModulithTest {
    @Test
    void verifyModules() {
        ApplicationModules.of(Application.class)
            .verify();  // Fails if module boundaries violated
    }
}
```

**Review Checklist:**
- [ ] Modules.verify() exists and passes in tests
- [ ] Cross-module communication uses `@ApplicationModuleListener` events
- [ ] Internal types kept package-private or under `internal/`
- [ ] Event publication is transactional

---

## Tomato Architecture

Value-object-heavy, richer domain within a modular monolith. JPA entities embed VOs; behavior moves into aggregates.

### Characteristics
- **Value Objects** for domain concepts; validation in constructors (fail fast)
- **Spring converters** to map request strings → VOs automatically
- **Richer entity behavior** instead of pure transaction scripts
- **Type safety** - impossible to confuse `OrderNumber` with `String`

**See:** [value-objects-patterns.md](value-objects-patterns.md) for detailed VO patterns and examples

### Simple Example

```java
// Value Object
public record OrderNumber(@JsonValue String value) {
    public OrderNumber {
        if (value == null || value.trim().isEmpty()) {
            throw new IllegalArgumentException("Order number cannot be empty");
        }
    }

    public static OrderNumber generate() {
        return new OrderNumber(UUID.randomUUID().toString());
    }
}

// Rich Entity
@Entity
public class Order {
    @Embedded
    private OrderNumber orderNumber;  // ✅ Value Object, not String

    @Embedded
    private Money total;  // ✅ Value Object, not BigDecimal

    @Enumerated(EnumType.STRING)
    private OrderStatus status;

    // ✅ Factory method
    public static Order createNew(Money total) {
        return new Order(OrderNumber.generate(), total, OrderStatus.PENDING);
    }

    // ✅ Business behavior
    public void cancel() {
        if (status != OrderStatus.PENDING) {
            throw new IllegalStateException("Cannot cancel " + status + " orders");
        }
        this.status = OrderStatus.CANCELLED;
    }

    // ✅ No setters, only getters
    public OrderNumber getOrderNumber() { return orderNumber; }
}
```

### Choose When
- Domain is medium complexity; type safety matters
- Team is comfortable with VO/rich model patterns
- Want to reduce defensive coding in services
- Financial, healthcare, or domains where type safety is critical

### Avoid When
- Domain is trivial (stay layered/package-by-module)
- Team unfamiliar with DDD concepts
- Need infrastructure-independence (go DDD + Hex)

**Review Checklist:**
- [ ] Core concepts use VOs (OrderNumber, Money, Quantity)
- [ ] Validation enforced at creation; primitives not leaking
- [ ] Spring converters registered for external → VO mapping
- [ ] Business rules live on aggregates; services orchestrate only

---

## Domain-Driven Design

**Choose When:** Complex/long-lived domains, multiple subdomains, evolving business rules.
**Avoid When:** Simple CRUD services, tiny teams, delivery speed matters more than modeling depth.

### Bounded Contexts

Organize code by business domain, not technical layer.

```
com.example.ecommerce
├── order/
│   ├── domain/
│   │   ├── Order.java
│   │   ├── OrderItem.java
│   │   └── OrderStatus.java
│   ├── application/
│   │   └── OrderService.java
│   ├── infrastructure/
│   │   └── OrderRepository.java
│   └── api/
│       └── OrderController.java
├── catalog/
└── payment/
```

### Entities vs Value Objects

✅ **Entity (has identity)**
```java
@Entity
public class User {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;  // Identity matters

    private String username;

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof User user)) return false;
        return Objects.equals(id, user.id);  // Compare by ID
    }
}
```

✅ **Value Object (no identity, immutable)**
```java
@Embeddable
public record Address(
    String street,
    String city,
    String state,
    String zipCode
) {
    // No ID - compared by value
    // Immutable - no setters
}
```

**See:** [value-objects-patterns.md](value-objects-patterns.md) for more VO patterns

### Aggregates

**Aggregate:** A cluster of entities and value objects with a root entity.

✅ **Aggregate example**
```java
@Entity
public class Order {  // Aggregate Root
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToMany(mappedBy = "order", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<OrderItem> items = new ArrayList<>();  // Part of aggregate

    @Embedded
    private Money total;

    // Business logic in aggregate root
    public void addItem(Product product, int quantity) {
        OrderItem item = new OrderItem(this, product, quantity);
        items.add(item);
        recalculateTotal();
    }

    public void removeItem(Long itemId) {
        items.removeIf(item -> item.getId().equals(itemId));
        recalculateTotal();
    }

    private void recalculateTotal() {
        this.total = items.stream()
            .map(OrderItem::getSubtotal)
            .reduce(Money.ZERO, Money::add);
    }
}
```

**Rules:**
- External objects can only reference the aggregate root (Order)
- Changes to aggregate parts (OrderItem) go through the root
- All parts saved/deleted together (cascade)

❌ **Violating aggregate boundary**
```java
@Service
public class OrderItemService {
    public void updateQuantity(Long itemId, int quantity) {
        OrderItem item = orderItemRepository.findById(itemId).orElseThrow();
        item.setQuantity(quantity);  // Bypasses Order aggregate root!
        orderItemRepository.save(item);  // Total not recalculated!
    }
}
```

✅ **Through aggregate root**
```java
@Service
public class OrderService {
    public void updateItemQuantity(Long orderId, Long itemId, int quantity) {
        Order order = orderRepository.findById(orderId).orElseThrow();
        order.updateItemQuantity(itemId, quantity);  // Through root
        orderRepository.save(order);  // Total recalculated
    }
}
```

**Review Checklist:**
- [ ] Code organized by domain (order, catalog, payment) not layer
- [ ] Entities have identity, value objects don't
- [ ] Aggregates enforce invariants
- [ ] Changes to aggregate parts go through root

---

## Hexagonal Architecture

**Choose When:** Need technology independence, port swapping (databases, gateways), strong testability.
**Avoid When:** Domain is simple and adapter indirection adds needless ceremony.

Also known as "Ports and Adapters".

### Structure

```
com.example.app
├── domain/             # Core business logic (no dependencies)
│   ├── model/
│   │   ├── User.java
│   │   └── Order.java
│   ├── port/           # Interfaces (ports)
│   │   ├── in/         # Use cases (incoming)
│   │   │   └── CreateOrderUseCase.java
│   │   └── out/        # External dependencies (outgoing)
│   │       ├── OrderRepository.java
│   │       └── PaymentGateway.java
│   └── service/        # Domain services
│       └── OrderService.java
├── adapter/
│   ├── in/             # Input adapters
│   │   ├── rest/
│   │   │   └── OrderController.java
│   │   └── messaging/
│   │       └── OrderEventListener.java
│   └── out/            # Output adapters
│       ├── persistence/
│       │   └── OrderJpaAdapter.java
│       └── payment/
│           └── StripePaymentAdapter.java
└── config/             # Wiring
    └── ApplicationConfig.java
```

### Example

✅ **Port (interface in domain)**
```java
// domain/port/in/CreateOrderUseCase.java
public interface CreateOrderUseCase {
    Order createOrder(CreateOrderCommand command);
}

// domain/port/out/OrderRepository.java
public interface OrderRepository {
    Order save(Order order);
    Optional<Order> findById(Long id);
}
```

✅ **Domain service implements use case**
```java
// domain/service/OrderService.java
@Service
public class OrderService implements CreateOrderUseCase {
    private final OrderRepository orderRepository;       // Out port
    private final PaymentGateway paymentGateway;         // Out port

    @Override
    public Order createOrder(CreateOrderCommand command) {
        Order order = new Order(command);
        PaymentResult result = paymentGateway.processPayment(order.getPayment());
        if (!result.isSuccess()) {
            throw new PaymentFailedException();
        }
        return orderRepository.save(order);
    }
}
```

✅ **Output adapter (persistence)**
```java
// adapter/out/persistence/OrderJpaAdapter.java
@Component
public class OrderJpaAdapter implements OrderRepository {  // Implements out port
    private final OrderJpaRepository jpaRepository;

    @Override
    public Order save(Order order) {
        OrderEntity entity = toEntity(order);
        OrderEntity saved = jpaRepository.save(entity);
        return toDomain(saved);
    }

    @Override
    public Optional<Order> findById(Long id) {
        return jpaRepository.findById(id).map(this::toDomain);
    }
}
```

**Benefits:**
- Domain logic independent of frameworks
- Easy to test (mock ports)
- Easy to swap implementations (e.g., Stripe → PayPal)

**Review Checklist:**
- [ ] Domain has no Spring/JPA annotations
- [ ] All external dependencies behind ports (interfaces)
- [ ] Adapters implement ports
- [ ] Domain logic testable without Spring context

---

## Spring Modulith

**Choose When:** Want module boundary enforcement and durable intra-monolith events.
**Avoid When:** Boundaries aren't important or need full domain/infra separation.

Spring Modulith enforces module boundaries at runtime.

### Module Structure

```
com.example.app
├── order/                  # Module
│   ├── Order.java
│   ├── OrderService.java
│   ├── OrderRepository.java
│   ├── OrderController.java
│   └── internal/           # Internal (not accessible from other modules)
│       └── OrderValidator.java
├── catalog/                # Module
└── payment/                # Module
```

### Module Dependencies

✅ **Public API**
```java
// order/Order.java
package com.example.app.order;

@Entity
public class Order {  // Public - accessible from other modules
    @Id
    private Long id;
}

// order/OrderService.java
@Service
public class OrderService {  // Public
    public Order createOrder(CreateOrderRequest request) { ... }
}
```

✅ **Internal implementation**
```java
// order/internal/OrderValidator.java
package com.example.app.order.internal;

@Component
class OrderValidator {  // Package-private - only accessible within 'order' module
    boolean isValid(Order order) { ... }
}
```

❌ **Violating module boundary**
```java
// payment/PaymentService.java
import com.example.app.order.internal.OrderValidator;  // Compile error!

@Service
public class PaymentService {
    private final OrderValidator validator;  // Cannot access internal!
}
```

**Review Checklist:**
- [ ] Modules organized by business domain
- [ ] Internal classes in `internal` package or package-private
- [ ] Cross-module communication via events
- [ ] Module boundaries verified in tests

---

## CQRS

**Choose When:** Read/write workloads differ, need denormalized read models, eventual consistency acceptable.
**Avoid When:** Simple CRUD or dual models add needless complexity.

Command Query Responsibility Segregation.

### Basic Pattern

✅ **Separate read and write models**
```java
// Write model (commands)
@Service
public class OrderCommandService {
    private final OrderRepository orderRepository;
    private final ApplicationEventPublisher eventPublisher;

    public Order createOrder(CreateOrderCommand command) {
        Order order = new Order(command);
        Order saved = orderRepository.save(order);
        eventPublisher.publishEvent(new OrderCreatedEvent(saved.getId()));
        return saved;
    }
}

// Read model (queries)
@Service
public class OrderQueryService {
    private final OrderReadRepository orderReadRepository;

    public OrderDTO findById(Long id) {
        return orderReadRepository.findDTOById(id)
            .orElseThrow(() -> new OrderNotFoundException(id));
    }

    public Page<OrderSummaryDTO> findAll(Pageable pageable) {
        return orderReadRepository.findAllSummaries(pageable);
    }
}
```

**Review Checklist:**
- [ ] Commands and queries separated
- [ ] Write model normalized (enforces invariants)
- [ ] Read model denormalized (optimized for queries)
- [ ] Event handlers keep read model in sync

---

## Event-Driven Architecture

**Choose When:** Need loose coupling, asynchronous workflows, multiple consumers of business facts.
**Avoid When:** Work is strictly request/response and consistency must be immediate.

### Domain Events

✅ **Define events**
```java
public record OrderCreatedEvent(
    Long orderId,
    Long customerId,
    BigDecimal total,
    LocalDateTime createdAt
) {}
```

✅ **Publish events**
```java
@Service
public class OrderService {
    private final ApplicationEventPublisher eventPublisher;

    public Order createOrder(CreateOrderRequest request) {
        Order order = orderRepository.save(new Order(request));
        eventPublisher.publishEvent(new OrderCreatedEvent(
            order.getId(),
            order.getCustomerId(),
            order.getTotal(),
            order.getCreatedAt()
        ));
        return order;
    }
}
```

✅ **Listen to events**
```java
@Service
public class InventoryService {
    @EventListener
    public void onOrderCreated(OrderCreatedEvent event) {
        reserveItems(event.orderId());
    }
}

@Service
public class NotificationService {
    @Async
    @EventListener
    public void onOrderCreated(OrderCreatedEvent event) {
        sendOrderConfirmation(event.customerId(), event.orderId());
    }
}
```

### Transactional Events

✅ **Publish after transaction commits**
```java
@Service
public class OrderService {
    @Transactional
    public Order createOrder(CreateOrderRequest request) {
        Order order = orderRepository.save(new Order(request));
        // Event only published if transaction commits
        eventPublisher.publishEvent(new OrderCreatedEvent(order.getId()));
        return order;
    }
}

@Service
public class InventoryService {
    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void onOrderCreated(OrderCreatedEvent event) {
        // Only called after order transaction commits
        reserveItems(event.orderId());
    }
}
```

**Review Checklist:**
- [ ] Domain events used for cross-module communication
- [ ] Events published after transaction commits
- [ ] Event handlers idempotent (can be called multiple times safely)
- [ ] Event versioning strategy in place

---

## Decision Guide

### Quick Decision Matrix

| Pattern | Domain Complexity | Team Size | Type Safety | Module Boundaries | Best For |
|---------|-------------------|-----------|-------------|-------------------|----------|
| Layered | Low | 1–3 | Low | None | Small CRUD services, prototypes |
| Package-By-Module | Low–Medium | 3–10 | Low | Soft | Feature-owned teams, clearer navigation |
| Simple Modular Monolith | Low–Medium | 5–15 | Low | Hard | Monoliths needing enforced boundaries & durable events |
| Tomato | Medium | 5–15 | High | Hard | Type-safe domains with richer entities |
| DDD + Hexagonal | High | 10+ | High | Hard | Complex, long-lived domains, infra swap/CQRS ready |

### When to Choose Each Pattern

#### 🎯 Layered Architecture

**Choose When:** Simple CRUD, small microservices, prototyping, minimal domain logic, team 1-3 people, lifespan months

**Example Use Cases:** Admin dashboards, simple REST APIs, internal tools, MVPs

---

#### 🎯 Package-By-Module Architecture

**Choose When:** Medium apps, 3-5 bounded contexts, feature ownership, team 3-10 people, may extract to microservices later

**Example Use Cases:** E-commerce (catalog, orders, users), social platforms (posts, users, messaging), CMS

---

#### 🎯 Simple Modular Monolith

**Choose When:** Need guaranteed module boundaries, durable cross-module events, event replay, team 5-15 people

**Example Use Cases:** Multi-tenant SaaS, enterprise apps with subdomains, systems needing audit trails, microservices migration candidates

---

#### 🎯 Tomato Architecture

**Choose When:** Moderate domain complexity, type safety important, want rich domain without full DDD, team 5-15 people, lifespan 3-5 years

**Example Use Cases:** Financial apps, healthcare systems, booking systems, inventory management, order processing

---

#### 🎯 DDD + Hexagonal Architecture

**Choose When:** Complex business domains, long-lived apps (5+ years), domain logic must be independent, CQRS beneficial, team 10+ people

**Example Use Cases:** Banking systems, insurance processing, complex e-commerce, trading platforms, supply chain management

### Signs You Need to Evolve

| Current | Sign to Evolve | Next Step |
|---------|----------------|-----------|
| **Layered** | Hard to find related code, teams stepping on each other | → Package-By-Module |
| **Package-By-Module** | Accidental cross-module dependencies, unreliable events | → Simple Modulith |
| **Simple Modulith** | Lots of validation scattered, primitive confusion bugs | → Tomato |
| **Tomato** | Need to swap databases, add CQRS, separate read/write | → DDD+Hexagonal |

---

## Summary

### Quick Reference

| Pattern | One-Liner | When to Use |
|---------|-----------|-------------|
| **Layered** | Quick and simple for basic CRUD | Small apps, prototypes, minimal domain logic |
| **Package-By-Module** | Organized by features, easy to navigate | Medium apps with clear feature ownership |
| **Simple Modulith** | Package-By-Module with guaranteed boundaries | Need module isolation and persistent events |
| **Tomato** | Type-safe domain with Value Objects | Medium complexity, need type safety |
| **DDD+Hexagonal** | Full domain independence for complex systems | Complex domains, long-lived, evolving |

### The Golden Rules

1. **Start Simple** - Choose the simplest architecture that solves your problem
2. **Evolve Gradually** - It's easier to add complexity than remove it
3. **Listen to Pain Points** - Let actual problems guide architectural evolution
4. **Consider Team Experience** - Don't jump to DDD if team isn't ready
5. **Value Delivery Over Purity** - Ship working software, refine architecture later

---

## Official Documentation

- [Structuring Your Code - Spring Boot](https://docs.spring.io/spring-boot/reference/using/structuring-your-code.html)
- [Spring Modulith Reference](https://docs.spring.io/spring-modulith/reference/)
- [Domain-Driven Design (DDD) - Martin Fowler](https://martinfowler.com/tags/domain%20driven%20design.html)
- [Hexagonal Architecture - Alistair Cockburn](https://alistair.cockburn.us/hexagonal-architecture/)
- [Spring Data JPA Reference](https://docs.spring.io/spring-data/jpa/reference/)
- [Spring Events Documentation](https://docs.spring.io/spring-framework/reference/core/beans/context-introduction.html#context-functionality-events)
- [CQRS Pattern - Martin Fowler](https://martinfowler.com/bliki/CQRS.html)
- [Anemic Domain Model - Martin Fowler](https://martinfowler.com/bliki/AnemicDomainModel.html)

---

**Remember:** The best architecture is the one that serves your current needs while allowing for future growth. Don't over-engineer, but don't paint yourself into a corner either. Start simple, ship value, and evolve thoughtfully.
