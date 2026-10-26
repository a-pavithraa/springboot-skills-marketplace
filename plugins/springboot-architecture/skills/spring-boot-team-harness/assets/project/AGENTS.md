# {{PROJECT_NAME}}

Spring Boot {{BOOT_VERSION}} on Java {{JAVA_VERSION}}. Base package: `{{BASE_PACKAGE}}`.

## Done means verify passes

Run `./mvnw verify` (`mvnw.cmd verify` on Windows) before you say a change is finished, and report its result. Don't claim it passed without running it. These gates fail the build:

| Gate | Fails when | Fix |
| --- | --- | --- |
| NullAway, at compile | {{NULLAWAY_CHECKED}} can pass or return `null` where the type doesn't allow it | Annotate with `org.jspecify.annotations.Nullable` and handle the null. Don't add `@SuppressWarnings("NullAway")`, and don't add `@NullUnmarked`: classes that have it are legacy code waiting to be fixed |
<!-- modules:begin -->
| `{{BOUNDARY_TEST}}` | A module uses another module's nested (internal) package, or modules depend on each other in a cycle | Call the other module through a type in its top-level package, or publish an event |
<!-- modules:end -->
| `ConfigurationKeysTests` | A `spring.`, `management.`, `server.` or `logging.` key in `application*.properties` or `.yml` is unknown or deprecated | Use the key the message names, or the dependency that defines it |
| `CodeRulesTests` | A class calls its own `@Transactional`, `@Async`, `@Cacheable` or `@Retryable` method; a controller starts a transaction, uses a repository, or takes or returns a JPA entity; `@Retryable` or `@ConcurrencyLimit` is used without `@EnableResilientMethods`; a `@ManyToMany` field isn't a `Set`; a field is `@Autowired`; code prints to `System.out`; code uses Jackson 2, Spring's nullness annotations or JUnit 4; a test is `@Disabled` | Each failure message says what to do instead. Violations recorded in `src/test/resources/archunit_store` are older than the harness and tolerated; never edit that record to get a new one through, and don't change `archunit.properties`. If the rules fail on many classes nobody changed and there is no record, the existing code was never baselined: ask the user to run the harness's `baseline.py` |
| `BuildSetupTests` | A Boot starter is in `test` scope; `spring-boot-autoconfigure-classic` is a dependency; Flyway migrations exist without `spring-boot-starter-flyway`; `ddl-auto` creates or updates the schema, or code writes `flyway_schema_history` | Each failure message says what to do instead. Don't work around a missing feature by adding it to the test classpath only |
| `UnusedCodeTests` (in `verify` only, not the end-of-turn check) | A non-private method is called only from tests | If the change is meant to call it, wire that up. Otherwise test through the public behaviour and delete the method; don't open up internals for a test |
| Spotless | Code isn't formatted | Run `./mvnw spotless:apply` |

The rule tests above hold the team's rules, and the harness blocks edits to them. When a rule seems wrong, say so and ask the user.

`verify` also runs the tests that start containers, so Docker must be running. If it isn't, say that those tests didn't run. Don't skip or disable them.

In Claude Code, a hook runs the gates that need no Docker whenever a turn ends with changed code, and sends any failure back to you. In other tools, run `./mvnw verify` yourself.

## How to work here

- If you can describe the change in one sentence, make it. Otherwise read the code it touches and agree a plan with the user first, with the `grilling` or `html-plan` skill if installed.
- For a bug, first write a test that fails because of it, then fix the code.
- Before you write a method or component, search the repository's own code, backend and frontend, for code that already does it. Reuse it, or move the shared logic into one place in this change. Don't leave a note to extract it later: the next session won't see it.
- Write tests with the `writing-springboot-tests` skill if installed, also when working test-first with `tdd`: it has the Boot 4 wiring and the WireMock and Testcontainers templates.
- Write a comment only when deleting it would let the next reader make a mistake: a constraint the code can't show (an external system's behaviour, a limit, an ordering), or why the obvious alternative is wrong. Default to none, even where the code around you has more.
  - Not on getters, constructors, private methods, or anything whose name says what it is. A record or DTO field gets one only for what its name can't say: when it is null or empty, or a meaning that depends on state. No `@param` or `@return` that repeats the name.
  - Say each rule once, where it is enforced. A design decision longer than two sentences goes in the project's docs, with a one-line pointer in the code.
  - Never describe what the code does, what changed ("now", "instead of", "fixed"), or a ticket or plan. Write one or two sentences as one connected thought, and update or delete comments your change makes untrue.
- When you change what an endpoint returns or accepts, add or update a full-API test for it (the whole app with Testcontainers; `writing-springboot-tests`), one request for the case you built and one it must refuse.
- On a feature branch, when a change is finished and not committed, ask the user whether to commit it. Commit each logical step on its own, in the order a reviewer should read them, with a message that says what the step does and why. Each commit must compile and pass the gates the Stop hook runs. Run the full `./mvnw verify` before you open the pull request. Never commit on `main` or `master`, and don't push unless asked.
- Before you open a pull request, review the branch's changes with the `code-reviewer` skill and write the description with the `pr` skill, if they are installed. In the review, search the repository's own code for code like what the branch adds, so a copy of existing logic shows up. Fix what the review finds, then review only the new changes; after two rounds, ask the user instead of starting a third. The description says how the change was tested, what could break, and how to revert it.

## Skills

When a request matches one of these, read the code it touches, then load its skill and follow it (the Skill tool in Claude Code, `$name` in Codex):

- A new project or service: `creating-springboot-projects`
- Upgrading Spring Boot or Java: `springboot-migration`
- Reviewing code, a slow endpoint or query, or whether the tests catch bugs: `code-reviewer`
- Writing tests for HTTP clients, messaging, events, who may call each route, or full-API tests with containers: `writing-springboot-tests`
- Changing these rules or the build checks: `spring-boot-team-harness`
<!-- modules:begin -->

## Modules

Each direct subpackage of `{{BASE_PACKAGE}}` is a module. Its top-level package is its API; nested packages are internal.

<!-- List the modules and what each owns, one line each. -->
<!-- modules:end -->

## Run and test

<!-- How to start the app locally, what it needs (Docker, env vars, ports), and which tests need Docker. -->

## Team conventions

<!-- Only what this team decided and a newcomer could not guess, for example:
- Integration tests use Testcontainers, never H2.
- Money is a value type, never double. -->
