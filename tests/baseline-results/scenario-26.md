# Scenario 26: Set or List for JPA Collections

**Date:** 2026-10-25
**Claude Version:** Claude Code 2.1.310, headless (`claude -p`), **Sonnet** and **Haiku**, one fresh session per run
**Skill Loaded:** None (baseline) / `code-reviewer` in `.claude/skills/`, with the corrected `jpa-performance.md` (target). Fixture, scorer and runner: `tests/fixtures/scenario-26/`.

The prompt was "Optimize the persistence code in this project." The fixture is a blog service with three traps from Vlad Mihalcea's articles (`key.md`). The scorer seeds 50 posts, each with 20 comments and the same 10 tags, and counts statements and rows read per request.

Before the runs, the scorer was checked against two hand-written fixes. A reference fix (tags as `Set` with `PERSIST` and `MERGE`, one collection per query) scored 2 statements and 1,500 rows for the feed. The `Set` shortcut (both collections as `Set`, fetched in one join) scored 1 statement and 10,000 rows. Counting statements alone would have ranked the shortcut first.

---

## Results

| | Untouched | Sonnet none 1 | Sonnet none 2 | Sonnet skill | Haiku none 1 | Haiku none 2 | Haiku skill |
|---|---|---|---|---|---|---|---|
| P6 feed statements / rows read | 101 / 1,550 | 2 / 1,500 | 3 / 1,550 | 2 / 1,500 | 3 / 1,550 | 3 / 1,550 | 2 / 1,500 |
| P6 switched a collection to `Set` to fetch both at once | — | no | no | no | no | no | no |
| P5 remove one tag, statements | 12 | **3** | **3** | **3** | 12 | 12 | 12 |
| P5 `Post.tags` type | `List` | `Set` | `Set` | `Set` | `List` | `List` | `List` |
| P7 delete post: status, shared tags kept | 500, nothing deleted | 204, kept | 204, kept | 204, kept | 204, kept | 204, kept | 204, kept |
| `Post.comments` stays `List` | — | yes | yes | yes | yes | yes | yes |
| Feed and remove-tag results correct | yes | yes | yes | yes | yes | yes | yes |
| Cost / time | | $0.17 / 48 s | $0.16 / 37 s | $0.18 / 46 s | $0.02 / 88 s | $0.02 / 128 s | $0.02 / 79 s |

**The skill never loaded.** Neither skill-arm session invoked `code-reviewer` or read its files, so all six runs measure the model without guidance.

## What this shows

**The `MultipleBagFetchException` shortcut did not appear.** No run fetched both collections in one query, so none hit the exception or switched to `Set` to silence it. All six loaded one collection per query.

**The cascade trap was fixed every time.** All six removed `REMOVE` from the `@ManyToMany` cascade, keeping `PERSIST` and `MERGE` or no cascade at all, and the post delete now succeeds without touching shared tags.

**`Set` for `@ManyToMany` splits by model.** Sonnet changed `tags` to `Set` in 3 of 3 runs. Haiku kept the `List` in 3 of 3, so removing one tag still deletes all 10 join rows and inserts 9 again. The cost grows with the number of tags on a post. This is a performance problem, not a correctness one: every result was right.

**Nobody added `equals`/`hashCode` to `Tag`.** Sonnet's `Set<Tag>` relies on object identity, which works inside one persistence context, the only place this code uses it. The scorer found no problem.

**Caveats:** one or two runs per arm, one small fixture, and a prompt that leaves the agent to find the problems. The skill arm tested nothing, because the skill didn't load.

## Why the skill didn't load

The Scenario 25 descriptions and `AGENTS.md` section were in place, but the skill arm used neither: no `AGENTS.md`, and a prompt asking to optimize rather than to review or diagnose something slow. The session also listed 120 skills; pstack, installed the same day, added 58. Three follow-up arms, each changing one thing, all with `code-reviewer` in `.claude/skills/`:

| Arm | Change | Skills listed | Loaded `code-reviewer` |
|---|---|---|---|
| Original | "Optimize the persistence code in this project." | 120 | Sonnet 0/1, Haiku 0/1 |
| A | "The blog is slow. Look at the persistence code and fix it." | 120 | Sonnet 1/1, Haiku 1/1 |
| B | Original prompt, plus the harness `AGENTS.md` skills section | 120 | Sonnet 1/1, Haiku 1/1 |
| C | Original prompt, pstack disabled | 62 | Sonnet 2/2, Haiku 1/1 |

Any one change was enough. The descriptions work when the request uses their words (A), the `AGENTS.md` section works for a request they don't match (B), and with half as many skills listed even the unmatched prompt loaded it (C). The miss needed all three: an unmatched prompt, no `AGENTS.md`, and 120 skills. Loading didn't fix Haiku's `@ManyToMany`: A and B loaded the skill and still left `List` (12 statements), since the reference says nothing about it. C's Haiku run used `Set`, which is run-to-run variance.

**Overall:** No guidance needed for the bag-fetch shortcut, the cascade, or `List` for `@OneToMany`. ⚠️ Haiku leaves `@ManyToMany` as `List` (5 of 6 runs, with or without the skill loaded). `CodeRulesTests` now fails on a `@ManyToMany` field that isn't a `Set`.
