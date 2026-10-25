# Skill triggering

Checks whether each skill loads on its own, from its description, for prompts that don't name it (Scenario 25).

- `prompts.json`: 3 prompts per skill and 5 near misses that should load none, each with the project it runs in.
- `projects/`: a Boot 4 shop, a Boot 3.5 copy for the migration prompts, a Kotlin project and an empty folder.
- `routing.md`: the `AGENTS.md` "Skills" section used in run 3.
- `run.py`: runs each prompt once per model in a fresh `claude -p` session, with the skills in `.claude/skills/`, read-only tools and at most 6 turns.

```bash
python3 tests/fixtures/triggering/run.py --models sonnet,haiku          # all prompts, about $3.50
python3 tests/fixtures/triggering/run.py --models haiku --routing tests/fixtures/triggering/routing.md
python3 tests/fixtures/triggering/run.py --only review-2,none-1          # a few prompts
```

Rerun it after changing any skill's description, and add a prompt for each way users phrase a request that a skill missed.
