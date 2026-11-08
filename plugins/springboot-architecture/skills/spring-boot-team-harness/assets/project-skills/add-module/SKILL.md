---
name: add-module
description: Adds a new application module to this Spring Modulith project with the package layout the ModuleBoundariesTests gate expects, and a module-scoped integration test. Use when the user asks for a new module, new top-level package, bounded context, or feature area that doesn't belong in an existing module.
---

# Add a module

Each direct subpackage of `{{BASE_PACKAGE}}` is a module. `{{VERIFY}}` fails if another module reaches into its nested packages or if modules form a cycle.

1. Pick a name from the domain language: the glossary term for the capability (`GLOSSARY.md` or `CONTEXT.md`), such as `billing` or `ticketing`, not a vendor (`zendesk`), a layer (`billingservice`) or `common`. If the glossary has no such term, agree one with the user and add it there first: one line saying what it means, no implementation detail. Check that no existing module owns it; the `Modules` section of `AGENTS.md` lists them.
2. Create the layout:
   ```
   {{BASE_PACKAGE}}.<module>            public API: the service other modules call, the records it takes and returns, its events
   {{BASE_PACKAGE}}.<module>.internal   everything else: implementation, entities, repositories, controllers
   ```
   Keep the top-level package small. Entities and repositories never go in it.
3. Let other modules talk to it in one of two ways only: call a type in its top-level package, or listen for an event it publishes (`@ApplicationModuleListener`). Prefer events when the caller doesn't need an answer.
4. Add `package-info.java` with `@ApplicationModule(allowedDependencies = {...})`, listing exactly the modules its code calls, each with the user's agreement. The build fails on any other dependency and on an entry nothing uses, and IntelliJ IDEA flags the first in the editor. Once the file exists, changing those rules is for the user: the harness refuses the edit.
5. Add `src/test/java/{{BASE_PATH}}/<module>/<Module>ModuleTests.java`, annotated `@ApplicationModuleTest(verifyAutomatically = false)`, which starts only this module. `ModuleBoundariesTests` checks the boundaries, honouring the record of older violations; a module test that checked them too would fail on those. Test the module through its public API.
6. Add one line for the module to the `Modules` section of `AGENTS.md`.
7. Run `{{VERIFY}}`. If it fails, fix what it names and run it again until it passes. A dependency the build rejects is a design question: route it through the other module's top-level package or an event, or ask the user to allow it; don't widen `allowedDependencies` on your own.
