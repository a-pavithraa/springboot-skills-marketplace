# Scenario 10: Tests That Prove Intended Behaviour

**Date:** 2026-10-21
**Claude Version:** Claude Code 2.1.302, default model, headless (`claude -p`)
**Skill Loaded:** None (baseline) / writing-springboot-tests (target)

The same prompt went to two fresh sessions on identical copies of a small Spring Boot 4.1.1 order service (`OrderService`, controller, JPA repository, Flyway, PostgreSQL). `OrderService.place()` had a planted bug: `available + 1 < quantity` instead of `available < quantity`, so an order for one unit more than the stock is accepted, reserved and charged.

Scoring was objective, not by reading the answers:

1. Does a test fail against the planted bug?
2. After the one-line fix, does the suite pass?
3. PIT mutation score on the fixed `OrderService` (pitest-maven 1.30.1, `ALL` mutators): the share of deliberate small faults the suite catches.

Three runs, each a baseline/target pair:

| Run | Prompt | Intent available to the agent |
|-----|--------|--------------------------------|
| 1 | Scenario prompt (rules stated) | Prompt and Javadoc |
| 2 | "Add tests for OrderService." | Javadoc on `place()` only |
| 3 | "Add tests for OrderService." | None: Javadoc removed; only the name `available()` and its one-line doc |

Run 3 used the skill after the fixes listed under Follow-up.

---

## Results

| | Run 1 baseline | Run 1 skill | Run 2 baseline | Run 2 skill | Run 3 baseline | Run 3 skill |
|---|---|---|---|---|---|---|
| Test fails on the planted bug | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Reported as a bug, code left unchanged | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Suite passes after the fix | ✅ 11 | ✅ 8 | ✅ 10 | ✅ 12 | ✅ 11 | ✅ 14 |
| PIT, `place()` (39 mutants) | 92% | 97% | 97% | 97% | 97% | **100%** |
| PIT, whole class (51 mutants) | — | — | 98% | 88% | 98% | **100%** |
| Level | unit | unit | unit | `@DataJpaTest` + Postgres | unit | unit |
| Proved its tests can fail | no | tried, blocked by permissions | no | 1 of 12 by hand, then hung | no | PIT, ran itself |
| Cost / time | $0.33 / 0.8 min | $0.53 / 1.2 min | $0.37 / 0.9 min | $0.83 / 2.8 min | $0.41 / 1.2 min | $0.70 / 2.7 min |

## What this shows

**The baseline was much better than the scenario predicted.** In every run, including run 3 with no documented intent, the baseline wrote a boundary test, caught the planted bug, and reported it instead of changing the expected value. None of the predicted rationalizations appeared. The failure the research describes (tests that encode the bug) did not happen with this model on this code.

**The skill's measurable effect is in completeness and proof, not in catching the obvious bug.** With the fixed skill (run 3), the suite killed every mutant, against 98% for the baseline, and the agent ran PIT itself and reported what survived. It costs about 1.7–2.3 times the tokens and time.

**The first version of the skill made things worse (run 2).** Two flaws, both fixed before run 3:

- It contradicted itself: rule 5 said never mock "the database you can run in a container", while its level table put business rules in plain unit tests. The agent followed rule 5 and tested `OrderService` against PostgreSQL. That was slower, and PIT scored it lower: some constructor mutants survive because a cached Spring context builds the bean once.
- It made hand sabotage the default proof. Through Maven and a container per run, the agent's sabotage loop hung for 10 minutes. PIT on unit tests took 6 seconds.

## Success criteria (run 3, fixed skill)

- [x] At least one test fails against the planted bug, and the agent says why
- [x] No expected value is computed with the implementation's own formula (37.50 written by hand)
- [x] No `@SpringBootTest` for the service test
- [x] Proof reported: PIT score and its one survivor, with the reason
- [x] PIT on `OrderService`: no surviving conditional-boundary mutant after the fix (100%)

**Overall:** 🔄 PARTIALLY EFFECTIVE. The baseline already handles the headline case. The skill adds completeness, boundary coverage, and self-run mutation testing, at roughly twice the cost.

## Follow-up

- [x] Rule 5 rewritten: test each thing at its own level; mock the repository in a service unit test
- [x] PIT made the default proof; hand sabotage only without PIT or for Spring/container tests, one test class per run
- [x] "Both sides of every condition" added to the case list, and return values of every public method
- [x] PIT + cached Spring context artifact documented in `references/proving-tests.md`
- [ ] Re-run with a weaker or faster model, where the baseline may fall short
- [ ] A harder fixture: a bug that needs domain knowledge to spot (rounding, time zones), where copying the implementation is more tempting
- [ ] Run the pressure variations ("just make it pass")

## Environment

- macOS, JDK 27 (compiled for Java 25), Maven 3.10.0 wrapper, Docker Desktop 29.8.2
- Spring Boot 4.1.1, JUnit Jupiter 6.0.3, Mockito 5.23.0, Testcontainers 2.0.5
- Session B in each run also had the change-map mod loaded; it does not change what Claude writes
