# Scenario 16: New Project Without progen (creating-springboot-projects)

**Date:** 2026-10-21
**Claude Version:** Claude Code 2.1.306, **Sonnet**, headless (`claude -p --model sonnet --max-budget-usd 4`, `stream-json`)
**Skill Loaded:** None (baseline) / the plugin's skills in `.claude/skills/` (target; it invoked `creating-springboot-projects` and read `references/architecture-guide.md`). progen was not installed, so the skill used its fallback path.

## Results

| | Baseline | Skill |
|---|---|---|
| Spring Boot / Java | **3.5.7 / 21** ("couldn't check whether that is the newest release") | **4.1.1 / 25** |
| Starters | Boot 3 names (`starter-web`, `starter-test`) | Boot 4 names (`starter-webmvc`, `starter-flyway`, `starter-webmvc-test`) |
| `./mvnw verify` | ✅ 18 tests | ✅ 15 tests |
| Database in tests | Testcontainers Postgres; it had to pin Testcontainers 1.21.4, because Boot 3.5's 1.21.3 couldn't talk to Docker Desktop 29 | Testcontainers 2 (Boot 4's), no override |
| Concurrency | single guarded stock update + test with 20 parallel orders | single guarded stock update + concurrent-order test |
| Layout | packages per feature plus a separate `web` package | package-by-module; only `CatalogApi` public in `catalog` |
| Errors | ProblemDetail (400/404/409/422) | ProblemDetail (400/404/409) |
| Architecture tests | none | none (the Taikai template is listed but wasn't used) |
| Taikai template on the result (information only) | 5 convention findings: public entities, no `@Version` | 1: a `@Transactional` method calling another in the same class (harmless here) |
| Cost / time | $0.62 / 5.5 min | $0.57 / 3.2 min |

## What this shows

**The baseline started a new project on the previous major version.** Every other quality is close: both designs are careful about concurrent stock updates, use the real database in tests, and return ProblemDetail errors. But the baseline's service starts life needing the Boot 4 migration from Scenario 15, and it already had to work around a Testcontainers 1.x incompatibility with current Docker.

The skill's gain is current-stack knowledge (version, starter names, Testcontainers 2), and a clearer module boundary. It was cheaper and faster too.

**The architecture test wasn't picked up.** The skill side wrote everything from scratch and never opened the asset list. If enforced architecture rules matter, SKILL.md's workflow needs a step that adds the Taikai test, not only a line in the template list.

**Overall:** ✅ EFFECTIVE on version currency. One run per side.

## Environment

As Scenario 11. Trial material: `~/springboot-testing-trial/s16/` (`run-session.sh`, `score.sh`, sessions `new-base`, `new-skill`).
