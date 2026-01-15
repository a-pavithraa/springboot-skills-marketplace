# CQRS Query Service Reference

Separate read operations from write operations for Tomato/DDD architectures.

## Pattern

- **Repository** (package-private): Write operations, returns entities
- **QueryService** (public): Read operations, returns View Models
- Clear separation of concerns

## Query Service Implementation

```java
@Service
@Transactional(readOnly = true)
public class ProductQueryService {

    private final JdbcTemplate jdbcTemplate;

    public ProductQueryService(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public List<ProductVM> findAllActive() {
        return jdbcTemplate.query("""
            SELECT id, sku, name, price, stock
            FROM products
            WHERE status = 'ACTIVE'
            ORDER BY created_at DESC
            """,
            (rs, rowNum) -> new ProductVM(
                rs.getLong("id"),
                rs.getString("sku"),
                rs.getString("name"),
                rs.getBigDecimal("price"),
                rs.getInt("stock")
            )
        );
    }

    public Optional<ProductDetailsVM> findDetailsById(Long id) {
        List<ProductDetailsVM> results = jdbcTemplate.query("""
            SELECT
                p.id, p.sku, p.name, p.description, p.price,
                c.id as category_id, c.name as category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.id = ?
            """,
            ps -> ps.setLong(1, id),
            new ProductDetailsMapper()
        );
        return results.isEmpty() ? Optional.empty() : Optional.of(results.get(0));
    }
}
```

## View Models (Records)

```java
public record ProductVM(
    Long id,
    String sku,
    String name,
    BigDecimal price,
    int stock
) {}

public record ProductDetailsVM(
    Long id,
    String sku,
    String name,
    String description,
    BigDecimal price,
    CategoryVM category
) {
    public record CategoryVM(Long id, String name) {}
}
```

## Complex Queries with JOINs

```java
public List<ProductWithStatsVM> findTopSelling(int limit) {
    return jdbcTemplate.query("""
        SELECT
            p.id, p.sku, p.name, p.price,
            COUNT(oi.id) as order_count,
            SUM(oi.quantity) as total_sold
        FROM products p
        LEFT JOIN order_items oi ON p.id = oi.product_id
        WHERE p.status = 'ACTIVE'
        GROUP BY p.id, p.sku, p.name, p.price
        ORDER BY total_sold DESC
        LIMIT ?
        """,
        ps -> ps.setInt(1, limit),
        (rs, rowNum) -> new ProductWithStatsVM(
            rs.getLong("id"),
            rs.getString("sku"),
            rs.getString("name"),
            rs.getBigDecimal("price"),
            rs.getInt("order_count"),
            rs.getInt("total_sold")
        )
    );
}
```

## Pagination

```java
public Page<ProductVM> findPage(int page, int size) {
    int offset = page * size;

    Long total = jdbcTemplate.queryForObject(
        "SELECT COUNT(*) FROM products WHERE status = 'ACTIVE'",
        Long.class
    );

    List<ProductVM> content = jdbcTemplate.query("""
        SELECT id, sku, name, price, stock
        FROM products
        WHERE status = 'ACTIVE'
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        ps -> {
            ps.setInt(1, size);
            ps.setInt(2, offset);
        },
        (rs, rowNum) -> new ProductVM(/* ... */)
    );

    return new Page<>(content, page, size, total);
}
```

## Dynamic Search

```java
public List<ProductVM> search(ProductSearchCriteria criteria) {
    StringBuilder sql = new StringBuilder("""
        SELECT id, sku, name, price, stock
        FROM products
        WHERE 1=1
        """);

    List<Object> params = new ArrayList<>();

    if (criteria.getName() != null) {
        sql.append(" AND LOWER(name) LIKE ?");
        params.add("%" + criteria.getName().toLowerCase() + "%");
    }

    if (criteria.getStatus() != null) {
        sql.append(" AND status = ?");
        params.add(criteria.getStatus().name());
    }

    sql.append(" ORDER BY created_at DESC LIMIT ?");
    params.add(criteria.getLimit());

    return jdbcTemplate.query(sql.toString(),
        (rs, rowNum) -> new ProductVM(/* ... */),
        params.toArray()
    );
}
```

## RowMapper for Complex Mappings

```java
class ProductDetailsMapper implements RowMapper<ProductDetailsVM> {

    @Override
    public ProductDetailsVM mapRow(ResultSet rs, int rowNum) throws SQLException {
        return new ProductDetailsVM(
            rs.getLong("id"),
            rs.getString("sku"),
            rs.getString("name"),
            rs.getString("description"),
            rs.getBigDecimal("price"),
            new ProductDetailsVM.CategoryVM(
                rs.getLong("category_id"),
                rs.getString("category_name")
            )
        );
    }
}
```

## Usage Pattern

```java
// Service uses both
@Service
@Transactional
public class ProductService {

    private final ProductRepository repository;      // Write
    private final ProductQueryService queryService;  // Read

    public void createProduct(CreateProductCmd cmd) {
        ProductEntity product = ProductEntity.create(cmd);
        repository.save(product);
    }

    public ProductDetailsVM getProductDetails(Long id) {
        return queryService.findDetailsById(id)
            .orElseThrow(() -> new ResourceNotFoundException("Product not found"));
    }
}
```

## Benefits

- JdbcTemplate faster than JPA for reads
- No lazy loading issues
- Clear separation of read/write models
- Returns View Models, never entities
- Read-only optimization with `@Transactional(readOnly = true)`
