# DTO Projections Reference

Use projections for read-only queries to fetch only needed columns.

## Table of Contents

1. [Java Records (Recommended)](#java-records-recommended)
2. [Nested Records — not directly addressable in JPQL](#nested-records-not-directly-addressable-in-jpql)
3. [Interface Projections](#interface-projections)
4. [Native Queries with Projections](#native-queries-with-projections)
5. [When to Use What](#when-to-use-what)
6. [Hypersistence Utils (Optional)](#hypersistence-utils-optional)

---

## Java Records (Recommended)

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

## Nested Records — not directly addressable in JPQL

Jakarta Persistence 3.2 only allows top-level `NEW` constructor expressions in
the `SELECT` clause, and Spring Data JPA's class-based DTO projections do not
support nested projections. Hibernate has its own non-portable extension for
nested constructors, but the portable patterns are:

**Option A — flat record + service-layer assembly (recommended)**

```java
public record ProductDetails(Long id, String name, CategoryInfo category) {
    public record CategoryInfo(Long id, String name) {}
}

record ProductFlatRow(Long id, String name, Long categoryId, String categoryName) {}

@Query("""
    SELECT new com.example.ProductFlatRow(p.id, p.name, c.id, c.name)
    FROM ProductEntity p
    JOIN p.category c
    WHERE p.id = :id
    """)
ProductFlatRow findFlatById(@Param("id") Long id);

// Service:
ProductDetails details(Long id) {
    var row = repository.findFlatById(id);
    return new ProductDetails(row.id(), row.name(),
            new ProductDetails.CategoryInfo(row.categoryId(), row.categoryName()));
}
```

**Option B — interface projection (Spring Data does nest these)**

```java
public interface ProductDetailsView {
    Long getId();
    String getName();
    CategoryView getCategory();

    interface CategoryView {
        Long getId();
        String getName();
    }
}

ProductDetailsView findById(Long id); // derived query works directly
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

- **Records**: Default choice — clean, immutable, work seamlessly with JPQL `new com.example.Foo(...)` constructor expressions
- **Interface Projections**: Simple cases, but watch for N+1
- **Native Queries**: Complex aggregations, database-specific features

## Hypersistence Utils (Optional)

To avoid fully-qualified class names in JPQL:

```xml
<dependency>
    <groupId>io.hypersistence</groupId>
    <artifactId>hypersistence-utils-hibernate-73</artifactId>
    <version>3.15.3</version>
</dependency>
```

> Spring Boot 4.1.x ships Hibernate 7.4.1.Final. Hypersistence publishes `-hibernate-70`, `-hibernate-71`, and `-hibernate-73` (no `-72`, and no `-74` yet); `-hibernate-73` is the newest published module and the closest fit for Boot 4.1.x — verify it runs against 7.4.1. Confirm the latest version on Maven Central before pinning: https://central.sonatype.com/artifact/io.hypersistence/hypersistence-utils-hibernate-73/versions

Register in config:
```java
@Bean
public HibernatePropertiesCustomizer hibernatePropertiesCustomizer() {
    return properties -> properties.put("hibernate.integrator_provider",
        (IntegratorProvider) () -> Collections.singletonList(
            new ClassImportIntegrator(List.of(ProductSummary.class))));
}
```
