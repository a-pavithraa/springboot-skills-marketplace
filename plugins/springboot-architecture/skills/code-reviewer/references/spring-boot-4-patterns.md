# Spring Boot 4 Patterns and Best Practices

## Table of Contents

1. [Dependency Management](#dependency-management)
2. [Modular Starters](#modular-starters)
3. [Jackson 3 Migration](#jackson-3-migration)
4. [Test Annotations](#test-annotations)
5. [Retry and Resilience](#retry-and-resilience)
6. [Observability](#observability)
7. [Problem Details (RFC 7807)](#problem-details-rfc-7807)
8. [Configuration](#configuration)
9. [Virtual Threads Integration](#virtual-threads-integration)

---

## Dependency Management

### Spring Boot 4 BOM

✅ **Always use Spring Boot BOM**
```xml
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>4.1.0</version>
</parent>
```

Or with dependency management:
```xml
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-dependencies</artifactId>
            <version>4.1.0</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>
```

---

## Modular Starters

Spring Boot 4 replaces monolithic starters with modular ones.

### Web Starter

❌ **Spring Boot 3**
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>
```

✅ **Spring Boot 4**
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-webmvc</artifactId>
</dependency>
```

### AOP Starter

❌ **Spring Boot 3**
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-aop</artifactId>
</dependency>
```

✅ **Spring Boot 4**
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-aspectj</artifactId>
</dependency>
```

### Test Starter

❌ **Spring Boot 3**
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-test</artifactId>
    <scope>test</scope>
</dependency>
```

✅ **Spring Boot 4 (Option A: Classic)**
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-test-classic</artifactId>
    <scope>test</scope>
</dependency>
```

✅ **Spring Boot 4 (Option B: Modular)**
```xml
<!-- Core testing -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-test</artifactId>
    <scope>test</scope>
</dependency>
<!-- Add modules as needed -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-test-mockito</artifactId>
    <scope>test</scope>
</dependency>
```

### Migration Strategy: Classic Starters

For **gradual migration**, use classic starters:

```xml
<!-- Runtime -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-classic</artifactId>
</dependency>

<!-- Test -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-test-classic</artifactId>
    <scope>test</scope>
</dependency>
```

**Benefits:**
- Fewer breaking changes
- Easier rollback
- Migrate incrementally later

---

## Jackson 3 Migration

Spring Boot 4.0.0-M3+ uses Jackson 3 as the default JSON library. Jackson 2 is available in a deprecated compatibility mode via `spring-boot-jackson2`.

Sources: [Spring Boot 4.0.0 M3 Release Notes](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0.0-M3-Release-Notes) | [Introducing Jackson 3 support in Spring](https://spring.io/blog/2025/10/07/introducing-jackson-3-support-in-spring/)

### Group ID Changes

The group ID change is confirmed but applies **only to `jackson-core` and `jackson-databind`**. `jackson-annotations` intentionally stays at the old group ID to allow Jackson 2 and Jackson 3 to coexist during ecosystem migration.

| Artifact | Jackson 2 group ID | Jackson 3 group ID |
|----------|-------------------|-------------------|
| `jackson-core` | `com.fasterxml.jackson.core` | `tools.jackson.core` |
| `jackson-databind` | `com.fasterxml.jackson.core` | `tools.jackson.core` |
| `jackson-annotations` | `com.fasterxml.jackson.core` | **`com.fasterxml.jackson.core` (unchanged)** |

❌ **Jackson 2 (Spring Boot 3)**
```xml
<dependency>
    <groupId>com.fasterxml.jackson.core</groupId>
    <artifactId>jackson-databind</artifactId>
</dependency>
```

✅ **Jackson 3 (Spring Boot 4)**
```xml
<dependency>
    <groupId>tools.jackson.core</groupId>
    <artifactId>jackson-databind</artifactId>
</dependency>
<!-- jackson-annotations stays at com.fasterxml.jackson.core — this is intentional -->
<dependency>
    <groupId>com.fasterxml.jackson.core</groupId>
    <artifactId>jackson-annotations</artifactId>
</dependency>
```

Source: [FasterXML/jackson MIGRATING_TO_JACKSON_3.md](https://github.com/FasterXML/jackson/blob/main/jackson3/MIGRATING_TO_JACKSON_3.md)

### Import Changes

❌ **Old imports**
```java
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.core.JsonProcessingException;
```

✅ **Jackson 3 imports**
```java
import tools.jackson.databind.ObjectMapper;
import tools.jackson.core.JsonProcessingException;
// jackson-annotations package is unchanged:
import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;
```

### Code Changes

❌ **Spring Boot 3**
```java
@Component
public class JacksonConfig implements Jackson2ObjectMapperBuilderCustomizer {
    @Override
    public void customize(Jackson2ObjectMapperBuilder builder) {
        builder.serializationInclusion(JsonInclude.Include.NON_NULL);
    }
}
```

✅ **Spring Boot 4**
```java
import tools.jackson.databind.json.JsonMapper;
import com.fasterxml.jackson.annotation.JsonInclude;
import org.springframework.boot.jackson.autoconfigure.JsonMapperBuilderCustomizer;
import org.springframework.stereotype.Component;

@Component
public class JacksonConfig implements JsonMapperBuilderCustomizer {
    @Override
    public void customize(JsonMapper.Builder jsonMapperBuilder) {
        jsonMapperBuilder.changeDefaultPropertyInclusion(
            incl -> incl.withValueInclusion(JsonInclude.Include.NON_NULL));
    }
}
```

> The parameter type is the `Builder` inner class on `tools.jackson.databind.json.JsonMapper`, not a top-level `JsonMapperBuilder`. Use the `changeDefaultPropertyInclusion(UnaryOperator)` builder method (Jackson 3 replacement for `serializationInclusion(...)`).

---

## Test Annotations

### Mockito Annotations

❌ **Spring Boot 3**
```java
@SpringBootTest
@MockBean
private UserService userService;

@SpyBean
private EmailService emailService;
```

✅ **Spring Boot 4**
```java
@SpringBootTest
@MockitoBean
private UserService userService;

@MockitoSpyBean
private EmailService emailService;
```

### Web Test Annotations

❌ **Spring Boot 3**
```java
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;

@WebMvcTest(UserController.class)
class UserControllerTest {
    // ...
}
```

✅ **Spring Boot 4**
```java
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;

@WebMvcTest(UserController.class)
class UserControllerTest {
    // ...
}
```

### Integration Tests

❌ **Spring Boot 3 (may work without explicit config)**
```java
@SpringBootTest
class UserServiceIntegrationTest {
    @Autowired
    private MockMvc mockMvc; // May be null!
}
```

✅ **Spring Boot 4 (explicit configuration)**
```java
@SpringBootTest
@AutoConfigureMockMvc
class UserServiceIntegrationTest {
    @Autowired
    private MockMvc mockMvc; // Properly configured
}
```

---

## Retry and Resilience

### Critical Configuration

❌ **Missing AOP support**
```xml
<!-- @Retryable won't work without AOP! -->
<!-- No spring-retry dependency needed — native in Spring Framework 7 -->
```

✅ **Include AspectJ starter**
```xml
<!-- Required for @Retryable and @ConcurrencyLimit -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-aspectj</artifactId>
</dependency>
```

### Native Resilience (Spring Framework 7)

Spring Retry is maintenance-only and superseded by native resilience in Spring Framework 7.
New Boot 4 projects should use `org.springframework.resilience.annotation.*`.

✅ **Native @Retryable + @ConcurrencyLimit (recommended)**
```java
import org.springframework.resilience.annotation.EnableResilientMethods;

@Configuration
@EnableResilientMethods
public class ResilienceConfig {}
```

```java
import org.springframework.resilience.annotation.Retryable;
import org.springframework.resilience.annotation.ConcurrencyLimit;

@Service
public class PaymentService {
    // 1 initial attempt + maxRetries — up to 3 total invocations
    @Retryable(
        includes = {PaymentException.class},
        maxRetries = 2,
        delay = 1000,
        multiplier = 2
    )
    public Payment processPayment(Order order) {
        // May throw PaymentException — retried automatically
    }

    @ConcurrencyLimit(2)
    public void processExpensiveReport(String id) {
        // Max 2 concurrent executions
    }
}
```

✅ **Resilience4j (for circuit breaker — NOT native)**
```java
@Service
public class PaymentService {
    @Retry(name = "paymentRetry")
    public Payment processPayment(Order order) {
        // Resilience4j retry
    }

    @CircuitBreaker(name = "externalApi", fallbackMethod = "fallbackUser")
    public User fetchUserFromExternalAPI(Long id) {
        // Circuit breaker pattern
    }

    private User fallbackUser(Long id, Exception e) {
        return User.cached(id);
    }
}
```

**Configuration (Resilience4j):**
```yaml
resilience4j:
  retry:
    instances:
      paymentRetry:
        maxAttempts: 3
        waitDuration: 1000
  circuitbreaker:
    instances:
      externalApi:
        failureRateThreshold: 50
        waitDurationInOpenState: 60000
```

**Review Checklist:**
- [ ] If using `@Retryable`/`@ConcurrencyLimit`, verify `spring-boot-starter-aspectj` is present
- [ ] If using native resilience, verify `@EnableResilientMethods` on a `@Configuration` class
- [ ] If using Resilience4j (circuit breaker), ensure `spring-boot-starter-aspectj` is present
- [ ] Verify retry configuration matches production requirements (backoff, max attempts)
- [ ] If legacy `spring-retry` dependency found, recommend migrating to native `org.springframework.resilience.annotation.*`

---

## Observability

Spring Boot 4 enhances observability with better metrics, tracing, and logging.

### Micrometer Integration

✅ **Enable observability**
```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,metrics,prometheus
  metrics:
    export:
      prometheus:
        enabled: true
  tracing:
    sampling:
      probability: 1.0  # 100% sampling for dev, lower in prod
```

✅ **Custom metrics**
```java
@Service
public class OrderService {
    private final MeterRegistry meterRegistry;
    private final Counter orderCounter;

    public OrderService(MeterRegistry meterRegistry) {
        this.meterRegistry = meterRegistry;
        this.orderCounter = Counter.builder("orders.created")
            .description("Total orders created")
            .register(meterRegistry);
    }

    public Order createOrder(OrderRequest request) {
        Order order = // create order
        orderCounter.increment();
        return order;
    }
}
```

### Distributed Tracing

✅ **Spring Boot 4 with Micrometer Tracing**
```xml
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-tracing-bridge-otel</artifactId>
</dependency>
<dependency>
    <groupId>io.opentelemetry</groupId>
    <artifactId>opentelemetry-exporter-otlp</artifactId>
</dependency>
```

```java
@Service
public class UserService {
    private final Tracer tracer;

    public User findUser(Long id) {
        Span span = tracer.spanBuilder("findUser").startSpan();
        try (var scope = span.makeCurrent()) {
            span.setAttribute("user.id", id);
            // Business logic
            return user;
        } finally {
            span.end();
        }
    }
}
```

---

## Problem Details (RFC 7807)

Spring Boot 4 has first-class support for RFC 7807 Problem Details.

❌ **Old custom error responses**
```java
@RestControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(UserNotFoundException.class)
    public ResponseEntity<ErrorResponse> handleUserNotFound(UserNotFoundException ex) {
        ErrorResponse error = new ErrorResponse(
            404,
            "User not found",
            ex.getMessage()
        );
        return ResponseEntity.status(404).body(error);
    }
}

// Custom ErrorResponse class
public class ErrorResponse {
    private int status;
    private String error;
    private String message;
    // getters, setters, constructors...
}
```

✅ **Spring Boot 4 with Problem Details**
```java
@RestControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(UserNotFoundException.class)
    public ProblemDetail handleUserNotFound(UserNotFoundException ex) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(
            HttpStatus.NOT_FOUND,
            ex.getMessage()
        );
        problem.setTitle("User Not Found");
        problem.setProperty("userId", ex.getUserId());
        problem.setType(URI.create("https://api.example.com/problems/user-not-found"));
        return problem;
    }
}
```

✅ **Enable in configuration**
```yaml
spring:
  mvc:
    problemdetails:
      enabled: true
```

**Response format:**
```json
{
  "type": "https://api.example.com/problems/user-not-found",
  "title": "User Not Found",
  "status": 404,
  "detail": "User with ID 123 does not exist",
  "userId": 123
}
```

---

## Configuration

### Application Properties

✅ **Use type-safe configuration**
```java
@ConfigurationProperties(prefix = "app")
public record AppConfig(
    String name,
    String version,
    Security security,
    Features features
) {
    public record Security(String secretKey, int tokenExpiry) {}
    public record Features(boolean enableCache, boolean enableMetrics) {}
}
```

```yaml
app:
  name: MyApp
  version: 1.0.0
  security:
    secret-key: ${SECRET_KEY}
    token-expiry: 3600
  features:
    enable-cache: true
    enable-metrics: true
```

❌ **Avoid `@Value` for complex configuration**
```java
@Value("${app.security.secret-key}")
private String secretKey;

@Value("${app.security.token-expiry}")
private int tokenExpiry;
```

---

## Virtual Threads Integration

Spring Boot 4 has first-class virtual thread support.

### ⚠️ CRITICAL: Evaluate Before Adopting Virtual Threads

**See [java-25-features.md](java-25-features.md) for full virtual threads guidance, official citations, and why the 10,000 concurrent tasks threshold exists.**

**Before recommending virtual threads, MUST verify:**

1. **Concurrency level** - Check actual concurrent requests (NOT daily totals)
   - ✅ Use if: 10,000+ concurrent tasks (per Oracle's official threshold)
   - ❌ Don't use if: <1,000 concurrent requests

2. **Workload type** - Identify I/O vs CPU characteristics
   - ✅ Use if: I/O-bound (database queries, REST calls, file operations)
   - ❌ Don't use if: CPU-bound (computation, data processing)

3. **Thread pool metrics** - Examine current pool utilization
   - ✅ Use if: Thread pool exhaustion, high queue depths
   - ❌ Don't use if: Low pool utilization, small queue sizes

4. **Pool size intent** - Understand why current pool is sized
   - ✅ Use if: Pool size limited by memory constraints
   - ❌ Don't use if: Small pool is intentional (rate limiting, backpressure)

### When Virtual Threads Are NOT Appropriate

❌ **Low-traffic applications**
```java
// Example: 100 requests/day (~4/hour)
// Virtual threads provide NO benefit here
@Bean(name = "auditExecutor")
public Executor auditExecutor() {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.setCorePoolSize(2);  // Already over-provisioned for this load
    executor.setMaxPoolSize(5);
    return executor;
}
```

❌ **Intentional rate limiting**
```java
// Small pool size is deliberate to throttle
@Bean(name = "externalApiExecutor")
public Executor externalApiExecutor() {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.setMaxPoolSize(5);  // Protects external API from overload
    // Virtual threads would bypass this protection!
    return executor;
}
```

❌ **CPU-bound tasks**
```java
// Virtual threads don't help CPU-intensive work
@Async
public void processLargeDataset(byte[] data) {
    // Heavy computation, no I/O wait
    performComplexCalculations(data);
}
```

### When Virtual Threads ARE Appropriate

✅ **High-concurrency I/O-bound applications**
```yaml
# Enable for web servers with thousands of concurrent requests
spring:
  threads:
    virtual:
      enabled: true
```

✅ **Requirements met:**
- 10,000+ concurrent requests
- I/O-bound workload (database, HTTP, messaging)
- Thread pool exhaustion observed in metrics
- Java 21+ on Spring Boot 4 (virtual threads have been GA since Java 21; Boot 4 enables them via `spring.threads.virtual.enabled=true`)

### Async Methods with Virtual Threads

✅ **@Async automatically uses virtual threads when enabled**
```java
@Service
public class EmailService {
    @Async  // Uses virtual threads if spring.threads.virtual.enabled=true
    public CompletableFuture<Void> sendEmail(String to, String subject, String body) {
        // Send email (blocking I/O) - benefits from virtual threads
        return CompletableFuture.completedFuture(null);
    }
}
```

### RestClient with Virtual Threads

**Requires:** `spring-boot-starter-restclient` (Boot 4 modular starter — not included in `spring-boot-starter-webmvc`)

✅ **RestClient (modern, virtual-thread-friendly)**
```java
@Configuration
public class RestClientConfig {
    @Bean
    public RestClient restClient(RestClient.Builder builder) {
        return builder
            .baseUrl("https://api.example.com")
            .build();
    }
}

@Service
public class UserService {
    private final RestClient restClient;

    public User fetchUser(Long id) {
        return restClient.get()
            .uri("/users/{id}", id)
            .retrieve()
            .body(User.class);
    }
}
```

❌ **Avoid WebClient for blocking operations**
```java
// BAD: WebClient is reactive, doesn't benefit from virtual threads
webClient.get()
    .uri("/users/{id}", id)
    .retrieve()
    .bodyToMono(User.class)
    .block();  // Blocking defeats reactive purpose
```

---

## Anti-Patterns to Flag

### 1. Old Starter Names

❌ `spring-boot-starter-web` → Should be `spring-boot-starter-webmvc`
❌ `spring-boot-starter-aop` → Should be `spring-boot-starter-aspectj`
❌ Using `RestClient` without `spring-boot-starter-restclient` dependency
❌ Using `WebClient` without `spring-boot-starter-webclient` dependency

Boot 4 modular starters split HTTP client support from the web starter. `spring-boot-starter-webmvc` no longer includes RestClient auto-configuration — add `spring-boot-starter-restclient` explicitly.

Source: [Spring Boot 4.0 Migration Guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide)

### 2. Old Jackson Group IDs

❌ `com.fasterxml.jackson.core:jackson-core` / `jackson-databind` → moved to `tools.jackson.core:jackson-core` / `jackson-databind` in Jackson 3.
✅ `jackson-annotations` intentionally stays on the legacy `com.fasterxml.jackson.core` group ID so projects can mix Jackson 2 and Jackson 3 during ecosystem migration. Source: [Introducing Jackson 3 support in Spring (2025-10-07)](https://spring.io/blog/2025/10/07/introducing-jackson-3-support-in-spring/).

### 3. Old Test Annotations

❌ `@MockBean` → Should be `@MockitoBean`
❌ `@SpyBean` → Should be `@MockitoSpyBean`
❌ `import org.springframework.boot.test.autoconfigure.web.servlet.*` → Should be `org.springframework.boot.webmvc.test.autoconfigure.*`

### 4. Missing AOP for Retry/Resilience

❌ Using `@Retryable` or Resilience4j annotations without AOP support
✅ Ensure `spring-boot-starter-aspectj` is present for annotation-based resilience

### 5. Recommending Virtual Threads Without Analysis

❌ Suggesting virtual threads without verifying workload characteristics
✅ Analyze concurrency level (must be 10,000+ concurrent tasks), workload type (must be I/O-bound), and thread pool metrics before recommending

**See [java-25-features.md](java-25-features.md) for detailed explanation of why 10,000 tasks is the threshold and full official citations.**

**Example of incorrect recommendation:**
- Application: 100 requests/day (~4/hour), 2-5 thread pool
- ❌ "Use virtual threads" - No benefit, unnecessary complexity
- ✅ Keep existing pool - Already over-provisioned for this load

### 6. Custom Error Responses

❌ Custom `ErrorResponse` classes instead of Problem Details
✅ Use `ProblemDetail` with `spring.mvc.problemdetails.enabled=true`

### 7. Non-Type-Safe Configuration

❌ Scattered `@Value` annotations
✅ Use `@ConfigurationProperties` with records

### 8. TestRestTemplate in Boot 4

❌ `TestRestTemplate` autowired by default → no longer auto-provided by `@SpringBootTest` in Boot 4 (the class itself is still supported, not deprecated)
✅ Use `RestTestClient` (`org.springframework.test.web.servlet.client.RestTestClient`)

```java
// Before (Boot 3)
@Autowired
private TestRestTemplate restTemplate;

// After (Boot 4)
@Autowired
private RestTestClient restTestClient;
```

Source: [RestTestClient :: Spring Framework](https://docs.spring.io/spring-framework/reference/testing/resttestclient.html)

### 9. Manual HttpServiceProxyFactory Boilerplate

❌ Manual `HttpServiceProxyFactory` bean setup for `@HttpExchange` clients
✅ Use `@ImportHttpServices` auto-configuration (Spring Framework 7.0)

```java
// Before (Boot 3 / Framework 6)
@Bean
ProductClient productClient(RestClient.Builder builder) {
    RestClient restClient = builder.baseUrl("http://api.example.com").build();
    return HttpServiceProxyFactory
            .builderFor(RestClientAdapter.create(restClient))
            .build()
            .createClient(ProductClient.class);
}

// After (Boot 4 / Framework 7)
@Configuration
@ImportHttpServices(group = "product", types = ProductClient.class)
public class ClientConfig { }
```

Note: `@HttpExchange` itself exists since Framework 6.0. Only `@ImportHttpServices` (`org.springframework.web.service.registry`) is new in Framework 7.0.

Source: [HTTP Service Client Enhancements](https://spring.io/blog/2025/09/23/http-service-client-enhancements/)

### 10. Custom API Versioning Instead of Native

❌ Custom versioning interceptors, filters, or external libraries
✅ Use native `spring.mvc.apiversion.*` properties and `version` attribute on `@GetMapping` / `@PostMapping`

```java
// Native API versioning (Framework 7.0)
@GetMapping(value = "/search", version = "2.0")
public List<ProductVM> searchV2(@RequestParam("q") String query) { ... }
```

```yaml
spring:
  mvc:
    apiversion:
      default: "1.0"
      supported: "1.0,2.0"
      use:
        header: X-API-Version
        # query-parameter: version
        # path-segment: 1
        # media-type-parameter[application/json]: version
```

The Java-config equivalent uses `WebMvcConfigurer.configureApiVersioning(ApiVersionConfigurer)` with `useRequestHeader`/`useQueryParam`/`useMediaTypeParameter`/`usePathSegment`. The `ApiVersionConfigurer` class is in `org.springframework.web.servlet.config.annotation`; the default parser is `SemanticApiVersionParser` in `org.springframework.web.accept`.

Source: [API Versioning in Spring](https://spring.io/blog/2025/09/16/api-versioning-in-spring/)

### 11. @ConcurrencyLimit Without @EnableResilientMethods

❌ Using `@ConcurrencyLimit` without `@EnableResilientMethods` on a `@Configuration` class
✅ Add `@EnableResilientMethods` — required for both `@ConcurrencyLimit` and native `@Retryable`

```java
@Configuration
@EnableResilientMethods  // Required
public class ResilienceConfig { }
```

Source: [Core Spring Resilience Features](https://spring.io/blog/2025/09/09/core-spring-resilience-features/)

---

## Review Checklist

When reviewing Spring Boot 4 code:

- [ ] All starters use Spring Boot 4 names (webmvc, aspectj, restclient, webclient)
- [ ] Jackson imports use `tools.jackson.*` (except `jackson-annotations`)
- [ ] Test annotations use `@MockitoBean` / `@MockitoSpyBean`
- [ ] `@Retryable` has `spring-boot-starter-aspectj` dependency
- [ ] Virtual threads evaluated for high-concurrency I/O-bound workloads (10,000+ concurrent tasks)
- [ ] Thread pool sizing is appropriate for workload (not blindly replaced with virtual threads)
- [ ] Problem Details used for error responses
- [ ] Type-safe configuration with `@ConfigurationProperties`
- [ ] Observability configured (metrics, tracing)
- [ ] `TestRestTemplate` replaced with `RestTestClient`
- [ ] HTTP service clients use `@ImportHttpServices` instead of manual `HttpServiceProxyFactory`
- [ ] API versioning uses native `spring.mvc.apiversion.*` and `version=` attribute
- [ ] `@ConcurrencyLimit` and native `@Retryable` have `@EnableResilientMethods` configured

---

## Official Documentation

- [Spring Boot 4.0 Release Notes](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Release-Notes)
- [Spring Boot 4.0 Migration Guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide)
- [Spring Boot Reference Documentation](https://docs.spring.io/spring-boot/reference/)
- [Upgrading Spring Boot](https://docs.spring.io/spring-boot/upgrading.html)
- [Modularizing Spring Boot (Blog)](https://spring.io/blog/2025/10/28/modularizing-spring-boot/)
- [Spring Boot 4.0.0 Announcement](https://spring.io/blog/2025/11/20/spring-boot-4-0-0-available-now/)
- [Spring Modulith Reference](https://docs.spring.io/spring-modulith/reference/)
- [Spring Retry (maintenance-only)](https://github.com/spring-projects/spring-retry) — superseded by Spring Framework 7 native resilience
- [Resilience4j Spring Boot](https://resilience4j.readme.io/docs/getting-started-3)
- [RestTestClient :: Spring Framework](https://docs.spring.io/spring-framework/reference/testing/resttestclient.html)
- [HTTP Service Client Enhancements (Blog)](https://spring.io/blog/2025/09/23/http-service-client-enhancements/)
- [API Versioning in Spring (Blog)](https://spring.io/blog/2025/09/16/api-versioning-in-spring/)
- [Core Spring Resilience Features (Blog)](https://spring.io/blog/2025/09/09/core-spring-resilience-features/)
