---
name: writing-springboot-tests
description: Use when writing tests for Spring Boot 4 code at a service's edges — HTTP clients to other services (WireMock), Kafka/RabbitMQ listeners, events published to other services, full-API tests with Testcontainers — or when a Boot 4 test needs the right imports, slices, or container wiring. Supplies verified Boot 4.1 templates and the framework traps that make such tests pass without proving anything. Not for reviewing existing tests (see code-reviewer) or Boot 3 → 4 test migration (see springboot-migration).
---

# Writing Spring Boot Tests

Use this for tests where the framework, not the logic, decides whether the test proves anything: calls and messages between services, retries, timeouts, transactions, and Boot 4 test wiring. For plain unit tests you need nothing here beyond the three rules.

## Rules

1. **Cases come from the contract, clause by clause.** Every sentence of the Javadoc, the provider's API documentation, or an agreed message format is a case: units and formats (cents or decimals, field names), status codes with a special meaning (a 409 that means "already done"), headers, time limits, delivery promises (once only, after commit, poison messages dead-lettered). Call the code the way its callers do, with their values, so conversions run.
2. **Run the real thing at the edge.** Real HTTP (WireMock), the real broker and database (Testcontainers), real transactions. A mocked client, template, or transaction manager can't show timeouts, retries, redelivery, or publish-after-commit. Timeout tests use the **production** timeout value.
3. **Show each test failing once, and treat a failing test as a finding.** Break the guarded line and watch the test go red (PIT for classes with logic). If a test fails on the current code, report it with the contract clause; never weaken the assertion.

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
| Web slice, persistence slice, service unit test | `assets/webmvc-slice-test.java`, `assets/repository-slice-test.java`, `assets/service-unit-test.java` |
| Shared containers; PIT | `assets/testcontainers-configuration.java`, `assets/pitest-plugin.xml` |

## Report

List the tests added (behavior and level), how each was shown to fail, tests that fail on the current code with the contract clause they rely on, and contract clauses left untested.

## Evidence

Trials on Sonnet (`tests/baseline-results/scenario-11.md` to `scenario-13.md`): general testing guidance made no difference, so it was removed. The traps and the real-infrastructure rule made the difference at service edges. Copying a template's cases instead of the contract made things worse, which is why rule 1 exists.
