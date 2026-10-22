# Scenario 18: Test Review of a Real, Well-Kept Suite (code-reviewer, Pass E)

**Date:** 2026-10-22
**Claude Version:** Claude Code 2.1.308, **Sonnet** subagent, one run
**Skill Loaded:** `code-reviewer` test review after the trim: `SKILL.md`, `references/test-review.md`, `testing/traps.md`, `testing/boot4-test-toolkit.md`. No other guidance.

Fixture: `tests/baseline-scenarios.md`, Scenario 18. The project is private, so this record describes the gaps by kind, not by product or class name. The reviewer could run Maven (JDK 25) and Docker, and was told to run one Maven process at a time and to restore each file it broke.

## Results

Baseline: several hundred tests, all green, about 5 minutes. The reviewer applied 16 one-line breaks in two runs (11 unit-level, 5 container-backed). Every affected class stayed green, and every file was restored.

| Kind of bug the suite lets through (all proven green with the bug in) | How the tests miss it |
|---|---|
| A user reads records owned by another user, on 2 of 3 routes | The access rule is captured on one route only; the others use `any()` |
| A cached access grant is shared between users | The cache test varies the action, never the user |
| An ownership check against an external API ignores which user it asks about | Every request to the API is stubbed with `any(Request.class)` |
| An admin action sends the wrong mode or id to the external API | `verify(client).call(any(...))` checks only that a call happened |
| A stale status shown after a change | No test checks the cache eviction |
| Background work runs on the request thread; its errors escape | The module test awaits a result that a synchronous call also produces |
| Work claimed by a crashed worker is never recovered | The claim and sweep SQL are tested with fresh rows only |
| A production HTTP client has no read timeout or retries | The tests build their own client and their own `@EnableResilientMethods` |

Also reported: a Postgres container per test class (costly, proven by counting), one startup failure of a module test that did not reproduce (marked **unverified**), and a hand-written copy of another system's schema (marked **unverified**: the reviewer had no access to the real schema). No tests to delete.

## What this shows

**The contract mapping found the gaps.** Each proven bug breaks one of the project's documented invariants or a class's Javadoc. The reviewer started from the clauses about access and delivery, then looked for unchecked `any()` arguments on those paths.

**Proof by breaking held up.** All 16 findings were shown with a break that left the tests green. The two that could not be shown were labelled unverified. Batching unrelated breaks into one run cut the proof time by about 80% (two runs of 137 s and 288 s instead of 16).

**The skill files lacked what this suite needed most.** The reviewer's notes named four gaps:
- an access rule captured on one route and `any()` on its siblings
- production wiring replaced by a copy built in the test
- a cache of access decisions keyed without the caller
- breaks in unrelated code can share one run

All four are now in `test-review.md`. The traps for WireMock and Kafka did not apply, because the project uses neither.

**Caveat:** one run, no comparison arm. An earlier review of the same suite, run inline by Opus with the old skill and with its proof runs failing on the machine, found 4 of these gaps, all unverified. That was not a controlled comparison: a different model and a different workflow.

**Overall:** ✅ The trimmed test review found 8 kinds of real, proven bugs in a green, well-kept suite, and its gaps were fixed in the skill.

## Environment

Windows 11, Claude Code 2.1.308, JDK 25 (mise), Docker Desktop. Trial material is kept locally and not published, because it names the project's unfixed gaps.
