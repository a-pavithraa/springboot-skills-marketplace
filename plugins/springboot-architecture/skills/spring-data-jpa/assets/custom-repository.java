package {{PACKAGE}}.{{MODULE}}.domain;

import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import jakarta.persistence.criteria.*;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;

/**
 * Custom Repository - for complex operations beyond standard JpaRepository.
 *
 * Use cases:
 * - Dynamic queries with optional filters (Criteria API)
 * - Bulk updates/deletes bypassing entity lifecycle
 * - Native queries with complex SQL
 * - Direct EntityManager access for specific operations
 *
 * Structure:
 * 1. Custom interface with your methods
 * 2. Implementation class (must be named <Repository>Impl)
 * 3. Main repository extends both JpaRepository and custom interface
 */

// ============================================================
// STEP 1: DEFINE CUSTOM INTERFACE
// ============================================================

/**
 * Custom interface - define methods not provided by JpaRepository.
 */
public interface {{NAME}}RepositoryCustom {

    /**
     * Dynamic query with optional filters.
     */
    List<{{NAME}}Entity> findByDynamicCriteria({{NAME}}SearchCriteria criteria);

    /**
     * Bulk update operation.
     * Returns: number of entities updated
     */
    int bulkUpdateStatus({{NAME}}Status oldStatus, {{NAME}}Status newStatus);

    /**
     * Complex query using native SQL.
     */
    List<{{NAME}}Entity> findUsingComplexSql(String param);
}

// ============================================================
// STEP 2: IMPLEMENT CUSTOM INTERFACE
// ============================================================

/**
 * Implementation - MUST be named <Repository>Impl (or configure suffix).
 * Spring Data JPA automatically detects and wires this implementation.
 */
@Repository
class {{NAME}}RepositoryImpl implements {{NAME}}RepositoryCustom {

    @PersistenceContext
    private EntityManager entityManager;

    // ==================== CRITERIA API - DYNAMIC QUERIES ====================

    /**
     * Dynamic query using Criteria API.
     * Add predicates conditionally based on search criteria.
     */
    @Override
    public List<{{NAME}}Entity> findByDynamicCriteria({{NAME}}SearchCriteria criteria) {
        CriteriaBuilder cb = entityManager.getCriteriaBuilder();
        CriteriaQuery<{{NAME}}Entity> query = cb.createQuery({{NAME}}Entity.class);
        Root<{{NAME}}Entity> root = query.from({{NAME}}Entity.class);

        List<Predicate> predicates = new ArrayList<>();

        // Add predicates conditionally
        if (criteria.getName() != null && !criteria.getName().isBlank()) {
            predicates.add(cb.like(
                cb.lower(root.get("name")),
                "%" + criteria.getName().toLowerCase() + "%"
            ));
        }

        if (criteria.getStatus() != null) {
            predicates.add(cb.equal(root.get("status"), criteria.getStatus()));
        }

        if (criteria.getMinPrice() != null) {
            predicates.add(cb.ge(root.get("price"), criteria.getMinPrice()));
        }

        if (criteria.getMaxPrice() != null) {
            predicates.add(cb.le(root.get("price"), criteria.getMaxPrice()));
        }

        if (criteria.getCategoryId() != null) {
            predicates.add(cb.equal(root.get("category").get("id"), criteria.getCategoryId()));
        }

        if (criteria.getCreatedAfter() != null) {
            predicates.add(cb.greaterThanOrEqualTo(
                root.get("createdAt"),
                criteria.getCreatedAfter()
            ));
        }

        // Combine all predicates with AND
        if (!predicates.isEmpty()) {
            query.where(cb.and(predicates.toArray(new Predicate[0])));
        }

        // Add ordering
        if (criteria.getSortBy() != null) {
            if (criteria.getSortDirection() == SortDirection.DESC) {
                query.orderBy(cb.desc(root.get(criteria.getSortBy())));
            } else {
                query.orderBy(cb.asc(root.get(criteria.getSortBy())));
            }
        }

        return entityManager.createQuery(query)
            .setMaxResults(criteria.getLimit())
            .setFirstResult(criteria.getOffset())
            .getResultList();
    }

    // ==================== BULK OPERATIONS ====================

    /**
     * Bulk update - bypasses entity lifecycle for performance.
     * IMPORTANT: Requires @Transactional in service layer.
     */
    @Override
    @Transactional
    public int bulkUpdateStatus({{NAME}}Status oldStatus, {{NAME}}Status newStatus) {
        return entityManager.createQuery("""
                UPDATE {{NAME}}Entity e
                SET e.status = :newStatus,
                    e.updatedAt = CURRENT_TIMESTAMP
                WHERE e.status = :oldStatus
                """)
            .setParameter("oldStatus", oldStatus)
            .setParameter("newStatus", newStatus)
            .executeUpdate();
    }

    /**
     * Bulk delete with conditions.
     */
    @Transactional
    public int bulkDeleteInactive(java.time.LocalDate beforeDate) {
        return entityManager.createQuery("""
                DELETE FROM {{NAME}}Entity e
                WHERE e.status = :status
                AND e.createdAt < :beforeDate
                """)
            .setParameter("status", {{NAME}}Status.INACTIVE)
            .setParameter("beforeDate", beforeDate)
            .executeUpdate();
    }

    // ==================== NATIVE QUERIES ====================

    /**
     * Native SQL query - use when JPQL is insufficient.
     * WARNING: Loses database portability.
     */
    @Override
    @SuppressWarnings("unchecked")
    public List<{{NAME}}Entity> findUsingComplexSql(String param) {
        return entityManager.createNativeQuery("""
                SELECT e.*
                FROM {{TABLE_NAME}} e
                WHERE e.status = 'ACTIVE'
                AND e.search_vector @@ plainto_tsquery(:param)
                ORDER BY ts_rank(e.search_vector, plainto_tsquery(:param)) DESC
                LIMIT 20
                """, {{NAME}}Entity.class)
            .setParameter("param", param)
            .getResultList();
    }

    // ==================== DIRECT ENTITYMANAGER OPERATIONS ====================

    /**
     * Force flush and clear - useful for batch operations.
     */
    public void flushAndClear() {
        entityManager.flush();
        entityManager.clear();
    }

    /**
     * Detach entity from persistence context.
     */
    public void detach({{NAME}}Entity entity) {
        entityManager.detach(entity);
    }

    /**
     * Refresh entity from database.
     */
    public void refresh({{NAME}}Entity entity) {
        entityManager.refresh(entity);
    }
}

// ============================================================
// STEP 3: MAIN REPOSITORY INTERFACE
// ============================================================

/**
 * Main repository - extends both JpaRepository and custom interface.
 * Spring Data JPA automatically implements both.
 */
public interface {{NAME}}Repository extends JpaRepository<{{NAME}}Entity, Long>,
                                            {{NAME}}RepositoryCustom {

    // Standard Spring Data JPA methods
    List<{{NAME}}Entity> findByStatus({{NAME}}Status status);

    // Custom methods automatically available from {{NAME}}RepositoryCustom
}

// ============================================================
// SUPPORTING CLASSES
// ============================================================

/**
 * Search criteria DTO - encapsulates dynamic query parameters.
 */
public class {{NAME}}SearchCriteria {
    private String name;
    private {{NAME}}Status status;
    private java.math.BigDecimal minPrice;
    private java.math.BigDecimal maxPrice;
    private Long categoryId;
    private java.time.LocalDate createdAfter;
    private String sortBy = "createdAt";
    private SortDirection sortDirection = SortDirection.DESC;
    private int limit = 20;
    private int offset = 0;

    // Getters and setters
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public {{NAME}}Status getStatus() { return status; }
    public void setStatus({{NAME}}Status status) { this.status = status; }

    public java.math.BigDecimal getMinPrice() { return minPrice; }
    public void setMinPrice(java.math.BigDecimal minPrice) { this.minPrice = minPrice; }

    public java.math.BigDecimal getMaxPrice() { return maxPrice; }
    public void setMaxPrice(java.math.BigDecimal maxPrice) { this.maxPrice = maxPrice; }

    public Long getCategoryId() { return categoryId; }
    public void setCategoryId(Long categoryId) { this.categoryId = categoryId; }

    public java.time.LocalDate getCreatedAfter() { return createdAfter; }
    public void setCreatedAfter(java.time.LocalDate createdAfter) { this.createdAfter = createdAfter; }

    public String getSortBy() { return sortBy; }
    public void setSortBy(String sortBy) { this.sortBy = sortBy; }

    public SortDirection getSortDirection() { return sortDirection; }
    public void setSortDirection(SortDirection sortDirection) { this.sortDirection = sortDirection; }

    public int getLimit() { return limit; }
    public void setLimit(int limit) { this.limit = limit; }

    public int getOffset() { return offset; }
    public void setOffset(int offset) { this.offset = offset; }
}

enum SortDirection {
    ASC, DESC
}

// ============================================================
// COMPLETE EXAMPLE: ProductRepository with Custom Methods
// ============================================================

/*
// Custom interface
public interface ProductRepositoryCustom {
    List<ProductEntity> searchProducts(ProductSearchCriteria criteria);
    int updatePricesByCategory(Long categoryId, BigDecimal multiplier);
    List<ProductEntity> findSimilar(Long productId, int limit);
}

// Implementation
@Repository
class ProductRepositoryImpl implements ProductRepositoryCustom {

    @PersistenceContext
    private EntityManager entityManager;

    @Override
    public List<ProductEntity> searchProducts(ProductSearchCriteria criteria) {
        CriteriaBuilder cb = entityManager.getCriteriaBuilder();
        CriteriaQuery<ProductEntity> query = cb.createQuery(ProductEntity.class);
        Root<ProductEntity> product = query.from(ProductEntity.class);
        Join<ProductEntity, CategoryEntity> category = product.join("category", JoinType.LEFT);

        List<Predicate> predicates = new ArrayList<>();

        // Search by name or description
        if (criteria.getSearchTerm() != null) {
            Predicate namePredicate = cb.like(
                cb.lower(product.get("name")),
                "%" + criteria.getSearchTerm().toLowerCase() + "%"
            );
            Predicate descPredicate = cb.like(
                cb.lower(product.get("description")),
                "%" + criteria.getSearchTerm().toLowerCase() + "%"
            );
            predicates.add(cb.or(namePredicate, descPredicate));
        }

        // Filter by price range
        if (criteria.getMinPrice() != null) {
            predicates.add(cb.ge(product.get("price"), criteria.getMinPrice()));
        }
        if (criteria.getMaxPrice() != null) {
            predicates.add(cb.le(product.get("price"), criteria.getMaxPrice()));
        }

        // Filter by categories
        if (criteria.getCategoryIds() != null && !criteria.getCategoryIds().isEmpty()) {
            predicates.add(category.get("id").in(criteria.getCategoryIds()));
        }

        // Filter by stock availability
        if (criteria.getInStockOnly()) {
            predicates.add(cb.gt(product.get("stock"), 0));
        }

        query.where(cb.and(predicates.toArray(new Predicate[0])));
        query.orderBy(cb.desc(product.get("createdAt")));

        return entityManager.createQuery(query)
            .setMaxResults(criteria.getLimit())
            .setFirstResult(criteria.getOffset())
            .getResultList();
    }

    @Override
    @Transactional
    public int updatePricesByCategory(Long categoryId, BigDecimal multiplier) {
        return entityManager.createQuery("""
                UPDATE ProductEntity p
                SET p.price = p.price * :multiplier,
                    p.updatedAt = CURRENT_TIMESTAMP
                WHERE p.category.id = :categoryId
                AND p.status = 'ACTIVE'
                """)
            .setParameter("categoryId", categoryId)
            .setParameter("multiplier", multiplier)
            .executeUpdate();
    }

    @Override
    @SuppressWarnings("unchecked")
    public List<ProductEntity> findSimilar(Long productId, int limit) {
        // Using native query with database-specific similarity functions
        return entityManager.createNativeQuery("""
                SELECT p2.*
                FROM products p1
                JOIN products p2 ON p1.category_id = p2.category_id
                WHERE p1.id = :productId
                AND p2.id != :productId
                AND p2.status = 'ACTIVE'
                AND ABS(p2.price - p1.price) / p1.price < 0.3
                ORDER BY ABS(p2.price - p1.price)
                LIMIT :limit
                """, ProductEntity.class)
            .setParameter("productId", productId)
            .setParameter("limit", limit)
            .getResultList();
    }
}

// Main repository
public interface ProductRepository extends JpaRepository<ProductEntity, Long>,
                                           ProductRepositoryCustom {
    Optional<ProductEntity> findBySku(String sku);
    List<ProductEntity> findByStatus(ProductStatus status);
}
*/

// ============================================================
// BEST PRACTICES
// ============================================================

/*
1. NAMING:
   - Custom interface: <Entity>RepositoryCustom
   - Implementation: <Entity>RepositoryImpl (or configure postfix in config)
   - Spring Data automatically detects and wires the implementation

2. TRANSACTIONS:
   - Add @Transactional to write operations (executeUpdate, flush, etc.)
   - Read operations don't require @Transactional in repository
   - Prefer @Transactional at service layer for proper boundaries

3. CRITERIA API:
   - Use for dynamic queries with optional filters
   - Type-safe (compile-time checking)
   - More verbose than JPQL but more maintainable for complex queries

4. BULK OPERATIONS:
   - Bypass entity lifecycle for performance
   - Don't trigger @PreUpdate, @PostUpdate callbacks
   - Use for batch updates/deletes of many entities
   - Remember to flush/clear EntityManager after bulk ops

5. NATIVE QUERIES:
   - Last resort when JPQL is insufficient
   - Loses database portability
   - Good for database-specific features (full-text search, JSON ops, etc.)
   - Can return entities or scalars

6. PERFORMANCE:
   - Use setMaxResults and setFirstResult for pagination
   - Call flush() and clear() after batch operations
   - Detach entities if you don't need tracking
   - Use query hints for specific database optimizations

7. TESTING:
   - Custom repositories are harder to test (need EntityManager)
   - Use @DataJpaTest with Testcontainers
   - Inject actual EntityManager for integration tests
*/
