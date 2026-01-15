# Query Patterns Reference

## Simple Query Methods

Use derived query methods for simple lookups (1-2 properties):
```java
Optional<Product> findByCode(String code);
List<Product> findByStatus(Status status);
```

## @Query with JPQL

Use for 3+ filters, joins, or readability:
```java
@Query("""
    SELECT DISTINCT o
    FROM OrderEntity o
    LEFT JOIN FETCH o.items
    WHERE o.userId = :userId
    AND o.status IN :statuses
    ORDER BY o.createdAt DESC
    """)
List<OrderEntity> findUserOrders(@Param("userId") Long userId,
                                  @Param("statuses") List<OrderStatus> statuses);
```

**Key points:**
- Use text blocks `"""` for readability
- Always use `@Param` for parameter binding
- Use `LEFT JOIN FETCH` to prevent N+1
- Use `DISTINCT` when fetching collections

## Pagination & Sorting

```java
@Query("""
    SELECT e FROM ProductEntity e
    WHERE e.category = :category
    """)
Page<ProductEntity> findByCategory(@Param("category") String category,
                                    Pageable pageable);

// Usage
Pageable pageable = PageRequest.of(0, 20, Sort.by("createdAt").descending());
Page<ProductEntity> page = repository.findByCategory("Electronics", pageable);
```

## Bulk Operations

```java
@Modifying
@Query("""
    UPDATE ProductEntity p
    SET p.status = :newStatus
    WHERE p.status = :oldStatus
    """)
int updateStatus(@Param("oldStatus") Status oldStatus,
                 @Param("newStatus") Status newStatus);
```

**Must be used with @Transactional in service layer.**

## Native Queries

Use only when JPQL is insufficient:
```java
@Query(value = """
    SELECT *
    FROM products e
    WHERE e.status = :status
    AND e.search_vector @@ to_tsquery(:searchTerm)
    """, nativeQuery = true)
List<ProductEntity> searchByFullText(@Param("status") String status,
                                      @Param("searchTerm") String searchTerm);
```

## Convenience Default Methods

```java
default ProductEntity getByCode(String code) {
    return findByCode(code)
        .orElseThrow(() -> new ResourceNotFoundException(
            "Product not found: " + code));
}
```

## N+1 Query Prevention

**Problem:**
```java
List<Order> orders = orderRepository.findAll();
for (Order order : orders) {
    order.getCustomer().getName(); // N+1!
}
```

**Solution - JOIN FETCH:**
```java
@Query("""
    SELECT o
    FROM Order o
    JOIN FETCH o.customer
    WHERE o.status = :status
    """)
List<Order> findWithCustomer(@Param("status") OrderStatus status);
```

**Solution - DTO Projection (better for reads):**
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
