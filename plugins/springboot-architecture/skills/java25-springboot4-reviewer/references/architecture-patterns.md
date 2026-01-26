# Architecture Patterns

## Table of Contents

1. [Layered Architecture](#layered-architecture)
2. [Package-By-Module Architecture](#package-by-module-architecture)
3. [Simple Modular Monolith](#simple-modular-monolith)
4. [Tomato Architecture](#tomato-architecture)
5. [Domain-Driven Design (DDD)](#domain-driven-design)
6. [Hexagonal Architecture](#hexagonal-architecture)
7. [Spring Modulith](#spring-modulith)
8. [CQRS](#cqrs)
9. [Event-Driven Architecture](#event-driven-architecture)

---

## Layered Architecture

The simplest pattern in this repo (`meetup4j-layered`) and a good starting point for small CRUD-style services.

### Structure

```
com.example.app
├── controller/           # REST endpoints
├── service/              # Transaction scripts / orchestration
├── repository/           # Data access
└── domain/
    ├── entities/         # JPA entities (anemic)
    ├── models/           # DTOs / view models
    ├── exceptions/
    └── events/
```

### When to Use
- Small teams (1–3 devs), short-lived apps, or simple microservices.
- Domain complexity is low; rich domain model not needed yet.
- You expect to evolve to feature-modular or Modulith later but don’t need it now.

### Rules

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

public interface UserRepository extends JpaRepository<User, Long> {
    // Repository → Database
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

❌ **Entities exposed to clients**
```java
@GetMapping("/users/{id}")
public User getUser(@PathVariable Long id) {  // Exposes JPA entity!
    return userRepository.findById(id).orElseThrow();
}
```

✅ **Use DTOs**
```java
@GetMapping("/users/{id}")
public UserDTO getUser(@PathVariable Long id) {  // Clean DTO
    return userService.findById(id);
}

public record UserDTO(Long id, String name, String email) {}
```

### Common Pitfalls (from Domain Modeling Guide)
- **Anemic domain**: entities are just getters/setters; all rules in services.
- **Primitive obsession**: `String`/`int` used for domain concepts (codes, money, capacity).
- **Invalid states**: no invariants (e.g., end date before start date, negative capacity).
- **Cross-layer leakage**: controllers talking directly to repositories; entities returned to API.

### Evolution Tips
- If feature ownership grows, reorganize by feature (package-by-module).
- Introduce value objects for high-risk primitives (price, code, capacity) before jumping to rich domain models.
- Add module tests (Spring Modulith) once boundaries start to matter.

**Review Checklist:**
- [ ] Controllers → Services only; no direct repository access.
- [ ] Services own business rules; controllers only orchestrate I/O.
- [ ] Entities never returned in API; DTOs/view models used.
- [ ] Validate invariants somewhere (preferably in service or emerging value objects).
- [ ] Watch for primitive obsession in core fields (code, money, dates, capacity).

---

## Package-By-Module Architecture

Feature-first structure from `meetup4j-package-by-feature`; same layers, grouped per business module.

### Structure
```
com.example.app
├── events/
│   ├── domain/
│   ├── rest/
│   └── internal/        # optional helpers
├── registrations/
│   ├── domain/
│   └── rest/
├── notifications/
└── shared/              # cross-cutting only (logging, time, ids)
```

### Choose When
- 3–10 person teams with clear feature ownership.
- Medium complexity; want easier navigation and potential later extraction to services.
- Need clearer bounded contexts than layered but not strict enforcement yet.

### Avoid When
- App is tiny (layered is simpler).
- You already need hard module boundaries or persistent events (go Modulith).

**Review Checklist:**
- [ ] Code grouped by feature/module, not technical layer.
- [ ] Shared package is minimal and generic; no business logic leaks there.
- [ ] Cross-module calls go through services or events, not direct repository/entity access.
- [ ] Controllers stay inside their module; no cross-module controllers.

---

## Simple Modular Monolith

Package-by-module plus Spring Modulith boundary enforcement and persistent events (`meetup4j-modulith-simple`).

### What’s Added
- `ApplicationModules.of(App.class).verify()` tests to prevent forbidden dependencies.
- `@ApplicationModuleListener` for transactional, persistent cross-module events (replayable, retried).
- Module metadata for visualization (optional).

### Choose When
- Need reliable module isolation but still a monolith.
- Require durable cross-module messaging without a broker.
- Want an easy migration path toward microservices later.

### Avoid When
- Overhead isn’t justified (very small apps).
- You need full domain/persistence separation (go Tomato or DDD/Hex).

**Review Checklist:**
- [ ] Modules.verify() (or equivalent) exists and passes in tests.
- [ ] Cross-module communication uses `@ApplicationModuleListener` events, not direct calls.
- [ ] Internal types kept package-private or under `internal/`.
- [ ] Event publication is transactional; event store configured if needed.

---

## Tomato Architecture

Value-object-heavy, richer domain within a modular monolith (`meetup4j-modulith-tomato`). JPA entities embed VOs; behavior starts moving into aggregates but domain and persistence are still coupled.

### Characteristics
- Value Objects for codes, prices, capacity, schedule, location; validation in constructors (fail fast).
- Spring converters to map request strings → VOs automatically.
- Richer entity behavior (publish, cancel, reserve slot) instead of pure transaction scripts.
- Still monolith; modules remain feature-scoped as in package-by-module.

### Choose When
- Domain is medium complexity; type safety and invariants matter.
- Team is comfortable with VO/rich model patterns but doesn’t need full port/adapter separation.
- You want to reduce defensive coding scattered in services.

### Avoid When
- Domain is trivial (stay layered/PBF).
- You need infrastructure-independence or CQRS (go DDD + Hex).

**Review Checklist:**
- [ ] Core concepts use VOs (EventCode, Capacity, TicketPrice, Schedule).
- [ ] Validation enforced at creation; primitives not leaking through APIs.
- [ ] Spring converters registered for external → VO mapping.
- [ ] Business rules live on aggregates; services orchestrate only.

---

## Domain-Driven Design

**Choose When:** Complex/long-lived domains, multiple subdomains, evolving business rules, teams that can invest in ubiquitous language and aggregates.  
**Avoid When:** Simple CRUD services, tiny teams, or when delivery speed matters more than modeling depth.

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
│   ├── domain/
│   │   ├── Product.java
│   │   └── Category.java
│   ├── application/
│   │   └── CatalogService.java
│   ├── infrastructure/
│   │   └── ProductRepository.java
│   └── api/
│       └── ProductController.java
└── payment/
    └── ...
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
    private String email;

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

@Entity
public class Customer {
    @Id
    private Long id;

    @Embedded
    private Address billingAddress;

    @Embedded
    @AttributeOverrides({
        @AttributeOverride(name = "street", column = @Column(name = "shipping_street")),
        @AttributeOverride(name = "city", column = @Column(name = "shipping_city")),
        @AttributeOverride(name = "state", column = @Column(name = "shipping_state")),
        @AttributeOverride(name = "zipCode", column = @Column(name = "shipping_zip"))
    })
    private Address shippingAddress;
}
```

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

@Entity
public class OrderItem {  // Not an aggregate root
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne
    @JoinColumn(name = "order_id", nullable = false)
    private Order order;

    @ManyToOne
    private Product product;

    private int quantity;

    @Embedded
    private Money subtotal;
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
    private final OrderItemRepository orderItemRepository;

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
    private final OrderRepository orderRepository;

    public void updateItemQuantity(Long orderId, Long itemId, int quantity) {
        Order order = orderRepository.findById(orderId).orElseThrow();
        order.updateItemQuantity(itemId, quantity);  // Through root
        orderRepository.save(order);  // Total recalculated
    }
}
```

### Domain Services

Business logic that doesn't belong to a single entity.

```java
@Service
public class PricingService {  // Domain service
    public Money calculateOrderTotal(Order order, Customer customer, Coupon coupon) {
        Money subtotal = order.getSubtotal();
        Money discount = calculateDiscount(subtotal, customer, coupon);
        Money tax = calculateTax(subtotal.subtract(discount), customer.getAddress());
        return subtotal.subtract(discount).add(tax);
    }

    private Money calculateDiscount(Money subtotal, Customer customer, Coupon coupon) {
        // Complex discount logic
    }

    private Money calculateTax(Money amount, Address address) {
        // Tax calculation
    }
}
```

**Review Checklist:**
- [ ] Code organized by domain (order, catalog, payment) not layer
- [ ] Entities have identity, value objects don't
- [ ] Aggregates enforce invariants
- [ ] Changes to aggregate parts go through root
- [ ] Domain services used for cross-entity logic

---

## Hexagonal Architecture

**Choose When:** Need technology independence, port swapping (databases, gateways), strong testability via ports/adapters, or CQRS readiness.  
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

// domain/port/out/PaymentGateway.java
public interface PaymentGateway {
    PaymentResult processPayment(Payment payment);
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

        // Business logic
        PaymentResult result = paymentGateway.processPayment(order.getPayment());
        if (!result.isSuccess()) {
            throw new PaymentFailedException();
        }

        return orderRepository.save(order);
    }
}
```

✅ **Input adapter (REST)**
```java
// adapter/in/rest/OrderController.java
@RestController
@RequestMapping("/orders")
public class OrderController {
    private final CreateOrderUseCase createOrderUseCase;  // In port

    @PostMapping
    public OrderDTO createOrder(@Valid @RequestBody CreateOrderRequest request) {
        CreateOrderCommand command = toCommand(request);
        Order order = createOrderUseCase.createOrder(command);
        return toDTO(order);
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

// Internal JPA repository (not exposed to domain)
interface OrderJpaRepository extends JpaRepository<OrderEntity, Long> {}
```

✅ **Output adapter (payment gateway)**
```java
// adapter/out/payment/StripePaymentAdapter.java
@Component
public class StripePaymentAdapter implements PaymentGateway {
    private final StripeClient stripeClient;

    @Override
    public PaymentResult processPayment(Payment payment) {
        try {
            ChargeResult result = stripeClient.charge(
                payment.getAmount(),
                payment.getCurrency(),
                payment.getToken()
            );
            return new PaymentResult(result.getId(), true);
        } catch (StripeException e) {
            return new PaymentResult(null, false);
        }
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

**Choose When:** You want module boundary enforcement and durable intra-monolith events without deploying separate services.  
**Avoid When:** Boundaries aren’t important (stay layered/PBF) or you need full domain/infra separation (go DDD/Hex).

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
│   ├── Product.java
│   ├── ProductService.java
│   └── ProductRepository.java
└── payment/                # Module
    ├── Payment.java
    ├── PaymentService.java
    └── PaymentRepository.java
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
    private Long customerId;
    private BigDecimal total;
}

// order/OrderService.java
package com.example.app.order;

@Service
public class OrderService {  // Public
    public Order createOrder(CreateOrderRequest request) {
        // ...
    }
}
```

✅ **Internal implementation**
```java
// order/internal/OrderValidator.java
package com.example.app.order.internal;

@Component
class OrderValidator {  // Package-private - only accessible within 'order' module
    boolean isValid(Order order) {
        // ...
    }
}
```

❌ **Violating module boundary**
```java
// payment/PaymentService.java
package com.example.app.payment;

import com.example.app.order.internal.OrderValidator;  // Compile error!

@Service
public class PaymentService {
    private final OrderValidator validator;  // Cannot access internal!
}
```

### Module Events

✅ **Publishing events**
```java
// order/OrderService.java
@Service
public class OrderService {
    private final ApplicationEventPublisher eventPublisher;

    public Order createOrder(CreateOrderRequest request) {
        Order order = orderRepository.save(new Order(request));

        // Publish event
        eventPublisher.publishEvent(new OrderCreatedEvent(order.getId()));

        return order;
    }
}

// order/OrderCreatedEvent.java
public record OrderCreatedEvent(Long orderId) implements Externalized {}
```

✅ **Listening to events (in different module)**
```java
// payment/PaymentService.java
package com.example.app.payment;

@Service
public class PaymentService {
    @ApplicationModuleListener  // Spring Modulith annotation
    public void onOrderCreated(OrderCreatedEvent event) {
        // Process payment for order
        processPayment(event.orderId());
    }
}
```

### Event Externalization

Spring Modulith can externalize events to message brokers.

```yaml
spring:
  modulith:
    events:
      externalization:
        enabled: true
      jdbc:
        schema-initialization:
          enabled: true
```

✅ **Event store table**
```sql
CREATE TABLE event_publication (
    id UUID PRIMARY KEY,
    event_type VARCHAR(255) NOT NULL,
    listener_id VARCHAR(255) NOT NULL,
    publication_date TIMESTAMP NOT NULL,
    serialized_event TEXT NOT NULL,
    completion_date TIMESTAMP
);
```

### Module Verification

✅ **Test module boundaries**
```java
@SpringBootTest
class ModulithTest {
    @Test
    void verifyModules() {
        ApplicationModules.of(Application.class)
            .verify();  // Fails if module boundaries violated
    }

    @Test
    void verifyModuleDependencies() {
        ApplicationModules modules = ApplicationModules.of(Application.class);

        modules.forEach(module -> {
            System.out.println("Module: " + module.getName());
            System.out.println("Dependencies: " + module.getDependencies());
        });
    }
}
```

**Review Checklist:**
- [ ] Modules organized by business domain
- [ ] Internal classes in `internal` package or package-private
- [ ] Cross-module communication via events
- [ ] Module boundaries verified in tests
- [ ] Event store configured for reliable messaging

---

## CQRS

**Choose When:** Read/write workloads differ a lot, you need denormalized read models, or eventual consistency is acceptable.  
**Avoid When:** Simple CRUD or when dual models add needless complexity.

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

### Advanced: Separate Databases

```
Write DB (PostgreSQL)     Read DB (MongoDB)
      ↓                          ↑
  Commands                    Queries
      ↓                          ↑
  Event Bus →→→→→→→→ Event Handler →→ Updates Read DB
```

✅ **Event handler updates read model**
```java
@Service
public class OrderReadModelUpdater {
    private final OrderReadRepository readRepository;

    @EventListener
    public void onOrderCreated(OrderCreatedEvent event) {
        Order order = orderRepository.findById(event.orderId()).orElseThrow();
        OrderReadModel readModel = toReadModel(order);
        readRepository.save(readModel);
    }

    @EventListener
    public void onOrderUpdated(OrderUpdatedEvent event) {
        OrderReadModel readModel = readRepository.findById(event.orderId()).orElseThrow();
        readModel.update(event);
        readRepository.save(readModel);
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

**Choose When:** You need loose coupling between modules/services, asynchronous workflows, or multiple consumers of the same business facts.  
**Avoid When:** Work is strictly request/response and consistency must be immediate everywhere.

### Domain Events

✅ **Define events**
```java
public record OrderCreatedEvent(
    Long orderId,
    Long customerId,
    BigDecimal total,
    LocalDateTime createdAt
) {}

public record PaymentProcessedEvent(
    Long paymentId,
    Long orderId,
    PaymentStatus status
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
        // Reserve inventory
        reserveItems(event.orderId());
    }
}

@Service
public class NotificationService {
    @Async
    @EventListener
    public void onOrderCreated(OrderCreatedEvent event) {
        // Send confirmation email
        sendOrderConfirmation(event.customerId(), event.orderId());
    }
}
```

### Transactional Events

✅ **Publish after transaction commits**
```java
@Service
public class OrderService {
    private final ApplicationEventPublisher eventPublisher;

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

## Quick Decision Matrix

| Pattern | Domain Complexity | Team Size | Type Safety | Module Boundaries | Best For |
|---------|-------------------|-----------|-------------|-------------------|----------|
| Layered | Low | 1–3 | Low | None | Small CRUD services, prototypes |
| Package-By-Module | Low–Medium | 3–10 | Low | Soft | Feature-owned teams, clearer navigation |
| Simple Modular Monolith | Low–Medium | 5–15 | Low | Hard (Modulith verify) | Monoliths needing enforced boundaries & durable events |
| Tomato | Medium | 5–15 | High (VOs) | Hard (per module) | Type-safe domains with richer entities, still monolith |
| DDD + Hexagonal | High | 10+ | High | Hard (ports/adapters) | Complex, long-lived domains, infra swap/CQRS ready |

---

## Architecture Review Checklist

### Layered Architecture

- [ ] Controllers don't call repositories directly
- [ ] Business logic in services (not controllers)
- [ ] DTOs used for API contracts (not entities)
- [ ] No circular dependencies between layers

### Domain-Driven Design

- [ ] Code organized by domain (not layer)
- [ ] Aggregates enforce invariants
- [ ] Changes to aggregate parts through root
- [ ] Value objects immutable
- [ ] Domain services for cross-entity logic

### Hexagonal Architecture

- [ ] Domain independent of frameworks
- [ ] External dependencies behind ports
- [ ] Adapters implement ports
- [ ] Domain testable without Spring

### Spring Modulith

- [ ] Modules organized by business domain
- [ ] Internal implementations not accessible
- [ ] Cross-module communication via events
- [ ] Module boundaries verified

### CQRS

- [ ] Commands and queries separated
- [ ] Write model normalized
- [ ] Read model denormalized
- [ ] Event handlers update read model

### Event-Driven

- [ ] Domain events published
- [ ] Transactional event listeners used
- [ ] Event handlers idempotent
- [ ] Event versioning considered

---

## Official Documentation

- [Structuring Your Code - Spring Boot](https://docs.spring.io/spring-boot/reference/using/structuring-your-code.html)
- [Spring Modulith Reference](https://docs.spring.io/spring-modulith/reference/)
- [Spring Modulith Fundamentals](https://docs.spring.io/spring-modulith/reference/fundamentals.html)
- [Domain-Driven Design (DDD) - Martin Fowler](https://martinfowler.com/tags/domain%20driven%20design.html)
- [Hexagonal Architecture - Alistair Cockburn](https://alistair.cockburn.us/hexagonal-architecture/)
- [Spring Data JPA Reference](https://docs.spring.io/spring-data/jpa/reference/)
- [Spring Events Documentation](https://docs.spring.io/spring-framework/reference/core/beans/context-introduction.html#context-functionality-events)
- [CQRS Pattern - Martin Fowler](https://martinfowler.com/bliki/CQRS.html)
- [Event-Driven Architecture - AWS](https://aws.amazon.com/event-driven-architecture/)
- [Spring Boot Application Architecture Patterns (repo)](https://github.com/sivaprasadreddy/spring-boot-application-architecture-patterns)
