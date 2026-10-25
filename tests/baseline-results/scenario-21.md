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

## Follow-up (2026-10-25): tests that sign in, instead of a running app

For an app that logs users in with `oauth2Login` and a server-side session, a running-app check would need a stand-in identity provider, and still couldn't check the provider's own setup. Probes on Boot 4.1.1 found two reasons the tests had missed access bugs instead: a `RANDOM_PORT` test can't sign in at all (401), and `oidcLogin()` skips the app's authorities mapper (a `roles` claim gives `OIDC_USER` and `SCOPE_read`; admin routes answer 403). `writing-springboot-tests` now has `personas-oidc.java`, `personas-jwt.java` and `personas-db.java`, which sign a request in through the app's own role mapping (the same trap exists for `jwt()` and for `user(...).roles(...)`), and `route-access-test.java`, which calls every route as every persona and fails on a route nobody listed. On Boot 4.1.1, a broken role mapping failed it with each of the three, and so did a route nobody listed, an admin rule narrowed so a sibling route lost it, and a dropped `@PreAuthorize`. It checks roles only, not whose records a user may read.

**Do agents write these tests unprompted?** Four sessions with no templates, given "Add tests for who may call the order endpoints" on the same app ($0.34 in total). All four signed in with `oidcLogin().authorities(ROLE_...)`, so none ran the mapper. Their tests, run against each planted gap:

| Planted gap | Sonnet (2) | Haiku (2) |
|---|---|---|
| Admin rule narrowed, sibling route open | 2/2 caught | 2/2 caught |
| `@PreAuthorize` dropped from `/api/audit` | 2/2 | 0/2 (didn't test that route) |
| Mapper reads the wrong claim | 0/2 | 0/2 |
| New route, nobody decided its access | 0/2 | 0/2 |

Agents test the role rules on the routes they're asked about. The mapper and an unlisted route were missed every time: those are what the `personas-*.java` helpers and the route check in `route-access-test.java` add.
