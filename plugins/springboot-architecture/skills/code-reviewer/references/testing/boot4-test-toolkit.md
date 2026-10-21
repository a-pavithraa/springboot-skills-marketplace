# Spring Boot 4 Test Toolkit

The mechanics, for Spring Boot 4.1 and Spring Framework 7.0. Packages were checked against the Boot 4.1.1 jars on Maven Central (October 2026). Agents most often get these imports wrong, because Boot 4 split the test support into modules. For more depth on each level, see Siva Prasad Reddy's [spring-boot skill references](https://github.com/sivaprasadreddy/sivalabs-agent-skills/tree/main/skills/spring-boot/references) (MIT).

## Imports

| Annotation / class | Package | Module |
|--------------------|---------|--------|
| `@SpringBootTest`, `@TestConfiguration` | `org.springframework.boot.test.context` | `spring-boot-test` |
| `@WebMvcTest`, `@AutoConfigureMockMvc` | `org.springframework.boot.webmvc.test.autoconfigure` | `spring-boot-webmvc-test` |
| `@DataJpaTest` | `org.springframework.boot.data.jpa.test.autoconfigure` | `spring-boot-data-jpa-test` |
| `TestEntityManager` | `org.springframework.boot.jpa.test.autoconfigure` | `spring-boot-jpa-test` |
| `@JdbcTest`, `@AutoConfigureTestDatabase` | `org.springframework.boot.jdbc.test.autoconfigure` | `spring-boot-jdbc-test` |
| `@JsonTest` | `org.springframework.boot.test.autoconfigure.json` | `spring-boot-test-autoconfigure` |
| `@RestClientTest` | `org.springframework.boot.restclient.test.autoconfigure` | `spring-boot-restclient-test` |
| `@AutoConfigureRestTestClient` | `org.springframework.boot.resttestclient.autoconfigure` | `spring-boot-resttestclient` |
| `@ServiceConnection` | `org.springframework.boot.testcontainers.service.connection` | `spring-boot-testcontainers` |
| `MockMvcTester` | `org.springframework.test.web.servlet.assertj` | `spring-test` |
| `RestTestClient` | `org.springframework.test.web.servlet.client` | `spring-test` |
| `@MockitoBean`, `@MockitoSpyBean` | `org.springframework.test.context.bean.override.mockito` | `spring-test` |
| `@TestBean` | `org.springframework.test.context.bean.override.convention` | `spring-test` |
| `DynamicPropertyRegistrar`, `@Sql` | `org.springframework.test.context`, `…context.jdbc` | `spring-test` |
| `PostgreSQLContainer` (Testcontainers 2) | `org.testcontainers.postgresql` | `testcontainers-postgresql` |
| `KafkaContainer` (Testcontainers 2) | `org.testcontainers.kafka` | `testcontainers-kafka` |
| `KafkaConnectionDetails` | `org.springframework.boot.kafka.autoconfigure` | `spring-boot-kafka` |
| `@EnableWireMock`, `@ConfigureWireMock`, `@InjectWireMock` | `org.wiremock.spring` | `org.wiremock.integrations:wiremock-spring-boot` 4.4.3 (not managed by Boot) |
| `@Retryable`, `@EnableResilientMethods` | `org.springframework.resilience.annotation` | `spring-context` |

Test starters per technology: `spring-boot-starter-webmvc-test`, `spring-boot-starter-data-jpa-test`, `spring-boot-starter-restclient-test`, `spring-boot-starter-kafka-test`, `spring-boot-starter-security-test`, all with `<scope>test</scope>`. Testcontainers support is `spring-boot-testcontainers`; there is no `-starter-` for it.

Versions Boot 4.1.1 manages: JUnit Jupiter 6.0.3, Mockito 5.23.0, AssertJ 3.27.7, Awaitility 4.3.0, Testcontainers 2.0.5. Don't pin them yourself.

`RestTestClient` sends a request body with `.body(object)`. `.bodyValue(...)` is `WebTestClient`'s method and does not compile on `RestTestClient`.

Gone in Boot 4: `@MockBean` and `@SpyBean` (use `@MockitoBean`, `@MockitoSpyBean`); `TestRestTemplate` is on its way out (use `RestTestClient`). HTTP test clients are no longer auto-configured by `@SpringBootTest`: add `@AutoConfigureRestTestClient` or `@AutoConfigureMockMvc`.

## Levels in one line each

- **Unit**: `@ExtendWith(MockitoExtension.class)`, constructor injection, no Spring. For rules and calculations.
- **Web slice**: `@WebMvcTest(OrderController.class)` + `MockMvcTester` + `@MockitoBean` for the service. Covers mapping, validation, status, JSON, `ProblemDetail`, and security (`.with(user("u").roles("ADMIN"))`, `.with(csrf())`).
- **Persistence slice**: `@DataJpaTest` + `@AutoConfigureTestDatabase(replace = NONE)` + `@Import(TestcontainersConfiguration.class)`. Use `TestEntityManager` to `persistAndFlush` and `clear`, so queries really reach the database. Each test rolls back.
- **HTTP client**: `@RestClientTest(PaymentClient.class)` with WireMock as a real HTTP server (`@AutoConfigureMockRestServiceServer(enabled = false)`), or `MockRestServiceServer` for request/response mapping only. The slice doesn't apply `spring.http.clients.*` timeouts: see `distributed-systems.md`.
- **Module (Modulith)**: `@ApplicationModuleTest` with a `Scenario` parameter: `scenario.publish(event).andWaitForStateChange(...)` or `.andWaitForEventOfType(...)`.
- **Full stack**: `@SpringBootTest(webEnvironment = RANDOM_PORT)` + `@AutoConfigureRestTestClient` + `RestTestClient`. Keep a few for critical paths. Clean data up yourself, because the server's transaction commits.

## Testcontainers wiring

- **One** `@TestConfiguration(proxyBeanMethods = false)` class holds every container as a `@Bean @ServiceConnection`, and every test imports it. Same imports means one cached context and one container per run. See `../../../writing-springboot-tests/assets/testcontainers-configuration.java`.
- `@ServiceConnection` covers JDBC databases, MongoDB, Redis (`GenericContainer` with `name = "redis"`), Kafka (`org.testcontainers.kafka.*` only), RabbitMQ, Elasticsearch, and others. Don't also set `spring.datasource.*`.
- No connection factory for the container (MailHog, a custom service): register its mapped host and port lazily with a `DynamicPropertyRegistrar` bean. Fixed values go in `application-test.properties`, never in dynamic properties.
- Never fix host ports (`withFixedExposedPorts`, hard-coded `5432`).
- Local speed: `testcontainers.reuse.enable=true` in `~/.testcontainers.properties` plus `.withReuse(true)` keeps containers between runs. Local only; CI starts fresh.
- No Docker: `@Testcontainers(disabledWithoutDocker = true)` skips locally. CI must have Docker, or the "passing" suite tested nothing.

## Keeping the context cache warm

Spring reuses an application context when the configuration is identical: classes, profiles, properties, `@MockitoBean` set, and imports. Every difference starts another context.

- Share one test configuration: a base class or a meta-annotation with the same `@SpringBootTest`, `@ActiveProfiles("test")`, `@Import(TestcontainersConfiguration.class)`, and mocks
- Don't add a different `@MockitoBean` per class to a full-context test; prefer a slice for that test
- Avoid `@DirtiesContext`; fix the state that leaks
- Measure: `logging.level.org.springframework.test.context.cache=DEBUG` and look for "Creating new context"
- Spring Framework 7 pauses cached contexts between uses (scheduled tasks and listeners stop), so idle cached contexts no longer interfere

## Test data

- Prefer `@Sql("/test-data.sql")` fixtures, or creating data through the application's own services or module APIs, over raw `JdbcTemplate` inserts
- State in the test the fixture values the expectation depends on
- Full-stack tests clean up in `@AfterEach` or with an `@Sql` cleanup script (`executionPhase = AFTER_TEST_METHOD`)

## Parallel runs

JUnit runs test classes one after another unless `junit.jupiter.execution.parallel.enabled=true`. Before turning it on: tests that reset shared tables (`@Sql` truncate scripts) or share one WireMock server can't run in parallel against the same context. Either keep those classes sequential (`@Execution(SAME_THREAD)`, or `@ResourceLock("db")`), or make each test own its data (unique codes and ids, no truncation) and assert only on that data.

## Async

- Awaitility: `await().atMost(Duration.ofSeconds(5)).untilAsserted(() -> ...)`
- Events across modules: Modulith `Scenario`, not sleeps or polling loops
