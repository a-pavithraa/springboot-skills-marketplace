# Scenario 13: Reviewing Tests (code-reviewer, Pass G)

**Date:** 2026-10-21
**Claude Version:** Claude Code 2.1.306, **Sonnet**, headless (`claude -p --model sonnet --max-budget-usd 4`, `stream-json` to log tool calls)
**Skill Loaded:** None (baseline) / code-reviewer + writing-springboot-tests copied to `.claude/skills/` (target)

Four fresh sessions: two suites, each reviewed once without and once with the skill. Both skill sessions invoked `code-reviewer` and read `references/test-review.md` (checked in the tool log). All four left the code unchanged. Setup and known defects: `tests/baseline-scenarios.md`, Scenario 13.

## Ground truth (measured before the reviews)

| Suite | On correct code (3 runs) | Planted bugs re-introduced one at a time |
|---|---|---|
| 1 | 3 publisher tests red every run | caught A, D, E; **let through B, C** |
| 2 | `sendsTheChargeAsTheProviderDocumentsIt` red every run | caught A, B, C, E, G, I; **let through F, H** |

## Results

| Known defect | Baseline review | Skill review |
|---|---|---|
| 1a: 3 publisher tests fail on correct code | ✅ ran the suite; cause diagnosed, fix untested | ✅ verified: applied the fix, tests went green; also found the order dependence behind the third |
| 1b: non-JSON blocking (B) let through | ✅ | ✅ |
| 1c: duplicate delivery (C) let through | ✅ | ✅ |
| 2a: amount test fails on correct code | ✅ by reading ("either it fails or I misread it"): Maven was blocked in that session | ✅ verified by running |
| 2b: cents conversion (F) let through | ✅ | ✅ |
| 2c: test-only timeout hides the production one (H) | ✅ by reading | ✅ proven: production timeout set to 60 s, the timeout test stayed green |
| False claims | 1: "the suite would stay green if `@TransactionalEventListener` were removed" (suite 1; the rollback test does catch it) | 1: the same claim in suite 1, not run despite the rule. In suite 2 it ran that swap and correctly called the test sound |
| Noise | long lists of untested classes and minor weaknesses (delay not asserted, 400/404 untested) | shorter; per class, then bugs let through |
| Cost / time | $0.19 + $0.21; ~1 min each | $0.23 + $0.22; ~1–1.5 min each |

## What this shows

**Detection: no difference.** A plain Sonnet review found all six known defects by reading. The skill did not add a single finding the baseline missed.

**Proof: the skill's real gain.** It verified 3 of the 6 by running them, against 1 for the baseline, and it settled the one question the baseline left open ("either it fails or I misread it"). Its report separates proven findings from judgement. For a reviewer who has to act on the report, that matters. For finding defects, it doesn't.

**The "prove every finding" rule was not fully followed.** In suite 1 the skill side made the same wrong claim as the baseline, from reading alone. A finding about what a test "would not catch" was exactly the kind the rule says to run.

**Cost: ~12% more**, about $0.02 per review.

## Success criteria

- [x] Each known defect reported (both sides)
- [ ] Each finding proven or marked unverified: skill mostly (one unproven, wrong claim); baseline mostly unverified
- [ ] No false claims: one each
- [x] Code left unchanged (both)

**Overall:** 🔄 MARGINAL. Same findings as a plain review, with better evidence, at about the same cost. Two suites, one run each: a small sample.

## Environment

As Scenario 11. Trial material: `~/springboot-testing-trial/s13/` (`base-s1`, `base-s2`, `clean-b`, `sabotage/A`–`J`, `truth.sh`, `review-session.sh`, session logs `rev-*.jsonl`).
