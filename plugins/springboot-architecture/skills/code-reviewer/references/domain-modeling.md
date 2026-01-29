# Domain Modeling: Anemic vs Rich

This guide explains the difference between anemic and rich domain models, primitive obsession anti-pattern, and migration strategies.

## Table of Contents

1. [Anemic Domain Models](#anemic-domain-models)
2. [Primitive Obsession Anti-Pattern](#primitive-obsession-anti-pattern)
3. [Rich Domain Models](#rich-domain-models)
4. [Comparison with Examples](#comparison-with-examples)
5. [When to Use Each Approach](#when-to-use-each-approach)
6. [Migration Path](#migration-path)

---

## Anemic Domain Models

### What is an Anemic Domain Model?

An **Anemic Domain Model** is an anti-pattern where domain objects contain only data (properties) with getters/setters, but **no business logic or behavior**. All business logic lives in service classes, treating domain objects as simple data containers.

Martin Fowler coined this term and describes it as an anti-pattern because it violates the fundamental principle of object-oriented programming: **objects should encapsulate both data and behavior**.

### Characteristics

❌ **Has:**
- Properties/fields with getters and setters
- No validation beyond simple null checks
- No business logic
- No domain behavior

✅ **Missing:**
- Business behavior (methods that operate on the data)
- Domain rules and invariants
- Self-validation
- Encapsulation

### Example: Anemic Entity

```java
// ❌ ANEMIC: Entity is just a data bag
@Entity
@Table(name = "orders")
public class Order {
    @Id
    private Long id;
    private String orderNumber;      // ❌ Primitive - any string
    private BigDecimal total;        // ❌ No validation
    private Integer quantity;        // ❌ Could be negative
    private String status;           // ❌ String, not enum

    // ONLY GETTERS AND SETTERS - NO BEHAVIOR
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public BigDecimal getTotal() { return total; }
    public void setTotal(BigDecimal total) { this.total = total; }
    // ... 50+ lines of getters/setters
}
```

### Example: Service with ALL Business Logic (Transaction Script)

```java
// ❌ ALL business logic in service
@Service
public class OrderService {
    @Transactional
    public void cancelOrder(Long orderId) {
        Order order = repository.findById(orderId).orElseThrow();

        // ❌ Business rules in service, not domain
        if ("SHIPPED".equals(order.getStatus())) {
            throw new IllegalStateException("Cannot cancel shipped orders");
        }
        if ("CANCELLED".equals(order.getStatus())) {
            return;  // Already cancelled
        }

        // ❌ Using setter to change state
        order.setStatus("CANCELLED");
        repository.save(order);
    }

    @Transactional
    public void createOrder(CreateOrderRequest request) {
        var order = new Order();
        order.setOrderNumber(UUID.randomUUID().toString());  // ❌ Manual construction
        order.setTotal(request.total());                     // ❌ No validation
        order.setQuantity(request.quantity());               // ❌ Could be negative!
        order.setStatus("PENDING");

        // What if we forget to set a field? Compile-time won't catch it!
        repository.save(order);
    }
}
```

### Problems with Anemic Models

1. **Scattered business logic** - Rules spread across multiple service methods
2. **Difficult to test** - Must test through services, can't test rules in isolation
3. **Duplication risk** - Same validation needed in multiple places
4. **Hard to maintain** - Must search through services to understand rules
5. **No encapsulation** - Can put entity in invalid state at any time
6. **Primitive obsession** - Using `String`, `Integer`, `BigDecimal` for domain concepts

---

## Primitive Obsession Anti-Pattern

### What is Primitive Obsession?

**Primitive Obsession** is using primitive types (`String`, `int`, `BigDecimal`) to represent domain concepts instead of creating proper domain types (Value Objects).

### Problems with Primitives

#### 1. No Type Safety

```java
// ❌ BAD: Using primitives
public void processOrder(String orderNumber, String customerEmail, String productCode) {
    // Can easily mix up parameters - all Strings!
    processOrder(customerEmail, orderNumber, productCode);  // Compiles! Runtime bug!
}

// ✅ GOOD: Using Value Objects
public void processOrder(OrderNumber orderNumber, EmailAddress email, ProductCode code) {
    // processOrder(email, orderNumber, code);  // ❌ Compiler error!
}
```

#### 2. No Validation

```java
// ❌ BAD: Validation scattered everywhere
public void createOrder(int quantity, BigDecimal price) {
    if (quantity < 0) {
        throw new IllegalArgumentException("Negative quantity");
    }
    if (price.compareTo(BigDecimal.ZERO) < 0) {
        throw new IllegalArgumentException("Negative price");
    }
    // ... actual logic
}

// Every method using these must duplicate validation!
public void updateOrder(int quantity, BigDecimal price) {
    // ❌ Must duplicate ALL validation again!
    if (quantity < 0) { ... }
    if (price.compareTo(BigDecimal.ZERO) < 0) { ... }
    // ...
}

// ✅ GOOD: Validation in Value Object
public OrderId createOrder(Quantity quantity, Money price) {
    // No validation needed - impossible to create invalid VOs!
    // If we got here, all parameters are already valid
}
```

#### 3. No Domain Meaning

```java
// ❌ BAD: What do these strings represent?
String code1 = "ABC-123";
String code2 = "user@example.com";
processOrder(code2);  // ❌ Wrong value, compiles fine!

// All are strings - easy to confuse
String orderNumber = "ORD-123";
String email = "user@example.com";
emailService.send(orderNumber);  // ❌ Oops! Wrong parameter

// ✅ GOOD: Clear domain meaning
OrderNumber orderNum = OrderNumber.of("ABC-123");
EmailAddress email = EmailAddress.of("user@example.com");
// processOrder(email);  // ❌ Compiler error!
// emailService.send(orderNum);  // ❌ Compiler error!
```

#### 4. No Domain Behavior

```java
// ❌ BAD: Behavior scattered in util classes
public class PriceUtils {
    public static boolean isFree(BigDecimal price) {
        return price.compareTo(BigDecimal.ZERO) == 0;
    }

    public static String format(BigDecimal price) {
        return "$" + price.setScale(2, RoundingMode.HALF_UP);
    }
}

BigDecimal price = order.getPrice();
if (PriceUtils.isFree(price)) { ... }
String formatted = PriceUtils.format(price);

// ✅ GOOD: Behavior in Value Object
Money price = order.getPrice();
if (price.isFree()) { ... }
String formatted = price.format();
```

### Real Examples

#### Example 1: Order Number as String

```java
// ❌ PRIMITIVE OBSESSION
@Entity
public class Order {
    private String orderNumber;  // Just a string - no validation, no type safety

    public String getOrderNumber() { return orderNumber; }
    public void setOrderNumber(String orderNumber) { this.orderNumber = orderNumber; }
}

// Problems:
order.setOrderNumber("");                    // ❌ Empty string allowed
order.setOrderNumber(null);                  // ❌ Null allowed
order.setOrderNumber("invalid-format");      // ❌ Any string allowed
String userEmail = "user@example.com";
order.setOrderNumber(userEmail);             // ❌ Wrong value, but compiles!
```

#### Example 2: Quantity as Integer

```java
// ❌ PRIMITIVE OBSESSION
@Entity
public class OrderItem {
    private Integer quantity;  // Any integer, even negative!

    public Integer getQuantity() { return quantity; }
    public void setQuantity(Integer quantity) { this.quantity = quantity; }
}

// Problems:
item.setQuantity(-100);              // ❌ Negative quantity
item.setQuantity(1000000);           // ❌ Unrealistic quantity
item.setQuantity(null);              // ❌ Null - what does this mean?

// Business logic scattered:
if (quantity != null && quantity > 0 && quantity < 10000) {
    // ... valid
}
```

#### Example 3: Date Range as Separate Fields

```java
// ❌ PRIMITIVE OBSESSION
@Entity
public class Reservation {
    private LocalDate startDate;
    private LocalDate endDate;

    // No validation that end > start!
}

// Problems:
reservation.setStartDate(LocalDate.of(2024, 12, 31));
reservation.setEndDate(LocalDate.of(2024, 1, 1));  // ❌ Before start! No error!

// Must validate relationships everywhere:
if (reservation.getEndDate().isBefore(reservation.getStartDate())) {
    throw new IllegalArgumentException("End before start");
}
```

#### Example 4: Money as BigDecimal

```java
// ❌ PRIMITIVE OBSESSION
@Entity
public class Product {
    private BigDecimal price;  // No currency, no validation
}

// Problems:
product.setPrice(new BigDecimal("-50.00"));  // ❌ Negative price
product.setPrice(null);                      // ❌ Null
product.setPrice(new BigDecimal("0.001"));   // ❌ Sub-cent precision

// What currency? USD? EUR? Unknown!
BigDecimal total = price1.add(price2);  // Adding prices from different currencies?
```

---

## Rich Domain Models

### What is a Rich Domain Model?

A **Rich Domain Model** contains both **data AND behavior**. Business logic lives in domain objects themselves, making them intelligent and self-validating.

### Characteristics

✅ **Has:**
- Encapsulated state (private fields)
- Business logic methods
- Self-validation
- Domain-specific behavior
- Factory methods for creation
- Value Objects for primitive concepts

❌ **Doesn't have:**
- Public setters (immutability preferred)
- Logic in services (services orchestrate, don't implement)
- Primitive obsession

### Example: Rich Entity

```java
// ✅ RICH: Entity has behavior
@Entity
@Table(name = "orders")
public class Order extends BaseEntity {

    @EmbeddedId
    private OrderId id;

    @Embedded
    private OrderNumber orderNumber;  // ✅ Value Object, not String

    @Embedded
    private Money total;  // ✅ Value Object, not BigDecimal

    @Embedded
    private Quantity quantity;  // ✅ Value Object, not Integer

    @Enumerated(EnumType.STRING)
    private OrderStatus status;

    // ✅ FACTORY METHOD - controls creation
    public static Order createNew(Quantity quantity, Money unitPrice) {
        Money total = unitPrice.multiply(quantity.value());
        return new Order(
            OrderId.generate(),
            OrderNumber.generate(),
            quantity,
            total,
            OrderStatus.PENDING
        );
    }

    // ✅ BUSINESS BEHAVIOR - not in service!
    public boolean canBeCancelled() {
        return status == OrderStatus.PENDING || status == OrderStatus.CONFIRMED;
    }

    public void cancel() {
        if (!canBeCancelled()) {
            throw new IllegalStateException(
                "Cannot cancel order in status: " + status);
        }
        this.status = OrderStatus.CANCELLED;
    }

    public void confirm() {
        if (status != OrderStatus.PENDING) {
            throw new IllegalStateException("Only pending orders can be confirmed");
        }
        this.status = OrderStatus.CONFIRMED;
    }

    public void ship() {
        if (status != OrderStatus.CONFIRMED) {
            throw new IllegalStateException("Only confirmed orders can be shipped");
        }
        this.status = OrderStatus.SHIPPED;
    }

    public boolean isShipped() {
        return status == OrderStatus.SHIPPED;
    }

    public boolean isPending() {
        return status == OrderStatus.PENDING;
    }

    // ✅ ONLY GETTERS - NO SETTERS!
    public OrderId getId() { return id; }
    public OrderNumber getOrderNumber() { return orderNumber; }
    public Money getTotal() { return total; }
    public OrderStatus getStatus() { return status; }
}
```

### Example: Thin Service - Just Orchestration

```java
// ✅ THIN SERVICE - domain does the work!
@Service
public class OrderService {
    private final OrderRepository repository;
    private final ApplicationEventPublisher eventPublisher;

    @Transactional
    public void cancelOrder(OrderId orderId) {
        Order order = repository.findById(orderId).orElseThrow();
        order.cancel();  // ✅ Domain does the work!
        repository.save(order);
        eventPublisher.publishEvent(new OrderCancelled(orderId));
    }

    @Transactional
    public OrderNumber createOrder(CreateOrderCommand cmd) {
        // ✅ Factory method creates valid entity
        Order order = Order.createNew(cmd.quantity(), cmd.unitPrice());
        repository.save(order);
        eventPublisher.publishEvent(new OrderCreated(order.getOrderNumber()));
        return order.getOrderNumber();
    }
}
```

### Benefits of Rich Models

1. ✅ **Self-documenting** - Methods show what objects can do
2. ✅ **Encapsulation** - Can't put entity in invalid state
3. ✅ **Testable** - Can test business logic without services
4. ✅ **Maintainable** - Business rules in one place
5. ✅ **Type-safe** - Can't confuse `OrderNumber` with `String`
6. ✅ **Fail-fast** - Invalid objects cannot be created

---

## Comparison with Examples

### Creating an Order

#### Anemic Model

```java
// ❌ ANEMIC: All logic in service
@Transactional
public String createOrder(CreateOrderRequest request) {
    // ❌ Manual construction with setters
    var order = new Order();
    order.setOrderNumber(UUID.randomUUID().toString());  // ❌ No type safety
    order.setTotal(request.total());                     // ❌ No validation
    order.setQuantity(request.quantity());               // ❌ Could be negative!
    order.setStatus("PENDING");

    // What if we forget to set a required field? No compile-time safety!
    repository.save(order);
    return order.getOrderNumber();
}
```

**Problems:**
- 15+ lines just to set values
- No validation anywhere
- Easy to forget to set a field
- No guarantee of valid state
- Can create order with negative quantity

#### Rich Model

```java
// ✅ RICH: Domain does the work
@Transactional
public OrderNumber createOrder(CreateOrderCommand cmd) {
    // ✅ Factory method creates valid entity
    Order order = Order.createNew(
        cmd.quantity(),   // ✅ Already validated VO
        cmd.unitPrice()   // ✅ Already validated VO
    );
    repository.save(order);
    return order.getOrderNumber();  // ✅ Returns VO, not String
}
```

**Benefits:**
- 5 lines instead of 15
- All validation done in VOs
- Impossible to create invalid order
- Type-safe
- Factory method ensures correct initialization

### Cancelling an Order

#### Anemic Model

```java
// ❌ ANEMIC: Business logic in service
@Transactional
public void cancelOrder(Long orderId) {
    Order order = repository.findById(orderId).orElseThrow();

    // ❌ Business rule in service, not domain
    if ("SHIPPED".equals(order.getStatus())) {
        throw new IllegalStateException("Cannot cancel shipped orders");
    }

    // ❌ Manual state check
    if ("CANCELLED".equals(order.getStatus())) {
        return;
    }

    // ❌ Using setter to change state
    order.setStatus("CANCELLED");
    repository.save(order);
}
```

**Problems:**
- Business rules scattered in service
- Direct state manipulation with setter
- Rules duplicated if needed elsewhere
- Hard to test rules without service

#### Rich Model

```java
// ✅ RICH: Domain encapsulates logic
@Transactional
public void cancelOrder(OrderId orderId) {
    Order order = repository.findById(orderId).orElseThrow();

    // ✅ Domain method with business rules
    order.cancel();  // Returns void or throws exception

    repository.save(order);
}

// Inside Order entity:
public void cancel() {
    // ✅ Business rule in domain
    if (this.isShipped()) {
        throw new IllegalStateException("Cannot cancel shipped orders");
    }
    // ✅ Idempotency check
    if (this.isCancelled()) {
        return;
    }
    this.status = OrderStatus.CANCELLED;
}
```

**Benefits:**
- Business logic testable without service
- Rules in domain where they belong
- Service is just orchestration
- Idempotency built-in
- Reusable cancel logic

---

## When to Use Each Approach

### Use Anemic Model When

✅ **Simple CRUD operations**
- Read/write to database with minimal logic
- No complex business rules
- Data is mostly displayed, not processed

✅ **Rapid prototyping**
- Speed over design
- Requirements unclear
- Likely to change drastically

✅ **Very small applications**
- 1-2 entities
- Short lifespan
- Single developer

**Example Use Cases:**
- Admin panels with simple forms
- Data entry applications
- Internal tools with basic CRUD
- Quick prototypes and MVPs

### Use Rich Model When

✅ **Complex business logic**
- Many rules and constraints
- State transitions with conditions
- Domain-specific behavior

✅ **Type safety matters**
- Financial applications (money handling)
- Healthcare systems (patient data)
- E-commerce with complex pricing

✅ **Long-lived applications**
- Need to evolve over time
- Multiple developers
- High maintainability requirements

✅ **Domain complexity**
- Multiple bounded contexts
- Complex workflows
- Business rule changes frequent

**Example Use Cases:**
- Banking systems
- E-commerce platforms
- Booking/reservation systems
- Order management systems
- Inventory management
- Healthcare applications

---

## Migration Path

### Migrating from Anemic to Rich Models

#### Step 1: Identify Primitives to Wrap

```java
// Before
private String orderNumber;
private Integer quantity;
private BigDecimal price;

// After
private OrderNumber orderNumber;
private Quantity quantity;
private Money price;
```

#### Step 2: Create Value Objects

```java
// Example: OrderNumber as a Value Object
public record OrderNumber(String value) {
    public OrderNumber {
        // Validation in constructor (fail-fast)
        if (value == null || value.trim().isEmpty()) {
            throw new IllegalArgumentException("Order number required");
        }
    }
}
```

**See:** [value-objects-patterns.md](value-objects-patterns.md) for comprehensive VO patterns including factory methods, JSON serialization, and format validation

#### Step 3: Move Validation to VOs

```java
// Before: Validation in service
if (quantity < 0) {
    throw new IllegalArgumentException("Negative quantity");
}

// After: Validation in VO
public record Quantity(Integer value) {
    public Quantity {
        if (value != null && value < 0) {
            throw new IllegalArgumentException("Negative quantity");
        }
    }
}
```

#### Step 4: Move Behavior to Domain

```java
// Before: Logic in service
if (order.getStatus() == OrderStatus.CONFIRMED) {
    return;
}
order.setStatus(OrderStatus.CONFIRMED);

// After: Method in entity
public boolean confirm() {
    if (this.isConfirmed()) {
        return false;
    }
    this.status = OrderStatus.CONFIRMED;
    return true;
}
```

#### Step 5: Replace Setters with Methods

```java
// Before
order.setStatus(OrderStatus.CANCELLED);

// After
order.cancel();  // Enforces business rules
```

#### Step 6: Use Factory Methods

```java
// Before: Constructor with many parameters
Order order = new Order(
    OrderNumber.generate(),
    quantity,
    price,
    OrderStatus.PENDING
);

// After: Named factory method
Order order = Order.createNew(quantity, unitPrice);
```

### Migration Strategy

**Gradual Approach (Recommended):**

1. Start with the most critical domain concepts
2. Create VOs for high-risk primitives (Money, Quantity, IDs)
3. Move validation to VOs
4. Gradually add behavior to entities
5. Remove setters as behavior is added
6. Keep anemic models for simple CRUD entities

**Don't Try to:**
- Convert everything at once
- Apply rich models to trivial CRUD entities
- Over-engineer simple domains
- Force the pattern where it doesn't fit

---

## Key Takeaways

### Anemic Domain Model

- ❌ Anti-pattern for complex domains
- ❌ Business logic scattered in services
- ❌ Difficult to maintain and test
- ✅ OK for simple CRUD
- ✅ OK for prototypes

### Primitive Obsession

- ❌ No type safety
- ❌ Validation duplicated
- ❌ No domain meaning
- ❌ Easy to make mistakes
- ✅ Replace with Value Objects

### Rich Domain Model

- ✅ Business logic in domain
- ✅ Self-validating
- ✅ Testable in isolation
- ✅ Type-safe with VOs
- ✅ Maintainable
- ⚠️ More complex initially

### Summary Table

| Aspect | Anemic + Primitives | Rich + Value Objects |
|--------|---------------------|----------------------|
| **Type Safety** | ❌ None | ✅ Strong |
| **Validation** | ❌ Scattered | ✅ At creation |
| **Business Logic** | ❌ In services | ✅ In domain |
| **Testability** | ❌ Through services | ✅ Direct unit tests |
| **Maintainability** | ❌ Hard to find rules | ✅ Rules in one place |
| **Complexity** | ✅ Low initially | ⚠️ Higher initially |
| **Long-term Cost** | ❌ High | ✅ Low |
| **Best For** | Simple CRUD | Complex domains |

---

## Further Reading

- [Anemic Domain Model - Martin Fowler](https://martinfowler.com/bliki/AnemicDomainModel.html)
- [Domain-Driven Design - Eric Evans](https://www.domainlanguage.com/ddd/)
- [Value Objects - Martin Fowler](https://martinfowler.com/bliki/ValueObject.html)
- [architecture-patterns.md](architecture-patterns.md) - Architecture pattern comparisons
- [value-objects-patterns.md](value-objects-patterns.md) - Value Object implementation patterns

---

**Remember:** Start simple with anemic models for CRUD. Introduce Value Objects when you see validation scattered or type confusion bugs. Move to rich models when domain complexity justifies the investment. Don't over-engineer, but don't underestimate the long-term benefits of rich domain models.
