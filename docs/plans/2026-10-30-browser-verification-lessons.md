# Browser verification: lessons from a second project

**Status:** Written into `browser-verification.md` on 2026-10-30. Not committed.

**Goal:** Add what a real project's verification skill learned to
`plugins/springboot-architecture/skills/spring-boot-team-harness/references/browser-verification.md`.

**Source:** one `oauth2Login` (BFF) app with a Vite frontend, a TanStack Query cache and a Playwright
journey runner. The file reports trial results today. Word these as observed on one app, not as
trial results.

## Changes

### 1. Doctor: prove the running code is this checkout

Today the doctor checks only that the app answers and the roles are right. A dev server that serves
another checkout, or a backend on another branch's commit, passes those checks and gives wrong
results.

- [ ] Frontend: Vite answers `/@fs/<checkout>/frontend/src/main.tsx` with 200 and a JavaScript
      content type only when it serves that checkout. Fail when it does not. Check the content type,
      not only the status: a missing file inside the allowed root returns 200 `text/html` (the SPA
      fallback), so a wrong path would pass on status alone.
- [ ] Note when the check holds: Vite's `server.fs.strict` (default `true`) returns 403 for paths
      outside `server.fs.allow`, whose default is the workspace root, or the project root when there
      is no workspace. It gives a false pass when the project sets `fs.strict: false`, or an
      `fs.allow` wide enough to cover the other checkout. The doctor reads `vite.config.*` and warns
      on either.
- [ ] Backend: `/actuator/info` `git.commit.id.abbrev` must match `git rev-parse --short HEAD`. Warn
      when it differs, and when `backend/` has uncommitted changes.
- [ ] Note the trap: a backend started from the IDE skips `git-commit-id:revision`, so the info has
      no commit. A shared run configuration (`.run/*.run.xml`) that runs that goal before launch
      fixes it. An Application configuration needs no paid IDE edition.

### 2. Journey first, with a before run

- [ ] Write the new checks before the app code. Run them against the code before the change.
      They must FAIL there.
- [ ] The tool saves that run (`--before`) as a file with the commit and a warning when the
      checkout has uncommitted app changes.
- [ ] The report gets a **Failed first** column that points to the file.
- [ ] Why: a check that passes on the old code proves nothing. Agents skip this step unless the
      report asks for its evidence.
- [ ] Recipe for the old code: `git worktree add <outside-the-repo>/<app>-before <base>`, then run
      the new journeys from the current checkout against the app started from that worktree.
  - Frontend-only change: start a second dev server from the worktree on another port. It reuses
    the running backend and its session, since cookies are per host, not per port.
  - Backend change: the old backend must run on the registered redirect origin, because
    `oauth2Login` builds the redirect URI from `{baseUrl}`, port included. Stop the current backend,
    start the old one on the same port, run `--before`, then start the current one again. Do not run
    two backends side by side unless the identity provider has a second redirect URI registered.
  - The worktree is a second checkout, so §1's doctor must point at it during the before run, and
    back at the main checkout afterwards.

### 3. SKIP is not PASS

- [ ] A check that cannot run because the data is missing raises SKIP, never PASS or FAIL.
- [ ] Say that this overrides the generator. pstack `create-verification-skill` §3 tells the
      journey to report a failure when the seed data lacks a precondition. Keep its rule never to
      weaken a journey, and the `Gotchas` entry, but report SKIP: a FAIL that means "no data"
      teaches agents to ignore failures.
- [ ] A run with skips and no failures exits with its own code (for example 2). The report shows
      each skip as NOT VERIFIED.
- [ ] Why: without it, agents report the gap as a pass, or change the data to make it pass.

### 4. Ask the API directly when comparing the page with data

- [ ] Give journeys an `api(path, body?)` helper that calls the app's API with the session and the
      CSRF token, as the SPA does.
- [ ] CSRF details from the Spring Security reference (7.1 docs, `csrf.spa()`): read the plain
      token from the `XSRF-TOKEN` cookie and send it as `X-XSRF-TOKEN` on unsafe methods. Read the
      cookie on every call, never once per run: Spring clears it on sign-in and sign-out, and loads
      the token lazily, so the cookie can be missing until a GET has run. When it is missing, make
      one GET first.
- [ ] Why: the SPA's query cache can answer a repeated query without a request. So the page's last
      network response can be older than the question being checked.

### 5. Wait for quiet on the app's own origin only

- [ ] Confirmed on the source app: once the persona's embedded third-party widget was signed in,
      two of its loads (a shared worker and a script) never reported as finished. Every check that
      waited for network quiet timed out after 20 s. The same journey went from 13 s to 60-120 s.
- [ ] Guidance: a quiet wait counts only requests to the app's own origin. Prefer waiting for a
      state the check needs (an element, a response, a loaded count) over any quiet wait.
- [ ] Never use Playwright's `waitUntil: 'networkidle'`. Its docs mark it discouraged (no
      connections for 500 ms) and say to rely on web assertions. It counts every origin, so the
      widget above keeps it from ever settling.

### 6. Time budgets

- [ ] The doctor finishes in seconds. On the source app it took 70-100 s per call.
- [ ] Each run has its own timeout and reports which step ran out of time.
- [ ] Guidance: run one journey per command. Do not chain the doctor and every journey for every
      persona into one shell call.
- [ ] Why: one chained call took 598 s against a 600 s tool timeout. One more journey and the agent
      would have lost every result in it.

### 7. One copy of the skill

- [ ] Keep the skill in one directory. Point the other agent's skill directory at it, or generate
      it, instead of keeping two copies.
- [ ] Why: with a copy under `.claude/skills` and one under `.agents/skills`, the agent copied the
      tool by hand and ran `diff -r` to check they matched.

### 8. One summary line and exit codes

- [ ] Each run ends with one machine-readable line: counts of PASS, FAIL and SKIP and the evidence
      path.
- [ ] Exit codes: 0 pass, 1 fail, 2 skips and no failures, 3 sign-in needed.
- [ ] Why: agents piped every run through `grep -E 'PASS|FAIL|SKIP'` to find the result.

### 9. Probes stay out of the journey set

- [ ] One-off probe scripts go in a folder that runs ignore, for example `journeys/scratch/`, or in
      the agent's scratchpad.
- [ ] Why: the agent wrote probes such as `zz-paging-probe.mjs` into `journeys/`. A run of every
      journey would pick them up.

## Where each item lands in the generated skill

pstack `create-verification-skill` writes these sections: Launch, Doctor, Drive, Evidence,
Cleanup, Helpers, and a feature map. Title the reference's sections so each one points at the
section it shapes:

| Generated section | Items |
| --- | --- |
| Doctor | 1, 6 |
| Drive | 4, 5, 9 |
| Evidence | 2, 3 |
| Helpers | 8 |
| Skill location | 7. The generator writes only `.claude/skills/` in Claude Code, so a Codex copy is made by hand. |

Already covered by the generator, so do not repeat it: kill only what you started (the source
session killed six stray dev servers by PID), and evidence survives cleanup.

## Not included

- App-specific tooling: domain test actions, persona names and the per-page feature map.
- Client names, hosts, IDs and third-party product names. This is a public repository. Describe
  what was observed in generic terms only.

## Done when

- [ ] `browser-verification.md` has sections for 1 to 9.
- [ ] No client-specific names, hosts or IDs in the diff: `git diff` grep for the source app's
      name and its vendors comes back empty.
- [ ] Each section says what goes wrong without it, in one or two sentences.
- [ ] `tests/` scenarios still pass, or a scenario is added if one of these needs proof.
