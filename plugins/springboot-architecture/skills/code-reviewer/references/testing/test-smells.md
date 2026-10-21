# Test Smells in Agent-Written Tests

Read every new test against this list. Each entry: what it looks like, why it lets bugs through, and the fix.

## 1. Expected value copied from the implementation

```java
// BAD: the test re-derives the answer the way the code does, so a wrong formula passes
assertThat(pricing.total(order)).isEqualTo(order.subtotal().multiply(TAX_RATE).add(order.subtotal()));
```

The test agrees with the code by construction. This is the most common agent failure: the expected value comes from reading the implementation.

```java
// GOOD: a worked example from the requirement: 100.00 at 8% tax is 108.00
var order = orderWithSubtotal("100.00");
assertThat(pricing.total(order)).isEqualByComparingTo("108.00");
```

## 2. Weak assertion

```java
// BAD
assertThat(result).isNotNull();
assertThat(items).hasSizeGreaterThan(0);
client.get().uri("/api/products").exchange().expectStatus().isOk();   // body never checked
```

Almost any bug still passes.

```java
// GOOD
assertThat(items).extracting(ProductView::code).containsExactly("P-1", "P-2");
```

## 3. Verify-only (testing the mock, not the outcome)

```java
// BAD: passes even if the order is never saved with the right status
orderService.place(command);
verify(orderRepository).save(any());
```

```java
// GOOD: assert what the caller gets back, and check the side effect's content
Order placed = orderService.place(command);
assertThat(placed.status()).isEqualTo(OrderStatus.PLACED);
verify(paymentGateway).charge(new Money("40.00"));   // the side effect itself is the behaviour
```

Use `verify` for side effects that *are* the behaviour (a charge, an email, an event), and `verifyNoInteractions` to prove one did **not** happen.

## 4. Mocking the subject, or what you own

```java
// BAD: the spy stubs the method under test, so nothing real runs
var service = spy(new DiscountService());
doReturn(10).when(service).percentFor(customer);
```

Also bad: mocking value objects, entities, mappers, or the repository in a test whose point is the query. Mock only external systems, the clock, and randomness.

## 5. Magic numbers

```java
// BAD: why 598?
scenario.publish(event).andWaitForStateChange(() -> inventory.stockLevel("P114") == 598);
```

```java
// GOOD: the expectation reads from the arrangement
int initialStock = 600, ordered = 2;   // P114 starts at 600 in test-products-data.sql
... == initialStock - ordered
```

## 6. Assertion roulette

Many unlabelled assertions in one test, so a failure doesn't say which behaviour broke. Split it into tests, or keep one behaviour and label the checks:

```java
SoftAssertions.assertSoftly(s -> {
    s.assertThat(view.code()).as("code").isEqualTo("P-1");
    s.assertThat(view.price()).as("price").isEqualByComparingTo("9.99");
});
```

## 7. Empty or print-only tests

```java
@Test void contextLoads() { }                    // fine as the ONE smoke test, not repeated per class
@Test void printStructure() { System.out.println(modules); }   // asserts nothing: delete or assert
```

## 8. Swallowed or vague exceptions

```java
// BAD
assertThrows(Exception.class, () -> service.withdraw(account, amount));
try { service.withdraw(...); fail(); } catch (Exception e) { }
```

```java
// GOOD
assertThatThrownBy(() -> service.withdraw(account, new Money("500.00")))
        .isInstanceOf(InsufficientFundsException.class)
        .hasMessageContaining("balance 100.00");
```

## 9. Sleeping for async work

`Thread.sleep(2000)` is slow when the work is fast and flaky when it is slow. Use Awaitility, or Modulith's `Scenario` for events:

```java
await().atMost(Duration.ofSeconds(5))
       .untilAsserted(() -> assertThat(repository.findByCode("P-1")).isPresent());
```

## 10. Hidden or shared test data

A test reads `"TEST-001"` that some other test, or nothing, created. It passes alone and fails in a different order, or the other way round. Each test creates its data, or loads a named `@Sql` fixture whose values it states.

**`@Transactional` does not roll back `RANDOM_PORT` tests:** the server handles the request on another thread and commits. Clean up explicitly (`@AfterEach` or an `@Sql` cleanup script) in full-stack tests.

## 11. Repository test that never reaches the database

```java
// BAD: save then find inside one transaction is served from the persistence context, never SQL
repository.save(product);
assertThat(repository.findBySku("P-1")).isPresent();
```

```java
// GOOD: flush and clear so the query really runs
entityManager.persistAndFlush(product);
entityManager.clear();
assertThat(repository.findBySku("P-1")).map(Product::getName).hasValue("Lamp");
```

## 12. Testing the framework

Getters and setters, `findById` from Spring Data, that `@Autowired` works. Spring tests those. Test your queries, your rules, and your mappings.

## 13. Context cache killers

Each distinct set of `@MockitoBean`s, properties, or profiles makes Spring start a new application context. Agents add a `@MockitoBean` per test class, and the suite slows from seconds to minutes.

- Put shared mocks and the container config in one base class or one `@TestConfiguration`
- Avoid `@DirtiesContext`; fix the leaking state instead
- Watch it with `logging.level.org.springframework.test.context.cache=DEBUG`

## 14. H2 instead of the real database

H2 passes SQL that PostgreSQL rejects, and the other way round, and ignores real constraint and type behaviour. Use the Testcontainers config the project already has.

## 15. Random data hiding the point

Instancio or random builders are fine for fields the test doesn't care about. Set the fields the behaviour depends on explicitly, so a reader sees why the result follows.

## 16. `@SpringBootTest` for a unit test

```java
// BAD: boots the whole application to test one calculation, every collaborator mocked anyway
@SpringBootTest
class PricingServiceTest {
    @MockitoBean TaxRates taxRates;
    @Autowired PricingService pricing;
    ...
}
```

Seconds instead of milliseconds per class, and each class with a different set of `@MockitoBean`s starts another application context. If everything around the subject is mocked, it's a unit test:

```java
// GOOD
@ExtendWith(MockitoExtension.class)
class PricingServiceTest {
    @Mock TaxRates taxRates;
    PricingService pricing;

    @BeforeEach
    void setUp() { pricing = new PricingService(taxRates); }
}
```

Needs only the web layer: `@WebMvcTest`. Only JPA: `@DataJpaTest`. The whole app: `@SpringBootTest`, shared configuration, few classes.

## 17. Change-detector test

```java
// BAD: restates the implementation line by line; any refactor breaks it, no bug does
verify(mapper).toEntity(command);
verify(repository).save(entity);
verify(mapper).toView(saved);
verify(events).publish(any(OrderPlaced.class));
```

It fails when the code changes, not when the behaviour breaks. Assert the outcome a caller sees (the returned view, the stored row, the published event's content), and verify only calls that change something outside the system.

## 18. The same rule tested at every level

The stock rule tested in the service unit test, again in the controller slice with the service mocked to throw, and again end to end. Three tests to update when the rule changes, and the slice test only proves the mock was set up to throw. Test the rule once in the unit test. The slice tests the mapping of the exception to a status, once. The end-to-end test covers one path through.

## Unwanted tests: delete, don't fix

- Getters, setters, records, Lombok output, `equals` and `hashCode` (unless written by hand with logic)
- DTO mappers that copy fields one to one: the API or service tests cover them
- Constants, enums without behaviour, configuration classes
- Spring Data's derived methods (`findById`, `save`) and that `@Autowired` works
- Private methods reached through reflection: test through the public method, or extract a class
- Tests added only to raise coverage, with weak or no assertions
- An empty `contextLoads` in every test class: keep one smoke test for the application

