package {{PACKAGE}}.{{MODULE}}.domain;

import {{PACKAGE}}.{{MODULE}}.domain.vo.{{NAME}}Code;
import {{PACKAGE}}.{{MODULE}}.domain.vo.{{NAME}}Id;
import {{PACKAGE}}.shared.ResourceNotFoundException;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;

/**
 * Repository template - collection-like interface for aggregate root.
 *
 * Key principles:
 * - Only for aggregate roots
 * - Use @Query with JPQL for custom queries
 * - Use default methods for convenience (getBy* throws if not found)
 * - Return domain objects from write, ViewModels from read (via QueryService)
 */
interface {{NAME}}Repository extends JpaRepository<{{NAME}}Entity, {{NAME}}Id> {

    // ==================== CUSTOM QUERIES ====================

    @Query("""
            SELECT e FROM {{NAME}}Entity e
            WHERE e.code = :code
            """)
    Optional<{{NAME}}Entity> findByCode(@Param("code") {{NAME}}Code code);

    @Query("""
            SELECT e FROM {{NAME}}Entity e
            WHERE e.status = {{PACKAGE}}.{{MODULE}}.domain.{{NAME}}Status.ACTIVE
            ORDER BY e.createdAt DESC
            """)
    List<{{NAME}}Entity> findAllActive();

    // ==================== CONVENIENCE METHODS ====================

    default {{NAME}}Entity getById({{NAME}}Id id) {
        return findById(id)
            .orElseThrow(() -> new ResourceNotFoundException(
                "{{NAME}} not found with id: " + id.id()));
    }

    default {{NAME}}Entity getByCode({{NAME}}Code code) {
        return findByCode(code)
            .orElseThrow(() -> new ResourceNotFoundException(
                "{{NAME}} not found with code: " + code.code()));
    }
}

// ============================================================
// EXAMPLE: ProductRepository
// ============================================================

// interface ProductRepository extends JpaRepository<ProductEntity, ProductId> {
//
//     @Query("""
//             SELECT p FROM ProductEntity p
//             WHERE p.sku = :sku
//             """)
//     Optional<ProductEntity> findBySku(@Param("sku") ProductSKU sku);
//
//     @Query("""
//             SELECT p FROM ProductEntity p
//             WHERE p.status = com.example.products.domain.ProductStatus.ACTIVE
//             AND p.quantity.value > 0
//             ORDER BY p.createdAt DESC
//             """)
//     List<ProductEntity> findAvailable();
//
//     @Query("""
//             SELECT p FROM ProductEntity p
//             WHERE p.price.amount BETWEEN :min AND :max
//             """)
//     List<ProductEntity> findByPriceRange(@Param("min") BigDecimal min,
//                                          @Param("max") BigDecimal max);
//
//     default ProductEntity getBySku(ProductSKU sku) {
//         return findBySku(sku)
//             .orElseThrow(() -> new ResourceNotFoundException(
//                 "Product not found: " + sku.code()));
//     }
// }
