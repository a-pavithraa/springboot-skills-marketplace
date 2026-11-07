---
name: add-module
description: Adds a new application module to this Spring Modulith project with the package layout the ModuleBoundariesTests gate expects, and a module-scoped integration test. Use when the user asks for a new module, bounded context, or feature area that doesn't belong in an existing module, and when code in one module needs another: whether to call its API or publish an event.
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
3. Other modules use this one in two ways only:
   - **They need an answer or must fail with it:** call a service in the top-level package.
   - **They only report that something happened:** the module where it happened publishes an event record from its top-level package (ids and facts, no entities), and the other module handles it with an idempotent `@ApplicationModuleListener`. The project needs the event publication registry (`spring-modulith-starter-jdbc` and its `event_publication` table), so a failed listener can be resubmitted.
   - **The listener depends on the publisher:** Spring Modulith counts the event type like any other reference, for `allowedDependencies` and for cycles. So an event breaks a cycle when the module that would call publishes instead, but it doesn't avoid a missing `allowedDependencies` entry: it moves the entry to the listener's module. Ask the user for that entry; don't add it yourself.
   - **Never call another module's `void` `@Async` method:** publish an event instead.
4. Add `package-info.java` with `@ApplicationModule(allowedDependencies = {...})`, listing exactly the modules its code calls, each with the user's agreement. The build fails on any other dependency and on an entry nothing uses, and IntelliJ IDEA flags the first in the editor. Once the file exists, changing those rules is for the user: the harness refuses the edit.
5. Add `src/test/java/{{BASE_PATH}}/<module>/<Module>ModuleTests.java`, annotated `@ApplicationModuleTest(verifyAutomatically = false)`, which starts only this module. `ModuleBoundariesTests` checks the boundaries, honouring the record of older violations; a module test that checked them too would fail on those. Test the module through its public API, and an event it handles with the `Scenario` test parameter: `scenario.publish(event).andWaitForStateChange(...)`.
6. Add one line for the module to the `Modules` section of `AGENTS.md`.
7. Run `{{VERIFY}}`.
