# Skill trial scenarios

Each scenario gives an agent the same task in fresh sessions, with and without the skill, and scores the result with something an agent can't talk its way past: planted bugs, PIT mutation scores, or Hibernate statement counts. The recorded runs are in `baseline-results/scenario-N.md`. Scenario numbers match those files.

---

## Scenario 10: Tests That Prove Intended Behaviour

**Objective:** Validate that writing-springboot-tests produces tests that encode the requirement, catch planted faults, and use the right Spring Boot 4 level.

### Test Prompt

```
Write tests for OrderService.place(). Orders above the available stock must be
rejected, quantity must be at least 1, and the customer is charged unit price
times quantity.
```

Run it in a project where `place()` has a planted bug: it accepts an order for exactly one more than the available stock (`available + 1 < quantity` instead of `available < quantity`).

### Expected Baseline Behavior

Agent writes tests that pass against the buggy code:
- Reads the implementation and sets expected values from what it returns
- Uses `@SpringBootTest` for a service with no framework behaviour
- Asserts `isNotNull()` or only `verify(repository).save(any())`
- Mocks the domain objects, or spies on the service under test
- Never tests the stock boundary, so the planted bug survives
- Reports "all tests pass"

**Predicted rationalizations:**
- "The tests match the current implementation"
- "Using @SpringBootTest ensures everything is wired correctly"
- "The test failed, so I adjusted the expected value"

### Target Behavior (With Skill)

- Writes the intended behaviour down before any test
- Plain JUnit + Mockito, mocking only the inventory and payment boundaries
- Has a boundary test for stock == quantity and stock + 1
- The boundary test **fails** against the planted bug, and the agent reports it as a likely bug instead of changing the expectation
- Breaks the code once per test and shows each failing
- Exact assertions on total, status, and exception type and message; `verifyNoInteractions(payments)` on rejection

### Pressure Variations

1. "The test is failing, just make it pass"
2. "Use @SpringBootTest, it's simpler"
3. "Don't bother breaking the code, the tests are obviously right"

### Success Criteria

- [ ] At least one test fails against the planted bug, and the agent says why
- [ ] No expected value is computed with the implementation's own formula
- [ ] No `@SpringBootTest` for the service test
- [ ] Sabotage results reported for each test
- [ ] PIT on `OrderService`: no surviving conditional-boundary mutant on the stock check

---

## Scenario 11: The User's Three Concerns (Unwanted Tests, Wrong Level, Service Edges)

**Objective:** Check the three problems writing-springboot-tests was written for: agents adding tests that catch nothing, using `@SpringBootTest` for plain rules, and skipping the integration tests a service needs at its edges.

### Fixture

A Spring Boot 4.1.1 orders service (Postgres, Kafka, an HTTP payment provider) with:
- bait for unwanted tests: records, an enum, a view mapper without logic, Spring Data repositories
- `DiscountPolicy`, a `@Component` with only rules
- five bugs at the edges, each contradicting the class's Javadoc:
  - A: `@Retryable` never retries (JDK proxy, `@EnableResilientMethods` without `proxyTargetClass`)
  - B: no `ErrorHandlingDeserializer`, so one non-JSON message blocks the partition
  - C: redelivered events are applied twice (no idempotency)
  - D: any 200 from the payment provider counts as paid
  - E: `OrderPlaced` is sent with `@EventListener`, so rolled-back orders are announced

### Test Prompts (one fresh session each)

```
P1: Add tests for the orders domain and web code (com.example.orders.domain and com.example.orders.web).
P2: Add tests for DiscountPolicy.
P3: Add tests for the payment gateway, the restock listener and the order event publisher.
```

### Expected Baseline Behavior

- P1: tests for records, mappers, getters, `contextLoads`, repository CRUD
- P2: `@SpringBootTest` for a class that needs no Spring
- P3: the clients and listeners mocked, so none of A–E is caught

### Success Criteria

- [ ] P1: no unwanted tests
- [ ] P2: plain JUnit, no Spring context
- [ ] P3: a test fails on each planted bug and passes once that bug alone is fixed; no test fails on correct code

---

## Scenario 12: Pressure on Concerns 1–2, and Edge Bugs the Skill Doesn't Name

**Objective:** Follow-ups to Scenario 11, which may have been too easy (concerns 1–2) and too close to the skill's own reference (concern 3).

### 12a: Coverage pressure in a project with bad house style

Fixture: the Scenario 11 app with A–E fixed, plus existing tests that model bad style: an `AbstractIntegrationTest` base (`@SpringBootTest` + containers), a "unit" test of `CatalogInventory` through the full context with `@MockitoBean`, a status-only controller test, and `contextLoads`. Planted bug J: `DiscountPolicy` uses `quantity > 50`; its Javadoc says "50 or more".

```
Increase test coverage of com.example.orders to at least 80%.
```

### 12b: Edge bugs not listed in references/distributed-systems.md

Fixture: the same app with A–E fixed, plus four bugs, each against a contract stated in the Javadoc:
- F: the charge sends `amount` as 37.50; the provider's documented API wants integer cents
- G: a 409 ("already captured under this Idempotency-Key") is treated as a decline
- H: no read timeout configured; the Javadoc promises a 2-second limit
- I: the `OrderPlaced` JSON has `amount`; the format agreed with other teams says `total`

```
Add tests for the payment gateway, the restock listener and the order event publisher.
```

### Success Criteria

- [ ] 12a: no new test uses the full context for code that needs none; no unwanted tests; bug J caught
- [ ] 12b: each of F–I caught (red on the fixture, green with that fix alone)

---

## Scenario 13: Reviewing Tests (code-reviewer, Pass E)

**Objective:** Check whether code-reviewer's test review finds known defects in existing suites that a plain review misses, and whether it proves its findings.

### Setup

Two suites from earlier trials, each placed on the **correct** code (all planted bugs fixed), with defects measured beforehand: the suite run 3 times on correct code, then once with each planted bug re-introduced alone.
- Suite 1 (Scenario 11 baseline, edge tests): 3 publisher tests fail on correct code; lets through a non-JSON message blocking the partition (B) and duplicate delivery (C)
- Suite 2 (Scenario 12b, first skill version): one gateway test fails on correct code (passes the pre-converted `3750`); lets through the cents bug (F) and a missing production timeout (H)

### Test Prompt

```
Review the tests in this project: would they catch real bugs, and is anything wrong with them?
Report your findings, and leave the code as you found it.
```

### Success Criteria

- [ ] Each known defect reported
- [ ] Each finding proven by running it, or marked unverified
- [ ] No false claims; code left unchanged

---

## Scenario 14: Persistence Fixes (spring-data-jpa)

**Objective:** Check whether spring-data-jpa changes how an agent fixes the persistence problems it teaches. (The skill was retired after this scenario.)

### Fixture

A Spring Boot 4.1.1 shop (Postgres, Flyway) with an API test defining the HTTP contract, and planted problems:
- P1: N+1 in the order list (lazy customer, two line queries per order, lazy products)
- P2: unbounded order list (Javadoc: thousands of orders, the screen shows 20)
- P3: `@ManyToOne` left EAGER
- P4: `cascade = ALL` from order line to product (removing a line deletes the product)
- P5: reprice loop, `findAll` + `save` per product (Javadoc: ~50,000 products)
- P6: a repository for the internal `OrderLine` entity

Scored by a hidden test: 200 orders, Hibernate `Statistics` statement counts, and correctness checks.

### Test Prompt

```
Optimize the persistence code in this project.
```

---

## Scenario 15: Boot 3.5 → 4 Migration With Silent Hazards (springboot-migration)

**Objective:** Check whether springboot-migration prevents behaviour changes that keep the build green.

### Fixture

A Spring Boot 3.5.16 shop (Postgres, Flyway, RestClient, Spring Retry, Jackson 2) whose tests pass, with hazards that a migration can break silently:
- M1: `flyway-core` without the Flyway starter, and `ddl-auto=update` (on Boot 4 Flyway stops running; Hibernate creates the tables, so the seed data quietly disappears)
- M2: a Jackson 2 `JsonSerializer` for money and a NON_NULL customizer (the JSON format)
- M3: `spring.jackson.parser.allow-comments=true` (renamed in Boot 4)
- M4: Spring Retry `maxAttempts = 4` with `@Recover`, on a class that implements an interface (`maxRetries` counts one fewer; no `@Recover`; the interface-proxy trap)
- Loud controls: `@MockBean` (also inside a `@TestConfiguration`), `TestRestTemplate`, Testcontainers 1.x, relocated imports

The visible tests don't check M1–M4. A hidden scorer, valid on Boot 3.5 and 4.1, checks each one over real HTTP. It passes 10/10 on the original app.

### Test Prompt

```
Upgrade this project to Spring Boot 4.
```

---

## Scenario 16: New Project Without progen (creating-springboot-projects)

**Objective:** Check what creating-springboot-projects changes when an agent creates a new service, on the path users without progen get.

### Test Prompt (one fresh session per side, empty directory with the Maven wrapper)

```
Create a new Spring Boot project in this directory for an order service (base package com.example.orders).
Customers place orders for products; placing an order checks stock and computes a total from its lines; an
order can be cancelled until it ships. Expose a REST API, store data in PostgreSQL. It is a medium-complexity
domain, one team, and will be maintained for several years. Make it buildable and tested.
```

The prompt answers the skill's assessment questions, so headless sessions don't stop to ask.

### Scored

Build and own tests (`./mvnw verify`), Spring Boot and Java versions, Boot 4 starter names, Testcontainers vs H2, test count, ProblemDetail errors, architecture tests, and the Taikai template run on the result (convention-biased: information only).

---

## Scenario 17: Seeded PR Review, Old vs Trimmed Reviewer (code-reviewer)

**Objective:** Check whether the general review passes and triggers cut from `code-reviewer/SKILL.md` (1268 to 735 words) were finding anything.

### Fixture

A Boot 4.1.1 shop (JPA, JdbcClient, method security, `@NullMarked` packages). Branch `feature/admin-and-history` adds 10 files against `main`, with planted issues:
- In the areas the trim removed: a delete route with no `@PreAuthorize` (S1), SQL injection through a `sort` parameter (S2), a card number in a log line (S3), a stack trace in the error response (S4), N+1 in an order history (P1), `findAll()` on about 2 million rows (P2), a controller calling the repository directly (A1), an entity returned with `passwordHash` (A2), `@RequestBody` without `@Valid` (B1)
- Controls, in the areas the trim kept: `@Retryable` with no `@EnableResilientMethods` on a class that implements an interface (K1), `TestRestTemplate` (K2), a Jackson 2 `ObjectMapper` (K3), an override that drops `@Nullable` (K4)

Two arms, two runs each. The arms differ only in `code-reviewer/SKILL.md`; every reference file is the same. The reviewers don't know which arm they are.

### Test Prompt

```
Please review this PR before I merge it.
```

### Scored

Each planted issue counts when the review names it at the right place with a correct reason.

---

## Scenario 18: Test Review of a Real, Well-Kept Suite (code-reviewer, Pass E)

**Objective:** Check whether the trimmed test-review guidance alone leads a reviewer to the gaps in a real suite that is green and carefully written, and whether it proves them.

### Fixture

A private production backend (Spring Boot 4.1.1, Java 25, Testcontainers 2, Postgres): several hundred tests, all green, about 5 minutes. Its docs state the contract as numbered invariants (who may see or change what, audit before sensitive data is returned, background work never blocks a request, recovery by sweeps). Nothing is planted. The gaps are whatever the suite already lets through.

### Test Prompt (fresh agent, given only the four skill files and how to run the build)

```
Review the backend test suite by following the skill's test-review procedure. Report which bugs the suite would let through and which tests can't be trusted, proving each finding by running it.
```

### Scored

Findings proven by a one-line break that leaves the affected classes green, restored afterwards; findings marked unverified; the production tree left clean; and the reviewer's notes on what the skill files lacked.

## Scenario 19: Team Harness, AGENTS.md vs Stop Hook (spring-boot-team-harness)

**Objective:** Find which part of the harness keeps an agent out of the traps the gates catch: the instructions in `AGENTS.md`, the Stop hook, or neither. Then check whether a line in `AGENTS.md` gets the agent to commit in small steps that each build.

### Fixture

A small Spring Boot 4 shop service (one `product` package, an in-memory `ProductCatalog`, a `ProductController`) with the current harness applied and `./mvnw verify` green. Each session runs on its own clone, in one of three arms:

- **none:** `AGENTS.md`, `CLAUDE.md`, `.claude/` and `.agents/` removed. The gates stay in the pom.
- **guide:** everything except the hooks.
- **full:** the harness as applied.

### Test Prompts (`claude -p`, Sonnet, `acceptEdits`, Maven and read-only git allowed)

Each prompt invites one trap:

```
null:  Add a method BigDecimal priceOf(String code) to ProductCatalog that returns the price, or null when the code is unknown. Use it in a new endpoint GET /api/products/{code}/price that returns 404 for unknown codes.
cache: Cache product lookups by code with @Cacheable("products"), and add a priceOf(String code) method on ProductCatalog that uses the cached lookup. Expose it as GET /api/products/{code}/price, 404 when unknown.
print: When a product code is not found, print a line to the console saying which code was asked for, so I can see misses while debugging locally.
```

The commit check uses the full arm on a `feature/discounts` branch, with and without the commit line in "How to work here", and also allows `git add`, `git commit` and `git log`:

```
Add product discounts. Add a Discount record holding a percentage, a method on ProductCatalog that returns the discount for a product code (10% for one existing product, none for the others), a GET /api/products/{code}/final-price endpoint that returns the price after the discount and 404 for unknown codes, and a test for that endpoint.
```

### Scored

By machine, after the session: NullAway errors and `CodeRulesTests` violations from `./mvnw test -Dtest=CodeRulesTests`, whether the Stop hook ran and passed, and cost, turns and time from `--output-format json`. For the commit check: the number of commits, whether each one passes the same command, and code left uncommitted.

## Scenario 20: Fresh-Context Offer (code-reviewer)

**Objective:** Check that `code-reviewer` offers a fresh-context review only when the session reviewing the code also wrote it.

### Fixture

The Scenario 19 shop service with the current harness and `code-reviewer` as a project skill. Subagents are disallowed, so a session can offer one but not start it.

- **wrote:** a clean clone.
- **fresh:** a clone with a finished `priceOf` change already in the working tree.

### Test Prompts (`claude -p`, Sonnet)

```
wrote: Add a method priceOf(String code) to ProductCatalog that returns the price, and a GET /api/products/{code}/price endpoint that returns 404 for unknown codes. When it builds, review your change with the code-reviewer skill.
fresh: Review the uncommitted change in this repository with the code-reviewer skill.
```

### Scored

Whether the final answer offers a fresh-context review and stops, or reviews inline.

## Scenario 21: Checking an Endpoint on the Running App (spring-boot-team-harness, run-app)

**Objective:** Check that after an endpoint change, the agent checks it on the running app with `run-app` without being asked.

`run-app` was later dropped from the harness; see the decision in `baseline-results/scenario-21.md`. The scenario needs commit `4b509bb` to rerun.

### Fixture

The Scenario 19 shop service with the current harness applied fresh, including the `run-app` skill and the `AGENTS.md` line that asks for it. Each session runs on its own port through `RUN_APP_PORT`.

### Test Prompt (`claude -p`, Sonnet, `acceptEdits`, Maven, read-only git and the `run-app` script allowed)

```
Add a GET /api/products/{code}/price endpoint that returns the product price, and 404 for unknown codes.
```

### Scored

From the session transcript: whether the agent ran `run-app.sh start`, called the new endpoint, and ran `stop`; whether anything still listens on the port afterwards; and whether the answer reports the calls.

