package {{PACKAGE}}.{{MODULE}}.domain;

import {{PACKAGE}}.{{MODULE}}.domain.vo.*;
import {{PACKAGE}}.shared.BaseEntity;
import jakarta.persistence.*;

/**
 * Rich Entity template - aggregate root with behavior.
 *
 * Key principles:
 * - Use @EmbeddedId with Value Object for ID
 * - Embed Value Objects with @AttributeOverride
 * - Factory methods for creation (not public constructors)
 * - Business logic methods (not just getters/setters)
 * - Protected no-arg constructor for JPA
 * - @Version for optimistic locking
 */
@Entity
@Table(name = "{{TABLE_NAME}}")
class {{NAME}}Entity extends BaseEntity {

    @EmbeddedId
    @AttributeOverride(name = "id", column = @Column(name = "id"))
    private {{NAME}}Id id;

    @Embedded
    @AttributeOverride(name = "code", column = @Column(name = "code", unique = true))
    private {{NAME}}Code code;

    // Embed composite Value Objects
    @Embedded
    @AttributeOverrides({
        @AttributeOverride(name = "name", column = @Column(name = "name")),
        @AttributeOverride(name = "description", column = @Column(name = "description"))
    })
    private {{NAME}}Details details;

    @Enumerated(EnumType.STRING)
    @Column(name = "status")
    private {{NAME}}Status status;

    @Version
    private int version;

    // Protected constructor for JPA
    protected {{NAME}}Entity() {}

    // Private constructor - use factory method
    private {{NAME}}Entity({{NAME}}Id id, {{NAME}}Code code,
                           {{NAME}}Details details, {{NAME}}Status status) {
        this.id = id;
        this.code = code;
        this.details = details;
        this.status = status;
    }

    // ==================== FACTORY METHODS ====================

    public static {{NAME}}Entity create({{NAME}}Details details) {
        return new {{NAME}}Entity(
            {{NAME}}Id.generate(),
            {{NAME}}Code.generate(),
            details,
            {{NAME}}Status.DRAFT
        );
    }

    // ==================== BUSINESS LOGIC ====================

    public boolean isActive() {
        return status == {{NAME}}Status.ACTIVE;
    }

    public void activate() {
        if (status == {{NAME}}Status.ACTIVE) {
            return; // Idempotent
        }
        // Add business rule checks here
        this.status = {{NAME}}Status.ACTIVE;
    }

    public void deactivate() {
        if (status == {{NAME}}Status.INACTIVE) {
            return; // Idempotent
        }
        this.status = {{NAME}}Status.INACTIVE;
    }

    // ==================== GETTERS ONLY - NO SETTERS ====================

    public {{NAME}}Id getId() { return id; }
    public {{NAME}}Code getCode() { return code; }
    public {{NAME}}Details getDetails() { return details; }
    public {{NAME}}Status getStatus() { return status; }
}

// ============================================================
// EXAMPLE: ProductEntity
// ============================================================

// @Entity
// @Table(name = "products")
// class ProductEntity extends BaseEntity {
//
//     @EmbeddedId
//     private ProductId id;
//
//     @Embedded
//     @AttributeOverride(name = "code", column = @Column(name = "sku", unique = true))
//     private ProductSKU sku;
//
//     @Embedded
//     private ProductDetails details;
//
//     @Embedded
//     @AttributeOverride(name = "amount", column = @Column(name = "price"))
//     private Price price;
//
//     @Embedded
//     @AttributeOverride(name = "value", column = @Column(name = "quantity"))
//     private Quantity quantity;
//
//     @Enumerated(EnumType.STRING)
//     private ProductStatus status;
//
//     @Version
//     private int version;
//
//     protected ProductEntity() {}
//
//     public static ProductEntity create(ProductSKU sku, ProductDetails details,
//                                        Price price, Quantity quantity) {
//         return new ProductEntity(ProductId.generate(), sku, details,
//                                  price, quantity, ProductStatus.DRAFT);
//     }
//
//     public boolean isInStock() {
//         return quantity.value() > 0;
//     }
//
//     public void adjustPrice(Price newPrice) {
//         if (newPrice.amount().compareTo(BigDecimal.ZERO) < 0) {
//             throw new InvalidPriceException("Price cannot be negative");
//         }
//         this.price = newPrice;
//     }
//
//     public void decreaseStock(int amount) {
//         if (quantity.value() < amount) {
//             throw new InsufficientStockException("Not enough stock");
//         }
//         this.quantity = Quantity.of(quantity.value() - amount);
//     }
// }
