# Scenario 17: Seeded PR Review, Old vs Trimmed Reviewer (code-reviewer)

**Date:** 2026-10-22
**Claude Version:** Claude Code 2.1.308, **Sonnet** subagents, one fresh agent per run
**Skill Loaded:** arm A: `code-reviewer/SKILL.md` as of commit `0be0bbb` (1268 words). Arm B: the trimmed `SKILL.md` (735 words). Both arms had the same references.

Fixture and planted issues: `tests/baseline-scenarios.md`, Scenario 17. The reviewers could read the repo and the skill folder only, and could not run Maven.

## Results

| Issue | A run 1 | A run 2 | B run 1 | B run 2 |
|---|---|---|---|---|
| S1 delete without `@PreAuthorize` | ✅ | ✅ | ✅ | ✅ |
| S2 SQL injection through `sort` | ✅ | ✅ | ✅ | ✅ |
| S3 card number logged | ✅ | ✅ | ✅ | ✅ |
| S4 stack trace in the response | ✅ | ✅ | ✅ | ✅ |
| P1 N+1 | ✅ | ✅ | ✅ | ✅ |
| P2 unbounded `findAll()` | ✅ | ✅ | ✅ | ✅ |
| A1 controller calls the repository | ✅ | ✅ | ✅ | ✅ |
| A2 entity with `passwordHash` returned | ✅ | ✅ | ✅ | ✅ |
| B1 missing `@Valid` | ✅ | ✅ | ✅ | ✅ |
| K1 `@Retryable` never applies | ✅ | ✅ | ✅ | ✅ |
| K2 `TestRestTemplate` | ✅ | ✅ | ✅ | ✅ |
| K3 Jackson 2 `ObjectMapper` | ✅ | ✅ | ✅ | ✅ |
| K4 override drops `@Nullable` | ✅ | ✅ | ✅ | ✅ |
| Unplanted: a new idempotency key per request allows a double refund | ✅ | ✅ | ✅ | ✅ |
| Findings in total | 18 | 16 | 20 | 17 |

## What this shows

**The cut text found nothing extra.** Both arms found all 13 planted issues in every run, so the general passes and the security, performance and architecture triggers did not change what Sonnet reports. This matches Scenarios 11–15: Sonnet finds general problems without being told to look.

**The trial cannot rank the arms.** Both scored the maximum. A harder fixture would be needed to show whether the shorter skill is better, not only no worse. No run without the skill was made, so this scenario says nothing about the Boot 4 triggers that both arms kept.

**Gap found: the migration scanner missed the Jackson 2 import.** Arm B's Pass A runs the scanner, and it reported 0 CRITICAL issues. It flagged `TestRestTemplate` and `@Retryable` only as warnings, and had no check for `com.fasterxml.jackson.databind` imports. The reviewers caught K3 by reading the code. The scanner now reports Jackson 2 `databind` and `core` imports as CRITICAL.

**Overall:** ✅ NO LOSS from the trim, at 42% fewer words in `SKILL.md`.

## Environment

Windows 11, Claude Code 2.1.308. Trial material: `~/springboot-testing-trial/s17/` (`fixture/` git repo, `key.md`, `arm-a-SKILL.md`, `arm-b-SKILL.md`, `reviews/a1.md` to `b2.md`).
