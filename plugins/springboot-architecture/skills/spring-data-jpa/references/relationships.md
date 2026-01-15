# JPA Relationships Reference

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

## @ManyToMany → Join Entity (Required)

**WRONG:**
```java
@ManyToMany
@JoinTable(name = "student_course", ...)
private Set<Course> courses;
```

**RIGHT - Use Join Entity:**
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

**Always use LAZY:**
```java
@ManyToOne(fetch = FetchType.LAZY)  // Default, explicit
@JoinColumn(name = "category_id")
private Category category;
```

**Never use EAGER:**
```java
@ManyToOne(fetch = FetchType.EAGER)  // ❌ Avoid!
private Brand brand;
```

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
4. **Never @ManyToMany** - Create join entity
5. **Use IDs for loose coupling** - Between modules
6. **Helper methods for bidirectional** - Maintain both sides
7. **CASCADE carefully** - Understand propagation
8. **Queries over mappings** - More explicit and maintainable
