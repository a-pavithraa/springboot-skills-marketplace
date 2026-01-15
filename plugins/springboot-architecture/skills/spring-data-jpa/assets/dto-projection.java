package {{PACKAGE}}.{{MODULE}};

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

/**
 * DTO Projections - for performance-critical read-only queries.
 *
 * Benefits:
 * - Fetch only needed columns (better performance)
 * - No lazy loading issues (no proxy objects)
 * - Clean separation of read/write models
 * - Type-safe query results
 */

// ============================================================
// APPROACH 1: JAVA RECORDS (RECOMMENDED FOR SPRING BOOT 3+)
// ============================================================

/**
 * Java Record - compact, immutable, equals/hashCode built-in.
 * Perfect for API responses and DTOs.
 */
public record {{NAME}}Summary(
    Long id,
    String code,
    String name,
    {{NAME}}Status status,
    LocalDate createdAt
) {}

/**
 * Nested/Hierarchical Record - for complex structures.
 */
public record {{NAME}}Details(
    Long id,
    String code,
    String name,
    CategoryInfo category,
    BigDecimal price,
    int stock
) {
    public record CategoryInfo(Long id, String name) {}
}

/**
 * Repository using Record projections.
 */
public interface {{NAME}}Repository extends JpaRepository<{{NAME}}Entity, Long> {

    /**
     * Constructor expression - fetch Record.
     * Must use fully-qualified class name (or configure Hypersistence Utils).
     */
    @Query("""
            SELECT new {{PACKAGE}}.{{MODULE}}.{{NAME}}Summary(
                e.id, e.code, e.name, e.status, e.createdAt
            )
            FROM {{NAME}}Entity e
            WHERE e.status = 'ACTIVE'
            ORDER BY e.createdAt DESC
            """)
    List<{{NAME}}Summary> findAllActiveSummaries();

    /**
     * Nested Record - requires nested constructor expressions.
     */
    @Query("""
            SELECT new {{PACKAGE}}.{{MODULE}}.{{NAME}}Details(
                e.id, e.code, e.name,
                new {{PACKAGE}}.{{MODULE}}.{{NAME}}Details$CategoryInfo(
                    c.id, c.name
                ),
                e.price, e.stock
            )
            FROM {{NAME}}Entity e
            JOIN e.category c
            WHERE e.id = :id
            """)
    {{NAME}}Details findDetailsById(@Param("id") Long id);

    /**
     * Parameterized query with Record.
     */
    @Query("""
            SELECT new {{PACKAGE}}.{{MODULE}}.{{NAME}}Summary(
                e.id, e.code, e.name, e.status, e.createdAt
            )
            FROM {{NAME}}Entity e
            WHERE e.category.name = :category
            AND e.price BETWEEN :minPrice AND :maxPrice
            ORDER BY e.price ASC
            """)
    List<{{NAME}}Summary> findByPriceRange(
        @Param("category") String category,
        @Param("minPrice") BigDecimal minPrice,
        @Param("maxPrice") BigDecimal maxPrice
    );
}

// ============================================================
// APPROACH 2: INTERFACE PROJECTIONS
// ============================================================

/**
 * Interface-based projection - Spring Data generates proxy.
 * Pros: Simple, no constructor needed
 * Cons: No custom equals/hashCode, lazy evaluation (beware N+1)
 */
public interface {{NAME}}View {
    Long getId();
    String getCode();
    String getName();
    {{NAME}}Status getStatus();
}

/**
 * Nested interface projection - for associations.
 * CAUTION: Can cause N+1 queries if not careful with JOIN.
 */
public interface {{NAME}}WithCategory {
    Long getId();
    String getName();
    CategoryView getCategory();

    interface CategoryView {
        Long getId();
        String getName();
    }
}

/**
 * Repository using Interface projections.
 */
public interface {{NAME}}InterfaceRepository extends JpaRepository<{{NAME}}Entity, Long> {

    /**
     * Interface projection - uses column aliases.
     */
    @Query("""
            SELECT e.id as id, e.code as code, e.name as name, e.status as status
            FROM {{NAME}}Entity e
            WHERE e.featured = true
            """)
    List<{{NAME}}View> findFeatured();

    /**
     * With nested projection - MUST include JOIN.
     */
    @Query("""
            SELECT e.id as id, e.name as name,
                   c.id as category.id, c.name as category.name
            FROM {{NAME}}Entity e
            JOIN e.category c
            WHERE e.status = 'ACTIVE'
            """)
    List<{{NAME}}WithCategory> findActiveWithCategory();

    /**
     * Alternative: Use class-based projection in same query.
     * Spring Data will automatically map to interface.
     */
    List<{{NAME}}View> findByStatus({{NAME}}Status status);
}

// ============================================================
// APPROACH 3: POJO CLASS PROJECTIONS
// ============================================================

/**
 * POJO class - maximum flexibility, explicit control.
 * Use when you need custom equals/hashCode/toString.
 */
public class {{NAME}}DTO {
    private final Long id;
    private final String code;
    private final String name;
    private final {{NAME}}Status status;

    public {{NAME}}DTO(Long id, String code, String name, {{NAME}}Status status) {
        this.id = id;
        this.code = code;
        this.name = name;
        this.status = status;
    }

    // Getters
    public Long getId() { return id; }
    public String getCode() { return code; }
    public String getName() { return name; }
    public {{NAME}}Status getStatus() { return status; }

    // Custom equals/hashCode/toString as needed
}

/**
 * Repository using POJO projections.
 */
public interface {{NAME}}PojoRepository extends JpaRepository<{{NAME}}Entity, Long> {

    @Query("""
            SELECT new {{PACKAGE}}.{{MODULE}}.{{NAME}}DTO(
                e.id, e.code, e.name, e.status
            )
            FROM {{NAME}}Entity e
            WHERE e.createdAt >= :since
            ORDER BY e.createdAt DESC
            """)
    List<{{NAME}}DTO> findRecentDTOs(@Param("since") LocalDate since);
}

// ============================================================
// APPROACH 4: NATIVE QUERY WITH PROJECTIONS
// ============================================================

/**
 * Native SQL with interface projection - for complex queries.
 * Use when JPQL is insufficient or performance is critical.
 */
public interface {{NAME}}StatsView {
    String getCategory();
    Long getCount();
    BigDecimal getAvgPrice();
    BigDecimal getTotalRevenue();
}

public interface {{NAME}}NativeRepository extends JpaRepository<{{NAME}}Entity, Long> {

    /**
     * Native query with projection - column aliases must match interface methods.
     * Note: Loses database portability.
     */
    @Query(value = """
            SELECT
                c.name as category,
                COUNT(*) as count,
                AVG(p.price) as avgPrice,
                SUM(p.price * p.sold_quantity) as totalRevenue
            FROM {{TABLE_NAME}} p
            JOIN categories c ON p.category_id = c.id
            WHERE p.status = 'ACTIVE'
            GROUP BY c.name
            ORDER BY totalRevenue DESC
            """, nativeQuery = true)
    List<{{NAME}}StatsView> findStatsByCategory();
}

// ============================================================
// BEST PRACTICES & TIPS
// ============================================================

/*
1. WHEN TO USE WHAT:
   - Java Records: Default choice for Spring Boot 3+ (clean, immutable)
   - Interface Projections: Simple cases, but watch out for N+1
   - POJO Classes: When you need custom equals/hashCode
   - Native Queries: Complex aggregations, database-specific features

2. PERFORMANCE:
   - Records & POJOs: Best performance (eager evaluation)
   - Interface Projections: Lazy evaluation (can cause N+1)
   - Always fetch only needed columns
   - Use projections for list endpoints (not full entities)

3. AVOID COMMON MISTAKES:
   - DON'T: Use interface projections with nested associations without JOIN
   - DON'T: Use projections for write operations (use entities)
   - DON'T: Forget @Param annotation with constructor expressions
   - DO: Keep projections in same package or use fully-qualified names

4. TESTING:
   - Enable SQL logging: spring.jpa.show-sql=true
   - Check for N+1 queries with Hibernate statistics
   - Test with realistic data volumes

5. HYPERSISTENCE UTILS (OPTIONAL):
   Add to pom.xml to avoid fully-qualified class names:
   <dependency>
       <groupId>io.hypersistence</groupId>
       <artifactId>hypersistence-utils-hibernate-63</artifactId>
       <version>3.7.0</version>
   </dependency>

   Register in HibernateConfig:
   @Bean
   public HibernatePropertiesCustomizer hibernatePropertiesCustomizer() {
       return properties -> properties.put("hibernate.integrator_provider",
           (IntegratorProvider) () -> Collections.singletonList(
               new ClassImportIntegrator(List.of(ProductSummary.class))));
   }
*/

// ============================================================
// COMPLETE EXAMPLE: ProductRepository with Projections
// ============================================================

/*
// DTOs
public record ProductSummary(
    Long id,
    String sku,
    String name,
    BigDecimal price,
    int stock
) {}

public record ProductDetails(
    Long id,
    String sku,
    String name,
    String description,
    BigDecimal price,
    int stock,
    CategoryInfo category,
    List<String> imageUrls
) {
    public record CategoryInfo(Long id, String name, String slug) {}
}

public interface ProductStatsView {
    String getCategory();
    Long getTotalProducts();
    BigDecimal getAvgPrice();
}

// Repository
public interface ProductRepository extends JpaRepository<ProductEntity, Long> {

    @Query("""
            SELECT new com.example.products.ProductSummary(
                p.id, p.sku, p.name, p.price, p.stock
            )
            FROM ProductEntity p
            WHERE p.status = 'ACTIVE'
            AND p.stock > 0
            ORDER BY p.salesRank ASC
            LIMIT 20
            """)
    List<ProductSummary> findTopSelling();

    @Query("""
            SELECT new com.example.products.ProductDetails(
                p.id, p.sku, p.name, p.description, p.price, p.stock,
                new com.example.products.ProductDetails$CategoryInfo(
                    c.id, c.name, c.slug
                ),
                (SELECT GROUP_CONCAT(i.url) FROM ProductImage i WHERE i.product = p)
            )
            FROM ProductEntity p
            JOIN p.category c
            WHERE p.sku = :sku
            """)
    ProductDetails findDetailsBySku(@Param("sku") String sku);

    @Query(value = """
            SELECT
                c.name as category,
                COUNT(p.id) as totalProducts,
                AVG(p.price) as avgPrice
            FROM products p
            JOIN categories c ON p.category_id = c.id
            WHERE p.status = 'ACTIVE'
            GROUP BY c.name
            HAVING COUNT(p.id) > 10
            ORDER BY avgPrice DESC
            """, nativeQuery = true)
    List<ProductStatsView> findCategoryStats();
}
*/
