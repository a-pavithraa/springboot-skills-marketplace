# Browser verification for `oauth2Login` apps

Guidance for a project skill that drives a Spring Boot app in a real browser and proves that a change works. pstack's `create-verification-skill` generates such skills. Give it this file. Browser skills depend on the app's routes, roles and features, so the harness ships none.

The guidance comes from two `oauth2Login` (BFF) apps with a separate frontend dev server. The sign-in, doctor and proof basics were tested on the first, with the trial below. Everything else was observed on the second, over about 110 journey runs. Rules marked *proposed* answer a failure seen there but have not been tried yet.

Each section names the part of the generated skill it shapes: Launch, Doctor, Drive, Evidence, Cleanup or Helpers.

## Sign-in (Launch)

- Keep one persistent Chrome profile per test persona, outside the repository, for example `~/.<app>-verify/profiles/<persona>`. The profiles hold live cookies. Never commit them, and add their path to `.gitignore`.
- A human signs each persona in once, in a visible window, and answers "Stay signed in: yes". The agent never types or asks for credentials.
- Spring's `JSESSIONID` has no expiry, and in our runs Chrome did not save it in the profile, so a run started without an app session. Session restore or a customized session cookie can keep it, so check the session rather than assume it's gone. The tool opens `/oauth2/authorization/{registrationId}`, and the identity provider signs the profile in silently from its own saved cookie. A backend restart, which drops in-memory sessions, needs nothing from the user.
- When the identity provider shows a password prompt, an account picker, MFA or consent, the tool stops with exit code 3. The agent then asks the user to sign in again.
- Always sign in through the origin registered as the redirect URI. You can then drive a dev server on another localhost port with the same session, because cookies are per host, not per port.
- Drive the installed Chrome (Playwright `channel: 'chrome'` with `launchPersistentContext`), so no browser download is needed. Install `@playwright/test` outside the repository, not `playwright-core`: its `expect` retries, and it works in a plain script, so journeys need no test runner.

## Doctor

Run one read-only check before any drive. It finishes in seconds; on the second app it took 70 to 100 s, which agents then paid before every run. Move first-time work, such as installing tools and checking the browser, into a separate `setup` command; that took the doctor to 12 s.

- Actuator health answers, and the frontend dev server answers.
- For each persona, the auth-status endpoint says signed in, and the current-user endpoint returns the expected role. A profile signed in with the wrong account still passes the auth check. Only the role check catches it.
- The running code looks like this checkout. These checks are preliminary: they catch a wrong checkout or branch, not every case. A dev server serving another checkout, or a backend built from another branch, passes every check above and gives wrong results. Agents that work in several worktrees hit this.

### Same checkout: frontend

Request `/@fs/<absolute checkout path>/frontend/src/main.tsx` from the dev server. Pass only on 200 with a JavaScript content type. This shows the server can read that file, not that the app it serves was started from it.

- Vite's `server.fs.strict` (on by default) answers 403 for files outside `server.fs.allow`. By default that is the workspace root, or the project root when there is no workspace, so a dev server started from another checkout refuses the path.
- Check the content type, not only the status. A missing file inside the allowed root returns 200 `text/html`, the SPA fallback, so a wrong path passes on status alone.
- The check proves nothing when `vite.config.*` sets `fs.strict: false`, or an `fs.allow` wide enough to cover the other checkout. The doctor reads the config and warns on either.

### Same checkout: backend

Compare the commit in `/actuator/info` (`git.commit.id`) with `git rev-parse HEAD`. The info id may be the short one, so pass when HEAD starts with it. When they differ (*proposed*), run `git diff --name-only <running>..HEAD -- backend/` and fail the run if it lists files or git does not know the commit. An empty list passes: a frontend commit moves HEAD without changing the backend. When the info has no commit, report the backend as unverified. Warn when the backend folder has uncommitted changes, because two worktrees on the same commit also match, and a commit doesn't say what was compiled.

*Proposed:* repeat this check at the start of every journey run and put both commits on the summary line. The doctor is a separate command, and on the second app its stale-backend warning appeared 5 times.

- The commit is there only when `git.properties` is on the classpath. Add `io.github.git-commit-id:git-commit-id-maven-plugin`; `spring-boot-starter-parent` already configures it, so the declaration needs no version or goals.
- Boot exposes only `health` over HTTP. Add `info` with `management.endpoints.web.exposure.include=health,info` in the local profile only. Call it with the persona's session if security does not permit it.
- A backend started from the IDE skips the plugin's `revision` goal, so the info has no commit. A shared run configuration in `.run/*.run.xml` that runs that goal before launch fixes it for the team. An Application configuration needs no paid IDE edition.

## Side effects (Drive)

- Mark every mapped feature as read-only or writing.
- Never drive a writing action unless the task asks for it, even against sandboxes.
- Name the flows the skill cannot verify, for example a flow that needs a live phone call.
- Give an action that costs money its own command, with a `--dry-run` that checks everything else. A journey declares that it needs the action, and the normal run command refuses that journey.

## Proof (Drive, Evidence)

- Drive the real user path. Do not stub the app's own API in the browser.
- For data on screen, compare what the page shows with the data. An empty cell with a filled response is a wiring bug.
- Fail the run on an error the page did not catch, even when every check passed. Print console errors and 5xx answers, and filter known noise by its exact text, so agents keep reading those lines.
- A check on a shared control loops over every instance on the screen, not one example. One button check passed while another button of the same kind was still wrong.
- Make each cross-field rule a scripted check, for example "no recording means no duration". A rule in the skill's review list was not enough to catch a false recording duration.

### What journeys miss

A journey proves only what its checks name, and its author writes them. On the second app, journeys caught fixes that did nothing, and a person still found most visible bugs: a duration on a call with no recording, a lost border, a missing row highlight, fewer visible rows. Most were things that disappeared, which generic layout checks such as sideways scrolling, cut-off text or contrast would not have caught. So pair journeys with the comparison and screenshot review below, and turn each bug they find into a failing check.

Move bad-input cases to unit tests, and keep one real browser path per filter. Unit tests do not replace journeys, which prove what only a browser can: wiring, sessions, live integrations and layout.

### Compare before and after

*Proposed.* Things that disappear pass every check that names only what should be there, so compare the two runs:

- Capture the same screens under the same labels in the `--before` run and the final run, and pair the shots by label.
- Crop to the changed area, which keeps live data out of the comparison.
- Record the row count of each list in both runs.
- Flag each image or count difference for review. A difference is a question, not a failure: the change may have meant it.

Visual quality, such as a poor calendar, stays a human judgment. The report never claims that this comparison covers it.

### Review screenshots

- Wait inside the shot helper until loading indicators clear, and turn animations off. Two early review shots showed a screen still loading.
- Crop to what changed. A viewport shot cost about 1,700 tokens and a cropped drawer about 670.
- Save the facts the screen should show in a file beside the image, picked by hand. Leave out fields the review does not need.
- List every place the change shows, then open one final shot per distinct kind and state, plus the shot of each failed check.
- Report one row per shot: the state it should show, the values compared, and each flaw marked bug or opinion.
- The agent can skip the review when the diff changes nothing a screen shows or lists, every check passed, and no check was skipped. It names the files it checked.

The first review found five issues while every check passed. On later shots it found fewer, and its catch rate is unmeasured.

### Measure what gets caught

*Proposed.* Use real bugs, not invented ones. In a worktree, undo real past fixes one at a time, run the journeys and the review, and count the catches. Do this once as a baseline and again after a change to the tool or skill, with the same set of fixes. Keep a ledger of which bug each journey caught, so a journey that never catches anything can be questioned.

### Ask the API directly

Give journeys an `api(path, body?)` helper that calls the app's API with the browser's session and CSRF token, as the SPA does. Compare the page with its answer, not with the page's last network response: the SPA's query cache can answer a repeated query without a request, so that response can be older than the question being checked.

With Spring Security's cookie CSRF setup (`csrf.spa()`), read the token from the `XSRF-TOKEN` cookie and send it as `X-XSRF-TOKEN` on unsafe methods. Read the cookie on every call, never once per run: Spring clears it on sign-in and sign-out and creates it only when a request needs it. When it is missing, make one GET first.

### Wait for state, not for quiet

Write each wait as a retrying `await expect(locator)...`, so the check ends on a state the page shows. Never use Playwright's `waitUntil: 'networkidle'`; its docs mark it discouraged. When a wait for quiet cannot be avoided, count only requests to the app's own origin.

On the second app, an embedded third-party widget opened two loads that never finished once its persona was signed in. Every wait for quiet timed out after 20 s, and one journey went from 13 s to 60 to 120 s. Hand-written waits also caused most of the journey bugs in one feature, which took about a third of its time.

### Keep journeys cheap

- Keep one journey per area, and add checks to it. One journey per PR does not scale.
- Put common steps in one shared file, each ending on a visible state: open a page, apply a filter, open a row, close a drawer, switch theme.
- Run a journey when it should fail first, and once at the end. Use unit tests while building.
- When a check fails twice because of the journey, rewrite it as one `expect`, or report the flow NOT VERIFIED.
- Find the record a check needs by asking the API with a filter. A check that looks only at the first page skips whenever dev data shifts.

### Fail first

- Write the new checks before the app code, and run them against the code before the change. They must FAIL there. A check that passes on the old code proves nothing.
- The tool saves that run (`--before`) as a file with the commit, and warns when the checkout has uncommitted app changes. The report has a **Failed first** column that points to the file. Agents skip this step unless the report asks for its evidence.
- *Proposed:* record the code the app serves, not the checkout the tool lives in, by reusing the tool's served-code check. The uncommitted-changes check looks at that same code. With `--app` on a base worktree, the file can otherwise name the wrong commit.
- *Proposed:* warn when a before run has no failures, and save each failure's reason. One check failed only because of its own ordering, which proves nothing about the app.
- *Proposed:* list the new checks by comparing check labels with the base branch, because the tool cannot tell which checks are new.
- *Proposed:* a before run never stops early, because its new checks are expected to time out.
- To run the old code, add a worktree of the base commit outside the repository (`git worktree add ../<app>-before <base>`), and run the new journeys from the current checkout against the app started from it. Point the doctor's checkout check at the worktree for that run.
  - Frontend-only change: start a second dev server from the worktree on another port. It reuses the running backend and its session.
  - Backend change: `oauth2Login` builds its redirect URI from the base URL, port included, so the old backend must run on the registered port. Stop the current backend, start the old one, run `--before`, then start the current one again. Two backends side by side need a second redirect URI registered with the identity provider.

### SKIP is not PASS

A check that cannot run because data is missing reports SKIP, never PASS or FAIL. This overrides pstack, which reports a failure for a missing seed precondition. Keep its other rules: never weaken the journey, and note the missing data in the feature's `Gotchas`.

A run with skips and no failures exits with code 2, and the report lists each skip as NOT VERIFIED. Without this, agents report the gap as a pass, or change the data until it passes. A FAIL that only means "no data" teaches them to ignore failures.

A check whose subject is missing calls `skip()` too. An early `return`, or an `if (visible)` around the assertions, reports PASS with nothing tested. *Proposed:* the tool counts `expect` and `ensure` calls per check and fails any check that makes none at runtime. A lint would miss an `if` with no `else`.

The report's other states: NOT APPLICABLE for a change no screen can show, with one line saying why, and NOT VERIFIED when verification is turned off.

## Getting agents to use it

A trial planted a wiring bug that every unit test missed, and ran 3 Sonnet sessions per setup:

| Setup | Caught the bug |
| --- | --- |
| Skill and an `AGENTS.md` line, task did not ask for proof | 0/3 (the skill was never used) |
| No skill, task asked for screenshot proof | 0/3 (no way to see the page) |
| Skill, task asked for screenshot proof | 3/3 |

- An `AGENTS.md` line alone does not make agents verify. Two sessions called the check "still outstanding" in their final report, then stopped.
- Asking for proof in the task works. It also made every session honest about what it could not check.
- Leave browser verification out of Stop hooks. Docs and config changes may validly skip it, so a hook that blocks when no run matches the diff would block correct work.

## Tool design (Helpers)

- Keep the mechanics generic: run accounting, exit codes, quiet output, before/after proof and code identity. Put project details behind configuration: personas, sign-in, routes, journeys, any live or paid flow, and how to detect the served code.
- Take settings as command flags (`--app <url>`), not environment-variable prefixes (`VAR=x node ...`). A prefixed command does not match common allow rules such as `Bash(node:*)`, and that blocked 2 sessions in the trial.
- End every run with one machine-readable line: the PASS, FAIL and SKIP counts and the evidence path. Exit 0 on pass, 1 on any failure, 2 on skips without failures, 3 when a person must act, 4 when verification is turned off.
- *Proposed:* print only failures and the summary line by default, keep screenshot paths available for the review, and tell agents not to pipe the tool. Agents piped 90 of 91 runs through `grep` or `cut` even with a summary line, and a pipe hides the exit code.
- Run one journey per command, and give each run a timeout that names the step that ran out. An agent that chained the doctor and every journey for every persona into one shell call used 598 s of a 600 s tool limit; one more journey and it would have lost every result.
- *Proposed:* after two timeouts in a row, probe a cheap authenticated endpoint, and stop the run only if that fails. Error text cannot separate setup timeouts from real failures: a failed retrying assertion also reports a timeout, so counting timeouts stopped one run with 16 checks unrun and blamed the setup for a real failure.
- Save a trace only for a failed run, and print its path.
- *Proposed:* set the action timeout to 15 s to match `expect`, and go lower only with data. Playwright actions wait 30 s by default, so one missing element cost twice the assertion limit.
- Keep one-off probe scripts out of the journey folder, in a subfolder runs ignore (for example `journeys/scratch/`) or in the agent's scratchpad. Probes left in `journeys/` run with the real journeys.
- When both Claude Code and Codex use the skill, keep its scripts and journeys in one folder that both `SKILL.md` files call. pstack writes only the Claude Code copy, and a second full copy drifts: the agent on the second app copied the tool across by hand and ran `diff -r` to check.
- On Windows, a visible browser window started from an agent's background shell does not appear. The user starts the sign-in command from their own prompt (`! node <tool> login <persona>`).
- Git Bash rewrites an argument such as `/orders/recent` into a Windows path. Take routes without the leading slash, or document `MSYS_NO_PATHCONV=1`.

## Cleanup

Save evidence outside the repository. Cleanup never deletes it.

Screenshots, facts files and traces can hold personal data, and Playwright traces record the DOM and network traffic. On an app with personal data, trim console lines and keep the files out of tickets and PRs.

*Proposed:* a `prune` command the user runs, separate from cleanup, with a retention limit that covers the whole evidence folder, screenshots included. Traces alone are not enough, because they are kept only for failed runs. With test data this is routine cleanup, so it comes after the fixes above.

## Build order

1. Trust fixes and quiet output: failure accounting, before-run identity, weak proof, empty passes, and the served-code check on every run.
2. Baseline measurement.
3. Before/after comparison, row counts and check-every-instance.
4. Second measurement, with the same fixes.
5. Remaining cost work and retention.
