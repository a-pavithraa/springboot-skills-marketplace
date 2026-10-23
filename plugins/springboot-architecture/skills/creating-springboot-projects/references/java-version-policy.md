# Java Version Policy (Spring Boot 4)

Single source for Java version advice. Other skills link here. Update this file when a new JDK ships.

Last checked: 2026-10-17.

## Policy

| Use | Java version |
|-----|--------------|
| Default for new projects | 25 (current LTS) |
| Accept when the user asks | 21 (previous LTS) or 17 (Boot 4 minimum) |
| Newest release | 27 (GA 2026-09-15, non-LTS) |
| Next LTS | 29 (expected September 2027) |

Rules:

- Default to Java 25. Do not pick a non-LTS release unless the project already tracks non-LTS releases.
- Do not flag Java 17 or 21 as "too old". Both are valid Boot 4 baselines.
- Before you pick Java 27, check the Spring Boot system requirements page. On 2026-10-17, Boot 4.1.1 lists support "up to and including Java 26".
- Read the Java version from `pom.xml` or `build.gradle` before you give version-specific advice.

## Preview APIs change between releases

Code compiled with `--enable-preview` runs only on the same JDK feature release. Preview APIs also change shape. Do not copy a preview sample to a different JDK.

| API | JDK 25 | JDK 26 | JDK 27 |
|-----|--------|--------|--------|
| Lazy init | `StableValue.of()` + `orElseSet(...)` (JEP 502) | `LazyConstant.of(supplier)` (JEP 526) | `LazyConstant.of(supplier)`; `isInitialized`/`orElse` removed; `Set.ofLazy` added (JEP 531) |
| Structured concurrency | `StructuredTaskScope.open(Joiner)` (JEP 505) | Sixth preview (JEP 525) | `join()` throws `ExecutionException`; third type parameter for the exception; `Joiner.awaitAll()` removed (JEP 533) |
| Primitive patterns | JEP 507 | JEP 530 | JEP 532 (unchanged from 26) |

## Runtime changes when you move past Java 25

### JDK 26

- **Final field mutation warns** (JEP 500). Deep reflection that writes `final` fields prints a warning. A future release will deny it. Serialization, mocking, and some injection libraries do this. Test with `--illegal-final-field-mutation=deny` to find them early. Prefer constructor injection.
- **AOT object caching works with any GC** (JEP 516). This can improve Boot startup.
- **HTTP/3 in `java.net.http.HttpClient`** (JEP 517).

### JDK 27

- **G1 is the default in all environments** (JEP 523). Before, the JVM picked Serial GC with 1 CPU or less than 1792 MB of memory. Small containers now get G1. Measure memory and latency in small pods. To keep Serial, set `-XX:+UseSerialGC`.
- **Compact object headers are on by default** (JEP 534). Headers shrink from 96 to 64 bits, so heap use drops. To turn them off, set `-XX:-UseCompactObjectHeaders`.
- **Post-quantum hybrid key exchange for TLS 1.3** (JEP 527). Test outbound HTTPS calls through your proxies before rollout.
- **JFR in-process data redaction** (JEP 536). Use it when JFR recordings leave the host.

## Sources

- [JDK 26](https://openjdk.org/projects/jdk/26/), [JDK 27](https://openjdk.org/projects/jdk/27/)
- [Spring Boot system requirements](https://docs.spring.io/spring-boot/system-requirements.html)
- [JEP 500](https://openjdk.org/jeps/500), [JEP 523](https://openjdk.org/jeps/523), [JEP 531](https://openjdk.org/jeps/531), [JEP 533](https://openjdk.org/jeps/533), [JEP 534](https://openjdk.org/jeps/534)
