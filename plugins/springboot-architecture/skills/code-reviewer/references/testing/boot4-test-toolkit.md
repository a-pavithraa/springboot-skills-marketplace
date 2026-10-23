# Spring Boot 4 Test Toolkit

Boot 4 split the test support into modules, and agents most often get these imports wrong. Packages were checked against the Boot 4.1.1 jars on Maven Central (October 2026).

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

## Boot 4 changes agents miss

- `@MockBean` and `@SpyBean` are gone: use `@MockitoBean`, `@MockitoSpyBean`. `TestRestTemplate` is on its way out: use `RestTestClient`.
- `@SpringBootTest` no longer auto-configures HTTP test clients. Add `@AutoConfigureRestTestClient` or `@AutoConfigureMockMvc`.
- `RestTestClient` sends a request body with `.body(object)`. `.bodyValue(...)` is `WebTestClient`'s method and does not compile on `RestTestClient`.
- The Testcontainers 2 module classes take no type parameter: `PostgreSQLContainer`, not `PostgreSQLContainer<?>`. `GenericContainer<?>` keeps it.
- Spring Framework 7 pauses cached contexts between uses, so scheduled tasks and listeners in an idle cached context no longer interfere with other tests.
- One shared container configuration for the whole suite: `../../../writing-springboot-tests/assets/testcontainers-configuration.java`.

## PIT

Use PIT before breaking code by hand, for any class with plain unit tests. In a trial on an `OrderService` (39 mutants), PIT took 6 seconds. Breaking each line of the same class by hand, through Maven and a container per run, did not finish in 10 minutes.

Add `../../../writing-springboot-tests/assets/pitest-plugin.xml` (`pitest-maven` 1.30.1, `pitest-junit5-plugin` 1.2.3, checked October 2026), then run it for one class:

```bash
./mvnw test-compile org.pitest:pitest-maven:mutationCoverage \
  -DtargetClasses=com.example.orders.domain.OrderService \
  -DtargetTests='com.example.orders.domain.*Test'
```

The report is in `target/pit-reports/index.html`. Gradle: the `info.solidsoft.pitest` plugin with `junit5PluginVersion` set; the parameters have the same names.

- Start with unit and slice tests. PIT runs the tests once per mutant, so tests that start containers make it very slow.
- In a test with a cached Spring context, mutants in constructors and `@PostConstruct` code survive however good the tests are: each bean is built once. A surviving "Removed assignment to member variable" there is this artifact, not a gap.
- Don't chase 100%. Chase survivors in the logic the change is about, and name equivalent mutants.
