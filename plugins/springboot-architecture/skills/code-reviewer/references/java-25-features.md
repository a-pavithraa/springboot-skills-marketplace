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

- High-concurrency I/O-bound workloads
- Microservices with many blocking calls (DB, HTTP, etc.)
- Replacing thread pools for blocking operations

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

- [ ] Replace `@Async` thread pools with virtual threads config
- [ ] Replace `synchronized` with `ReentrantLock` in I/O code paths
- [ ] Remove manual thread pool sizing (virtual threads scale automatically)
- [ ] Test under load to verify no pinning issues

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
List<String> reversed = list.reversed(); // Immutable view
```

---

## String Templates

**Status:** ❌ WITHDRAWN (was JEP 430/459, removed in Java 23)

⚠️ **String Templates were withdrawn from the Java language and are NOT available in Java 25.**

The feature was previewed in Java 21-22 but was removed before becoming standard due to community feedback. Use traditional string formatting instead:

```java
String name = "Alice";
int age = 30;

// ✅ Use String.format
String msg = String.format("Hello, %s! You are %d years old.", name, age);

// ✅ Or StringBuilder/concat for simple cases
String msg = "Hello, " + name + "! You are " + age + " years old.";

// ✅ Or text blocks for multi-line
String msg = """
    Hello, %s!
    You are %d years old.
    """.formatted(name, age);

// ❌ NOT AVAILABLE: String templates
// String msg = STR."Hello, \{name}! You are \{age} years old.";
```

**Reference:** [JEP 430 (Withdrawn)](https://openjdk.org/jeps/430)

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

**Status:** Preview (Java 25)

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

**Status:** Preview (Java 25)

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

**Status:** Preview (Java 25)

Thread-local-like values optimized for virtual threads and structured concurrency.

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

**Status:** Preview (Java 25)

Provides values that are computed lazily and cached.

```java
public class ConfigurationManager {
    private final StableValue<DatabaseConfig> config = StableValue.of(() -> {
        // Expensive computation, only runs once
        return loadDatabaseConfig();
    });

    public DatabaseConfig getConfig() {
        return config.get();  // Cached after first call
    }
}
```

**Use cases:**
- Expensive computations that should run at most once
- Thread-safe lazy initialization
- Simpler than double-checked locking patterns

---

## Key Derivation Function API

**Status:** Preview (Java 25)

Standard API for password-based key derivation (PBKDF2, bcrypt, scrypt, argon2).

```java
// Generate key from password
KeyDerivation kd = KeyDerivation.getInstance("PBKDF2WithHmacSHA256");
KDFParameters params = KDFParameters.ofPBKDF2()
    .salt(salt)
    .iterations(100000)
    .keyLength(256);

SecretKey key = kd.deriveKey(password, params);

// For password hashing (bcrypt-style)
KeyDerivation kd = KeyDerivation.getInstance("bcrypt");
byte[] hash = kd.deriveKey(password, params).getEncoded();
```

**Benefit:** Unified API for all KDF algorithms instead of provider-specific code.

---

## Foreign Function & Memory API

**Status:** Preview (JEP 454 - Java 22+)

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

### Medium Priority

6. **Virtual Threads** - Requires testing, high impact for I/O-bound apps
7. **Sealed Classes** - Where type hierarchies are fixed
8. **Switch Pattern Matching** - When working with type hierarchies
9. **Primitive Patterns** - When pattern matching with primitives (preview)

### Low Priority (Evaluate Carefully)

10. **Module Import Declarations** - Preview, only for module-heavy codebases
11. **Flexible Constructor Bodies** - Preview, only when needed for validation
12. **Scoped Values** - Preview, only for virtual thread-heavy applications
13. **Stable Values** - Preview, can use existing lazy initialization patterns
14. **Key Derivation Function API** - Preview, only for new security code
15. **FFM API** - Only if calling native libraries

### Not Available

❌ **String Templates** - Withdrawn, not available in Java 25

---

## Review Checklist

When reviewing Java code, check for:

- [ ] Old `instanceof` + cast patterns → Use pattern matching
- [ ] Mutable DTOs with boilerplate → Use records
- [ ] String concatenation for multi-line text → Use text blocks
- [ ] Old switch statements → Use switch expressions
- [ ] Thread pools for I/O blocking operations → Consider virtual threads
- [ ] `list.get(0)` / `list.get(list.size()-1)` → Use `getFirst()` / `getLast()`
- [ ] Open-ended class hierarchies that should be sealed → Use sealed classes
- [ ] Pattern matching with boxed primitives → Consider primitive patterns (preview)
- [ ] Many imports from single module → Consider module import declarations (preview)
- [ ] Complex constructor validation → Consider flexible constructor bodies (preview)
- [ ] ThreadLocal for request context → Consider Scoped Values (preview)
- [ ] Manual lazy initialization → Consider Stable Values (preview)
- [ ] Custom KDF implementations → Consider Key Derivation Function API (preview)

## Official Documentation

- [JDK 25 Release Notes](https://www.oracle.com/java/technologies/javase/25-relnote-issues.html)
- [OpenJDK JDK 25](https://openjdk.org/projects/jdk/25/)
- [Virtual Threads Guide](https://docs.oracle.com/en/java/javase/25/core/virtual-threads.html)
- [JEP 507: Primitive Types in Patterns](https://openjdk.org/jeps/507)
- [JEP 441: Pattern Matching for switch](https://openjdk.org/jeps/441)
- [JEP 409: Sealed Classes](https://openjdk.org/jeps/409)
- [JEP 395: Records](https://openjdk.org/jeps/395)
