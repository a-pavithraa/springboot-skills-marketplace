# Browser verification for `oauth2Login` apps

Guidance for a project skill that drives a Spring Boot app in a real browser and proves that a change works. pstack's `create-verification-skill` generates such skills. Give it this file. Browser skills depend on the app's routes, roles and features, so the harness ships none.

The guidance comes from two `oauth2Login` (BFF) apps with a separate frontend dev server. The sign-in, doctor and proof basics were tested on the first, with the trial below. The checkout check, the before run, SKIP, the API helper, waits, time limits and the tool output were observed on the second.

Each section names the part of the generated skill it shapes: Launch, Doctor, Drive, Evidence, Cleanup or Helpers.

## Sign-in (Launch)

- Keep one persistent Chrome profile per test persona, outside the repository, for example `~/.<app>-verify/profiles/<persona>`. The profiles hold live cookies. Never commit them, and add their path to `.gitignore`.
- A human signs each persona in once, in a visible window, and answers "Stay signed in: yes". The agent never types or asks for credentials.
- Spring's `JSESSIONID` has no expiry, and in our runs Chrome did not save it in the profile, so a run started without an app session. Session restore or a customized session cookie can keep it, so check the session rather than assume it's gone. The tool opens `/oauth2/authorization/{registrationId}`, and the identity provider signs the profile in silently from its own saved cookie. A backend restart, which drops in-memory sessions, needs nothing from the user.
- When the identity provider shows a password prompt, an account picker, MFA or consent, the tool stops with exit code 3. The agent then asks the user to sign in again.
- Always sign in through the origin registered as the redirect URI. You can then drive a dev server on another localhost port with the same session, because cookies are per host, not per port.
- Drive the installed Chrome (Playwright `channel: 'chrome'` with `launchPersistentContext`), so no browser download is needed. Install `playwright-core` outside the repository.

## Doctor

Run one read-only check before any drive. It finishes in seconds; on the second app it took 70 to 100 s, which agents then paid before every run.

- Actuator health answers, and the frontend dev server answers.
- For each persona, the auth-status endpoint says signed in, and the current-user endpoint returns the expected role. A profile signed in with the wrong account still passes the auth check. Only the role check catches it.
- The running code looks like this checkout. These checks are preliminary: they catch a wrong checkout or branch, not every case. A dev server serving another checkout, or a backend built from another branch, passes every check above and gives wrong results. Agents that work in several worktrees hit this.

### Same checkout: frontend

Request `/@fs/<absolute checkout path>/frontend/src/main.tsx` from the dev server. Pass only on 200 with a JavaScript content type. This shows the server can read that file, not that the app it serves was started from it.

- Vite's `server.fs.strict` (on by default) answers 403 for files outside `server.fs.allow`. By default that is the workspace root, or the project root when there is no workspace, so a dev server started from another checkout refuses the path.
- Check the content type, not only the status. A missing file inside the allowed root returns 200 `text/html`, the SPA fallback, so a wrong path passes on status alone.
- The check proves nothing when `vite.config.*` sets `fs.strict: false`, or an `fs.allow` wide enough to cover the other checkout. The doctor reads the config and warns on either.

### Same checkout: backend

Compare the commit in `/actuator/info` (`git.commit.id`) with `git rev-parse HEAD`. The info id may be the short one, so pass when HEAD starts with it. Fail the run when they differ: a journey against another commit proves nothing. When the info has no commit, report the backend as unverified. Warn when the backend folder has uncommitted changes, because two worktrees on the same commit also match, and a commit doesn't say what was compiled.

- The commit is there only when `git.properties` is on the classpath. Add `io.github.git-commit-id:git-commit-id-maven-plugin`; `spring-boot-starter-parent` already configures it, so the declaration needs no version or goals.
- Boot exposes only `health` over HTTP. Add `info` with `management.endpoints.web.exposure.include=health,info` in the local profile only. Call it with the persona's session if security does not permit it.
- A backend started from the IDE skips the plugin's `revision` goal, so the info has no commit. A shared run configuration in `.run/*.run.xml` that runs that goal before launch fixes it for the team. An Application configuration needs no paid IDE edition.

## Side effects (Drive)

- Mark every mapped feature as read-only or writing.
- Never drive a writing action unless the task asks for it, even against sandboxes.
- Name the flows the skill cannot verify, for example a flow that needs a live phone call.

## Proof (Drive, Evidence)

- Drive the real user path. Do not stub the app's own API in the browser.
- Take a screenshot before and after the action.
- For data on screen, compare what the page shows with the data. An empty cell with a filled response is a wiring bug.
- The agent opens and looks at its own screenshots.

### Ask the API directly

Give journeys an `api(path, body?)` helper that calls the app's API with the browser's session and CSRF token, as the SPA does. Compare the page with its answer, not with the page's last network response: the SPA's query cache can answer a repeated query without a request, so that response can be older than the question being checked.

With Spring Security's cookie CSRF setup (`csrf.spa()`), read the token from the `XSRF-TOKEN` cookie and send it as `X-XSRF-TOKEN` on unsafe methods. Read the cookie on every call, never once per run: Spring clears it on sign-in and sign-out and creates it only when a request needs it. When it is missing, make one GET first.

### Wait for state, not for quiet

Wait for what the check needs: an element, a response, a row count. Never use Playwright's `waitUntil: 'networkidle'`; its docs mark it discouraged. When a wait for quiet cannot be avoided, count only requests to the app's own origin.

On the second app, an embedded third-party widget opened two loads that never finished once its persona was signed in. Every wait for quiet timed out after 20 s, and one journey went from 13 s to 60 to 120 s.

### Fail first

- Write the new checks before the app code, and run them against the code before the change. They must FAIL there. A check that passes on the old code proves nothing.
- The tool saves that run (`--before`) as a file with the commit, and warns when the checkout has uncommitted app changes. The report has a **Failed first** column that points to the file. Agents skip this step unless the report asks for its evidence.
- To run the old code, add a worktree of the base commit outside the repository (`git worktree add ../<app>-before <base>`), and run the new journeys from the current checkout against the app started from it. Point the doctor's checkout check at the worktree for that run.
  - Frontend-only change: start a second dev server from the worktree on another port. It reuses the running backend and its session.
  - Backend change: `oauth2Login` builds its redirect URI from the base URL, port included, so the old backend must run on the registered port. Stop the current backend, start the old one, run `--before`, then start the current one again. Two backends side by side need a second redirect URI registered with the identity provider.

### SKIP is not PASS

A check that cannot run because data is missing reports SKIP, never PASS or FAIL. This overrides pstack, which reports a failure for a missing seed precondition. Keep its other rules: never weaken the journey, and note the missing data in the feature's `Gotchas`.

A run with skips and no failures exits with code 2, and the report lists each skip as NOT VERIFIED. Without this, agents report the gap as a pass, or change the data until it passes. A FAIL that only means "no data" teaches them to ignore failures.

## Getting agents to use it

A trial planted a wiring bug that every unit test missed, and ran 3 Sonnet sessions per setup:

| Setup | Caught the bug |
| --- | --- |
| Skill and an `AGENTS.md` line, task did not ask for proof | 0/3 (the skill was never used) |
| No skill, task asked for screenshot proof | 0/3 (no way to see the page) |
| Skill, task asked for screenshot proof | 3/3 |

- An `AGENTS.md` line alone does not make agents verify. Two sessions called the check "still outstanding" in their final report, then stopped.
- Asking for proof in the task works. It also made every session honest about what it could not check.
- An open idea, untested: a Stop hook that blocks the end of a turn when frontend files changed and no screenshot was saved in the session.

## Tool design (Helpers)

- Take settings as command flags (`--app <url>`), not environment-variable prefixes (`VAR=x node ...`). A prefixed command does not match common allow rules such as `Bash(node:*)`, and that blocked 2 sessions in the trial.
- End every run with one machine-readable line: the PASS, FAIL and SKIP counts and the evidence path. Exit 0 on pass, 1 on any failure, 2 on skips without failures, 3 when sign-in is needed. Otherwise agents grep the log for the result.
- Run one journey per command, and give each run a timeout that names the step that ran out. An agent that chained the doctor and every journey for every persona into one shell call used 598 s of a 600 s tool limit; one more journey and it would have lost every result.
- Keep one-off probe scripts out of the journey folder, in a subfolder runs ignore (for example `journeys/scratch/`) or in the agent's scratchpad. Probes left in `journeys/` run with the real journeys.
- When both Claude Code and Codex use the skill, keep its scripts and journeys in one folder that both `SKILL.md` files call. pstack writes only the Claude Code copy, and a second full copy drifts: the agent on the second app copied the tool across by hand and ran `diff -r` to check.
- On Windows, a visible browser window started from an agent's background shell does not appear. The user starts the sign-in command from their own prompt (`! node <tool> login <persona>`).
- Git Bash rewrites an argument such as `/orders/recent` into a Windows path. Take routes without the leading slash, or document `MSYS_NO_PATHCONV=1`.

## Cleanup

Save evidence outside the repository. Cleanup never deletes it.
