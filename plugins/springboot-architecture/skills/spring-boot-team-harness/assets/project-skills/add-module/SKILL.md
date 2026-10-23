---
name: add-module
description: Adds a new application module to this Spring Modulith project with the package layout the ModuleBoundariesTests gate expects, and a module-scoped integration test. Use when the user asks for a new module, bounded context, or feature area that doesn't belong in an existing module.
---

# Add a module

Each direct subpackage of `{{BASE_PACKAGE}}` is a module. `./mvnw verify` fails if another module reaches into its nested packages or if modules form a cycle.

1. Pick a name: a noun for the capability, such as `billing`, not `billingservice` or `common`. Check that no existing module owns it; the `Modules` section of `AGENTS.md` lists them.
2. Create the layout:
   ```
   {{BASE_PACKAGE}}.<module>            public API: the service other modules call, the records it takes and returns, its events
   {{BASE_PACKAGE}}.<module>.internal   everything else: implementation, entities, repositories, controllers
   ```
   Keep the top-level package small. Entities and repositories never go in it.
3. Let other modules talk to it in one of two ways only: call a type in its top-level package, or listen for an event it publishes (`@ApplicationModuleListener`). Prefer events when the caller doesn't need an answer.
4. Add `src/test/java/{{BASE_PATH}}/<module>/<Module>ModuleTests.java`, annotated `@ApplicationModuleTest`, which starts only this module. Test the module through its public API.
5. Add one line for the module to the `Modules` section of `AGENTS.md`.
6. Run `./mvnw verify`.
