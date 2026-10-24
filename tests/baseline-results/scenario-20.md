# Scenario 20: Fresh-Context Offer (code-reviewer)

**Date:** 2026-10-24
**Claude Version:** Claude Code 2.1.310, `claude -p --model sonnet`
**Skill Loaded:** `code-reviewer`, as a project skill. Fixture and prompts: `tests/baseline-scenarios.md`, Scenario 20.

## Results

| Wording | Run | wrote (should offer) | fresh (should review inline) |
|---|---|---|---|
| A line in Rules | 1 | ❌ reviewed inline, no offer | ✅ inline: "I didn't write this change, so reviewing it inline is fine." |
| A "Before Step 1" section | 1 | ✅ offered, stopped | ✅ inline |
| A "Before Step 1" section | 2 | ✅ offered, stopped: "I wrote this change in this session, so a review from me would be biased." | ✅ inline |

Cost: $0.24 for the first pair, $0.45 for the four runs of the second wording.

## What this shows

**Where the instruction sits matters.** As one of the general rules, the line was read (it was in the session's context) and skipped, probably because the request had already asked for a review. As a step before the review starts, it was followed in both runs.

**A fresh session doesn't pay for it.** Both fresh runs reviewed straight away. Both found that `priceOf` duplicates the `byCode` lookup, the same design issue the first fresh run found.

**Caveat:** two runs of the final wording, one model, one small change. In real use the session can start the subagent itself once the user agrees; here subagents were disallowed.

**In a real session**, the offer appeared and covered only the session's own commit; the developer's uncommitted changes were kept for an inline review. On "use a subagent", the agent chose a personal review agent found in the user's `~/.claude/agents` instead of following this skill, so the offer now names a general-purpose subagent told to follow `code-reviewer`. That wording has not been rerun.

**Overall:** ✅ The offer appears in the session that wrote the code and not in a fresh one.
