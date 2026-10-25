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

To add a scenario, write the task and how it's scored in `baseline-scenarios.md`, run it with and without the skill, and record both runs in `baseline-results/scenario-N.md`. Put the fixture, its answer key or scorer, and a `run.sh` in `fixtures/scenario-N/` so others can rerun it (see `fixtures/README.md`).

## Script tests

`tests/scripts/` holds `unittest` tests for the bundled scripts. They use the standard library only, and need no network or Docker:

- `test_scan_migration_issues.py`: Maven dependency boundaries, exclusions and namespaces, Modulith schema detection in properties and YAML, SQL comments.
- `test_progen_config.py`: package and app-name validation, the existing-directory guard, progen failure handling, and Java version patching. A fake `progen` on `PATH` replaces the real binary.
- `test_check_new_project.py`: the new-project checks.
- `test_apply_harness.py`: where the harness script puts each pom fragment, the files it adds or appends to, idempotency, `--no-modules` and `--dry-run`.
- `test_install.py`: the installer picks only the listed skills at the pinned commit, replaces only Codex folders it copied, turns auto-update on without overriding the user's choice, and every upstream entry is pinned to a full commit.
- `test_baseline.py`: reading NullAway errors from Maven output (Windows and POSIX paths), and marking a class `@NullUnmarked` without disturbing its annotations or line endings.
- `test_report.py`: the hook report counts checks, blocks by gate and fixes after a block, leaves out old events, and skips damaged lines.
- `test_harness_hooks.py`: the harness's hooks. The PreToolUse hook blocks destructive git commands, including ones with quoted arguments, and edits to migrations already on `main`, and allows everything else. The Stop hook, run against a fake `mvnw`, skips sessions that changed no code, checks committed changes, blocks only on errors in files the session changed, reports failures elsewhere without blocking, never records a failure as passed, and lets a retry on unchanged failing code stop. The archunit_store record can't be edited. Needs `bash` (Git for Windows on Windows).

```bash
python3 -m unittest discover -s tests/scripts -v
```

Run them after any change to the scripts. Add a failing test first for each new bug.
