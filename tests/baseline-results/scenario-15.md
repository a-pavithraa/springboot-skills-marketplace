# Scenario 15: Boot 3.5 → 4 Migration With Silent Hazards (springboot-migration)

**Date:** 2026-10-21
**Claude Version:** Claude Code 2.1.306, **Sonnet**, headless (`claude -p --model sonnet --max-budget-usd 4`, `stream-json`)
**Skill Loaded:** None (baseline) / the plugin's skills copied to `.claude/skills/` (target; it invoked `springboot-migration`, ran its scanner and read the Boot 4 reference)

Fixture and hazards: `tests/baseline-scenarios.md`, Scenario 15. Both sessions could run `./mvnw` and `python3`. The scorer ran outside the sessions, so it could download any Boot version.

## Results

| Hazard (checked on Boot 4) | Baseline as delivered (4.0.0) | Skill (4.1.1) | Baseline bumped to 4.1.1 |
|---|---|---|---|
| M1 Flyway runs and seeds | ✅ | ✅ | ❌ context fails to start |
| M2 money "12.50 EUR", no null fields | ✅ | ✅ | ❌ |
| M3 JSON with comments accepted | ✅ | ✅ | ❌ |
| M4 4 attempts then 1:1 fallback; recovers after 2 failures | ✅ | ✅ | ❌ |
| Own tests + hidden scorer | 10/10 | 10/10 | 3/10 (7 errors) |
| Built and tested in the session | no: chose 4.0.0 from memory, which wasn't cached, and the session couldn't download it; it reported the work as unverified | yes: `./mvnw clean verify` green | — |
| Cost / time | $0.36 / 2.3 min | $0.41 / 2.0 min | |

Both moved `@Retryable` from the interface-implementing provider to the client class. That keeps retries working (and the skill side named self-invocation as its reason). Both translated `maxAttempts = 4` to `maxRetries = 3`, replaced `@Recover` with a catch in the caller, renamed the Jackson property, and moved Flyway to its starter.

## What this shows

**Silent hazards: no difference.** Sonnet already knows the Boot 4 changes behind M1–M4 well enough to keep behaviour intact.

**Version and completeness: a real but narrow gain.** The skill targeted the current release and a dependency set that works on it. The baseline's migration is correct for 4.0.0 but misses `spring-boot-starter-restclient`, so it fails at startup on 4.1. That fails loudly, but it would block the next upgrade. The skill side also finished with a verified build.

**Caveat:** the baseline couldn't build only because its session couldn't download 4.0.0. On a normal machine it would have verified a 4.0.0 migration. One run per side.

**Overall:** 🔄 SMALL GAIN: current target version, complete dependencies, verified result, at about the same cost (+14%).

## Note on the first scoring

The first scorer replaced `RateClient` with a `@MockitoBean`. Both migrations had moved `@Retryable` onto `RateClient`, and a mock isn't proxied, so it reported "1 call, no retries" for both. That was a scorer artifact. The final scorer stubs the rates service over real HTTP and was re-validated on Boot 3.5 (10/10).

## Environment

As Scenario 11. Trial material: `~/springboot-testing-trial/s15/` (`fixture/` on Boot 3.5.16, `scorer/`, `score.sh`, `run-session.sh`, sessions `mig-base`, `mig-skill`, `mig-base-411`).
