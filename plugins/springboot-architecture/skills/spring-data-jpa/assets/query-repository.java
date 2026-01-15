package {{PACKAGE}}.{{MODULE}}.domain;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;

/**
 * Repository with @Query examples - use for non-trivial queries.
 *
 * Key principles:
 * - Use @Query for queries with 3+ filters
 * - Use text blocks (""") for readability
 * - Always use @Param for parameter binding
 * - Use JOIN FETCH to avoid N+1 queries
 * - Use DISTINCT when fetching collections
 * - Add default methods for convenience
 */
public interface {{NAME}}Repository extends JpaRepository<{{NAME}}Entity, Long> {

    // ==================== SIMPLE QUERIES ====================

    @Query("""
            SELECT e
            FROM {{NAME}}Entity e
            WHERE e.code = :code
            """)
    Optional<{{NAME}}Entity> findByCode(@Param("code") String code);

    @Query("""
            SELECT e
            FROM {{NAME}}Entity e
            WHERE e.status = :status
            ORDER BY e.createdAt DESC
            """)
    List<{{NAME}}Entity> findByStatus(@Param("status") {{NAME}}Status status);

    // ==================== COMPLEX QUERIES WITH JOINS ====================

    /**
     * Fetch with associations - use JOIN FETCH to prevent N+1.
     * IMPORTANT: Use DISTINCT to avoid duplicates from JOIN.
     */
    @Query("""
            SELECT DISTINCT e
            FROM {{NAME}}Entity e
            LEFT JOIN FETCH e.relatedItems
            WHERE e.status = :status
            """)
    List<{{NAME}}Entity> findWithRelatedItems(@Param("status") {{NAME}}Status status);

    /**
     * Multiple filters with joins.
     */
    @Query("""
            SELECT e
            FROM {{NAME}}Entity e
            JOIN e.category c
            WHERE e.status = :status
            AND c.name = :categoryName
            AND e.createdAt >= :fromDate
            ORDER BY e.createdAt DESC
            """)
    List<{{NAME}}Entity> findByStatusAndCategory(
        @Param("status") {{NAME}}Status status,
        @Param("categoryName") String categoryName,
        @Param("fromDate") java.time.LocalDate fromDate
    );

    // ==================== PAGINATION & SORTING ====================

    /**
     * Paginated query with sorting.
     * Usage: repository.findByStatus(Status.ACTIVE,
     *                                PageRequest.of(0, 20, Sort.by("createdAt").desc()))
     */
    @Query("""
            SELECT e
            FROM {{NAME}}Entity e
            WHERE e.status = :status
            """)
    Page<{{NAME}}Entity> findByStatus(
        @Param("status") {{NAME}}Status status,
        Pageable pageable
    );

    /**
     * Sorting without pagination.
     * Usage: repository.findAllActive(Sort.by("name").ascending())
     */
    @Query("""
            SELECT e
            FROM {{NAME}}Entity e
            WHERE e.status = 'ACTIVE'
            """)
    List<{{NAME}}Entity> findAllActive(Sort sort);

    // ==================== AGGREGATIONS ====================

    @Query("""
            SELECT COUNT(e)
            FROM {{NAME}}Entity e
            WHERE e.status = :status
            """)
    long countByStatus(@Param("status") {{NAME}}Status status);

    @Query("""
            SELECT e.category, COUNT(e)
            FROM {{NAME}}Entity e
            WHERE e.status = 'ACTIVE'
            GROUP BY e.category
            """)
    List<Object[]> countByCategory();

    // ==================== EXISTS QUERIES ====================

    @Query("""
            SELECT CASE WHEN COUNT(e) > 0 THEN true ELSE false END
            FROM {{NAME}}Entity e
            WHERE e.code = :code
            """)
    boolean existsByCode(@Param("code") String code);

    // ==================== MODIFYING QUERIES ====================

    /**
     * Bulk update - use sparingly, bypasses entity lifecycle.
     * MUST be used with @Transactional in service layer.
     */
    @Modifying
    @Query("""
            UPDATE {{NAME}}Entity e
            SET e.status = :newStatus
            WHERE e.status = :oldStatus
            """)
    int updateStatus(
        @Param("oldStatus") {{NAME}}Status oldStatus,
        @Param("newStatus") {{NAME}}Status newStatus
    );

    @Modifying
    @Query("""
            DELETE FROM {{NAME}}Entity e
            WHERE e.status = :status
            AND e.createdAt < :beforeDate
            """)
    int deleteOldByStatus(
        @Param("status") {{NAME}}Status status,
        @Param("beforeDate") java.time.LocalDate beforeDate
    );

    // ==================== NATIVE QUERIES ====================

    /**
     * Use native queries only when JPQL is insufficient.
     * Note: Loses database portability.
     */
    @Query(value = """
            SELECT *
            FROM {{TABLE_NAME}} e
            WHERE e.status = :status
            AND e.search_vector @@ to_tsquery(:searchTerm)
            ORDER BY ts_rank(e.search_vector, to_tsquery(:searchTerm)) DESC
            """, nativeQuery = true)
    List<{{NAME}}Entity> searchByFullText(
        @Param("status") String status,
        @Param("searchTerm") String searchTerm
    );

    // ==================== CONVENIENCE METHODS ====================

    /**
     * Default methods provide convenience without additional queries.
     * Use for common patterns like "getOrThrow".
     */
    default {{NAME}}Entity getByCode(String code) {
        return findByCode(code)
            .orElseThrow(() -> new ResourceNotFoundException(
                "{{NAME}} not found with code: " + code));
    }

    default {{NAME}}Entity getById(Long id) {
        return findById(id)
            .orElseThrow(() -> new ResourceNotFoundException(
                "{{NAME}} not found with id: " + id));
    }
}

// ============================================================
// EXAMPLE: ProductRepository
// ============================================================

/*
public interface ProductRepository extends JpaRepository<ProductEntity, Long> {

    @Query("""
            SELECT p
            FROM ProductEntity p
            WHERE p.sku = :sku
            AND p.status = 'ACTIVE'
            """)
    Optional<ProductEntity> findActiveBySku(@Param("sku") String sku);

    @Query("""
            SELECT DISTINCT p
            FROM ProductEntity p
            LEFT JOIN FETCH p.images
            WHERE p.featured = true
            AND p.stock > 0
            ORDER BY p.salesRank ASC
            """)
    List<ProductEntity> findFeaturedInStock();

    @Query("""
            SELECT p
            FROM ProductEntity p
            JOIN p.category c
            WHERE c.name = :category
            AND p.price BETWEEN :minPrice AND :maxPrice
            AND p.status = 'ACTIVE'
            """)
    Page<ProductEntity> findByPriceRangeInCategory(
        @Param("category") String category,
        @Param("minPrice") BigDecimal minPrice,
        @Param("maxPrice") BigDecimal maxPrice,
        Pageable pageable
    );

    @Modifying
    @Query("""
            UPDATE ProductEntity p
            SET p.stock = p.stock - :quantity
            WHERE p.id = :id
            AND p.stock >= :quantity
            """)
    int decreaseStock(@Param("id") Long id, @Param("quantity") int quantity);

    default ProductEntity getBySku(String sku) {
        return findActiveBySku(sku)
            .orElseThrow(() -> new ResourceNotFoundException(
                "Product not found: " + sku));
    }
}
*/
