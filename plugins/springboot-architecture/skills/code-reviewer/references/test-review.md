# Reviewing Tests

A test suite can be green, long, and full of failure-case names, and still miss the bugs it claims to guard, or fail on correct code. Reading the tests alone doesn't show this. The review below checks what each test can actually catch, and proves every finding by running it.

Smell catalogue with bad and good code: `testing/test-smells.md`. Mechanics and traps at service edges: `testing/distributed-systems.md`.

## Step 1: Map tests to the contract

For each class under test, write down its contract: the Javadoc, API documentation, agreed message formats, and the requirement. Then list each clause and the test that guards it, or "none". Look hardest at clauses about:

- units and formats: cents or decimals, field names in JSON, date formats
- status codes with a special meaning: a 409 that means "already done", a 202
- limits: timeouts, retry counts, sizes
- delivery promises: once only, after commit, never on rollback, in order, poison messages dead-lettered without blocking the rest

An unguarded clause is a finding.

## Step 2: Check that each test runs the real thing it claims to test

A test only guards behaviour that actually runs in it. Common ways it doesn't:

| The test claims to cover | But | So it can't catch |
|--------------------------|-----|-------------------|
| retries (`@Retryable`) | builds the class with `new`, or injects it without the proxy | retries that never happen; on Framework 7.0.9 a JDK proxy on a class implementing an interface never retries |
| a timeout | sets its own `spring.http.clients.read-timeout` | a missing or wrong production timeout |
| a timeout in `@RestClientTest` | doesn't import `HttpClientAutoConfiguration` / `ImperativeHttpClientAutoConfiguration` | any timeout: the slice's client has none |
| publish after commit (`@TransactionalEventListener`) | mocks `KafkaTemplate` in a hand-built context, or one without transaction management | publishing inside the transaction; such tests often fail on correct code |
| a message listener | calls the listener method directly, or mocks the service behind it | duplicate delivery, deserialization failures, dead-lettering, offset handling |
| deserialization of bad messages | sends only valid JSON through the app's own template | a non-JSON record blocking the partition (needs `ErrorHandlingDeserializer`) |
| the request sent to a provider | arranges the value already converted (`3750` instead of `37.50`) | the conversion itself |
| retries on 503 | uses 503 only, with WireMock on the classpath | a dead `@Retryable`: Apache HttpClient retries 503 by itself |
| a database query or constraint | H2, or no `flush()`/`clear()` before reading back | the real SQL |
| full-app behaviour | `@MockitoBean` for everything around the subject | anything: it's a slow unit test |

## Step 3: Check that each test can be trusted

- **Fails on correct code**: wrong expectation, missing infrastructure, order dependence. Run the suite; for every red test, decide whether the test or the code is wrong, from the contract.
- **Racy**: reading a topic with a single `KafkaTestUtils.getRecords` call (returns one batch), sleeps, assertions on timing, shared state between tests. Racy tests pass on one run and fail on the next.
- **Proves nothing**: status-only or `isNotNull()` assertions, verify-only tests, `contextLoads` with no assertions, the expected value computed with the code's own formula.
- **Costly for no gain**: `@SpringBootTest` where a slice or plain unit test sees the same thing; each different `@MockitoBean` set starts another context.

## Step 4: Prove every finding

A finding the review hasn't run is a guess. Before reporting:

- **"Can't catch X"**: break X in the production code (one line), run only the affected test class, show it stays green, restore with `git checkout`. Example: change `@TransactionalEventListener` to `@EventListener`; the publisher tests stay green.
- **"Fails on correct code"**: run it, show the failure, and quote the contract clause that says the code is right.
- **"Racy"**: run the class three times, or show the code path that makes it order-dependent.
- **"Clause not guarded"**: cite the clause and show no test exercises it (`grep` for the method, status code, or field).

Label anything you couldn't run as **unverified** and say why. Leave the code exactly as found.

## Report

Per test class, then a summary:

```markdown
## <TestClass>
- **[Can't catch | Fails on correct code | Racy | Proves nothing | Costly]**: <what>
  - **Evidence**: <what was broken / run, and the result>
  - **Fix**: <the change to the test>

## Contract clauses with no test
- <Class>: "<clause>"

## Summary
- Bugs this suite would let through, most expensive first
- Tests to delete
```
