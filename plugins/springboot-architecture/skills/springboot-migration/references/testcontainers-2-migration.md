# Testcontainers 1.x → 2.x Migration

Official: [2.0.0 release notes](https://github.com/testcontainers/testcontainers-java/releases/tag/2.0.0), [OpenRewrite recipe](https://docs.openrewrite.org/recipes/java/testing/testcontainers/testcontainers2migration). Checked against Testcontainers 2.0.5 (the version Boot 4.1.1 manages) on 2026-10-17.

Boot 4 manages Testcontainers 2 versions, so this migration is part of the Boot 4 upgrade when the project uses Testcontainers.

## 1. Artifacts (required)

Every module artifact gets the `testcontainers-` prefix. The core artifact `testcontainers` keeps its name.

| 1.x | 2.x |
|-----|-----|
| `org.testcontainers:junit-jupiter` | `org.testcontainers:testcontainers-junit-jupiter` |
| `org.testcontainers:postgresql`, `mysql`, `mariadb`, `mongodb`, `kafka`, `rabbitmq`, `localstack`, `elasticsearch`, `jdbc`, ... | `org.testcontainers:testcontainers-<same name>` |

Boot 4's BOM manages only the 2.x names. Old artifact IDs lose their managed version, and Maven fails with "version is missing" (or Gradle with "could not find").

There is no official Redis module. Use `GenericContainer` with `redis:<tag>` (Boot's `@ServiceConnection` supports it with `name = "redis"`), or the third-party `com.redis:testcontainers-redis`.

## 2. Classes (recommended)

Module containers moved to `org.testcontainers.<module>` packages. The old classes in `org.testcontainers.containers` still exist in 2.0.x but are **deprecated**, so the code still compiles. Move to the new classes now; the old ones will be removed later.

| Deprecated (1.x location) | New |
|---------------------------|-----|
| `org.testcontainers.containers.PostgreSQLContainer<?>` | `org.testcontainers.postgresql.PostgreSQLContainer` |
| `org.testcontainers.containers.MySQLContainer<?>` | `org.testcontainers.mysql.MySQLContainer` |
| `org.testcontainers.containers.MariaDBContainer<?>` | `org.testcontainers.mariadb.MariaDBContainer` |
| `org.testcontainers.containers.MongoDBContainer` | `org.testcontainers.mongodb.MongoDBContainer` |
| `org.testcontainers.containers.RabbitMQContainer` | `org.testcontainers.rabbitmq.RabbitMQContainer` |
| `org.testcontainers.containers.localstack.LocalStackContainer` | `org.testcontainers.localstack.LocalStackContainer` |
| `org.testcontainers.containers.KafkaContainer` (image `confluentinc/cp-kafka`) | `org.testcontainers.kafka.ConfluentKafkaContainer` (same image) or `org.testcontainers.kafka.KafkaContainer` (image `apache/kafka`) |
| `org.testcontainers.elasticsearch.ElasticsearchContainer` | unchanged |

The new JDBC containers are not generic: write `PostgreSQLContainer`, not `PostgreSQLContainer<?>`.

**Kafka trap:** the new `org.testcontainers.kafka.KafkaContainer` accepts only `apache/kafka` images. With `confluentinc/cp-kafka`, it fails at construction: "Failed to verify that image 'confluentinc/cp-kafka:...' is a compatible substitute for 'apache/kafka'". Use `ConfluentKafkaContainer` for Confluent images.

**Kafka + `@ServiceConnection`:** Boot 4 has connection factories only for the new `org.testcontainers.kafka.KafkaContainer` and `ConfluentKafkaContainer`. A deprecated `org.testcontainers.containers.KafkaContainer` bean with `@ServiceConnection` gets no connection details, so Kafka tests fail even though the code compiles. JDBC, MongoDB, and RabbitMQ factories accept both old and new classes.

```java
@TestConfiguration(proxyBeanMethods = false)
class TestcontainersConfig {
    @Bean
    @ServiceConnection
    PostgreSQLContainer postgres() {
        return new PostgreSQLContainer(DockerImageName.parse("postgres:17-alpine"));
    }

    @Bean
    @ServiceConnection
    ConfluentKafkaContainer kafka() {
        return new ConfluentKafkaContainer("confluentinc/cp-kafka:7.8.0");
    }
}
```

## 3. LocalStack

| 1.x (deprecated class) | 2.x (`org.testcontainers.localstack.LocalStackContainer`) |
|------------------------|-----------------------------------------------------------|
| `.withServices(Service.S3, Service.SQS)` | `.withServices("s3", "sqs")`. The new class has no `Service` enum |
| `getEndpointOverride(Service.S3)` | `getEndpoint()`. One endpoint for all services |
| `getAccessKey()`, `getSecretKey()`, `getRegion()` | unchanged |

```java
LocalStackContainer localstack = new LocalStackContainer(DockerImageName.parse("localstack/localstack:<pinned-tag>"))
        .withServices("s3", "sqs");

S3Client s3 = S3Client.builder()
        .endpointOverride(localstack.getEndpoint())
        .credentialsProvider(StaticCredentialsProvider.create(
                AwsBasicCredentials.create(localstack.getAccessKey(), localstack.getSecretKey())))
        .region(Region.of(localstack.getRegion()))
        .build();
```

**Image licensing (2026):** from LocalStack 2026.03 (March 23, 2026), `localstack/localstack` is a single image that requires an auth token. Without `LOCALSTACK_AUTH_TOKEN` in the container environment, startup fails. Do not move to `latest` as part of this migration. Either keep a pinned pre-2026.03 tag, or pass the token (`.withEnv("LOCALSTACK_AUTH_TOKEN", System.getenv("LOCALSTACK_AUTH_TOKEN"))`) and configure it in CI. Ask the user which option fits. Source: [LocalStack single-image announcement](https://blog.localstack.cloud/localstack-single-image-next-steps/).

## 4. JUnit 4 (required if used)

Containers no longer implement JUnit 4's `TestRule`, and Testcontainers no longer brings `junit:junit` as a dependency. Code that used JUnit 4 only through Testcontainers stops compiling (`org.junit.Rule` not found). If JUnit 4 is declared directly, `@Rule` / `@ClassRule` container fields compile but fail at run time with an `initializationError` ("must implement MethodRule or TestRule"). Move to JUnit 5 (`@Testcontainers` + `@Container`) or, in Spring Boot, to `@ServiceConnection` beans as above.

## 5. Images

Testcontainers 2 does not require new image versions. Keep pinned tags and upgrade images separately, so a failing test points to one change.

## Verification

```bash
./mvnw dependency:tree -Dincludes=org.testcontainers   # all 2.0.x, no 1.x artifacts
./mvnw clean test-compile -Dmaven.compiler.showDeprecation=true   # remaining deprecated classes
./mvnw verify                                           # container tests (needs Docker)
```

## Common failures

| Error | Cause | Fix |
|-------|-------|-----|
| `'dependencies.dependency.version' for org.testcontainers:postgresql:jar is missing` | 1.x artifact ID under the Boot 4 BOM | Use `testcontainers-postgresql` |
| `package org.junit does not exist`, or `initializationError: ... must implement MethodRule or TestRule` | JUnit 4 rules | Move to JUnit 5 or `@ServiceConnection` |
| Kafka tests cannot connect; no `KafkaConnectionDetails` from the container | Deprecated `org.testcontainers.containers.KafkaContainer` with `@ServiceConnection` | `ConfluentKafkaContainer` or the new `KafkaContainer` |
| `Failed to verify that image 'confluentinc/cp-kafka...' is a compatible substitute for 'apache/kafka'` | New `KafkaContainer` with a Confluent image | `ConfluentKafkaContainer` |
| `cannot find symbol: Service` with the new `LocalStackContainer` | Enum exists only on the deprecated class | `.withServices("s3")`, `getEndpoint()` |
| LocalStack container exits with an authentication error | 2026.03+ image without auth token | Pin an older tag, or set `LOCALSTACK_AUTH_TOKEN` |
| `Could not find a valid Docker environment` | Docker not running or not reachable | Start Docker; Boot 4.1 prints a failure analysis with details |

## Checklist

- [ ] All `org.testcontainers` artifacts use the `testcontainers-` prefix (except core `testcontainers`)
- [ ] Imports moved to `org.testcontainers.<module>`; no `<?>` on JDBC containers
- [ ] Kafka: `ConfluentKafkaContainer` for `cp-kafka`, `KafkaContainer` for `apache/kafka` (required for `@ServiceConnection`)
- [ ] LocalStack: string services, `getEndpoint()`, image tag and auth token decided with the user
- [ ] No JUnit 4 `@Rule`/`@ClassRule` containers
- [ ] Image tags unchanged in this step
