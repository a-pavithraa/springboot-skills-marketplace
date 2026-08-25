# Java 25 Features and Modern Patterns

## Table of Contents

1. [Virtual Threads (Project Loom)](#virtual-threads)
2. [Pattern Matching](#pattern-matching)
3. [Records](#records)
4. [Sealed Classes](#sealed-classes)
5. [Text Blocks](#text-blocks)
6. [Switch Expressions](#switch-expressions)
7. [Sequenced Collections](#sequenced-collections)
8. [String Templates](#string-templates)
9. [Foreign Function & Memory API](#foreign-function--memory-api)

---

## Virtual Threads

**Status:** Stable (JEP 444 - Java 21+)

### What They Are

Lightweight threads managed by the JVM, not the OS. Enable millions of concurrent threads with minimal overhead.

### When to Use

**Official Oracle guidance** ([Java Virtual Threads](https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html)):
> "If your application never has 10,000 virtual threads or more, it is unlikely to benefit from virtual threads."

✅ **Use virtual threads when ALL criteria are met:**
- 10,000+ concurrent tasks (not daily totals, actual concurrency)
  - **Source:** This threshold is from [Oracle's official Java 21 Virtual Threads Guide](https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html)
  - **JEP 444** also emphasizes virtual threads are for "a **great number** of concurrent tasks"
- I/O-bound workload (database queries, HTTP calls, file I/O)
- Tasks spend most time waiting/blocked on I/O
- Thread pool exhaustion observed in production metrics

❌ **Do NOT use virtual threads when:**
- Low concurrency (<10,000 concurrent tasks)
  - **Evidence:** Oracle states applications below this threshold "are unlikely to benefit"
- CPU-bound workload (computation, data processing)
  - **Evidence:** [JEP 444](https://openjdk.org/jeps/444) explicitly states "cannot improve throughput for CPU-bound workloads"
- Intentional thread pool sizing (rate limiting, backpressure)
- Low-traffic applications (hundreds of requests per day)

### Anti-Patterns

❌ **Don't use for CPU-bound tasks**
```java
// BAD: Virtual threads don't help CPU-intensive work
ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor();
executor.submit(() -> {
    // CPU-intensive computation
    return computePrimeFactors(largeNumber);
});
```

❌ **Don't pin virtual threads** (synchronized blocks on long operations)
```java
// BAD: synchronized blocks pin virtual threads
synchronized (lock) {
    String response = httpClient.send(request); // Blocking I/O
}
```

✅ **Use ReentrantLock instead**
```java
// GOOD: ReentrantLock doesn't pin
private final ReentrantLock lock = new ReentrantLock();

lock.lock();
try {
    String response = httpClient.send(request);
} finally {
    lock.unlock();
}
```

### Spring Boot 4 Integration

✅ **Enable virtual threads**
```yaml
spring:
  threads:
    virtual:
      enabled: true
```

✅ **Async methods automatically use virtual threads**
```java
@Service
public class UserService {
    @Async // Uses virtual threads when enabled
    public CompletableFuture<User> fetchUser(Long id) {
        return CompletableFuture.completedFuture(userRepository.findById(id));
    }
}
```

### Migration Checklist

**BEFORE migrating to virtual threads, verify requirements:**
- [ ] Application has 10,000+ concurrent tasks (measure actual concurrency, not daily totals)
- [ ] Workload is primarily I/O-bound (database, HTTP, file operations)
- [ ] Thread pool exhaustion is observed in production metrics
- [ ] Using Java 21+ on Spring Boot 4 (or Spring Boot 3.2+ on legacy stacks)

**IF requirements met, then migrate:**
- [ ] Replace `@Async` thread pools with virtual threads config
- [ ] Replace `synchronized` with `ReentrantLock` in I/O code paths
- [ ] Remove manual thread pool sizing (virtual threads scale automatically)
- [ ] Test under load to verify no pinning issues

**IF requirements NOT met:**
- [ ] Keep existing thread pools - they are appropriate for the workload
- [ ] Consider tuning pool sizes if metrics show under-provisioning
- [ ] Re-evaluate when concurrency increases significantly

### Official References for Virtual Threads

The 10,000 concurrent tasks threshold and usage guidance comes from official sources:

1. **[Oracle Java 21 Virtual Threads Guide](https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html)**
   - Primary documentation stating: "If your application never has 10,000 virtual threads or more, it is unlikely to benefit from virtual threads."

2. **[JEP 444: Virtual Threads](https://openjdk.org/jeps/444)**
   - Official Java Enhancement Proposal (Final)
   - States: "Virtual threads cannot improve throughput for CPU-bound workloads"
   - Uses softer language than Oracle's guide: "significant improvement when the number of concurrent tasks is high (more than a few thousand)" — does **not** state the 10,000 threshold specifically

3. **[JEP 425: Virtual Threads (Preview)](https://openjdk.org/jeps/425)**
   - Earlier preview specification

4. **[Spring Boot Task Execution Documentation](https://docs.spring.io/spring-boot/reference/features/task-execution-and-scheduling.html)**
   - How Spring Boot integrates virtual threads

---

## Pattern Matching

### instanceof Pattern Matching

**Status:** Stable (JEP 394 - Java 16+)

❌ **Old way**
```java
if (obj instanceof String) {
    String str = (String) obj;
    return str.length();
}
```

✅ **Modern way**
```java
if (obj instanceof String str) {
    return str.length();
}
```

### Switch Pattern Matching

**Status:** Stable (JEP 441 - Java 21+)

❌ **Old way**
```java
String formatted;
if (obj instanceof Integer i) {
    formatted = String.format("int %d", i);
} else if (obj instanceof Long l) {
    formatted = String.format("long %d", l);
} else if (obj instanceof Double d) {
    formatted = String.format("double %f", d);
} else {
    formatted = obj.toString();
}
```

✅ **Modern way**
```java
String formatted = switch (obj) {
    case Integer i -> String.format("int %d", i);
    case Long l    -> String.format("long %d", l);
    case Double d  -> String.format("double %f", d);
    case null      -> "null";
    default        -> obj.toString();
};
```

### Record Pattern Matching

**Status:** Stable (JEP 440 - Java 21+)

```java
record Point(int x, int y) {}

// Deconstruct records in pattern matching
if (obj instanceof Point(int x, int y)) {
    return x + y;
}

// Or in switch
String result = switch (shape) {
    case Circle(double radius) -> "Circle: " + radius;
    case Rectangle(double w, double h) -> "Rectangle: " + w + "x" + h;
    default -> "Unknown";
};
```

---

## Records

**Status:** Stable (JEP 395 - Java 16+)

### When to Use

- DTOs (Data Transfer Objects)
- Value objects in DDD
- Immutable data carriers
- API request/response models

❌ **Old DTO**
```java
public class UserDTO {
    private final Long id;
    private final String name;
    private final String email;

    public UserDTO(Long id, String name, String email) {
        this.id = id;
        this.name = name;
        this.email = email;
    }

    public Long getId() { return id; }
    public String getName() { return name; }
    public String getEmail() { return email; }

    @Override
    public boolean equals(Object o) { /* boilerplate */ }
    @Override
    public int hashCode() { /* boilerplate */ }
    @Override
    public String toString() { /* boilerplate */ }
}
```

✅ **Modern record**
```java
public record UserDTO(Long id, String name, String email) {
    // Optional: Custom validation
    public UserDTO {
        Objects.requireNonNull(id, "id cannot be null");
        Objects.requireNonNull(email, "email cannot be null");
    }
}
```

### Records with JPA (Spring Boot 4)

✅ **Use records for projections**
```java
public interface UserRepository extends JpaRepository<User, Long> {
    // Records work great for projections
    @Query("SELECT new com.example.UserSummary(u.id, u.name) FROM User u")
    List<UserSummary> findAllSummaries();
}

record UserSummary(Long id, String name) {}
```

❌ **Don't use records as entities** (records are immutable, JPA needs mutability)

---

## Sealed Classes

**Status:** Stable (JEP 409 - Java 17+)

### When to Use

- Domain modeling with fixed type hierarchies
- State machines
- ADTs (Algebraic Data Types)

✅ **Example: Domain events**
```java
public sealed interface DomainEvent
    permits UserCreated, UserUpdated, UserDeleted {

    LocalDateTime occurredAt();
}

public record UserCreated(Long userId, String email, LocalDateTime occurredAt)
    implements DomainEvent {}

public record UserUpdated(Long userId, Map<String, Object> changes, LocalDateTime occurredAt)
    implements DomainEvent {}

public record UserDeleted(Long userId, LocalDateTime occurredAt)
    implements DomainEvent {}
```

✅ **Exhaustive pattern matching**
```java
String describe(DomainEvent event) {
    return switch (event) {
        case UserCreated e -> "User created: " + e.email();
        case UserUpdated e -> "User updated: " + e.changes().size() + " fields";
        case UserDeleted e -> "User deleted: " + e.userId();
        // No default needed - compiler knows all cases
    };
}
```

---

## Text Blocks

**Status:** Stable (JEP 378 - Java 15+)

❌ **Old way**
```java
String query = "SELECT u.id, u.name, u.email\n" +
               "FROM users u\n" +
               "WHERE u.active = true\n" +
               "ORDER BY u.name";
```

✅ **Modern way**
```java
String query = """
    SELECT u.id, u.name, u.email
    FROM users u
    WHERE u.active = true
    ORDER BY u.name
    """;
```

### Spring Boot Integration

✅ **Use in @Query**
```java
@Query("""
    SELECT u FROM User u
    LEFT JOIN FETCH u.roles
    WHERE u.active = true
    AND u.createdAt > :since
    """)
List<User> findActiveUsersSince(@Param("since") LocalDateTime since);
```

---

## Switch Expressions

**Status:** Stable (JEP 361 - Java 14+)

❌ **Old switch statement**
```java
String result;
switch (status) {
    case PENDING:
        result = "Waiting";
        break;
    case APPROVED:
        result = "Accepted";
        break;
    case REJECTED:
        result = "Denied";
        break;
    default:
        result = "Unknown";
}
```

✅ **Modern switch expression**
```java
String result = switch (status) {
    case PENDING -> "Waiting";
    case APPROVED -> "Accepted";
    case REJECTED -> "Denied";
};
```

✅ **With yield for complex logic**
```java
int bonus = switch (performanceRating) {
    case EXCELLENT -> {
        log.info("Calculating excellent bonus");
        yield salary * 20 / 100;
    }
    case GOOD -> salary * 10 / 100;
    case AVERAGE -> salary * 5 / 100;
    default -> 0;
};
```

---

## Sequenced Collections

**Status:** Stable (JEP 431 - Java 21+)

### New Methods

```java
List<String> list = List.of("a", "b", "c");

String first = list.getFirst();     // "a"
String last = list.getLast();       // "c"
List<String> reversed = list.reversed();  // [c, b, a]
```

❌ **Old way**
```java
String first = list.isEmpty() ? null : list.get(0);
String last = list.isEmpty() ? null : list.get(list.size() - 1);
Collections.reverse(list); // Mutates!
```

✅ **Modern way**
```java
String first = list.getFirst();
String last = list.getLast();
List<String> reversed = list.reversed(); // Read-only view (writes throw UnsupportedOperationException)
```

---

## String Templates

**Status:** ❌ WITHDRAWN — not available in Java 25

⚠️ **String Templates were withdrawn from the Java language and are NOT available in Java 25.**

Timeline:
- JEP 430 — First Preview, delivered in JDK 21 (Status: Closed / Delivered)
- JEP 459 — Second Preview, delivered in JDK 22 (Status: Closed / Delivered)
- JEP 465 — proposed Third Preview, **Closed / Withdrawn** before JDK 23. No string-template feature shipped in JDK 23 or later.

Use traditional string formatting instead:

```java
String name = "Alice";
int age = 30;

// ✅ Use String.format
String msg = String.format("Hello, %s! You are %d years old.", name, age);

// ✅ Or StringBuilder/concat for simple cases
String msg = "Hello, " + name + "! You are " + age + " years old.";

// ✅ Or text blocks for multi-line
// Note: closing """ on its own line keeps a trailing newline. Strip it
// with .stripTrailing(), or put the """ right after the last character.
String msg = """
    Hello, %s!
    You are %d years old.
    """.stripTrailing().formatted(name, age);

// ❌ NOT AVAILABLE: String templates
// String msg = STR."Hello, \{name}! You are \{age} years old.";
```

**References:** [JEP 430](https://openjdk.org/jeps/430), [JEP 459](https://openjdk.org/jeps/459), [JEP 465 (Withdrawn)](https://openjdk.org/jeps/465)

---

## Primitive Types in Patterns

**Status:** Third Preview (JEP 507 - Java 25)

Extends pattern matching to work with all primitive types in `instanceof` and `switch`.

```java
// Before: Only reference types
Object obj = 42;
if (obj instanceof Integer i) {
    int value = i.intValue();
}

// Java 25: Direct primitive patterns
Object obj = 42;
if (obj instanceof int i) {
    // i is already an int
    return i * 2;
}

// Switch with primitives
String describe(Object obj) {
    return switch (obj) {
        case int i -> "Integer: " + i;
        case long l -> "Long: " + l;
        case double d -> "Double: " + d;
        case boolean b -> "Boolean: " + b;
        default -> "Other";
    };
}
```

**Safeguards lossy conversions:**
```java
Object obj = 1000L;
if (obj instanceof byte b) {  // Won't match - lossy conversion
    // Never executes
}
```

**Reference:** [JEP 507](https://openjdk.org/jeps/507)

---

## Module Import Declarations

**Status:** Standard (JEP 511 - Java 25; previewed via JEP 476 in JDK 23 and JEP 494 in JDK 24)

Simplifies importing all packages from a module.

```java
// Before: Import each package individually
import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;

// Java 25: Import entire module
import module java.sql;

// Now all java.sql packages are available
Connection conn = ...;
ResultSet rs = ...;
```

**Use case:** Reduces boilerplate when using many packages from a single module.

---

## Flexible Constructor Bodies

**Status:** Standard (JEP 513 - Java 25; previewed via JEP 447 in JDK 22 and JEP 492 in JDK 24)

Allows statements before `this()` or `super()` calls in constructors.

```java
public class User {
    private final String username;
    private final String normalizedUsername;

    // Before: Can't validate before super()
    public User(String username) {
        super();  // Must be first
        if (username == null) throw new IllegalArgumentException();
        this.username = username;
        this.normalizedUsername = username.toLowerCase();
    }

    // Java 25: Validate before calling super()
    public User(String username) {
        if (username == null) {
            throw new IllegalArgumentException("Username cannot be null");
        }
        String normalized = username.toLowerCase();
        super();  // Can come after validation
        this.username = username;
        this.normalizedUsername = normalized;
    }
}
```

**Benefit:** Cleaner validation logic without helper methods.

---

## Scoped Values API

**Status:** Standard (JEP 506, finalized in Java 25)

Thread-local-like values optimized for virtual threads and structured concurrency. Finalized in JDK 25 with one behavior change: `ScopedValue.orElse` no longer accepts null as its argument.

```java
public class RequestContext {
    private static final ScopedValue<String> USER_ID = ScopedValue.newInstance();

    public static void handleRequest(String userId, Runnable task) {
        ScopedValue.where(USER_ID, userId).run(task);
    }

    public static String getCurrentUserId() {
        return USER_ID.get();
    }
}

// Usage
RequestContext.handleRequest("user123", () -> {
    // USER_ID is available in this scope and child threads
    String userId = RequestContext.getCurrentUserId();
    // Process request
});
```

**Advantages over ThreadLocal:**
- Immutable once set
- Better performance with virtual threads
- Clear scoping with try-with-resources style

---

## Stable Values API

**Status:** Preview (JEP 502 - Java 25)

Provides at-most-once initialization with deferred immutability — like `final` but initialized on demand. JEP 502 uses a no-arg factory `StableValue.of()` to create an unset holder, and `orElseSet(Supplier)` to initialize-or-read.

```java
public class ConfigurationManager {
    // Unset stable value
    private final StableValue<DatabaseConfig> config = StableValue.of();

    public DatabaseConfig getConfig() {
        // orElseSet returns the cached value if already set; otherwise it
        // evaluates the supplier exactly once (even under concurrent calls)
        // and caches the result.
        return config.orElseSet(this::loadDatabaseConfig);
    }

    private DatabaseConfig loadDatabaseConfig() {
        // Expensive initialization — runs at most once via orElseSet above.
        return new DatabaseConfig(/* ... */);
    }
}
```

**Source:** [JEP 502](https://openjdk.org/jeps/502) — "stable value, created with the static factory method `StableValue.of()` ... `orElseSet` method guarantees that the provided lambda expression is evaluated only once, even when ... invoked concurrently."

**Use cases:**
- Expensive computations that should run at most once
- Thread-safe lazy initialization
- Simpler than double-checked locking patterns

---

## Key Derivation Function API

**Status:** Standard (JEP 510 - Java 25; previewed via JEP 478 in JDK 24)

JEP 510 introduces `javax.crypto.KDF`, a unified API for Key Derivation Functions. **The only algorithm shipped in JDK 25 is HKDF** (HMAC-based, RFC 5869). PBKDF1 and PBKDF2 stay on the existing `SecretKeyFactory` API. Argon2 is listed as future work, and bcrypt/scrypt are not included.

```java
import javax.crypto.KDF;
import javax.crypto.SecretKey;
import javax.crypto.spec.HKDFParameterSpec;
import java.security.spec.AlgorithmParameterSpec;

// HKDF "extract then expand" mode — produce a 32-byte derived key
KDF hkdf = KDF.getInstance("HKDF-SHA256");

AlgorithmParameterSpec spec = HKDFParameterSpec
        .ofExtract()
        .addIKM(inputKeyMaterial)   // initial key material (byte[] or SecretKey)
        .addSalt(salt)              // byte[]
        .thenExpand(info, 32);      // info bytes + output length in bytes

SecretKey derived = hkdf.deriveKey("AES", spec);

// For raw bytes instead of a SecretKey
byte[] keyBytes = hkdf.deriveData(spec);
```

**Use cases:** session-key derivation in TLS 1.3-style protocols, deriving multiple keys from a master secret, PKCS#11-backed HKDF on hardware crypto devices.

**Do NOT use this API for:**
- **Password hashing.** JEP 510 explicitly leaves PBKDF1/PBKDF2 on `SecretKeyFactory`; bcrypt, scrypt, and Argon2 are not included in JDK 25.

**Source:** [JEP 510](https://openjdk.org/jeps/510) — "We define a new class, `javax.crypto.KDF` ... The HKDF algorithm ... is the only KDF we intend to include at this time ... PBKDF1 and PBKDF2 ... will remain available via the existing `SecretKeyFactory` API."

---

## Foreign Function & Memory API

**Status:** Standard (JEP 454 - Java 22+)

**Use case:** Native library integration without JNI

⚠️ **Advanced feature - only use if necessary**

✅ **When to use:**
- Calling native libraries (C/C++)
- Performance-critical native code
- Legacy system integration

❌ **When not to use:**
- Pure Java solutions exist
- Not performance-critical
- Team lacks native code expertise

---

## Migration Priority

### High Priority (Do First)

1. **Records** - Easy wins for DTOs
2. **Text Blocks** - Improves readability
3. **Switch Expressions** - Reduces bugs
4. **instanceof Pattern Matching** - Common pattern
5. **Sequenced Collections** - Safer than manual index access

### Medium Priority (Evaluate Carefully)

6. **Virtual Threads** - ONLY if 10,000+ concurrent tasks, I/O-bound workload, and thread pool exhaustion
   - Most applications do NOT meet these criteria
   - Measure actual concurrency before adopting
   - Reference: [Oracle Virtual Threads Guide](https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html)
7. **Sealed Classes** - Where type hierarchies are fixed
8. **Switch Pattern Matching** - When working with type hierarchies
9. **Primitive Patterns** - When pattern matching with primitives (preview)

### Medium Priority (Standard but situational)

10. **Scoped Values** - Standard in JDK 25 (JEP 506). Adopt for request-scoped context propagation in virtual-thread-heavy applications instead of `ThreadLocal`.
11. **Module Import Declarations** - Standard in JDK 25 (JEP 511). Only worth adopting for module-heavy codebases.
12. **Flexible Constructor Bodies** - Standard in JDK 25 (JEP 513). Adopt only when constructor validation logic is genuinely cleaner than helper-method workarounds.
13. **Key Derivation Function API** - Standard in JDK 25 (JEP 510). Adopt `javax.crypto.KDF` for HKDF-based key derivation (e.g. deriving session or sub-keys from a master secret). It ships **only HKDF** — password hashing stays on `SecretKeyFactory` (PBKDF1/PBKDF2), and Argon2/scrypt/bcrypt are not included.

### Low Priority (Evaluate Carefully)

14. **Stable Values** - Preview in JDK 25 (JEP 502). Existing lazy-initialization patterns already cover most cases.
15. **FFM API** - Standard since JDK 22 (JEP 454). Adopt only if calling native libraries; otherwise plain Java is simpler.

### Not Available

❌ **String Templates** - Withdrawn, not available in Java 25

---

## Review Checklist

When reviewing Java code, check for:

- [ ] Old `instanceof` + cast patterns → Use pattern matching
- [ ] Mutable DTOs with boilerplate → Use records
- [ ] String concatenation for multi-line text → Use text blocks
- [ ] Old switch statements → Use switch expressions
- [ ] Thread pools with metrics showing exhaustion → Evaluate virtual threads (requires 10,000+ concurrent tasks and I/O-bound workload)
- [ ] `list.get(0)` / `list.get(list.size()-1)` → Use `getFirst()` / `getLast()`
- [ ] Open-ended class hierarchies that should be sealed → Use sealed classes
- [ ] Pattern matching with boxed primitives → Consider primitive patterns (preview in JDK 25, JEP 507)
- [ ] Many imports from single module → Consider module import declarations (standard in JDK 25, JEP 511)
- [ ] Complex constructor validation → Consider flexible constructor bodies (standard in JDK 25, JEP 513)
- [ ] ThreadLocal for request context → Use Scoped Values (standard in JDK 25, JEP 506)
- [ ] Manual lazy initialization → Consider Stable Values (preview in JDK 25, JEP 502)
- [ ] Custom KDF implementations → Consider Key Derivation Function API (standard in JDK 25, JEP 510)

## Official Documentation

- [JDK 25 Release Notes](https://www.oracle.com/java/technologies/javase/25-relnote-issues.html)
- [OpenJDK JDK 25](https://openjdk.org/projects/jdk/25/)
- [Virtual Threads Guide](https://docs.oracle.com/en/java/javase/25/core/virtual-threads.html)
- [JEP 507: Primitive Types in Patterns](https://openjdk.org/jeps/507)
- [JEP 441: Pattern Matching for switch](https://openjdk.org/jeps/441)
- [JEP 409: Sealed Classes](https://openjdk.org/jeps/409)
- [JEP 395: Records](https://openjdk.org/jeps/395)
