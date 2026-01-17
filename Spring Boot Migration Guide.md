# Spring Boot 4.0 Migration Guide

> **Based on Official Documentation**: [Spring Boot 4.0 Migration Guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide)

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Migration Strategy](#migration-strategy)
3. [Spring Boot 4.0 Changes](#spring-boot-40-changes)
   - [Dependency Changes](#dependency-changes)
   - [Code Changes](#code-changes)
   - [Configuration Changes](#configuration-changes)
   - [Test Changes](#test-changes)
4. [Spring Modulith 2.0 Migration](#spring-modulith-20-migration)
5. [Testcontainers 2.x Migration](#testcontainers-2x-migration)
6. [Current Project Analysis](#current-project-analysis)
7. [Action Items](#action-items)

---

## System Requirements

### ✅ Required Versions

| Component | Minimum | Recommended | Current Project |
|-----------|---------|-------------|-----------------|
| **Java** | 17 | 21+ | ✅ 25 |
| **Spring Boot** | 4.0.0 | 4.0.0 | ✅ 4.0.0 |
| **Spring Modulith** | 2.0.0 | 2.0.0 | ✅ 2.0.0 |
| **Jakarta EE** | 11 | 11 | Auto-managed |
| **Servlet** | 6.1 | 6.1 | Auto-managed |

**Java Version Note**:
- Minimum: Java 17
- Recommended: Java 21 (LTS)
- Current: Java 25 (latest features, suitable for new projects)

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

**Current Project Status**: ❌ Not using classic starters (direct migration approach)

**Recommendation**: Consider using classic starters for safer migration, then gradually migrate to modular starters.

---

## Spring Boot 4.0 Changes

### Dependency Changes

#### 1. Web Starter Rename

**Official Change**:
| Old | New |
|-----|-----|
| `spring-boot-starter-web` | `spring-boot-starter-webmvc` |

**Current Project**: ⚠️ Still using `spring-boot-starter-web` (pom.xml:40)

**Action Required**:
```xml
<!-- Change this -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>

<!-- To this -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-webmvc</artifactId>
</dependency>

<!-- OR use classic starter for gradual migration -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-classic</artifactId>
</dependency>
```

#### 2. AOP Starter Rename

**Official Change**:
| Old | New |
|-----|-----|
| `spring-boot-starter-aop` | `spring-boot-starter-aspectj` |

**Current Project**: ❌ Removed completely

**Action Required**:
- If AOP is needed (for @Async, @Transactional, @Cacheable, @Retryable), add: `spring-boot-starter-aspectj`
- Spring Retry requires AOP support

#### 3. Flyway Migration

**Official Change**: Flyway and Liquibase now require explicit starters

**Current Project**: ✅ Correctly using `spring-boot-starter-flyway` (pom.xml:61)

**Correct Implementation**:
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

#### 4. Security Test Starter

**Official Change**:
| Old | New |
|-----|-----|
| `spring-security-test` | `spring-boot-starter-security-test` |

**Current Project**: ⚠️ Still using `spring-security-test` (pom.xml:133)

**Action Required**:
```xml
<!-- Change this -->
<dependency>
    <groupId>org.springframework.security</groupId>
    <artifactId>spring-security-test</artifactId>
    <scope>test</scope>
</dependency>

<!-- To this -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-security-test</artifactId>
    <scope>test</scope>
</dependency>
```

#### 5. Web MVC Test Starter

**Official Change**: New modular test starter for web MVC testing

**Current Project**: ✅ Added `spring-boot-starter-webmvc-test` (pom.xml:118)

**Note**: This is correct for modular architecture, but may not be necessary if using classic test starters.

### Code Changes

#### 1. Jackson 3 Migration (CRITICAL)

**Official Change**: Jackson upgraded from 2.x to 3.x with breaking changes

##### Group ID Changes
```xml
<!-- Old -->
<dependency>
    <groupId>com.fasterxml.jackson.core</groupId>
    <artifactId>jackson-databind</artifactId>
</dependency>

<!-- New -->
<dependency>
    <groupId>tools.jackson.core</groupId>
    <artifactId>jackson-databind</artifactId>
</dependency>

<!-- Exception: jackson-annotations stays with com.fasterxml.jackson.core -->
```

##### Class Renames
| Old | New |
|-----|-----|
| `Jackson2ObjectMapperBuilderCustomizer` | `JsonMapperBuilderCustomizer` |
| `@JsonComponent` | `@JacksonComponent` |
| `JsonObjectSerializer` | `ObjectValueSerializer` |
| `JsonValueDeserializer` | `ObjectValueDeserializer` |

**Current Project**:
- ✅ Using `JsonMapper` from `tools.jackson.databind.json` (AuthControllerTest.java:35)
- ✅ Import package: `tools.jackson.databind.json.JsonMapper`

**Analysis**: Correctly migrated to Jackson 3

##### Compatibility Module (For Gradual Migration)
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-jackson2</artifactId>
</dependency>
```

#### 2. Package Relocations

##### Bootstrap Registry
```java
// Old
import org.springframework.boot.BootstrapRegistry;
import org.springframework.boot.BootstrapContext;

// New
import org.springframework.boot.bootstrap.BootstrapRegistry;
import org.springframework.boot.bootstrap.BootstrapContext;
```

##### Entity Scan
```java
// Old
import org.springframework.boot.autoconfigure.domain.EntityScan;

// New
import org.springframework.boot.persistence.autoconfigure.EntityScan;
```

**Current Project**: ⚠️ Not verified (check if used)

#### 3. Spring Retry (No Longer Auto-Managed)

**Official Documentation**:
- Spring Retry is **no longer dependency-managed** by Spring Boot
- If using Spring Retry, must explicitly specify version:

**Current Project**: ❌ Using `org.springframework.resilience.annotation.Retryable` (S3FileService.java:7)

**Analysis**:
- There is **NO** `org.springframework.resilience` package in Spring Boot 4 or Spring Framework 7
- This appears to be an incorrect assumption or placeholder
- Spring Retry is still the correct library, just no longer auto-managed

**Action Required**:

**Add to pom.xml**:
```xml
<!-- Spring Retry dependency (no longer managed by Spring Boot) -->
<dependency>
    <groupId>org.springframework.retry</groupId>
    <artifactId>spring-retry</artifactId>
    <version>2.0.5</version>
</dependency>

<!-- AOP support required for @Retryable -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-aspectj</artifactId>
</dependency>
```

**S3FileService.java**:
```java
// Remove this (incorrect):
import org.springframework.resilience.annotation.Retryable;

// Add this:
import org.springframework.retry.annotation.Retryable;
import org.springframework.retry.annotation.Backoff;

// Update annotation syntax:
@Retryable(
    retryFor = {S3Exception.class},
    maxAttempts = 3,
    backoff = @Backoff(delay = 1000, multiplier = 2.0)
)
public String uploadFile(String key, MultipartFile file) {
    // ...
}
```

**S3Config.java**:
```java
import org.springframework.context.annotation.Configuration;
import org.springframework.retry.annotation.EnableRetry;

@Configuration
@EnableRetry  // Restore this annotation
public class S3Config {
    // ...
}
```

#### 4. Test Annotations Migration

##### MockBean → MockitoBean
```java
// Old
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.boot.test.mock.mockito.SpyBean;

@MockBean
private UserRepository userRepository;

@SpyBean
private EmailService emailService;

// New
import org.springframework.boot.test.mock.mockito.MockitoBean;
import org.springframework.boot.test.mock.mockito.MockitoSpyBean;

@MockitoBean
private UserRepository userRepository;

@MockitoSpyBean
private EmailService emailService;
```

**Current Project**: ❌ Not migrated (still using old annotations)

**Action Required**: Update all test files using `@MockBean` and `@SpyBean`

**Affected Files**:
- `AssignmentSubmissionServiceTest.java`
- `AssignmentSubmissionControllerTest.java`
- Other test files using mocking

##### WebMvcTest Package Relocation
```java
// Old
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;

// New
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
```

**Current Project**: ✅ Already migrated (AssignmentSubmissionControllerTest.java, etc.)

##### Auto-Configuration in @SpringBootTest
```java
// Old (Spring Boot 3 - auto-provided)
@SpringBootTest(webEnvironment = WebEnvironment.RANDOM_PORT)
class MyControllerTest {
    @Autowired
    private MockMvc mockMvc; // Auto-configured
}

// New (Spring Boot 4 - requires explicit annotation)
@SpringBootTest(webEnvironment = WebEnvironment.RANDOM_PORT)
@AutoConfigureMockMvc  // Now required
class MyControllerTest {
    @Autowired
    private MockMvc mockMvc;
}
```

**Current Project**: ⚠️ Check integration tests

### Configuration Changes

#### 1. Jackson Properties
```properties
# Old
spring.jackson.read.allow-trailing-comma=true
spring.jackson.write.indent-output=true

# New
spring.jackson.json.read.allow-trailing-comma=true
spring.jackson.json.write.indent-output=true
```

**Current Project**: ⚠️ Not verified (check application.properties)

#### 2. Health Probes (New Default Behavior)
```properties
# Spring Boot 4 enables liveness/readiness probes by default
# To disable (if not needed):
management.endpoint.health.probes.enabled=false
```

**Current Project**: ⚠️ Not configured (using defaults - probes enabled)

#### 3. DevTools Live Reload (New Default Behavior)
```properties
# Spring Boot 4 disables live reload by default
# To enable:
spring.devtools.livereload.enabled=true
```

**Current Project**: ⚠️ Not configured (using defaults - live reload disabled)

### Test Changes

#### Maven Surefire Plugin Configuration

**Current Project**: ✅ Added enhanced test reporting with tree reporter (pom.xml:171-198)

**Analysis**: This is a **project improvement**, not a Spring Boot 4 requirement.

**Benefits**:
- Better test output formatting
- Enhanced error diagnostics
- Unicode tree-style reporting

**Recommendation**: Keep this configuration (it's a good practice)

---

## Spring Modulith 2.0 Migration

> **Note**: This is a **separate migration** from Spring Boot 4.0. Spring Modulith 2.0 has its own breaking changes.

### Version Update

**Current Project**: ✅ Updated to 2.0.0 (pom.xml:31)

```xml
<properties>
    <spring-modulith.version>2.0.0</spring-modulith.version>
</properties>
```

### Required Changes for Spring Modulith 2.0

#### 1. Event Store Schema Migration

**Requirement**: Spring Modulith 2.0 requires a dedicated schema for event storage when using JDBC event store.

**Current Project**: ✅ Created `V0__create_events_schema.sql` (src/main/resources/db/migration/__root/)

```sql
CREATE SCHEMA events;
```

**Why This is Required**:
- Spring Modulith 2.0 separates event storage into its own schema
- Prevents conflicts with application data
- Allows for independent event store management

**Important**: This migration must run **before** any module-specific migrations (hence V0 prefix).

#### 2. Flyway Integration Configuration

**Requirement**: Spring Modulith 2.0 requires explicit Flyway integration enablement.

**Current Project**: ✅ Added to application.properties (line 38)

```properties
spring.modulith.runtime.flyway-enabled=true
```

**Why This is Required**:
- Enables Spring Modulith's integration with Flyway for schema management
- Ensures event store schema is properly initialized
- Coordinates migration execution with Spring Modulith lifecycle

#### 3. Event Store Configuration

**Current Project Configuration** (application.properties):
```properties
#### Events Config ######
spring.modulith.events.jdbc.schema=events
spring.modulith.events.jdbc.schema-initialization.enabled=true
spring.modulith.events.republish-outstanding-events-on-restart=true
spring.modulith.runtime.flyway-enabled=true
```

**Configuration Breakdown**:
- `spring.modulith.events.jdbc.schema=events`: Uses the dedicated events schema
- `spring.modulith.events.jdbc.schema-initialization.enabled=true`: Enables automatic schema initialization
- `spring.modulith.events.republish-outstanding-events-on-restart=true`: Ensures event consistency across restarts
- `spring.modulith.runtime.flyway-enabled=true`: Integrates with Flyway

### Spring Modulith 2.0 Breaking Changes

#### Event Publishing API Changes
- Review any custom event publication code
- Update to new event publication mechanisms if using advanced features

#### Event Store Schema
- **Must** create events schema before application startup
- Event tables will be created in the events schema, not the default schema

### Spring Modulith Dependencies

**Current Project** (pom.xml):
```xml
<dependency>
    <groupId>org.springframework.modulith</groupId>
    <artifactId>spring-modulith-events-amqp</artifactId>
    <scope>runtime</scope>
</dependency>
<dependency>
    <groupId>org.springframework.modulith</groupId>
    <artifactId>spring-modulith-starter-jdbc</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.modulith</groupId>
    <artifactId>spring-modulith-starter-core</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.modulith</groupId>
    <artifactId>spring-modulith-starter-test</artifactId>
    <scope>test</scope>
</dependency>
```

**Analysis**: ✅ Correct dependencies for Spring Modulith 2.0

### Spring Modulith Migration Checklist

- [x] Update spring-modulith.version to 2.0.0
- [x] Create events schema migration (V0__create_events_schema.sql)
- [x] Add spring.modulith.runtime.flyway-enabled=true
- [x] Configure events schema in application.properties
- [x] Enable schema initialization
- [x] Configure event republishing on restart
- [ ] Test event publication and consumption
- [ ] Verify event store tables are created in events schema
- [ ] Review custom event handling code for API changes

### Reference
- [Spring Modulith 2.0 Reference Documentation](https://docs.spring.io/spring-modulith/reference/)

---

## Testcontainers 2.x Migration

> **Note**: This is a **separate migration** from Spring Boot 4.0. Testcontainers 2.0 introduced breaking changes to package structure and API.

### Package Structure Changes

#### Artifact Name Changes

**Current Project**: ✅ Updated to Testcontainers 2.x naming (pom.xml:137-149)

| Old (1.x) | New (2.x) | Current Project |
|-----------|-----------|-----------------|
| `org.testcontainers:junit-jupiter` | `org.testcontainers:testcontainers-junit-jupiter` | ✅ Updated |
| `org.testcontainers:postgresql` | `org.testcontainers:testcontainers-postgresql` | ✅ Updated |
| `org.testcontainers:localstack` | `org.testcontainers:testcontainers-localstack` | ✅ Updated |

```xml
<dependency>
    <groupId>org.testcontainers</groupId>
    <artifactId>testcontainers-junit-jupiter</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.testcontainers</groupId>
    <artifactId>testcontainers-postgresql</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.testcontainers</groupId>
    <artifactId>testcontainers-localstack</artifactId>
    <scope>test</scope>
</dependency>
```

### Import Changes

**Current Project**: ✅ Updated imports (TestcontainersConfiguration.java)

#### PostgreSQL Container
```java
// Old (1.x)
import org.testcontainers.containers.PostgreSQLContainer;

PostgreSQLContainer<?> postgresContainer() {
    return new PostgreSQLContainer<>(DockerImageName.parse("postgres:latest"));
}

// New (2.x)
import org.testcontainers.postgresql.PostgreSQLContainer;

PostgreSQLContainer postgresContainer() {
    return new PostgreSQLContainer(DockerImageName.parse("postgres:latest"));
}
```

**Changes**:
- Package: `org.testcontainers.containers` → `org.testcontainers.postgresql`
- Generic type: `PostgreSQLContainer<?>` → `PostgreSQLContainer` (raw type)

#### LocalStack Container
```java
// Old (1.x)
import org.testcontainers.containers.localstack.LocalStackContainer;
import static org.testcontainers.containers.localstack.LocalStackContainer.Service.S3;

LocalStackContainer localStackContainer() {
    return new LocalStackContainer(DockerImageName.parse("localstack/localstack:3.0"))
            .withServices(S3);
}

// New (2.x)
import org.testcontainers.localstack.LocalStackContainer;

LocalStackContainer localStackContainer() {
    return new LocalStackContainer(DockerImageName.parse("localstack/localstack:latest"));
}
```

**Changes**:
- Package: `org.testcontainers.containers.localstack` → `org.testcontainers.localstack`
- `.withServices(S3)` is **no longer required** (services auto-detected)
- Removed `LocalStackContainer.Service.S3` import

### API Changes

#### Endpoint Configuration
```java
// Old (1.x)
import static org.testcontainers.containers.localstack.LocalStackContainer.Service.S3;

S3Client s3Client(LocalStackContainer localStackContainer) {
    return S3Client.builder()
            .endpointOverride(localStackContainer.getEndpointOverride(S3))
            .credentialsProvider(...)
            .build();
}

// New (2.x)
S3Client s3Client(LocalStackContainer localStackContainer) {
    return S3Client.builder()
            .endpointOverride(localStackContainer.getEndpoint())
            .credentialsProvider(...)
            .build();
}
```

**Changes**:
- `getEndpointOverride(Service)` → `getEndpoint()`
- No service parameter needed

### LocalStack Image Version

**Current Project**: ✅ Updated to `latest` (TestcontainersConfiguration.java)

```java
// Old
DockerImageName.parse("localstack/localstack:3.0")

// New
DockerImageName.parse("localstack/localstack:latest")
```

**Why**: LocalStack versioning changed; `latest` is recommended for Testcontainers 2.x

### Current Project Implementation

**TestcontainersConfiguration.java**:
```java
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.context.annotation.Bean;
import org.testcontainers.localstack.LocalStackContainer;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.DockerImageName;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;

@TestConfiguration(proxyBeanMethods = false)
public class TestcontainersConfiguration {

    @Bean
    @ServiceConnection
    PostgreSQLContainer postgresContainer() {
        return new PostgreSQLContainer(DockerImageName.parse("postgres:latest"));
    }

    @Bean(initMethod = "start", destroyMethod = "stop")
    public LocalStackContainer localStackContainer() {
        return new LocalStackContainer(DockerImageName.parse("localstack/localstack:latest"));
    }

    @Bean
    public S3Client s3Client(LocalStackContainer localStackContainer) {
        S3Client s3Client = S3Client.builder()
                .endpointOverride(localStackContainer.getEndpoint())
                .credentialsProvider(
                        StaticCredentialsProvider.create(
                                AwsBasicCredentials.create(
                                        localStackContainer.getAccessKey(),
                                        localStackContainer.getSecretKey()
                                )
                        )
                )
                .region(Region.of(localStackContainer.getRegion()))
                .build();

        return s3Client;
    }
}
```

**Analysis**: ✅ Fully migrated to Testcontainers 2.x API

### Testcontainers 2.x Migration Checklist

- [x] Update artifact names with `testcontainers-` prefix
- [x] Update PostgreSQL imports to `org.testcontainers.postgresql`
- [x] Update LocalStack imports to `org.testcontainers.localstack`
- [x] Remove generic type from PostgreSQLContainer
- [x] Remove `.withServices()` from LocalStack configuration
- [x] Update `getEndpointOverride(Service)` to `getEndpoint()`
- [x] Update LocalStack image to `latest`
- [ ] Test all container-based tests
- [ ] Verify S3 integration tests work with new LocalStack
- [ ] Verify PostgreSQL integration tests work

### Reference
- [Testcontainers 2.0 Migration Guide](https://java.testcontainers.org/migrations/testcontainers-2/)

---

## Current Project Analysis

### ✅ Correct Changes Made

#### Spring Boot 4.0
1. **Spring Boot Version**: Updated to 4.0.0
2. **Flyway Starter**: Changed to `spring-boot-starter-flyway`
3. **WebMvcTest Package**: Relocated correctly
4. **Jackson**: Using `JsonMapper` from `tools.jackson` package
5. **Maven Surefire**: Enhanced test reporting

#### Spring Modulith 2.0
1. **Version**: Updated to 2.0.0
2. **Events Schema**: Created `V0__create_events_schema.sql`
3. **Flyway Integration**: Added `spring.modulith.runtime.flyway-enabled=true`
4. **Event Store Config**: Properly configured events schema

#### Testcontainers 2.x
1. **Artifact Names**: Updated with `testcontainers-` prefix
2. **PostgreSQL**: Updated imports and API
3. **LocalStack**: Updated imports and API
4. **Endpoint Configuration**: Using new `getEndpoint()` method
5. **Image Version**: Updated to `latest`

### ⚠️ Incomplete/Incorrect Changes

#### Spring Boot 4.0
1. **Web Starter**: Still using `spring-boot-starter-web` (should change to `-webmvc` or use classic)
2. **Security Test**: Still using `spring-security-test` (should use Spring Boot starter)
3. **Retry Mechanism**: Using non-existent `org.springframework.resilience` (should use Spring Retry)
4. **MockBean/SpyBean**: Not migrated to `@MockitoBean`/`@MockitoSpyBean`
5. **AOP Starter**: Removed instead of renamed (needed for @Retryable)

### ❓ Changes Needing Verification

1. **Exception Handling**: Changed `SecurityException` to `AuthenticationException` (not in official docs)
2. **Test Status Codes**: Changed expected status from 401 to 500 (may be incorrect)
3. **Integration Tests**: Need to verify `@AutoConfigureMockMvc` is added where needed

---

## Action Items

### 🔴 Critical (Must Fix)

#### 1. Fix Retry Implementation
**Files**: S3FileService.java, S3Config.java, pom.xml

**Actions**:
- Remove `org.springframework.resilience` imports
- Add Spring Retry dependency (version 2.0.5)
- Add `spring-boot-starter-aspectj` dependency
- Restore `@EnableRetry` in S3Config
- Fix `@Retryable` annotation syntax

**Code Changes**:
```xml
<!-- pom.xml: Add these dependencies -->
<dependency>
    <groupId>org.springframework.retry</groupId>
    <artifactId>spring-retry</artifactId>
    <version>2.0.5</version>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-aspectj</artifactId>
</dependency>
```

```java
// S3FileService.java
import org.springframework.retry.annotation.Retryable;
import org.springframework.retry.annotation.Backoff;

@Retryable(
    retryFor = {S3Exception.class},
    maxAttempts = 3,
    backoff = @Backoff(delay = 1000, multiplier = 2.0)
)
public String uploadFile(String key, MultipartFile file) { ... }
```

```java
// S3Config.java
import org.springframework.retry.annotation.EnableRetry;

@Configuration
@EnableRetry
public class S3Config { ... }
```

#### 2. Update Web Starter
**File**: pom.xml:40

**Options**:
- **Option A** (Direct): Change to `spring-boot-starter-webmvc`
- **Option B** (Gradual): Use `spring-boot-starter-classic`

#### 3. Update Security Test Starter
**File**: pom.xml:133

**Action**:
```xml
<!-- Change from -->
<dependency>
    <groupId>org.springframework.security</groupId>
    <artifactId>spring-security-test</artifactId>
    <scope>test</scope>
</dependency>

<!-- To -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-security-test</artifactId>
    <scope>test</scope>
</dependency>
```

### 🟡 Important (Should Fix)

#### 4. Migrate Test Annotations
**Files**: All test classes using `@MockBean` and `@SpyBean`

**Actions**:
- Update all `@MockBean` to `@MockitoBean`
- Update all `@SpyBean` to `@MockitoSpyBean`
- Add `@AutoConfigureMockMvc` to `@SpringBootTest` classes that inject MockMvc

**Affected Files**:
- `AssignmentSubmissionServiceTest.java`
- `AssignmentSubmissionControllerTest.java`
- Other test files

#### 5. Verify Integration Tests
**Files**: All integration test files

**Actions**:
- Check if `@SpringBootTest` tests inject `MockMvc`
- Add `@AutoConfigureMockMvc` if needed
- Verify tests pass after changes

### 🟢 Optional (Nice to Have)

#### 6. Consider Classic Starters
- For safer gradual migration
- Easier rollback if issues arise
- Can migrate to modular starters incrementally

#### 7. Add Configuration Properties
- Health probes configuration (if customization needed)
- DevTools live reload (if needed in development)

---

## Migration Checklist

### Phase 1: Spring Boot 4.0 Dependencies
- [ ] Update `spring-boot-starter-web` to `-webmvc` or use classic starter
- [ ] Update `spring-security-test` to Spring Boot starter
- [ ] Add Spring Retry dependency with explicit version (2.0.5)
- [ ] Add `spring-boot-starter-aspectj` for AOP support

### Phase 2: Spring Boot 4.0 Code
- [ ] Fix retry imports and annotations in S3FileService
- [ ] Restore `@EnableRetry` in S3Config
- [ ] Update all `@MockBean` to `@MockitoBean`
- [ ] Update all `@SpyBean` to `@MockitoSpyBean`
- [ ] Add `@AutoConfigureMockMvc` to integration tests
- [ ] Verify package relocations (EntityScan, BootstrapRegistry)
- [ ] Update Jackson configuration if using custom ObjectMapper

### Phase 3: Spring Boot 4.0 Configuration
- [ ] Update Jackson properties (if used)
- [ ] Configure health probes (if needed)
- [ ] Configure DevTools live reload (if needed)

### Phase 4: Spring Modulith 2.0 (Already Complete)
- [x] Update spring-modulith.version to 2.0.0
- [x] Create events schema migration
- [x] Add spring.modulith.runtime.flyway-enabled=true
- [x] Configure events schema in application.properties
- [ ] Test event publication and consumption

### Phase 5: Testcontainers 2.x (Already Complete)
- [x] Update artifact names with `testcontainers-` prefix
- [x] Update PostgreSQL imports and API
- [x] Update LocalStack imports and API
- [x] Update endpoint configuration
- [ ] Test all container-based tests

### Phase 6: Testing
- [ ] Run all unit tests
- [ ] Run all integration tests
- [ ] Verify retry logic works correctly
- [ ] Test file uploads (S3 integration)
- [ ] Test authentication/authorization
- [ ] Verify Testcontainers functionality
- [ ] Verify Spring Modulith event handling

### Phase 7: Verification
- [ ] Build project: `./mvnw clean package`
- [ ] Check for deprecation warnings
- [ ] Review application startup logs
- [ ] Test all critical endpoints
- [ ] Performance testing
- [ ] Verify event store tables in events schema

---

## References

### Spring Boot 4.0
- [Spring Boot 4.0 Migration Guide (Official)](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide)
- [Spring Boot 4.0 Release Notes](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Release-Notes)
- [Spring Framework 7.0 What's New](https://docs.spring.io/spring-framework/reference/7.0/whatsnew.html)
- [Jackson 3.0 Migration Guide](https://github.com/FasterXML/jackson/wiki/Jackson-Release-3.0)

### Spring Modulith 2.0
- [Spring Modulith 2.0 Reference Documentation](https://docs.spring.io/spring-modulith/reference/)
- [Spring Modulith Release Notes](https://github.com/spring-projects/spring-modulith/releases)

### Testcontainers 2.x
- [Testcontainers 2.0 Migration Guide](https://java.testcontainers.org/migrations/testcontainers-2/)
- [Testcontainers Documentation](https://java.testcontainers.org/)

---

## Summary

This project is undergoing **three concurrent migrations**:

### 1. Spring Boot 4.0 Migration
**Status**: Partially complete
**Critical Issues**:
- Retry mechanism is broken (using non-existent `org.springframework.resilience`)
- Web and security test starters need updating
- Test annotations need migration

### 2. Spring Modulith 2.0 Migration
**Status**: ✅ Complete
**Completed**:
- Events schema created
- Flyway integration configured
- Event store properly configured

### 3. Testcontainers 2.x Migration
**Status**: ✅ Complete
**Completed**:
- Artifact names updated
- Imports and API migrated
- LocalStack and PostgreSQL containers updated

**Recommended Next Steps**:
1. Fix critical Spring Boot 4.0 issues (retry, starters)
2. Migrate test annotations (`@MockBean` → `@MockitoBean`)
3. Run full test suite to verify all migrations
4. Consider using classic starters for safer migration path
