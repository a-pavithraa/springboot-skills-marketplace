# {{PROJECT_NAME}}

Spring Boot {{BOOT_VERSION}} on Java {{JAVA_VERSION}}. Base package: `{{BASE_PACKAGE}}`.

## Done means verify passes

Run `./mvnw verify` (`mvnw.cmd verify` on Windows) before you say a change is finished, and report its result. Don't claim it passed without running it. These gates fail the build:

| Gate | Fails when | Fix |
| --- | --- | --- |
| NullAway, at compile | Code under `{{BASE_PACKAGE}}` can pass or return `null` where the type doesn't allow it | Annotate with `org.jspecify.annotations.Nullable` and handle the null. Don't add `@SuppressWarnings("NullAway")`, and don't add `@NullUnmarked`: classes that have it are legacy code waiting to be fixed |
<!-- modules:begin -->
| `ModuleBoundariesTests` | A module uses another module's nested (internal) package, or modules depend on each other in a cycle | Call the other module through a type in its top-level package, or publish an event |
<!-- modules:end -->
| `ConfigurationKeysTests` | A `spring.`, `management.`, `server.` or `logging.` key in `application*.properties` or `.yml` is unknown or deprecated | Use the key the message names, or the dependency that defines it |
| `CodeRulesTests` | A class calls its own `@Transactional`, `@Async`, `@Cacheable` or `@Retryable` method; a controller starts a transaction or uses a repository; a field is `@Autowired`; code prints to `System.out`; code uses Jackson 2, Spring's nullness annotations or JUnit 4 | Each failure message says what to do instead. Violations recorded in `src/test/resources/archunit_store` are older than the harness and tolerated; never edit that record to get a new one through, and don't change `archunit.properties`. If the rules fail on many classes nobody changed and there is no record, the existing code was never baselined: ask the user to run the harness's `baseline.py` |
| Spotless | Code isn't formatted | Run `./mvnw spotless:apply` |

`verify` also runs the tests that start containers, so Docker must be running. If it isn't, say that those tests didn't run. Don't skip or disable them.

In Claude Code, a hook runs the gates that need no Docker whenever a turn ends with changed code, and sends any failure back to you. In other tools, run `./mvnw verify` yourself.

## How to work here

- If you can describe the change in one sentence, make it. Otherwise read the code it touches and agree a plan with the user first, with the `grilling` or `html-plan` skill if installed.
- For a bug, first write a test that fails because of it, then fix the code.
- Before you open a pull request, review the diff with the `code-reviewer` skill and write the description with the `pr` skill, if they are installed. Fix what the review finds.
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
