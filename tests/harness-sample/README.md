# Harness sample

A small Spring Boot 4.1.1 project with two modules (`catalog`, marked `@NullMarked`, and `orders`), each with an `@ApplicationModuleTest`. `check.sh` copies it to a temporary folder, applies `spring-boot-team-harness`, and checks that:

- `verify` passes on the clean project;
- NullAway fails on a `return null` (in both modules, or with `marked` only in `catalog`);
- `CodeRulesTests` fails on `System.out`, and each of its other recent rules fails on a mistake planted for it (one build for all of them); `ConfigurationKeysTests` on a misspelt key and on a stand-in placeholder default outside a local profile, `ModuleBoundariesTests` on use of another module's internal package and on an allowed dependency nothing uses (but not on one used only through a constant), `BuildSetupTests` on two `@Scheduled` jobs without a scheduler pool, and Spotless on unformatted code.
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

`check-gradle.sh` does the same on a Gradle build of the sample, in Groovy or Kotlin DSL: the build applies `gradle/harness.gradle` and passes clean; NullAway, `CodeRulesTests`, `ConfigurationKeysTests`, `ModuleBoundariesTests`, `BuildSetupTests` (reading the Gradle build's declared dependencies), `LogLeakCheck` and Spotless each fail on their planted mistake; a rerun changes nothing; the Stop hook formats only the session's files, blocks a self-invoked `@Async` method and lets the fix through; `baseline.py` records legacy code and new violations still fail; the integrity check refuses a change to `gradle/harness.gradle`; and the `move-code` skill's OpenRewrite init script previews a move.

```bash
tests/harness-sample/check-gradle.sh groovy      # or: kotlin
```

It needs JDK 25, Gradle 9 and Python 3; on Windows, run `tests/harness-sample/check-gradle-in-docker.sh groovy`.

`check.sh` needs JDK 21.0.8 or later, Maven and Python 3, on Linux or macOS. On Windows, run `tests/harness-sample/check-in-docker.sh all` from Git Bash instead; it runs the same check in a Linux container. CI runs it on JDK 21 and 25 in both NullAway modes (`.github/workflows/harness-build.yml`).
