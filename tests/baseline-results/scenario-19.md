# Scenario 19: Team Harness, AGENTS.md vs Stop Hook (spring-boot-team-harness)

**Date:** 2026-10-24
**Claude Version:** Claude Code 2.1.310, `claude -p --model sonnet`, one run per task and arm
**Skill Loaded:** none. The sessions ran in projects that `apply_harness.py` had set up, with the arms described in `tests/baseline-scenarios.md`, Scenario 19.

## Results

| Task | none (gates in the pom only) | guide (`AGENTS.md`, no hooks) | full (`AGENTS.md` and hooks) |
|---|---|---|---|
| null | ❌ `priceOf` returns `null` without `@Nullable`: NullAway fails the compile | ✅ `@Nullable`, null handled | ✅ same, Stop hook passed |
| cache | ✅ separate `ProductLookup` bean | ✅ separate bean | ✅ separate bean, Stop hook passed |
| print | ❌ `System.out.println` in `ProductController`: `CodeRulesTests` fails | ✅ SLF4J logger | ✅ logger, Stop hook passed |

| Arm | Cost, 3 tasks | Turns | Time |
|---|---|---|---|
| none | $0.32 | 37 | 56 s |
| guide | $0.36 | 45 | 129 s |
| full | $0.43 | 53 | 297 s |

In the none arm, the agent never ran the build. It finished the null and print tasks in 7 turns and 10 s each, and left a project that fails `./mvnw verify`.

### Commit check

Full harness on `feature/discounts`, with `git add` and `git commit` allowed:

| Arm | Commits | Left uncommitted | Cost | Time |
|---|---|---|---|---|
| with the commit line | 0 | 4 files | $0.12 | 157 s |
| without it | 0 | 4 files | $0.11 | 157 s |

Neither session committed. With the line, the agent finished with "Nothing is committed. You're on `feature/discounts` … Do you want me to commit them?" Without it, it said "I didn't commit anything." Both features were correct and the Stop hook passed in both.

## What this shows

**`AGENTS.md` is what keeps the agent out of the traps.** The gates catch a mistake only if someone runs them. With the instruction "Run `./mvnw verify` … before you say a change is finished", the agent ran the build, met the gates inside its own loop, and fixed the code before it finished. Without the instruction, the same gates sat unused in the pom.

**The Stop hook caught nothing extra here.** It passed first time in every full-arm run, because the agent had already run `verify`. It added 18 to 125 s per task, and about 50% to the cost of the cache task. It remains the check for a session that skips `verify`: in the pilot, a forced `System.out` was blocked by the hook and fixed.

**The cache trap tested nothing.** Sonnet used a separate bean in all three arms, so this rule guards a mistake that this model did not make here.

**The commit line does not make Claude Code commit on its own.** Claude Code's own instructions are to commit only when the user asks, and the session followed those over `AGENTS.md`. The line changed one thing: the agent offered to commit. A developer who wants commits after each step has to ask for them in the request. Asking is enough, since it reminds a developer who forgot, so the line now tells the agent to ask whether to commit a finished change, and says how to commit once the user agrees.

**Caveat:** one run per arm, one model, a three-class project, and prompts that each invite one trap. A strong signal, not proof.

**Overall:** ✅ `AGENTS.md` plus the gates prevented 2 of 2 real traps that Sonnet fell into without it. The Stop hook is a safety net, not the main lever. ⚠️ The commit line does not cause commits; it gets the agent to ask, which the line now asks for directly.

## Environment

Windows 11, Claude Code 2.1.310, JDK 25 (mise), an isolated `CLAUDE_CONFIG_DIR`. Total cost about $1.33 for 11 sessions.
