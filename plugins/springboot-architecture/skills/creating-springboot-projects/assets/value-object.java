package {{PACKAGE}}.{{MODULE}}.domain.vo;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;
import jakarta.persistence.Embeddable;

/**
 * Value Object template - immutable, self-validating, type-safe.
 *
 * Replace:
 *   {{PACKAGE}} - base package (e.g., com.example)
 *   {{MODULE}} - module name (e.g., products)
 *   {{NAME}} - VO name (e.g., ProductSKU, Email, Price)
 *   {{TYPE}} - wrapped type (e.g., String, Long, BigDecimal)
 *   {{FIELD}} - field name (e.g., code, value, amount)
 *
 * @Embeddable lets this record be used in JPA entities via @Embedded /
 * @EmbeddedId — required by Jakarta Persistence 3.2 §2.7 even though records
 * are otherwise the standard embeddable shape on Hibernate 6.2+. Drop the
 * annotation (and the import) if this VO will never be stored by JPA.
 */
@Embeddable
public record {{NAME}}(@JsonValue {{TYPE}} {{FIELD}}) {

    // DELEGATING mode pairs with @JsonValue on the single component: Jackson
    // deserializes the whole JSON scalar (e.g. "ABC-123") and hands it to the
    // canonical/compact constructor, instead of expecting a JSON object with
    // a {{FIELD}} property. Drop @JsonCreator entirely if Jackson 2.12+ /
    // Jackson 3 record auto-detection is enough for your stack.
    @JsonCreator(mode = JsonCreator.Mode.DELEGATING)
    public {{NAME}} {
        // Validation - fail fast at construction
        if ({{FIELD}} == null) {
            throw new IllegalArgumentException("{{NAME}} cannot be null");
        }
        // Add domain-specific validation here
        // Example for SKU: if (!SKU_PATTERN.matcher(code).matches()) { throw... }
        // Example for Price: if (amount.compareTo(BigDecimal.ZERO) < 0) { throw... }
    }

    // Factory method
    public static {{NAME}} of({{TYPE}} {{FIELD}}) {
        return new {{NAME}}({{FIELD}});
    }

    // Optional: generation method for IDs/codes
    // public static {{NAME}} generate() {
    //     return new {{NAME}}(TSIDUtil.generateTsidString());
    // }
}

// ============================================================
// EXAMPLES
// ============================================================

// --- Simple String VO ---
// public record ProductSKU(@JsonValue String code) {
//     @JsonCreator
//     public ProductSKU {
//         if (code == null || code.isBlank()) {
//             throw new IllegalArgumentException("SKU cannot be null or blank");
//         }
//     }
//     public static ProductSKU of(String code) { return new ProductSKU(code); }
// }

// --- Email with regex validation ---
// public record Email(@JsonValue String value) {
//     private static final Pattern EMAIL_PATTERN =
//         Pattern.compile("^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$");
//
//     @JsonCreator
//     public Email {
//         if (value == null || !EMAIL_PATTERN.matcher(value).matches()) {
//             throw new IllegalArgumentException("Invalid email: " + value);
//         }
//     }
// }

// --- Price with BigDecimal ---
// public record Price(@JsonValue BigDecimal amount) {
//     public static final Price ZERO = new Price(BigDecimal.ZERO);
//
//     @JsonCreator
//     public Price {
//         if (amount == null || amount.compareTo(BigDecimal.ZERO) < 0) {
//             throw new IllegalArgumentException("Price cannot be negative");
//         }
//     }
//     public boolean isFree() { return amount.compareTo(BigDecimal.ZERO) == 0; }
// }

// --- ID with TSID generation ---
// public record ProductId(@JsonValue Long id) {
//     @JsonCreator
//     public ProductId {
//         if (id == null || id < 0) {
//             throw new IllegalArgumentException("Invalid ID");
//         }
//     }
//     public static ProductId generate() {
//         return new ProductId(TSIDUtil.generateTsidLong());
//     }
// }
