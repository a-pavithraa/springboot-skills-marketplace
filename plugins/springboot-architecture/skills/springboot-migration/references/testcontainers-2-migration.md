# Testcontainers 2.x Migration Guide

> **Official Documentation**: [Testcontainers 2.0 Migration Guide](https://java.testcontainers.org/migrations/testcontainers-2/)

## Table of Contents

1. [Overview](#overview)
2. [Artifact Name Changes](#artifact-name-changes)
3. [Package Structure Changes](#package-structure-changes)
4. [API Changes](#api-changes)
5. [Migration Examples](#migration-examples)
6. [Verification](#verification)

---

## Overview

**IMPORTANT:** Testcontainers 2.x migration is **separate** from Spring Boot 4.0 migration, though they can be done concurrently.

**Key changes:**
- Artifact names now use `testcontainers-` prefix
- Package structure reorganized (module-specific packages)
- API simplifications (removed unnecessary generics, service parameters)
- Image version updates

---

## Artifact Name Changes

### Before (Testcontainers 1.x)

```xml
<dependency>
    <groupId>org.testcontainers</groupId>
    <artifactId>junit-jupiter</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.testcontainers</groupId>
    <artifactId>postgresql</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.testcontainers</groupId>
    <artifactId>localstack</artifactId>
    <scope>test</scope>
</dependency>
```

### After (Testcontainers 2.x)

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

### Mapping Table

| Old (1.x) | New (2.x) |
|-----------|-----------|
| `junit-jupiter` | `testcontainers-junit-jupiter` |
| `postgresql` | `testcontainers-postgresql` |
| `mysql` | `testcontainers-mysql` |
| `mongodb` | `testcontainers-mongodb` |
| `localstack` | `testcontainers-localstack` |
| `kafka` | `testcontainers-kafka` |
| `rabbitmq` | `testcontainers-rabbitmq` |
| `elasticsearch` | `testcontainers-elasticsearch` |
| `redis` | `testcontainers-redis` |

**Pattern:** Add `testcontainers-` prefix to all module artifacts

---

## Package Structure Changes

### PostgreSQL Container

#### Before (1.x)

```java
import org.testcontainers.containers.PostgreSQLContainer;

PostgreSQLContainer<?> postgresContainer() {
    return new PostgreSQLContainer<>(DockerImageName.parse("postgres:latest"));
}
```

#### After (2.x)

```java
import org.testcontainers.postgresql.PostgreSQLContainer;

PostgreSQLContainer postgresContainer() {
    return new PostgreSQLContainer(DockerImageName.parse("postgres:latest"));
}
```

**Changes:**
- Package: `org.testcontainers.containers` → `org.testcontainers.postgresql`
- Generic type: `PostgreSQLContainer<?>` → `PostgreSQLContainer` (raw type)

### MySQL Container

#### Before (1.x)

```java
import org.testcontainers.containers.MySQLContainer;

MySQLContainer<?> mysqlContainer() {
    return new MySQLContainer<>(DockerImageName.parse("mysql:8.0"));
}
```

#### After (2.x)

```java
import org.testcontainers.mysql.MySQLContainer;

MySQLContainer mysqlContainer() {
    return new MySQLContainer(DockerImageName.parse("mysql:8.0"));
}
```

**Changes:**
- Package: `org.testcontainers.containers` → `org.testcontainers.mysql`
- Generic type removed

### LocalStack Container

#### Before (1.x)

```java
import org.testcontainers.containers.localstack.LocalStackContainer;
import static org.testcontainers.containers.localstack.LocalStackContainer.Service.S3;
import static org.testcontainers.containers.localstack.LocalStackContainer.Service.SQS;

LocalStackContainer localStackContainer() {
    return new LocalStackContainer(DockerImageName.parse("localstack/localstack:3.0"))
            .withServices(S3, SQS);
}
```

#### After (2.x)

```java
import org.testcontainers.localstack.LocalStackContainer;

LocalStackContainer localStackContainer() {
    return new LocalStackContainer(DockerImageName.parse("localstack/localstack:latest"));
}
```

**Changes:**
- Package: `org.testcontainers.containers.localstack` → `org.testcontainers.localstack`
- `.withServices()` **removed** (services auto-detected)
- `LocalStackContainer.Service` **removed**
- Image version: `3.0` → `latest`

### Other Common Containers

| Container | Old Package | New Package |
|-----------|-------------|-------------|
| MongoDB | `org.testcontainers.containers` | `org.testcontainers.mongodb` |
| Kafka | `org.testcontainers.containers` | `org.testcontainers.kafka` |
| RabbitMQ | `org.testcontainers.containers` | `org.testcontainers.rabbitmq` |
| Elasticsearch | `org.testcontainers.elasticsearch` | `org.testcontainers.elasticsearch` (no change) |
| Redis | `org.testcontainers.containers` | `org.testcontainers.redis` |

**Pattern:** Module-specific packages under `org.testcontainers.<module>`

---

## API Changes

### 1. LocalStack Service Configuration

#### Before (1.x)

```java
import static org.testcontainers.containers.localstack.LocalStackContainer.Service.S3;

S3Client s3Client(LocalStackContainer localStackContainer) {
    return S3Client.builder()
            .endpointOverride(localStackContainer.getEndpointOverride(S3))
            .credentialsProvider(...)
            .build();
}
```

#### After (2.x)

```java
S3Client s3Client(LocalStackContainer localStackContainer) {
    return S3Client.builder()
            .endpointOverride(localStackContainer.getEndpoint())
            .credentialsProvider(...)
            .build();
}
```

**Changes:**
- `getEndpointOverride(Service)` → `getEndpoint()`
- No service parameter needed
- Services auto-detected by LocalStack

### 2. Generic Type Removal

**Before:**
```java
PostgreSQLContainer<?> container = new PostgreSQLContainer<>("postgres:16");
```

**After:**
```java
PostgreSQLContainer container = new PostgreSQLContainer("postgres:16");
```

**Why:** Simplified API, generic types were unnecessary complexity

### 3. Image Version Updates

**LocalStack:**
```java
// Before
DockerImageName.parse("localstack/localstack:3.0")

// After
DockerImageName.parse("localstack/localstack:latest")
```

**PostgreSQL:**
```java
// Before
DockerImageName.parse("postgres:15-alpine")

// After
DockerImageName.parse("postgres:16-alpine")  // or latest
```

---

## Migration Examples

### Complete PostgreSQL Migration

#### Before (1.x)

```java
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.context.annotation.Bean;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.utility.DockerImageName;

@TestConfiguration(proxyBeanMethods = false)
public class TestcontainersConfiguration {

    @Bean
    @ServiceConnection
    PostgreSQLContainer<?> postgresContainer() {
        return new PostgreSQLContainer<>(DockerImageName.parse("postgres:15-alpine"));
    }
}
```

#### After (2.x)

```java
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.context.annotation.Bean;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.DockerImageName;

@TestConfiguration(proxyBeanMethods = false)
public class TestcontainersConfiguration {

    @Bean
    @ServiceConnection
    PostgreSQLContainer postgresContainer() {
        return new PostgreSQLContainer(DockerImageName.parse("postgres:16-alpine"));
    }
}
```

### Complete LocalStack Migration

#### Before (1.x)

```java
import org.testcontainers.containers.localstack.LocalStackContainer;
import static org.testcontainers.containers.localstack.LocalStackContainer.Service.S3;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.regions.Region;

@TestConfiguration
public class LocalStackConfig {

    @Bean(initMethod = "start", destroyMethod = "stop")
    public LocalStackContainer localStackContainer() {
        return new LocalStackContainer(DockerImageName.parse("localstack/localstack:3.0"))
                .withServices(S3);
    }

    @Bean
    public S3Client s3Client(LocalStackContainer localStackContainer) {
        return S3Client.builder()
                .endpointOverride(localStackContainer.getEndpointOverride(S3))
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
    }
}
```

#### After (2.x)

```java
import org.testcontainers.localstack.LocalStackContainer;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.regions.Region;

@TestConfiguration
public class LocalStackConfig {

    @Bean(initMethod = "start", destroyMethod = "stop")
    public LocalStackContainer localStackContainer() {
        return new LocalStackContainer(DockerImageName.parse("localstack/localstack:latest"));
    }

    @Bean
    public S3Client s3Client(LocalStackContainer localStackContainer) {
        return S3Client.builder()
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
    }
}
```

### Multi-Container Test Configuration

#### Before (1.x)

```java
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.containers.localstack.LocalStackContainer;
import org.testcontainers.containers.RabbitMQContainer;

@TestConfiguration
public class TestcontainersConfig {

    @Bean
    PostgreSQLContainer<?> postgres() {
        return new PostgreSQLContainer<>("postgres:15");
    }

    @Bean
    RabbitMQContainer<?> rabbitmq() {
        return new RabbitMQContainer<>("rabbitmq:3.12-alpine");
    }

    @Bean
    LocalStackContainer localstack() {
        return new LocalStackContainer(DockerImageName.parse("localstack/localstack:3.0"))
                .withServices(S3, SQS);
    }
}
```

#### After (2.x)

```java
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.localstack.LocalStackContainer;
import org.testcontainers.rabbitmq.RabbitMQContainer;

@TestConfiguration
public class TestcontainersConfig {

    @Bean
    PostgreSQLContainer postgres() {
        return new PostgreSQLContainer("postgres:16");
    }

    @Bean
    RabbitMQContainer rabbitmq() {
        return new RabbitMQContainer("rabbitmq:3.13-alpine");
    }

    @Bean
    LocalStackContainer localstack() {
        return new LocalStackContainer(DockerImageName.parse("localstack/localstack:latest"));
    }
}
```

---

## Verification

### 1. Dependency Verification

```bash
# Check Testcontainers version
./mvnw dependency:tree | grep testcontainers

# Expected: org.testcontainers:testcontainers-<module>:2.x
```

### 2. Import Verification

**Run tests and check for compilation errors:**

```bash
./mvnw clean test-compile
```

**Common errors:**
```
error: package org.testcontainers.containers does not exist
error: cannot find symbol PostgreSQLContainer<?>
```

**Solution:** Update imports and remove generics

### 3. Runtime Verification

```bash
# Run container tests
./mvnw test -Dtest=*ContainerTest

# Check container startup logs
```

**Expected logs:**
```
Creating container for image: postgres:16-alpine
Container started: postgres
Creating container for image: localstack/localstack:latest
Container started: localstack
```

### 4. LocalStack Service Verification

**Test S3 operations:**

```java
@Test
void testS3Operations() {
    s3Client.createBucket(b -> b.bucket("test-bucket"));

    // Upload file
    s3Client.putObject(
        PutObjectRequest.builder().bucket("test-bucket").key("test.txt").build(),
        RequestBody.fromString("test content")
    );

    // Download file
    String content = s3Client.getObjectAsBytes(
        GetObjectRequest.builder().bucket("test-bucket").key("test.txt").build()
    ).asUtf8String();

    assertThat(content).isEqualTo("test content");
}
```

---

## Common Issues

### Issue 1: ClassNotFoundException

**Error:**
```
java.lang.ClassNotFoundException: org.testcontainers.containers.PostgreSQLContainer
```

**Cause:** Old import path

**Solution:**
```java
// Change
import org.testcontainers.containers.PostgreSQLContainer;

// To
import org.testcontainers.postgresql.PostgreSQLContainer;
```

### Issue 2: Cannot Resolve Generic Type

**Error:**
```
incompatible types: PostgreSQLContainer cannot be converted to PostgreSQLContainer<?>
```

**Cause:** Using old generic syntax

**Solution:**
```java
// Change
PostgreSQLContainer<?> container = ...

// To
PostgreSQLContainer container = ...
```

### Issue 3: LocalStack Service Not Found

**Error:**
```
error: cannot find symbol LocalStackContainer.Service.S3
```

**Cause:** Service enum removed in 2.x

**Solution:**
```java
// Remove
import static org.testcontainers.containers.localstack.LocalStackContainer.Service.S3;
.withServices(S3)

// Services now auto-detected
```

### Issue 4: Container Fails to Start

**Error:**
```
Could not start container: localstack/localstack:3.0
```

**Cause:** Old image version

**Solution:**
```java
// Change
DockerImageName.parse("localstack/localstack:3.0")

// To
DockerImageName.parse("localstack/localstack:latest")
```

---

## Migration Checklist

### Phase 1: Dependencies
- [ ] Update artifact names with `testcontainers-` prefix
- [ ] Verify all test dependencies use Testcontainers 2.x
- [ ] Remove old Testcontainers 1.x dependencies

### Phase 2: Imports
- [ ] Update PostgreSQL imports to `org.testcontainers.postgresql`
- [ ] Update MySQL imports to `org.testcontainers.mysql`
- [ ] Update LocalStack imports to `org.testcontainers.localstack`
- [ ] Update other container imports to module-specific packages
- [ ] Remove LocalStack Service enum imports

### Phase 3: Code Changes
- [ ] Remove generic types from container declarations
- [ ] Remove `.withServices()` from LocalStack configuration
- [ ] Update `getEndpointOverride(Service)` to `getEndpoint()`
- [ ] Update container image versions

### Phase 4: Testing
- [ ] Run compilation: `./mvnw clean test-compile`
- [ ] Run all container tests
- [ ] Verify PostgreSQL integration tests
- [ ] Verify LocalStack integration tests (S3, SQS, etc.)
- [ ] Verify other container tests
- [ ] Check container startup performance

---

## Best Practices

### 1. Use Latest Stable Images

```java
// Prefer specific versions for reproducibility
PostgreSQLContainer container = new PostgreSQLContainer("postgres:16-alpine");

// Or use latest for development
PostgreSQLContainer container = new PostgreSQLContainer("postgres:latest");
```

### 2. Reuse Containers Across Tests

```java
@Testcontainers
@SpringBootTest
class IntegrationTests {

    @Container
    static PostgreSQLContainer postgres = new PostgreSQLContainer("postgres:16");

    // Container reused across all test methods
}
```

### 3. Use @ServiceConnection

```java
@TestConfiguration
class TestConfig {

    @Bean
    @ServiceConnection  // Auto-configures DataSource
    PostgreSQLContainer postgres() {
        return new PostgreSQLContainer("postgres:16");
    }
}
```

### 4. Cleanup Resources

```java
@Bean(initMethod = "start", destroyMethod = "stop")
LocalStackContainer localstack() {
    return new LocalStackContainer("localstack/localstack:latest");
}
```

---

## References

- [Testcontainers 2.0 Migration Guide](https://java.testcontainers.org/migrations/testcontainers-2/)
- [Testcontainers Documentation](https://java.testcontainers.org/)
- [LocalStack Documentation](https://docs.localstack.cloud/)
- [Spring Boot Testcontainers Support](https://docs.spring.io/spring-boot/docs/current/reference/html/features.html#features.testing.testcontainers)
