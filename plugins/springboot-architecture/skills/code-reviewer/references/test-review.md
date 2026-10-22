# Reviewing Tests

A suite can be green and long and still miss the bugs it claims to guard, or fail on correct code. Reading the tests doesn't show this. The review maps the contract to the tests, checks what each test can actually catch, and proves every finding by running it.

Framework traps that make a test pass without proving anything: `testing/traps.md`. Imports, slices and PIT setup: `testing/boot4-test-toolkit.md`.

## Step 1: Map the contract to the tests

For each class under test, collect its contract:
- the Javadoc, API documentation and agreed message formats
- the project's own statements of what must hold: a system map, invariants, ADRs, `AGENTS.md`/`CLAUDE.md`. These are often the best source. A rule like "only the record's owner may read it" is a clause.

List each clause with the test that guards it, or "none". An unguarded clause is a finding.

In a large project, start with the clauses about who may see or change what, and about delivery (once only, never blocks, recovered after a crash). On those paths, grep the tests for `any(` and `verify(`: an argument nobody checks is where these clauses go unguarded. Then look at units and formats, status codes with a special meaning, and limits.

## Step 2: Check that each test runs the real thing

A test guards only what actually runs in it, and only the parts of a request it actually looks at.

| The test claims to cover | But | So it can't catch |
|--------------------------|-----|-------------------|
| the request sent to a dependency | stubs it with `any(Request.class)` and never captures it | a wrong or missing parameter: a dropped filter, the wrong id, the wrong account. Capture it, or stub the exact request |
| an access rule the controller passes to a service | captures the rule on one route and uses `any()` on the others | a route that passes `owner -> true`, or the wrong rule |
| a cache of access decisions | reads it back with the same caller each time | a key that leaves out who asked, so one user's grant serves another |
| production wiring (a client factory, an `@Enable…` annotation, a timeout) | builds its own client or configuration in the test | the production class losing the setting |
| the request sent to a provider | arranges the value already converted (`3750` instead of `37.50`) | the conversion itself |
| async work (`@Async`) | mocks the async bean, or awaits a result that a synchronous call also produces | the work running on the caller's thread: assert the thread, or that the caller returns while the work is blocked |
| recovery by a scheduled sweep | calls the sweep with fresh rows only | the stale or claimed rows the sweep exists for |
| retries, timeouts, publish after commit, listeners | see `testing/traps.md` | |
| a database query or constraint | H2, or reads back inside the same persistence context | the real SQL |
| full-app behavior | `@MockitoBean` for everything around the subject | anything: it's a slow unit test |

## Step 3: Check that each test can be trusted

Run the suite first. For each red test, decide from the contract whether the test or the code is wrong. Then note tests that are racy (sleeps, single reads of an async result, shared state), prove nothing (status-only, `isNotNull()`, verify-only, expected value computed with the code's own formula), or cost a context or container each for no gain.

## Step 4: Prove every finding

A finding the review hasn't run is a guess.

- **"Can't catch X"**: for a class with plain unit tests, run PIT on it (`testing/boot4-test-toolkit.md`). It is seconds per class, where a hand-run break through Maven and containers can take minutes. Otherwise break X by hand in one line, run only the affected test classes, show they stay green, and restore with `git checkout`.
- **"Fails on correct code"**: show the failure, and quote the clause that says the code is right.
- **"Racy"**: run the class three times, or show the code path that makes it order-dependent.
- **"Clause not guarded"**: cite the clause, and show with `grep` that no test exercises it.

Before running proofs:
- Use the JDK the build requires (`JAVA_HOME`), not whatever is on `PATH`.
- Check Docker is running when the classes use Testcontainers.
- Run one Maven process at a time. Overlapping runs can exhaust memory. A run that dies on memory, a fork error or Docker proves nothing, even if it exits 0. Check that each run printed a test summary.
- Breaks in unrelated code can share one run, if the run includes the test classes for every break. All green proves every break went unnoticed. If the run goes red, split the breaks to find which one a test caught.

Label anything you couldn't run as **unverified**, and say why. Finish with `git status` clean on production code.

## Report

Per test class, then a summary:

```markdown
## <TestClass>
- **[Can't catch | Fails on correct code | Racy | Proves nothing | Costly]**: <what>
  - **Evidence**: <what was broken / run, and the result>
  - **Fix**: <the change to the test>

## Contract clauses with no test
- <Class>: "<clause>"

## Summary
- Bugs this suite would let through, most expensive first
- Tests to delete
```
