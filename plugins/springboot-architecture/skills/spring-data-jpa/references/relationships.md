# JPA Relationships Reference

## Table of Contents

1. [@ManyToOne (Recommended)](#manytoone-recommended)
2. [@OneToOne (Use Sparingly)](#onetoone-use-sparingly)
3. [@OneToMany (Avoid When Possible)](#onetomany-avoid-when-possible)
4. [@ManyToMany: Prefer an explicit Join Entity](#manytomany-prefer-an-explicit-join-entity)
5. [@ElementCollection (Value Types)](#elementcollection-value-types)
6. [Cascade Types](#cascade-types)
7. [Fetch Strategies](#fetch-strategies)
8. [Best Practices Summary](#best-practices-summary)

---

## @ManyToOne (Recommended)

Most common and efficient relationship type.

```java
@Entity
@Table(name = "order_items")
public class OrderItem {

    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE)
    private Long id;

    // RECOMMENDED: Entity reference
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "order_id", nullable = false)
    private Order order;

    // ALTERNATIVE: Just store the ID (loose coupling)
    @Column(name = "product_id", nullable = false)
    private Long productId;
}
```

**When to use ID instead of entity:**
- Loose coupling between modules
- Rarely need related entity properties
- Prevents lazy loading issues

## @OneToOne (Use Sparingly)

### Unidirectional (Recommended)

```java
@Entity
@Table(name = "user_profiles")
public class UserProfile {

    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE)
    private Long id;

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id", unique = true, nullable = false)
    private User user;
}
```

### Shared Primary Key (Alternative)

```java
@Entity
@Table(name = "user_profiles")
public class UserProfile {

    @Id
    private Long id;

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @MapsId
    @JoinColumn(name = "id")
    private User user;
}
```

**Avoid bidirectional @OneToOne** - causes N+1 queries even with LAZY.

**Reference:** [Vlad Mihalcea - One-to-One Table Relationships](https://vladmihalcea.com/one-to-one-table-relationships/)

**Analysis (from the article):**
- Shared primary key: child FK equals parent PK to model true one-to-one
- Optional data: separate table enforces NOT NULL pairs without triggers
- Concurrency: splitting reduces optimistic lock conflicts and row blocking
- IO/cache: narrower hot rows reduce dirty page churn

## @OneToMany (Avoid When Possible)

**Better alternative:** Query from many side
```java
List<OrderItem> items = orderItemRepository.findByOrderId(orderId);
```

**If you must use:**
```java
@Entity
@Table(name = "orders")
public class Order {

    @OneToMany(
        mappedBy = "order",
        cascade = CascadeType.ALL,
        orphanRemoval = true,
        fetch = FetchType.LAZY
    )
    private List<OrderItem> items = new ArrayList<>();

    // Helper methods to maintain both sides
    public void addItem(OrderItem item) {
        items.add(item);
        item.setOrder(this);
    }

    public void removeItem(OrderItem item) {
        items.remove(item);
        item.setOrder(null);
    }
}
```

**Only use when:**
- Strong parent-child lifecycle (cascade operations)
- Collection is always small (<20 items)
- Need to modify collection from parent

## @ManyToMany: Prefer an explicit Join Entity

Jakarta Persistence 3.2 defines `@ManyToMany` as a first-class relationship with a `LAZY` default, so this is a design recommendation, not a spec restriction. The plain `@ManyToMany` works — the trade-off is that the join table becomes invisible to your domain.

**Avoid plain `@ManyToMany` when:**
- The relationship has any attribute of its own (enrolment date, status, grade, weight, role on the project, …) — these cannot live on `@ManyToMany`'s implicit join table
- You need lifecycle events on the link itself (audit, soft-delete)
- You need to query the relationship directly (e.g. `find enrollments completed last quarter`)

**Plain `@ManyToMany` is acceptable when:** the link genuinely carries no data and you never need to query it as an entity — e.g. tagging.

```java
// Acceptable: pure tagging, no link attributes ever needed
@ManyToMany
@JoinTable(name = "post_tags", ...)
private Set<Tag> tags;
```

**Prefer an explicit join entity:**
```java
@Entity
@Table(name = "enrollments")
public class Enrollment {

    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "student_id", nullable = false)
    private Student student;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "course_id", nullable = false)
    private Course course;

    // Relationship attributes
    private LocalDate enrolledAt;
    private EnrollmentStatus status;
    private Integer grade;
}
```

**Benefits:**
- Can add attributes (enrolledAt, status, grade)
- Better control and maintainability
- Has its own ID and lifecycle

## @ElementCollection (Value Types)

For collections of primitives or @Embeddable objects:

```java
@Entity
@Table(name = "products")
public class Product {

    @ElementCollection
    @CollectionTable(
        name = "product_tags",
        joinColumns = @JoinColumn(name = "product_id")
    )
    @Column(name = "tag")
    private Set<String> tags = new HashSet<>();

    @ElementCollection
    @CollectionTable(
        name = "product_images",
        joinColumns = @JoinColumn(name = "product_id")
    )
    private List<ProductImage> images = new ArrayList<>();
}

@Embeddable
public class ProductImage {
    private String url;
    private String altText;
    private int displayOrder;
}
```

**Use for:**
- Collections of primitives (String, Integer)
- Collections of @Embeddable objects
- Simple data without its own identity

**NOT for:**
- Entities with their own ID
- Complex objects needing relationships

## Cascade Types

```java
// All operations propagate
@OneToMany(cascade = CascadeType.ALL, orphanRemoval = true)
private List<OrderItem> items;

// Only persist and merge propagate
@ManyToOne(cascade = {CascadeType.PERSIST, CascadeType.MERGE})
private Customer customer;
```

**Types:**
- `PERSIST`: Save parent saves children
- `MERGE`: Merge parent merges children
- `REMOVE`: Delete parent deletes children
- `ALL`: All of the above

**Use carefully** - can cause unexpected deletes!

## Fetch Strategies

**Always set LAZY explicitly on @ManyToOne / @OneToOne:**
```java
@ManyToOne(fetch = FetchType.LAZY)  // ⚠️ JPA default for @ManyToOne is EAGER — always override
@JoinColumn(name = "category_id")
private Category category;
```

**Never use EAGER (and remember it is the default unless you override it):**
```java
@ManyToOne(fetch = FetchType.EAGER)  // ❌ Avoid! Also the silent default if you omit fetch=
private Brand brand;
```

> Per the Jakarta Persistence spec: `@ManyToOne` and `@OneToOne` default to EAGER, while `@OneToMany` and `@ManyToMany` default to LAZY. Most teams want LAZY everywhere — to-one associations must override the default explicitly.

**Use JOIN FETCH in queries instead:**
```java
@Query("""
    SELECT p
    FROM Product p
    JOIN FETCH p.category
    WHERE p.id = :id
    """)
Optional<Product> findByIdWithCategory(@Param("id") Long id);
```

## Best Practices Summary

1. **Prefer @ManyToOne** - Query from many side
2. **Always use LAZY** - Use JOIN FETCH when needed
3. **Avoid bidirectional** - Query instead of mapping
4. **Prefer a join entity over plain @ManyToMany** when the relationship has attributes or needs to be queried (plain `@ManyToMany` itself is part of the JPA spec and fine for pure tagging-style links)
5. **Use IDs for loose coupling** - Between modules
6. **Helper methods for bidirectional** - Maintain both sides
7. **CASCADE carefully** - Understand propagation
8. **Queries over mappings** - More explicit and maintainable
