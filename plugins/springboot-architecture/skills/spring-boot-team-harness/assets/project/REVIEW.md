# Review guide

Read this before reviewing a change, whether you are a person or an agent. It lists only what the code doesn't show.

## Failures: report every break of these

<!-- The rules a reviewer can't infer from the code, one line each, for example:
1. Patient data is audited before it is returned, and a failed audit returns 503 and no data.
2. 404 means "no record"; 503 means "we could not ask". Never show an outage as "nothing found".
Add a line each time a review misses a bug that one would have caught. -->

## Risk

- High: security configuration, sign-in and access checks, database migrations, `pom.xml`, CI workflows.<!-- Add the packages where a bug is expensive. --> Read the callers and the tests of what changed, and check each rule above that the change touches.
- Low: docs, changes to tests only, frontend copy and styling. A quick pass is enough.

## Don't report

- Formatting and import order: Spotless checks them.
- What the build already fails on: NullAway, `CodeRulesTests` and the other rule tests.
- Naming and comment style, unless they hide a bug.

## Report

Give every finding a file and line. Mark findings in code the change didn't touch as pre-existing. End with the number of findings, or "No issues found".
