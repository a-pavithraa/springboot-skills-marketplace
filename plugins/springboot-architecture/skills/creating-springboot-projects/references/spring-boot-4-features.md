# Spring Boot 4 New Features Reference

## Overview

Spring Boot 4 (with Java 25) includes six major features that eliminate the need for external libraries and improve developer experience.

## 1. TestRestClient - Modern REST Testing

**Replaces:** TestRestTemplate

**Benefits:**
- Fluent, readable API for integration tests
- Built-in API versioning support with `.apiVersion("2.0")`
- Better type safety with ParameterizedTypeReference
- More intuitive assertions

**Template:** `testrestclient-test.java`

**Basic Usage:**
```java
@SpringBootTest(webEnvironment = RANDOM_PORT)
class ProductControllerTest {
    @Autowired
    private WebApplicationContext context;

    private RestTestClient client;

    @BeforeEach
    void setup() {
        client = RestTestClient.bindToApplicationContext(context)
                .apiVersionInserter(ApiVersionInserter.useHeader("API-Version"))
                .build();
    }

    @Test
    void shouldGetProduct() {
        ProductVM product = client.get()
                .uri("/api/products/{id}", "PRD-001")
                .exchange()
                .expectStatus().isOk()
                .expectBody(ProductVM.class)
                .returnResult()
                .getResponseBody();

        assertThat(product.id()).isEqualTo("PRD-001");
    }
}
```

**Key Methods:**
- `.get()`, `.post()`, `.patch()`, `.delete()` - HTTP methods
- `.uri()` - Set request URI with path variables
- `.apiVersion("2.0")` - Set API version header
- `.exchange()` - Execute request
- `.expectStatus()` - Assert status code
- `.expectBody()` - Assert response body

## 2. Native Resiliency Features

**Replaces:** Spring Cloud Circuit Breaker, Resilience4j

**Benefits:**
- Zero external dependencies
- Simpler configuration
- Lower overhead
- Production-ready defaults

**Template:** `resilience-service.java`

### @Retryable - Automatic Retries

```java
@Retryable(
    maxRetries = 5L,
    delay = 2000L,
    includes = {RuntimeException.class}
)
public Optional<Product> fetchFromExternalApi(String id) {
    return externalClient.getById(id);
}
```

**Use cases:**
- External API calls with transient failures
- Database operations during brief connection issues
- Network operations with temporary disruptions

### @CircuitBreaker - Fail Fast

```java
@CircuitBreaker(
    failureThreshold = 5,
    waitDurationInOpenState = 30000L,
    slidingWindowSize = 10
)
public List<Product> fetchFromUnreliableService() {
    return externalClient.getAll();
}
```

**States:**
- CLOSED: Normal operation
- OPEN: Too many failures, fail fast
- HALF_OPEN: Testing if service recovered

**Use cases:**
- Protect against failing downstream services
- Prevent resource exhaustion
- Fail fast when dependencies are down

### @ConcurrencyLimit - Rate Limiting

```java
@ConcurrencyLimit(5)
public void processExpensiveOperation(String id) {
    performExpensiveWork(id);
}
```

**Use cases:**
- Limit expensive operations (heavy DB queries)
- Prevent thread pool exhaustion
- Rate limiting for external API calls
- Bulkhead pattern implementation

### Combining Patterns

```java
@Retryable(maxRetries = 3L, delay = 1000L)
@CircuitBreaker(failureThreshold = 5)
public Product fetchWithResiliency(String id) {
    return externalClient.getById(id)
            .orElseThrow(() -> new NotFoundException("Not found: " + id));
}
```

**Configuration (application.yml):**
```yaml
spring:
  resilience:
    retry:
      enabled: true
      max-attempts: 3
      wait-duration: 1s
    circuit-breaker:
      enabled: true
      failure-rate-threshold: 50
      wait-duration-in-open-state: 30s
    rate-limiter:
      enabled: true
      limit-for-period: 10
      limit-refresh-period: 1s
```

## 3. HTTP Service Client Simplification

**Replaces:** Manual RestClient/WebClient setup with HttpServiceProxyFactory

**Benefits:**
- Declarative interface-based clients
- Auto-configuration with @ImportHttpServices
- Less boilerplate
- Type-safe API definitions

**Template:** `http-service-client.java`

**Before Spring Boot 4:**
```java
@Bean
ProductClient productClient(RestClient.Builder builder) {
    RestClient restClient = builder.baseUrl("http://api.example.com").build();
    var factory = HttpServiceProxyFactory
            .builderFor(RestClientAdapter.create(restClient))
            .build();
    return factory.createClient(ProductClient.class);
}
```

**With Spring Boot 4:**
```java
// 1. Define interface
@HttpExchange
public interface ProductClient {
    @GetExchange(url = "/api/products/{id}")
    Optional<ProductDTO> findById(@PathVariable Long id);

    @PostExchange(url = "/api/products")
    ProductDTO create(CreateProductRequest request);
}

// 2. Auto-configure
@Configuration
@ImportHttpServices(ProductClient.class)
public class ClientConfig {
    // That's it!
}
```

**Features:**
- `@HttpExchange` - Mark interface as HTTP client
- `@GetExchange`, `@PostExchange`, `@PutExchange`, `@DeleteExchange` - HTTP methods
- API versioning support: `@GetExchange(url = "...", version = "2.0")`
- Path variables: `@PathVariable`
- Query params: `@RequestParam`
- Request body: Method parameter

**Configuration (application.yml):**
```yaml
spring:
  web:
    client:
      connect-timeout: 5s
      read-timeout: 10s
  http:
    services:
      product-service:
        url: http://localhost:8080
```

## 4. API Versioning

**Replaces:** Custom versioning implementations, external libraries

**Benefits:**
- Native Spring Boot support
- Clean URL structure (with header approach)
- Easy to test
- Works with HTTP Service Client

**Template:** `api-versioning-config.java`

**Configuration:**
```java
@Configuration
public class ApiVersioningConfig implements WebMvcConfigurer {
    @Override
    public void configureApiVersioning(ApiVersionConfigurer configurer) {
        configurer
                .addSupportedVersions("1.0", "2.0", "3.0")
                .setDefaultVersion("1.0")
                .useRequestHeader("API-Version");  // Recommended
    }
}
```

**Versioning Strategies:**
1. **Request Header** (recommended): `API-Version: 2.0`
2. **Query Parameter**: `/api/products?version=2.0`
3. **Media Type**: `Accept: application/json;ver=2.0`

**Controller Implementation:**
```java
@RestController
@RequestMapping("/api/products")
public class ProductController {

    @GetMapping(value = "/search", version = "1.0")
    public List<ProductVM> searchV1(@RequestParam("q") String query) {
        return service.searchByTitle(query);
    }

    @GetMapping(value = "/search", version = "2.0")
    public List<ProductEnrichedVM> searchV2(@RequestParam("q") String query) {
        return service.searchWithDetails(query);
    }
}
```

**Testing with TestRestClient:**
```java
client.get()
        .uri("/api/products/search?q=test")
        .apiVersion("2.0")  // Sets API-Version header
        .exchange()
        .expectStatus().isOk();
```

**HTTP Service Client with Versioning:**
```java
@HttpExchange
public interface ProductClient {
    @GetExchange(url = "/api/products/search", version = "1.0")
    List<ProductVM> searchV1(@RequestParam("q") String query);

    @GetExchange(url = "/api/products/search", version = "2.0")
    List<ProductEnrichedVM> searchV2(@RequestParam("q") String query);
}
```

## 5. Spring Data AOT - Native Image Support

**Benefits:**
- Faster startup with GraalVM native images
- Better performance for cloud/serverless
- Reduced memory footprint

**Configuration (pom.xml):**
```xml
<build>
    <plugins>
        <plugin>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-maven-plugin</artifactId>
            <executions>
                <execution>
                    <id>process-aot</id>
                    <goals>
                        <goal>process-aot</goal>
                    </goals>
                </execution>
            </executions>
        </plugin>
    </plugins>
</build>
```

**When to use:**
- Cloud-native applications
- Serverless deployments (AWS Lambda, Google Cloud Functions)
- Applications needing fast startup
- Containerized microservices

**Limitations:**
- Reflection and dynamic proxies may need hints
- Some libraries may not be fully compatible
- Build time increases

## 6. JSpecify Null-Safety

**Benefits:**
- Compile-time null checking
- Better IDE support
- Improved code documentation
- Works with Kotlin null safety

**Template:** `package-info-jspecify.java`

**Package-level Configuration:**
```java
@NullMarked
package com.example.products;

import org.jspecify.annotations.NullMarked;
```

**Usage:**
```java
// All types are non-null by default
public class ProductEntity {
    private Long id;              // Non-null (required)
    private String name;          // Non-null (required)
    @Nullable private String description;  // Nullable (optional)

    public @Nullable String getDescription() {
        return description;
    }
}

// Repository with Optional
public interface ProductRepository extends JpaRepository<ProductEntity, Long> {
    // Good: Use Optional for potentially absent values
    Optional<ProductEntity> findByName(String name);

    // Good: List is never null
    List<ProductEntity> findByStatus(String status);
}

// Controller with validation
@RestController
public class ProductController {
    @GetMapping("/{id}")
    public ProductVM getById(@PathVariable @NotNull Long id) {
        return service.findById(id);
    }

    @GetMapping("/search")
    public List<ProductVM> search(
            @RequestParam @Nullable String query,  // Optional
            @RequestParam(defaultValue = "0") int page
    ) {
        return service.search(query, page);
    }
}
```

**IDE Configuration:**
- IntelliJ IDEA: Settings → Editor → Inspections → Nullability problems
- Eclipse: Preferences → Java → Compiler → Errors/Warnings → Null analysis

**Best Practices:**
- Use @Nullable sparingly - most things should be non-null
- Prefer Optional<T> for return types over @Nullable
- Use @Nullable for optional fields in entities/records
- Validate at API boundaries (controllers, external integrations)
- Fail fast - throw exceptions early for invalid nulls

## Dependencies

All Spring Boot 4 features are included by default. No additional dependencies required.

**Verify versions:**
```xml
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>4.0.0</version>
</parent>

<properties>
    <java.version>25</java.version>
</properties>
```

## Migration from Spring Boot 3

| Spring Boot 3 | Spring Boot 4 | Notes |
|---------------|---------------|-------|
| TestRestTemplate | TestRestClient | More fluent API |
| Resilience4j | @Retryable, @CircuitBreaker | Native annotations |
| Manual HttpServiceProxyFactory | @ImportHttpServices | Auto-configuration |
| Custom versioning | ApiVersionConfigurer | Native support |
| Spring Nullability | JSpecify @NullMarked | Better IDE support |

**Breaking Changes:**
- TestRestTemplate still works but deprecated
- Some Resilience4j annotations need migration to native equivalents
- HttpServiceProxyFactory manual setup still works but unnecessary
