package {{PACKAGE}}.{{MODULE}}.domain;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import java.util.Optional;

/**
 * CQRS Query Service - separate read model from write model.
 *
 * Use for:
 * - Tomato and DDD+Hexagonal architectures
 * - Performance-critical read operations
 * - Complex reporting queries
 * - Queries that don't fit entity model
 *
 * Benefits:
 * - Clear separation of reads and writes
 * - JdbcTemplate is faster than JPA for reads
 * - No lazy loading issues
 * - Returns View Models, not entities
 *
 * Pattern:
 * - Repository (package-private) for writes (commands)
 * - QueryService (public) for reads (queries)
 * - Use JdbcTemplate or @Query in repository
 */

/**
 * Query Service - read-only operations returning View Models.
 * Mark entire class as @Transactional(readOnly = true) for optimization.
 */
@Service
@Transactional(readOnly = true)
public class {{NAME}}QueryService {

    private final JdbcTemplate jdbcTemplate;

    public {{NAME}}QueryService(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    // ==================== SIMPLE QUERIES ====================

    /**
     * Find all active items.
     * Returns lightweight View Models for list display.
     */
    public List<{{NAME}}VM> findAllActive() {
        return jdbcTemplate.query("""
                SELECT id, code, name, status, created_at
                FROM {{TABLE_NAME}}
                WHERE status = 'ACTIVE'
                ORDER BY created_at DESC
                """,
            (rs, rowNum) -> new {{NAME}}VM(
                rs.getLong("id"),
                rs.getString("code"),
                rs.getString("name"),
                {{NAME}}Status.valueOf(rs.getString("status")),
                rs.getTimestamp("created_at").toInstant()
            )
        );
    }

    /**
     * Find by ID - returns detailed View Model.
     */
    public Optional<{{NAME}}DetailsVM> findDetailsById(Long id) {
        List<{{NAME}}DetailsVM> results = jdbcTemplate.query("""
                SELECT
                    e.id, e.code, e.name, e.description,
                    e.status, e.created_at, e.updated_at,
                    c.id as category_id, c.name as category_name
                FROM {{TABLE_NAME}} e
                LEFT JOIN categories c ON e.category_id = c.id
                WHERE e.id = ?
                """,
            ps -> ps.setLong(1, id),
            new {{NAME}}DetailsMapper()
        );
        return results.isEmpty() ? Optional.empty() : Optional.of(results.get(0));
    }

    // ==================== COMPLEX QUERIES WITH JOINS ====================

    /**
     * Find with related data - using JOIN.
     */
    public List<{{NAME}}WithRelatedVM> findWithRelated({{NAME}}Status status) {
        return jdbcTemplate.query("""
                SELECT
                    e.id, e.code, e.name,
                    r.id as related_id, r.name as related_name,
                    COUNT(i.id) as item_count
                FROM {{TABLE_NAME}} e
                LEFT JOIN related_table r ON e.related_id = r.id
                LEFT JOIN items i ON i.{{TABLE_NAME}}_id = e.id
                WHERE e.status = ?
                GROUP BY e.id, e.code, e.name, r.id, r.name
                ORDER BY e.created_at DESC
                """,
            ps -> ps.setString(1, status.name()),
            (rs, rowNum) -> new {{NAME}}WithRelatedVM(
                rs.getLong("id"),
                rs.getString("code"),
                rs.getString("name"),
                new RelatedVM(
                    rs.getLong("related_id"),
                    rs.getString("related_name")
                ),
                rs.getInt("item_count")
            )
        );
    }

    // ==================== AGGREGATIONS & STATISTICS ====================

    /**
     * Get statistics - aggregations across entities.
     */
    public List<{{NAME}}StatsVM> findStatsByCategory() {
        return jdbcTemplate.query("""
                SELECT
                    c.name as category,
                    COUNT(e.id) as total_count,
                    COUNT(CASE WHEN e.status = 'ACTIVE' THEN 1 END) as active_count,
                    AVG(e.price) as avg_price,
                    MIN(e.created_at) as oldest_created_at
                FROM {{TABLE_NAME}} e
                JOIN categories c ON e.category_id = c.id
                GROUP BY c.name
                HAVING COUNT(e.id) > 0
                ORDER BY total_count DESC
                """,
            (rs, rowNum) -> new {{NAME}}StatsVM(
                rs.getString("category"),
                rs.getLong("total_count"),
                rs.getLong("active_count"),
                rs.getBigDecimal("avg_price"),
                rs.getTimestamp("oldest_created_at").toLocalDateTime()
            )
        );
    }

    /**
     * Count by status - simple aggregation.
     */
    public long countByStatus({{NAME}}Status status) {
        return jdbcTemplate.queryForObject("""
                SELECT COUNT(*)
                FROM {{TABLE_NAME}}
                WHERE status = ?
                """,
            Long.class,
            status.name()
        );
    }

    // ==================== SEARCH & FILTERING ====================

    /**
     * Dynamic search with optional filters.
     * Build SQL dynamically based on criteria.
     */
    public List<{{NAME}}VM> search({{NAME}}SearchCriteria criteria) {
        StringBuilder sql = new StringBuilder("""
                SELECT id, code, name, status, created_at
                FROM {{TABLE_NAME}}
                WHERE 1=1
                """);

        List<Object> params = new ArrayList<>();

        if (criteria.getName() != null && !criteria.getName().isBlank()) {
            sql.append(" AND LOWER(name) LIKE ?");
            params.add("%" + criteria.getName().toLowerCase() + "%");
        }

        if (criteria.getStatus() != null) {
            sql.append(" AND status = ?");
            params.add(criteria.getStatus().name());
        }

        if (criteria.getCreatedAfter() != null) {
            sql.append(" AND created_at >= ?");
            params.add(criteria.getCreatedAfter());
        }

        sql.append(" ORDER BY created_at DESC");
        sql.append(" LIMIT ?");
        params.add(criteria.getLimit());

        return jdbcTemplate.query(
            sql.toString(),
            (rs, rowNum) -> new {{NAME}}VM(
                rs.getLong("id"),
                rs.getString("code"),
                rs.getString("name"),
                {{NAME}}Status.valueOf(rs.getString("status")),
                rs.getTimestamp("created_at").toInstant()
            ),
            params.toArray()
        );
    }

    // ==================== PAGINATION ====================

    /**
     * Paginated query - fetch page of results.
     */
    public Page<{{NAME}}VM> findPage(int page, int size) {
        int offset = page * size;

        // Count total
        Long total = jdbcTemplate.queryForObject("""
                SELECT COUNT(*)
                FROM {{TABLE_NAME}}
                WHERE status = 'ACTIVE'
                """,
            Long.class
        );

        // Fetch page
        List<{{NAME}}VM> content = jdbcTemplate.query("""
                SELECT id, code, name, status, created_at
                FROM {{TABLE_NAME}}
                WHERE status = 'ACTIVE'
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
            ps -> {
                ps.setInt(1, size);
                ps.setInt(2, offset);
            },
            (rs, rowNum) -> new {{NAME}}VM(
                rs.getLong("id"),
                rs.getString("code"),
                rs.getString("name"),
                {{NAME}}Status.valueOf(rs.getString("status")),
                rs.getTimestamp("created_at").toInstant()
            )
        );

        return new Page<>(content, page, size, total);
    }

    // ==================== EXISTS CHECKS ====================

    /**
     * Check if exists - returns boolean.
     */
    public boolean existsByCode(String code) {
        return Boolean.TRUE.equals(jdbcTemplate.queryForObject("""
                SELECT EXISTS(
                    SELECT 1 FROM {{TABLE_NAME}}
                    WHERE code = ?
                )
                """,
            Boolean.class,
            code
        ));
    }
}

// ============================================================
// VIEW MODELS (VMs)
// ============================================================

/**
 * List View Model - minimal data for list display.
 */
public record {{NAME}}VM(
    Long id,
    String code,
    String name,
    {{NAME}}Status status,
    java.time.Instant createdAt
) {}

/**
 * Details View Model - full data for single item view.
 */
public record {{NAME}}DetailsVM(
    Long id,
    String code,
    String name,
    String description,
    {{NAME}}Status status,
    java.time.Instant createdAt,
    java.time.Instant updatedAt,
    CategoryVM category
) {
    public record CategoryVM(Long id, String name) {}
}

/**
 * View Model with related data.
 */
public record {{NAME}}WithRelatedVM(
    Long id,
    String code,
    String name,
    RelatedVM related,
    int itemCount
) {}

public record RelatedVM(Long id, String name) {}

/**
 * Statistics View Model.
 */
public record {{NAME}}StatsVM(
    String category,
    long totalCount,
    long activeCount,
    java.math.BigDecimal avgPrice,
    java.time.LocalDateTime oldestCreatedAt
) {}

// ============================================================
// ROW MAPPERS
// ============================================================

/**
 * Reusable RowMapper for complex mappings.
 */
class {{NAME}}DetailsMapper implements RowMapper<{{NAME}}DetailsVM> {

    @Override
    public {{NAME}}DetailsVM mapRow(ResultSet rs, int rowNum) throws SQLException {
        return new {{NAME}}DetailsVM(
            rs.getLong("id"),
            rs.getString("code"),
            rs.getString("name"),
            rs.getString("description"),
            {{NAME}}Status.valueOf(rs.getString("status")),
            rs.getTimestamp("created_at").toInstant(),
            rs.getTimestamp("updated_at").toInstant(),
            new {{NAME}}DetailsVM.CategoryVM(
                rs.getLong("category_id"),
                rs.getString("category_name")
            )
        );
    }
}

// ============================================================
// SUPPORTING CLASSES
// ============================================================

/**
 * Simple Page wrapper.
 */
public record Page<T>(
    List<T> content,
    int page,
    int size,
    long total
) {
    public int totalPages() {
        return (int) Math.ceil((double) total / size);
    }

    public boolean hasNext() {
        return page < totalPages() - 1;
    }
}

/**
 * Search criteria.
 */
public class {{NAME}}SearchCriteria {
    private String name;
    private {{NAME}}Status status;
    private java.time.LocalDate createdAfter;
    private int limit = 20;

    // Getters and setters
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public {{NAME}}Status getStatus() { return status; }
    public void setStatus({{NAME}}Status status) { this.status = status; }

    public java.time.LocalDate getCreatedAfter() { return createdAfter; }
    public void setCreatedAfter(java.time.LocalDate createdAfter) { this.createdAfter = createdAfter; }

    public int getLimit() { return limit; }
    public void setLimit(int limit) { this.limit = limit; }
}

// ============================================================
// USAGE PATTERN: CQRS SEPARATION
// ============================================================

/*
// Repository (package-private) - for writes only
interface ProductRepository extends JpaRepository<ProductEntity, ProductId> {
    Optional<ProductEntity> findBySku(ProductSKU sku);
}

// QueryService (public) - for reads only
@Service
@Transactional(readOnly = true)
public class ProductQueryService {

    private final JdbcTemplate jdbcTemplate;

    public List<ProductVM> findAllActive() {
        // JdbcTemplate query returning View Models
    }

    public ProductDetailsVM getDetails(Long id) {
        // Complex query with joins
    }
}

// Service (uses both)
@Service
@Transactional
public class ProductService {

    private final ProductRepository repository;  // Write
    private final ProductQueryService queryService;  // Read

    public void createProduct(CreateProductCmd cmd) {
        ProductEntity product = ProductEntity.create(cmd);
        repository.save(product);
    }

    public ProductDetailsVM getProductDetails(Long id) {
        return queryService.getDetails(id);
    }
}
*/

// ============================================================
// BEST PRACTICES
// ============================================================

/*
1. SEPARATION:
   - Repository: Package-private, write operations, returns entities
   - QueryService: Public, read operations, returns View Models
   - Never return entities from QueryService
   - Never put queries in Repository if they return VMs

2. TRANSACTIONS:
   - Mark QueryService with @Transactional(readOnly = true) at class level
   - Enables read-only optimizations (no flush, no dirty checking)
   - Override with @Transactional for rare write operations

3. VIEW MODELS:
   - Use Java Records for immutable VMs
   - Create specific VMs for different use cases (list, details, stats)
   - Don't reuse entity classes as VMs
   - Include only needed data (avoid over-fetching)

4. JDBCTEMPLATE:
   - Faster than JPA for read-only queries
   - No lazy loading issues
   - Direct SQL control
   - Use PreparedStatementSetter to prevent SQL injection

5. MAPPING:
   - Use lambdas for simple mappings
   - Create RowMapper classes for complex/reusable mappings
   - Handle nulls appropriately (use Optional, nullable fields)

6. PERFORMANCE:
   - Fetch only needed columns (avoid SELECT *)
   - Use LIMIT/OFFSET for pagination
   - Add database indexes for frequently queried columns
   - Use COUNT(*) separately for pagination total

7. TESTING:
   - Use @JdbcTest or @DataJpaTest with Testcontainers
   - Test with realistic data volumes
   - Verify query performance with EXPLAIN
   - Mock JdbcTemplate for unit tests
*/
