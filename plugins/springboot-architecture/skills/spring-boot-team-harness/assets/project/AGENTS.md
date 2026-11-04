# {{PROJECT_NAME}}

Spring Boot {{BOOT_VERSION}} on Java {{JAVA_VERSION}}, built on JDK {{BUILD_JDK}} (Error Prone needs 21.0.8 or later). Base package: `{{BASE_PACKAGE}}`.

## Done means verify passes

Run `./mvnw verify` (`mvnw.cmd verify` on Windows) before you say a change is finished, and report its result. Don't claim it passed without running it. These gates fail the build:

| Gate | Fails when | Fix |
| --- | --- | --- |
| NullAway, at compile | {{NULLAWAY_CHECKED}} can pass or return `null` where the type doesn't allow it | Annotate with `org.jspecify.annotations.Nullable` and handle the null. Don't add `@SuppressWarnings("NullAway")`, and don't add `@NullUnmarked`: classes that have it are legacy code waiting to be fixed. NullAway skips all of such a class, your changes included, so when you change one, remove the mark and fix what NullAway reports; if that grows past the change, put the mark back and say the class is still unchecked |
<!-- modules:begin -->
| `{{BOUNDARY_TEST}}` | A module uses another module's internal type (outside its top-level package and named interfaces), modules depend on each other in a cycle, a module depends on one its `allowedDependencies` leave out or lists one it doesn't use | Call the other module through a type in its top-level package, or publish an event. Don't change `allowedDependencies` or a module's type to get through: ask the user. Violations in the violation record `src/test/resources/modulith_store` are older than the harness and tolerated; never edit it. When you change a module, fix its recorded violations one module per change |
<!-- modules:end -->
| `ConfigurationKeysTests` | A `spring.`, `management.`, `server.` or `logging.` key in `application*.properties` or `.yml` is unknown or deprecated | Use the key the message names, or the dependency that defines it |
| `CodeRulesTests` | Code compiles but breaks at runtime or on an upgrade. Among the rules: a class calls its own `@Transactional` or `@Async` method; a controller starts a transaction, uses a repository, or takes or returns a JPA entity; a transaction waits on an HTTP or AWS call; a service throws `ResponseStatusException`; a test is `@Disabled` | Each failure message says what to do instead. Violations recorded in `src/test/resources/archunit_store` are older than the harness and tolerated; never edit that record to get a new one through, and don't change `archunit.properties`. If a rule fails on code nobody changed, the record is missing or older than the rule: ask the user to run the harness's `baseline.py` |
<!-- observability:begin -->
| `LogLeakCheck` (around every test) | The app's code logs an email address or a credential | Log an internal id, or give the type a `toString` that leaves the value out |
<!-- observability:end -->
| `BuildSetupTests` | A Boot starter is in `test` scope; `spring-boot-autoconfigure-classic` is a dependency; Flyway migrations exist without `spring-boot-starter-flyway`; `ddl-auto` creates or updates the schema, or code writes `flyway_schema_history` | Each failure message says what to do instead. Don't work around a missing feature by adding it to the test classpath only |
| `UnusedCodeTests` (in `verify` only, not the end-of-turn check) | A non-private method is called only from tests | If the change is meant to call it, wire that up. Otherwise test through the public behaviour and delete the method; don't open up internals for a test. If the user asked for a method nothing calls yet, ask them; don't route existing code through it to pass |
| {{FORMATTER}} | Code isn't formatted | Run `./mvnw {{FORMAT_APPLY}}` |

Log levels: ERROR means someone must act, and passes the exception as the last argument. WARN means the app recovered but someone should look. INFO is one line per business state change. DEBUG is everything else. Log internal ids, never personal data or credentials. Let `@ExceptionHandler` methods build the response<!-- failure-filter:begin -->; `HandledFailureFilter` logs every 5xx with its cause, so don't log the same exception again<!-- failure-filter:end -->.

<!-- observability:begin -->
To see what the running app did, read `docs/observability.md`. It shows how to start the local stack and query traces, metrics and logs. A response that looks right can hide a failure, so check for errors as well.

Before you say a change to runtime behaviour works, prove it on one request: start the app from this checkout with the local stack, run `python3 observability/check_request.py --service <spring.application.name> <url>` on a request the change affects, and report its output. The check shows the request ran here and hid no failure. You still have to say what in the trace or response shows the change worked. If you can't run the app or the stack, say that the change isn't verified at runtime. Tests alone aren't this proof, and neither is `check_dashboards.py`.

<!-- observability:end -->
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

Each direct subpackage of `{{BASE_PACKAGE}}` is a module. Its top-level package is its API; nested packages are internal. A module that declares `@ApplicationModule(allowedDependencies = ...)` in its `package-info.java` may depend only on those modules; add one there only when the user agrees the dependency belongs.

Modules are named in the domain language of the project's glossary (`GLOSSARY.md` or `CONTEXT.md`): each owns a section of it, and is named after that business capability, not a vendor or a layer. A term the glossary lacks is agreed with the user and added there before code uses it.

<!-- List the modules, one line each: name, the glossary section it owns, what it owns. -->
<!-- modules:end -->

## Run and test

<!-- How to start the app locally, what it needs (Docker, env vars, ports), and which tests need Docker. -->

## Team conventions

<!-- Only what this team decided and a newcomer could not guess, for example:
- Integration tests use Testcontainers, never H2.
- Money is a value type, never double. -->
