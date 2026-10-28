# Harness sample

A small Spring Boot 4.1.1 project with two modules (`catalog`, marked `@NullMarked`, and `orders`). `check.sh` copies it to a temporary folder, applies `spring-boot-team-harness`, and checks that:

- `verify` passes on the clean project;
- NullAway fails on a `return null` (in both modules, or with `marked` only in `catalog`);
- `CodeRulesTests` fails on `System.out`, and each of its other recent rules fails on a mistake planted for it (one build for all of them); `ConfigurationKeysTests` on a misspelt key, `ModuleBoundariesTests` on use of another module's internal package, and Spotless on unformatted code.
- rerunning `apply_harness.py` changes nothing;
- the Stop hook, on a real build, blocks a class that calls its own `@Async` method and lets the fixed code through;
- on code that broke the rules before the harness, `baseline.py` marks and records it, `verify` passes, a new violation still fails, and the integrity check refuses a pull request that adds to the freeze record.

```bash
tests/harness-sample/check.sh all      # or: marked
```

It needs JDK 21.0.8 or later, Maven and Python 3. CI runs it on JDK 21 and 25 in both NullAway modes (`.github/workflows/harness-build.yml`).
