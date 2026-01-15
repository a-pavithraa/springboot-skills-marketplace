package {{PACKAGE}}.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.ApiVersionConfigurer;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * API Versioning Configuration (Spring Boot 4 native feature).
 *
 * Spring Boot 4 provides built-in API versioning support without external libraries.
 * Three versioning strategies:
 * 1. Request Header (recommended) - API-Version: 2.0
 * 2. Query Parameter - /api/books?version=2.0
 * 3. Media Type Parameter - Accept: application/json;ver=2.0
 *
 * Benefits:
 * - No external dependencies
 * - Clean URL structure (with header approach)
 * - Easy to test
 * - Works with HTTP Service Client (@HttpExchange)
 */
@Configuration
public class ApiVersioningConfig implements WebMvcConfigurer {

    @Override
    public void configureApiVersioning(ApiVersionConfigurer configurer) {
        configurer
                // Define supported versions
                .addSupportedVersions("1.0", "2.0", "3.0")

                // Set default version (used when client doesn't specify)
                .setDefaultVersion("1.0")

                // Choose versioning strategy (pick ONE)
                .useRequestHeader("API-Version");      // Recommended
                // .useQueryParam("version");           // Alternative
                // .useMediaTypeParameter(              // Alternative
                //     MediaType.APPLICATION_JSON, "ver"
                // );
    }
}

// ============================================================
// CONTROLLER WITH VERSIONED ENDPOINTS
// ============================================================

// package {{PACKAGE}}.{{MODULE}}.rest;
//
// import org.springframework.web.bind.annotation.*;
// import java.util.List;
//
// /**
//  * Controller demonstrating API versioning.
//  *
//  * Same endpoint path, different behavior based on version.
//  */
// @RestController
// @RequestMapping("/api/{{MODULE}}")
// public class {{NAME}}Controller {
//
//     private final {{NAME}}Service service;
//
//     public {{NAME}}Controller({{NAME}}Service service) {
//         this.service = service;
//     }
//
//     /**
//      * Version 1.0 - Returns simple list.
//      */
//     @GetMapping(value = "/search", version = "1.0")
//     public List<{{NAME}}VM> searchV1(@RequestParam("q") String query) {
//         return service.searchByTitle(query);
//     }
//
//     /**
//      * Version 2.0 - Returns enriched data with additional fields.
//      */
//     @GetMapping(value = "/search", version = "2.0")
//     public List<{{NAME}}EnrichedVM> searchV2(@RequestParam("q") String query) {
//         return service.searchWithDetails(query);
//     }
//
//     /**
//      * Version 3.0 - Returns paginated results.
//      */
//     @GetMapping(value = "/search", version = "3.0")
//     public Page<{{NAME}}VM> searchV3(
//             @RequestParam("q") String query,
//             @RequestParam(defaultValue = "0") int page,
//             @RequestParam(defaultValue = "20") int size
//     ) {
//         return service.searchPaginated(query, page, size);
//     }
//
//     /**
//      * Endpoint without version - uses default version (1.0).
//      */
//     @GetMapping
//     public List<{{NAME}}VM> findAll() {
//         return service.findAll();
//     }
// }

// ============================================================
// TESTING VERSIONED ENDPOINTS WITH TestRestClient
// ============================================================

// package {{PACKAGE}}.{{MODULE}}.rest;
//
// import org.junit.jupiter.api.BeforeEach;
// import org.junit.jupiter.api.Test;
// import org.springframework.beans.factory.annotation.Autowired;
// import org.springframework.boot.test.context.SpringBootTest;
// import org.springframework.test.web.servlet.client.RestTestClient;
// import org.springframework.web.client.ApiVersionInserter;
// import org.springframework.web.context.WebApplicationContext;
//
// import static org.assertj.core.api.Assertions.assertThat;
// import static org.springframework.boot.test.context.SpringBootTest.WebEnvironment.RANDOM_PORT;
//
// @SpringBootTest(webEnvironment = RANDOM_PORT)
// class {{NAME}}ControllerTests {
//
//     @Autowired
//     private WebApplicationContext context;
//
//     RestTestClient client;
//
//     @BeforeEach
//     void setup() {
//         client = RestTestClient.bindToApplicationContext(context)
//                 .apiVersionInserter(ApiVersionInserter.useHeader("API-Version"))
//                 .build();
//     }
//
//     @Test
//     void shouldUseDefaultVersion() {
//         var result = client.get()
//                 .uri("/api/{{MODULE}}/search?q=test")
//                 .exchange()
//                 .expectStatus().isOk()
//                 .expectBody(List.class)
//                 .returnResult()
//                 .getResponseBody();
//
//         assertThat(result).isNotNull();
//     }
//
//     @Test
//     void shouldUseVersion2() {
//         var result = client.get()
//                 .uri("/api/{{MODULE}}/search?q=test")
//                 .apiVersion("2.0")  // Sets API-Version header
//                 .exchange()
//                 .expectStatus().isOk()
//                 .expectBody(List.class)
//                 .returnResult()
//                 .getResponseBody();
//
//         assertThat(result).isNotNull();
//     }
// }

// ============================================================
// TESTING WITH MockMvcTester (Alternative)
// ============================================================

// package {{PACKAGE}}.{{MODULE}}.rest;
//
// import org.junit.jupiter.api.Test;
// import org.springframework.beans.factory.annotation.Autowired;
// import org.springframework.boot.test.context.SpringBootTest;
// import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
// import org.springframework.test.web.servlet.assertj.MockMvcTester;
// import org.springframework.test.web.servlet.assertj.MvcTestResult;
//
// import static org.assertj.core.api.Assertions.assertThat;
//
// @SpringBootTest
// @AutoConfigureMockMvc
// class {{NAME}}MockMvcTests {
//
//     @Autowired
//     MockMvcTester mvc;
//
//     @Test
//     void shouldTestWithVersion1() {
//         MvcTestResult result = mvc.get()
//                 .uri("/api/{{MODULE}}/search?q=test")
//                 .apiVersion("1.0")
//                 .exchange();
//
//         assertThat(result).hasStatusOk();
//     }
// }

// ============================================================
// HTTP SERVICE CLIENT WITH VERSIONING
// ============================================================

// package {{PACKAGE}}.{{MODULE}}.client;
//
// import org.springframework.web.service.annotation.GetExchange;
// import org.springframework.web.service.annotation.HttpExchange;
// import java.util.List;
//
// /**
//  * HTTP Service Client interface with versioned endpoints.
//  */
// @HttpExchange
// public interface {{NAME}}Client {
//
//     @GetExchange(url = "/api/{{MODULE}}/search", version = "1.0")
//     List<{{NAME}}VM> searchV1(@RequestParam("q") String query);
//
//     @GetExchange(url = "/api/{{MODULE}}/search", version = "2.0")
//     List<{{NAME}}EnrichedVM> searchV2(@RequestParam("q") String query);
// }
//
// // Configuration remains the same:
// // @Configuration
// // @ImportHttpServices({{NAME}}Client.class)
// // public class ClientConfig { }

// ============================================================
// MIGRATION STRATEGY
// ============================================================

// When adding new API version:
// 1. Keep old version endpoints running (backwards compatibility)
// 2. Add new version with improved behavior
// 3. Document breaking changes in release notes
// 4. Deprecate old version after migration period
// 5. Remove deprecated version in next major release
//
// Example deprecation:
// @GetMapping(value = "/search", version = "1.0")
// @Deprecated(since = "2.0.0", forRemoval = true)
// public List<{{NAME}}VM> searchV1(@RequestParam("q") String query) {
//     // Old implementation
// }
