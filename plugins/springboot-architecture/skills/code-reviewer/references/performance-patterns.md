# Performance Patterns and Anti-Patterns

## Table of Contents

1. [Database access](#database-access)
2. [Caching Strategies](#caching-strategies)
3. [Virtual Threads](#virtual-threads)
4. [Async Processing](#async-processing)
5. [Resource Management](#resource-management)

---

## Database access

Full guidance and fixes: `jpa-performance.md`.

| Flag | Impact | Fix |
|------|--------|-----|
| Lazy association accessed in a loop | N+1 queries | `JOIN FETCH`, `@EntityGraph`, DTO projection, or `hibernate.default_batch_fetch_size` |
| `@ManyToOne` / `@OneToOne` without `fetch = LAZY` | Extra queries on every load | Set `LAZY`; fetch per use case |
| `JOIN FETCH` of a collection with `Pageable` | Hibernate pages in memory over all rows | Page IDs first, or project to DTOs |
| `findAll()` on a growing table | Memory and latency grow with data | `Pageable` / `Slice` |
| Entities loaded only to map to DTOs | Over-fetching | DTO or interface projection |
| `save()` in a loop; `IDENTITY` IDs on bulk-insert paths | No JDBC batching | `hibernate.jdbc.batch_size`, `SEQUENCE`/TSID IDs, flush and clear per batch |
| Read services without `@Transactional(readOnly = true)` | Dirty checking and flush cost | Add it at class level |
| `maximum-pool-size: 100` or more | Contention; exceeds database connection limit | Size from measurement; start near `cores * 2 + 1` |
| `hibernate.session.events.log.LOG_QUERIES_SLOWER_THAN_MS` | Ignored on Hibernate 7 | `hibernate.log_slow_query` |

---

## Caching Strategies

### Spring Cache Abstraction

✅ **Enable caching** — the `Caffeine` builder must be wired into `CaffeineCacheManager` via `setCaffeine(...)`. A free-standing `@Bean Caffeine<Object, Object>` next to a hand-built `CaffeineCacheManager` is a common mistake: the cache runs with Caffeine's defaults (unbounded, no TTL) and the builder bean is dead code.

```java
@Configuration
@EnableCaching
public class CacheConfig {

    @Bean
    public CacheManager cacheManager(Caffeine<Object, Object> caffeine) {
        CaffeineCacheManager manager =
            new CaffeineCacheManager("users", "products");
        manager.setCaffeine(caffeine); // <-- the wiring step
        return manager;
    }

    @Bean
    public Caffeine<Object, Object> caffeineConfig() {
        return Caffeine.newBuilder()
            .maximumSize(1000)
            .expireAfterWrite(Duration.ofMinutes(10));
    }
}
```

> **Alternative:** drop the manual `CacheManager` bean and let Spring Boot auto-configure it. With `spring-boot-starter-cache` + Caffeine on the classpath, set `spring.cache.type=caffeine` and `spring.cache.cache-names=users,products`, then expose only the `Caffeine` bean — Boot wires it for you.

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
        .expireAfterWrite(Duration.ofMinutes(10))   // Absolute expiration
        .expireAfterAccess(Duration.ofMinutes(5));  // Sliding expiration
}
```

> **How the two clocks combine:** Caffeine evaluates both independently. An entry is evicted as soon as **either** deadline passes (the earlier of `write + 10m` and `lastAccess + 5m`), not the union. Setting both does not "extend" the TTL — it tightens it. Use one if you want one behavior, both only if you want "expire after 10m even if hot, sooner if idle." See: https://github.com/ben-manes/caffeine/wiki/Eviction#time-based

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
        // Jackson 3 serializer (Spring Data Redis 4). Type info is needed so cached
        // values come back as their classes, not LinkedHashMap. Restrict it to your packages.
        var values = GenericJacksonJsonRedisSerializer.builder()
            .enableDefaultTyping(BasicPolymorphicTypeValidator.builder()
                .allowIfSubType("com.example.")
                .build())
            .build();
        RedisCacheConfiguration config = RedisCacheConfiguration.defaultCacheConfig()
            .entryTtl(Duration.ofMinutes(10))
            .serializeKeysWith(SerializationPair.fromSerializer(new StringRedisSerializer()))
            .serializeValuesWith(SerializationPair.fromSerializer(values));
        return RedisCacheManager.builder(connectionFactory).cacheDefaults(config).build();
    }
}
```

Boot 4 gotchas (Spring Data Redis 4):

- `GenericJackson2JsonRedisSerializer` and `Jackson2JsonRedisSerializer` are deprecated (Jackson 2). Use `GenericJacksonJsonRedisSerializer` or `JacksonJsonRedisSerializer<T>`.
- `GenericJacksonJsonRedisSerializer.builder().build()` has no type info by default. Cached objects deserialize as `LinkedHashMap`, and `@Cacheable` methods fail with `ClassCastException`. Enable typing with a validator, as above, or use a typed `JacksonJsonRedisSerializer<>(User.class)` per cache.
- Do not use `enableUnsafeDefaultTyping()`. It allows any class in the cache data to be instantiated.

**Review Checklist:**
- [ ] Caching enabled for expensive operations
- [ ] Cache expiration configured
- [ ] Cache keys properly defined
- [ ] Cache invalidation on updates/deletes
- [ ] Cache size limits set
- [ ] Redis value serializer is the Jackson 3 one, with type info limited to app packages

---

## Virtual Threads

> Full guidance, usage thresholds, anti-patterns, and official citations are in [`java-25-features.md`](java-25-features.md#virtual-threads).

**Quick review checklist:**
- [ ] `spring.threads.virtual.enabled: true` is set (Spring Boot 4 config)
- [ ] Java 21-23 only: no `synchronized` blocks wrapping blocking I/O (use `ReentrantLock`). On Java 24+ `synchronized` does not pin (JEP 491), so do not flag it
- [ ] Virtual threads are not recommended for CPU-bound workloads
- [ ] Recommendation to use virtual threads is backed by measured workload evidence, not assumed

---

## Async Processing

### Spring @Async

Add `@EnableAsync` and use Boot's auto-configured executor. Tune it with properties instead of a custom bean:

```yaml
spring:
  task:
    execution:
      thread-name-prefix: async-
      pool:                 # platform threads (ThreadPoolTaskExecutor)
        core-size: 5
        max-size: 10
        queue-capacity: 100
      simple:               # used when spring.threads.virtual.enabled=true
        concurrency-limit: 50
```

| Flag | Why | Fix |
|------|-----|-----|
| Custom `AsyncConfigurer` or `TaskExecutor` bean while `spring.threads.virtual.enabled=true` | The custom executor replaces Boot's, so `@Async` does not run on virtual threads | Remove the custom bean, or build it on virtual threads on purpose |
| `@Async` method called from the same class | The proxy is skipped; the call runs synchronously | Call it through another bean |
| `@Async` side effect (email, message) sent inside a transaction | It can run before the commit, or for a rolled-back change | Publish an event and handle it with `@TransactionalEventListener` (or `@ApplicationModuleListener`) |
| `@Async void` method with no error handling | Exceptions are only logged | Return `CompletableFuture`, or configure an `AsyncUncaughtExceptionHandler` |
| Unbounded queue or no limit with virtual threads | Memory growth; overloads downstream systems | Set `queue-capacity` or `simple.concurrency-limit` |

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

### Structured Concurrency (preview only)

**Status:** Preview in every release so far: JDK 25 (JEP 505), JDK 26 (JEP 525), JDK 27 (JEP 533). It needs `--enable-preview` at compile time and at run time. The API changes between releases.

**Review rule:** in code built without `--enable-preview`, do not suggest Structured Concurrency, and do not flag `CompletableFuture` as outdated. `CompletableFuture` is the standard choice for parallel calls.

If the project already uses preview features, match the sample to its exact JDK:

```java
// JDK 25 shape (JEP 505)
public Dashboard getDashboard(Long userId) throws InterruptedException {
    try (var scope = StructuredTaskScope.open(Joiner.allSuccessfulOrThrow())) {
        Subtask<User> userTask = scope.fork(() -> userService.findById(userId));
        Subtask<List<Order>> ordersTask = scope.fork(() -> orderService.findByUserId(userId));
        scope.join();  // allSuccessfulOrThrow propagates any subtask failure
        return new Dashboard(userTask.get(), ordersTask.get());
    }
}

// JDK 27 shape (JEP 533): join() now throws ExecutionException on failure
public Dashboard getDashboard(Long userId) throws InterruptedException, ExecutionException {
    try (var scope = StructuredTaskScope.open(Joiner.allSuccessfulOrThrow())) {
        Subtask<User> userTask = scope.fork(() -> userService.findById(userId));
        Subtask<List<Order>> ordersTask = scope.fork(() -> orderService.findByUserId(userId));
        scope.join();
        return new Dashboard(userTask.get(), ordersTask.get());
    }
}
```

Other JDK 27 changes: `StructuredTaskScope` and `Joiner` take a third type parameter for the exception that `join()` throws, `Joiner.awaitAll()` is removed, and timeouts use `open(joiner, cfg -> cfg.withTimeout(duration))`.

**Benefits once it is final:** automatic cancellation of sibling tasks, task lifetime bound to the scope, one place to handle errors, and natural use of virtual threads.

| Use case | Without `--enable-preview` | With `--enable-preview` |
|----------|----------------------------|-------------------------|
| Spring `@Async` | `CompletableFuture` | `CompletableFuture` |
| Composition chains (`thenCompose`, `exceptionally`) | `CompletableFuture` | `CompletableFuture` |
| Parallel independent calls | `CompletableFuture` | Structured Concurrency (match the JDK) |
| Simple blocking I/O on virtual threads | Direct blocking calls | Direct blocking calls |

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
- [ ] Structured Concurrency suggested only if the project already uses `--enable-preview` (preview through JDK 27)
- [ ] CompletableFuture used appropriately (Spring @Async, complex composition chains)

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
- [ ] **Virtual threads**: recommended only with 10,000+ concurrent I/O-bound tasks and measured pool exhaustion
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
