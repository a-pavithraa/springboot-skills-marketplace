# Spring Boot 4 New Features Reference

## Overview

Spring Boot 4 (with Java 25) includes six major features that eliminate the need for external libraries and improve developer experience.

## 1. RestTestClient - Modern REST Testing

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

**What's Native in Spring Framework 7:**
- `@Retryable` - Automatic retry support (from Spring Retry integration)
- `@ConcurrencyLimit` - Concurrency control and rate limiting

**What Still Requires External Libraries:**
- Circuit Breaker → Resilience4j (`spring-cloud-starter-circuitbreaker-resilience4j`)
- Advanced rate limiting → Resilience4j
- Bulkhead patterns → Resilience4j

**Benefits:**
- Native retry and concurrency features with zero dependencies
- Seamless reactive programming support
- Integration with Virtual Threads (Project Loom)

**Template:** `resilience-service.java`

### @Retryable - Automatic Retries (NATIVE)

```java
import org.springframework.resilience.annotation.Retryable;

@Service
public class ProductService {

    @Retryable(
        includes = {RuntimeException.class},
        maxRetries = 5,
        delay = 2000L  // milliseconds
    )
    public Optional<Product> fetchFromExternalApi(String id) {
        return externalClient.getById(id);
    }

    // Optional: Advanced configuration with exponential backoff
    @Retryable(
        includes = {IOException.class},
        maxRetries = 4,
        delayString = "500ms",
        multiplier = 1.5,
        maxDelay = 3000
    )
    public String callRemoteService() {
        // transient failures handled automatically
    }
}
```

**Configuration:**
- Requires `@EnableResilientMethods` on a `@Configuration` class
- Package: `org.springframework.resilience.annotation.*`
- Supports exponential backoff, jitter, and reactive types
- Works seamlessly with Virtual Threads

**Parameters:**
- `includes` - Exception types that trigger retry
- `excludes` - Exception types that should never retry
- `maxRetries` - Maximum retry attempts (default: 3)
- `delay` / `delayString` - Delay between retries
- `multiplier` - Exponential backoff multiplier
- `maxDelay` - Maximum delay ceiling

**Use cases:**
- External API calls with transient failures
- Database operations during brief connection issues
- Network operations with temporary disruptions

### @ConcurrencyLimit - Rate Limiting (NATIVE)

```java
import org.springframework.resilience.annotation.ConcurrencyLimit;

@Service
public class ReportService {

    @ConcurrencyLimit(2)  // Max 2 concurrent executions
    public void processExpensiveOperation(String id) {
        performExpensiveWork(id);
    }
}
```

**Configuration:**
- Requires `@EnableResilientMethods` on a `@Configuration` class
- Package: `org.springframework.resilience.annotation.*`
- Particularly valuable with Virtual Threads for controlling parallelism
- Implements bulkhead pattern for resource isolation

**Use cases:**
- Limit expensive operations (heavy DB queries)
- Prevent thread pool exhaustion
- Rate limiting for external API calls
- Bulkhead pattern implementation

### Circuit Breaker - Requires Resilience4j

**NOT native in Spring Boot 4.** For circuit breaker patterns, use Resilience4j:

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-circuitbreaker-resilience4j</artifactId>
</dependency>
<dependency>
    <groupId>io.github.resilience4j</groupId>
    <artifactId>resilience4j-spring-boot3</artifactId>
</dependency>
```

```java
@Service
public class ProductService {

    @CircuitBreaker(name = "productService", fallbackMethod = "fallbackFetch")
    public List<Product> fetchFromUnreliableService() {
        return externalClient.getAll();
    }

    private List<Product> fallbackFetch(Exception e) {
        return Collections.emptyList();
    }
}
```

**Configuration (application.yml):**
```yaml
resilience4j:
  circuitbreaker:
    instances:
      productService:
        failure-rate-threshold: 50
        wait-duration-in-open-state: 30s
        sliding-window-size: 10
```

**⚠️ Note:** As of December 2025, there are compatibility issues between Resilience4j and Spring Boot 4. Check the latest Resilience4j releases before upgrading.

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
  http:
    serviceclient:
      product-service:  # Group name
        base-url: http://localhost:8080
        connect-timeout: 5s
        read-timeout: 10s
        apiversion:
          default-version: "1.0"
          insert:
            header: API-Version
```

## 4. API Versioning

**Replaces:** Custom versioning implementations, external libraries

**Benefits:**
- Native Spring Boot support
- Clean URL structure (with header approach)
- Easy to test
- Works with HTTP Service Client

**Template:** `api-versioning-config.java`

**Configuration Option 1 - Properties (Recommended):**
```yaml
spring:
  mvc:
    apiversion:
      enabled: true
      strategy: header  # or: path, query-parameter, media-type
      default-version: "1.0"
      header-name: "API-Version"
```

**Configuration Option 2 - Java Beans:**
```java
@Configuration
public class ApiVersioningConfig {

    @Bean
    public ApiVersionResolver apiVersionResolver() {
        return ApiVersionResolver.fromHeader("API-Version");
        // Alternative: ApiVersionResolver.fromQueryParameter("version")
        // Alternative: ApiVersionResolver.fromMediaType()
    }

    @Bean
    public ApiVersionParser apiVersionParser() {
        return ApiVersionParser.semantic();  // Supports semver (1.0.0, 2.1.3)
    }
}
```

**Versioning Strategies:**
1. **Request Header** (recommended): `API-Version: 2.0`
2. **Query Parameter**: `/api/products?version=2.0`
3. **Media Type**: `Accept: application/json;ver=2.0`
4. **Path**: `/v2/api/products` (less common with native support)

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
    public ProductVM getById(@PathVariable Long id) {  // Non-null by default with @NullMarked
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
| TestRestTemplate | RestTestClient | More fluent API, better type safety |
| Resilience4j @Retry | @Retryable (native) | Now built into Spring Framework 7 |
| Manual concurrency control | @ConcurrencyLimit (native) | Now built into Spring Framework 7 |
| Resilience4j @CircuitBreaker | Still Resilience4j | Circuit breaker NOT native, still requires external library |
| Manual HttpServiceProxyFactory | @ImportHttpServices | Auto-configuration, zero boilerplate |
| Custom versioning | spring.mvc.apiversion.* | Native support via properties or beans |
| Spring Nullability | JSpecify @NullMarked | Better IDE support, standard annotations |

**Breaking Changes:**

- TestRestTemplate still works but deprecated
- @Retryable API different from Resilience4j version (different package and parameters)
- HttpServiceProxyFactory manual setup still works but unnecessary
- Circuit breaker still requires Resilience4j (check compatibility with Spring Boot 4)

**Migration Strategy:**

1. Replace TestRestTemplate with RestTestClient in tests
2. Replace Resilience4j @Retry with native @Retryable (requires @EnableResilientMethods)
   - Change package: `org.springframework.resilience.annotation.*`
   - Update parameters: `retryFor` → `includes`, `maxAttempts` → `maxRetries`
3. Keep Resilience4j for circuit breaker and advanced patterns
4. Replace manual HTTP client setup with @ImportHttpServices
5. Configure API versioning via spring.mvc.apiversion.* properties
