# Scenario 25: Do the Skills Load on Their Own?

**Date:** 2026-10-25
**Claude Version:** Claude Code 2.1.310, headless (`claude -p`), **Sonnet** and **Haiku**, one fresh session per prompt and model
**Skills:** all five, in the project's `.claude/skills/`, alongside the session's other installed skills (including Claude Code's built-in `code-review`)

Every earlier trial told the agent to read the skill. This one checks whether Claude Code picks the skill itself from its description. Prompts, projects and the runner are in `tests/fixtures/triggering/`. There are 20 prompts: 3 per skill that don't name it, and 5 near misses that should load none of them (a general Spring question, Kotlin code, a README, a rename, a Python script). Sessions could only load skills and read files, for up to 6 turns. A run passes when the expected skill loaded, or no skill of ours for a near miss.

## Results

Run 1, the descriptions on `main`:

| Skill | Sonnet | Haiku |
|---|---|---|
| creating-springboot-projects | 3/3 | 1/3 |
| springboot-migration | 3/3 | 2/3 |
| code-reviewer | 2/3 | 0/3 |
| writing-springboot-tests | 3/3 | 0/3 |
| spring-boot-team-harness | 2/3 | 2/3 |
| Near misses, none loaded | 5/5 | 5/5 |

Sonnet missed "the orders list endpoint is slow, look at the persistence code" (`code-reviewer`) and "how do I make sure everyone's agent follows the same rules" (`spring-boot-team-harness`). In the Haiku session that was inspected, the skills were listed, and Haiku read the files and answered without loading one.

Run 2 reran the 12 misses and the 5 near misses with descriptions that start with "Use when" and use the words in the prompts ("review, check or diagnose", "slow endpoint or query", "every developer's coding agent", "upgrading ... to the latest Spring Boot and Java"). Run 3 is run 2 plus a five-line "Skills" section in the project's `AGENTS.md`, imported by `CLAUDE.md`, as the harness sets it up.

| | Run 1 | Run 2: new descriptions | Run 3: plus `AGENTS.md` |
|---|---|---|---|
| Sonnet, earlier misses | 0/2 | **2/2** | not run |
| Haiku, earlier misses | 0/10 | **6/10** | **10/10** |
| Near misses, none loaded | 10/10 | 10/10 | 5/5 (Haiku) |
| Cost | $3.35 (40 sessions) | $0.70 (22) | $0.13 (15) |

Haiku still missed after run 2: the slow-endpoint and test-review prompts (`code-reviewer`), the HTTP-client test prompt, and the team-rules prompt.

## What this shows

**On Sonnet, the descriptions were nearly enough, and the new ones fix both misses.** The misses were wording: a performance diagnosis didn't read as a "review", and the harness description began with what it adds rather than when to use it.

**On Haiku, the skills mostly didn't run unless named.** Two of five skills never loaded. Better descriptions recovered 6 of the 10 misses, and the `AGENTS.md` section recovered all 10. Earlier Haiku trials (Scenarios 23 and 24) told the agent to read the skill, so they measured what the skill does once loaded, not whether it would load.

**No false triggers.** No near miss loaded a skill in any run, including with the `AGENTS.md` section.

**Changes made:** all five descriptions rewritten as above (each under 650 characters, with their "Not for … (see …)" hand-offs kept), and a "Skills" section added to the harness's `AGENTS.md` template.

**Caveats:** one run per prompt and model. Runs 2 and 3 reran only the earlier misses and the near misses, so prompts that passed in run 1 were not rerun with the new descriptions. Run 3 ran on Haiku only, and its `AGENTS.md` line for the harness was worded for setting it up ("Shared agent rules, AGENTS.md or build checks") rather than the template's line for a project that already has it.

**Overall:** ✅ new descriptions: Sonnet 15/15 and Haiku 11/15 on the prompts rerun or kept; ✅ `AGENTS.md` routing: Haiku 15/15 on the misses, with no false triggers.

## Environment

Linux cloud workspace, Claude Code 2.1.310. Total cost about $4.20 for 77 sessions. Raw results: `tests/fixtures/triggering/results/`.
