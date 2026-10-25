# Trial fixtures

Each folder holds what a scenario needs to be rerun by anyone: the fixture, its answer key or hidden scorer, and a `run.sh` that runs one arm in a fresh headless session (`claude -p`). Run each arm several times and on more than one model before drawing a conclusion. Record the runs in `../baseline-results/scenario-N.md`.

| Folder | Scenario | Needs | Scored by |
|---|---|---|---|
| `scenario-23/` | Seeded PR review (code-reviewer) | git, Claude Code | Reading `review.md` against `key.md` |
| `scenario-24/` | Persistence fixes (retired spring-data-jpa) | git, Claude Code, JDK 21+, Maven, Maven Central | `score.sh` (statement counts on H2) |

```bash
# code-reviewer: old SKILL.md, trimmed SKILL.md, no skill
tests/fixtures/scenario-23/run.sh haiku 0be0bbb /tmp/s23/old
tests/fixtures/scenario-23/run.sh haiku current /tmp/s23/trimmed
tests/fixtures/scenario-23/run.sh haiku none    /tmp/s23/none

# spring-data-jpa: retired skill vs none
tests/fixtures/scenario-24/run.sh haiku 23a35a4^ /tmp/s24/skill
tests/fixtures/scenario-24/run.sh haiku none     /tmp/s24/none
```

Keep `key.md` and `scorer/` away from the session: `run.sh` copies only the fixture into the work folder.

The fixtures for Scenarios 10–22 are not here yet. Add each one in the same layout when it is next run.
