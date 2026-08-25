package {{PACKAGE}};

import org.junit.jupiter.api.Test;
import org.springframework.modulith.core.ApplicationModules;
import org.springframework.modulith.docs.Documenter;

/**
 * Spring Modulith module boundary verification.
 *
 * Required for: Modular Monolith, Tomato, DDD+Hexagonal patterns.
 *
 * This test:
 * - Verifies no circular dependencies between modules
 * - Ensures modules only access each other's public APIs
 * - Fails build if module boundaries are violated
 */
class ModularityTest {

    ApplicationModules modules = ApplicationModules.of(Application.class);

    @Test
    void verifyModularity() {
        // Fails if:
        // - Circular dependencies exist
        // - Internal packages accessed from outside
        // - Module boundaries violated
        modules.verify();
    }

    @Test
    void printModuleStructure() {
        // Prints detected modules to console (useful for debugging)
        System.out.println(modules.toString());
    }

    @Test
    void generateDocumentation() {
        // Generates module documentation in target/modulith-docs/
        new Documenter(modules)
            .writeModulesAsPlantUml()
            .writeIndividualModulesAsPlantUml();
    }
}

// ============================================================
// MODULE STRUCTURE CONVENTIONS
// ============================================================
//
// Spring Modulith auto-detects modules as top-level packages:
//
// com.example.myapp/
// ├── products/          ← Module (auto-detected)
// │   ├── ProductsAPI.java       ← PUBLIC (can be accessed by other modules)
// │   ├── domain/                ← INTERNAL (only accessible within module)
// │   │   ├── ProductEntity.java
// │   │   └── ProductService.java
// │   └── rest/
// │       └── ProductController.java
// ├── orders/            ← Module (auto-detected)
// │   ├── OrdersAPI.java         ← PUBLIC
// │   └── domain/                ← INTERNAL
// └── shared/            ← Shared module (accessible by all)
//
// Rules:
// - Classes in module root (e.g., ProductsAPI) are PUBLIC
// - Classes in subpackages (e.g., domain/, rest/) are INTERNAL
// - INTERNAL classes can only be accessed within same module
// - Use *API classes for inter-module communication


// ============================================================
// EXAMPLE: Module API (Public Facade)
// ============================================================
//
// package com.example.products;
//
// @Service
// public class ProductsAPI {
//     private final ProductService productService;
//     private final ProductQueryService queryService;
//
//     // Only expose what other modules need
//     public ProductVM getProduct(ProductId id) {
//         return queryService.getById(id);
//     }
//
//     public void reserveStock(ProductId id, int quantity) {
//         productService.reserveStock(id, quantity);
//     }
// }
//
// // Usage from orders module:
// @Service
// public class OrderService {
//     private final ProductsAPI productsAPI;  // ✅ Allowed - public API
//     // private final ProductService productService;  // ❌ FAILS - internal
//
//     public void createOrder(OrderCmd cmd) {
//         productsAPI.reserveStock(cmd.productId(), cmd.quantity());
//     }
// }


// ============================================================
// PERSISTENT EVENTS (Cross-Module Communication)
// ============================================================
//
// Instead of direct API calls, use events for loose coupling:
//
// // Publishing module (products)
// @Service
// public class ProductService {
//     private final ApplicationEventPublisher events;
//
//     public void reserveStock(ProductId id, int qty) {
//         // ... business logic
//         events.publishEvent(new StockReserved(id, qty));
//     }
// }
//
// // Listening module (orders)
// @Service
// public class OrderEventListener {
//     // @ApplicationModuleListener always runs as:
//     //   @Async + @Transactional(REQUIRES_NEW) + @TransactionalEventListener
//     // — async, after the publishing transaction commits, in its own new
//     // transaction. Publications become PERSISTENT and REPLAYABLE only when
//     // a Modulith event registry starter (spring-modulith-starter-jdbc /
//     // -jpa / -mongodb / -neo4j) is on the classpath and its backing storage
//     // (e.g. the event_publication table for JDBC/JPA) is present. Without
//     // the registry the listener still runs, but a crash between commit and
//     // listener completion loses the event.
//     @ApplicationModuleListener
//     public void on(StockReserved event) {
//         // Handle event
//     }
// }


// ============================================================
// DEPENDENCIES
// ============================================================
//
// Add to pom.xml:
//
// <dependency>
//     <groupId>org.springframework.modulith</groupId>
//     <artifactId>spring-modulith-starter-core</artifactId>
// </dependency>
// <dependency>
//     <groupId>org.springframework.modulith</groupId>
//     <artifactId>spring-modulith-starter-jpa</artifactId>
// </dependency>
// <dependency>
//     <groupId>org.springframework.modulith</groupId>
//     <artifactId>spring-modulith-starter-test</artifactId>
//     <scope>test</scope>
// </dependency>
//
// Add BOM to dependencyManagement:
//
// <dependency>
//     <groupId>org.springframework.modulith</groupId>
//     <artifactId>spring-modulith-bom</artifactId>
//     <version>2.1.0</version>
//     <type>pom</type>
//     <scope>import</scope>
// </dependency>
