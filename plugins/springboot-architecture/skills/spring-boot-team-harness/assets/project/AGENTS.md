# {{PROJECT_NAME}}

Spring Boot {{BOOT_VERSION}} on Java {{JAVA_VERSION}}. Base package: `{{BASE_PACKAGE}}`.

## Done means verify passes

Run `./mvnw verify` (`mvnw.cmd verify` on Windows) before you say a change is finished, and report its result. Don't claim it passed without running it. These gates fail the build:

| Gate | Fails when | Fix |
| --- | --- | --- |
| NullAway, at compile | Code under `{{BASE_PACKAGE}}` can pass or return `null` where the type doesn't allow it | Annotate with `org.jspecify.annotations.Nullable` and handle the null. Don't add `@SuppressWarnings("NullAway")` |
<!-- modules:begin -->
| `ModuleBoundariesTests` | A module uses another module's nested (internal) package, or modules depend on each other in a cycle | Call the other module through a type in its top-level package, or publish an event |
<!-- modules:end -->
| `ConfigurationKeysTests` | A `spring.`, `management.`, `server.` or `logging.` key in `application*.properties` or `.yml` is unknown or deprecated | Use the key the message names, or the dependency that defines it |
| Spotless | Code isn't formatted | Run `./mvnw spotless:apply` |
<!-- modules:begin -->

## Modules

Each direct subpackage of `{{BASE_PACKAGE}}` is a module. Its top-level package is its API; nested packages are internal.

<!-- List the modules and what each owns, one line each. -->
<!-- modules:end -->

## Team conventions

<!-- Only what this team decided and a newcomer could not guess, for example:
- Integration tests use Testcontainers, never H2.
- Money is a value type, never double. -->
