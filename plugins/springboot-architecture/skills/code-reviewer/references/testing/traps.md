# Traps: Tests That Pass Without Proving Anything

Each entry is a way a Spring Boot 4.1 test stays green while the behavior it names is broken, or goes red on correct code. The HTTP, retry and Kafka entries were found by running `../../../writing-springboot-tests/assets/` on Boot 4.1.1 with Postgres 18, Kafka 4.1 and WireMock 3.13, each new test shown red against a planted bug (October 2026).

## HTTP clients and retries

- **A test that sets its own timeout can't catch a missing production one.** It must run with the production value and a stub delay just past it. In Scenario 12 an agent copied a `spring.http.clients.read-timeout` override into the timeout test and missed exactly that bug. Shorten timeouts only in tests that aren't about them.
- **`MockRestServiceServer` replaces the client's request factory.** Connect and read timeouts, the HTTP client and its settings never run, so a test with it can't catch a missing or wrong timeout, or a retry the real client adds. Use it only to check the shape of a request. For timeouts, retries and error answers, run the client as production builds it against WireMock. On a real codebase, deleting a client's timeout settings left every test built on `MockRestServiceServer` green.
- **AWS SDK clients have no call timeout unless you set one.** The SDK sets no `apiCallTimeout` or `apiCallAttemptTimeout` by default, so a hung AWS endpoint holds the caller for the HTTP client's read timeout on every retry. A Mockito mock of the SDK client can't show this. Test the client against WireMock: build it with the production `overrideConfiguration` (retry strategy, timeouts), `endpointOverride` set to WireMock's URL, a fixed region and static test credentials, and stub the AWS JSON error shape (`x-amzn-ErrorType`, for example `ThrottlingException`). If production sets no call timeout, report it.
- **`@RestClientTest` ignores `spring.http.clients.*`.** The slice doesn't import `HttpClientAutoConfiguration` or `ImperativeHttpClientAutoConfiguration`, so its client has no read timeout whatever the properties say. Import both, or a timeout test there proves nothing.
- **`@Retryable` on a class that implements an interface never retries** (Framework 7.0.9). The JDK proxy looks for the annotation on the interface method and finds none. Use `@EnableResilientMethods(proxyTargetClass = true)`. A test that builds the class with `new` can't see this either way.
- **WireMock changes the HTTP client.** `wiremock-spring-boot` puts Apache HttpClient 5 on the test classpath, and Boot then picks it over the JDK client. Apache's client retries a 503 POST once by itself, so a 503 → 200 retry test passes while `@Retryable` does nothing. Count the requests, and test with 500 too.
- **Matching JSON numbers as strings.** The request carried `37.5`, so `matchingJsonPath("$.amount", equalTo("37.50"))` failed on correct code. `equalToJson` compares numbers as numbers.

## Security

- **Test logins skip the app's own role mapping.** `oidcLogin()` ignores the app's `GrantedAuthoritiesMapper` (a `roles` claim gives `OIDC_USER` and `SCOPE_read`), `jwt()` ignores its `JwtAuthenticationConverter` (it reads only `scope`), and `user(...).roles(...)` never calls its `UserDetailsService`. A test that sets `ROLE_ADMIN` directly then passes while the mapping is broken. In a trial, four agents asked to test access all did this, and none caught a mapper reading the wrong claim. Sign in through the app's own code (`../../../writing-springboot-tests/assets/personas-*.java`).
- **A random-port test can't sign in through a browser login.** The request post-processors work only with MockMvc. With `oauth2Login` and a server-side session, a `RANDOM_PORT` test reaches only public routes; test the rest through `@AutoConfigureMockMvc`.
- **A role rule checked on one route says nothing about its siblings or new routes.** Narrowing `/api/admin/**` to `/api/admin/orders` leaves `/api/admin/orders/{id}` open while the one admin test stays green, and a new route ships with whatever the default is. Calling every route as every persona, and failing on a route nobody listed, catches both (`../../../writing-springboot-tests/assets/route-access-test.java`). It checks roles only: one user reading another user's records needs a test with two users.

## Events and messaging

- **Publish after commit can only be tested if something can fail after the event is raised.** If `publishEvent()` is the method's last line, publishing inside the transaction is harmless and the rollback test can't tell the difference. A `KafkaTemplate` mock in a context without transaction management can't tell either, and such tests often fail on correct code.
- **One `KafkaTestUtils.getRecords` call returns one batch.** The record you want may not be in it: in a trial, a dead-letter test failed on correct code for this reason. Poll into a list until the record is there.
- **A message that fails deserialization never reaches the listener or its error handler.** Without `ErrorHandlingDeserializer`, one non-JSON record blocks its partition for good. Test with a payload that isn't JSON, sent through a plain `StringSerializer` producer.
- **The dead letter of an unreadable message is corrupted.** `DeadLetterPublishingRecoverer` sends the original bytes through the app's JSON serializer, which writes them as a base64 string. Give the recoverer a byte-array template for `byte[]` values:

  ```java
  @Bean
  DefaultErrorHandler errorHandler(KafkaTemplate<Object, Object> kafka, ProducerFactory<Object, Object> producers) {
      var rawBytes = new KafkaTemplate<>(((DefaultKafkaProducerFactory<Object, Object>) producers)
              .copyWithConfigurationOverride(Map.of(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, ByteArraySerializer.class)));
      Map<Class<?>, KafkaOperations<?, ?>> templates = new LinkedHashMap<>();   // most specific type first
      templates.put(byte[].class, rawBytes);
      templates.put(Object.class, kafka);
      var handler = new DefaultErrorHandler(new DeadLetterPublishingRecoverer(templates), new FixedBackOff(100, 2));
      handler.addNotRetryableExceptions(IllegalArgumentException.class);   // a bad message won't get better
      return handler;
  }
  ```

- **The DLT name changed.** Spring Kafka 4 writes to `<topic>-dlt`, not `<topic>.DLT`.
- **`auto-offset-reset` defaults to `latest`.** A message sent before the listener joins its group is skipped, and the test fails at random. Set `spring.kafka.consumer.auto-offset-reset=earliest` in tests.

## Testcontainers

- **`@ServiceConnection` only reaches Boot's auto-configured connections.** A `DataSource` the app builds itself from its own properties (several databases, custom prefixes) never sees it. There, `DynamicPropertyRegistrar` or `@DynamicPropertySource` is correct, not a smell.
- **A shared container started by `@Testcontainers`/`@Container` breaks the cached context.** The extension stops the container after the first class, but the cached context keeps the old URL, so later classes fail. Start shared containers as `@Bean`s (`../../../writing-springboot-tests/assets/testcontainers-configuration.java`) or in a static block.
- **A container per class with `@DynamicPropertySource` means a context per class.** Each class's properties differ, so no context is shared. On a slow suite, count started containers and "Creating new context" lines (`logging.level.org.springframework.test.context.cache=DEBUG`) before tuning anything else.
- **Testcontainers 2 still compiles the 1.x classes.** `org.testcontainers.containers.PostgreSQLContainer` and the other moved modules are deprecated, not removed. For Kafka it matters now: Boot has no `@ServiceConnection` factory for the old `KafkaContainer`. Run `../../../springboot-migration/scripts/scan_migration_issues.py`.
- **No Docker skips silently.** `@Testcontainers(disabledWithoutDocker = true)` passes a run that tested nothing. CI must have Docker.

## Test data

- **`@Transactional` doesn't roll back a `RANDOM_PORT` test.** The server handles the request on another thread and commits. Clean up explicitly.
- **Clean before each test, not after.** A `@BeforeEach` delete or `@Sql` reset also survives a test that crashed or a run that was killed. A cleanup that runs only after a test leaves the next run dirty.
- **A fixture for a schema the project doesn't own is a contract copy.** A hand-written `CREATE TABLE` for another system's database drifts from the real one, and the tests then pass against the copy. Keep it as a `.sql` file, note where it came from, and review it when the other side changes. Copy it in with `withCopyFileToContainer`, not a bind mount, so it works on a remote Docker host.
