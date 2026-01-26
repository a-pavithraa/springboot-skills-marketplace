# Performance Patterns and Anti-Patterns

## Table of Contents

1. [N+1 Query Problem](#n1-query-problem)
2. [Caching Strategies](#caching-strategies)
3. [Virtual Threads](#virtual-threads)
4. [Database Performance](#database-performance)
5. [Async Processing](#async-processing)
6. [Connection Pooling](#connection-pooling)
7. [Resource Management](#resource-management)

---

## N+1 Query Problem

The most common JPA performance issue.

### Problem Detection

❌ **Classic N+1 pattern**
```java
@Entity
public class Order {
    @Id
    private Long id;

    @ManyToOne  // Lazy by default
    private User user;

    @OneToMany(mappedBy = "order")  // Lazy by default
    private List<OrderItem> items;
}

// Service layer
List<Order> orders = orderRepository.findAll();
for (Order order : orders) {
    System.out.println(order.getUser().getName());  // N+1 here!
    System.out.println(order.getItems().size());    // Another N+1!
}
```

**What happens:**
- 1 query to fetch all orders
- N queries to fetch each user (one per order)
- N queries to fetch each order's items
- Total: **1 + N + N = 1 + 2N queries**

### Solutions

✅ **Solution 1: Fetch Joins**
```java
public interface OrderRepository extends JpaRepository<Order, Long> {
    @Query("SELECT o FROM Order o " +
           "LEFT JOIN FETCH o.user " +
           "LEFT JOIN FETCH o.items")
    List<Order> findAllWithUserAndItems();
}
```

✅ **Solution 2: Entity Graphs**
```java
public interface OrderRepository extends JpaRepository<Order, Long> {
    @EntityGraph(attributePaths = {"user", "items"})
    List<Order> findAll();
}
```

✅ **Solution 3: @NamedEntityGraph**
```java
@Entity
@NamedEntityGraph(
    name = "Order.full",
    attributeNodes = {
        @NamedAttributeNode("user"),
        @NamedAttributeNode("items")
    }
)
public class Order {
    // ...
}

public interface OrderRepository extends JpaRepository<Order, Long> {
    @EntityGraph("Order.full")
    List<Order> findAll();
}
```

### Detection Tools

✅ **Enable Hibernate statistics**
```yaml
spring:
  jpa:
    properties:
      hibernate:
        generate_statistics: true
        session:
          events:
            log:
              LOG_QUERIES_SLOWER_THAN_MS: 10
```

✅ **Use p6spy for query logging**
```xml
<dependency>
    <groupId>com.github.gavlyukovskiy</groupId>
    <artifactId>p6spy-spring-boot-starter</artifactId>
</dependency>
```

**Review Checklist:**
- [ ] No lazy loading in loops
- [ ] Associations fetched eagerly when needed (fetch join or entity graph)
- [ ] Query logging enabled during development

---

## Caching Strategies

### Spring Cache Abstraction

✅ **Enable caching**
```java
@Configuration
@EnableCaching
public class CacheConfig {
    @Bean
    public CacheManager cacheManager() {
        return new CaffeineCacheManager("users", "products");
    }

    @Bean
    public Caffeine<Object, Object> caffeineConfig() {
        return Caffeine.newBuilder()
            .maximumSize(1000)
            .expireAfterWrite(10, TimeUnit.MINUTES);
    }
}
```

✅ **Cache usage**
```java
@Service
public class UserService {
    @Cacheable(value = "users", key = "#id")
    public User findById(Long id) {
        return userRepository.findById(id)
            .orElseThrow(() -> new UserNotFoundException(id));
    }

    @CachePut(value = "users", key = "#user.id")
    public User update(User user) {
        return userRepository.save(user);
    }

    @CacheEvict(value = "users", key = "#id")
    public void delete(Long id) {
        userRepository.deleteById(id);
    }

    @CacheEvict(value = "users", allEntries = true)
    public void clearCache() {
        // Clears all users from cache
    }
}
```

### Caching Anti-Patterns

❌ **Caching without expiration**
```java
@Cacheable("users")  // Never expires!
public User findById(Long id) {
    return userRepository.findById(id).orElseThrow();
}
```

✅ **Proper expiration**
```java
@Bean
public Caffeine<Object, Object> caffeineConfig() {
    return Caffeine.newBuilder()
        .expireAfterWrite(10, TimeUnit.MINUTES)  // Absolute expiration
        .expireAfterAccess(5, TimeUnit.MINUTES); // Sliding expiration
}
```

❌ **Caching large objects**
```java
@Cacheable("reports")
public byte[] generateLargeReport() {  // Don't cache multi-MB objects!
    return reportGenerator.generate();
}
```

✅ **Cache metadata instead**
```java
@Cacheable("reportMetadata")
public ReportMetadata getReportMetadata(String reportId) {
    return new ReportMetadata(reportId, location, size);
}
```

### Distributed Caching (Redis)

✅ **Redis configuration**
```yaml
spring:
  cache:
    type: redis
  data:
    redis:
      host: localhost
      port: 6379
```

```java
@Configuration
@EnableCaching
public class RedisCacheConfig {
    @Bean
    public RedisCacheManager cacheManager(RedisConnectionFactory connectionFactory) {
        RedisCacheConfiguration config = RedisCacheConfiguration.defaultCacheConfig()
            .entryTtl(Duration.ofMinutes(10))
            .serializeKeysWith(RedisSerializationContext.SerializationPair.fromSerializer(
                new StringRedisSerializer()))
            .serializeValuesWith(RedisSerializationContext.SerializationPair.fromSerializer(
                new GenericJackson2JsonRedisSerializer()));

        return RedisCacheManager.builder(connectionFactory)
            .cacheDefaults(config)
            .build();
    }
}
```

**Review Checklist:**
- [ ] Caching enabled for expensive operations
- [ ] Cache expiration configured
- [ ] Cache keys properly defined
- [ ] Cache invalidation on updates/deletes
- [ ] Cache size limits set

---

## Virtual Threads

Spring Boot 4 has first-class virtual thread support.

### Enable Virtual Threads

```yaml
spring:
  threads:
    virtual:
      enabled: true
```

### When to Use

✅ **I/O-bound operations**
```java
@Service
public class UserService {
    private final RestClient restClient;

    @Async  // Uses virtual threads when enabled
    public CompletableFuture<User> fetchUserFromExternalAPI(Long id) {
        User user = restClient.get()
            .uri("/users/{id}", id)
            .retrieve()
            .body(User.class);  // Blocking I/O - perfect for virtual threads
        return CompletableFuture.completedFuture(user);
    }
}
```

### When NOT to Use

❌ **CPU-bound operations**
```java
@Service
public class ComputeService {
    @Async  // Virtual threads don't help here!
    public CompletableFuture<BigInteger> computeLargePrime(int bits) {
        // CPU-intensive - use platform threads
        return CompletableFuture.completedFuture(BigInteger.probablePrime(bits, new Random()));
    }
}
```

### Pinning Issues

❌ **Synchronized blocks pin virtual threads**
```java
private final Object lock = new Object();

public void processRequest() {
    synchronized (lock) {  // Pins virtual thread!
        String response = httpClient.send(request);  // Blocking I/O
    }
}
```

✅ **Use ReentrantLock instead**
```java
private final ReentrantLock lock = new ReentrantLock();

public void processRequest() {
    lock.lock();
    try {
        String response = httpClient.send(request);
    } finally {
        lock.unlock();
    }
}
```

**Review Checklist:**
- [ ] Virtual threads enabled for I/O-bound services
- [ ] No `synchronized` blocks in I/O code paths (use `ReentrantLock`)
- [ ] Thread pool sizes removed (virtual threads scale automatically)
- [ ] CPU-bound tasks use platform threads

---

## Database Performance

### Batch Operations

❌ **One-by-one inserts**
```java
for (User user : users) {
    userRepository.save(user);  // N queries!
}
```

✅ **Batch insert**
```java
userRepository.saveAll(users);  // Batched!
```

✅ **Configure batch size**
```yaml
spring:
  jpa:
    properties:
      hibernate:
        jdbc:
          batch_size: 50
        order_inserts: true
        order_updates: true
```

### Pagination

❌ **Loading all records**
```java
List<User> users = userRepository.findAll();  // Loads entire table!
```

✅ **Pagination**
```java
Pageable pageable = PageRequest.of(0, 20, Sort.by("name"));
Page<User> users = userRepository.findAll(pageable);
```

### Projections

❌ **Loading entire entity when only few fields needed**
```java
List<User> users = userRepository.findAll();
return users.stream()
    .map(u -> new UserDTO(u.getId(), u.getName()))
    .toList();
```

✅ **Interface projections**
```java
public interface UserSummary {
    Long getId();
    String getName();
}

public interface UserRepository extends JpaRepository<User, Long> {
    List<UserSummary> findAllProjectedBy();
}
```

✅ **DTO projections**
```java
public record UserDTO(Long id, String name) {}

@Query("SELECT new com.example.UserDTO(u.id, u.name) FROM User u")
List<UserDTO> findAllDTOs();
```

### Read-Only Queries

✅ **Mark read-only transactions**
```java
@Transactional(readOnly = true)
public List<User> findActiveUsers() {
    return userRepository.findByActiveTrue();
}
```

**Benefits:**
- Optimizations at JDBC driver level
- No dirty checking overhead
- Can route to read replicas

**Review Checklist:**
- [ ] Batch operations for bulk inserts/updates
- [ ] Pagination used for large result sets
- [ ] Projections used when only few fields needed
- [ ] Read-only transactions marked as such

---

## Async Processing

### Spring @Async

✅ **Configure async executor**
```java
@Configuration
@EnableAsync
public class AsyncConfig implements AsyncConfigurer {
    @Override
    public Executor getAsyncExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(5);
        executor.setMaxPoolSize(10);
        executor.setQueueCapacity(100);
        executor.setThreadNamePrefix("async-");
        executor.initialize();
        return executor;
    }
}
```

✅ **Async methods**
```java
@Service
public class NotificationService {
    @Async
    public CompletableFuture<Void> sendEmail(String to, String subject, String body) {
        // Send email asynchronously
        emailClient.send(to, subject, body);
        return CompletableFuture.completedFuture(null);
    }
}

@Service
public class OrderService {
    private final NotificationService notificationService;

    public Order createOrder(OrderRequest request) {
        Order order = orderRepository.save(new Order(request));

        // Send email asynchronously - doesn't block
        notificationService.sendEmail(
            request.getEmail(),
            "Order Confirmation",
            "Your order has been placed"
        );

        return order;
    }
}
```

### CompletableFuture Composition

✅ **Parallel execution (Traditional approach)**
```java
@Service
public class DashboardService {
    private final UserService userService;
    private final OrderService orderService;
    private final ProductService productService;

    public Dashboard getDashboard(Long userId) {
        CompletableFuture<User> userFuture = userService.findByIdAsync(userId);
        CompletableFuture<List<Order>> ordersFuture = orderService.findByUserIdAsync(userId);
        CompletableFuture<List<Product>> productsFuture = productService.findRecommendedAsync(userId);

        return CompletableFuture.allOf(userFuture, ordersFuture, productsFuture)
            .thenApply(v -> new Dashboard(
                userFuture.join(),
                ordersFuture.join(),
                productsFuture.join()
            ))
            .join();
    }
}
```

### Structured Concurrency (Java 25 Alternative)

**New in Java 21+**: Structured Concurrency provides a cleaner alternative to CompletableFuture for parallel execution.

✅ **Structured Concurrency approach**
```java
@Service
public class DashboardService {
    private final UserService userService;
    private final OrderService orderService;
    private final ProductService productService;

    public Dashboard getDashboard(Long userId) throws ExecutionException, InterruptedException {
        try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
            Subtask<User> userTask = scope.fork(() -> userService.findById(userId));
            Subtask<List<Order>> ordersTask = scope.fork(() -> orderService.findByUserId(userId));
            Subtask<List<Product>> productsTask = scope.fork(() -> productService.findRecommended(userId));

            scope.join()           // Wait for all subtasks
                .throwIfFailed();  // Propagate exceptions

            return new Dashboard(
                userTask.get(),
                ordersTask.get(),
                productsTask.get()
            );
        }
    }
}
```

### When to Use What in Java 25

| Use Case | Recommended Approach | Reason |
|----------|---------------------|--------|
| **Spring @Async integration** | CompletableFuture | Spring @Async returns CompletableFuture, maintains framework compatibility |
| **Complex composition chains** | CompletableFuture | `.thenCompose()`, `.thenApply()`, `.exceptionally()` provide fluent API |
| **Parallel execution of independent tasks** | Structured Concurrency | Cleaner error handling, automatic cancellation, structured lifecycle |
| **Simple blocking I/O with virtual threads** | Direct blocking calls | Virtual threads make blocking acceptable - no async wrapper needed |
| **Timeout/cancellation requirements** | Structured Concurrency | Built-in timeout support with `ShutdownOnFailure` |

### Migration Example

❌ **Old CompletableFuture pattern**
```java
public Dashboard getDashboard(Long userId) {
    CompletableFuture<User> user = CompletableFuture.supplyAsync(() -> fetchUser(userId));
    CompletableFuture<List<Order>> orders = CompletableFuture.supplyAsync(() -> fetchOrders(userId));

    return user.thenCombine(orders, (u, o) -> new Dashboard(u, o)).join();
}
```

✅ **Modern Structured Concurrency**
```java
public Dashboard getDashboard(Long userId) throws ExecutionException, InterruptedException {
    try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
        var userTask = scope.fork(() -> fetchUser(userId));
        var ordersTask = scope.fork(() -> fetchOrders(userId));

        scope.join().throwIfFailed();
        return new Dashboard(userTask.get(), ordersTask.get());
    }
}
```

**Benefits of Structured Concurrency:**
- **Automatic cancellation**: If one task fails, others are cancelled immediately
- **Clear ownership**: Task lifetime bound to scope (like try-with-resources)
- **Better error handling**: Single exception propagation point
- **Works naturally with virtual threads**: No need for explicit executor configuration

### CompletableFuture Still Valuable For

1. **Spring framework integration** (@Async returns CompletableFuture)
2. **Complex async pipelines** with multiple transformation steps
3. **Backward compatibility** with existing APIs
4. **Fine-grained control** over completion and exception handling

**Review Checklist:**
- [ ] Long-running operations are async
- [ ] Async executor properly configured (or using virtual threads)
- [ ] Independent operations run in parallel
- [ ] Error handling in async methods
- [ ] For Java 21+: Consider Structured Concurrency over CompletableFuture for parallel execution
- [ ] CompletableFuture used appropriately (Spring @Async, complex composition chains)

---

## Connection Pooling

### HikariCP Configuration (Default in Spring Boot 4)

✅ **Tuned connection pool**
```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 10  # Not too high!
      minimum-idle: 5
      connection-timeout: 30000
      idle-timeout: 600000
      max-lifetime: 1800000
      leak-detection-threshold: 60000  # Detect connection leaks
```

**Sizing formula:**
```
connections = ((core_count * 2) + effective_spindle_count)
```

For cloud/SSDs: `core_count * 2 + 1`

❌ **Too many connections**
```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 100  # Way too high for most apps!
```

**Problems:**
- Context switching overhead
- Database connection limits exceeded
- Memory waste

**Review Checklist:**
- [ ] Connection pool size tuned (not default)
- [ ] Leak detection enabled
- [ ] Connection timeout configured
- [ ] Idle timeout configured

---

## Resource Management

### Always Close Resources

❌ **Resource leak**
```java
public String readFile(String path) {
    InputStream is = new FileInputStream(path);
    return new String(is.readAllBytes());  // Stream never closed!
}
```

✅ **Try-with-resources**
```java
public String readFile(String path) throws IOException {
    try (InputStream is = new FileInputStream(path)) {
        return new String(is.readAllBytes());
    }  // Automatically closed
}
```

### HTTP Client Resource Management

❌ **Creating clients per request**
```java
public String fetchData(String url) {
    RestClient client = RestClient.create();  // New client per request!
    return client.get().uri(url).retrieve().body(String.class);
}
```

✅ **Reuse clients**
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
public class ExternalApiService {
    private final RestClient restClient;  // Injected, shared

    public String fetchData(String path) {
        return restClient.get().uri(path).retrieve().body(String.class);
    }
}
```

**Review Checklist:**
- [ ] All resources closed (try-with-resources)
- [ ] HTTP clients reused (not created per request)
- [ ] No connection leaks

---

## Performance Review Checklist

### Critical Issues

- [ ] **N+1 queries**: All associations use fetch joins or entity graphs
- [ ] **Missing indexes**: All foreign keys and frequently queried columns indexed
- [ ] **No pagination**: Large result sets use `Pageable`
- [ ] **Expensive operations in loops**: Batch operations used
- [ ] **Connection leaks**: Resources properly closed

### Optimizations

- [ ] **Caching**: Expensive reads cached with proper expiration
- [ ] **Read-only transactions**: Read operations marked `readOnly = true`
- [ ] **Projections**: DTOs used instead of full entities when possible
- [ ] **Async processing**: Independent operations run in parallel
- [ ] **Virtual threads**: I/O-bound operations use virtual threads
- [ ] **Batch operations**: Bulk inserts/updates batched
- [ ] **Connection pool tuning**: HikariCP properly configured

### Tools

- [ ] Query logging enabled during development
- [ ] Hibernate statistics enabled for N+1 detection
- [ ] Connection leak detection configured
- [ ] Performance testing done under load

---

## Official Documentation

- [Spring Data JPA Reference - Performance](https://docs.spring.io/spring-data/jpa/reference/jpa/query-methods.html)
- [Hibernate Performance Tuning](https://docs.jboss.org/hibernate/orm/current/userguide/html_single/Hibernate_User_Guide.html#performance)
- [HikariCP Configuration](https://github.com/brettwooldridge/HikariCP#configuration-knobs-baby)
- [Virtual Threads - Oracle Java](https://docs.oracle.com/en/java/javase/25/core/virtual-threads.html)
- [Spring Cache Abstraction](https://docs.spring.io/spring-framework/reference/integration/cache.html)
- [Caffeine Cache](https://github.com/ben-manes/caffeine/wiki)
- [Redis Spring Data](https://spring.io/projects/spring-data-redis)
- [Spring Async Documentation](https://docs.spring.io/spring-framework/reference/integration/scheduling.html)
- [N+1 Query Problem - Vladmihalcea](https://vladmihalcea.com/n-plus-1-query-problem/)
- [JPA EntityGraph](https://docs.oracle.com/javaee/7/tutorial/persistence-entitygraphs002.htm)
