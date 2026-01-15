# Custom Repositories Reference

Use for complex operations beyond standard JpaRepository.

## Structure

1. **Custom interface** - Define methods
2. **Implementation class** - Named `<Repository>Impl`
3. **Main repository** - Extends both JpaRepository and custom interface

## Criteria API - Dynamic Queries

```java
public interface ProductRepositoryCustom {
    List<ProductEntity> findByDynamicCriteria(ProductSearchCriteria criteria);
}

@Repository
class ProductRepositoryImpl implements ProductRepositoryCustom {

    @PersistenceContext
    private EntityManager entityManager;

    @Override
    public List<ProductEntity> findByDynamicCriteria(ProductSearchCriteria criteria) {
        CriteriaBuilder cb = entityManager.getCriteriaBuilder();
        CriteriaQuery<ProductEntity> query = cb.createQuery(ProductEntity.class);
        Root<ProductEntity> root = query.from(ProductEntity.class);

        List<Predicate> predicates = new ArrayList<>();

        if (criteria.getName() != null) {
            predicates.add(cb.like(
                cb.lower(root.get("name")),
                "%" + criteria.getName().toLowerCase() + "%"
            ));
        }

        if (criteria.getMinPrice() != null) {
            predicates.add(cb.ge(root.get("price"), criteria.getMinPrice()));
        }

        query.where(cb.and(predicates.toArray(new Predicate[0])));
        query.orderBy(cb.desc(root.get("createdAt")));

        return entityManager.createQuery(query)
            .setMaxResults(criteria.getLimit())
            .getResultList();
    }
}

// Main repository
public interface ProductRepository extends JpaRepository<ProductEntity, Long>,
                                           ProductRepositoryCustom {
    Optional<ProductEntity> findBySku(String sku);
}
```

## Bulk Operations

```java
@Transactional
public int bulkUpdateStatus(Status oldStatus, Status newStatus) {
    return entityManager.createQuery("""
        UPDATE ProductEntity p
        SET p.status = :newStatus,
            p.updatedAt = CURRENT_TIMESTAMP
        WHERE p.status = :oldStatus
        """)
        .setParameter("oldStatus", oldStatus)
        .setParameter("newStatus", newStatus)
        .executeUpdate();
}
```

**Important:**
- Bypasses entity lifecycle (no @PreUpdate callbacks)
- Requires @Transactional
- Call `entityManager.flush()` and `clear()` after bulk ops

## Native Queries

```java
@SuppressWarnings("unchecked")
public List<ProductEntity> findUsingNativeQuery(String param) {
    return entityManager.createNativeQuery("""
        SELECT e.*
        FROM products e
        WHERE e.search_vector @@ plainto_tsquery(:param)
        ORDER BY ts_rank(e.search_vector, plainto_tsquery(:param)) DESC
        LIMIT 20
        """, ProductEntity.class)
        .setParameter("param", param)
        .getResultList();
}
```

## EntityManager Operations

```java
// Force flush and clear for batch operations
public void flushAndClear() {
    entityManager.flush();
    entityManager.clear();
}

// Detach entity from persistence context
public void detach(ProductEntity entity) {
    entityManager.detach(entity);
}

// Refresh entity from database
public void refresh(ProductEntity entity) {
    entityManager.refresh(entity);
}
```

## Best Practices

1. **Naming**: Implementation must be named `<Repository>Impl` (or configure suffix)
2. **Transactions**: Add @Transactional to write operations
3. **Type Safety**: Criteria API provides compile-time checking
4. **Performance**: Use setMaxResults/setFirstResult for pagination
5. **Testing**: Requires @DataJpaTest with actual EntityManager
