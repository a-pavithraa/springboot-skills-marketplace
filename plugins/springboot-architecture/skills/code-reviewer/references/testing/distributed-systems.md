# Testing a Service That Talks to Other Services

Most bugs in a service sit where it meets other systems: the request it sends, how it reads the answer, what it does when the other side is slow, down, or says no, and what it does when a message comes twice or can't be read. A unit test with the client mocked sees none of it, because the mock answers whatever the test tells it to. Test these at the service's edges, with real HTTP and real brokers.

Every asset named here was run on Spring Boot 4.1.1 against Postgres 18, Kafka 4.1 and WireMock 3.13, and each new test was shown to fail against a planted bug (October 2026). The traps below are what those runs turned up.

## The cases, as the caller sees them

For each call to another service, list these before writing tests:

| The other side... | What our service must do | Test with |
|-------------------|--------------------------|-----------|
| answers as documented | send exactly the documented request; map the answer | WireMock `verify(...)` on path, headers, `equalToJson` body |
| refuses (4xx) | a domain error the caller understands; **no retry** | stub 4xx, assert the exception, `verify(1, ...)` |
| fails (5xx, connection reset) | retry if the call is safe to repeat, then give up with a clear error | WireMock scenario 503 → 200; `Fault.CONNECTION_RESET_BY_PEER` |
| is slow | time out instead of hanging the request thread | `withFixedDelay(...)` just past the **production** read timeout, read from `application.properties` |
| answers 200 with something we can't use | **not** treat it as success | 200 with HTML, `{}`, and a readable but wrong status |
| gets our retry after the first call went through | do the side effect once | same idempotency key on every attempt (`verify(2, ...withHeader(...))`) |

For each message the service consumes:

| What happens | What our service must do | Test with |
|--------------|--------------------------|-----------|
| a message arrives | the stored state changes | send with `KafkaTemplate`, assert the state with Awaitility |
| the same message arrives again | change the state once | send it twice, then a later message with the same key; await the final state |
| a message can't be processed | dead-letter it and carry on with the next one | send the bad one then a good one; await the good one's effect; read the DLT |

For each event the service publishes: it is published when the change commits, and never for a change that rolled back.

## Assets

| File | Shows |
|------|-------|
| `../../../writing-springboot-tests/assets/http-client-wiremock-test.java` | `@RestClientTest` + WireMock: the request, 4xx, retries with the same idempotency key, giving up, timeout, dropped connection, unusable 200 |
| `../../../writing-springboot-tests/assets/message-listener-test.java` | Kafka listener with Testcontainers: state change, redelivery applied once, an invalid message and a non-JSON message each dead-lettered without blocking the next |
| `../../../writing-springboot-tests/assets/event-publication-test.java` | `OrderPlaced` reaches Kafka after commit and never for a rolled-back order |
| `../../../writing-springboot-tests/assets/api-integration-test.java` | The service end to end, with the payment provider as a WireMock stub, including a declined payment rolling back the stock reservation |

## Traps found while running the assets

These pass silently in any test that mocks the client, so they are worth a line in a review:

- **`@RestClientTest` ignores `spring.http.clients.*`** (Boot 4.1.1). The slice doesn't import `HttpClientAutoConfiguration` or `ImperativeHttpClientAutoConfiguration`, so its client has no read timeout, whatever the properties say. Import both (see the asset), or a timeout test there proves nothing.
- **`@Retryable` on a class that implements an interface never retries** (Framework 7.0.9). The default JDK proxy looks the annotation up on the interface method and finds none. Use `@EnableResilientMethods(proxyTargetClass = true)`, and inject the interface in tests, as the rest of the app does.
- **WireMock changes the HTTP client.** `wiremock-spring-boot` puts Apache HttpClient 5 on the test classpath, and Boot then picks `HttpComponentsClientHttpRequestFactory` over the JDK client. Apache's client retried a 503 POST once on its own (a 500 it didn't), so a 503 → 200 retry test passed while `@Retryable` was doing nothing. Count the requests, and test with 500 too.
- **Testing a publish-after-commit only works if something can fail after the event is raised.** If `publishEvent()` is the method's last line, publishing inside the transaction is harmless and the rollback test can't tell the difference. Check the order of calls before trusting a green test.
- **The dead letter of an unreadable message gets corrupted.** `DeadLetterPublishingRecoverer` sends the original bytes through the app's JSON value serializer, which writes them as a base64 string. Give the recoverer a byte-array template for `byte[]` values (below). The asset's assertion on the DLT content catches this.
- **The DLT name changed.** Spring Kafka 4's `DeadLetterPublishingRecoverer` writes to `<topic>-dlt`, not `<topic>.DLT`.
- **Matching JSON numbers as strings.** The request carried `37.5`, so `matchingJsonPath("$.amount", equalTo("37.50"))` failed. `equalToJson` compares numbers as numbers.

## Messaging details

- One `TestcontainersConfiguration` holds the broker next to the database (`KafkaContainer` from `org.testcontainers.kafka`, `@ServiceConnection`). Don't use `@EmbeddedKafka` when the real broker is one container away: it runs a different code path and its own configuration.
- `spring.kafka.consumer.auto-offset-reset=earliest`, or a message sent before the listener joins its group is skipped and the test fails at random.
- Read a topic in a test by polling into a list until the expected record is in it (see the asset). One `KafkaTestUtils.getRecords` call returns the first batch only, so the record you want may not be in it: in the trial, an agent's dead-letter test failed on correct code for this reason.
- Order within a key is the tool for proving "nothing else happened" without a sleep: send the message under test, then a marker with the same key, and wait for the marker's effect.
- A message that fails deserialization never reaches your listener or its error handler. Without `ErrorHandlingDeserializer`, one non-JSON record blocks its partition for good: in the trial, the valid message behind it was never applied. Test it with a payload that isn't JSON (the asset sends one with a plain `StringSerializer` producer).
- The consumer side the listener asset expects, as it ran on Boot 4.1.1:

  ```properties
  spring.kafka.consumer.auto-offset-reset=earliest
  spring.kafka.consumer.value-deserializer=org.springframework.kafka.support.serializer.ErrorHandlingDeserializer
  spring.kafka.consumer.properties.spring.deserializer.value.delegate.class=org.springframework.kafka.support.serializer.JacksonJsonDeserializer
  ```

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

- Give idempotency keys unique values per test (`UUID`): processed-message tables usually survive the per-test data reset.
- RabbitMQ: the same tests apply with `RabbitMQContainer` and `RabbitTemplate`. Assert dead-lettering through the queue's `x-dead-letter-exchange`.

## Outbox and Spring Modulith

A plain `@TransactionalEventListener` that sends to Kafka loses the event if the process dies between commit and send. A transactional outbox, or Spring Modulith's event publication registry, stores the event in the same transaction and sends it afterwards. Test:

- the event row is stored in the same transaction as the business change, and is absent when the change rolls back
- it is sent after commit (`event-publication-test.java` shows how to read the topic)
- a failed send is retried: with Modulith, make the first send fail, then call `IncompleteEventPublications.resubmitIncompletePublications(...)` and see it arrive

Inside one application, between modules, use `@ApplicationModuleTest` with `Scenario` instead (see `boot4-test-toolkit.md`).

## Network faults below HTTP

WireMock covers HTTP faults: delays, resets, garbage. For faults between the service and its own infrastructure (a database or broker that becomes slow or unreachable mid-test), put Testcontainers' Toxiproxy module (`org.testcontainers.toxiproxy.ToxiproxyContainer`, artifact `testcontainers-toxiproxy`) between them and add latency or cut the connection. Reserve this for code that claims to survive such faults (connection-pool timeouts, consumer reconnects). It was not part of the verified assets.

## Contracts between teams

A WireMock stub is our guess at the other service's API. It drifts when they change. Consumer-driven contracts turn the guess into a check that runs in the provider's build.

- **Spring Cloud Contract**: JVM only. Contracts are written by hand (Groovy or YAML) and kept with the provider. The provider build generates tests from them; consumers get a stub jar for WireMock. Fits teams where everyone runs Spring.
- **Pact**: across languages. The consumer's tests generate the contract; a broker stores it, the provider verifies it, and `can-i-deploy` gates releases. Fits mixed stacks.

Start with contracts once a stub has been wrong in production, or once more than one team consumes the API. Before that, keep realistic recorded fixtures (real responses saved as files) and review them when the provider's API changes.

## What not to do

- Start other teams' services locally, or run tests against a shared environment: slow, flaky, and the failures belong to someone else. Stub them.
- Mock your own HTTP client in the service's integration tests. Stub the server, so your mapping, timeouts and error handling run.
- Assert only that "a call was made". Assert the request content the provider documents, and how many calls.
- Retry a call that isn't idempotent without an idempotency key.
- Shorten a timeout with a test property in the test that checks the timeout. It must run with the production value and a stub delay just past it, or a missing production timeout passes (Scenario 12: an agent copied such an override and missed exactly that bug). Shorten timeouts only in tests that aren't about them.
