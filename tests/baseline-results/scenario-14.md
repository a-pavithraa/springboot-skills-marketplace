# Scenario 14: Persistence Fixes (spring-data-jpa)

**Date:** 2026-10-21
**Claude Version:** Claude Code 2.1.306, **Sonnet**, headless (`claude -p --model sonnet --max-budget-usd 4`)
**Skill Loaded:** None (baseline) / spring-data-jpa copied to `.claude/skills/` (target)

One fresh session per side, same allowed tools and plugins as Scenarios 11–13. Fixture and planted problems: `tests/baseline-scenarios.md`, Scenario 14. A hidden test scored each session's code against 200 seeded orders, counting prepared statements with Hibernate `Statistics`.

## Results

| | Fixture | Baseline | Skill |
|---|---|---|---|
| P1 list: statements | 482 | **1** (aggregate query) | **1** (aggregate query) |
| P2 list: items returned | 200 | **20** (page/size, default 20) | **20** (default 20, max 100) |
| P3 get one: statements | 2 | 1 (fetch join) | 1 (fetch join), plus to-one associations set `LAZY` |
| P4 remove line keeps the product | ❌ product deleted | ✅ cascade removed | ✅ cascade removed |
| P5 reprice: statements | 32 | **1** (bulk update) | **1** (bulk update) |
| Correct results (hidden test) and existing API tests | ✅ | ✅ | ✅ |
| P6 `OrderLineRepository` removed | — | no (unused) | no (unused) |
| Cost / wall time | | $0.23 / 16.7 min | $0.25 / 1.2 min |

The baseline's wall time was mostly one long Maven run. Its API time and cost were the same as the skill side's.

## What this shows

**No difference.** Both sides chose the same fixes, and every measured number is identical. The only extra on the skill side was setting the to-one associations to `LAZY`, which the fixture doesn't measure (P3 showed 2 statements either way). Neither removed the repository for the internal entity, which is the skill's first critical rule.

The skill's content is standard JPA guidance that the model already applies. Its few version-specific facts (Jakarta Persistence 3.2 limits on `NEW`, `@ManyToMany` defaults, Hibernate 7 logging properties, Hypersistence module versions) moved to `code-reviewer/references/jpa-performance.md`, and the skill was retired.

**Overall:** ❌ NO GAIN. One run per side.

## Environment

As Scenario 11. Trial material: `~/springboot-testing-trial/s14/` (`fixture/`, `scorer/` with the hidden `ZScoreTest`, `score.sh`, `run-session.sh`, sessions `jpa-base`, `jpa-skill`).
