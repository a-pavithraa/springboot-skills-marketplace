# Spring Boot 4.0 Migration Guide

> **Official Documentation**: [Spring Boot 4.0 Migration Guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide)

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Migration Strategy](#migration-strategy)
3. [Dependency Changes](#dependency-changes)
4. [Code Changes](#code-changes)
5. [Configuration Changes](#configuration-changes)
6. [Test Changes](#test-changes)
7. [Verification](#verification)

---

## System Requirements

### Required Versions

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **Java** | 17 | 21+ (25 for latest features) |
| **Spring Boot** | 4.0.0 | 4.0.x (latest stable) |
| **Jakarta EE** | 11 | 11 |
| **Servlet** | 6.1 | 6.1 |

**Java Version Note:**
- Minimum: Java 17
- Recommended: Java 21 (LTS) or Java 25 (latest features)

---

## Migration Strategy

### Recommended Approach: Gradual Migration with Classic Starters

Spring Boot 4.0 introduces **modular architecture** with granular starters. For existing projects, Spring Boot provides "classic" starters to ease migration:

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-classic</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-test-classic</artifactId>
    <scope>test</scope>
</dependency>
```

**Benefits:**
- Fewer breaking changes upfront
- Easier rollback if issues arise
- Gradual migration to modular starters

**Recommended Migration Path:**
1. Upgrade to classic starters first
2. Verify application works
3. Incrementally migrate to modular starters (optional)

### Alternative: Direct Migration

Update directly to new modular starters (web→webmvc, aop→aspectj, etc.)

**Benefits:**
- Clean, modern codebase from the start
- No technical debt from classic starters

**Drawbacks:**
- More changes at once
- Higher risk

---

## Dependency Changes

### 1. Web Starter Rename

**Change:**

| Old | New |
|-----|-----|
| `spring-boot-starter-web` | `spring-boot-starter-webmvc` |

**Migration:**

```xml
<!-- Before -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>

<!-- After (Option A: Direct) -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-webmvc</artifactId>
</dependency>

<!-- After (Option B: Classic) -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-classic</artifactId>
</dependency>
```

### 2. AOP Starter Rename

**Change:**

| Old | New |
|-----|-----|
| `spring-boot-starter-aop` | `spring-boot-starter-aspectj` |

**IMPORTANT:** Before migrating, **review if you actually need this starter**.

**When you need it:**
- Your application uses AspectJ annotations (typically in `org.aspectj.lang.annotation` package)
- Using `@Retryable` / `@ConcurrencyLimit` annotations
- Using certain Micrometer annotations like `@Timed`
- Spring Modulith event handling (if using aspect-based features)

**When you DON'T need it:**
- Only using Spring AOP features like `@Async`, `@Transactional`, `@Cacheable` (these work without the starter)
- Spring context automatically includes `spring-aop` module

**Migration (if needed):**

```xml
<!-- Before -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-aop</artifactId>
</dependency>

<!-- After -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-aspectj</artifactId>
</dependency>
```

### 3. Flyway Migration

**Change:** Flyway now requires explicit starter

**Migration:**

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-flyway</artifactId>
</dependency>
<dependency>
    <groupId>org.flywaydb</groupId>
    <artifactId>flyway-database-postgresql</artifactId>
</dependency>
```

### 4. Security Test Starter

**Change:**

| Old | New |
|-----|-----|
| `spring-security-test` | `spring-boot-starter-security-test` |

**Migration:**

```xml
<!-- Before -->
<dependency>
    <groupId>org.springframework.security</groupId>
    <artifactId>spring-security-test</artifactId>
    <scope>test</scope>
</dependency>

<!-- After -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-security-test</artifactId>
    <scope>test</scope>
</dependency>
```

### 5. Retry/Resilience Annotations

**Sample usage (from `sivaprasadreddy/spring-boot-4-features`):**
- Package: `org.springframework.resilience.annotation.*`
- Annotations: `@Retryable`, `@ConcurrencyLimit`
- Enablement: `@EnableResilientMethods`
- Parameters used: `includes`, `maxRetries`, `delay`
- Circuit breaker is still external (Resilience4j)

**Decision point (ask the user):** Do you want to keep Spring Retry or move to the native Spring Framework 7 resilience annotations?

- **Native (recommended for Boot 4):**
  - Use `org.springframework.resilience.annotation.*` + `@EnableResilientMethods`
  - Remove `spring-retry` if no longer used
  - Official reference: https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/resilience/annotation/Retryable.html
  - Spring Retry status: maintenance only, superseded by Spring Framework 7: https://github.com/spring-projects/spring-retry
- **Spring Retry (legacy):**
  - Use `org.springframework.retry.annotation.*` + `@EnableRetry`
  - Keep `spring-retry` with an explicit version

**Migration (Spring Retry variant, if used directly):**

```xml
<!-- Add explicit version (check Maven Central for latest) -->
<dependency>
    <groupId>org.springframework.retry</groupId>
    <artifactId>spring-retry</artifactId>
    <version><!-- Specify version explicitly, e.g., 2.0.x --></version>
</dependency>

<!-- AOP support required for @Retryable -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-aspectj</artifactId>
</dependency>
```

**Code changes required:**

```java
// Config (sample repo)
import org.springframework.resilience.annotation.EnableResilientMethods;

@Configuration
@EnableResilientMethods  // Required
public class ResilienceConfig {
}

// Service (sample repo)
import org.springframework.resilience.annotation.Retryable;

@Retryable(
    includes = {SomeException.class},
    maxRetries = 3,
    delay = 1000L
)
public void methodWithRetry() {
    // ...
}
```

**Alternative:** If using Spring Retry directly, use `org.springframework.retry.annotation.*` and `@EnableRetry`.

### 6. Web MVC Test Starter

**New modular test starter:**

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-webmvc-test</artifactId>
    <scope>test</scope>
</dependency>
```

**Note:** Only needed if using modular architecture. Classic test starter includes this.

---

## Code Changes

### 1. Jackson 3 Migration (CRITICAL)

**Breaking Change:** Jackson upgraded from 2.x to 3.x

#### Group ID Changes

```xml
<!-- Old (Jackson 2.x) -->
<dependency>
    <groupId>com.fasterxml.jackson.core</groupId>
    <artifactId>jackson-databind</artifactId>
</dependency>

<!-- New (Jackson 3.x) -->
<dependency>
    <groupId>tools.jackson.core</groupId>
    <artifactId>jackson-databind</artifactId>
</dependency>

<!-- Exception: jackson-annotations stays with old group -->
<dependency>
    <groupId>com.fasterxml.jackson.core</groupId>
    <artifactId>jackson-annotations</artifactId>
</dependency>
```

#### Class Renames

| Old (Jackson 2) | New (Jackson 3) |
|-----------------|-----------------|
| `Jackson2ObjectMapperBuilderCustomizer` | `JsonMapperBuilderCustomizer` |
| `@JsonComponent` | `@JacksonComponent` |
| `JsonObjectSerializer` | `ObjectValueSerializer` |
| `JsonValueDeserializer` | `ObjectValueDeserializer` |

#### Import Changes

```java
// Old
import com.fasterxml.jackson.databind.ObjectMapper;

// New
import tools.jackson.databind.json.JsonMapper;

// Usage
JsonMapper mapper = JsonMapper.builder().build();
```

#### Compatibility Module (For Gradual Migration)

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-jackson2</artifactId>
</dependency>
```

### 2. Package Relocations

#### Bootstrap Registry

```java
// Old
import org.springframework.boot.BootstrapRegistry;
import org.springframework.boot.BootstrapContext;

// New
import org.springframework.boot.bootstrap.BootstrapRegistry;
import org.springframework.boot.bootstrap.BootstrapContext;
```

#### Entity Scan

```java
// Old
import org.springframework.boot.autoconfigure.domain.EntityScan;

// New
import org.springframework.boot.persistence.autoconfigure.EntityScan;
```

---

## Test Changes

### 1. MockBean → MockitoBean

**Change:** Migrate from **deprecated** to **standard** annotations

| Deprecated (still available in 4.0) | Standard (since 3.4) |
|-----|-----|
| `@MockBean` | `@MockitoBean` |
| `@SpyBean` | `@MockitoSpyBean` |

**Timeline:**
- **Spring Boot 3.4** (Spring Framework 6.2): `@MockitoBean` introduced, `@MockBean` deprecated
- **Spring Boot 4.0**: `@MockBean` **still available but deprecated** (will be removed in future version)
- **Future Spring Boot version**: `@MockBean` will be removed completely

**Migration urgency:** While `@MockBean` still works in Spring Boot 4.0, migrate to `@MockitoBean` now to avoid breaking changes in future releases.

**CRITICAL CONSTRAINT:** `@MockitoBean` and `@MockitoSpyBean` can **ONLY** be used on test class fields, **NOT** in `@Configuration` or `@TestConfiguration` classes.

**Migration - Test Class Fields (Standard Case):**

```java
// Before (Using deprecated annotations - still works in 4.0)
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.boot.test.mock.mockito.SpyBean;

@SpringBootTest
class UserServiceTest {
    @MockBean  // Deprecated since 3.4, still available in 4.0
    private UserRepository userRepository;

    @SpyBean  // Deprecated since 3.4, still available in 4.0
    private EmailService emailService;
}

// After (Recommended - using standard annotations)
import org.springframework.boot.test.mock.mockito.MockitoBean;
import org.springframework.boot.test.mock.mockito.MockitoSpyBean;

@SpringBootTest
class UserServiceTest {
    @MockitoBean  // Standard since 3.4, recommended for 4.0+
    private UserRepository userRepository;

    @MockitoSpyBean  // Standard since 3.4, recommended for 4.0+
    private EmailService emailService;
}
```

**Migration - @TestConfiguration Classes (Special Handling Required):**

If you were using `@MockBean` in `@TestConfiguration` classes, you **MUST** move them to test class fields:

```java
// Before (Spring Boot 3.x) - @MockBean in @TestConfiguration
@TestConfiguration
class TestConfig {
    @MockBean
    private UserRepository userRepository;
}

@SpringBootTest
@Import(TestConfig.class)
class UserServiceTest {
    // Test uses mocked repository from config
}

// After (Spring Boot 4.0) - Move to test class field
@SpringBootTest
class UserServiceTest {
    @MockitoBean  // Must be declared on test class field
    private UserRepository userRepository;
}
```

**Alternative for Complex Test Configurations:**

If you need to share mocks across multiple test classes, create a custom annotation:

```java
// Custom annotation combining multiple mocks
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.TYPE)
@MockitoBean(UserRepository.class)
@MockitoBean(OrderRepository.class)
@MockitoSpyBean(EmailService.class)
public @interface CommonTestMocks {
}

// Use in test classes
@SpringBootTest
@CommonTestMocks
class UserServiceTest {
    @Autowired
    private UserRepository userRepository;  // Will be mocked
}
```

**Temporary Workaround (Spring Boot 3.4+ including 4.0):**

If you're not ready to migrate yet, suppress deprecation warnings:

```java
// Works in Spring Boot 3.4+ and 4.0 (deprecated but still available)
// Will be removed in a future Spring Boot version
@SpringBootTest
@SuppressWarnings("removal")
class UserServiceTest {
    @MockBean  // Deprecated since 3.4, still works in 4.0
    private UserRepository userRepository;
}
```

**Important:**
- `@MockBean` **still works** in Spring Boot 4.0, but is deprecated
- It **will be removed** in a future Spring Boot version
- Migrate to `@MockitoBean` soon to avoid future breaking changes
- Per [official Spring Boot 4.0 Migration Guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide): "@MockBean and @SpyBean support will be removed in the future"

### 2. WebMvcTest Package Relocation

```java
// Old
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;

// New
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
```

### 3. Auto-Configuration in @SpringBootTest

**Change:** MockMvc no longer auto-configured in `@SpringBootTest`

```java
// Before (Spring Boot 3)
@SpringBootTest(webEnvironment = WebEnvironment.RANDOM_PORT)
class MyControllerTest {
    @Autowired
    private MockMvc mockMvc; // Auto-configured
}

// After (Spring Boot 4)
@SpringBootTest(webEnvironment = WebEnvironment.RANDOM_PORT)
@AutoConfigureMockMvc  // Now required
class MyControllerTest {
    @Autowired
    private MockMvc mockMvc;
}
```

---

## Configuration Changes

### 1. Jackson Properties

```properties
# Old
spring.jackson.read.allow-trailing-comma=true
spring.jackson.write.indent-output=true

# New
spring.jackson.json.read.allow-trailing-comma=true
spring.jackson.json.write.indent-output=true
```

### 2. Health Probes (New Default Behavior)

**Change:** Liveness/readiness probes **enabled by default** in Spring Boot 4

```properties
# To disable (if not needed):
management.endpoint.health.probes.enabled=false
```

**Endpoints available:**
- `/actuator/health/liveness`
- `/actuator/health/readiness`

### 3. DevTools Live Reload (New Default Behavior)

**Change:** Live reload **disabled by default** in Spring Boot 4

```properties
# To enable:
spring.devtools.livereload.enabled=true
```

---

## Verification

### Build Verification

```bash
# Clean build
./mvnw clean package

# Check for deprecation warnings
./mvnw clean compile | grep -i deprecated
```

### Test Verification

```bash
# Run all tests
./mvnw clean verify

# Run specific test categories
./mvnw test -Dtest=*Test
./mvnw test -Dtest=*IT
```

### Runtime Verification

1. **Application Startup**
   - Check logs for errors
   - Look for deprecation warnings
   - Verify bean creation

2. **Critical Endpoints**
   - Test main API endpoints
   - Verify authentication/authorization
   - Check database connectivity

3. **Health Checks**
   - `GET /actuator/health`
   - `GET /actuator/health/liveness`
   - `GET /actuator/health/readiness`

### Common Issues After Migration

#### Issue 1: NoSuchMethodError or NoClassDefFoundError

**Cause:** Conflicting Jackson versions

**Solution:**
```bash
# Check dependency tree
./mvnw dependency:tree | grep jackson

# Resolve conflicts by excluding old Jackson from transitive dependencies
```

#### Issue 2: Tests Fail with LazyInitializationException

**Cause:** Changes in transaction management

**Solution:** Use `@Transactional` on test methods or fetch associations eagerly

#### Issue 3: @Retryable Not Working

**Cause:** Missing `@EnableResilientMethods` or missing AOP support

**Solution:**
1. Add `spring-boot-starter-aspectj`
2. Add `@EnableResilientMethods` to configuration
3. If using Spring Retry directly, ensure `spring-retry` dependency is present with explicit version

---

## Migration Checklist

### Phase 1: Dependencies
- [ ] Update Spring Boot version to 4.0.x
- [ ] Rename `spring-boot-starter-web` to `-webmvc` (or use classic)
- [ ] Rename `spring-boot-starter-aop` to `-aspectj`
- [ ] Update `spring-security-test` to Spring Boot starter
- [ ] Add Spring Retry with explicit version (if using Spring Retry directly)
- [ ] Add Flyway starter (if using database migrations)
- [ ] Update Testcontainers dependencies (if used)

### Phase 2: Code
- [ ] Update Jackson imports (if using custom ObjectMapper)
- [ ] **Recommended:** Update `@MockBean` to `@MockitoBean` (deprecated but still works)
- [ ] **Recommended:** Update `@SpyBean` to `@MockitoSpyBean` (deprecated but still works)
- [ ] Update `@WebMvcTest` import
- [ ] Add `@AutoConfigureMockMvc` where needed
- [ ] Fix retry/resilience imports and annotations
- [ ] Update package relocations (EntityScan, BootstrapRegistry)

### Phase 3: Configuration
- [ ] Update Jackson properties (if used)
- [ ] Configure health probes (if needed)
- [ ] Configure DevTools live reload (if needed)

### Phase 4: Testing
- [ ] Run all unit tests
- [ ] Run all integration tests
- [ ] Test application startup
- [ ] Verify critical endpoints
- [ ] Check health actuator endpoints
- [ ] Performance testing (if applicable)

---

## References

- [Spring Boot 4.0 Migration Guide (Official)](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide)
- [Spring Boot 4.0 Release Notes](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Release-Notes)
- [Spring Framework 7.0 What's New](https://docs.spring.io/spring-framework/reference/7.0/whatsnew.html)
- [Jackson 3.0 Migration Guide](https://github.com/FasterXML/jackson/wiki/Jackson-Release-3.0)
- [Vlad Mihalcea - Spring Transaction Best Practices](https://vladmihalcea.com/spring-transaction-best-practices/)
