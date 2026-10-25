# Scenario 24: Persistence Fixes on Haiku (spring-data-jpa, retired)

**Date:** 2026-10-25
**Claude Version:** Claude Code, **Haiku** subagents, one fresh agent per side
**Skill Loaded:** None (baseline) / `spring-data-jpa` as of `23a35a4^`, the commit before it was retired (target)

Repeats Scenario 14 on Haiku. The fixture was rebuilt from the Scenario 14 description, on **H2 instead of Postgres** and with Hibernate `ddl-auto` instead of Flyway. It has the same planted problems (P1–P6) and an API test that defines the HTTP contract. A hidden test seeded 200 orders and counted every JDBC statement through a counting `DataSource` proxy. The untouched fixture gives the same counts as in Scenario 14 (482 for the list, 32 for reprice), so the numbers are comparable. Each side could edit the project and run `mvn test`. Prompt: `Optimize the persistence code in this project.`

## Results

| | Fixture | Baseline | Skill |
|---|---|---|---|
| P1 list: statements | 482 | **1** (aggregate query) | **1** (aggregate query) |
| P2 list: items returned | 200 | 200 ❌ (raised as a question, not done) | **20** (page/size, default 20, max 100) |
| P3 get one: statements | 3 | 1 (fetch join) | 2 (two projections) |
| P3 `@ManyToOne` EAGER fixed | ❌ | ✅ `LAZY` | ✅ `LAZY` |
| P4 remove line keeps the product | ❌ product deleted | ✅ cascade removed | ✅ cascade removed |
| P5 reprice: statements | 32 | **1** (bulk update) | 2 (batches of 500, flush and clear) |
| P6 `OrderLineRepository` removed | — | no | no |
| Correct results (hidden test) and existing API tests | ✅ | ✅ | ✅ |
| New tests added | | 4 (product kept, cross-order delete, empty order, rounding) | 0 |
| Subagent tokens | | 67k | 82k |

## What this shows

**One gain: pagination.** Without the skill, Haiku left the list unbounded and asked first, because paging changes the response shape. With the skill, it added `page` and `size`. In Scenario 14 Sonnet paginated either way.

**One loss: reprice.** The skill side walked the catalogue in batches of 500. That is 2 statements here but about 200 at the documented 50,000 products, with every product loaded. The baseline's bulk update stays at 1 statement at any size.

**No other difference.** Both fixed the N+1, the EAGER association and the cascade. Neither removed the repository for the internal entity, the skill's first critical rule, as in Scenario 14.

**Overall:** ❌ NO NET GAIN on Haiku. The retirement holds. To keep the pagination gain without the skill, a line in `code-reviewer/references/jpa-performance.md` could say that a list behind a paged screen takes `Pageable`, even if the response shape changes. One run per side.

## Environment

Linux cloud workspace, Maven 3.9.11, JDK 21 (`java.version` 21 in the fixture instead of 25), H2. Trial material was not kept.
