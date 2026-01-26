# Spring Boot 4 Patterns and Best Practices

## Table of Contents

1. [Dependency Management](#dependency-management)
2. [Modular Starters](#modular-starters)
3. [Jackson 3 Migration](#jackson-3-migration)
4. [Test Annotations](#test-annotations)
5. [Retry and Resilience](#retry-and-resilience)
6. [Observability](#observability)
7. [Problem Details (RFC 7807)](#problem-details)
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
    <version>4.0.0</version>
</parent>
```

Or with dependency management:
```xml
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-dependencies</artifactId>
            <version>4.0.0</version>
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

### Group ID Changes

> **⚠️ IMPORTANT:** As of Spring Boot 4.0.0, Jackson 3 integration details are still evolving. Verify actual group IDs in your `pom.xml` or `build.gradle` when migrating. The information below is based on early Jackson 3 specifications and may need adjustment.

**Expected Jackson 3 Group ID Changes:**

❌ **Jackson 2 (Spring Boot 3)**
```xml
<dependency>
    <groupId>com.fasterxml.jackson.core</groupId>
    <artifactId>jackson-databind</artifactId>
</dependency>
```

✅ **Jackson 3 (Expected in Spring Boot 4)**
```xml
<!-- Expected group ID change - verify in your project -->
<dependency>
    <groupId>tools.jackson.core</groupId>
    <artifactId>jackson-databind</artifactId>
</dependency>
```

⚠️ **Exception: jackson-annotations may keep old group ID**
```xml
<!-- May still use old group ID - verify in your project -->
<dependency>
    <groupId>com.fasterxml.jackson.core</groupId>
    <artifactId>jackson-annotations</artifactId>
</dependency>
```

**Verification Steps:**
1. Check your `pom.xml` or `build.gradle` after upgrading to Spring Boot 4
2. Look for Jackson dependencies managed by Spring Boot BOM
3. Verify group IDs match what Spring Boot 4 expects

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

✅ **Spring Boot 4 (Expected)**
```java
@Component
public class JacksonConfig implements JsonMapperBuilderCustomizer {
    @Override
    public void customize(JsonMapperBuilder builder) {
        builder.serializationInclusion(JsonInclude.Include.NON_NULL);
    }
}
```

**Note:** Class names and interfaces may vary based on final Jackson 3 integration. Consult Spring Boot 4 migration guide for actual class names.

### Import Changes (Expected)

❌ **Old imports**
```java
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.core.JsonProcessingException;
```

✅ **Expected new imports**
```java
// Expected Jackson 3 package structure - verify in your project
import tools.jackson.databind.ObjectMapper;
import tools.jackson.core.JsonProcessingException;
```

**If imports fail:**
- Check if Spring Boot 4 is using a different Jackson 3 packaging
- Review Spring Boot 4.x migration documentation
- Verify Jackson version in dependency tree: `mvn dependency:tree | grep jackson`

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
import org.springframework.boot.test.autoconfigure.webmvc.WebMvcTest;

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
<dependency>
    <groupId>org.springframework.retry</groupId>
    <artifactId>spring-retry</artifactId>
</dependency>
```

✅ **Include AspectJ starter**
```xml
<!-- Required for @Retryable to work -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-aspectj</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.retry</groupId>
    <artifactId>spring-retry</artifactId>
</dependency>
```

### Spring Retry Integration

✅ **Option A: Spring Retry (classic pattern)**
```java
@Service
@EnableRetry
public class PaymentService {
    @Retryable(
        retryFor = PaymentException.class,
        maxAttempts = 3,
        backoff = @Backoff(delay = 1000)
    )
    public Payment processPayment(Order order) {
        // May throw PaymentException
    }

    @Recover
    public Payment recoverPayment(PaymentException e, Order order) {
        // Fallback logic after all retries fail
        return handlePaymentFailure(order);
    }
}
```

✅ **Option B: Resilience4j (declarative resilience)**
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
- [ ] If using `@Retryable`, verify `spring-boot-starter-aspectj` is present
- [ ] If using Spring Retry directly, ensure explicit `spring-retry` dependency + version
- [ ] If using Resilience4j, ensure `spring-boot-starter-aop` or `spring-boot-starter-aspectj` is present
- [ ] Verify retry configuration matches production requirements (backoff, max attempts)

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

### Enable Virtual Threads

```yaml
spring:
  threads:
    virtual:
      enabled: true
```

### Async Methods

✅ **@Async automatically uses virtual threads**
```java
@Service
public class EmailService {
    @Async  // Uses virtual threads when enabled
    public CompletableFuture<Void> sendEmail(String to, String subject, String body) {
        // Send email (blocking I/O)
        return CompletableFuture.completedFuture(null);
    }
}
```

### RestClient with Virtual Threads

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

### 2. Old Jackson Group IDs

❌ `com.fasterxml.jackson.*` → Expected to change to `tools.jackson.*` (verify in your project)
⚠️ Note: Jackson 3 packaging details may vary - check Spring Boot 4 BOM for actual group IDs

### 3. Old Test Annotations

❌ `@MockBean` → Should be `@MockitoBean`
❌ `@SpyBean` → Should be `@MockitoSpyBean`
❌ `import org.springframework.boot.test.autoconfigure.web.servlet.*` → Should be `.webmvc.*`

### 4. Missing AOP for Retry/Resilience

❌ Using `@Retryable` or Resilience4j annotations without AOP support
✅ Ensure `spring-boot-starter-aspectj` is present for annotation-based resilience

### 5. Ignoring Virtual Threads

❌ Using manual thread pools for I/O-bound tasks
✅ Enable virtual threads and use `@Async`

### 6. Custom Error Responses

❌ Custom `ErrorResponse` classes instead of Problem Details
✅ Use `ProblemDetail` with `spring.mvc.problemdetails.enabled=true`

### 7. Non-Type-Safe Configuration

❌ Scattered `@Value` annotations
✅ Use `@ConfigurationProperties` with records

---

## Review Checklist

When reviewing Spring Boot 4 code:

- [ ] All starters use Spring Boot 4 names (webmvc, aspectj, test-classic)
- [ ] Jackson imports use `tools.jackson.*` (except `jackson-annotations`)
- [ ] Test annotations use `@MockitoBean` / `@MockitoSpyBean`
- [ ] `@Retryable` has `spring-boot-starter-aspectj` dependency
- [ ] Virtual threads enabled for I/O-bound workloads
- [ ] Problem Details used for error responses
- [ ] Type-safe configuration with `@ConfigurationProperties`
- [ ] Observability configured (metrics, tracing)
- [ ] No manual thread pools for blocking I/O (use virtual threads instead)

---

## Official Documentation

- [Spring Boot 4.0 Release Notes](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Release-Notes)
- [Spring Boot 4.0 Migration Guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide)
- [Spring Boot Reference Documentation](https://docs.spring.io/spring-boot/reference/)
- [Upgrading Spring Boot](https://docs.spring.io/spring-boot/upgrading.html)
- [Modularizing Spring Boot (Blog)](https://spring.io/blog/2025/10/28/modularizing-spring-boot/)
- [Spring Boot 4.0.0 Announcement](https://spring.io/blog/2025/11/20/spring-boot-4-0-0-available-now/)
- [Spring Modulith Reference](https://docs.spring.io/spring-modulith/reference/)
- [Spring Retry Documentation](https://docs.spring.io/spring-retry/docs/current/reference/html/)
- [Resilience4j Spring Boot](https://resilience4j.readme.io/docs/getting-started-3)
