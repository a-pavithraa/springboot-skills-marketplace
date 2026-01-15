# DTO Projections Reference

Use projections for read-only queries to fetch only needed columns.

## Java Records (Recommended for Spring Boot 3+)

```java
public record ProductSummary(
    Long id,
    String sku,
    String name,
    BigDecimal price
) {}

// Repository
@Query("""
    SELECT new com.example.products.ProductSummary(
        p.id, p.sku, p.name, p.price
    )
    FROM ProductEntity p
    WHERE p.status = 'ACTIVE'
    ORDER BY p.createdAt DESC
    """)
List<ProductSummary> findActiveSummaries();
```

**Benefits:** Immutable, equals/hashCode built-in, concise

## Nested Records

```java
public record ProductDetails(
    Long id,
    String name,
    CategoryInfo category
) {
    public record CategoryInfo(Long id, String name) {}
}

@Query("""
    SELECT new com.example.ProductDetails(
        p.id, p.name,
        new com.example.ProductDetails$CategoryInfo(c.id, c.name)
    )
    FROM ProductEntity p
    JOIN p.category c
    WHERE p.id = :id
    """)
ProductDetails findDetailsById(@Param("id") Long id);
```

## Interface Projections

```java
public interface ProductView {
    Long getId();
    String getName();
    BigDecimal getPrice();
}

@Query("""
    SELECT p.id as id, p.name as name, p.price as price
    FROM ProductEntity p
    WHERE p.featured = true
    """)
List<ProductView> findFeatured();
```

**Note:** Can cause N+1 if used with nested associations. Use with caution.

## Native Queries with Projections

```java
public interface ProductStatsView {
    String getCategory();
    Long getCount();
    BigDecimal getAvgPrice();
}

@Query(value = """
    SELECT
        c.name as category,
        COUNT(*) as count,
        AVG(p.price) as avgPrice
    FROM products p
    JOIN categories c ON p.category_id = c.id
    GROUP BY c.name
    """, nativeQuery = true)
List<ProductStatsView> findStatsByCategory();
```

## When to Use What

- **Records**: Default choice for Spring Boot 3+
- **Interface Projections**: Simple cases, but watch for N+1
- **Native Queries**: Complex aggregations, database-specific features

## Hypersistence Utils (Optional)

To avoid fully-qualified class names in JPQL:

```xml
<dependency>
    <groupId>io.hypersistence</groupId>
    <artifactId>hypersistence-utils-hibernate-63</artifactId>
    <version>3.7.0</version>
</dependency>
```

Register in config:
```java
@Bean
public HibernatePropertiesCustomizer hibernatePropertiesCustomizer() {
    return properties -> properties.put("hibernate.integrator_provider",
        (IntegratorProvider) () -> Collections.singletonList(
            new ClassImportIntegrator(List.of(ProductSummary.class))));
}
```
