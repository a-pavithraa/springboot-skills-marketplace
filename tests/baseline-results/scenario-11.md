# Scenario 11: The User's Three Concerns

**Date:** 2026-10-21
**Claude Version:** Claude Code 2.1.306, **Sonnet**, headless (`claude -p --model sonnet --max-budget-usd 4`)
**Skill Loaded:** None (baseline) / writing-springboot-tests copied to `.claude/skills/` (target)

Six fresh sessions: three prompts, each run once without and once with the skill, on identical copies of a Spring Boot 4.1.1 orders service (fixture and planted bugs in `tests/baseline-scenarios.md`, Scenario 11). Same allowed tools as Scenario 10. Both sides had the same user plugins; `triage-gate` and `model-fit` were switched off.

Scoring, objective where possible:

- P1, P2: the suite run on the fixture, PIT (`ALL` mutators) on the classes under test, and a read of every test method for unwanted tests and Spring usage
- P3: the session's tests run on the fixture, then with each planted bug fixed alone, then with all fixed. A bug counts as caught when a test is red on the fixture and green with that fix

---

## Results

### P1: "Add tests for the orders domain and web code" (concern 1: unwanted tests)

| | Baseline | Skill |
|---|---|---|
| Tests | 19, all pass | 26, all pass |
| Unwanted tests (records, enum, mapper, getters, `contextLoads`, repository CRUD) | 0 | 0 |
| Levels | Mockito for the service, `@WebMvcTest` for the controller | same |
| PIT, `OrderService` + `DiscountPolicy` (80 mutants) | 78 | 79 |
| Survivors | `quantity < 1` boundary (no test that quantity 1 is accepted) | `UUID.toString()` removed (irrelevant) |
| Ran its own tests | no: tried `mvn test`, which the allowed tools didn't include | yes, and broke 4 lines by hand |
| Cost / time | $0.26 / 1.0 min | $0.44 / 2.6 min |

### P2: "Add tests for DiscountPolicy" (concern 2: `@SpringBootTest` for rules)

| | Baseline | Skill |
|---|---|---|
| Spring context | none: plain JUnit | none: plain JUnit |
| Boundaries tested | 1, 9, 10, 49, 50, 500 | 1, 9, 10, 49, 50, 500 + HALF_UP vs HALF_EVEN |
| PIT (24 mutants) | 24 | 24 |
| Proof | none | 4 hand sabotages, each red |
| Cost / time | $0.10 / 0.5 min | $0.21 / 1.5 min |

### P3: "Add tests for the payment gateway, the restock listener and the order event publisher" (concern 3: service edges)

| Planted bug | Baseline | Skill |
|---|---|---|
| A: `@Retryable` never retries | ✅ caught (3 tests) | ✅ caught (2 tests) |
| B: non-JSON message blocks the partition | ❌ no test ("needs an embedded broker") | ⚠️ test red on the bug, but its dead-letter read is racy, so it also failed with the fix |
| C: redelivery applied twice | ❌ no test (named in the report) | ✅ caught |
| D: any 200 counts as paid | ⚠️ caught only with A also fixed: the tests expect retries | ✅ caught |
| E: event sent for rolled-back orders | ⚠️ 1 test catches it, but 3 tests fail on the correct code | ✅ caught |
| Tests failing on correct code (all five fixed) | 3 | 1 (the racy one) |
| HTTP stub | `MockRestServiceServer` | WireMock, real HTTP |
| Broker and database | none: Kafka mocked, a hand-made transaction manager | Kafka + Postgres in containers |
| Bugs named in the final report | 4 of 5 (A, C, D, E) | 5 of 5 |
| Cost / time | $0.72 / 5.5 min | $0.51 / 3.3 min |

## What this shows

**Concerns 1 and 2 did not reproduce with Sonnet on this code.** Neither side wrote a single unwanted test or booted Spring for a rules class. The skill side was slightly more thorough (one more boundary, self-run sabotage) at about twice the cost. On these prompts the baseline already behaves as the skill asks.

**Concern 3 did reproduce, and the skill fixed most of it.** The baseline tested the edges with mocks: `MockRestServiceServer` for HTTP, a mocked `KafkaTemplate`, and a hand-built transaction manager. That caught the in-process bugs (A, D, E) but none of the ones that need a real broker (B, C). Its publisher tests built a context without transaction support, so 3 of them fail on correct code and would tell a developer the right fix is wrong. The skill side tested against real HTTP and containers, caught four bugs cleanly and the fifth with a flawed assertion. It was also cheaper and faster, because it didn't spend turns building mock infrastructure.

**Caveat: the fixture's bugs come from the skill's own reference.** A–E are the traps listed in `references/distributed-systems.md`, found while building its assets. This run shows the skill passes on what it teaches. It does not show it finds edge bugs it doesn't list. A fairer test needs edge bugs the reference doesn't name.

**The trial found a defect in the skill.** The racy dead-letter read was copied from `assets/message-listener-test.java`, which had passed by luck. Fixed: the asset now polls into a list until the record appears (3 stable runs, still red when the deserializer is sabotaged), and the reference explains why.

## Success criteria

- [x] P1: no unwanted tests (both sides)
- [x] P2: plain JUnit, no Spring context (both sides)
- [ ] P3: every planted bug caught cleanly, nothing red on correct code. Skill: 4 of 5 clean, 1 racy (cause fixed in the asset). Baseline: 1 of 5 clean

**Overall:** 🔄 PARTIALLY EFFECTIVE. Clear gain at service edges (concern 3), where the baseline mocks what it should run. No measurable gain on concerns 1 and 2 with Sonnet: the baseline already avoids those mistakes on these prompts.

## Follow-up

- [x] Fix the racy dead-letter read in `message-listener-test.java`
- [ ] Re-run P3 on a fixture with edge bugs the reference doesn't list (e.g. missing timeout on a second client, consumer committing before the database write, wrong partition key)
- [ ] Concerns 1 and 2 under pressure: "get coverage to 80%", "add tests for everything in this package", or a project whose existing tests already use `@SpringBootTest` everywhere
- [ ] One run per cell is a small sample: repeat P3 to see the variance

## Environment

- macOS, JDK 27 (compiled for Java 25), Maven wrapper, Docker Desktop 29.8.2
- Spring Boot 4.1.1, Testcontainers 2.0.5, Kafka `apache/kafka-native:4.1.1`, Postgres 18, pitest-maven 1.30.1
- Trial material: `~/springboot-testing-trial/scenario-11-fixture` (fixture), `~/springboot-testing-trial/s11/` (sessions, `fixes/A`–`E`, `score.sh`)
