# Spring Boot 4 New Features Reference

## Table of Contents

1. [Overview](#overview)
2. [1. RestTestClient - Modern REST Testing](#1-resttestclient---modern-rest-testing)
3. [2. Native Resiliency Features](#2-native-resiliency-features)
4. [3. HTTP Service Client Simplification](#3-http-service-client-simplification)
5. [4. API Versioning](#4-api-versioning)
6. [5. Spring Data AOT - Native Image Support](#5-spring-data-aot---native-image-support)
7. [6. JSpecify Null-Safety](#6-jspecify-null-safety)
8. [Dependencies](#dependencies)
9. [Migration from Spring Boot 3](#migration-from-spring-boot-3)

---

## Overview

Spring Boot 4 (built on Spring Framework 7; Java 17 minimum) includes six major features that eliminate the need for external libraries and improve developer experience. Recommended toolchain: Java 25 — the current LTS, which Boot 4's tooling and Spring's null-safety guidance both target. Java 26 (GA March 2026) is the newest feature release but not an LTS; only adopt it if a project policy already moves to non-LTS releases.

## 1. RestTestClient - Modern REST Testing

**Recommended new HTTP test client.** `TestRestTemplate` is not deprecated, but `@SpringBootTest` no longer auto-provides it in Boot 4 — opt in via `@AutoConfigureTestRestTemplate` to keep existing tests, or migrate to `RestTestClient` for new ones.

**Benefits:**
- Fluent, readable API for integration tests
- Built-in API versioning support with `.apiVersion("2.0")`
- Better type safety with ParameterizedTypeReference
- More intuitive assertions

**Template:** `resttestclient-test.java`

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
                .apiVersionInserter(ApiVersionInserter.useHeader("X-API-Version"))
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
- `@Retryable` — automatic retry with backoff (`org.springframework.resilience.annotation`)
- `@ConcurrencyLimit` — concurrent-invocation throttling. From the Framework reference: "specifies a concurrency limit for an individual method ... meant to protect the target resource from being accessed from too many threads at the same time, similar to the effect of a pool size limit for a thread pool or a connection pool that blocks access if its limit is reached." This is **not** time-window rate limiting and **not** the Resilience4j bulkhead.

**What Still Requires External Libraries:**
- Circuit Breaker → Resilience4j (`spring-cloud-starter-circuitbreaker-resilience4j`)
- Time-window rate limiting (requests-per-second budgets) → Resilience4j or Bucket4j; `@ConcurrencyLimit` only caps in-flight concurrency.
- Resilience4j-style Bulkhead with queueing semantics → Resilience4j

**Benefits:**
- Native retry and concurrency features with zero dependencies
- Seamless reactive programming support
- Integration with Virtual Threads (Project Loom)

**Decision note:**
- Spring Retry is now maintenance-only and superseded by Spring Framework 7 resilience features.
- Prefer `org.springframework.resilience.annotation.*` for new Boot 4 projects and remove `spring-retry` if not needed.
- Reference: https://github.com/spring-projects/spring-retry

**Template:** `resilience-service.java`

### @Retryable - Automatic Retries (NATIVE)

```java
import org.springframework.resilience.annotation.Retryable;

@Service
public class ProductService {

    // 1 initial attempt + maxRetries — up to 5 total invocations here
    @Retryable(
        includes = {RuntimeException.class},
        maxRetries = 4,
        delay = 2000L  // milliseconds
    )
    public Optional<Product> fetchFromExternalApi(String id) {
        return externalClient.getById(id);
    }

    // Optional: Advanced configuration with exponential backoff (up to 4 total invocations)
    @Retryable(
        includes = {IOException.class},
        maxRetries = 3,
        delay = 1000,
        multiplier = 2
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
- `maxRetries` - Number of retries after the initial attempt (default: 3 — total invocations = 1 + maxRetries)
- `delay` / `delayString` - Delay between retries
- `multiplier` - Exponential backoff multiplier
- `maxDelay` - Maximum delay ceiling

**Use cases:**
- External API calls with transient failures
- Database operations during brief connection issues
- Network operations with temporary disruptions

### @ConcurrencyLimit - Concurrent Invocation Throttling (NATIVE)

```java
import org.springframework.resilience.annotation.ConcurrencyLimit;

@Service
public class ReportService {

    @ConcurrencyLimit(2)  // At most 2 invocations in flight at any time
    public void processExpensiveOperation(String id) {
        performExpensiveWork(id);
    }
}
```

Semantics: when the third caller arrives while 2 invocations are already running, it **blocks** until a slot frees up — same shape as a fixed-size connection pool. It is not a time-window rate limit and does not implement Resilience4j-style bulkhead queueing.

**Configuration:**
- Requires `@EnableResilientMethods` on a `@Configuration` class
- Package: `org.springframework.resilience.annotation.*`
- Particularly valuable with Virtual Threads, where caller threads are cheap and back-pressure has to come from somewhere

**Good fits:**
- Cap concurrent calls into an expensive downstream (DB report query, slow third-party API) to protect the resource
- Hold the in-flight count below a known safe ceiling regardless of how many caller threads exist

**NOT this annotation's job:**
- Time-window rate limiting ("≤ 100 requests/sec") — use Resilience4j or Bucket4j
- Resilience4j-style Bulkhead with explicit queue depth / wait timeout semantics — use Resilience4j

### RetryTemplate - Programmatic Retry (NATIVE)

For scenarios needing more control than `@Retryable`:

```java
import org.springframework.core.retry.RetryPolicy;
import org.springframework.core.retry.RetryTemplate;

@Service
public class DriverAssignmentService {

    private final RetryTemplate retryTemplate;

    public DriverAssignmentService() {
        // 1 initial attempt + maxRetries — up to 11 total invocations
        RetryPolicy retryPolicy = RetryPolicy.builder()
                .maxRetries(10)
                .delay(Duration.ofMillis(2000))
                .multiplier(1.5)
                .maxDelay(Duration.ofMillis(10000))
                .includes(NoDriversAvailableException.class)
                .build();

        this.retryTemplate = new RetryTemplate(retryPolicy);
    }

    public Driver assignDriver(Order order) {
        return retryTemplate.execute(() -> {
            // logic that may throw NoDriversAvailableException
            return findAvailableDriver(order);
        });
    }
}
```

**Observability with RetryListener:**

```java
import org.springframework.core.retry.RetryListener;
import org.springframework.core.retry.RetryPolicy;
import org.springframework.core.retry.Retryable;

@Component
public class MetricsRetryListener implements RetryListener {

    @Override
    public void beforeRetry(RetryPolicy policy, Retryable<?> retryable) {
        // track attempt count, log retry start
    }

    @Override
    public void onRetrySuccess(RetryPolicy policy, Retryable<?> retryable, Object result) {
        // track successful recovery
    }

    @Override
    public void onRetryFailure(RetryPolicy policy, Retryable<?> retryable, Throwable t) {
        // track exhausted retries
    }
}
```

Attach to template: `retryTemplate.setRetryListener(listener)`

Source: [danvega/quick-bytes](https://github.com/danvega/quick-bytes) (Spring Boot 4.0.0-RC2)

### Circuit Breaker - Requires Resilience4j

**NOT native in Spring Boot 4.** For circuit breaker patterns, use Resilience4j:

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-circuitbreaker-resilience4j</artifactId>
</dependency>
<!-- Use the Boot 4-specific starter. The dedicated resilience4j-spring-boot4 module is currently 2.4.0 on Maven Central — confirm the latest at https://central.sonatype.com/artifact/io.github.resilience4j/resilience4j-spring-boot4 before pinning. -->
<dependency>
    <groupId>io.github.resilience4j</groupId>
    <artifactId>resilience4j-spring-boot4</artifactId>
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

**⚠️ Note:** Verify the current Resilience4j release before upgrading — see [the Resilience4j releases page](https://github.com/resilience4j/resilience4j/releases). The dedicated `resilience4j-spring-boot4` module is the right starter for Boot 4; the older `resilience4j-spring-boot3` is for Boot 3 stacks.

## 3. HTTP Service Client Simplification

**What's new:** `@ImportHttpServices` auto-configuration (Spring Framework 7.0) replaces manual `HttpServiceProxyFactory` bean wiring. `@HttpExchange` itself exists since Framework 6.0.

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

// 2. Auto-configure — group organizes services sharing the same HTTP client config
@Configuration
@ImportHttpServices(group = "product", types = ProductClient.class)
public class ClientConfig {
    // That's it! RestClient is the default client type.
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
    clients:
      connect-timeout: 5s
    serviceclient:
      product:  # Group name (matches @ImportHttpServices group)
        base-url: http://localhost:8080
        read-timeout: 10s
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
      default: "1.0"
      supported: "1.0,2.0"
      use:
        header: X-API-Version
        # Alternative strategies (use only one resolver):
        # query-parameter: version
        # path-segment: 1
        # media-type-parameter[application/json]: version
```

**Configuration Option 2 - Java (`WebMvcConfigurer.configureApiVersioning`):**
```java
import org.springframework.web.accept.SemanticApiVersionParser;
import org.springframework.web.servlet.config.annotation.ApiVersionConfigurer;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class ApiVersioningConfig implements WebMvcConfigurer {

    @Override
    public void configureApiVersioning(ApiVersionConfigurer configurer) {
        configurer
                .useRequestHeader("X-API-Version")             // resolver
                // .useQueryParam("version")
                // .useMediaTypeParameter(MediaType.APPLICATION_JSON, "version")
                // .usePathSegment(1)
                .addSupportedVersions("1.0", "2.0")
                .setDefaultVersion("1.0")
                .setVersionParser(new SemanticApiVersionParser()); // optional — default
    }
}
```

Notes: `ApiVersionConfigurer` lives in `org.springframework.web.servlet.config.annotation`. The default parser is `SemanticApiVersionParser` from `org.springframework.web.accept`. There are no `ApiVersionResolver.fromHeader(...)` / `ApiVersionParser.semantic()` static factories.

**Versioning Strategies:**
1. **Request Header** (recommended): `X-API-Version: 2.0`
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

**Testing with RestTestClient:**
```java
client.get()
        .uri("/api/products/search?q=test")
        .apiVersion("2.0")  // Sets X-API-Version header
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

Boot 4 uses modular starters. Add only what you need:

| Starter | Provides |
|---------|----------|
| `spring-boot-starter-webmvc` | Spring MVC (replaces `spring-boot-starter-web`) |
| `spring-boot-starter-restclient` | RestClient / RestTemplate |
| `spring-boot-starter-webclient` | WebClient (reactive) |
| `spring-boot-starter-aspectj` | AOP / `@Retryable` / `@ConcurrencyLimit` support |

**Verify versions:**
```xml
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>4.1.0</version>
</parent>

<properties>
    <!-- Boot 4 baseline is 17. Recommended: 25 (current LTS). Use 21 for the
         previous LTS, 17 for stricter compatibility, or 26 (GA 2026-03-17)
         only when your project tracks non-LTS feature releases. -->
    <java.version>25</java.version>
</properties>
```

## Migration from Spring Boot 3

| Spring Boot 3 | Spring Boot 4 | Notes |
|---------------|---------------|-------|
| TestRestTemplate (auto-wired in Boot 3) | RestTestClient + `@AutoConfigureRestTestClient` (Boot 4) | `TestRestTemplate` is still supported; opt in with `@AutoConfigureTestRestTemplate`. New tests should prefer `RestTestClient`. |
| Resilience4j @Retry | @Retryable (native) | Now built into Spring Framework 7 |
| Manual concurrency control | @ConcurrencyLimit (native) | Now built into Spring Framework 7 |
| Resilience4j @CircuitBreaker | Still Resilience4j | Circuit breaker NOT native, still requires external library |
| Manual HttpServiceProxyFactory | @ImportHttpServices | Auto-configuration, zero boilerplate |
| Custom versioning | spring.mvc.apiversion.* | Native support via properties or beans |
| Spring Nullability | JSpecify @NullMarked | Better IDE support, standard annotations |

**Breaking Changes:**

- TestRestTemplate still works (not deprecated) but is no longer auto-provided by `@SpringBootTest` — opt in with `@AutoConfigureTestRestTemplate`; prefer `RestTestClient` for new tests
- @Retryable API different from Resilience4j version (different package and parameters)
- HttpServiceProxyFactory manual setup still works but unnecessary
- Circuit breaker still requires Resilience4j (check compatibility with Spring Boot 4)

**Migration Strategy:**

1. For tests still using `TestRestTemplate`, either add `@AutoConfigureTestRestTemplate` (minimum change) or migrate the test to `RestTestClient` + `@AutoConfigureRestTestClient`. `TestRestTemplate` itself is not deprecated.
2. Replace Resilience4j @Retry with native @Retryable (requires @EnableResilientMethods)
   - Change package: `org.springframework.resilience.annotation.*`
   - Update parameters: `retryFor` → `includes`; `maxAttempts` (total) → `maxRetries` (retries after the first call — subtract 1, so `maxAttempts = 4` becomes `maxRetries = 3`)
3. Keep Resilience4j for circuit breaker and advanced patterns
4. Replace manual HTTP client setup with @ImportHttpServices
5. Configure API versioning via spring.mvc.apiversion.* properties
