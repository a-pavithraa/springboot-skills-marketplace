# Value Objects: Review Rules

A value object (VO) is an immutable, self-validating type for a domain concept (`OrderNumber`, `Money`, `EmailAddress`). It has no identity. Two VOs with the same values are equal.

Full template: `../../creating-springboot-projects/assets/value-object.java`. Converter template: `../../creating-springboot-projects/assets/spring-converter.java`.

## Contents

1. [Rules](#rules)
2. [Single-value and multi-value VOs](#single-value-and-multi-value-vos)
3. [JPA](#jpa)
4. [Spring MVC and Jackson 3](#spring-mvc-and-jackson-3)
5. [Review checklist](#review-checklist)

---

## Rules

| Rule | Flag this |
|------|-----------|
| Immutable | Setters, non-final fields. Use a `record` or a final class with final fields |
| Validate in the constructor | A VO that accepts any value; the same checks repeated in services |
| Factory methods | Optional: `of(...)`, `generate()`, `zero(currency)` make intent clear |
| Equality by value | Hand-written `equals` that compares an ID. Records do value equality for free |
| Domain behavior belongs on the VO | Utility classes like `MoneyUtils.add(a, b)` |
| Meaningful names | `OrderNumberVO` (no suffix), `Email` when other emails exist, `Price(BigDecimal)` without currency |
| Keep it small | A VO with `createdAt`/`createdBy`: that is an entity |
| Make invalid states impossible | Separate `start`/`end` fields that can be reversed. Use `DateRange` that rejects `end < start` |

Typical VOs: typed IDs (`OrderId`, `CustomerId`, so arguments cannot be swapped), constrained strings (`OrderNumber`, `EmailAddress`), `Money` (amount + currency), `Quantity`, `Percentage` (0-100), `DateRange`, `Address`.

**`BigDecimal` equality trap:** records use `BigDecimal.equals`, which compares scale. `new BigDecimal("19.99")` and `new BigDecimal("19.990")` are NOT equal. In `Money`, normalize the scale in the constructor (`amount.setScale(2, RoundingMode.HALF_EVEN)`) or override `equals`/`hashCode` with `compareTo`. Use `compareTo`, not `equals`, for comparisons.

**`Money` rules:** reject a null amount or currency; refuse to add, subtract, or compare different currencies; decide whether negative amounts are allowed (refunds) and enforce it.

---

## Single-value and multi-value VOs

```java
// Single value: JSON is a plain string ("ORD-1")
@Embeddable
public record OrderNumber(@JsonValue String value) {
    @JsonCreator
    public OrderNumber {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException("Order number cannot be empty");
        }
    }
}

// Two values: JSON is an object {"amount": 19.99, "currency": "USD"} by default
@Embeddable
public record Money(BigDecimal amount, Currency currency) {
    public Money {
        Objects.requireNonNull(amount, "amount");
        Objects.requireNonNull(currency, "currency");
        amount = amount.setScale(2, RoundingMode.HALF_EVEN);  // fixed scale keeps equals() sane
    }
    public Money add(Money other) {
        if (!currency.equals(other.currency)) {
            throw new IllegalArgumentException("Currency mismatch");
        }
        return new Money(amount.add(other.amount), currency);
    }
}
```

Do NOT put `@JsonValue` on one component of a multi-value VO. Jackson then writes only that component and drops the others.

---

## JPA

- Use `@Embedded` fields. The VO type needs `@Embeddable`, also when it is a record.
- Records as `@Embeddable` and `@EmbeddedId` need Hibernate 6.2+. Boot 4 ships Hibernate 7, so they work.
- For a typed ID as primary key: `@EmbeddedId private OrderId id;` with `@Embeddable record OrderId(Long id) implements Serializable`.
- Two fields of the same VO type (billing and shipping `Address`) need `@AttributeOverrides` with distinct column names.
- For a single-value VO, name the column with `@AttributeOverride(name = "value", column = @Column(name = "email"))`.
- Use a JPA `AttributeConverter<Money, String>` only when the VO must fit one column. Prefer two columns for `Money`, so the database can sort and sum amounts.

Tooling caveats:

- QueryDSL APT does not accept `@Embeddable` records ([querydsl#3695](https://github.com/querydsl/querydsl/issues/3695)). With QueryDSL, use a final class with `private final` fields instead of a record.
- MapStruct sometimes needs explicit `@Mapping(target = ..., source = ...)` for nested embeddable records. Check the generated code.

---

## Spring MVC and Jackson 3

**Spring `Converter<String, VO>` applies only to `@PathVariable`, `@RequestParam`, and `@RequestHeader`.** It does NOT apply to JSON request bodies. Jackson handles bodies.

| Input | Mechanism |
|-------|-----------|
| `@PathVariable OrderNumber number` | `@Component class StringToOrderNumberConverter implements Converter<String, OrderNumber>` |
| JSON body field of a single-value VO | `@JsonValue` on the component + `@JsonCreator` on the constructor |
| JSON body field of a multi-value VO | Default record mapping (JSON object), or a custom serializer for another shape |

A custom serializer on Boot 4 uses Jackson 3 types. The Jackson 2 classes (`JsonSerializer`, `JsonDeserializer`, `SerializerProvider`) do not exist in Jackson 3:

```java
import tools.jackson.core.JsonGenerator;
import tools.jackson.core.JsonParser;
import tools.jackson.databind.*;
import tools.jackson.databind.annotation.JsonDeserialize;
import tools.jackson.databind.annotation.JsonSerialize;

// Writes Money as "19.99 USD"
class MoneySerializer extends ValueSerializer<Money> {
    @Override
    public void serialize(Money m, JsonGenerator gen, SerializationContext ctxt) {
        gen.writeString(m.amount().toPlainString() + " " + m.currency().getCurrencyCode());
    }
}

class MoneyDeserializer extends ValueDeserializer<Money> {
    @Override
    public Money deserialize(JsonParser p, DeserializationContext ctxt) {
        String[] parts = p.getValueAsString().split(" ");
        return new Money(new BigDecimal(parts[0]), Currency.getInstance(parts[1]));
    }
}

@JsonSerialize(using = MoneySerializer.class)
@JsonDeserialize(using = MoneyDeserializer.class)
public record Money(BigDecimal amount, Currency currency) { /* ... */ }
```

Jackson 3 methods do not throw `IOException`. Errors are unchecked `JacksonException`. A VO constructor that throws during deserialization surfaces as `ValueInstantiationException`. Map it to a 400 response in the exception handler.

---

## Review checklist

- [ ] Domain concepts use VOs, not raw `String`/`Long`/`BigDecimal`, where mixing them up is a real risk
- [ ] VOs are immutable and validate in the constructor
- [ ] `Money` handles currency and `BigDecimal` scale; comparisons use `compareTo`
- [ ] VOs stored by JPA are `@Embeddable`; repeated VO fields have attribute overrides
- [ ] Path and query parameters use Spring converters; JSON uses `@JsonValue`/`@JsonCreator` or Jackson 3 serializers
- [ ] No Jackson 2 serializer classes in a Boot 4 codebase
- [ ] Deserialization failures from VO validation return 400, not 500
