---
name: run-app
description: Starts this service, calls its endpoints and stops it, to check behaviour on the running app. Use after changing what an endpoint returns or accepts, before saying the change is done, or when asked to try an endpoint.
---

# Check the running app

Tests check what they were written to check. Calling the running app shows what a client actually gets. The script is next to this file. Run it with `bash` from the repository root, as below.

1. `bash {{RUN_APP}} start`. It starts the app on port 18080, with the Docker Compose services the app declares, and waits until it's up. Docker must be running. If it doesn't start, it prints the end of the log: fix the cause, and don't skip the check.
2. Call each endpoint you changed, for the case you changed and for one it must still refuse, such as an unknown id or invalid input:
   ```bash
   bash {{RUN_APP}} call GET /api/orders/42
   bash {{RUN_APP}} call POST /api/orders '{"sku":"A-1","quantity":2}'
   ```
   Each call prints the status and up to 4,000 characters of the body.
3. `bash {{RUN_APP}} stop`, also when a check failed. Never leave the app running.
4. Report each call you made, with its status and what it showed.

`bash {{RUN_APP}} logs 100` shows the end of the app's log. `RUN_APP_PORT` changes the port and `RUN_APP_PROFILES` sets Spring profiles.

## Secured endpoints

Never fetch, create or save credentials, and never turn security off to get a call through. The developer can supply one, and the script sends it with each call:

- `RUN_APP_TOKEN`: a bearer token.
- `RUN_APP_COOKIE`: the `Cookie` header from their logged-in browser, for apps that log in through the browser. An `XSRF-TOKEN` in it is also sent as the `X-XSRF-TOKEN` header.

They set it in their shell before starting the session, or under `env` in `.claude/settings.local.json`, which isn't committed. If a call returns 401 or 403 and neither is set, say which endpoints you couldn't check and why.
