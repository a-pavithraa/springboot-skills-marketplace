package {{PACKAGE}}.{{MODULE}}.client;

import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.service.annotation.GetExchange;
import org.springframework.web.service.annotation.HttpExchange;
import org.springframework.web.service.annotation.PostExchange;

import java.util.List;
import java.util.Optional;

/**
 * HTTP Service Client template (Spring Boot 4 simplified approach).
 *
 * Spring Boot 4 dramatically simplifies HTTP client creation:
 * - Define interface with @HttpExchange
 * - Use @GetExchange, @PostExchange, @PutExchange, @DeleteExchange
 * - Spring Boot auto-configures RestClient and creates proxy
 * - No manual HttpServiceProxyFactory setup needed!
 *
 * Benefits:
 * - Less boilerplate than RestTemplate or WebClient
 * - Type-safe API definitions
 * - Supports API versioning
 * - Built-in JSON serialization
 */
@HttpExchange
public interface {{NAME}}Client {

    /**
     * Simple GET request returning a list.
     */
    @GetExchange(url = "/api/{{MODULE}}")
    List<{{NAME}}DTO> findAll();

    /**
     * GET with path variable.
     */
    @GetExchange(url = "/api/{{MODULE}}/{id}")
    Optional<{{NAME}}DTO> findById(@PathVariable Long id);

    /**
     * GET with query parameters.
     */
    @GetExchange(url = "/api/{{MODULE}}/search")
    List<{{NAME}}DTO> search(@RequestParam("q") String query);

    /**
     * GET with API versioning (v1.0).
     */
    @GetExchange(url = "/api/{{MODULE}}/search", version = "1.0")
    List<{{NAME}}DTO> searchV1(@RequestParam("q") String query);

    /**
     * GET with API versioning (v2.0).
     */
    @GetExchange(url = "/api/{{MODULE}}/search", version = "2.0")
    List<{{NAME}}DTO> searchV2(@RequestParam("q") String query);

    /**
     * POST request.
     */
    @PostExchange(url = "/api/{{MODULE}}")
    {{NAME}}DTO create(Create{{NAME}}Request request);
}

// ============================================================
// CLIENT CONFIGURATION - Spring Boot 4 Simplified Approach
// ============================================================

// package {{PACKAGE}}.config;
//
// import org.springframework.context.annotation.Configuration;
// import org.springframework.web.service.registry.ImportHttpServices;
// import {{PACKAGE}}.{{MODULE}}.client.{{NAME}}Client;
//
// /**
//  * Spring Boot 4 HTTP Service Client configuration.
//  *
//  * Before Spring Boot 4, you had to manually create beans with
//  * HttpServiceProxyFactory and RestClientAdapter. Now it's just
//  * one annotation!
//  */
// @Configuration
// @ImportHttpServices({{NAME}}Client.class)
// public class ClientConfig {
//     // That's it! Spring Boot 4 handles the rest.
//     //
//     // Under the hood, Spring Boot:
//     // 1. Creates a RestClient.Builder
//     // 2. Configures HttpServiceProxyFactory
//     // 3. Registers the client bean in the context
// }

// ============================================================
// CONFIGURING BASE URL (application.yml)
// ============================================================

// spring:
//   web:
//     client:
//       connect-timeout: 5s
//       read-timeout: 10s
//   http:
//     services:
//       {{MODULE}}-service:
//         url: http://localhost:8080

// ============================================================
// USAGE IN SERVICE
// ============================================================

// package {{PACKAGE}}.{{MODULE}}.service;
//
// import {{PACKAGE}}.{{MODULE}}.client.{{NAME}}Client;
// import org.springframework.stereotype.Service;
// import java.util.List;
//
// @Service
// public class {{NAME}}IntegrationService {
//     private final {{NAME}}Client client;
//
//     public {{NAME}}IntegrationService({{NAME}}Client client) {
//         this.client = client;
//     }
//
//     public List<{{NAME}}DTO> fetchAll() {
//         return client.findAll();
//     }
//
//     public {{NAME}}DTO fetchById(Long id) {
//         return client.findById(id)
//             .orElseThrow(() -> new NotFoundException("{{NAME}} not found: " + id));
//     }
// }

// ============================================================
// ADVANCED: Custom RestClient Configuration
// ============================================================

// package {{PACKAGE}}.config;
//
// import org.springframework.beans.factory.annotation.Value;
// import org.springframework.context.annotation.Bean;
// import org.springframework.context.annotation.Configuration;
// import org.springframework.web.client.RestClient;
// import org.springframework.web.client.support.RestClientAdapter;
// import org.springframework.web.service.invoker.HttpServiceProxyFactory;
// import {{PACKAGE}}.{{MODULE}}.client.{{NAME}}Client;
//
// /**
//  * Use this approach if you need custom RestClient configuration:
//  * - Custom headers (authentication)
//  * - Interceptors
//  * - Error handlers
//  * - Custom message converters
//  */
// @Configuration
// public class CustomClientConfig {
//
//     @Bean
//     RestClient {{MODULE}}RestClient(
//             RestClient.Builder builder,
//             @Value("${services.{{MODULE}}.url}") String baseUrl
//     ) {
//         return builder
//                 .baseUrl(baseUrl)
//                 .defaultHeader("X-Client-Version", "1.0")
//                 .build();
//     }
//
//     @Bean
//     {{NAME}}Client {{MODULE}}Client(RestClient {{MODULE}}RestClient) {
//         var adapter = RestClientAdapter.create({{MODULE}}RestClient);
//         var factory = HttpServiceProxyFactory
//                 .builderFor(adapter)
//                 .build();
//         return factory.createClient({{NAME}}Client.class);
//     }
// }
