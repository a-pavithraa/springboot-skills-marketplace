# Review guide

Read this before reviewing a change, whether you are a person or an agent. It lists only what the code doesn't show.

## Report a finding only when you can trace it

Start at a supported entry point: a user action, a route the UI calls, a scheduled job, an external event, or data the schema allows. Follow it through the changed lines to a wrong result someone sees. Then look for the strongest reason it cannot happen, such as an earlier guard, a type, a database constraint, server-side validation, or a caller that never sends that value, and drop the finding if one holds.

Zero findings is a valid review.

## Failures: report every break of these

<!-- The rules a reviewer can't infer from the code, one line each, for example:
1. Patient data is audited before it is returned, and a failed audit returns 503 and no data.
2. 404 means "no record"; 503 means "we could not ask". Never show an outage as "nothing found".
3. A setting the app needs at startup has a working default while its feature is off.
4. A call to an external API stays within each of its documented limits: page size, rate, payload size.
Add a line each time a review misses a bug that one would have caught. -->

- A contract change, to a request, response, event or configuration key, with no matching doc update.
- A comment the change makes untrue.
- Code moved only to satisfy a rule: a file split, a method moved to another class, or an exception added so a check passes while its aim is defeated.

## Risk

- High: security configuration, sign-in and access checks, database migrations, `{{BUILD_FILE}}`, CI workflows.<!-- Add the packages where a bug is expensive, starting with those past fixes touched most:
git log -i -E --grep='fix|bug|revert|regression' --format= --name-only | grep 'src/main/' | xargs -n1 dirname | sort | uniq -c | sort -rn | head --> Read the callers and the tests of what changed, and check each rule above that the change touches.
- High: `management.tracing.sampling.probability` raised in shipped config (it can overwhelm the trace store), `server.shutdown=immediate` (it drops requests during deploys), and `include-parameter-values` turned on (it puts personal data in spans).
- High: a log line, exception message or `addKeyValue` that holds personal data or a credential.<!-- observability:begin --> `LogLeakCheck` catches emails and credentials on tested paths; names, phone numbers and untested paths need a reader.<!-- observability:end -->
- High: a `catch` that returns a default or a success response without logging, or a 5xx built by hand in a controller.<!-- failure-filter:begin --> `HandledFailureFilter` only sees exceptions that reach an `@ExceptionHandler`.<!-- failure-filter:end -->
- Medium: a log line inside a loop or on every request at INFO or above, an expected client error logged as ERROR, or the same failure logged again on its way up.<!-- observability:begin --> The Log lines by level panel shows the effect.<!-- observability:end -->
- Medium: a security failure with no log line: failed sign-ins and refused access should leave a WARN.
- Medium: an ID or free text as a metric tag, which creates one series per value. Put it in a span instead. A `@KafkaListener` or `KafkaTemplate` without `observationEnabled`, which ends the trace at the topic.
- Low: docs, changes to tests only, frontend copy and styling. A quick pass is enough.

## Don't report

- Formatting and import order: {{FORMATTER}} checks them.
- What the build already fails on: NullAway, `CodeRulesTests` and the other rule tests.
- Naming and comment style, unless they hide a bug.
- A situation no supported entry point reaches.
- A choice one of the project's decision records documents. Read the record before calling the choice a bug.

## Report

- Give every finding a file and line, the entry point, what happens, and the wrong result.
- At most five findings, one per cause, most serious first.
- Mark findings in code the change didn't touch as pre-existing. The author answers them, and doesn't fix them in this change.
- End with the number of findings, or "No issues found", and name what you could not check.
- On a later round, review only the new changes, and don't repeat a finding that already has an answer.
