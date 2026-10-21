package {{PACKAGE}};

import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.context.annotation.Bean;
import org.testcontainers.postgresql.PostgreSQLContainer;

import static org.testcontainers.utility.DockerImageName.parse;

/**
 * The ONE place the test containers are declared. Every persistence and integration test imports it with
 * {@code @Import(TestcontainersConfiguration.class)}: the same import keeps one cached Spring context and one
 * running container for the whole test run.
 *
 * Use the database version production runs. @ServiceConnection wires spring.datasource.* for you, so don't
 * also set those properties.
 *
 * Boot 4 dependencies (test scope): spring-boot-testcontainers, org.testcontainers:testcontainers-junit-jupiter,
 * org.testcontainers:testcontainers-postgresql. Versions come from the Boot BOM.
 */
@TestConfiguration(proxyBeanMethods = false)
public class TestcontainersConfiguration {

    @Bean
    @ServiceConnection
    PostgreSQLContainer postgres() {
        return new PostgreSQLContainer(parse("postgres:18-alpine"));
    }

    // Kafka: org.testcontainers.kafka.KafkaContainer (not the old org.testcontainers.containers one).
    // @ServiceConnection sets spring.kafka.bootstrap-servers. Needs org.testcontainers:testcontainers-kafka.
    // @Bean
    // @ServiceConnection
    // KafkaContainer kafka() {
    //     return new KafkaContainer(parse("apache/kafka-native:4.1.1"));
    // }

    // Redis has no dedicated container class: a GenericContainer plus a name hint.
    // @Bean
    // @ServiceConnection(name = "redis")
    // GenericContainer<?> redis() {
    //     return new GenericContainer<>(parse("redis:8-alpine")).withExposedPorts(6379);
    // }

    // A container Boot has no connection factory for: register its mapped address lazily.
    // Fixed settings (feature flags, ddl-auto) belong in application-test.properties, not here.
    // @Bean
    // GenericContainer<?> mailpit() {
    //     return new GenericContainer<>(parse("axllent/mailpit:v1.27")).withExposedPorts(1025);
    // }
    //
    // @Bean
    // DynamicPropertyRegistrar mailProperties(GenericContainer<?> mailpit) {
    //     return registry -> {
    //         registry.add("spring.mail.host", mailpit::getHost);
    //         registry.add("spring.mail.port", () -> mailpit.getMappedPort(1025));
    //     };
    // }
}
