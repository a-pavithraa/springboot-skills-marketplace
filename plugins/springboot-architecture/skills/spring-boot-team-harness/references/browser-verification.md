# Browser verification for `oauth2Login` apps

Guidance for a project skill that drives a Spring Boot app in a real browser and proves that a change works. pstack's `create-verification-skill` generates such skills. Give it this file. Browser skills depend on the app's routes, roles and features, so the harness ships none.

Everything below was tested on an `oauth2Login` (BFF) app with a separate frontend dev server.

## Sign-in

- Keep one persistent Chrome profile per test persona, outside the repository, for example `~/.<app>-verify/profiles/<persona>`. The profiles hold live cookies. Never commit them, and add their path to `.gitignore`.
- A human signs each persona in once, in a visible window, and answers "Stay signed in: yes". The agent never types or asks for credentials.
- Spring's `JSESSIONID` has no expiry, so Chrome does not save it in the profile. Every run starts without an app session. The tool opens `/oauth2/authorization/{registrationId}`, and the identity provider signs the profile in silently from its own saved cookie. A backend restart, which drops in-memory sessions, needs nothing from the user.
- When the identity provider shows a password prompt, an account picker, MFA or consent, the tool stops with its own exit code (for example 3). The agent then asks the user to sign in again.
- Always sign in through the origin registered as the redirect URI. You can then drive a dev server on another localhost port with the same session, because cookies are per host, not per port.
- Drive the installed Chrome (Playwright `channel: 'chrome'` with `launchPersistentContext`), so no browser download is needed. Install `playwright-core` outside the repository.

## Doctor

Run one read-only check before any drive:

- Actuator health answers, and the frontend dev server answers.
- For each persona, the auth-status endpoint says signed in, and the current-user endpoint returns the expected role.

The role check matters. A profile signed in with the wrong account still passes the auth check. Only the role check catches it.

## Side effects

- Mark every mapped feature as read-only or writing.
- Never drive a writing action unless the task asks for it, even against sandboxes.
- Name the flows the skill cannot verify, for example a flow that needs a live phone call.

## Proof

- Drive the real user path. Do not stub the app's own API in the browser.
- Take a screenshot before and after the action.
- For data on screen, compare the network response with what the page shows. An empty cell with a filled response is a wiring bug.
- The agent opens and looks at its own screenshots.

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

## Tool design

- Take settings as command flags (`--app <url>`), not environment-variable prefixes (`VAR=x node ...`). A prefixed command does not match common allow rules such as `Bash(node:*)`, and that blocked 2 sessions in the trial.
- On Windows, a visible browser window started from an agent's background shell does not appear. The user starts the sign-in command from their own prompt (`! node <tool> login <persona>`).
- Git Bash rewrites an argument such as `/orders/recent` into a Windows path. Take routes without the leading slash, or document `MSYS_NO_PATHCONV=1`.
- Save evidence outside the repository. Cleanup never deletes it.
