package {{PACKAGE}}.{{MODULE}}.rest.converters;

import {{PACKAGE}}.{{MODULE}}.domain.vo.{{NAME}};
import org.springframework.core.convert.converter.Converter;
import org.springframework.stereotype.Component;

/**
 * Spring Converter for Value Object binding in @PathVariable and @RequestParam.
 *
 * Enables:
 *   @GetMapping("/{code}")
 *   public Response get(@PathVariable ProductSKU code) { ... }
 *
 * Instead of:
 *   @GetMapping("/{code}")
 *   public Response get(@PathVariable String code) {
 *       ProductSKU sku = ProductSKU.of(code);  // Manual conversion
 *   }
 */
@Component
public class StringTo{{NAME}}Converter implements Converter<String, {{NAME}}> {

    @Override
    public {{NAME}} convert(String source) {
        return {{NAME}}.of(source);
    }
}


// ============================================================
// EXAMPLES
// ============================================================

// --- ProductSKU Converter ---
// @Component
// public class StringToProductSKUConverter implements Converter<String, ProductSKU> {
//     @Override
//     public ProductSKU convert(String source) {
//         return ProductSKU.of(source);
//     }
// }

// --- ProductId Converter (Long to Value Object) ---
// @Component
// public class StringToProductIdConverter implements Converter<String, ProductId> {
//     @Override
//     public ProductId convert(String source) {
//         return ProductId.of(Long.parseLong(source));
//     }
// }

// --- Email Converter ---
// @Component
// public class StringToEmailConverter implements Converter<String, Email> {
//     @Override
//     public Email convert(String source) {
//         return Email.of(source);
//     }
// }


// ============================================================
// USAGE IN CONTROLLER
// ============================================================

// @RestController
// @RequestMapping("/api/products")
// class ProductController {
//
//     // With converter - clean, type-safe
//     @GetMapping("/{sku}")
//     public ProductVM getProduct(@PathVariable ProductSKU sku) {
//         return queryService.getBySku(sku);  // Already a Value Object!
//     }
//
//     @GetMapping("/search")
//     public List<ProductVM> search(@RequestParam Email email) {
//         return queryService.findByEmail(email);
//     }
// }


// ============================================================
// REGISTRATION (Usually automatic with @Component)
// ============================================================

// If converters aren't picked up automatically, register explicitly:
//
// @Configuration
// public class WebConfig implements WebMvcConfigurer {
//     @Override
//     public void addFormatters(FormatterRegistry registry) {
//         registry.addConverter(new StringToProductSKUConverter());
//         registry.addConverter(new StringToProductIdConverter());
//         registry.addConverter(new StringToEmailConverter());
//     }
// }
