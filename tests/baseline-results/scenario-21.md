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

## Decision: dropped before release

`run-app` was removed from the harness, and `AGENTS.md` asks for a full-API test instead.

- **It found nothing the tests missed.** Both sessions had already written tests and run `./mvnw verify` before they started the app.
- **It can't reach most team endpoints.** In the two real applications it was tried against, sign-in goes through an Entra BFF with in-memory sessions. A new instance has no session, and Entra accepts sign-ins only on the registered ports. Only health checks and public routes answered.
- **It can have side effects.** The local profile talks to real external services, so a checked POST can create real records. A full-API test runs against containers and WireMock.
- **A full-API test is the standard practice and does the same job.** It starts the whole app on a real port, signs in with a test user or token, runs in CI and stays in the repository.

The script and skill are in commit `4b509bb` if a service turns up where checking on the running app catches what tests don't. For applications checked through their UI, browser tests (Playwright) fill this role.
