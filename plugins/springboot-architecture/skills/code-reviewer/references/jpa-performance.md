# JPA Performance Guide

Spring Data JPA performance on Boot 4 (Hibernate 7), plus the few Jakarta Persistence 3.2 / Hibernate 7 facts that differ from older guidance.

## Contents

1. [N+1 queries](#n1-queries)
2. [Projections and pagination](#projections-and-pagination)
3. [Batch writes](#batch-writes)
4. [Read-only work and streaming](#read-only-work-and-streaming)
5. [Connection pool](#connection-pool)
6. [Indexes](#indexes)
7. [Detection and monitoring](#detection-and-monitoring)
8. [Checklist](#checklist)

---

## N+1 queries

One query loads N rows, then each row triggers another query for an association:

```java
List<Order> orders = orderRepository.findAll();      // 1 query
for (Order order : orders) {
    order.getCustomer().getName();                    // +1 query per order
    order.getItems().size();                          // +1 more per order
}
```

`@ManyToOne` and `@OneToOne` are EAGER by default in JPA. Set `fetch = FetchType.LAZY` on every association, then fetch what each use case needs:

| Fix | Use when |
|-----|----------|
| `JOIN FETCH` in `@Query` | You need entities with their associations |
| DTO projection | Read-only views (best performance) |
| `@EntityGraph(attributePaths = {"customer", "items"})` | Same as `JOIN FETCH` on a derived query method |
| `hibernate.default_batch_fetch_size: 50` | Global safety net. Loads lazy associations in batches with `IN (...)` |

```java
@Query("""
    SELECT o FROM Order o
    JOIN FETCH o.customer
    WHERE o.status = :status
    """)
List<Order> findWithCustomer(@Param("status") OrderStatus status);
```

Gotchas:

- **`JOIN FETCH` of a collection + `Pageable`:** Hibernate loads all rows and pages in memory. It logs "firstResult/maxResults specified with collection fetch; applying in memory". Set `hibernate.query.fail_on_pagination_over_collection_fetch=true` to fail instead. Fix: page the IDs first, then fetch the entities for those IDs, or use a DTO projection.
- **Two `List` collections in one fetch** throws `MultipleBagFetchException`. Fetch one collection per query in the same transaction (the persistence context fills the second collection on the entities the first query loaded), or rely on batch fetching. Don't switch to `Set` to silence it: the join still returns every child row multiplied by every other, for example 50 parents × 20 × 10 = 10,000 rows.
- **Lazy access outside a transaction** throws `LazyInitializationException`. Fetch in the query. Do not enable `open-in-view` to hide it.

## Projections and pagination

- Never return `findAll()` for tables that grow. Use `Pageable` (`PageRequest.of(0, 20, Sort.by("createdAt").descending())`).
- A list behind a paged screen takes `Pageable` even if that changes the response shape. Say so in the change summary rather than leaving the list unbounded (Haiku left it unbounded without this, `tests/baseline-results/scenario-24.md`).
- For a change to every row (repricing, status updates), use one bulk `UPDATE` rather than loading the rows in batches, unless each row needs entity logic or lifecycle callbacks.
- `Page` runs an extra count query. Use `Slice` when the UI does not need a total.
- For lists and API responses, select only the needed columns with a DTO projection (`SELECT new com.example.OrderSummary(o.id, c.name, o.total) ...`) or an interface projection. See `dto-projections.md`.

## Batch writes

```yaml
spring:
  jpa:
    properties:
      hibernate:
        jdbc:
          batch_size: 50
        order_inserts: true
        order_updates: true
```

- `saveAll()` loops over `save()`. It batches only when `batch_size` is set.
- **`GenerationType.IDENTITY` disables insert batching.** Hibernate needs each generated ID right away. Use `SEQUENCE` with `allocationSize > 1`, or application-generated IDs (TSID, UUID).
- For large imports, flush and clear the persistence context every batch, or memory grows with every entity:

```java
for (int i = 0; i < products.size(); i++) {
    entityManager.persist(products.get(i));
    if ((i + 1) % 50 == 0) {
        entityManager.flush();
        entityManager.clear();
    }
}
```

- For bulk updates or deletes, use a `@Modifying` JPQL query. It skips loading entities.

## Read-only work and streaming

- Put `@Transactional(readOnly = true)` on query services. Hibernate skips dirty checking and flushing. Override with `@Transactional` on write methods.
- Stream large results inside a transaction, close the stream, and set a fetch size:

```java
@QueryHints(@QueryHint(name = HINT_FETCH_SIZE, value = "50"))
@Query("SELECT p FROM Product p WHERE p.status = 'ACTIVE'")
Stream<Product> streamAllActive();

try (Stream<Product> stream = repository.streamAllActive()) {
    stream.forEach(this::process);
}
```

- For heavy reporting reads, `JdbcClient` with plain SQL is often simpler and faster than JPA.

## Connection pool

Boot uses HikariCP.

```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 10           # start small; measure
      connection-timeout: 30000
      leak-detection-threshold: 60000 # logs connections held longer than 60 s
```

- Size from measurement. A common starting point is `cores * 2 + 1` (the HikariCP pool-sizing guidance). Large pools (100+) add contention and can exceed the database's connection limit.
- Pool size × number of instances must stay below the database's `max_connections`.
- With virtual threads, many more threads can wait for connections. The pool becomes the limit. Do not raise it without checking the database.

## Indexes

Index columns in `WHERE`, `JOIN`, and `ORDER BY` clauses of frequent queries. Put the most selective column first in composite indexes. Add indexes in Flyway/Liquibase migrations:

```sql
CREATE INDEX idx_orders_customer_created ON orders (customer_id, created_at DESC);
```

## Detection and monitoring

Development:

```yaml
spring:
  jpa:
    properties:
      hibernate:
        format_sql: true
        generate_statistics: true    # logs query counts per session
        log_slow_query: 10           # ms; logs slower queries
logging:
  level:
    org.hibernate.SQL: DEBUG
    org.hibernate.orm.jdbc.bind: TRACE   # bound parameters on Hibernate 6/7
```

- Hibernate 7 removed `hibernate.session.events.log.LOG_QUERIES_SLOWER_THAN_MS`. Use `hibernate.log_slow_query`.
- The pre-6 logger `org.hibernate.type.descriptor.sql.BasicBinder` is ignored on Hibernate 6/7.
- In integration tests, assert query counts (Hibernate `Statistics`, or a datasource proxy) on hot paths to catch N+1 regressions.

Production:

- Watch `hikaricp.connections.pending` and `hikaricp.connections.usage` (Actuator + Micrometer).
- Use the database's slow-query log or `pg_stat_statements` for real query cost.

## Checklist

- [ ] All associations `LAZY`; needed ones fetched per query
- [ ] No lazy loading in loops; no `JOIN FETCH` of collections with pagination
- [ ] DTO projections for read-only lists
- [ ] Pagination on growing tables
- [ ] `batch_size` set; no `IDENTITY` IDs where batch inserts matter
- [ ] `@Transactional(readOnly = true)` on query services
- [ ] Pool sized from measurement; leak detection on
- [ ] Indexes for frequent filters and sorts
- [ ] Query logging in development; query counts tested on hot paths

## Version-specific facts (Jakarta Persistence 3.2, Hibernate 7, Boot 4.1)

- **Nested DTO projections:** Jakarta Persistence 3.2 allows only top-level `NEW` constructor expressions in `SELECT`, and Spring Data's class-based projections don't nest. Select a flat record and assemble nested views in the service, or use Hibernate's non-portable extension knowingly.
- **`@ManyToMany`** is first-class in Jakarta Persistence 3.2 with a `LAZY` default. Preferring an explicit join entity is a design choice (the link has attributes or lifecycle), not a spec rule.
- **To-one defaults:** `@ManyToOne` and `@OneToOne` are still `EAGER` by default. Flag every one without `fetch = FetchType.LAZY`.
- **Hypersistence Utils:** Boot 4.1 ships Hibernate 7.4. Hypersistence publishes `-hibernate-70`, `-71` and `-73` modules (no `-72` or `-74` as of October 2026). `-hibernate-73` is the closest fit; verify it against 7.4 before relying on it.

