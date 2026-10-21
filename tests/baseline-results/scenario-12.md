# Scenario 12: Pressure on Concerns 1–2, and Edge Bugs the Skill Doesn't Name

**Date:** 2026-10-21
**Claude Version:** Claude Code 2.1.306, **Sonnet**, headless (`claude -p --model sonnet --max-budget-usd 4`)
**Skill Loaded:** None (baseline) / writing-springboot-tests copied to `.claude/skills/` (target)

Same method as Scenario 11: one fresh session per cell, same allowed tools, same plugins (`triage-gate`, `model-fit` off). A planted bug counts as caught when a test is red on the fixture and green with that bug alone fixed. Fixtures are described in `tests/baseline-scenarios.md`, Scenario 12.

---

## Results

### 12a: "Increase test coverage of com.example.orders to at least 80%." (bad house style in the project)

| | Baseline | Skill |
|---|---|---|
| New tests on the full context (`AbstractIntegrationTest` / `@SpringBootTest`) | 0 | 0 |
| Levels | plain JUnit/Mockito, standalone MockMvc for the controller | plain JUnit/Mockito, `@WebMvcTest`, `@RestClientTest` + WireMock |
| Unwanted tests (records, enum, getters, mapper, `contextLoads`) | 0 | 0 |
| Bug J (`> 50` vs "50 or more") | ✅ caught, reported, code left alone | ✅ caught, reported, code left alone |
| Coverage reached (JaCoCo, added by the agent) | ~99% instructions | ~96% lines |
| Gaps it named | `@Retryable` not exercised (gateway built by hand) | Kafka send in the publisher not tested |
| Cost / wall time | $0.37 / 5.8 min | $0.46 / 9.5 min |

### 12b: "Add tests for the payment gateway, the restock listener and the order event publisher." (bugs F–I)

| Planted bug | Baseline | Skill |
|---|---|---|
| F: amount sent as 37.50, not integer cents | ✅ caught | ❌ not caught: its tests pass `3750` into `charge()`, so the conversion is never exercised |
| G: 409 "already captured" treated as a decline | ✅ caught | ✅ caught |
| H: no production read timeout | ✅ caught: its timeout test runs with the production properties | ❌ not caught: it set `read-timeout=500ms` in the test, as the asset does, so the test passes without a production timeout (it noticed the gap in its report) |
| I: event JSON says `amount`, the agreed format says `total` | ✅ caught | ✅ caught |
| Tests failing on correct code | 0 (one apparent failure is a scoring artifact: fixes F and G replace the same file) | 0 |
| Restock listener tested against real Kafka + Postgres | yes (duplicate, poison, unknown product, raw bytes kept in the DLT) | yes (same cases) |
| Cost / wall time | $0.59 / 22.6 min (one 10-minute Kafka run) | $0.57 / 9.8 min |

## What this shows

**Concerns 1 and 2 did not reproduce, even under pressure.** A coverage target and a project whose tests all boot the full application did not push either side into `@SpringBootTest` or into tests of records and getters. With Scenario 11 that makes three prompt pairs without a difference. For Sonnet, the skill's rules for these concerns repeat what it already does.

**On edge bugs the skill doesn't name, the baseline did better: 4 of 4 against 2 of 4.** The baseline read each class's documented contract and turned every clause into a test, including the units of `amount` and the 2-second limit. The skill side followed its asset. Three of its eight gateway test names come from `http-client-wiremock-test.java`, and so does its test-only timeout override. That override is the reason it missed H: the asset shortens the timeout in the test to keep it fast, which also hides a missing production timeout. Its tests also used the asset's arrangement (passing an amount straight to `charge()`), which is how F slipped through.

**Combined with Scenario 11:** the skill helps where it lists a trap (Scenario 11: 4–5 of 5 against 1 of 5 cleanly), and it can hurt where it doesn't, because the agent copies the template's cases and shortcuts instead of deriving cases from the code's own contract.

## Defects in the skill found by this run

- `http-client-wiremock-test.java` overrides `spring.http.clients.read-timeout` in the test. A timeout test must run with the production value (and a stub delay just past it), or a missing production timeout passes.
- The skill gives no instruction to derive edge cases from the documented contract clause by clause. The assets act as the case list.

## Re-run of 12b after fixing the skill

Changes: the HTTP asset's timeout test uses the production timeout (no test override); step 3 derives cases from the documented contract clause by clause, and step 4 says to call code with its callers' values and to take only mechanics from the assets; rules 5, 6, 8, 9 merged into two short rules. The asset was re-verified: 31/31 green, and the timeout test now fails when the production timeout is removed.

| Planted bug | Skill run 2 | Skill run 3 |
|---|---|---|
| F: amount not in cents | ✅ | ✅ |
| G: 409 treated as a decline | ✅ | ✅ |
| H: no production read timeout | ✅ | ✅ |
| I: `amount` vs `total` | ✅ | ✅ |
| Cost / wall time | $0.45 / 3.3 min | $0.54 / 3.6 min |

Both now match the baseline (4 of 4), cheaper and faster than its $0.59 / 22.6 min. (Under "all fixed" one F test stays red in both: fixes F and G replace the same file, a scoring artifact.)

## Success criteria

- [x] 12a: no full-context tests for plain code, no unwanted tests, bug J caught (both sides)
- [x] 12b: all of F–I caught. Baseline yes; skill 2 of 4 before the fix, 4 of 4 in both runs after it

**Overall:** 🔄 NO GAIN, NO LOSS after the fix. No gain on concerns 1–2. On unlisted edge bugs the first version was worse than baseline; the fixed version matches it (2 runs).

## Environment

As Scenario 11. Trial material: `~/springboot-testing-trial/s12/` (`clean/`, `fixture-a/`, `fixture-b/`, sessions, `fixes/F`–`J`, `score.sh`, `run-session.sh`).
