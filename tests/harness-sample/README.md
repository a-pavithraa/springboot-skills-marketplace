# Harness sample

A small Spring Boot 4.1.1 project with two modules (`catalog`, marked `@NullMarked`, and `orders`), each with an `@ApplicationModuleTest`. `check.sh` copies it to a temporary folder, applies `spring-boot-team-harness`, and checks that:

- `verify` passes on the clean project;
- NullAway fails on a `return null` (in both modules, or with `marked` only in `catalog`);
- `CodeRulesTests` fails on `System.out`, and each of its other recent rules fails on a mistake planted for it (one build for all of them); `ConfigurationKeysTests` on a misspelt key, `ModuleBoundariesTests` on use of another module's internal package, and Spotless on unformatted code.
- `UnusedCodeTests` lets through a setter only a test calls, and `BuildSetupTests` a test-only HTTP client starter unless main code builds a client with it;
- `ConfigurationKeysTests` fails on Actuator endpoints exposed on the public port, `LogLeakCheck` on a logged email address, and `CodeRulesTests` on `printStackTrace` and a hand-built OpenTelemetry bean;
- `HandledFailureFilter` logs sync and async handled failures on a real server, and its test fails on a filter that skips async dispatches;
- rerunning `apply_harness.py` changes nothing;
- on a copy that formats with Spring Java Format, the harness adds no Spotless and `verify` passes;
- the Stop hook, on a real build, blocks a class that calls its own `@Async` method and lets the fixed code through;
- on code that broke the rules before the harness, `baseline.py` marks and records it (including a module-boundary violation in `modulith_store`), `verify` passes, a recorded boundary violation moved down a line still passes, a new violation of either kind still fails, and the integrity check refuses a pull request that adds to the freeze record or to `modulith_store`.

```bash
tests/harness-sample/check.sh all      # or: marked
```

It needs JDK 21.0.8 or later, Maven and Python 3, on Linux or macOS. On Windows, run `tests/harness-sample/check-in-docker.sh all` from Git Bash instead; it runs the same check in a Linux container. CI runs it on JDK 21 and 25 in both NullAway modes (`.github/workflows/harness-build.yml`).
