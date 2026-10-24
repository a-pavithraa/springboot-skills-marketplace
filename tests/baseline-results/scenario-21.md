# Scenario 21: Checking an Endpoint on the Running App (spring-boot-team-harness, run-app)

**Date:** 2026-10-24
**Claude Version:** Claude Code 2.1.310, `claude -p --model sonnet`, two runs
**Skill Loaded:** none named in the prompt. Fixture and prompt: `tests/baseline-scenarios.md`, Scenario 21.

## Results

| Run | Started the app | Calls | Stopped it | Left running | Reported | Cost | Time |
|---|---|---|---|---|---|---|---|
| 1 | ✅ | `GET /api/products/P-1/price` 200 `19.99`; `GET /api/products/NOPE/price` 404 | ✅ | no | ✅ | $0.11 | 170 s |
| 2 | ✅ | the same two calls, same results | ✅ | no | ✅ as a table | $0.13 | 166 s |

Both sessions also wrote tests for the endpoint and ran `./mvnw verify` before calling the app.

## What this shows

**One line in `AGENTS.md` was enough.** Neither prompt mentioned the skill. Both agents checked the case they built and the case the endpoint must refuse, which is what the skill asks for, and stopped the app afterwards.

**Caveat:** two runs, one model, one public endpoint. The token and session-cookie options were not tried against a secured endpoint.

**Overall:** ✅ After an endpoint change, the agent checks it on the running app and cleans up.
