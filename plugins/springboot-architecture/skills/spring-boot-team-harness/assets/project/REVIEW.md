# Review guide

Read this before reviewing a change, whether you are a person or an agent. It lists only what the code doesn't show.

## Failures: report every break of these

<!-- The rules a reviewer can't infer from the code, one line each, for example:
1. Patient data is audited before it is returned, and a failed audit returns 503 and no data.
2. 404 means "no record"; 503 means "we could not ask". Never show an outage as "nothing found".
Add a line each time a review misses a bug that one would have caught. -->

## Risk

- High: security configuration, sign-in and access checks, database migrations, `pom.xml`, CI workflows.<!-- Add the packages where a bug is expensive. --> Read the callers and the tests of what changed, and check each rule above that the change touches.
- High: `management.tracing.sampling.probability` raised in shipped config (it can overwhelm the trace store), `server.shutdown=immediate` (it drops requests during deploys), and `include-parameter-values` turned on (it puts personal data in spans).
- High: a log line, exception message or `addKeyValue` that holds personal data or a credential. `LogLeakCheck` catches emails and credentials on tested paths; names, phone numbers and untested paths need a reader.
- High: a `catch` that returns a default or a success response without logging, or a 5xx built by hand in a controller. `HandledFailureFilter` only sees exceptions that reach an `@ExceptionHandler`.
- Medium: a log line inside a loop or on every request at INFO or above, an expected client error logged as ERROR, or the same failure logged again on its way up. The Log events by level panel shows the effect.
- Medium: a security failure with no log line: failed sign-ins and refused access should leave a WARN.
- Medium: an ID or free text as a metric tag, which creates one series per value. Put it in a span instead. A `@KafkaListener` or `KafkaTemplate` without `observationEnabled`, which ends the trace at the topic.
- Low: docs, changes to tests only, frontend copy and styling. A quick pass is enough.

## Don't report

- Formatting and import order: Spotless checks them.
- What the build already fails on: NullAway, `CodeRulesTests` and the other rule tests.
- Naming and comment style, unless they hide a bug.

## Report

Give every finding a file and line. Mark findings in code the change didn't touch as pre-existing. End with the number of findings, or "No issues found".
