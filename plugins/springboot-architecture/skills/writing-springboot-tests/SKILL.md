---
name: writing-springboot-tests
description: "Use when writing or adding tests for Spring Boot code at a service's edges: HTTP clients that call other services (WireMock: 4xx and 5xx responses, timeouts, retries), Kafka or RabbitMQ listeners (redelivery, poison messages, dead-letter topics), events published to other services, or full-API tests against real databases with Testcontainers; also when a Boot 4 test needs the right imports, slices or container wiring. Supplies verified Boot 4.1 templates and the framework traps that make such tests pass without proving anything. Not for reviewing existing tests (see code-reviewer) or Boot 3 to 4 test migration (see springboot-migration)."
---

# Writing Spring Boot Tests

Use this for tests where the framework, not the logic, decides whether the test proves anything: calls and messages between services, retries, timeouts, transactions, and Boot 4 test wiring. For plain unit tests you need nothing here beyond the three rules.

## Rules

1. **Cases come from the contract, clause by clause.** Every sentence of the Javadoc, the provider's API documentation, or an agreed message format is a case: units and formats (cents or decimals, field names), status codes with a special meaning (a 409 that means "already done"), headers, time limits, delivery promises (once only, after commit, poison messages dead-lettered). Call the code the way its callers do, with their values, so conversions run.
2. **Run the real thing at the edge.** Real HTTP (WireMock), the real broker and database (Testcontainers), real transactions. A mocked client, template, or transaction manager can't show timeouts, retries, redelivery, or publish-after-commit. Timeout tests use the **production** timeout value. Build the client the way production does (its bean, or its builder settings) and point it at the stub. If the client can't be pointed elsewhere, make its base URL or endpoint configurable: that improves the design. If it has no timeout at all, report that as a finding instead of skipping the test. AWS SDK clients count: see `traps.md`.
3. **Show each test failing once, and treat a failing test as a finding.** Break the guarded line and watch the test go red (PIT for classes with logic). If a test fails on the current code, report it with the contract clause; never weaken the assertion.
4. **Test through what the code does, not its internals.** Assert on results, stored rows, sent messages, and calls to other services. Don't widen a method's visibility, or add a getter, counter or flag that only a test uses: `UnusedCodeTests` fails on a method only tests call. Changing the code for a test is right when it also improves the design, such as taking a `Clock` or a client through the constructor instead of creating it.

## Before writing

Read `../code-reviewer/references/testing/traps.md`: the Boot 4.1 / Framework 7 / Spring Kafka 4 traps found by running these templates (`@Retryable` behind an interface proxy, `@RestClientTest` ignoring timeouts, Apache HttpClient retrying 503, blocked partitions, corrupted dead letters, single-batch topic reads), and the Testcontainers and test-data traps.

Imports, starters and PIT: `../code-reviewer/references/testing/boot4-test-toolkit.md`.

## Templates

Verified on Spring Boot 4.1.1 with Postgres 18, Kafka 4.1 and WireMock 3.13. Take the mechanics (annotations, wiring, stubbing, polling) from them; take the cases from rule 1, not from the template.

| Edge | Template |
|------|----------|
| Outbound HTTP client: request, 4xx, 5xx, retries, timeout, unusable answers | `assets/http-client-wiremock-test.java` |
| Message listener: state change, redelivery, poison and non-JSON messages | `assets/message-listener-test.java` |
| Event other services consume: after commit, never on rollback | `assets/event-publication-test.java` |
| The whole service over HTTP, other services stubbed | `assets/api-integration-test.java` |
| Secured routes: signing in as a named user through the app's own role mapping (session OIDC login, JWT bearer, or database users); who may call each route | `assets/personas-oidc.java`, `assets/personas-jwt.java` or `assets/personas-db.java`; `assets/route-access-test.java` |
| Web slice, persistence slice, service unit test | `assets/webmvc-slice-test.java`, `assets/repository-slice-test.java`, `assets/service-unit-test.java` |
| Shared containers; PIT | `assets/testcontainers-configuration.java`, `assets/pitest-plugin.xml` |

## Secured routes

Spring's test logins skip the app's own role mapping. `oidcLogin().authorities(...)`, `jwt().authorities(...)` and `user(...).roles(...)` hand the test a finished role. A test that signs in this way passes even when the code that turns the provider's claims, or the stored user, into roles is broken. Sign in through a persona instead, so that code runs:

```java
.with(oidcLogin().authorities(new SimpleGrantedAuthority("ROLE_ADMIN")))  // the role mapping never runs
.with(personas.as("admin"))                                                // the app's mapping produces the role
```

Copy the helper that matches how the app signs users in: `personas-oidc.java` for an OIDC login kept in a server-side session, `personas-jwt.java` for JWT bearer tokens, or `personas-db.java` for users loaded by a `UserDetailsService`. A persona is the claims the provider sends, or the username of a seeded user. The helper needs the app's mapper, `JwtAuthenticationConverter` or `UserDetailsService` as a bean.

`route-access-test.java` lists who may call each route. It calls every route as every persona and with no login, and it fails when a route is missing from the list. It checks roles, not records. Whether one user can read another user's data needs a test with two users. A request on a random port can't sign in through a persona, so test secured routes through `@AutoConfigureMockMvc`.

## Report

List the tests added (behavior and level), how each was shown to fail, tests that fail on the current code with the contract clause they rely on, and contract clauses left untested.
