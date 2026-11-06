---
name: add-module
description: Adds a new application module to this Spring Modulith project with the package layout the ModuleBoundariesTests gate expects, and a module-scoped integration test. Use when the user asks for a new module, bounded context, or feature area that doesn't belong in an existing module, and when code in one module needs another: whether to call its API or publish an event, and whether `@Async` or `CompletableFuture` fits.
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
3. Let other modules talk to it in one of two ways only: call a type in its top-level package, or listen for an event it publishes. Pick by what the caller needs, not by taste:
   - **It needs an answer, or must fail when this module refuses** (a lookup, a check, a price, an id): call the service in the top-level package. It runs in the caller's transaction and its exception reaches the caller.
   - **It only reports that something happened, and the follow-up can finish later** (a notice, a read model, a call to an external system): publish an event record, with ids and facts and no entities, from the transaction that changed the state, and handle it with `@ApplicationModuleListener`. The project needs an event publication registry (`spring-modulith-starter-jdbc` and its `event_publication` table) so the event survives a restart and a failed listener can be resubmitted. Make the listener idempotent: the registry can deliver an event twice.
   - **A direct call would add a dependency `allowedDependencies` doesn't list, or close a cycle**: publish an event. The publisher then doesn't depend on the listener. Don't add the dependency without the user.
   - Neither a `void` `@Async` method nor a `CompletableFuture` is a way for modules to talk. The first loses its work if the app stops before it ends, unless the work is saved in a table that a `@Scheduled` method retries; the second is for a result the caller waits for, such as slow calls run in parallel and joined.
   - When users see the follow-up's outcome and can retry it (a ticket raised or failed), that status is this module's data and belongs in its table. The registry only guarantees the event is delivered.
4. Add `package-info.java` with `@ApplicationModule(allowedDependencies = {...})`, listing exactly the modules its code calls, each with the user's agreement. The build fails on any other dependency and on an entry nothing uses, and IntelliJ IDEA flags the first in the editor. Once the file exists, changing those rules is for the user: the harness refuses the edit.
5. Add `src/test/java/{{BASE_PATH}}/<module>/<Module>ModuleTests.java`, annotated `@ApplicationModuleTest(verifyAutomatically = false)`, which starts only this module. `ModuleBoundariesTests` checks the boundaries, honouring the record of older violations; a module test that checked them too would fail on those. Test the module through its public API, and an event it handles with the `Scenario` test parameter: `scenario.publish(event).andWaitForStateChange(...)`.
6. Add one line for the module to the `Modules` section of `AGENTS.md`.
7. Run `{{VERIFY}}`.
