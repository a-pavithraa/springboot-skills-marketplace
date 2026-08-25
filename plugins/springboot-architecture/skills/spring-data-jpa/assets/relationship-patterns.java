// ============================================================
// BUNDLE TEMPLATE — split into separate .java files when applying.
// Java only allows one public top-level type per source file, so the
// public @Entity classes and repository declarations below must each
// live in their own .java file with a matching filename. The
// {{PACKAGE}} and {{MODULE}} placeholders resolve identically across
// all of them. Each entity below illustrates a different relationship
// pattern — pick the ones you need; you are not meant to apply all
// of them in one project.
// ============================================================

package {{PACKAGE}}.{{MODULE}}.domain;

import jakarta.persistence.*;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;

/**
 * JPA Relationship Patterns - Best practices for associations.
 *
 * Key principles:
 * - Always use FetchType.LAZY
 * - Avoid bidirectional relationships when possible
 * - Use JOIN FETCH in queries instead of EAGER
 * - Prefer @ManyToOne over @OneToMany
 * - Prefer an explicit join entity over plain @ManyToMany when the
 *   relationship has attributes or needs to be queried as an entity;
 *   plain @ManyToMany is part of the JPA spec and is fine for pure
 *   tagging-style links with no link data
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
 * - ALWAYS set fetch = FetchType.LAZY explicitly — the JPA default for
 *   @ManyToOne is EAGER, which causes hidden N+1 queries
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
// @MANYTOMANY - FINE FOR PURE TAGGING; PREFER A JOIN ENTITY WHEN THE LINK HAS DATA
// ============================================================

/**
 * Plain @ManyToMany is a valid JPA mapping, but it has no place to store
 * data about the link itself. For an enrollment — which needs a date,
 * status, and grade — that is a real limitation:
 * - Nowhere to add relationship attributes (enrollmentDate, grade, status)
 * - The join table is managed implicitly, so it is awkward to query directly
 * For a pure tagging-style link with no extra columns, plain @ManyToMany is fine.
 */
@Entity
@Table(name = "students_wrong")
public class StudentWrong {

    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE)
    private Long id;

    // Plain @ManyToMany: no column for enrollment attributes (date, grade, status)
    @ManyToMany
    @JoinTable(
        name = "student_course",
        joinColumns = @JoinColumn(name = "student_id"),
        inverseJoinColumns = @JoinColumn(name = "course_id")
    )
    private Set<Course> courses = new HashSet<>();
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
 * Per the Jakarta Persistence specification:
 *   @ManyToOne, @OneToOne  -> default EAGER (must override to LAZY)
 *   @OneToMany, @ManyToMany -> default LAZY
 *
 * EAGER:
 * - Load immediately with parent
 * - Easy to forget; can fan out into N+1 queries
 * - Cannot be downgraded to LAZY at query time
 *
 * LAZY:
 * - Load only when first accessed
 * - May throw LazyInitializationException if accessed outside a session
 * - Pair with JOIN FETCH / @EntityGraph for paths that genuinely need the
 *   association
 *
 * BEST PRACTICE:
 * - Explicitly set FetchType.LAZY on every @ManyToOne / @OneToOne (the
 *   defaults are EAGER and almost always wrong for production code).
 * - Leave @OneToMany / @ManyToMany at the LAZY default; never set them EAGER.
 * - Use JOIN FETCH or @EntityGraph in queries when you need the association.
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

4. PREFER A JOIN ENTITY WHEN THE LINK HAS DATA:
   - Plain @ManyToMany is valid JPA and fine for pure tagging-style links
   - Use an explicit join entity when the link needs attributes or its own lifecycle
   - A join entity gives better control, queryability, and maintainability

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

❌ @ManyToMany when the link needs attributes or lifecycle
   ✅ Create a join entity (plain @ManyToMany is fine for pure tagging)

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
