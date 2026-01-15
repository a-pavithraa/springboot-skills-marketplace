package {{PACKAGE}}.{{MODULE}}.domain;

import jakarta.persistence.*;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * JPA Relationship Patterns - Best practices for associations.
 *
 * Key principles:
 * - Always use FetchType.LAZY
 * - Avoid bidirectional relationships when possible
 * - Use JOIN FETCH in queries instead of EAGER
 * - Prefer @ManyToOne over @OneToMany
 * - Never use @ManyToMany - use join entity
 * - Consider using IDs instead of associations for loose coupling
 */

// ============================================================
// @MANYTOONE - MOST COMMON, RECOMMENDED
// ============================================================

/**
 * @ManyToOne - The most common and recommended relationship.
 *
 * Use when:
 * - Many items belong to one parent
 * - You need to navigate from child to parent
 * - Examples: OrderItem -> Order, Product -> Category
 *
 * Best practices:
 * - ALWAYS use FetchType.LAZY (it's the default)
 * - Use optional = false if relationship is required
 * - Specify @JoinColumn name explicitly
 * - Consider using ID instead of entity reference
 */
@Entity
@Table(name = "order_items")
public class OrderItem {

    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE)
    private Long id;

    /**
     * RECOMMENDED: @ManyToOne with entity reference.
     * Use when you need to access parent properties frequently.
     */
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "order_id", nullable = false)
    private Order order;

    /**
     * ALTERNATIVE: Store only the ID (loose coupling).
     * Use when you rarely need parent properties.
     * Benefits:
     * - No lazy loading issues
     * - Better performance
     * - Clearer boundaries
     */
    @Column(name = "product_id", nullable = false)
    private Long productId;

    private int quantity;
    private java.math.BigDecimal price;

    // Getters and setters
}

/**
 * Parent side - no @OneToMany mapping.
 * Query from the many side instead.
 */
@Entity
@Table(name = "orders")
public class Order {

    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE)
    private Long id;

    private String orderNumber;

    // NO @OneToMany here!
    // Query items like this: orderItemRepository.findByOrderId(orderId)
}

// ============================================================
// @ONETOONE - USE SPARINGLY
// ============================================================

/**
 * @OneToOne - Use only when truly one-to-one.
 *
 * Types:
 * 1. Unidirectional - Only one side has reference
 * 2. Bidirectional - Both sides have reference (avoid)
 *
 * Common mistake: Using @OneToOne when @ManyToOne is better
 */

/**
 * UNIDIRECTIONAL @OneToOne (RECOMMENDED)
 * Only child references parent.
 */
@Entity
@Table(name = "user_profiles")
public class UserProfile {

    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE)
    private Long id;

    /**
     * Foreign key is in this table.
     * Use when profile is optional for user.
     */
    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id", unique = true, nullable = false)
    private User user;

    private String bio;
    private String avatarUrl;
}

/**
 * SHARED PRIMARY KEY @OneToOne (ALTERNATIVE)
 * Profile ID is same as User ID.
 * Use when profile is mandatory and lifecycle is tied to user.
 */
@Entity
@Table(name = "user_profiles_shared_pk")
public class UserProfileSharedPK {

    /**
     * Uses User's ID as its own ID.
     * No separate ID generation needed.
     */
    @Id
    private Long id;

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @MapsId
    @JoinColumn(name = "id")
    private User user;

    private String bio;
}

/**
 * AVOID: Bidirectional @OneToOne
 * Causes N+1 queries even with LAZY.
 */
@Entity
@Table(name = "users")
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE)
    private Long id;

    // AVOID: This always triggers a query
    @OneToOne(mappedBy = "user", fetch = FetchType.LAZY)
    private UserProfile profile;  // Use query instead!
}

// ============================================================
// @ONETOMANY - AVOID IN MOST CASES
// ============================================================

/**
 * @OneToMany - Use only when necessary.
 *
 * Problems:
 * - Performance issues (loads entire collection)
 * - Harder to maintain consistency
 * - Better to query from many side
 *
 * Use when:
 * - Strong parent-child lifecycle (cascade operations)
 * - Collection is always small (< 20 items)
 * - Need to modify collection from parent
 */

/**
 * IF YOU MUST USE @OneToMany:
 * Follow these rules strictly.
 */
@Entity
@Table(name = "orders_with_items")
public class OrderWithItems {

    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE)
    private Long id;

    /**
     * Bidirectional @OneToMany with proper configuration.
     *
     * REQUIRED:
     * - mappedBy: Points to field in child entity
     * - cascade: Define lifecycle operations
     * - orphanRemoval: Delete children when removed from collection
     * - Use ArrayList/HashSet, never null
     * - Initialize in field declaration
     */
    @OneToMany(
        mappedBy = "order",
        cascade = CascadeType.ALL,
        orphanRemoval = true,
        fetch = FetchType.LAZY
    )
    private List<OrderItemBidirectional> items = new ArrayList<>();

    /**
     * Helper method to maintain both sides of bidirectional relationship.
     * ALWAYS provide these methods!
     */
    public void addItem(OrderItemBidirectional item) {
        items.add(item);
        item.setOrder(this);
    }

    public void removeItem(OrderItemBidirectional item) {
        items.remove(item);
        item.setOrder(null);
    }
}

/**
 * Child side of bidirectional relationship.
 */
@Entity
@Table(name = "order_items_bidirectional")
public class OrderItemBidirectional {

    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "order_id", nullable = false)
    private OrderWithItems order;

    // Setter needed for helper methods
    void setOrder(OrderWithItems order) {
        this.order = order;
    }
}

/**
 * BETTER ALTERNATIVE: Query from many side.
 * No @OneToMany mapping needed!
 */
@Entity
@Table(name = "orders_simple")
public class OrderSimple {

    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE)
    private Long id;

    // No items collection!
}

// Repository method instead
interface OrderItemRepository extends JpaRepository<OrderItem, Long> {
    List<OrderItem> findByOrderId(Long orderId);
}

// ============================================================
// @MANYTOMANY - NEVER USE, CREATE JOIN ENTITY INSTEAD
// ============================================================

/**
 * WRONG: Using @ManyToMany
 * Problems:
 * - Cannot add attributes to relationship
 * - Hard to maintain
 * - Performance issues
 */
@Entity
@Table(name = "students_wrong")
public class StudentWrong {

    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE)
    private Long id;

    // WRONG: Direct @ManyToMany
    @ManyToMany
    @JoinTable(
        name = "student_course",
        joinColumns = @JoinColumn(name = "student_id"),
        inverseJoinColumns = @JoinColumn(name = "course_id")
    )
    private Set<CourseWrong> courses = new HashSet<>();
}

/**
 * RIGHT: Use join entity.
 * Benefits:
 * - Can add attributes (enrollmentDate, status, grade)
 * - Better control and maintainability
 * - Can have its own ID and lifecycle
 */
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
    private java.time.LocalDate enrolledAt;
    private EnrollmentStatus status;
    private Integer grade;

    // Business logic
    public void complete(Integer grade) {
        this.status = EnrollmentStatus.COMPLETED;
        this.grade = grade;
    }
}

@Entity
@Table(name = "students")
public class Student {

    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE)
    private Long id;
    private String name;

    // No direct reference to courses!
    // Query: enrollmentRepository.findByStudentId(studentId)
}

@Entity
@Table(name = "courses")
public class Course {

    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE)
    private Long id;
    private String name;

    // No direct reference to students!
}

// ============================================================
// ELEMENT COLLECTION - FOR VALUE TYPES
// ============================================================

/**
 * @ElementCollection - For collections of value types (not entities).
 *
 * Use for:
 * - Collections of primitives (String, Integer, etc.)
 * - Collections of @Embeddable objects
 * - Simple data without its own identity
 *
 * NOT for:
 * - Entities with their own ID
 * - Complex objects needing relationships
 */
@Entity
@Table(name = "products_with_tags")
public class ProductWithTags {

    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE)
    private Long id;

    /**
     * Collection of primitives.
     */
    @ElementCollection
    @CollectionTable(
        name = "product_tags",
        joinColumns = @JoinColumn(name = "product_id")
    )
    @Column(name = "tag")
    private Set<String> tags = new HashSet<>();

    /**
     * Collection of embeddables.
     */
    @ElementCollection
    @CollectionTable(
        name = "product_images",
        joinColumns = @JoinColumn(name = "product_id")
    )
    private List<ProductImage> images = new ArrayList<>();
}

/**
 * Embeddable - value type without identity.
 */
@Embeddable
public class ProductImage {
    private String url;
    private String altText;
    private int displayOrder;

    // Constructor, getters, setters
}

// ============================================================
// CASCADE TYPES
// ============================================================

/**
 * CascadeType - defines which operations propagate to related entities.
 *
 * Types:
 * - PERSIST: Save parent saves children
 * - MERGE: Merge parent merges children
 * - REMOVE: Delete parent deletes children
 * - REFRESH: Refresh parent refreshes children
 * - DETACH: Detach parent detaches children
 * - ALL: All of the above
 *
 * Use carefully! Can cause unexpected deletes.
 */
@Entity
@Table(name = "orders_cascade_example")
public class OrderCascadeExample {

    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE)
    private Long id;

    /**
     * CascadeType.ALL + orphanRemoval
     * Use when children have no meaning without parent.
     * Example: Order items without order
     */
    @OneToMany(
        mappedBy = "order",
        cascade = CascadeType.ALL,
        orphanRemoval = true
    )
    private List<OrderItem> items = new ArrayList<>();

    /**
     * CascadeType.PERSIST + MERGE only
     * Use when children can exist independently but are saved together.
     */
    @ManyToOne(
        cascade = {CascadeType.PERSIST, CascadeType.MERGE},
        fetch = FetchType.LAZY
    )
    @JoinColumn(name = "customer_id")
    private Customer customer;
}

// ============================================================
// FETCH STRATEGIES
// ============================================================

/**
 * FetchType - when to load related entities.
 *
 * LAZY (default for @ManyToOne, @OneToOne):
 * - Load only when accessed
 * - Better performance
 * - May cause LazyInitializationException
 *
 * EAGER (default for @OneToMany, @ManyToMany):
 * - Load immediately with parent
 * - Causes N+1 queries
 * - Avoid unless collection is tiny
 *
 * BEST PRACTICE:
 * - Always use LAZY
 * - Use JOIN FETCH in queries when needed
 */
@Entity
@Table(name = "fetch_example")
public class FetchExample {

    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE)
    private Long id;

    // GOOD: Explicit LAZY
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "category_id")
    private Category category;

    // BAD: EAGER loading
    @ManyToOne(fetch = FetchType.EAGER)  // Avoid!
    @JoinColumn(name = "brand_id")
    private Brand brand;
}

// Repository with JOIN FETCH (BEST)
interface FetchExampleRepository extends JpaRepository<FetchExample, Long> {

    @Query("""
        SELECT f
        FROM FetchExample f
        JOIN FETCH f.category
        WHERE f.id = :id
        """)
    Optional<FetchExample> findByIdWithCategory(@Param("id") Long id);
}

// ============================================================
// BEST PRACTICES SUMMARY
// ============================================================

/*
1. PREFER @MANYTOONE:
   - Most efficient relationship type
   - Query from many side using repository methods
   - Avoid @OneToMany unless absolutely necessary

2. ALWAYS USE LAZY FETCHING:
   - Never use FetchType.EAGER
   - Use JOIN FETCH in queries when you need associations
   - Prevents N+1 queries

3. AVOID BIDIRECTIONAL:
   - Adds complexity
   - Harder to maintain
   - Query from the owning side instead

4. NEVER USE @MANYTOMANY:
   - Create explicit join entity
   - Allows adding attributes to relationship
   - Better control and maintainability

5. USE IDS INSTEAD OF ENTITIES:
   - For loose coupling between modules
   - When you rarely need related entity properties
   - Prevents lazy loading issues

6. CASCADE CAREFULLY:
   - Understand what operations will propagate
   - Test delete operations thoroughly
   - Use orphanRemoval only when appropriate

7. HELPER METHODS FOR BIDIRECTIONAL:
   - Always maintain both sides
   - Prevent inconsistent state
   - Make methods package-private if possible

8. QUERIES OVER MAPPINGS:
   - Better to write query than add mapping
   - More explicit and maintainable
   - Easier to optimize
*/

// ============================================================
// ANTI-PATTERNS TO AVOID
// ============================================================

/*
❌ Using FetchType.EAGER
   ✅ Use FetchType.LAZY + JOIN FETCH

❌ Bidirectional @OneToMany everywhere
   ✅ Query from many side

❌ @ManyToMany relationships
   ✅ Create join entity

❌ Mapping every association
   ✅ Use IDs for loose coupling

❌ CascadeType.ALL without thought
   ✅ Specify only needed cascade types

❌ Null collections
   ✅ Initialize to empty collection

❌ Public setters for collections
   ✅ Use helper methods (add/remove)

❌ Forgetting to maintain both sides
   ✅ Use helper methods
*/
