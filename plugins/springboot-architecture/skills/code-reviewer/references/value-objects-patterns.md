# Value Objects Patterns

This guide provides practical patterns and examples for implementing Value Objects in Spring Boot applications.

## Table of Contents

1. [What are Value Objects?](#what-are-value-objects)
2. [Core Value Object Patterns](#core-value-object-patterns)
3. [Embedding Value Objects](#embedding-value-objects)
4. [Spring Integration](#spring-integration)
5. [Best Practices](#best-practices)

---

## What are Value Objects?

**Value Objects** are immutable objects representing domain concepts, defined by their values (not identity).

### Characteristics

- **Immutable** - Cannot be changed after creation
- **Self-validating** - Invalid VOs cannot exist
- **Equality by value** - Two VOs with same values are equal
- **No identity** - No ID field; defined by attributes
- **Rich behavior** - Can have domain-specific methods

### Why Use Value Objects?

| Problem with Primitives | Solution with Value Objects |
|-------------------------|------------------------------|
| No type safety (`String` orderNumber vs `String` email) | Compiler catches type mismatches |
| Validation scattered everywhere | Validation in VO constructor (once) |
| No domain meaning (`BigDecimal` could be price or discount) | Clear intent (`Money`, `Percentage`) |
| No domain behavior (util classes) | Behavior in VO methods |
| Easy to pass wrong values | Impossible to create invalid VOs |

---

## Core Value Object Patterns

### 1. Simple Identity Value Object

Wrapping IDs for type safety.

```java
public record OrderId(Long id) {

    public OrderId {
        if (id == null || id < 0) {
            throw new IllegalArgumentException("Invalid order ID");
        }
    }

    public static OrderId of(Long id) {
        return new OrderId(id);
    }

    public static OrderId generate() {
        return new OrderId(generateId());  // Your ID generation logic
    }
}

public record CustomerId(Long id) {
    public CustomerId {
        if (id == null || id < 0) {
            throw new IllegalArgumentException("Invalid customer ID");
        }
    }
}

public record ProductId(Long id) {
    public ProductId {
        if (id == null || id < 0) {
            throw new IllegalArgumentException("Invalid product ID");
        }
    }
}
```

**Usage:**
```java
// ❌ Before - all Longs, easy to mix up
void processOrder(Long orderId, Long customerId, Long productId) {
    // processOrder(customerId, orderId, productId);  // Compiles! Wrong order!
}

// ✅ After - type-safe
void processOrder(OrderId orderId, CustomerId customerId, ProductId productId) {
    // processOrder(customerId, orderId, productId);  // ❌ Compiler error!
}
```

### 2. Constrained String Value Object

Wrapping strings with validation.

```java
public record OrderNumber(@JsonValue String value) {

    @JsonCreator
    public OrderNumber {
        if (value == null || value.trim().isEmpty()) {
            throw new IllegalArgumentException("Order number cannot be empty");
        }
        // Optional: add format validation
        if (!value.matches("^ORD-\\d{8}$")) {
            throw new IllegalArgumentException("Invalid order number format");
        }
    }

    public static OrderNumber of(String value) {
        return new OrderNumber(value);
    }

    public static OrderNumber generate() {
        return new OrderNumber("ORD-" + System.currentTimeMillis());
    }
}
```

**Usage:**
```java
// ❌ Before
String orderNum = "";  // Empty allowed!
String orderNum = "invalid";  // Any format allowed!

// ✅ After
// OrderNumber orderNum = OrderNumber.of("");  // ❌ Exception!
// OrderNumber orderNum = OrderNumber.of("invalid");  // ❌ Exception!
OrderNumber orderNum = OrderNumber.generate();  // ✅ Valid
```

### 3. Email Address Value Object

```java
public record EmailAddress(@JsonValue String value) {

    private static final Pattern EMAIL_PATTERN =
        Pattern.compile("^[A-Za-z0-9+_.-]+@(.+)$");

    @JsonCreator
    public EmailAddress {
        if (value == null || !EMAIL_PATTERN.matcher(value).matches()) {
            throw new IllegalArgumentException("Invalid email address: " + value);
        }
    }

    public static EmailAddress of(String value) {
        return new EmailAddress(value);
    }

    public String domain() {
        return value.substring(value.indexOf('@') + 1);
    }

    public String localPart() {
        return value.substring(0, value.indexOf('@'));
    }
}
```

### 4. Quantity Value Object with Business Logic

```java
public record Quantity(@JsonValue Integer value) {

    public static final Quantity ZERO = new Quantity(0);

    @JsonCreator
    public Quantity {
        if (value == null || value < 0) {
            throw new IllegalArgumentException("Quantity cannot be negative");
        }
        if (value > 10000) {
            throw new IllegalArgumentException("Quantity cannot exceed 10,000");
        }
    }

    public static Quantity of(Integer value) {
        return new Quantity(value);
    }

    public boolean isZero() {
        return value == 0;
    }

    public boolean isPositive() {
        return value > 0;
    }

    public Quantity add(Quantity other) {
        return new Quantity(this.value + other.value);
    }

    public Quantity subtract(Quantity other) {
        int result = this.value - other.value;
        if (result < 0) {
            throw new IllegalArgumentException("Cannot have negative quantity");
        }
        return new Quantity(result);
    }
}
```

**Usage:**
```java
// ❌ Before
Integer qty1 = 5;
Integer qty2 = 3;
Integer total = qty1 + qty2;  // Just numbers, no domain meaning

// ✅ After
Quantity qty1 = Quantity.of(5);
Quantity qty2 = Quantity.of(3);
Quantity total = qty1.add(qty2);  // Domain operation
if (total.isPositive()) { ... }
```

### 5. Money Value Object

```java
public record Money(
    @JsonValue BigDecimal amount,
    Currency currency) {

    public static final Money ZERO_USD = Money.usd(BigDecimal.ZERO);

    public Money {
        if (amount == null) {
            throw new IllegalArgumentException("Amount cannot be null");
        }
        if (amount.compareTo(BigDecimal.ZERO) < 0) {
            throw new IllegalArgumentException("Amount cannot be negative");
        }
        if (currency == null) {
            throw new IllegalArgumentException("Currency cannot be null");
        }
    }

    public static Money of(BigDecimal amount, Currency currency) {
        return new Money(amount, currency);
    }

    public static Money usd(BigDecimal amount) {
        return new Money(amount, Currency.getInstance("USD"));
    }

    public static Money eur(BigDecimal amount) {
        return new Money(amount, Currency.getInstance("EUR"));
    }

    public boolean isFree() {
        return amount.compareTo(BigDecimal.ZERO) == 0;
    }

    public Money add(Money other) {
        ensureSameCurrency(other);
        return new Money(amount.add(other.amount), currency);
    }

    public Money subtract(Money other) {
        ensureSameCurrency(other);
        BigDecimal result = amount.subtract(other.amount);
        if (result.compareTo(BigDecimal.ZERO) < 0) {
            throw new IllegalArgumentException("Cannot have negative money");
        }
        return new Money(result, currency);
    }

    public Money multiply(int multiplier) {
        return new Money(
            amount.multiply(BigDecimal.valueOf(multiplier)),
            currency
        );
    }

    public Money multiply(BigDecimal multiplier) {
        return new Money(amount.multiply(multiplier), currency);
    }

    public boolean isGreaterThan(Money other) {
        ensureSameCurrency(other);
        return amount.compareTo(other.amount) > 0;
    }

    public boolean isLessThan(Money other) {
        ensureSameCurrency(other);
        return amount.compareTo(other.amount) < 0;
    }

    private void ensureSameCurrency(Money other) {
        if (!currency.equals(other.currency)) {
            throw new IllegalArgumentException(
                "Cannot operate on different currencies: " +
                currency.getCurrencyCode() + " vs " + other.currency.getCurrencyCode()
            );
        }
    }

    public String format() {
        return currency.getSymbol() +
               amount.setScale(2, RoundingMode.HALF_UP).toString();
    }
}
```

**Usage:**
```java
// ❌ Before
BigDecimal price = new BigDecimal("19.99");
BigDecimal total = price.multiply(new BigDecimal(5));
// What currency? Can add different currencies by mistake!

// ✅ After
Money price = Money.usd(new BigDecimal("19.99"));
Money total = price.multiply(5);
if (total.isGreaterThan(Money.usd(new BigDecimal("100")))) {
    applyDiscount();
}
System.out.println(total.format());  // $99.95
```

### 6. Date Range Value Object

```java
public record DateRange(
    LocalDate startDate,
    LocalDate endDate) {

    public DateRange {
        if (startDate == null || endDate == null) {
            throw new IllegalArgumentException("Dates cannot be null");
        }
        // ✅ BUSINESS RULE: end must be after or equal to start
        if (endDate.isBefore(startDate)) {
            throw new IllegalArgumentException(
                "End date cannot be before start date");
        }
    }

    public static DateRange of(LocalDate startDate, LocalDate endDate) {
        return new DateRange(startDate, endDate);
    }

    public static DateRange ofDays(LocalDate startDate, int days) {
        return new DateRange(startDate, startDate.plusDays(days));
    }

    public boolean contains(LocalDate date) {
        return !date.isBefore(startDate) && !date.isAfter(endDate);
    }

    public long durationInDays() {
        return ChronoUnit.DAYS.between(startDate, endDate);
    }

    public boolean overlaps(DateRange other) {
        return !endDate.isBefore(other.startDate) &&
               !other.endDate.isBefore(startDate);
    }

    public boolean isCurrentlyActive() {
        LocalDate today = LocalDate.now();
        return contains(today);
    }
}
```

**Usage:**
```java
// ❌ Before - separate fields, no validation
reservation.setStartDate(LocalDate.of(2024, 12, 31));
reservation.setEndDate(LocalDate.of(2024, 1, 1));  // ❌ Before start! No error!

// Must validate everywhere:
if (reservation.getEndDate().isBefore(reservation.getStartDate())) {
    throw new IllegalArgumentException("Invalid range");
}

// ✅ After - DateRange VO
// DateRange range = DateRange.of(
//     LocalDate.of(2024, 12, 31),
//     LocalDate.of(2024, 1, 1)  // ❌ Exception! Can't create invalid
// );

DateRange range = DateRange.of(
    LocalDate.of(2024, 1, 1),
    LocalDate.of(2024, 12, 31)
);
if (range.contains(LocalDate.now())) {
    // Currently active
}
```

### 7. Address Value Object

```java
@Embeddable
public record Address(
    @Column(name = "street")
    @NotBlank(message = "Street is required")
    String street,

    @Column(name = "city")
    @NotBlank(message = "City is required")
    String city,

    @Column(name = "state")
    @Size(min = 2, max = 2, message = "State must be 2 characters")
    String state,

    @Column(name = "zip_code")
    @Pattern(regexp = "\\d{5}(-\\d{4})?", message = "Invalid ZIP code")
    String zipCode
) {

    @JsonCreator(mode = JsonCreator.Mode.PROPERTIES)
    public Address {
        if (street == null || city == null || state == null || zipCode == null) {
            throw new IllegalArgumentException("All address fields are required");
        }
    }

    public static Address of(String street, String city, String state, String zipCode) {
        return new Address(street, city, state, zipCode);
    }

    public String fullAddress() {
        return street + ", " + city + ", " + state + " " + zipCode;
    }
}
```

### 8. Percentage Value Object

```java
public record Percentage(@JsonValue BigDecimal value) {

    public Percentage {
        if (value == null) {
            throw new IllegalArgumentException("Percentage cannot be null");
        }
        if (value.compareTo(BigDecimal.ZERO) < 0 ||
            value.compareTo(new BigDecimal("100")) > 0) {
            throw new IllegalArgumentException("Percentage must be between 0 and 100");
        }
    }

    public static Percentage of(BigDecimal value) {
        return new Percentage(value);
    }

    public static Percentage of(int value) {
        return new Percentage(BigDecimal.valueOf(value));
    }

    public BigDecimal asDecimal() {
        return value.divide(new BigDecimal("100"), 4, RoundingMode.HALF_UP);
    }

    public Money applyTo(Money amount) {
        BigDecimal result = amount.amount().multiply(asDecimal());
        return Money.of(result, amount.currency());
    }

    public String format() {
        return value.setScale(2, RoundingMode.HALF_UP) + "%";
    }
}
```

**Usage:**
```java
// ✅ Calculate discount
Money price = Money.usd(new BigDecimal("100"));
Percentage discount = Percentage.of(15);  // 15%
Money discountAmount = discount.applyTo(price);  // $15.00
Money finalPrice = price.subtract(discountAmount);  // $85.00
```

---

## Embedding Value Objects

### In JPA Entities

```java
@Entity
@Table(name = "customers")
public class Customer {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // Simple embedded VO
    @Embedded
    @AttributeOverride(name = "value", column = @Column(name = "email"))
    private EmailAddress email;

    // Embedded VO with multiple fields
    @Embedded
    private Address billingAddress;

    // Multiple instances of same VO type
    @Embedded
    @AttributeOverrides({
        @AttributeOverride(name = "street", column = @Column(name = "shipping_street")),
        @AttributeOverride(name = "city", column = @Column(name = "shipping_city")),
        @AttributeOverride(name = "state", column = @Column(name = "shipping_state")),
        @AttributeOverride(name = "zipCode", column = @Column(name = "shipping_zip"))
    })
    private Address shippingAddress;

    // Embedded VO with currency
    @Embedded
    @AttributeOverrides({
        @AttributeOverride(name = "amount", column = @Column(name = "credit_limit_amount")),
        @AttributeOverride(name = "currency", column = @Column(name = "credit_limit_currency"))
    })
    private Money creditLimit;
}
```

### Using EmbeddedId

```java
@Embeddable
public record OrderId(@Column(name = "id") Long id) implements Serializable {
    public OrderId {
        if (id == null || id < 0) {
            throw new IllegalArgumentException("Invalid order ID");
        }
    }

    public static OrderId of(Long id) {
        return new OrderId(id);
    }

    public static OrderId generate() {
        return new OrderId(generateId());
    }
}

@Entity
@Table(name = "orders")
public class Order {

    @EmbeddedId
    private OrderId id;

    @Embedded
    private OrderNumber orderNumber;

    @Embedded
    private Money total;

    // Constructor
    private Order(OrderId id, OrderNumber orderNumber, Money total) {
        this.id = id;
        this.orderNumber = orderNumber;
        this.total = total;
    }

    // Factory method
    public static Order createNew(Money total) {
        return new Order(
            OrderId.generate(),
            OrderNumber.generate(),
            total
        );
    }

    // Getters only, no setters
    public OrderId getId() { return id; }
    public OrderNumber getOrderNumber() { return orderNumber; }
    public Money getTotal() { return total; }
}
```

---

## Spring Integration

### 1. Spring Converters for REST Endpoints

```java
@Component
public class StringToOrderNumberConverter implements Converter<String, OrderNumber> {
    @Override
    public OrderNumber convert(String source) {
        return OrderNumber.of(source);
    }
}

@Component
public class StringToEmailAddressConverter implements Converter<String, EmailAddress> {
    @Override
    public EmailAddress convert(String source) {
        return EmailAddress.of(source);
    }
}

@Component
public class StringToMoneyConverter implements Converter<String, Money> {
    @Override
    public Money convert(String source) {
        // Parse format: "19.99 USD"
        String[] parts = source.split(" ");
        return Money.of(
            new BigDecimal(parts[0]),
            Currency.getInstance(parts[1])
        );
    }
}
```

**Usage in Controllers:**

```java
@RestController
@RequestMapping("/orders")
public class OrderController {

    @GetMapping("/{orderNumber}")
    public OrderDTO getOrder(@PathVariable OrderNumber orderNumber) {
        // String "ORD-12345" automatically converted to OrderNumber!
        return orderService.findByOrderNumber(orderNumber);
    }

    @PostMapping
    public OrderDTO createOrder(@RequestBody CreateOrderRequest request) {
        // request.email() is already EmailAddress
        // request.total() is already Money
        return orderService.createOrder(request);
    }
}

public record CreateOrderRequest(
    EmailAddress email,      // Automatically converted from JSON string
    Money total,             // Automatically converted
    Quantity quantity        // Automatically converted
) {}
```

### 2. JPA AttributeConverter

For VOs that need custom database mapping:

```java
@Converter(autoApply = true)
public class MoneyConverter implements AttributeConverter<Money, String> {

    @Override
    public String convertToDatabaseColumn(Money money) {
        if (money == null) {
            return null;
        }
        return money.amount() + "|" + money.currency().getCurrencyCode();
    }

    @Override
    public Money convertToEntityAttribute(String dbData) {
        if (dbData == null || dbData.isEmpty()) {
            return null;
        }
        String[] parts = dbData.split("\\|");
        return Money.of(
            new BigDecimal(parts[0]),
            Currency.getInstance(parts[1])
        );
    }
}
```

### 3. Jackson Serialization

```java
// Using @JsonValue and @JsonCreator
public record OrderNumber(@JsonValue String value) {

    @JsonCreator
    public OrderNumber {
        if (value == null || value.trim().isEmpty()) {
            throw new IllegalArgumentException("Order number cannot be empty");
        }
    }
}

// Custom serializer for complex cases
public class MoneySerializer extends JsonSerializer<Money> {
    @Override
    public void serialize(Money value, JsonGenerator gen, SerializerProvider serializers)
            throws IOException {
        gen.writeStartObject();
        gen.writeNumberField("amount", value.amount());
        gen.writeStringField("currency", value.currency().getCurrencyCode());
        gen.writeEndObject();
    }
}

public class MoneyDeserializer extends JsonDeserializer<Money> {
    @Override
    public Money deserialize(JsonParser p, DeserializationContext ctxt)
            throws IOException {
        JsonNode node = p.getCodec().readTree(p);
        BigDecimal amount = new BigDecimal(node.get("amount").asText());
        Currency currency = Currency.getInstance(node.get("currency").asText());
        return Money.of(amount, currency);
    }
}

// Apply custom serializers
@JsonSerialize(using = MoneySerializer.class)
@JsonDeserialize(using = MoneyDeserializer.class)
public record Money(BigDecimal amount, Currency currency) { ... }
```

---

## Best Practices

### 1. Make Them Immutable

```java
// ✅ GOOD - Using record (immutable by default)
public record OrderNumber(String value) { ... }

// ✅ GOOD - Using final fields
public final class OrderNumber {
    private final String value;

    public OrderNumber(String value) {
        this.value = value;
    }

    public String value() { return value; }
}

// ❌ BAD - Mutable
public class OrderNumber {
    private String value;  // Not final

    public void setValue(String value) {  // Setter!
        this.value = value;
    }
}
```

### 2. Validate in Constructor

```java
// ✅ GOOD - Fail fast
public record EmailAddress(String value) {
    public EmailAddress {
        if (value == null || !isValid(value)) {
            throw new IllegalArgumentException("Invalid email");
        }
    }
}

// ❌ BAD - No validation
public record EmailAddress(String value) {}
```

### 3. Provide Factory Methods

```java
// ✅ GOOD - Clear intent
public record Money(BigDecimal amount, Currency currency) {
    public static Money of(BigDecimal amount, Currency currency) {
        return new Money(amount, currency);
    }

    public static Money usd(BigDecimal amount) {
        return new Money(amount, Currency.getInstance("USD"));
    }

    public static Money zero(Currency currency) {
        return new Money(BigDecimal.ZERO, currency);
    }
}

// Usage
Money price = Money.usd(new BigDecimal("19.99"));  // Clear
Money zero = Money.zero(Currency.getInstance("USD"));  // Clear
```

### 4. Implement equals/hashCode Based on Value

```java
// ✅ Records do this automatically
public record OrderNumber(String value) {}

// ✅ Manual implementation if not using records
@Override
public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof OrderNumber other)) return false;
    return Objects.equals(value, other.value);
}

@Override
public int hashCode() {
    return Objects.hash(value);
}
```

### 5. Add Domain Behavior

```java
// ✅ GOOD - Rich behavior
public record Money(BigDecimal amount, Currency currency) {
    public Money add(Money other) { ... }
    public Money multiply(int quantity) { ... }
    public boolean isGreaterThan(Money other) { ... }
    public boolean isFree() {
        return amount.compareTo(BigDecimal.ZERO) == 0;
    }
}

// ❌ BAD - Just data
public record Money(BigDecimal amount, Currency currency) {}
```

### 6. Use Meaningful Names

```java
// ✅ GOOD
public record OrderNumber(String value) {}
public record EmailAddress(String value) {}
public record Money(BigDecimal amount, Currency currency) {}

// ❌ BAD
public record OrderNumberVO(String value) {}  // Don't suffix with VO
public record Email(String value) {}          // Too generic
public record Price(BigDecimal amount) {}     // Missing currency context
```

### 7. Keep Them Simple

```java
// ✅ GOOD - Single responsibility
public record OrderNumber(String value) {
    // Just validation and simple formatting
}

// ❌ BAD - Too complex
public record OrderNumber(String value, LocalDateTime createdAt, String createdBy) {
    // Too much responsibility - this should be an entity!
}
```

### 8. Make Invalid States Unrepresentable

```java
// ✅ GOOD - Can't create invalid DateRange
public record DateRange(LocalDate startDate, LocalDate endDate) {
    public DateRange {
        if (endDate.isBefore(startDate)) {
            throw new IllegalArgumentException("End before start");
        }
    }
}

// ❌ BAD - Can be in invalid state
public record DateRange(LocalDate startDate, LocalDate endDate) {}
```

---

## Common Patterns Summary

| Pattern | Example | Use When |
|---------|---------|----------|
| **Identity VO** | `OrderId`, `CustomerId` | Wrapping database IDs for type safety |
| **Constrained String** | `OrderNumber`, `EmailAddress`, `PhoneNumber` | Strings with validation rules |
| **Constrained Number** | `Quantity`, `Percentage` | Numbers with business constraints |
| **Money** | `Money(amount, currency)` | Financial calculations |
| **Date Range** | `DateRange(start, end)` | Period/duration with validation |
| **Composite VO** | `Address`, `FullName` | Grouping related primitives |
| **Measurement** | `Weight`, `Temperature` | Values with units |

---

## Further Reading

- [Value Object - Martin Fowler](https://martinfowler.com/bliki/ValueObject.html)
- [Domain-Driven Design - Eric Evans](https://www.domainlanguage.com/ddd/)
- [architecture-patterns.md](architecture-patterns.md) - Architecture pattern comparisons
- [domain-modeling.md](domain-modeling.md) - Anemic vs Rich domain models

---

**Remember:** Value Objects are the foundation of a rich domain model. Start with high-risk primitives (Money, IDs, Quantities) and expand as needed. They reduce bugs, improve type safety, and make your code more expressive and maintainable.
