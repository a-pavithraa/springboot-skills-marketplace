# Side effects across modules in a Spring Boot 4 / Spring Modulith 2.x monolith

Date: 2026-11-07. Scope: what a module's save should do when another module must react, often by calling an external system (for example, raising a ticket in an external ticketing system).

Source conventions:
- `modulith@2.1.1:<path>:<line>` is a file in the Spring Modulith tag 2.1.1 (blob read with `git cat-file`; the local clone's working tree has staged deletions for these files, so the tag blobs are the citation).
- `docs:<page> <section>` is the Spring Modulith 2.1.1 reference page at `src/docs/antora/modules/ROOT/pages/<page>.adoc` in the tag.
- Spring Framework and Spring Boot references are cited by URL (fetched 2026-11-07).

## 1. The question

1. Which mechanism should carry a follow-up from one module's save to another module, including a call to an external system?
   - (a) synchronous call inside the save;
   - (b) `void @Async` method;
   - (c) application event with `@ApplicationModuleListener` and the event publication registry;
   - (d) hand-made outbox (a pending row plus a scheduled retry);
   - (e) event externalization or a message broker.
2. Where does the user-visible status of that follow-up (raised, failed, retry) belong: in the registry or in the module's own table?
3. Which architecture decisions do coding agents tend to shortcut in such codebases, and what rule should each agent apply?

## 2. Short answer

Decision table (situation, mechanism, why):

| Situation | Mechanism | Why |
|---|---|---|
| Follow-up is local data work in the same module and must be atomic with the save | Same transaction, direct call | Nothing to decouple; a rollback should undo it. |
| Follow-up is an internal reaction in another module; must not block the save; must survive a crash | Publish an application event from the save; handle it with `@ApplicationModuleListener` | The registry writes one publication row in the save's transaction, so an uncommitted save produces no reaction. Completion is recorded on success; failed publications can be resubmitted (modulith@2.1.1 `PersistentApplicationEventMulticaster.java:142`, `DefaultEventPublicationRegistry.java:81`, `CompletionRegisteringAdvisor.java:170,180,212`). |
| Follow-up calls an external system, and users must see its status and retry it | Domain table is the record of truth: a state column (PENDING / DONE / FAILED) plus a failure reason. A listener or a scheduled sweep claims PENDING rows and moves them. | Status the user acts on is domain state. The registry is internal delivery bookkeeping with no status API for it (`docs:events Event Publication Completion`). |
| Work is fire-and-forget and loss is acceptable (cache warm-up, metrics) | `void @Async` method | No delivery record; exceptions are only logged by default (Spring scheduling reference, "Exception Management with @Async"). |
| The save's own response depends on the external result | Synchronous call with timeouts, outside the save's transaction, accepting the coupling | Only justified when the result belongs in the response. Otherwise an external outage blocks the user. |
| Events must reach another process or system | Event externalization or a broker, with an outbox | The registry guards broker failures. Modulith's built-in externalization is documented as lacking outbox features (`docs:events Externalizing Events`). |
| Hand-written outbox | Only where the registry cannot express the need (for example, a queryable status with a manual retry screen) | It is more code and needs a claim column and an idempotency key. |

Default for an agent: for cross-module reactions, publish an event in the save and handle it with `@ApplicationModuleListener`. When the reaction calls an external system whose result the user sees, keep the domain row as the outbox (state column plus reason), use the listener to attempt the send promptly after commit, and use a scheduled sweep to recover stuck rows. The registry is not the place for business status.

## 3. Findings

### F1. `@ApplicationModuleListener` is a composition of three annotations

`ApplicationModuleListener` is annotated `@Async`, `@Transactional(propagation = REQUIRES_NEW)`, and `@TransactionalEventListener`. `@TransactionalEventListener` defaults to the commit phase.
- Source: `modulith@2.1.1:spring-modulith-events/spring-modulith-events-api/src/main/java/org/springframework/modulith/events/ApplicationModuleListener.java:45-47`.
- Default phase `AFTER_COMMIT`, and a listener is not invoked when no transaction is active unless `fallbackExecution = true`: https://docs.spring.io/spring-framework/reference/data-access/transaction/event.html
- The registry only tracks listeners in the `AFTER_COMMIT` phase: `modulith@2.1.1:.../events/support/PersistentApplicationEventMulticaster.java:335`.

Consequence: the listener runs on another thread, in its own transaction, after the publisher's transaction commits. A listener failure cannot roll back the save.

### F2. The publication row is written inside the publisher's transaction, before the listener runs

`PersistentApplicationEventMulticaster.multicastEvent` stores the publications (line 142) and then invokes the listeners (line 145). The store calls `DefaultEventPublicationRegistry.store` (`modulith@2.1.1:.../events/core/DefaultEventPublicationRegistry.java:81`). The JDBC repository is `@Transactional` at class level (`modulith@2.1.1:spring-modulith-events/spring-modulith-events-jdbc/src/main/java/org/springframework/modulith/events/jdbc/JdbcEventPublicationRepositoryV2.java:55`), so the write joins the publisher's transaction (its default is REQUIRED).

Docs say the same: "writes entries ... into an event publication log as part of the original business transaction" (`docs:events The Event Publication Registry`).

Consequence: if the save rolls back, there is no publication and no listener call. This is the main reason to prefer (c) over (b).

### F3. Completion is recorded after the listener succeeds; the mechanism gives at-least-once delivery in practice

- The advisor marks `PROCESSING` before the listener body (`CompletionRegisteringAdvisor.java:170`), marks `COMPLETED` after it returns (`:180` for futures, `:196` for synchronous results), and marks `FAILED` on exception (`:212`).
- Each mark runs in `REQUIRES_NEW` (`DefaultEventPublicationRegistry.java:116,126,146`).
- Docs: "Event publications are marked as completed when a transactional or `@ApplicationModuleListener` execution completes successfully" (`docs:events Event Publication Completion`).

Consequence (derived, not stated by the docs): if the listener's transaction commits and the `COMPLETED` mark then fails, the publication stays incomplete and runs again on resubmission. The docs never say "idempotent" or "at-least-once"; listeners must be idempotent anyway.

### F4. Failed publications, restart, and staleness

- Failed publications can be resubmitted with `FailedEventPublications.resubmit(ResubmissionOptions)`. Options include batch size, max in-flight, minimum age, and a filter (for example by `completionAttempts`) (`docs:events Failed publications and resubmission`; `modulith@2.1.1:.../events/core/DefaultEventPublicationRegistry.java:228`).
- Restart: `spring.modulith.events.republish-outstanding-events-on-restart` defaults to `false` (`modulith@2.1.1:spring-modulith-events/spring-modulith-events-core/src/main/resources/META-INF/spring-configuration-metadata.json`). When `true`, `afterSingletonsInstantiated` resubmits every incomplete publication with filter `__ -> true` (`PersistentApplicationEventMulticaster.java:78,190-201`). In a multi-instance deployment this also resubmits publications that other live instances are still processing.
- Staleness: the staleness monitor is only scheduled when a staleness duration is non-zero (`modulith@2.1.1:.../events/config/StalenessMonitorConfiguration.java:64`; `docs:events Event Publication Staleness`). With defaults, a publication stuck in `PROCESSING` after a crash is never marked failed automatically.
- Shutdown: `DefaultEventPublicationRegistry.destroy` only logs unfinished publications (`DefaultEventPublicationRegistry.java:266-284`). It does not wait for them.

### F5. `void @Async` loses exceptions and in-flight work

- Exceptions from a `void @Async` method are "merely logged" by default; a custom `AsyncUncaughtExceptionHandler` can be defined (https://docs.spring.io/spring-framework/reference/integration/scheduling.html, "Exception Management with @Async").
- The Spring page describes graceful shutdown of `ThreadPoolTaskExecutor` but does not document the wait-on-shutdown setting. I did not verify its default (open question 3).
- Without a record, work in flight at shutdown or a crash is gone unless the method writes its own record.

### F6. Transactions and `@Async`

- Spring: "listeners are guaranteed to see the current thread-bound transaction" (event page). The `@Async` page does not say whether transaction context propagates to the async thread.
- Derived (not quoted from docs): an `@Async` method started from inside a transaction is handed to another thread immediately. It can start before the publisher commits, and then it cannot see the uncommitted rows. `@ApplicationModuleListener` avoids this by waiting for `AFTER_COMMIT`. Verify with a test before relying on it.

### F7. Module dependencies and cycles

- Modules expose the event type they publish as part of their provided interface (`docs:fundamentals`, first section).
- The listener's module depends on the publisher's module, because it imports the event type. The publisher does not need to depend on the listener.
- `verify()` checks for cycles, access to internal packages, and `allowedDependencies` (`docs:verification`; `docs:fundamentals Explicit Application Module Dependencies`).
- Event-listener dependencies are a dependency type in the model (`modulith@2.1.1:spring-modulith-core/src/main/java/org/springframework/modulith/core/ApplicationModule.java:187`). I did not confirm that cycle detection includes them (open question 5).

### F8. External HTTP calls from a listener

Modulith gives no retry, no timeout, and no idempotency key. Those belong in the listener's client and in the domain. Guidance (design, not sourced from the docs):
- set connect and read timeouts, and keep the total retry time well under the stale threshold used by the domain sweep;
- retry only idempotent calls, and send an idempotency key for create calls;
- do not retry a non-idempotent call (for example, adding a comment without a key) automatically; mark it failed for a human to retry;
- cap attempts (`completionAttempts`) before a publication is treated as permanently failed.

### F9. Business status does not belong in the registry

- The registry's public APIs are `CompletedEventPublications`, `IncompleteEventPublications` and `FailedEventPublications`. They describe delivery, not business state (`docs:events Managing Event Publications`).
- Completed publications are kept, deleted, or archived depending on `spring.modulith.events.completion-mode` (`docs:events Event Publication Completion`). Business status must not depend on that retention.
- So: "raised", "failed with reason X", and "retry" are columns in the module's own table, updated by the listener or the sweep.

### F10. Event externalization and brokers

- Modulith's built-in externalization is an async transactional listener; the docs say it "lacks critical features developers might expect from actual outbox pattern implementations" and point to Namastack Outbox and JobRunr support (`docs:events Externalizing Events`).
- The registry guards the broker interaction, so failed sends can be resubmitted (`docs:events Fundamentals of Event Externalization`).
- A broker adds infrastructure and a second failure domain. Use it only when another process or system must receive the event.

### F11. Versions

- The local clone is at tag 2.1.1. The client codebase in the related review uses Spring Modulith 2.1.0 (its pom). I did not diff 2.1.0 against 2.1.1 for the events code (open question 1).

### F12. An after-commit listener writes only in a new transaction

- A `@TransactionalEventListener` runs after the publisher's transaction commits (the default `AFTER_COMMIT` phase), on the publisher's thread. The finished transaction's resources are still bound there, so "any data access code triggered at this point will still 'participate' in the original transaction ... (with no commit following anymore!)". Spring's advice: "Use `PROPAGATION_REQUIRES_NEW` for any transactional operation that is called from here." Source: [`TransactionSynchronization.afterCommit` Javadoc](https://github.com/spring-projects/spring-framework/blob/main/spring-tx/src/main/java/org/springframework/transaction/support/TransactionSynchronization.java).
- A listener in a phase other than `BEFORE_COMMIT` that carries `@Transactional` with any propagation except `REQUIRES_NEW` or `NOT_SUPPORTED` fails at startup: "@TransactionalEventListener method must not be annotated with @Transactional unless when declared as REQUIRES_NEW or NOT_SUPPORTED". Source: [`RestrictedTransactionalEventListenerFactory`](https://github.com/spring-projects/spring-framework/blob/main/spring-tx/src/main/java/org/springframework/transaction/annotation/RestrictedTransactionalEventListenerFactory.java). A listener with no `@Transactional` at all is not caught: its writes are silently not committed.
- `@ApplicationModuleListener` already declares `@Transactional(propagation = REQUIRES_NEW)` and `@Async` (F1).

| Listener | Thread | Transaction | Writes |
|---|---|---|---|
| `@EventListener` | publisher's | publisher's, still open | commit or roll back with the publisher |
| `@TransactionalEventListener` alone | publisher's, after commit | the finished one | silently not committed |
| + `@Transactional(REQUIRES_NEW)` | publisher's, after commit | a new one | committed, but the publisher waits |
| `@ApplicationModuleListener` | another thread | a new one | committed, the publisher doesn't wait, and the registry tracks it |

No ArchUnit rule is proposed for the silent case: a rule can't tell a listener that writes from one that only reads.

## 4. Agent shortcuts

Each entry: the shortcut, the correct default, when the shortcut is fine, and a one-line rule for the agent.

1. **"`@Async` is enough; an event listener is not worth it."**
   - Correct default: use `@ApplicationModuleListener` for a cross-module reaction whose loss would matter (F2, F3, F5).
   - Fine when: the reaction is best-effort (cache, metrics, notification that can be skipped) and nothing needs to be retried or inspected.
   - Rule: "If losing this reaction matters, publish an event in the save and handle it with `@ApplicationModuleListener`; `@Async` is for best-effort work only."

2. **"Use `@TransactionalEventListener` (or `@EventListener`) directly."**
   - Correct default: `@ApplicationModuleListener`, which adds `@Async` and `REQUIRES_NEW`. A plain `@TransactionalEventListener` runs on the publisher's thread after commit, so a slow external call delays the publisher's response (F1).
   - Fine when: the listener is quick and local (for example, updating an in-memory index).
   - Rule: "Cross-module external work goes through `@ApplicationModuleListener`, not a bare transactional listener."

3. **"Call the other module's service directly inside the save."**
   - Correct default: publish an event. A direct call couples the modules, puts the external latency inside the save, and makes a failure roll back the save or hide it.
   - Fine when: the other module's call is local, fast, part of the same transaction on purpose, and the module's `allowedDependencies` already allow it.
   - Rule: "A save never calls another module's external-system client directly; publish an event."

4. **"Store the ticket status in the event registry."**
   - Correct default: the module's own table with a state column and failure reason (F9).
   - Fine when: never for user-visible status. The registry may hold delivery state for operators.
   - Rule: "Business status (pending, done, failed, retry) is a column in the owning module's table."

5. **"A hand-written outbox is simpler than the registry."**
   - Correct default: use the registry for internal reactions. Hand-write an outbox only when the user must see and retry the status (F9), and then use a claim column plus an idempotency key.
   - Fine when: the status-table design is already in place and tested, and swapping it would add risk without a benefit.
   - Rule: "A status-table outbox needs a claim (with a timeout), an idempotency key for the external call, and a sweep for stuck rows."

6. **"Retry the external call with `@Retryable` everywhere."**
   - Correct default: retry only idempotent calls. A non-idempotent call that timed out may have succeeded, and a retry duplicates it (F8).
   - Fine when: the operation is idempotent or carries a server-side idempotency key.
   - Rule: "Automatic retry only for idempotent calls or calls with an idempotency key; otherwise mark failed for a human retry."

7. **"The listener will run exactly once."**
   - Correct default: the listener must be idempotent (F3, F4).
   - Fine when: never assumed.
   - Rule: "Every `@ApplicationModuleListener` must be safe to run twice for the same event."

8. **"Turn on republish-on-restart to recover from crashes."**
   - Correct default: leave it off in a multi-instance deployment, or accept duplicate runs; enable staleness with a non-zero duration if stuck `PROCESSING` rows must be recovered (F4).
   - Fine when: a single instance, and the listeners are idempotent.
   - Rule: "Do not enable republish-on-restart without a single-instance check and idempotent listeners."

9. **"`@Async` runs after the transaction, so the data is there."**
   - Correct default: use `AFTER_COMMIT` (F6). Hand-off to an async thread inside a transaction can run before commit.
   - Fine when: the async work does not read the save's data.
   - Rule: "Work that reads the save's data starts after commit (`@ApplicationModuleListener`), never from inside the transaction via `@Async`."

10. **"Events make a module depend on another one, so use a broker."**
    - Correct default: in-process events do not add a module dependency beyond the event type (F7). A broker is for other processes (F10).
    - Fine when: a second process or system consumes the event.
    - Rule: "Keep events in-process unless another process must consume them; then externalize with an outbox."

## 5. Open questions and what I could not verify

1. Modulith 2.1.0 (used by the client) versus 2.1.1 (read here): I did not diff the events code between them.
2. The `AbstractAdvisingBeanPostProcessor` source (advisor insertion order) was not retrievable (404 on the path I tried). The `beforeExistingAdvisors = true` setting in `AsyncAnnotationBeanPostProcessor` was fetched from the Spring Framework main branch, not the 6.x/7.x release used by the framework. The exact ordering between `@Async`, `@Transactional`, and the completion advisor (F3) is therefore inferred from code, not confirmed by a test.
3. Spring Boot's `spring.task.execution` defaults (max size, queue capacity, shutdown await-termination) were not retrieved; the Boot appendix page was too long for the fetch.
4. Whether an `@Async` method started inside a transaction can run before commit (F6) is a consequence of the threading model, not quoted from any page. Test it before relying on it.
5. Resolved: Modulith's cycle check is an ArchUnit `slices().should().beFreeOfCycles()` over all classes (`ApplicationModules.java:611-619`), so a listener's reference to another module's event type counts toward cycles; `detectDependencies` checks every dependency type, `EVENT_LISTENER` included, against `allowedDependencies` (`ApplicationModule.java:389-394`, `674-678`).
6. Modulith's docs do not say "at-least-once" or "idempotent"; F3 is derived from the completion code.
7. I did not run any Modulith test or build; all statements about behavior come from reading the source and docs.
8. Documentation inconsistency noticed: the appendix gives `spring.modulith.events.jdbc-schema-initialization.enabled` while the events page gives `spring.modulith.events.jdbc.schema-initialization.enabled`. Check the property name against the code before use.
