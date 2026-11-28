# AI code review: what the team harness should take from a real codebase, and whether the triage gate ports

**Status:** Research only. Nothing in the harness changed. Not committed.

**Goal:** A real codebase written mostly by agents wrote a `REVIEW.md` and two research notes after its AI reviews
turned nit-picky. Decide what of that belongs in `spring-boot-team-harness`, and whether the "triage gate" from
[a-pavithraa/claude-mods](https://github.com/a-pavithraa/claude-mods), which holds risky commits in Claude Code, can
be rebuilt for Codex and Kiro, which have no mod API.

**Sources:** The real codebase's documents live in a private checkout and are cited by repo-relative path only:
`docs/reference/ai-code-review.md`, `docs/reference/modular-code-research.md`, `REVIEW.md`, `AGENTS.md`, and two
standalone notes kept beside the checkout, `ai-code-review-codex.md` and `ai-code-review-learnings.md`. Everything else is public and linked. A claim
with no source is marked UNVERIFIED.

---

## Summary

The real codebase found that its AI reviewer reported findings no user could reach, and that the agent asked to
"fix the ones that are real" fixed every one of them, so each review round added a commit and another round. Its
fix is a `REVIEW.md` read before every review that demands a trace from a supported entry point to a wrong result,
asks the reviewer to look for the guard that rules the finding out, caps findings at five, names what CI already
fails on, lists the failures earlier reviews missed, and says zero findings is a valid review. The harness's own
`REVIEW.md` template already has the skeleton (failures, risk, don't report, report) but not the trace rule, the
cap, the "pre-existing" bucket, the round limit, or the reviewer-side rule for agents that fix findings. The second
research note shows that, on that codebase, fixes clustered in short files that call external systems and in
configuration, not in long files, which supports the harness's framing of its 20 KB rule as a read-size limit and
argues for deriving `REVIEW.md`'s high-risk paths from `git log`. The triage gate is a Claude Code mod: it
intercepts `Bash` and `PowerShell` tool calls, parses them for `git commit`, scores the uncommitted change by
size, reach and sensitive paths, denies the call when the score is five or more, and lets the human approve from
a pane. The scoring, the commit parsing and the deny are plain shell-hook work and port to all three tools; the
pane, the buttons and the paid risk model do not. On Codex and Kiro the approval becomes a file the human writes
from their own terminal, backed by a CI label, which is how the harness's integrity check already works.

---

## 1. What each source says that matters here

### 1.1 `docs/reference/ai-code-review.md` (the reasons behind the real codebase's REVIEW.md)

- The fix loop is the cost, not the review. In 13 Codex review rounds, Claude, asked to "fix the ones that are
  real", accepted all of about 33 findings and rejected none; some needed input the product never sends, such as a
  hand-edited `?from=2026-13-01` URL. Anthropic reports the same: a person waves off a nit in seconds, an agent
  author fixes it, adding a commit and a round. Source: section "What earlier reviews tell us", last paragraph,
  citing [Claude Code team on code review](https://claude.dev/blog/solving-code-review-at-anthropic/).
- Three past reviews are kept as a table of what the reviewer did and what it should have done: a severity that
  rested on an unresolved read policy (ask who may read before rating); a race the existing suite missed, proven
  by a failing test (keep); a map that disagreed with the code (report the map correction once, state the
  unverified playback gap separately). Source: same section's table.
- The review method is five steps: start from the promise (acceptance criteria, touched flows, invariants; write
  down what each actor should observe, and check for promised behaviour the author left out); trace each suspected
  failure from a real button, route, job or event; try to disprove it (an earlier guard, a database constraint, a
  documented exception; a fake that bypasses production validation proves only that the fake can build the state);
  one comment per cause with trigger, expected, actual, location and evidence; and a short review path for the
  human (contract, decisive code, test assertion). Source: section "Review a pull request".
- Rules for the agent that fixes findings: tag each Important, Nit or Pre-existing; fix Important only; answer the
  rest in a line or file them in `docs/known-gaps.md`; stop after three rounds and ask the human to reconsider the
  approach; after round one review only the new diff; fix the class of bug, not the line; check invariants only
  when the diff matches their trigger. Source: list "When an agent fixes the findings".
- A regression check should fail on the broken revision and pass on the fix; for a feature, derive expected results
  from acceptance criteria before reading the implementation, since a green suite can repeat the author's
  assumption. Source: paragraph after that list.
- Evaluation: replay old and new prompts on the same historical PR heads with later fixes hidden, include clean
  changes and dismissed findings, have a maintainer judge blind, and count confirmed/reported, known bugs found,
  and triage minutes; "a quieter reviewer can still miss more bugs". Source: section "Check whether this helps".
- Research it rests on, each marked as field study, vendor account or practitioner post: RevMate's 8.1% and 7.2%
  acceptance ([arXiv 2411.07091](https://arxiv.org/abs/2411.07091)); the Claude Code team's first-round pass
  65% to 78% and reviews-to-pass 2.08 to 1.32, 59% of repeated flags on code older than the first pass, one
  reviewer tuned by a `REVIEW.md` read from the base branch so a change can't edit its own checks
  ([blog](https://claude.dev/blog/solving-code-review-at-anthropic/),
  [post](https://x.com/addyosmani/status/2122590683055993308)); Cursor's validator step
  ([Bugbot](https://cursor.com/blog/building-bugbot)). Source: section "Research behind the proposal".

### 1.2 `REVIEW.md` (the guide itself)

- "Report a finding only when you can trace it": start at a supported entry point, follow it through the changed
  lines to a wrong result someone sees, look for the strongest reason it cannot happen, drop it if one holds. "Zero
  findings is a valid review." Source: `REVIEW.md`, first section.
- Severity P0 (data lost, personal data leaks, an invariant on access or audit breaks), P1 (a normal user gets a
  wrong result; a break of a written rule in `AGENTS.md`), P2 (rare setup, or a nit worth one line), P3 (the code
  had the problem before this change). Fix P0 and P1 in the same PR; answer P2 and P3 in one line each; follow-ups
  go to `docs/known-gaps.md`. Source: section "Severity".
- "Always report" holds four kinds: a break of a numbered invariant, a contract change with no doc update, a
  comment the change makes untrue, and a bulleted list of failures earlier reviews missed. Source: section
  "Always report".
- "Risk" names packages and files by their fix history ("Most past fixes landed here"). Source: section "Risk".
- "Do not report": what the build or CI already fails on, listed per layer; style unless it hides a bug; a
  situation no supported entry point reaches; a choice a decision record documents. Source: section "Do not
  report".
- Report shape: `- [P1] <title> -- <file>:<line>` plus entry point, what happens, wrong result; at most five
  findings, one per cause, most serious first; end with the count or "No issues found"; name what could not be
  checked; on a later round review only the new diff and don't repeat an answered finding. Source: section
  "Report".

### 1.3 `AGENTS.md` (one changed line)

The only change in the commit that added `REVIEW.md` replaces "Reviewers check the diff against the updated map"
with "Reviewers, people or agents, read `REVIEW.md` first, then check the diff against the updated map. If the map
and the code disagree, the PR is not ready." Source: `git show HEAD -- AGENTS.md` in the private checkout, hunk at
line 101. The harness's `AGENTS.md` template has no such pointer; its `code-reviewer` skill reads `REVIEW.md` on
its own (`plugins/springboot-architecture/skills/code-reviewer/SKILL.md:10`), but a reviewer that isn't using
that skill, such as Codex `review` or a Kiro session, is never told.

### 1.4 `ai-code-review-codex.md` (standalone note)

An earlier, shorter draft of 1.1: same five steps, same prompt, same evaluation section, but without the fix-loop
paragraph, the agent-fix rules and the Claude Code team's numbers. Nothing in it is absent from 1.1, so it adds no
claim here. Source: the two files compared side by side.

### 1.5 `docs/reference/modular-code-research.md` (keeping agent code modular)

- No source gives an evidence-based threshold for file length, function length or complexity as a gate; the
  defaults are tool authors' opinions, and complexity metrics add little beyond line count. Source: sections
  "Summary" and "2. Which structural metrics predict defects or cost".
- On that codebase, counted over 76 `fix` commits, the most-fixed files were short (216, 200, 138 and 79 lines),
  the two long SQL repositories were hot too, and the longest file (854 lines) had 3 fixes in 22 commits. Fixes
  clustered in one business module, in calls to one external system, and in configuration, not in long
  files. Source: section "2", subsection "This repo's history".
- Ratchets (ArchUnit `FreezingArchRule`, ESLint bulk suppressions, deslop's allow file) are documented patterns
  with no outcome data. Source: section "6. Ratchet and baseline patterns".
- Anthropic's best-practices page splits instructions into non-deterministic (prompts, `CLAUDE.md`) and
  deterministic (hooks, deny rules), shows a `Stop` hook that blocks until the typecheck passes, and says a rule
  the agent keeps ignoring belongs in a hook when it has no exceptions. Source: section "7", citing
  [Claude Code best practices](https://code.claude.com/docs/en/best-practices).
- deslop-please is Rust-only (reads `cargo metadata`, builds a rust-analyzer SCIP index); its `HELD_IN_MIND = 7`
  cites Miller 1956, which is about human memory, so the number is opinion; porting means a symbol-graph reader and
  a new rule set. Verdict there: do not port. Source: section "5. deslop-please, and porting its ideas".

What this means for the harness: the file-size check (`assets/project/.github/harness/check-file-size.sh`) is
already justified as "an agent reads a smaller file in one go" (`SKILL.md`, table row "check-file-size.sh"), not
as a defect predictor, and that framing should stay. The hotspot finding supports two existing gates
(`ConfigurationKeysTests` and the no-timeout client rule in `CodeRulesTests`) and suggests `REVIEW.md`'s risk
section should come from the project's own `git log`, not from a generic list.

### 1.6 `ai-code-review-learnings.md` (standalone note, written after the replay)

A later note than 1.1 and 1.4, written once the new `REVIEW.md` had been replayed against the old prompt. It
adds results and corrections that the other two don't have:

- Replay on 8 past PRs with Codex (5 with a known bug, 3 clean): findings fell from 32 to 17, on clean PRs from 14
  to 4; both prompts found the same 3 of 5 known bugs; precision rose from 22% to 31%. Source: section "What the
  replay actually showed".
- The reviewer's severity tags can't be trusted: with P1 defined as "a traced bug", 13 of 13 findings were P1
  (one was a 2017 ticket in a rare time zone); a stricter consequence rule still left 15 of 20 at P1. The lesson:
  the tag must not decide what gets fixed; the fixing agent applies the consequence test itself (trace it, does
  it hit a normal user doing normal work, frequency times severity) and answers the rest with a reason. Source:
  same section. This changes candidate 4 below: the fix rule is "re-trace, then fix", not "fix what's tagged".
- Run-to-run variation is as large as the difference between prompts; the same prompt found the key race in one
  run and missed it in the next. Run each case several times before comparing prompts. Source: same section.
  This changes candidate 12.
- The one earlier round that filtered well used a score: frequency (1-10) times severity (1-10), under 5 filed as
  an issue and not fixed; it dropped 5 of 17 items. Source: same section.
- A second reviewer or second model doesn't help: "two models agreeing leaves the claim untested". Source:
  section "The core problem". This weakens the cross-model argument for route B in §2.4: the fresh context
  matters, the different vendor does not.
- Every bug both prompts missed became an "always report" item (a setting required at startup when its feature
  is off; an external API rejecting a request at one of its limits). Source: same section.
- Replay harness traps: the bug must be in the diff; answer keys come from the fix commit and a subject-only
  commit needs a person to confirm; clean controls need the right base; blind grading leaks through counts per
  label and progress lines; a failed run (usage limit returning an empty review) must be saved as failed, not as
  "no findings"; save each review as it finishes so a killed run resumes; replay on the model the real reviews
  use. Source: section "Building a replay harness: traps".
- A rule can be met by its wording and defeat its aim ("`useEffect` only in `use*.ts`" was met by moving the
  effect into a hook file). No linter judges intent, so it is a review rule: "Code moved only to satisfy a lint
  exception is a finding." Source: sections "Rules belong in tools, not prompts" and "Retro", item 3.
- Retro fixes that are environment, not reminders: make the safe setting the default in the local profile; a
  lock file so a verify tool refuses a second run for a persona already running; label each research claim with
  how it was checked (run here, read in source, docs only). Source: section "Retro".
- Cited there, not checked here: He et al., MSR 2026, Cursor adoption brought about 30% more static-analysis
  warnings and 41% more complexity. UNVERIFIED beyond the note.
- A portable one-paragraph review prompt ending "Zero findings is a valid result." Source: section "Portable
  prompt".

---

## 2. The triage gate

### 2.1 How claude-mods implements it, exactly

- It is a **mod**, "a plugin that runs code inside Claude Code and can show you panes, bands, buttons and toasts",
  needing "a Claude Code build with mods (tested on 2.1.296; the mod API is early access and can change)". Its
  `hooks/hooks.json` is `{ "modules": ["./register.tsx"] }`, not the command-hook schema. Sources:
  [README](https://github.com/a-pavithraa/claude-mods), `plugins/triage-gate/hooks/hooks.json`.
- **Events** (`plugins/triage-gate/hooks/register.tsx`, `register`): `tool.call` for `Bash` and `PowerShell` runs
  `gate()`; `tool.call` for `Edit` and `Write` marks the assessment stale; `turn.complete` raises a size toast;
  `prompt.submit` records what the user asked for; `command.run` serves `/gate`, `/gate approve`, `/gate details`,
  `/gate codex` and `/guide`; `ui.render` draws the Triage pane.
- **What it reads** (`shell.ts`, `commitIn`): it splits the shell command into segments, follows `cd`, `git -C` and
  nested `bash -c`, collects `git add` paths, and returns the commit's scope (`staged`, `tracked` or whole `tree`)
  only when a segment is `git commit`. Any other command passes untouched.
- **What it scores** (`register.tsx` `runTriage`, `blast.ts`, `verdict.ts`): `git diff HEAD --numstat` plus
  untracked files (first 30 read, 4000 chars each); for the first 15 files, `git grep` counts code files that name
  it (Java and Kotlin by class name as a word). Points, each kind capped: size (lines 150 → 1, 400 → 2; files 5 →
  1, 10 → 2; four or more top-level areas → 1; cap 3), reach (widest file used by 4 → 1, by 10 → 2; a build,
  schema, migration, workflow or infra path → 1; cap 2), risk and quality from Jev, an optional paid model at
  TypeSafe (cap 2 each). `HOLD_AT = 5`, `READ_AT = 2`. A path matching
  `auth|login|session|token|secret|credential|password|permission|acl|polic(y|ies)|security|crypto|\.env` is never
  a pass; Jev's security ≥ 0.7 is always a hold. Without a key, "triage uses the blast radius alone"
  (`plugin.json`, `typesafeApiKey`).
- **What it blocks and how**: on `hold`, `gate()` opens the pane and returns a string; the `tool.call` handler
  returns `{ deny: held }`, so the commit's Bash call is denied with this message to Claude: "triage-gate held this
  commit for human review. Why: ... Do not retry the commit or work around this hold. Tell the user: they can read
  the change, run /gate codex for a Codex review, or run /gate approve to let this exact change through."
  `read` lets the commit through with a toast. Source: `register.tsx`, `gate`.
- **Approval**: a fingerprint of the paths and blob hashes the commit would take (`git diff --raw`, `git hash-object
  --stdin-paths` for untracked files; `fingerprintOf`). `/gate approve` or the pane's button adds the fingerprint
  to an `approved` atom, after re-checking the tree still matches; any later edit makes it stale. The approval
  text is put in the user's prompt box, never sent by the mod. Source: `register.tsx`, `approve`, `approveAndAsk`.
- Exit codes and JSON output: none. The mod API returns `{ deny }` from a handler. This is the part with no
  equivalent in command hooks and the reason the README says "it has to stop the commit, and the pane and buttons
  are how you review and approve".

### 2.2 What each harness can do with command hooks

| Capability | Claude Code | Codex | Kiro |
| --- | --- | --- | --- |
| Run a script before a shell command and deny it | Proven: `PreToolUse`, matcher `Bash`, JSON `permissionDecision: "deny"` or exit 2 with stderr ([hooks reference](https://code.claude.com/docs/en/hooks), "How a hook resolves", "Exit code 2"; table row "`PreToolUse` \| Yes \| Blocks the tool call") | Proven: `PreToolUse`, matcher `Bash`, same JSON shape, older `{"decision":"block"}`, or exit 2 with stderr ([Codex hooks](https://learn.chatgpt.com/docs/hooks), section "PreToolUse"). Runs only after the developer trusts the hook's hash (same page, "Trust") | Proven: `PreToolUse` command hook, matcher `shell` (the built-in category) or a regex on the tool ID; any non-zero exit blocks the call and sends stderr to the agent ([Hook actions](https://kiro.dev/docs/hooks/actions/), [Hook triggers](https://kiro.dev/docs/hooks/types/), "Pre Tool Use") |
| What the script reads | `tool_name`, `tool_input.command` on stdin (hooks reference, step 1) | `tool_name`, `tool_input.command` for Bash (Codex hooks, "PreToolUse" fields) | `tool_name`, `tool_input` on stdin (Hook triggers, MCP example and `PermissionRequest` example). The field name of the shell tool's command is UNVERIFIED on this page |
| Tell the agent something without blocking | `additionalContext` on `UserPromptSubmit`/`SessionStart`; plain stdout on those events (hooks reference, "Exit code 0") | `hookSpecificOutput.additionalContext` on `PreToolUse`, `SessionStart`, `UserPromptSubmit`; 2,500-token cap unless `additionalContextLimit` is set (Codex hooks, "Large hook output") | Exit 0 stdout "is added to the agent's context" (Hook actions). Arrives as a `HOOK_INSTRUCTION` block, which this session's own system prompt describes; UNVERIFIED in the public docs |
| Force another turn at Stop | Proven: `decision: "block"` or exit 2 (hooks reference; table row "`Stop` \| Yes") | Proven: `{"decision":"block","reason":...}` becomes a continuation prompt (Codex hooks, "Stop") | Documented only for `SubagentStop` (`{"decision":"block","reason"}` or exit 1 gives the subagent one more turn). For the main `Stop`, the docs say stdout goes to the agent's context; whether it forces a turn is UNVERIFIED (Hook triggers, "Agent Stop", "Subagent Stop") |
| Pane, buttons, toast, prompt-box fill | Mod API only, early access | None documented | None documented |
| Hook file the harness would write | `.claude/settings.json` (already) | `.codex/hooks.json` (already) | `.kiro/hooks/<name>.json`, `{"version":"v1","hooks":[{"name","trigger","matcher","action":{"type":"command","command"}}]}` ([Hooks](https://kiro.dev/docs/hooks/)); not written today |

What the harness already has on each: `guard.sh` is a `PreToolUse` hook on `Bash|Edit|Write|MultiEdit` (Claude)
and `Bash|apply_patch` (Codex) that reads `tool_name` and `tool_input.command` from stdin and prints the deny JSON
(`assets/project/.claude/hooks/guard.sh:10-30`; `SKILL.md`, "Limits": Codex 0.166 let an `apply_patch` through on
exit 2, so the JSON shape is the one to use). `verify-on-stop.sh` prints `{"decision":"block","reason":...}` at
Stop and honours `stop_hook_active` (`verify-on-stop.sh:118-135`). Both scripts are bash; Kiro gets nothing today,
and the integrity check in CI is the backstop for all tools (`references/gates.md`, last section).

### 2.3 The port

The deterministic half of the triage gate is a third case in `guard.sh`, or a sibling `triage.sh` registered on
the same event, on all three tools:

1. Recognise `git commit` in the command. `guard.sh` already greps commands for `git push --force` and `git reset
   --hard`; a port needs the `shell.ts` logic (segments, `cd`, `git -C`, `git add` paths, `-a`) or a deliberately
   narrower rule: any segment whose words start `git commit`, scoring the whole working tree. The narrower rule
   over-holds when the agent commits a small staged subset of a big tree. Design choice, UNVERIFIED either way.
2. Score: `git diff HEAD --numstat`, untracked files, `git grep -w -F <ClassName>` for the first 15 Java files, the
   risky-path and sensitive-path regexes, the same point caps and `HOLD_AT`. All are git and grep; the thresholds
   are the mod's, tuned on its author's repositories, not on a Spring Boot codebase (UNVERIFIED fit).
3. Deny with the message the mod uses, minus `/gate`, plus the approval instruction for that tool.
4. Approval without a pane: the human runs `python3 .claude/hooks/triage.py approve` (or `bash triage.sh approve`)
   in their own terminal; it writes the fingerprint to `.git/harness/approved`. The hook passes a commit whose
   fingerprint is listed and removes the entry. The agent can run the same command through `Bash`, so `guard.sh`
   should refuse any command naming the approval script, the way it refuses the record flags
   (`references/gates.md`, "`.claude/hooks/guard.sh`"). Still advisory, like every hook in the harness.
5. CI backstop: a step in `harness-integrity.yml` (or a sibling) computes the same score on the pull request's
   diff against its base and fails above `HOLD_AT` unless a maintainer adds a label, mirroring
   `harness-rule-change`. This is the only part that holds on a tool with no hooks at all.

What cannot be ported anywhere: the Triage pane and its buttons, the toast at turn end, filling the prompt box,
`/gate codex` running Codex inside the session, and Jev's security, data, money and concurrency judgements (a paid
API that would send up to 60k characters of diff off the machine; the harness adds no network calls today). On
Kiro specifically: the hook file format differs, the shell tool's input field name must be checked, and the
Stop-hook continuation is undocumented, so `verify-on-stop.sh` should not be promised on Kiro until tried.

### 2.4 Review and classification without `/gate codex` and without Jev

The mod's two model-backed parts, `/gate codex` (a Codex review of the held change) and Jev (risk and quality
scores), both have substitutes that need no mod API.

**Review of a held commit.** Three routes, strongest last:

| Route | How | Where it is proven |
| --- | --- | --- |
| A. The deny message tells the host agent to run the review in a subagent | The hold reason says: "run the `code-reviewer` skill in a fresh subagent on `git diff HEAD`, with `REVIEW.md` from the base branch, write its report to `.git/harness/review-<fingerprint>.md`, then stop and show the human". The hook passes the commit only when the human has approved; the report is for the human | Claude: Agent tool and forked skills ([headless docs](https://code.claude.com/docs/en/headless), "Follow subagent messages"). Kiro: `invoke_sub_agent` (this session's tool list). Codex: subagent support is UNVERIFIED in the docs read here; fall back to route B |
| B. The hook runs a headless review itself | On hold, the hook runs `codex exec review`-style or `claude -p` with the diff on stdin and `REVIEW.md` in the prompt, saves the final message, and quotes its first lines in the deny reason. Cross-model when both CLIs are present: a Claude session asks Codex, a Codex session asks Claude | `claude -p` reads piped stdin and is shown as a diff reviewer in the docs ("Add Claude to a build script"); `codex exec` reads piped stdin, `-o` writes the final message ([non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)). Hook `timeout` must be raised; the default hook budget is seconds, a review is minutes |
| C. CI review | The PR workflow runs the same headless review on the PR diff and posts it; the hold only tells the human "wait for the CI review" | Tool-independent; the harness already has `harness-integrity.yml` and Claude Code's GitHub review (`SKILL.md` table) |

Route A keeps the author agent in charge of launching its own reviewer, so the hook should check for the report
file, not trust the agent's word; a subagent gets a fresh context, which is the property `/gate codex` bought
with a second model. Route B is closest to the mod and the only one that gives a second model locally, but the
learnings note says a second model agreeing "leaves the claim untested" (§1.6), so prefer route A where the host
has subagents and treat B as the fallback for hosts without them, not as an upgrade. Both are
opt-in by environment variable (`HARNESS_TRIAGE_REVIEWER=subagent|claude|codex|off`), defaulting to A where
the host has subagents and to "off" elsewhere, so a hold with no reviewer still holds.

**Classification (Jev's security, data, money, concurrency scores).** Three layers, each optional:

1. Deterministic, always on: extend the mod's sensitive-path regex with content greps the harness already cares
   about: `@Transactional`, `BigDecimal`, SQL migrations, `synchronized`/`ExecutorService`/`@Async`,
   `@PreAuthorize`/`SecurityFilterChain`, `*Client` calls. Each hit adds a point in its category with the mod's
   caps. Free, offline, testable in `tests/scripts`. Coarse: it flags the file type, not the bug.
2. Local model, opt-in: the same headless call as route B with a JSON schema, `{security, data, money,
   concurrency: number 0..1}`, over the diff. `claude -p --output-format json --json-schema` returns it in
   `structured_output` ([headless docs](https://code.claude.com/docs/en/headless), "Get structured output");
   `codex exec --output-schema schema.json -o scores.json` does the same ([non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)).
   The diff stays on the developer's existing tool account; no new vendor. Thresholds (`≥ 0.7` security is a
   hold, as in the mod) are a guess until counted on past PRs.
3. Jev, opt-in: when `TYPESAFE_API_KEY` is set, call it exactly as the mod does and use its scores in place of
   layer 2. Document that it sends up to 60k characters of diff to a third party; default off, as the mod itself
   does without a key (`plugin.json`, `typesafeApiKey`).

Layer 2 needs care: the hold decision then depends on a model, so the hook must treat a timeout, a missing
`structured_output` field or a malformed response as "unknown" and fall back to layers 1's score, never to
"pass". The docs warn that `structured_output` is absent when the run ends without valid output.

---

## 3. Candidate changes

Effort: S under an hour, M a day, L more. "Proven" means the mechanism is documented or already used in this
repo; "trial" means run `tests/harness-sample/check.sh` or a scenario before claiming it.

| # | Change | File in this repo | From | Effort | Claude / Codex / Kiro |
| --- | --- | --- | --- | --- | --- |
| 1 | Add the trace rule to the review template: entry point → changed lines → wrong result → strongest reason it can't happen → drop; "zero findings is a valid review" | `assets/project/REVIEW.md`, new first section | `REVIEW.md` §"Report a finding only when you can trace it"; `ai-code-review.md` steps 2 and 3 | S | Text; proven to be read by `code-reviewer` (`SKILL.md:10`) and Claude Code's GitHub review (`SKILL.md` table). Codex `review` and Kiro: trial |
| 2 | Cap findings at five, one per cause; name what wasn't checked; on a later round review only the new diff and don't repeat an answered finding | `assets/project/REVIEW.md` §Report | `REVIEW.md` §Report | S | As 1 |
| 3 | Add a "pre-existing" bucket that is reported but never fixed in the PR, and "a situation no supported entry point reaches" to Don't report | `assets/project/REVIEW.md` §Don't report | `REVIEW.md` §Severity P3, §Do not report | S | As 1 |
| 4 | Agent-fix rules: re-trace each finding and apply the consequence test yourself (normal user, normal work, frequency times severity); the reviewer's tag does not decide; fix what passes, answer the rest in one line with the reason; after two rounds ask the user (the template already says two); fix the class, not the line | `assets/project/AGENTS.md`, "How to work here", the pull-request bullet | `ai-code-review.md` §"When an agent fixes the findings"; `ai-code-review-learnings.md` §"What the replay actually showed" (13 of 13 tagged P1) | S | Text; proven read by Claude and Codex (`SKILL.md` table, `AGENTS.md`). Kiro reads `AGENTS.md`: trial |
| 5 | One line telling any reviewer to read `REVIEW.md` first, so reviewers outside `code-reviewer` see it | `assets/project/AGENTS.md`, "How to work here" | private `AGENTS.md` diff, line 101 | S | As 4 |
| 6 | Risk paths from history: in `SKILL.md` step 4, derive `REVIEW.md`'s High list from `git log --format= --name-only` counts over `fix` commits, and say so in the template comment | `SKILL.md` step 4; `assets/project/REVIEW.md` §Risk comment | `modular-code-research.md` §2 "This repo's history"; `REVIEW.md` §Risk | S (instruction) or M (a `scripts/hotspots.py`) | Instruction proven; script needs a test under `tests/scripts` |
| 7 | Add the "one line each time a review misses a bug" list with a worked example of the shape (entry point, what happened, what to check), without the real codebase's items | `assets/project/REVIEW.md` §Failures comment | `REVIEW.md` §Always report; `ai-code-review.md` table | S | Text |
| 8 | Triage gate, deterministic half: `git commit` detection, blast score, deny JSON, file-based approval, guard refusal of the approval command | `assets/project/.claude/hooks/triage.sh` (new) or a case in `guard.sh`; `.claude/settings.json` and `.codex/hooks.json` matcher groups; `scripts/apply_harness.py` `HOOKS` tuple and `check-protected.sh` | claude-mods `shell.ts`, `blast.ts`, `verdict.ts`, `register.tsx` | M | Claude: proven mechanism. Codex: proven mechanism, trust step. Kiro: proven block-on-nonzero, but needs item 10 first. Thresholds: trial on `tests/harness-sample` and on a real codebase |
| 8b | Triage gate, review and classification: deny message that asks for a subagent review and checks for the report file; opt-in headless review (`HARNESS_TRIAGE_REVIEWER`); deterministic content greps for security / data / money / concurrency; opt-in model scores by JSON schema; Jev only with `TYPESAFE_API_KEY` | `triage.sh`; a `triage-schema.json`; `SKILL.md` "Limits" for the opt-in flags | §2.4; claude-mods `jev.ts`, `verdict.ts` | M | Headless CLIs and JSON schema proven for Claude and Codex (docs cited in §2.4). Kiro headless and Codex subagents: trial. Thresholds: trial |
| 9 | Triage gate, CI half: score the PR diff against base and require a label above the hold threshold | `assets/project/.github/harness/check-blast.sh` (new), step in `harness-integrity.yml` | claude-mods `verdict.ts`; harness `harness-rule-change` pattern (`references/gates.md`) | M | Proven pattern on all tools (CI is tool-independent) |
| 10 | Kiro registration: write `.kiro/hooks/harness.json` with `PreToolUse` on `shell` running `guard.sh` (and `triage.sh`), and `SessionStart`; add it to the integrity check's registration list | `scripts/apply_harness.py` (template loop at line 914), new `assets/project/.kiro/hooks/harness.json`, `check-protected.sh` | Kiro [Hooks](https://kiro.dev/docs/hooks/), [triggers](https://kiro.dev/docs/hooks/types/) | M | Kiro only. Block on non-zero exit is proven; `guard.sh` prints the Claude deny JSON and exits 0, so on Kiro it must exit non-zero instead: trial. Stop hook: leave out until 2.2's open question is answered |
| 11 | Pull request template: how tested, what could break, how to revert, which `REVIEW.md` rules the change touches | `assets/project/.github/pull_request_template.md` (new); `apply_harness.py` | `ai-code-review.md` step 1 ("Start with the promise"); harness `AGENTS.md` already asks for the first three in prose | S | Proven (GitHub feature); no tool dependency |
| 12 | Evaluation: before adopting 1 to 4, replay the old and new `REVIEW.md` on the same planted-bug sample, several runs per case, failed runs saved as failed rather than "no findings", and count findings per confirmed bug, as the README's 6-of-6 trial did | `tests/harness-sample/` or `tests/baseline-results/` | `ai-code-review.md` §"Check whether this helps"; `ai-code-review-learnings.md` §"Building a replay harness: traps"; `README.md:15` | M | Tool-independent |
| 13 | Add to `REVIEW.md` §Always report: "Code moved only to satisfy a lint or architecture exception is a finding." The harness's `check-file-size.sh` and the `FreezingArchRule` ratchet can both be met by moving code | `assets/project/REVIEW.md` §Always report | `ai-code-review-learnings.md` §"Rules belong in tools", Retro item 3 | S | Text |
| 14 | Seed the Failures section with the shape of the two patterns both prompts missed, as examples the team replaces: a setting required at startup when its feature is off (ties to `ConfigurationKeysTests`); an external API rejecting a request at one of its limits | `assets/project/REVIEW.md` §Failures comment | `ai-code-review-learnings.md` §"What the replay actually showed" | S | Text |
| 15 | Optional triage score for the fixing agent: frequency (1-10) times severity (1-10), under 5 filed in `docs/known-gaps.md` and not fixed | `assets/project/AGENTS.md` pull-request bullet, or `REVIEW.md` §Report | `ai-code-review-learnings.md` §"What the replay actually showed" (dropped 5 of 17) | S | Text; one data point, trial |
| 16 | Verification lock: browser verification refuses a second run for a persona already running (lock file) instead of relying on a doc rule | `references/browser-verification.md` and whatever verify script the harness ships | `ai-code-review-learnings.md` Retro item 2 | S/M | Needs a check of what the harness's verification does today |
| Don't | Port P0 to P3 numbering | `assets/project/REVIEW.md` | `REVIEW.md` §Severity | — | The harness template uses High / Medium / Low and `code-reviewer` prints Critical / High / Medium / Low (`code-reviewer/SKILL.md:91-108`). Two vocabularies in one project would cost more than the numbers add. Keep the levels, add the pre-existing bucket (item 3) |
| Don't | Port the real codebase's "Always report" items, its risk paths, or its invariant numbering | — | `REVIEW.md` | — | Domain-specific; the template's comment already tells the team to fill these in |
| Don't | Port Jev / TypeSafe scoring as the default | — | claude-mods `jev.ts` | — | Paid API, sends diff off the machine, thresholds tuned on another model; the harness adds no network calls by default. Keep it as the opt-in third layer in §2.4 |
| Don't | Port the pane, toast, prompt-box fill, `/gate codex`, `/guide` | — | claude-mods `register.tsx`, `pane.tsx` | — | Mod API only; no equivalent on any tool's command hooks |
| Don't | Port deslop-please, oxlint or dependency-cruiser items | — | `modular-code-research.md` §3, §5 | — | Rust-only or frontend; the Java side (cycles, boundaries, ratchet) is already `ModuleBoundariesTests` and `FreezingArchRule` |
| Don't | Add a file-length or complexity gate | — | `modular-code-research.md` §2 | — | No evidence-based threshold; the 20 KB rule stays justified as agent read size, not as a defect predictor |

---

## 4. Open questions

1. Kiro `Stop`: does a non-zero exit or `{"decision":"block"}` on the main agent's Stop force another turn, as it
   does for `SubagentStop`? The public docs don't say. Until tried, `verify-on-stop.sh` is Claude and Codex only.
2. Kiro shell tool input: the `PreToolUse` stdin shows `tool_name` and `tool_input`, but the field that holds the
   command for `execute_bash` / `execute_pwsh` is not on the triggers page. Run a logging hook once to see it.
3. Kiro on Windows: the harness hooks are bash and rely on Git for Windows (`SKILL.md`, "Limits"). Whether Kiro's
   command action finds `bash` on PATH there is untested.
4. Thresholds: the mod's `HOLD_AT = 5`, 150/400 lines and 5/10 files were tuned on its author's repositories. A
   Spring Boot change that adds an entity, a migration, a repository, a service, a controller and two tests already
   scores size 2 (7 files) + reach 1 (migration) = 3, "read" not "hold". Whether that is the right line for a
   Boot codebase needs a count over past PRs, as item 12 proposes for the review rules.
5. Approval token: a file under `.git/harness/` is outside the tree, so CI can't see it, and an agent can write it
   with `Bash` unless `guard.sh` refuses the command. Is an advisory hold enough, or must the CI label (item 9) be
   the only approval that counts?
6. Scope of the commit check: whole working tree (simple, over-holds staged subsets) or the mod's exact `git add`
   parsing (about 200 lines of shell-splitting to port to bash)?
7. Does the real codebase's finding that fixes cluster in external-system calls and configuration hold on a second
   codebase? If so, `REVIEW.md`'s default Risk line should name `*Client`, `*Properties` and `application*.yml`
   before "security configuration".
