# Testing the skills

## Skill trials

`baseline-scenarios.md` defines Scenarios 10–18. Each one runs the same task with and without a skill, in fresh sessions, and scores the result with planted bugs, PIT mutation scores or Hibernate statement counts. The recorded runs are in `baseline-results/scenario-N.md`.

| Scenario | Skill | What it checks |
|----------|-------|----------------|
| 10–12 | writing-springboot-tests | Tests that prove behaviour; unwanted tests and the wrong test level; edge bugs the skill doesn't name |
| 13 | code-reviewer | Reviewing tests |
| 14 | spring-data-jpa (retired after this) | Persistence fixes, scored with Hibernate statement counts |
| 15 | springboot-migration | Boot 3.5 → 4 with silent behaviour hazards |
| 16 | creating-springboot-projects | New project without progen |
| 17 | code-reviewer | Seeded PR review, old vs trimmed reviewer |
| 18 | code-reviewer | Test review of a real, well-kept suite |
| 23 | code-reviewer | Scenario 17 on Haiku, with a no-skill arm |
| 24 | spring-data-jpa (retired) | Scenario 14 on Haiku |
| 26 | code-reviewer (`jpa-performance.md`) | `Set` or `List` for JPA collections, scored by statements and rows read |
| 27 | spring-boot-team-harness (`telemetry.py`) | Server failures behind healthy responses, with and without the CLI |

To add a scenario, write the task and how it's scored in `baseline-scenarios.md`, run it with and without the skill, and record both runs in `baseline-results/scenario-N.md`. Put the fixture, its answer key or scorer, and a `run.sh` in `fixtures/scenario-N/` so others can rerun it (see `fixtures/README.md`).

## Script tests

`tests/scripts/` holds `unittest` tests for the bundled scripts. They use the standard library only, and need no network or Docker:

- `test_scan_migration_issues.py`: Maven dependency boundaries, exclusions and namespaces, Modulith schema detection in properties and YAML, SQL comments.
- `test_progen_config.py`: package and app-name validation, the existing-directory guard, progen failure handling, and Java version patching. A fake `progen` on `PATH` replaces the real binary.
- `test_check_new_project.py`: the new-project checks.
- `test_check_dashboards.py`: which empty panels and missing traces `check_dashboards.py` fails on.
- `test_check_request.py`: what `check_request.py` passes and fails on: the sent trace id, failed spans, ERROR lines, a missing trace and a stack that's down.
- `test_align_progen_project.py`: the edits that align a new progen project with the harness.
- `test_apply_harness.py`: where the harness script puts each pom fragment, the project's own compiler plugin moved to `<pluginManagement>` with its processor paths kept, the files it adds or appends to (including `.codex/hooks.json`, merged into an existing one), idempotency, a rerun raising the versions it pinned while keeping newer ones and replacing its own hook entries while keeping the team's, `--no-modules` and `--dry-run`. On Gradle: the script it writes and the one line that applies it, in Groovy and Kotlin DSL, starters and plugins read from the version catalog only where the build refers to them, the build's own Spotless kept, an installed observability pack's dependencies kept on a rerun with `--no-observability`, the Gradle commands in every template, updates to an unedited script, and the builds it stops on (multi-project, Error Prone already applied, both build files).
- `test_install.py`: the installer picks only the listed skills at the pinned commit, replaces only Codex folders it copied, turns auto-update on without overriding the user's choice, and every upstream entry is pinned to a full commit.
- `test_baseline.py`: reading NullAway errors from Maven and Gradle output (Windows and POSIX paths), the Gradle tasks and record property it runs, and marking a class `@NullUnmarked` without disturbing its annotations or line endings.
- `test_report.py`: the hook report counts checks, blocks by gate and fixes after a block, counts turns with no recorded starting point as not checked, leaves out old events, and skips damaged lines.
- `test_harness_hooks.py`: the harness's hooks. The PreToolUse hook blocks destructive git commands, including ones with quoted arguments, gate runs that skip tests or checks (but not packaging that does), and edits to migrations already on `main`, and allows everything else. It reads Codex's `apply_patch` edits too, and finds the repository without `CLAUDE_PROJECT_DIR` when Codex runs it from a subfolder. The Stop hook, run against a fake `mvnw`, skips sessions that changed no code, checks committed changes, blocks only on errors in files the session changed, reports failures elsewhere without blocking, never records a failure as passed, and lets a retry on unchanged failing code stop. A Stop in a session with no recorded starting point says the turn wasn't checked, and a session in use outlives sessions that started after it when old ones are pruned. The ArchUnit and Spring Modulith violation records, the record flags and a module's `package-info.java` can't be edited. The CI integrity check fails a pull request that adds to either record or widens a module's `allowedDependencies` (with a new entry, a constant or an escaped name, by removing the list, or by opening the module), and passes narrowing and new modules. It also fails one that unregisters a harness hook in `.claude/settings.json` or `.codex/hooks.json`, changes the harness's plugin block in the pom, removes a line from `.mvn/jvm.config`, or changes the verify workflow the harness added, and passes the team's own edits to those files. On Gradle, it fails a change to `gradle/harness.gradle` or a build file that stops applying it; the guard refuses `-Pharness.record=true`; and the Stop hook, against a fake `gradlew`, formats the session's files by path, runs `harnessCheck`, and reads Gradle's compiler errors, indented test failures and build-file messages. The file-size check fails a new or grown source file over the limit, passes an old oversized file the change doesn't grow, and skips generated code and migrations. It fails a new numbered copy and passes an old one or another name. The Stop hook blocks on it, also for a file the session committed. Needs `bash` (Git for Windows on Windows).
- `test_telemetry.py`: the Scenario 27 `telemetry.py` CLI that finds server failures behind healthy responses.
- `test_docs.py`: the docs name every gate, hook and project skill the harness ships, and this file lists every script test.

```bash
python3 -m unittest discover -s tests/scripts -v
```

Run them after any change to the scripts. Add a failing test first for each new bug.
