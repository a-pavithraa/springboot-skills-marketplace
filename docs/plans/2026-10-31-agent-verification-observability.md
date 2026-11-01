# Observability as the agent's verification loop

**Status:** Phases 1 and 2 built and not committed. The Phase 3 trial showed no gain for the CLI (`tests/baseline-results/scenario-27.md`), so Phases 4 and 5 are on hold until a harder trial says otherwise.

**Goal:** Let a coding agent prove a Spring Boot change works by reading what the running app did, not only what the page shows. Config and code-rule gates from `2026-10-31-observability-research.md` stay useful, but they are the smaller part of this.

**Scope:** The local verification loop. ECS and production monitoring are kept outside this repository.

---

## The gap

The harness has two kinds of proof today.

| Proof | Answers | Blind to |
| --- | --- | --- |
| `./mvnw verify` gates | Is the code well formed? | Anything at runtime |
| Browser journeys (`references/browser-verification.md`) | Did the user see the right thing? | Everything behind the page |

Nothing answers: **what did the server do for that request?** A journey can pass while the server swallowed an exception, fell back to a default, retried a dependency, or ran 200 queries. These bug classes are this note's own hypothesis until the trial below measures them.

## What the sources say

| Source | Point used here |
| --- | --- |
| Addy Osmani, [Agentic Verification](https://addyo.substack.com/p/agentic-verification) | Without self-verification, the human is "the slowest, costliest feedback loop". Signals must be fast and deterministic. "Specific messages about what failed are better than voluminous logs about what passed." Screenshots, tracing and the failed step stop the agent working blind. |
| Addy Osmani, [Agent Harness Engineering](https://addyosmani.com/blog/agent-harness-engineering/) | "Success is silent, failures are verbose." Browsers, logs, screenshots and test runners close the self-verification loop. |
| Addy Osmani, [AI writes code faster](https://addyosmani.com/blog/code-review-ai/) | The PR contract: intent, proof, risk, review focus. (Search excerpt.) |
| Lauren Tan, [Complete Guide to pstack Pt. 1](https://x.com/poteto/status/2094457600259842065) | Verification is "critical infrastructure". "Build the Lever": give agents a small CLI, not only markdown. CLI properties: composable, `--dry-run` on destructive commands, subcommands, errors that say what to do instead, rich `--help`, machine-readable output. Her example command groups include `console`, `network-log`, `trace` and `perf-metrics`. Keep a Feature Map. Run `/maintain-verification-skill` daily. |
| Lauren Tan, [Loops You Can Trust](https://x.com/poteto/status/2069824386283319343) | Teach verification before building loops. "'I fixed it' isn't good enough. Show me the trace, the heap snapshot, or the screenshot." |
| [Datadog](https://www.datadoghq.com/blog/ai/harness-first-agents/) | "explicit invariants turn every agent iteration into an objective pass/fail decision". "Without observability, the loop is not closed." |
| OpenAI, Harness Engineering | Reported to give each worktree an ephemeral logs, metrics and traces stack, so prompts like "no span in these journeys exceeds two seconds" become workable. The original returned 403, so this comes from [VictoriaMetrics' commentary](https://victoriametrics.com/blog/observability-lessons-from-openai/). Treat as secondary. |

Limit of these sources: Addy and Lauren name logs and traces as agent inputs, but neither sets out a server-side telemetry design. Their examples are mostly client apps. The structure below is this note's extension of their principles to Spring Boot.

## The decision that changes the harness

`browser-verification.md` says the harness ships no browser skill, because journeys depend on the app. **Telemetry does not.** Every target is Boot 4 with a known log format and known endpoints. So the harness can ship the telemetry part as a working tool, and the generated verification skill calls it.

## The structure

```
journey or curl  ──traceparent: <id>──►  app (verify profile)
       │                                    │ JSON log file, spans, metrics
       ▼                                    ▼
  telemetry CLI  ◄── reads by trace id ── Tier 1: log file
  (JSON, exit codes)                      Tier 2: Tempo, Prometheus
       │
       ▼
  evidence row: trace id, new errors, budgets, failed-first
```

### 1. Correlation: one id from action to logs

An agent must find the logs for its own request, not grep a shared file.

Default proposal: **the client picks the trace id.** The CLI or journey generates an id and sends W3C `traceparent` with the sampled flag. Boot's default sampler is `parent-based-trace-id-ratio` ([Tracing](https://docs.spring.io/spring-boot/reference/actuator/tracing.html)), so the server should join that trace, and the default log correlation carries the id. This needs no application code.

Proved on Boot 4.1.1 and Java 25: the id reaches the JSON log, stack traces included, and no filter is needed. With `spring.task.execution.propagate-context=true` it also reaches `@Async` work. `management.tracing.export.enabled=false` breaks joining, so the profile must not set it.

Browser journeys set the header on requests to the app's own origin only, so third-party widgets receive nothing.

### 2. A `verify` profile

One shipped asset, `application-verify.properties`, used only for local runs:

```properties
logging.file.name=${VERIFY_DIR:target/verify}/app.jsonl
logging.structured.format.file=logstash
management.tracing.sampling.probability=1
management.endpoints.web.exposure.include=health,info,metrics,loggers
spring.task.execution.propagate-context=true
logging.level.org.springframework.web.servlet.DispatcherServlet=DEBUG
management.otlp.metrics.export.enabled=false
```

- `logging.file.name` and `logging.structured.format.file` are documented, and console and file formats are separate ([Logging](https://docs.spring.io/spring-boot/reference/features/logging.html)).
- Sampling at 1 is safe here and only here. A journey with a 10% sample loses 9 traces in 10, so the default of 0.1 would make the loop flaky. Addy's rule applies: a flaky signal teaches agents to retry.
- `loggers` lets the agent raise one package to DEBUG for one run, rather than restarting.
- P1's config gate must treat `verify` as a non-shipped profile, like `local`.

### 3. Two tiers of capture

| Tier | Needs | Gives | When |
| --- | --- | --- | --- |
| **1. File** | Nothing | Logs per trace, exceptions, Actuator metrics | Default. Every project, every worktree. |
| **2. Stack** | Docker | Spans, timing, queries, PromQL | When a change touches performance, cross-service calls or async work. |

Tier 2 is `grafana/otel-lgtm` in `compose.yml`. Boot's Docker Compose and Testcontainers support wire OTLP logging, metrics and tracing connections to it automatically ([Dev services](https://docs.spring.io/spring-boot/reference/features/dev-services.html), [Testcontainers](https://docs.spring.io/spring-boot/reference/testing/testcontainers.html)). The image is intended for development and testing, and data is lost with the container unless `/data` is mounted ([docker-otel-lgtm](https://github.com/grafana/docker-otel-lgtm)).

Three traps found in the docs:

- **Logs stay in the file, even at Tier 2.** Boot does not bridge logs to its `SdkLoggerProvider` out of the box ([Observability](https://docs.spring.io/spring-boot/reference/actuator/observability.html)). Loki would stay empty without a third-party appender. Skip it: the file already works.
- **Query counts need extra instrumentation.** JDBC is not built into Boot's observability and needs the Datasource Micrometer starter (same page). Without it, a trace cannot show an N+1. Add it to the verify path only, and check the scope in Phase 3.
- **Worktrees share ports.** Tier 1 isolates itself, since the file lives in the checkout. Tier 2 shares one stack, so filter by `service.name` and the `commit` key-value.

### 4. The `telemetry` CLI

This is the lever. Shipped by the harness into the project, called by the verification skill. Written in Python 3, standard library only.

```
telemetry doctor                     # built: app up, a canary request reached the log
telemetry mark                       # built: start a run
telemetry new-trace                  # built: id and header for a journey
telemetry call GET /api/orders       # built: sends traceparent, reports status and log lines
telemetry logs <traceId> --level WARN  # built
telemetry errors                     # built: WARN and ERROR since the mark, ends with the summary line
telemetry trace <traceId> --summary  # Tier 2: spans, slowest, error spans, query count
telemetry metric <name> --tag k=v    # Tier 2
telemetry budget <traceId> --max-ms 500 --max-queries 20  # Tier 2
```

Design rules, from Lauren's list and the existing Tool design section:

- JSON output. Quiet on success, specific on failure, and a failure says what to do next: not "no logs found" but "no line with this trace id: the app is on commit X, run doctor".
- Exit codes extend the journeys' set: 0 pass, 1 fail, and 4 for no telemetry, because **no data is never a pass**. Empty results must not read as zero errors.
- `doctor` must prove the pipe works by sending a canary. Otherwise a logging misconfiguration reports clean forever.
- `errors` compares against a baseline from the same run, because startup WARNs are noise. Without this, agents learn to ignore it.
- `budget` turns an observation into an invariant. It takes numbers from the feature map, not from the agent's own run.
- Flags, not environment prefixes, per `browser-verification.md`.

Tier 2 reads Tempo's `/api/traces/<id>` ([Tempo API](https://grafana.com/docs/tempo/latest/api_docs/)) and Prometheus on port 9090. Agents never need Grafana's UI.

### 5. Telemetry in the feature map

The generated feature map gets one more H2 per feature:

```markdown
## Healthy signals

- Observation: `orders.place`, status ok
- Budget: under 500 ms, at most 12 queries
- Allowed WARN: none
- Side effects: `module.events.published` for `OrderPlaced`
```

This is the "materialized memory" for runtime behaviour: what normal looks like, written before the change. `/maintain-verification-skill` already drives every feature, so it can refresh these. Spring Modulith's `module.events.published` counter and module spans fit harness projects directly ([Modulith](https://docs.spring.io/spring-modulith/reference/production-ready.html)).

### 6. Evidence and fail-first

Add to the report in `browser-verification.md`:

| Journey | Result | Failed first | Trace | New errors | Budget |
| --- | --- | --- | --- | --- | --- |

- A journey that passes with new ERROR lines in its trace is a **FAIL**. This is the rule that catches what the page hides.
- Fail-first now covers telemetry too: `budget` must fail on the old code when the change is a performance fix.
- Evidence stays outside the repository, and may contain personal data from local fixtures.

### 7. Tests in `./mvnw verify`

For signals that must not regress, cheaper than any run:

- `TestObservationRegistry` for custom observations ([Micrometer](https://docs.micrometer.io/micrometer/reference/observation/testing.html)).
- Trap for `writing-springboot-tests`: in `@SpringBootTest`, reporting tracing components and non-memory meter registries are not auto-configured. Use `@AutoConfigureTracing` or `@AutoConfigureMetrics`. On a sliced test, the Tracer is a no-op ([Boot testing](https://docs.spring.io/spring-boot/reference/testing/spring-boot-applications.html)). A span assertion without this checks nothing.

### 8. Getting agents to use it

`browser-verification.md` already has the data: an `AGENTS.md` line alone caught 0/3, and asking for proof in the task caught 3/3. So guidance is not enough.

- **Task and PR contract:** a Proof section in the PR template and `REVIEW.md`, with trace id, report line and failed-first file. A reviewer rejects a behaviour change without one.
- **Stop hook, untested:** extend `verify-on-stop.sh` to block when `src/main` changed and no report is newer than the last source edit. It costs seconds, and it can only check that proof exists, not that it is good. Trial it before shipping, since a hook that blocks wrongly is worse than none.

## What this changes in the research note

- **P9 reverses, on by default.** The note said not to require actuator. This loop needs actuator and tracing. The installer adds the pack unless `--no-observability` is passed. The CLI isn't part of it: it stays in the trial fixture.
- **P2 narrows.** Ban a hand-built `OpenTelemetry` bean only. Do not ban `io.opentelemetry.sdk..` outright: a project may need a custom `SpanExporter`.
- **P1 skip list** gains `verify`.
- **P14 (Modulith insight)** moves up: it feeds the feature map's signals.

## Build order

Each phase must work before the next starts.

1. **Prove the pipe.** On one real app: `traceparent` in, id in the JSON log. Decide header or filter. Write `references/telemetry-verification.md`. No tooling yet.
2. **Tier 1.** `application-verify.properties` and `telemetry doctor|call|logs|errors|report`, which were trialled in a fixture and not shipped.
3. **Trial** (below). Stop here if it shows no gain.
4. **Evidence and contract.** Report columns, feature-map section, PR Proof section. Then the Stop hook trial.
5. **Tier 2.** `compose.yml`, `trace`, `budget`, JDBC instrumentation.
6. **Gates.** P1 to P3, which are independent and can ship earlier.

## Trial

Same shape as the browser trial: planted bugs that unit tests miss, 3 Sonnet sessions per setup, kept cheap.

| Setup | Expected question |
| --- | --- |
| Journeys only | Baseline: does the agent notice? |
| Journeys and Tier 1 CLI | Does log access catch the bugs? |
| Same, plus Proof required | Does it get used? |

Planted bugs, all returning a correct-looking 200:

1. An exception swallowed in a fallback.
2. An event listener that fails after the response.
3. A retry loop against a failing dependency.
4. An N+1 (Tier 2 only).

**Done when:** a telemetry setup catches at least 2 of bugs 1 to 3 more often than the baseline, with no increase in false reports. Numbers decide whether Phases 4 and 5 are worth building.

## Risks

- **Noise.** A chatty app makes `errors` useless. Baseline comparison and grouping are required, not optional.
- **Cost.** Output kept small by default, or the loop burns tokens. Addy: unwanted output costs attention on every turn.
- **Data.** JSON logs at DEBUG can hold personal data. The verify profile is local, on fixtures only.
- **Same author, same mistake.** An agent can write a wrong budget to match wrong code. Budgets belong in the feature map before the change, and failed-first still applies.

## Open decisions

1. **Tracing library in the opt-in.** Default: `spring-boot-starter-opentelemetry`. OpenTelemetry names its Java agent as the general default ([OpenTelemetry](https://opentelemetry.io/docs/zero-code/java/spring-boot-starter/)), but the agent cannot be configured from `application.properties`, and this design relies on that.
2. **Stop hook.** Default: trial it, ship only if it does not block wrongly.
