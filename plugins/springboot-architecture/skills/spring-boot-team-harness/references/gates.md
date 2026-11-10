# Hooks and gates in detail

`SKILL.md` summarises each piece in one line. Read the section here when a team asks how a piece behaves, or when one blocks something it shouldn't.

## `.claude/hooks/verify-on-stop.sh`

SessionStart and Stop hook, for Claude Code and Codex. It records the code each session starts from. When a turn ends and the session has changed the code under `src` or `pom.xml`, committed or not, it formats the code and runs the gates that need no Docker (compile with NullAway, `CodeRulesTests`, `ConfigurationKeysTests`, `BuildSetupTests`, the module and ArchUnit tests). It blocks the turn only on errors in files the session changed, so the agent fixes its own mistakes and never code it didn't touch; when the build fails only elsewhere, it tells the user the change couldn't be fully verified. A formatting failure blocks too. It skips code that already passed, and gives up after one failed retry on the same code. In a session with no recorded starting point, such as one that began before the hooks were installed, it tells the user the turn wasn't checked instead of passing it silently. A session that changes no code costs nothing; a check takes 25 to 75 s.

## `.claude/hooks/guard.sh`

PreToolUse hook, for Claude Code and Codex (which edits files with `apply_patch`; the hook reads each file the patch updates, deletes or moves to). Refuses `git push --force`, `git reset --hard`, `git clean -f`, edits to a Flyway migration that is already on the main branch, edits to the ArchUnit freeze record or `modulith_store`, any edit or shell write to a module's `package-info.java`, since telling a widening edit from a harmless one would take parsing Java (creating one for a new module passes), and edits to the rule tests (`CodeRulesTests`, `ConfigurationKeysTests`, `BuildSetupTests`, `ModuleBoundariesTests`, `LogLeakCheck`, and progen's `ArchUnitTests` and `ModularityTests`). A developer changes a rule by hand. It also refuses Bash commands that write to those files and the Maven flags that record violations as accepted (`allowStoreCreation=true`, `freeze.refreeze=true`, `modulith.store.record=true`), and gate runs that skip checks: `verify` or `install` with `-DskipTests`, `-Dmaven.test.skip`, `-Djacoco.skip` or `-Denforcer.skip`, and Gradle `build` or `check` with `-x test`. Packaging without tests, as `./mvnw package -DskipTests`, passes. It is advisory, not a boundary: a command it doesn't recognise gets through, so `harness-integrity.yml` backs it up in CI.

## `scripts/report.py`

Both hooks append one line per run to `.git/harness/events.jsonl`, capped at 2000 lines. A line holds no paths, commands or file contents. `report.py` summarises that file.

## `ModuleBoundariesTests`

Spring Modulith's checks: no use of another module's internal types, no cycles, no dependency that a module's `allowedDependencies` leave out. It also fails on what `verify()` lets through: a published class whose public constructor takes an internal type, and an `allowedDependencies` entry no code uses (the guard hook stops an agent widening the list, but an unused entry is already open to it).

An `@ApplicationModuleTest` checks the module's boundaries again when it starts, without the record, so on an existing codebase set `verifyAutomatically = false` on module tests and leave the boundaries to this test.

Violations listed in `src/test/resources/modulith_store` are tolerated. Each is keyed by what it is, not by line: a cycle by its modules, so another call along a recorded cycle passes while a new cycle fails; a disallowed dependency by its two modules; an internal-type access by caller and callee. A fixed violation drops out of this violation record when the test runs. Only `baseline.py` adds to it.

IntelliJ IDEA Ultimate's Spring Modulith plugin flags internal-type access and disallowed dependencies in the editor, but not cycles and not the violation record, so recorded violations still show red there. Declaring `allowedDependencies` on each module gives developers the editor warning before the build fails.

## `CodeRulesTests`

ArchUnit rules for mistakes that compile and pass most tests:

- a class calling its own `@Transactional`, `@Async`, `@Cacheable` or `@Retryable` method (the proxy is skipped)
- controllers that start transactions, use repositories (Spring Data, `@Repository` classes, or an interface one of them implements), or take or return JPA entities
- `@Retryable` or `@ConcurrencyLimit` with nothing switching them on
- `@ManyToMany` fields that aren't a `Set` (with a `List`, removing one element rewrites every join row)
- `@ManyToOne` and `@OneToOne` without `fetch = LAZY`
- enum columns stored by position
- a `@Transactional` method calling an HTTP client, an HTTP interface or an AWS SDK client, directly or through the project's own classes (it holds a database connection for the whole call)
- `RestClient.create()`, `WebClient.create()`, `new RestTemplate()`, or the static `builder()` in a class that sets no request factory (no timeouts)
- proxy annotations on private, final or static methods
- `@Async` or `@Scheduled` with nothing switching them on
- services that throw `ResponseStatusException`, use the servlet API or return `ResponseEntity`
- `@Deprecated` code outside controllers (update the callers and delete it)
- `@Autowired` fields, `System.out`, Jackson 2 (Boot 4 ignores it), Spring's deprecated nullness annotations
- JUnit 4 tests (never run) and `@Disabled` tests

Each failure message says how to fix it. It uses the project's ArchUnit or Taikai, and adds ArchUnit only when neither is declared. It and `UnusedCodeTests` leave out classes generated into `target/generated-sources` or `build/generated`, such as OpenAPI models and MapStruct mappers.

## `.github/workflows/harness-integrity.yml`, `.github/harness/check-protected.sh`

Fails a pull request that:

- adds entries to the ArchUnit freeze record or `modulith_store`
- widens a module's rules in `package-info.java` (adds to or removes `allowedDependencies`, lists an entry that isn't a quoted module name, such as a constant, or changes the module's type; dropping entries passes)
- changes `archunit.properties`, or changes or deletes an existing rule test
- changes or deletes a migration on the base branch
- changes the hooks or this check, unregisters a harness hook or narrows its matcher in `.claude/settings.json` or `.codex/hooks.json`
- changes the harness's plugin block in the pom (NullAway, Spotless) or `gradle/harness.gradle`, or stops a Gradle build file applying that script
- removes a line from `.mvn/jvm.config`
- changes or deletes the verify workflow the harness added
- stops `LogLeakCheck` running by unregistering it or turning off extension autodetection

whichever tool made the change. Removing fixed violations from the record and adding new migrations or rule tests pass, and so do other edits to those two JUnit files, which aren't checked at all in a project without `LogLeakCheck`. It runs the base branch's copy of the script, so a pull request can't weaken it. A maintainer accepts an intended change, such as a harness update, with the `harness-rule-change` label; the files are still listed for the reviewer. Make it a required status check and put `.github/` and the rule tests under CODEOWNERS. Added for every project, also when CI already runs Maven.
