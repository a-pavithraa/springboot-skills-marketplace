# Java 25 Features: Review Rules

Read the Java version from the build file first. Flag a feature only when the project's version supports it. For Java 26+ targets and preview-API changes, read `../../creating-springboot-projects/references/java-version-policy.md`.

## Contents

1. [Virtual Threads](#virtual-threads)
2. [Language features, Java 14-21](#language-features-java-14-21)
3. [Features finalized in JDK 22-25](#features-finalized-in-jdk-22-25)
4. [Preview features](#preview-features)
5. [Review checklist](#review-checklist)

---

## Virtual Threads

**Status:** Final since Java 21 ([JEP 444](https://openjdk.org/jeps/444)).

### When to recommend them

Recommend virtual threads only when ALL of these are true:

- 10,000+ concurrent tasks (actual concurrency, not daily totals).
- The workload is I/O-bound (database, HTTP, file I/O).
- Production metrics show thread-pool exhaustion.

Evidence:

- [Oracle Virtual Threads Guide](https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html): "If your application never has 10,000 virtual threads or more, it is unlikely to benefit from virtual threads."
- JEP 444: "Virtual threads cannot improve throughput for CPU-bound workloads." JEP 444 says "more than a few thousand" concurrent tasks. The 10,000 number comes from Oracle's guide, not from the JEP.

Do NOT recommend them for CPU-bound work, low concurrency, low-traffic services, or pools that are sized on purpose (rate limiting, backpressure).

### Pinning depends on the Java version

[JEP 491](https://openjdk.org/jeps/491), delivered in JDK 24:

- **Java 24+:** `synchronized` does NOT pin virtual threads. Do not flag `synchronized` as a pinning risk. Do not ask for a rewrite to `ReentrantLock`. Code that already uses `ReentrantLock` can stay as it is.
- **Java 21-23:** `synchronized` around blocking I/O pins the carrier thread. Flag it, and suggest `ReentrantLock`.
- **All versions:** pinning still occurs when a thread blocks in native code that calls back into Java, blocks in a class initializer, or waits for another thread to initialize a class. These cases are rare.

```java
// Java 21-23 only: pins the carrier
synchronized (lock) {
    String response = httpClient.send(request);
}

// Fix on Java 21-23
lock.lock();   // private final ReentrantLock lock = new ReentrantLock();
try {
    String response = httpClient.send(request);
} finally {
    lock.unlock();
}
```

On all versions, keep lock scopes narrow and avoid blocking I/O while holding a lock. That is a contention issue, not a pinning issue.

Diagnostics: `-Djdk.tracePinnedThreads` has no effect on JDK 24+. Use the JFR event `jdk.VirtualThreadPinned`.

### Spring Boot 4

- Enable with `spring.threads.virtual.enabled=true`.
- When enabled, the auto-configured task executor uses virtual threads, so `@Async` methods run on them.
- Remove manual thread-pool sizing for work that moves to virtual threads.
- If the requirements above are not met, keep the existing pools. They fit the workload.

---

## Language features, Java 14-21

All of these are final. Flag the old form only when the project's Java version supports the new one.

| Feature (min Java) | Flag this | Suggest this | Notes |
|--------------------|-----------|--------------|-------|
| Switch expressions (14) | `switch` statements that assign a variable with `break` | `switch` expression with `->` and `yield` | |
| Text blocks (15) | Multi-line SQL/JSON built with `+` and `\n` | `"""` text block, also in `@Query` | A closing `"""` on its own line keeps a trailing newline |
| `instanceof` patterns (16) | `instanceof` followed by a cast | `if (obj instanceof String s)` | |
| Records (16) | Immutable DTOs with hand-written getters, `equals`, `hashCode` | `record`, with validation in the compact constructor | Use records for DTOs, projections, value objects. Never as JPA entities |
| Sealed types (17) | Fixed hierarchies (events, states) left open | `sealed interface ... permits ...` | Enables exhaustive `switch` without `default` |
| Switch patterns (21) | `if/else instanceof` chains | `switch (obj) { case Integer i -> ... }` | `case null` is allowed |
| Record patterns (21) | Manual accessor calls after a type check | `if (obj instanceof Point(int x, int y))` | Also works in `switch` |
| Sequenced collections (21) | `list.get(0)`, `list.get(list.size() - 1)`, `Collections.reverse` | `getFirst()`, `getLast()`, `reversed()` | `reversed()` is a view; on an unmodifiable list it is read-only |

String Templates do not exist. They previewed in JDK 21-22 (JEP 430, 459) and were withdrawn (JEP 465). Flag any `STR."..."` code. Use `formatted()` or `String.format`.

---

## Features finalized in JDK 22-25

| Feature | Status | Recommend when | Do not recommend when |
|---------|--------|----------------|-----------------------|
| Foreign Function & Memory API | Final in 22 (JEP 454) | The code calls native C/C++ libraries | A pure-Java solution exists |
| Module import declarations (`import module java.sql;`) | Final in 25 (JEP 511) | Many imports from one module | Most Spring code; normal imports are clearer |
| Flexible constructor bodies | Final in 25 (JEP 513) | Validation or argument prep must run before `super(...)`/`this(...)` | A helper method is already clear |
| Scoped values | Final in 25 (JEP 506) | Request context passed down a call tree, mainly with virtual threads; replaces `ThreadLocal` | The value must change inside the scope |
| Key Derivation Function API (`javax.crypto.KDF`) | Final in 25 (JEP 510) | HKDF key derivation (session keys, sub-keys from a master secret) | Password hashing |

Facts to check in review:

- Flexible constructor bodies: code before `super(...)` can validate arguments and assign fields, but cannot read `this`.
- Scoped values: `ScopedValue.where(KEY, value).run(task)`, then `KEY.get()` inside the scope. In JDK 25, `ScopedValue.orElse` does not accept `null`.
- KDF: HKDF is the only algorithm in JDK 25 (`KDF.getInstance("HKDF-SHA256")`, `HKDFParameterSpec.ofExtract().addIKM(ikm).addSalt(salt).thenExpand(info, 32)`). PBKDF2 stays on `SecretKeyFactory`. bcrypt, scrypt, and Argon2 are not included. For passwords, use Spring Security's `PasswordEncoder`.

---

## Preview features

Preview features need `--enable-preview` at compile time and at run time, and the API can change in each release. Suggest them only when the project already uses `--enable-preview`. Match samples to the project's exact JDK.

### Lazy Constants (was Stable Values)

JDK 25: `StableValue` (JEP 502). JDK 26: `LazyConstant` (JEP 526). JDK 27: third preview (JEP 531).

```java
// JDK 25 only (JEP 502), removed in JDK 26
private final StableValue<DatabaseConfig> config = StableValue.of();
DatabaseConfig getConfig() { return config.orElseSet(this::loadDatabaseConfig); }

// JDK 26 and 27 (JEP 526 / JEP 531)
private final LazyConstant<DatabaseConfig> config = LazyConstant.of(this::loadDatabaseConfig);
DatabaseConfig getConfig() { return config.get(); }
```

Since JDK 26, `null` results are not allowed, and lazy collections use `List.ofLazy` and `Map.ofLazy`. JDK 27 removes `isInitialized()` and `orElse()` and adds `Set.ofLazy`.

Without `--enable-preview`, a `static final` holder class or a Spring singleton bean covers most cases.

### Primitive types in patterns

Preview: JDK 25 (JEP 507), JDK 26 (JEP 530), JDK 27 (JEP 532, unchanged from 26). Allows `obj instanceof int i` and `case int i ->`. A pattern does not match when the conversion would lose data: with `long v = 1000L`, `v instanceof byte b` is false; with `v = 100L` it is true.

### Structured concurrency

See `performance-patterns.md#structured-concurrency-preview-only`.

---

## Review checklist

- [ ] Java version read from the build file before any version-specific finding
- [ ] Old `switch`, `instanceof` + cast, string concatenation for multi-line text, boilerplate DTOs: use the Java 14-21 forms above
- [ ] `list.get(0)` / `list.get(list.size() - 1)`: use `getFirst()` / `getLast()`
- [ ] Virtual threads recommended only with 10,000+ concurrent I/O-bound tasks and measured pool exhaustion
- [ ] Java 21-23 only: `synchronized` around blocking I/O. Not a finding on Java 24+
- [ ] `ThreadLocal` for request context: consider scoped values (Java 25)
- [ ] Custom HKDF code: consider `javax.crypto.KDF` (Java 25). Never for passwords
- [ ] Preview APIs suggested only when the project uses `--enable-preview`

## Official documentation

- [OpenJDK JDK 25](https://openjdk.org/projects/jdk/25/), [JDK 25 release notes](https://www.oracle.com/java/technologies/javase/25-relnote-issues.html)
- [Virtual Threads Guide](https://docs.oracle.com/en/java/javase/25/core/virtual-threads.html), [Spring Boot task execution](https://docs.spring.io/spring-boot/reference/features/task-execution-and-scheduling.html)
- JEPs: [444](https://openjdk.org/jeps/444), [491](https://openjdk.org/jeps/491), [506](https://openjdk.org/jeps/506), [510](https://openjdk.org/jeps/510), [511](https://openjdk.org/jeps/511), [513](https://openjdk.org/jeps/513), [531](https://openjdk.org/jeps/531)
