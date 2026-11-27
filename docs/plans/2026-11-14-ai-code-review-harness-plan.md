# AI code review in the team harness: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the reviews the harness drives quieter and truer (trace a finding before reporting it), make the agent that fixes findings re-check them instead of fixing everything, hold a commit whose blast radius is large until a person reads it, and give every tool, Kiro included, the same guard.

**Architecture:** Phase 1 is text: the `REVIEW.md` and `AGENTS.md` templates and the `code-reviewer` skill carry the trace rule, the finding cap and the fix rule, and a replay on the sample project decides whether the new text ships. Phase 2 is a hotspot script so `REVIEW.md`'s risk list comes from `git log`, and a pull request template. Phase 3 is the triage gate: one bash scorer under `.github/harness/` used by a new `PreToolUse` hook on `git commit` and by a CI step, with a file-based approval the human writes. Phase 4 is a Kiro spike that decides whether the hooks can register there.

**Tech Stack:** Bash hooks (Git for Windows on Windows), Python 3 scripts and `unittest`, GitHub Actions, Markdown templates rendered by `apply_harness.py`.

**Spec:** `docs/plans/2026-11-14-ai-code-review-research.md` (sections §1.1 to §1.6, §2.3, §2.4, table §3). Each task names the table row it implements.

## Global Constraints

- This repository is public. Name no client, client project or client data in code, docs, commits or pull requests; write `a real codebase` instead (`AGENTS.md`).
- Every hook stays a bash script that both Claude Code and Codex run; a refusal prints the deny JSON and exits 0 (`SKILL.md` "Limits": Codex 0.166 let an `apply_patch` through on exit 2).
- Every file the harness writes is tracked in `.claude/harness.lock` by `apply_harness.py`, and rerunning the script on an applied project changes nothing (`tests/harness-sample/check.sh`).
- `tests/scripts/test_docs.py` must stay green: every hook is named in `SKILL.md`, every script test is described in `tests/README.md`.
- Severity vocabulary stays High / Medium / Low in `REVIEW.md` and Critical / High / Medium / Low in `code-reviewer`; do not introduce P0 to P3 (spec §3 "Don't").
- The harness adds no network calls. Headless review and model scoring (spec §2.4 layers 2 and 3) are not in this plan.
- This branch was cut from `main` at `dd1395a`. The recorded-decision gate (`RecordedDecisionsTests`, `recorded_decisions`, the `undecided` refusal in `guard.sh`) lives on `harness/recorded-decisions` and is not here; don't reference it. Both branches add to `guard.sh`, `test_harness_hooks.py`, `SKILL.md`, `AGENTS.md` and `tests/README.md`, so expect a mechanical merge later.
- Script tests: `python -m unittest tests.scripts.<module>`; the whole suite `python -m unittest discover -s tests/scripts` takes about four minutes on Windows.

## Review Focus

Failure modes the spec implies that no task's tests would otherwise exercise; each has a test pinned to the task that owns it.

1. A commit command inside a chained line (`cd backend && git commit -m x`) or with `-C` must still be scored; a `git commit` inside a quoted string of another command must not. (Task 7)
2. An approval written for one tree must not pass a different tree: one more edit after approval makes it stale. (Task 7)
3. The agent must not be able to approve itself through `Bash`: `guard.sh` refuses the approval command and writes to the approval file. (Task 7)
4. A repository with no commits yet, or a change with only untracked files, must score without `git diff HEAD` failing. (Task 6)
5. The CI step must run the base branch's copy of the scorer, so a pull request can't lower its own score. (Task 8)

---

## Phase 1: the review text, and proof it helps

### Task 1: `REVIEW.md` template carries the trace rule, the cap and the pre-existing bucket

Spec rows 1, 2, 3, 7, 13, 14.

**Files:**
- Modify: `plugins/springboot-architecture/skills/spring-boot-team-harness/assets/project/REVIEW.md`
- Test: `tests/scripts/test_docs.py`

**Interfaces:**
- Produces: the exact phrases Task 2 and Task 3 point at: "trace it", "Zero findings is a valid review", "at most five findings", "pre-existing".

- [ ] **Step 1: Write the failing test** in `tests/scripts/test_docs.py`, class `DocsNameWhatShipsTests`:

```python
def test_the_review_template_states_the_trace_rule_the_cap_and_the_fix_rule(self):
    review = text(ASSETS / "project" / "REVIEW.md")
    for phrase in ("Zero findings is a valid review", "at most five findings", "pre-existing",
                   "strongest reason it cannot happen", "only the new diff",
                   "moved only to satisfy"):
        self.assertIn(phrase, review)
```

`ASSETS` is the constant the file already uses for the skill's `assets/` folder; add it if the module only has `SKILL`-level paths.

- [ ] **Step 2: Run it:** `python -m unittest tests.scripts.test_docs -k trace_rule`. Expected: FAIL on "Zero findings is a valid review".

- [ ] **Step 3: Edit the template.** Keep the existing sections and placeholders. Changes, in order:
  - New section after the intro, titled `## Report a finding only when you can trace it`, three sentences: start at a supported entry point (a user action, a route the UI calls, a scheduled job, an external event, data the schema allows); follow it through the changed lines to a wrong result someone sees; look for the strongest reason it cannot happen (an earlier guard, a type, a database constraint, server-side validation, a caller that never sends that value) and drop the finding if one holds. Last line: `Zero findings is a valid review.`
  - In `## Failures`, extend the comment with the shape of two patterns, marked as examples to replace: "a setting the app needs at startup when its feature is off" and "an external API refusing a request at one of its documented limits" (spec §1.6).
  - New bullets at the end of `## Failures`, outside the comment: "A contract change (request, response, event, config key) with no doc update." "A comment the change makes untrue." "Code moved only to satisfy a rule: a file split, a method moved to another class, or an exception added so a check passes while its aim is defeated."
  - In `## Risk`, add a comment on the first bullet: `<!-- Replace with the packages scripts/hotspots.py lists for this repository; see the harness skill, step 4. -->`
  - In `## Don't report`, add: "A situation no supported entry point reaches." and "A choice a decision record documents (`docs/decisions/`): read it before calling the choice a bug."
  - Replace `## Report` with: file and line for every finding; entry point, what happens, wrong result; at most five findings, one per cause, most serious first; mark findings in code the change didn't touch as pre-existing, and never fix them in this pull request; end with the count or "No issues found" and name what could not be checked; on a later round review only the new diff and don't repeat a finding that has an answer.

- [ ] **Step 4: Run it:** `python -m unittest tests.scripts.test_docs`. Expected: PASS.

- [ ] **Step 5: Commit:** `git add plugins/.../assets/project/REVIEW.md tests/scripts/test_docs.py && git commit -m "harness: REVIEW.md asks for a trace before a finding, caps findings at five"`

### Task 2: `AGENTS.md` template points reviewers at `REVIEW.md` and tells the fixing agent to re-trace

Spec rows 4, 5, 15.

**Files:**
- Modify: `plugins/springboot-architecture/skills/spring-boot-team-harness/assets/project/AGENTS.md`, section "How to work here", last bullet (the pull-request bullet)
- Modify: `plugins/springboot-architecture/skills/spring-boot-team-harness/SKILL.md`, table row `REVIEW.md`
- Test: `tests/scripts/test_docs.py`

**Interfaces:**
- Consumes: phrases from Task 1.

- [ ] **Step 1: Write the failing test** in `test_docs.py`:

```python
def test_the_agents_template_sends_every_reviewer_to_review_md_and_makes_the_fixer_re_trace(self):
    agents = text(ASSETS / "project" / "AGENTS.md")
    self.assertIn("read `REVIEW.md` first", agents)
    self.assertIn("re-trace", agents)
    self.assertIn("frequency", agents)
```

- [ ] **Step 2: Run it.** Expected: FAIL on "read `REVIEW.md` first".

- [ ] **Step 3: Edit `AGENTS.md`.** Add a bullet before the pull-request bullet: "Reviewers, people or agents, read `REVIEW.md` first. It says what to report, what to skip, and how." Rewrite the pull-request bullet's review sentences to: "Before you open a pull request, review the branch's changes with the `code-reviewer` skill (in a fresh subagent where the tool has one) and write the description with the `pr` skill, if they are installed. In the review, search the repository's own code for code like what the branch adds, so a copy of existing logic shows up. For each finding, re-trace it yourself: a reviewer's severity tag does not decide. Fix it when a normal user doing normal work would hit it, judged by frequency times harm; answer the rest in one line with the reason, and file a follow-up in `docs/known-gaps.md` rather than widening the change. Fix the class of bug, not one line. Then review only the new changes; after two rounds, ask the user instead of starting a third." Keep the sentence about the description.

- [ ] **Step 4: Edit the `SKILL.md` table row `REVIEW.md`** to end: "Added only when missing; the team fills in the failures, one line each time a review misses a bug, and the risk packages from `scripts/hotspots.py` (Task 5)". Adjust once Task 5 names the script.

- [ ] **Step 5: Run** `python -m unittest tests.scripts.test_docs`. Expected: PASS.

- [ ] **Step 6: Commit:** `git commit -am "harness: every reviewer reads REVIEW.md; the fixing agent re-traces each finding"`

### Task 3: `code-reviewer` skill applies the trace rule and the cap when `REVIEW.md` is absent too

Spec row 1 (the reviewer side).

**Files:**
- Modify: `plugins/springboot-architecture/skills/code-reviewer/SKILL.md`, section "## Rules" (lines 10 to 16) and the report format section (around lines 91 to 108)

- [ ] **Step 1: Add three rules** after the `REVIEW.md` rule: "Report a finding only when you can trace it from a supported entry point through the changed lines to a wrong result, and no earlier guard, type, constraint or caller rules it out. Zero findings is a valid review." "At most five findings, one per cause, most serious first. Name what you could not check." "Mark findings in code the change didn't touch as pre-existing; the author answers those, and doesn't fix them in this change."

- [ ] **Step 2: In the report format**, add under each finding the lines `Entry point:`, `What happens:`, `Wrong result:` next to the existing file and line.

- [ ] **Step 3: Check by reading** that nothing in the skill now contradicts `REVIEW.md` (levels stay Critical / High / Medium / Low). Run `python -m unittest tests.scripts.test_docs`. Expected: PASS.

- [ ] **Step 4: Commit:** `git commit -am "code-reviewer: trace before reporting, five findings at most"`

### Task 4: Replay the old and new review text on the sample and decide

Spec row 12. This task decides whether Tasks 1 to 3 merge; it produces a result file, not code.

**Files:**
- Create: `tests/baseline-results/review-replay-2026-11.md`
- Read: `tests/harness-sample/README.md` (the planted mistakes), `README.md:15` (the earlier 6-of-6 trial)

- [ ] **Step 1: Build the sample.** Pick the planted mistakes `check.sh` describes that a reviewer could find by reading (`System.out`, the self-invoked `@Async`, the controller using a repository, the client without a timeout, the logged email) and two clean changes (a renamed test, a new DTO field). Each case is one commit on a copy of `tests/harness-sample/project` with the harness applied; write a one-sentence answer key per case before any run.

- [ ] **Step 2: Run each case three times with each template**, the old `REVIEW.md` (from `git show main:plugins/.../assets/project/REVIEW.md`) and the new one, with the `code-reviewer` skill in a fresh subagent. Save each raw review as it finishes to `tests/baseline-results/review-replay-raw/<case>-<template>-<run>.md`; a run that fails (quota, timeout) is saved with `-failed` in the name and counted as failed, never as "no findings".

- [ ] **Step 3: Grade blind.** Shuffle the raw files, grade each finding as confirmed or not against the answer key, then unshuffle. Record per template: confirmed ÷ reported, known bugs found ÷ planted, findings on clean cases, failed runs.

- [ ] **Step 4: Write the result file** with the table, the per-run variation (the same case across three runs), and the decision rule from the spec: adopt when triage noise fell with no planted bug lost. If a planted bug is lost, revert the text that lost it (bisect by section) before Task 5.

- [ ] **Step 5: Commit:** `git add tests/baseline-results/review-replay-2026-11.md tests/baseline-results/review-replay-raw && git commit -m "tests: replay of the old and new REVIEW.md on the sample"`

---

## Phase 2: risk from history, and the pull request shape

### Task 5: `scripts/hotspots.py` lists the paths past fixes clustered in

Spec row 6.

**Files:**
- Create: `plugins/springboot-architecture/skills/spring-boot-team-harness/scripts/hotspots.py`
- Modify: `plugins/springboot-architecture/skills/spring-boot-team-harness/SKILL.md`, step 4 and the "What each piece does" table
- Modify: `tests/README.md` (describe the new test)
- Test: `tests/scripts/test_hotspots.py`

**Interfaces:**
- Produces: `hotspots(root: Path, since: str | None = None, limit: int = 10) -> list[tuple[str, int, int]]` returning `(path, fix_commits, all_commits)` sorted by `fix_commits` descending, where a fix commit is one whose subject matches `(?i)\b(fix|bug|revert|hotfix|regression)\b`; CLI `python3 hotspots.py <project> [--since 2025-01-01] [--limit 10] [--by package]`, `--by package` collapsing paths to their directory. Output: one line per entry, `fixes/commits  path`, then a footer `Top directories by fixes:` with the three most frequent directories. Skips `src/test/`, migrations and non-code files by the same extension list `check-file-size.sh` uses.

- [ ] **Step 1: Write the failing test** `tests/scripts/test_hotspots.py`, class `HotspotsTests`, using a temporary git repository built with `subprocess` (`git init`, `git -c user.name=t -c user.email=t@t commit`):

```python
def test_counts_fix_commits_per_file_and_ranks_them(self):
    # three commits: "feat: add A" touching a/A.java and b/B.java; "fix: A null" touching a/A.java;
    # "Fix regression in A" touching a/A.java and src/test/a/ATest.java
    result = hotspots.hotspots(self.root)
    self.assertEqual(result[0], ("src/main/java/a/A.java", 2, 3))
    self.assertEqual(result[1], ("src/main/java/b/B.java", 0, 1))
    self.assertNotIn("src/test/a/ATest.java", [path for path, _, _ in result])

def test_by_package_collapses_to_directories_and_since_limits_the_range(self):
    ...  # --by package gives ("src/main/java/a", 2, 3); --since a date after the first commit drops it
```

- [ ] **Step 2: Run:** `python -m unittest tests.scripts.test_hotspots`. Expected: FAIL, module not found.

- [ ] **Step 3: Implement** `hotspots.py` with `git log --since <date> --format=%x1e%s --name-only` parsed in one pass; `main()` with `argparse`.

- [ ] **Step 4: Run** the test. Expected: PASS.

- [ ] **Step 5: Docs.** In `SKILL.md` step 4 add: "Run `python3 ${CLAUDE_SKILL_DIR}/scripts/hotspots.py . --by package` and put the top directories in `REVIEW.md`'s Risk section as High, before the generic entries; on a real codebase fixes clustered in short files that call an external system and in configuration, not in long files." Add a table row for `scripts/hotspots.py`. Add one line to `tests/README.md` for `test_hotspots.py`. Run `python -m unittest tests.scripts.test_docs`. Expected: PASS.

- [ ] **Step 6: Commit:** `git add ... && git commit -m "harness: hotspots.py ranks files by fix commits for REVIEW.md's risk list"`

### Task 6: Pull request template

Spec row 11.

**Files:**
- Create: `plugins/springboot-architecture/skills/spring-boot-team-harness/assets/project/.github/pull_request_template.md`
- Modify: `plugins/springboot-architecture/skills/spring-boot-team-harness/scripts/apply_harness.py`, the block at lines 948 to 951 that adds `REVIEW.md` (add the template the same way: written when missing, kept when present, not tracked in the lock since the team edits it)
- Test: `tests/scripts/test_apply_harness.py`

**Interfaces:**
- Produces: the template with four headings: `## What and why`, `## How it was tested` (with a line "Runtime proof: `check_request.py` output or 'not verified at runtime'"), `## What could break and how to revert`, `## REVIEW.md rules this change touches`.

- [ ] **Step 1: Write the failing test** in `test_apply_harness.py`, next to the existing `REVIEW.md` test:

```python
def test_adds_a_pull_request_template_when_missing_and_keeps_the_teams(self):
    self.apply()
    template = self.project / ".github" / "pull_request_template.md"
    self.assertIn("## How it was tested", template.read_text(encoding="utf-8"))
    template.write_text("team's own\n", encoding="utf-8")
    self.apply()
    self.assertEqual(template.read_text(encoding="utf-8"), "team's own\n")
```

Use the fixture and `apply()` helper the file already has (check its name).

- [ ] **Step 2: Run** it. Expected: FAIL, file missing.
- [ ] **Step 3: Write the template and the `apply_harness.py` block.** Use `at_root(...)` as `REVIEW.md` does, since GitHub reads `.github/` at the repository root.
- [ ] **Step 4: Run** `python -m unittest tests.scripts.test_apply_harness`. Expected: PASS. Then `bash tests/harness-sample/check-in-docker.sh all` (or `check.sh all`) and confirm the rerun step still reports no changes.
- [ ] **Step 5: Commit.**

---

## Phase 3: the triage gate

### Task 7: `blast-score.sh` scores the uncommitted change

Spec row 8, scoring half. The scorer lives under `.github/harness/` so CI can run the base branch's copy; the hook sources it.

**Files:**
- Create: `plugins/springboot-architecture/skills/spring-boot-team-harness/assets/project/.github/harness/blast-score.sh`
- Test: `tests/scripts/test_harness_hooks.py`, new class `BlastScoreTests`

**Interfaces:**
- Produces: `blast-score.sh <base>` where `<base>` is a commit (`HEAD` for the working tree, the merge base in CI). Prints to stdout one line `score=<n> verdict=<pass|read|hold>` then one `reason: ...` line per point. Exit 0 always; errors to stderr. Environment: `HOLD_AT` (default 5), `READ_AT` (default 2). Points, each kind capped:
  - size: lines changed (added plus deleted, from `git diff <base> --numstat` plus every line of each untracked file) 150 → 1, 400 → 2; files 5 → 1, 10 → 2; four or more top-level areas → 1; area is the directory two levels below `src/main/java/` (the module) or the first path segment otherwise; cap 3.
  - reach: for the first 15 changed `.java` files, `git grep -lw <ClassName> -- '*.java' ':!src/test'` count minus itself; widest 4 → 1, 10 → 2; a path matching `pom\.xml|build\.gradle|gradle/|db/migration/|\.github/|infra/|Dockerfile|compose.*\.ya?ml|application.*\.(ya?ml|properties)` → 1; cap 2.
  - content: one point each for a category whose pattern appears in added lines (`git diff <base> -U0 | grep '^+'`): security `@PreAuthorize|SecurityFilterChain|HttpSecurity|@Secured|permitAll`, data `db/migration|@Entity|ddl-auto|DELETE FROM|DROP `, money `BigDecimal|Money|amount|price|invoice`, concurrency `synchronized|ExecutorService|@Async|@Scheduled|ConcurrentHashMap|AtomicLong|volatile`; cap 2.
  - a changed path matching `auth|login|session|token|secret|credential|password|permission|acl|polic(y|ies)|security|crypto|\.env` makes the verdict at least `read`.
  - verdict: `hold` when `score >= HOLD_AT`, else `read` when `score >= READ_AT`, else `pass`.

- [ ] **Step 1: Write the failing tests** in a temporary git repository (follow `IntegrityCheckTests.setUp` for the layout and `commit_as_base`):

```python
def test_a_small_change_passes(self):            # one file, 20 lines -> score=0 verdict=pass
def test_size_and_reach_add_up_to_a_hold(self):   # 11 files, 450 lines, a migration, a class used by 10 others -> score>=5 verdict=hold
def test_sensitive_paths_are_never_a_pass(self):  # one 5-line change to .../security/Policy.java -> verdict=read
def test_content_categories_are_capped_at_two(self):  # added lines with all four patterns -> content contributes 2
def test_an_empty_repository_and_untracked_only_changes_score(self):  # git init with no commit; base=HEAD must not fail
```

Each asserts on the `score=` line and on one `reason:` line.

- [ ] **Step 2: Run** `python -m unittest tests.scripts.test_harness_hooks -k BlastScore`. Expected: FAIL, script missing.
- [ ] **Step 3: Implement** `blast-score.sh` in bash with `git`, `grep`, `awk` only. When `<base>` can't be resolved (no commits), treat every tracked and untracked file as added.
- [ ] **Step 4: Run** the tests. Expected: PASS.
- [ ] **Step 5: Commit:** `git commit -m "harness: blast-score.sh scores a change by size, reach and content"`

### Task 8: `triage.sh` holds a `git commit` whose score reaches the threshold

Spec row 8, hook half; Review Focus 1, 2, 3.

**Files:**
- Create: `plugins/springboot-architecture/skills/spring-boot-team-harness/assets/project/.claude/hooks/triage.sh`
- Modify: `assets/project/.claude/hooks/guard.sh` (one new refusal in the `Bash` branch)
- Modify: `assets/project/.claude/settings.json` and `assets/project/.codex/hooks.json` (a second hook in the existing `PreToolUse` group for `Bash`, timeout 30)
- Modify: `scripts/apply_harness.py:54` `HOOKS` tuple (add `.claude/hooks/triage.sh`)
- Modify: `SKILL.md` table (new row `.claude/hooks/triage.sh`), `references/gates.md` (a section), `README.md` point 2, `tests/README.md`
- Test: `tests/scripts/test_harness_hooks.py`, new class `TriageHookTests`

**Interfaces:**
- Consumes: `blast-score.sh HEAD` from Task 7.
- Produces:
  - As a hook: reads the `PreToolUse` JSON on stdin; acts only when `tool_name` is `Bash` and the command has a segment (split on `;`, `&&`, `||`, `|`, newline, outside quotes) whose first words, after an optional `cd <dir> &&` prefix and `git -C <dir>`, are `git commit`. Runs the scorer; on `hold`, prints the deny JSON with reason: "Blocked by the team harness: this commit's blast radius scored <n> (hold at <HOLD_AT>): <reasons, comma separated>. Don't retry, split or amend the change to get under the limit. Tell the user the commit is held for a human read: they can review the diff, ask you to run the `code-reviewer` skill in a fresh subagent on `git diff HEAD` and show them its report, and then run `bash .claude/hooks/triage.sh approve` in their own terminal to let this exact change through." Appends an event line to `.git/harness/events.jsonl` with `"hook":"triage"` and the score, like `guard.sh`'s `block`. On `read` or `pass`, exits 0 with no output.
  - `triage.sh approve`: computes the fingerprint `sha256` of (`git diff HEAD --raw` sorted, plus `git ls-files --others --exclude-standard | git hash-object --stdin-paths`), appends it to `.git/harness/triage-approved`, prints the score and "approved for this exact tree". The hook, on `hold`, passes when the current fingerprint is in that file and removes the line.
  - `triage.sh score`: prints the scorer's output for the working tree, for people.

- [ ] **Step 1: Write the failing tests** (`self.guard(...)`-style helper `self.triage(payload, project)`):

```python
def test_commits_below_the_threshold_pass_silently(self)
def test_a_large_commit_is_held_with_the_score_and_the_approval_command(self)   # asserts "permissionDecision":"deny", "scored", "triage.sh approve"
def test_commit_is_found_after_cd_and_git_c_but_not_inside_a_quoted_string(self)  # Review Focus 1
def test_approval_passes_the_same_tree_once_and_goes_stale_after_an_edit(self)    # Review Focus 2
def test_other_commands_are_never_scored(self)   # git status, mvnw verify
def test_the_guard_refuses_the_agent_approving_or_writing_the_approval_file(self)  # Review Focus 3, in GuardHookTests
def test_a_hold_is_recorded_with_its_score(self)  # events.jsonl line has "hook":"triage"
```

- [ ] **Step 2: Run** `python -m unittest tests.scripts.test_harness_hooks -k Triage`. Expected: FAIL.
- [ ] **Step 3: Implement `triage.sh`.** Reuse `guard.sh`'s stdin parsing for `tool_name` and `command`. Segment splitting: a small awk state machine over the command tracking single and double quotes; simpler than the mod's TypeScript. `HOLD_AT` and `READ_AT` pass through to the scorer.
- [ ] **Step 4: Add the refusal to `guard.sh`'s `Bash` branch:** a command matching `triage\.sh[[:space:]]+approve|harness/triage-approved` → `block "approving a held commit is the user's call, from their own terminal. Tell them the commit is held and why." triage-approve`.
- [ ] **Step 5: Register the hook** in both JSON files inside the existing `PreToolUse` group whose matcher contains `Bash` (a second entry in its `hooks` array, `timeout: 30`). Add `.claude/hooks/triage.sh` to `HOOKS` in `apply_harness.py`. `check-protected.sh` already covers `.claude/hooks/*` and hook registrations.
- [ ] **Step 6: Run** `python -m unittest tests.scripts.test_harness_hooks tests.scripts.test_apply_harness tests.scripts.test_docs`. Expected: PASS once the docs name the hook. Then `check-in-docker.sh all`: the rerun step still reports no changes, and the existing Stop-hook scenario still passes.
- [ ] **Step 7: Docs.** `SKILL.md` table row: what it holds, that it is advisory, the approval command, and that `HOLD_AT` can be raised in the hook registration's environment. `references/gates.md`: the point table from Task 7. `README.md` point 2: one sentence. `tests/README.md`: the new tests.
- [ ] **Step 8: Commit:** `git commit -m "harness: triage.sh holds a large commit until a person approves it"`

### Task 9: CI scores the pull request and asks for a label above the threshold

Spec row 9; Review Focus 5.

**Files:**
- Modify: `assets/project/.github/workflows/harness-integrity.yml` (third step, same base-branch-copy pattern as the other two)
- Create: `assets/project/.github/harness/check-blast.sh`
- Test: `tests/scripts/test_harness_hooks.py`, new class `BlastCheckTests` (follow `FileSizeCheckTests`)

**Interfaces:**
- Consumes: `blast-score.sh <base>` from Task 7.
- Produces: `check-blast.sh <base-commit>`: runs the scorer against the merge base; prints `::notice::` with the score and reasons when `read`; on `hold`, prints `::error::` and exits 1 unless `HARNESS_BLAST_REVIEWED=true` (the `blast-reviewed` label), in which case `::warning::` and exit 0. Workflow step `env`: `HARNESS_BLAST_REVIEWED: ${{ contains(github.event.pull_request.labels.*.name, 'blast-reviewed') }}`.

- [ ] **Step 1: Write the failing tests:**

```python
def test_a_small_pull_request_passes(self)
def test_a_large_pull_request_fails_until_the_label_accepts_it_and_is_still_listed(self)
def test_the_workflow_runs_the_base_branch_copy_of_the_check(self)  # parse harness-integrity.yml: the step contains 'git show "$BASE:.github/harness/check-blast.sh"'
```

- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement** the script and the step. `check-blast.sh` sources `blast-score.sh` from its own directory, so the base copy of both must be fetched in the step: `git show "$BASE:.github/harness/blast-score.sh" > "$RUNNER_TEMP/blast-score.sh"` next to the check.
- [ ] **Step 4: Run** the tests, then `check-in-docker.sh all` for the rerun step. Expected: PASS.
- [ ] **Step 5: Docs:** `SKILL.md` table row for `harness-integrity.yml` gains the blast step and the `blast-reviewed` label; `tests/README.md`. Commit.

---

## Phase 4: Kiro

### Task 10: Spike: can Kiro run the guard and the triage hook

Spec row 10 and open questions 1 to 3. Output is a decision note, then either Task 11 or a line in `SKILL.md` "Limits".

**Files:**
- Create: `docs/plans/2026-11-14-kiro-hooks-spike.md`

- [ ] **Step 1: Log a payload.** In a scratch copy of `tests/harness-sample/project`, write `.kiro/hooks/log.json` with a `PreToolUse` command hook on matcher `shell` whose command is `cat >> /tmp/kiro-hook.jsonl` (per [Kiro hook triggers](https://kiro.dev/docs/hooks/types/)). Run one shell command in a Kiro session. Record the JSON: the `tool_name` value and the field that holds the command.
- [ ] **Step 2: Test blocking.** Change the command to `exit 1` and confirm the shell call is refused and stderr reaches the agent. Then test `guard.sh` as is: does Kiro honour the deny JSON with exit 0, or does the call go through?
- [ ] **Step 3: Test Stop.** Register `verify-on-stop.sh` on Kiro's agent-stop trigger and end a turn with a planted `@Async` self-call; record whether `{"decision":"block"}` or exit 1 forces another turn.
- [ ] **Step 4: Test Windows.** Repeat Step 1 on Windows and record whether Kiro finds `bash` on PATH.
- [ ] **Step 5: Write the note** with the four results and one of: "Task 11 as planned", "Task 11 with exit-code refusals only", or "Kiro gets AGENTS.md and CI only; add that line to Limits". Commit the note.

### Task 11: Kiro hook registration (only if the spike says yes)

**Files:**
- Create: `assets/project/.kiro/hooks/harness.json` with `PreToolUse` on the shell matcher running `guard.sh` and `triage.sh`, and the stop trigger running `verify-on-stop.sh` if Step 3 passed
- Modify: `guard.sh` and `triage.sh`: when the payload carries Kiro's `tool_name` (from the spike), refuse with the message on stderr and exit the code the spike found; the JSON path stays for Claude and Codex
- Modify: `apply_harness.py:914` template loop (add the Kiro file), `check-protected.sh` (add `.kiro/hooks/harness.json` to the registration case and `hook_entries` to its format), `SKILL.md`, `tests/README.md`
- Test: `test_harness_hooks.py` (`test_a_kiro_payload_is_refused_by_exit_code_with_the_reason_on_stderr`, and an `IntegrityCheckTests` case for unregistering the Kiro hook), `test_apply_harness.py` (the file is written and rerun changes nothing)

- [ ] Steps follow the Task 8 pattern: failing tests, implement, run, `check-in-docker.sh all`, docs, commit.

---

## Not in this plan, and why

- Headless review from inside the hook and model-based classification (spec §2.4 layers 2 and 3): the harness adds no network calls today, and the learnings note says a second model agreeing proves nothing. Revisit after Task 8 has run on a real codebase for a month and `report.py` shows how often holds happen.
- Checking for a review report file before releasing a hold: the hold is advisory and the human approves; add it only if `report.py` shows agents skipping the subagent review.
- A lock so browser verification refuses a second run for a persona in use (spec row 16): needs a read of what the verification skill generators ship; separate plan.
- The mod's exact `git add` parsing: Task 8 scores the whole working tree. If holds on small staged commits annoy people, port the staged-scope logic then.

## Self-review

- Spec coverage: rows 1 to 5 → Tasks 1 to 3; 6 → Task 5; 7, 13, 14 → Task 1; 8 → Tasks 7, 8; 9 → Task 9; 10 → Tasks 10, 11; 11 → Task 6; 12 → Task 4; 15 → Task 2; 16 → not in plan, stated. Every "Don't" row is honoured by the Global Constraints.
- Names: `blast-score.sh <base>` (Task 7) is what Task 8 and Task 9 call; `HOLD_AT`, `READ_AT`, `.git/harness/triage-approved`, `triage.sh approve|score` are used with the same spelling throughout; `hotspots()` signature matches its CLI.
- Proportion: the scorer's point table is given once (Task 7) and referenced, not repeated.
