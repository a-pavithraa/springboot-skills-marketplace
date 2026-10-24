# Scenario 22: Comment Density (spring-boot-team-harness `AGENTS.md`, code-reviewer Pass F)

**Date:** 2026-10-24
**Claude Version:** Claude Code 2.1.310, `claude -p --model sonnet`
**Fixture:** a private service, not in this repository. See `tests/baseline-scenarios.md`, Scenario 22.

## Round 1: a rule that banned comments on DTO fields

- **Pruning, 2 runs over 7 files:** 114 comment lines became 38 and 31, with no code changed. Both runs kept the reasons that matter, shortened to a sentence each.
- **What it lost:** the field notes on a record that say when a field is null and that an end date is the planned end until the record closes and the actual end after. The code shows neither. The rule said "not on record and DTO fields", which was too absolute. One run also dropped why a cache key ignores id order.
- **Feature:** too small (one field, one column, one mapping line). No copy added any comments, so it said nothing about density.

## Round 2: the rule as shipped, and a feature that creates new types

**Pruning, 1 run over 10 files:** 173 comment lines became 102 (−41%), with no code changed. The field notes and the cache-key reason were kept.

**Feature, 1 run per copy:**

| Copy | Comment lines added | Code lines added | Comment share |
|---|---|---|---|
| current | 25 | 94 | 21% |
| rule | 19 | 92 | 17% |
| pruned | 12 | 101 | 11% |

All three copies kept the comments that matter: validation happens in the service because bean validation would log the rejected value, the result order, and the audit before the answer. The current copy also wrote comments that restate what a type holds, such as a result record described as the results of the search.

## What this shows

**Agents write comments as densely as the code they read.** On the current copy the share (21%) was close to the codebase's (18%). The rule alone lowered it a little; pruning the code the agent reads halved it.

**A pruning pass is safe to run.** In three runs it changed only comment lines. A field comment is worth keeping when it says what the name can't: when the value is null or empty, or a meaning that depends on state.

**Caveat:** one feature and one or two runs per copy, so treat the numbers as a direction.

**Overall:** ✅ The rule goes in the harness `AGENTS.md`, the pruning pass in `code-reviewer` (Pass F), and the harness skill offers to prune an existing codebase's densest files module by module.

Cost: $1.53 (round 1) and $1.38 (round 2).
