# Scenario 23: Seeded PR Review on Haiku (code-reviewer)

**Date:** 2026-10-24
**Claude Version:** Claude Code, **Haiku** subagents, one fresh agent per run
**Skill Loaded:** arm A: `code-reviewer/SKILL.md` as of commit `0be0bbb` (1265 words). Arm B: `SKILL.md` on `main` (968 words). Arm C: no skill. Arms A and B had the same `references/`.

Repeats Scenario 17 on Haiku and adds a no-skill arm. The fixture was rebuilt from the Scenario 17 description (Boot 4.1.1, JPA, JdbcClient, method security, `@NullMarked` packages; branch `feature/admin-and-history` adds 10 files with S1–S4, P1–P2, A1–A2, B1 and K1–K4 planted). It is not the original fixture. The reviewers could read the repo and the skill folder only, and could not run Maven. Prompt: `Please review this PR before I merge it.`

## Results

| Issue | A (old) | B (trimmed) | C (no skill) |
|---|---|---|---|
| S1 delete without `@PreAuthorize` | ✅ | ✅ | ✅ |
| S2 SQL injection through `sort` | ✅ | ✅ | ✅ |
| S3 card number logged | ✅ | ✅ | ✅ |
| S4 stack trace in the response | ✅ | ✅ | ✅ |
| P1 N+1 | ✅ | ✅ | ✅ |
| P2 unbounded `findAll()` | ✅ | ✅ | ✅ |
| A1 controller calls the repository | ✅ | ✅ | ❌ |
| A2 entity with `passwordHash` returned | ✅ | ✅ | ✅ |
| B1 missing `@Valid` | ✅ | ✅ | ❌ |
| K1 `@Retryable` never applies | ✅ | ✅ | ✅ |
| K2 `TestRestTemplate` | ✅ | ✅ | ❌ |
| K3 Jackson 2 `ObjectMapper` | ✅ | ✅ | ❌ (flagged as style only, not as Jackson 2) |
| K4 override drops `@Nullable` | ✅ | ✅ | ✅ (as an NPE, not as the contract) |
| Unplanted: a new idempotency key per retry allows a double refund | ✅ | ✅ | ✅ |
| Planted issues found | 13/13 | 13/13 | 9/13 |
| Subagent tokens | 103k | 112k | 67k |

K1 in A and B also named `proxyTargetClass = true`, because `RefundService` implements an interface. C noted only that `@EnableResilientMethods` is missing.

## What this shows

**The trim holds on Haiku.** Arms A and B found the same 13 issues. The cut text was not doing the work on the smaller model either.

**The kept Boot 4 content earns its place.** This is the first run without the skill. Haiku without it missed K2 and K3, the Boot 4 changes, which Scenario 17 could not test.

**The review passes still matter on Haiku.** Unlike Sonnet in Scenario 17, Haiku without the skill missed A1 and B1. The trimmed `SKILL.md` recovered both, so the pass structure helps a smaller model even without the removed checklists.

**The trial cannot rank A and B.** Both scored the maximum.

**Gap found:** given only the `code-reviewer` folder, arm B's Pass A could not find `../springboot-migration/scripts/scan_migration_issues.py`. A full plugin install has it. A manual copy of one skill folder does not.

**Overall:** ✅ NO LOSS from the trim on Haiku; ✅ GAIN from the skill against no skill (13 vs 9). One run per arm.

## Environment

Linux cloud workspace. Trial material was not kept.
