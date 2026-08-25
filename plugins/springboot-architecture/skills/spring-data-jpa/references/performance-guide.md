# Performance Optimization Guide

## Table of Contents

1. [N+1 Query Problem](#n1-query-problem)
2. [Batch Operations](#batch-operations)
3. [Pagination](#pagination)
4. [Query Hints](#query-hints)
5. [Read-Only Optimization](#read-only-optimization)
6. [Connection Pooling](#connection-pooling)
7. [Database Indexes](#database-indexes)
8. [Use Projections for Lists](#use-projections-for-lists)
9. [Avoid SELECT All Columns](#avoid-select-all-columns)
10. [Stream Large Result Sets](#stream-large-result-sets)
11. [Lazy Loading Best Practices](#lazy-loading-best-practices)
12. [Enable SQL Logging (Development)](#enable-sql-logging-development)
13. [Performance Checklist](#performance-checklist)
14. [Monitoring](#monitoring)

---

## N+1 Query Problem

**The Issue:**
```java
List<Order> orders = orderRepository.findAll(); // 1 query
for (Order order : orders) {
    String name = order.getCustomer().getName(); // N queries!
}
```

**Solutions:**

### 1. JOIN FETCH (Best for entities)
```java
@Query("""
    SELECT o
    FROM Order o
    JOIN FETCH o.customer
    WHERE o.status = :status
    """)
List<Order> findWithCustomer(@Param("status") OrderStatus status);
```

### 2. DTO Projection (Best for reads)
```java
@Query("""
    SELECT new com.example.OrderSummary(
        o.id, o.orderNumber, c.name, o.total
    )
    FROM Order o
    JOIN o.customer c
    WHERE o.status = :status
    """)
List<OrderSummary> findOrderSummaries(@Param("status") OrderStatus status);
```

### 3. @EntityGraph (Alternative)
```java
@EntityGraph(attributePaths = {"customer", "items"})
List<Order> findByStatus(OrderStatus status);
```

## Batch Operations

### Configure Batch Size
```yaml
# application.yml
spring:
  jpa:
    properties:
      hibernate:
        jdbc:
          batch_size: 25
        order_inserts: true
        order_updates: true
```

### Use saveAll()
```java
List<Product> products = createManyProducts();
productRepository.saveAll(products); // Iterates and calls save() per entity
```

> **Important:** `SimpleJpaRepository#saveAll` is implemented as a loop over `save(entity)` — it does **not** automatically batch on its own. To get real JDBC batch inserts you need to:
> 1. Set `hibernate.jdbc.batch_size` (e.g. `25`–`50`) and ideally `hibernate.order_inserts=true` / `order_updates=true`.
> 2. Use a non-IDENTITY ID strategy — `GenerationType.IDENTITY` forces a per-row round trip and disables batching; prefer `SEQUENCE` (allocation-size > 1) or an application-generated ID (TSID/UUID).
> 3. Avoid intervening flushes inside the loop.
>
> Without those, `saveAll` issues one INSERT per row regardless of the call shape.

### Flush & Clear for Large Batches
```java
for (int i = 0; i < products.size(); i++) {
    productRepository.save(products.get(i));
    if (i % 25 == 0) {
        entityManager.flush();
        entityManager.clear();
    }
}
```

## Pagination

Always use pagination for large result sets:

```java
Pageable pageable = PageRequest.of(0, 20, Sort.by("createdAt").desc());
Page<Product> page = productRepository.findByCategory("Electronics", pageable);
```

## Query Hints

```java
@QueryHints(@QueryHint(name = "org.hibernate.fetchSize", value = "50"))
@Query("SELECT p FROM Product p WHERE p.status = 'ACTIVE'")
Stream<Product> streamAllActive();
```

## Read-Only Optimization

```java
@Service
@Transactional(readOnly = true)  // Class-level for read services
public class ProductQueryService {

    public List<ProductVM> findAll() {
        // Read operations - no flush, no dirty checking
    }

    @Transactional  // Override for writes
    public void updateStock(Long id, int quantity) {
        // Write operation
    }
}
```

## Connection Pooling

Spring Boot uses HikariCP by default (optimal):

```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 10
      minimum-idle: 5
      connection-timeout: 30000
```

## Database Indexes

Add indexes for frequently queried columns:

```sql
CREATE INDEX idx_products_status ON products(status);
CREATE INDEX idx_products_category_status ON products(category_id, status);
CREATE INDEX idx_orders_user_created ON orders(user_id, created_at DESC);
```

## Use Projections for Lists

**DON'T:**
```java
List<Product> products = productRepository.findAll(); // Fetches all columns
```

**DO:**
```java
List<ProductSummary> summaries = productRepository.findAllSummaries(); // Only needed columns
```

## Avoid SELECT All Columns

**DON'T:**
```sql
SELECT * FROM products WHERE status = 'ACTIVE'
```

**DO:**
```sql
SELECT id, name, price FROM products WHERE status = 'ACTIVE'
```

## Stream Large Result Sets

```java
@QueryHints(@QueryHint(name = HINT_FETCH_SIZE, value = "50"))
@Query("SELECT p FROM Product p WHERE p.status = 'ACTIVE'")
Stream<Product> streamAllActive();

// Usage
try (Stream<Product> stream = repository.streamAllActive()) {
    stream.forEach(product -> process(product));
}
```

## Lazy Loading Best Practices

1. **Use FetchType.LAZY** for all associations
2. **Use JOIN FETCH** in queries when you need associations
3. **Never access lazy associations outside transaction**
4. **Use DTOs** for read-only API responses

## Enable SQL Logging (Development)

```yaml
spring:
  jpa:
    show-sql: true
    properties:
      hibernate:
        format_sql: true
        use_sql_comments: true
logging:
  level:
    org.hibernate.SQL: DEBUG
    # Hibernate 6+ logger for bound parameter values.
    # (Pre-6 used org.hibernate.type.descriptor.sql.BasicBinder — that name is
    # silently ignored on Hibernate 6/7, so logs go quiet without warning.)
    org.hibernate.orm.jdbc.bind: TRACE
```

## Performance Checklist

- [ ] Use FetchType.LAZY for all relationships
- [ ] Add JOIN FETCH for needed associations in queries
- [ ] Use DTO projections for read-only queries
- [ ] Enable query logging in dev to check for N+1
- [ ] Configure JDBC batch size for bulk operations
- [ ] Use pagination for large result sets
- [ ] Add database indexes for frequently queried columns
- [ ] Use @Transactional(readOnly = true) for query services
- [ ] Avoid calling lazy associations outside transactions
- [ ] Use JdbcTemplate for performance-critical reads
- [ ] Monitor query execution time in production
- [ ] Use connection pooling (HikariCP default)

## Monitoring

```java
// Add to application.yml for metrics
management:
  endpoints:
    web:
      exposure:
        include: health,metrics,prometheus
  metrics:
    enable:
      hibernate: true
```

Check metrics:
- `hikaricp.connections.*` - Connection pool usage
- `hibernate.query.executions` - Query count
- `hibernate.sessions.*` - Session statistics
