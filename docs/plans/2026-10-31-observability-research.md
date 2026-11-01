# Observability: what the team harness can and cannot gate

**Status:** Research only. Nothing in the harness or the skills changed. Not committed.

**Superseded in focus by:** `2026-10-31-agent-verification-observability.md`, which treats telemetry as the agent's verification loop. This note remains the reference for Boot facts and config gates. P1, P2 and P9 changed there.

**Goal:** Decide which observability mistakes `spring-boot-team-harness` can catch mechanically, which need review, and which do not belong in it. Covers Spring Boot 4.1 and, where the service runs on ECS, AWS ECS.

**Sources:** Primary docs only (docs.spring.io, docs.micrometer.io, opentelemetry.io, docs.aws.amazon.com, docs.oracle.com). Each claim is cited inline. Claims without a source are marked UNVERIFIED. The Boot target is 4.1.x: `creating-springboot-projects/references/spring-boot-4-features.md` pins `4.1.0`, and the migration notes say `4.1.1`. The Boot reference pages fetched were the 4.1.2 docs.

---

## Summary

Ranked by value per unit of harness cost.

1. **Gate: actuator exposure and health-detail values in shipped config.** `ConfigurationKeysTests` checks key names only. It never checks values. Boot exposes only `health` over HTTP by default, but `exposure.include=*` and `show-details=always` are the usual leaks. A value check is deterministic, reads files the test already reads, and costs close to nothing.
2. **Gate: no hand-built OpenTelemetry SDK bean in main code.** The Boot docs say a custom `OpenTelemetry` bean disables Boot's OpenTelemetry auto-configuration and may break built-in observability. This is a mechanical ArchUnit check with a low false-positive rate.
3. **Review rule (REVIEW.md): sampling, log format and shutdown values.** `management.tracing.sampling.probability` defaults to 0.1. Setting it to 1 is a cost decision, so a reviewer should judge it, not a test. Same for `server.shutdown=immediate` and the structured log format. Each is a value a human should choose.
4. **Guidance (AGENTS.md and writing-springboot-tests): metric cardinality and observation tests.** A gate cannot tell a user ID in a meter tag from a bounded enum. Micrometer's introduction defines the two cardinality kinds (verified); that only low-cardinality values become meter tags is from a search excerpt (UNVERIFIED on the page). The guidance should say so, and endpoints that add observations should assert them with `TestObservationRegistry`.
5. **Do not add: ECS task-definition checks to this harness.** `stopTimeout`, health-check `startPeriod`, the log driver mode and circuit-breaker settings live in ECS task definitions, not in the Maven project. The harness sees them only if the team keeps that IaC in the repo. If it does, add a CI check then. Otherwise leave them to `aws-infrastructure-skills`.

Verdict counts: 4 gates (P1-P3, P10), 4 review rules (P4, P7, P8, P15), 4 guidance items (P5, P6, P12, P14), 3 do-not-add (P9, P11, P13).

---

## Current state

### What the harness does

| Item | Where | Observability effect |
| --- | --- | --- |
| Key-name check for `spring.`, `management.`, `server.`, `logging.` | `assets/tests/ConfigurationKeysTests.java:28-33` (`CHECKED_PREFIXES`), test `everyBootKeyIsDefinedAndCurrent` | Fails on a key that no classpath jar defines, or that is deprecated. Management keys are checked against actuator's metadata, so a `management.*` key with no actuator on the classpath fails as "defined by no dependency". This is the only observability key check. |
| Config-key row in the gate table | `assets/project/AGENTS.md:15`, `SKILL.md:51` | Same check, described to the agent. |
| HTTP clients must come from the injected builder | `assets/tests/CodeRulesTests.java:244-252` (`httpClientsComeFromTheBuilder`) | Its message says a client built with `RestClient.create()` "skips Boot's metrics and tracing". This is the one harness rule that is observability-motivated. |
| `@Async` and `@Scheduled` must be switched on | `CodeRulesTests.java:224-232` (`asyncAndSchedulingAreSwitchedOn`) | Not observability as such, but a missing `@EnableAsync` loses the executor's context setup. |
| No `System.out` or `System.err` | `CodeRulesTests.java:345-351` (`codeLogsInsteadOfPrinting`) | Message: output "skips log levels and structured logging". This is the only logging rule. |
| Starter in `test` scope fails | `assets/tests/BuildSetupTests.java`, `bootDependenciesAreNotTestOnly` | Covers `spring-boot-starter-actuator` or `spring-boot-starter-opentelemetry` added only for tests. |
| Boot target version | `scripts/apply_harness.py:333` (`BOOT_VERSION` from the parent POM, default `4`) | No version pin of its own. |

### What the harness does not do

- No rule reads the value of any `management.*` or `logging.*` key. `management.endpoints.web.exposure.include=*` passes.
- No rule checks that `spring-boot-starter-actuator` is present. A project without it has no health or metrics endpoint, and no gate notices. The harness has no opinion on this (see P9).
- `assets/pom/plugins.xml`, `properties.xml`, `dependencies.xml` and `managed-dependencies.xml` add no observability dependency and no observability property. The harness does not add actuator, Micrometer, or the OpenTelemetry starter.
- `assets/project/REVIEW.md` has no observability line. Its "Failures" list is empty, and its "Risk" list names security, migrations and CI, not telemetry.
- `assets/project/AGENTS.md` has no observability guidance. The only mention is the config-key row.
- `scripts/apply_harness.py` never mentions actuator, metrics or tracing.
- Nothing about ECS, container health, shutdown timing or log delivery exists in the harness.

### Sibling skills and references

| File | Line(s) | What it says | Gap or issue |
| --- | --- | --- | --- |
| `code-reviewer/references/spring-boot-4-patterns.md` | 107-109 | Expose `health,metrics,prometheus`; prometheus export via `management.prometheus.metrics.export.enabled`; sample at `management.tracing.sampling.probability`; use `spring-boot-starter-opentelemetry` | The prometheus export key is UNVERIFIED (not on the pages fetched). The sampling key is verified. The OTel starter is verified. |
| `code-reviewer/references/security-checklist.md` | 35-36 | `exposure.include=*` and `show-details=always` are flagged | Correct per docs (default `never`). The harness should enforce these; this file only advises. |
| `code-reviewer/references/security-checklist.md` | 95-97 | A09: log auth events; forged log lines via CR/LF | Advice only. |
| `code-reviewer/references/jpa-performance.md` | 157 | Watch `hikaricp.connections.pending` and `usage` | Metric names are not in the fetched Boot pages. The Boot page says Hikari metrics use the `hikaricp` prefix, tagged by pool name (verified). The exact `.connections.pending` names are UNVERIFIED. |
| `creating-springboot-projects/assets/pom-additions.xml` | 158-159 | Lists `spring-boot-starter-opentelemetry` as an optional feature | Consistent with the docs. |
| `creating-springboot-projects/references/spring-boot-4-features.md` | 210-218 | `MetricsRetryListener` with empty bodies | Sample code with no metric is written. |
| `creating-springboot-projects/assets/testcontainers-test.java` | 43-45 | Health endpoint test on `/actuator/health` | Good: it proves the endpoint answers, but only with the default exposure. |
| `springboot-migration/references/spring-boot-4-migration.md` | 153 | Liveness and readiness probes on by default | Consistent with the endpoints docs (verified). |
| `springboot-migration/references/spring-modulith-2-migration.md` | 116 | `/actuator/modulith` needs `spring-modulith-actuator` | Not fetched. UNVERIFIED. |
| `spring-boot-team-harness/references/browser-verification.md` | 36-39 | `/actuator/info` exposure is local-profile only | Correct: the harness already applies the "expose only in local" pattern here. |

Note on `code-reviewer/references/spring-boot-4-patterns.md:107`: it recommends `health,metrics,prometheus` as a flag fix. The docs say `metrics` and `prometheus` are not exposed by default, which is consistent, but the line implies they are safe to expose. Expose them only behind a separate management port or auth. The docs describe `management.server.port` as the way to put actuator on another port (verified).

---

## Spring Boot observability best practices

Each point is cited to the page that owns it. Snippets are checked against those pages.

### Actuator exposure and security

- Only `health` is exposed over HTTP by default. Source: [Actuator endpoints](https://docs.spring.io/spring-boot/reference/actuator/endpoints.html). "By default, only the health endpoint is exposed over HTTP and JMX."
- `management.endpoints.web.exposure.include` lists what is exposed. `exclude` wins over `include`. `*` selects all. Same source.
- `management.endpoint.health.show-details` defaults to `never`. Accepts `never`, `when-authorized`, `always`. Same source.
- `management.server.port` moves actuator to another port. Same source. Use it as a private port for metrics and admin endpoints, but keep the probes on the main port (next section).

```properties
management.endpoints.web.exposure.include=health,info,prometheus
management.endpoint.health.probes.add-additional-paths=true
management.endpoint.health.show-details=when-authorized
management.server.port=8081
```

Checked: each key appears on the endpoints page. `prometheus` as an exposure ID is consistent with the metrics page, which says the endpoint "is not available and must be exposed" ([Metrics](https://docs.spring.io/spring-boot/reference/actuator/metrics.html)).

### Health groups and probes

- Liveness and readiness health groups exist at `/actuator/health/liveness` and `/actuator/health/readiness`. They are enabled automatically. Disable with `management.endpoint.health.probes.enabled`. Source: [Actuator endpoints](https://docs.spring.io/spring-boot/reference/actuator/endpoints.html), quoted: "These health groups are automatically enabled."
- "By default, Spring Boot does not add other health indicators to these groups." Same source. Add a dependency's indicator to a group deliberately, or a database outage will restart the container.
- `management.endpoint.health.probes.add-additional-paths=true` serves the groups at `/livez` and `/readyz` on the main server port. Same source.
- With a separate management port, "a probe check could be successful even if the main application does not work properly (for example, it cannot accept new connections). For this reason, it is a good idea to make the `liveness` and `readiness` health groups available on the main server port." Source: [Actuator endpoints](https://docs.spring.io/spring-boot/reference/actuator/endpoints.html).
- Liveness "should not depend on health checks for external systems", because an external outage can restart every instance and cascade. For readiness, Boot leaves the choice to the developer. Same source.

### Micrometer Observation API

- Metrics and traces come from Micrometer Observation. Inject `ObservationRegistry` to create observations. Source: [Observability](https://docs.spring.io/spring-boot/reference/actuator/observability.html).
- Common tags on every observation: `management.observations.key-values.<name>=<value>`. Same source. Example: `management.observations.key-values.stack=prod`.
- Annotation support (`@Observed`, `@Timed`, `@Counted`, `@MeterTag`, `@NewSpan`) is on with `management.observations.annotations.enabled=true`. It needs AspectJ: "requires `org.aspectj:aspectjweaver`, which ... is part of `spring-boot-starter-aspectj`" ([Observability](https://docs.spring.io/spring-boot/reference/actuator/observability.html)).
- `ObservationPredicate` beans filter observations programmatically. Same source.
- HTTP server metrics are named `http.server.requests` by default. Renamed with `management.observations.http.server.requests.name`. Source: [Metrics](https://docs.spring.io/spring-boot/reference/actuator/metrics.html).

### Metric tags and cardinality

- "Low cardinality means that a key value will have a bounded number of possible values." "High cardinality means that a pair will have an unbounded number of possible values." Source: [Micrometer Observation introduction](https://docs.micrometer.io/micrometer/reference/observation/introduction.html).
- Micrometer's search excerpt says only low-cardinality key values become meter tags, and high-cardinality values go to traces and logs. The fetched introduction page does not say this, so the precise claim is UNVERIFIED on the primary page. Confirm before quoting it.
- OpenTelemetry metrics SDK: default cardinality limit is 2000 per metric when none is configured. Past it, measurements go to an overflow attribute `otel.metric.overflow=true`. Source: [OpenTelemetry metrics SDK specification](https://opentelemetry.io/docs/specs/otel/metrics/sdk/). Whether the Boot OTLP path uses this default is UNVERIFIED.
- Percentile histograms: `management.metrics.distribution.percentiles-histogram`, `management.metrics.distribution.percentiles`, `management.metrics.distribution.slo`. Source: [Metrics](https://docs.spring.io/spring-boot/reference/actuator/metrics.html). `percentiles-histogram` publishes "a histogram suitable for computing aggregable (across dimension) percentile approximations", which matters on ECS with several tasks. `percentiles` publishes values computed in the application, which cannot be aggregated across tasks.
- The Boot 4.1 metrics page documents no `max-uri-tags` property. Its hooks are a `ServerRequestObservationConvention` bean and any `MeterFilter` bean, which Boot binds to the registry ([Metrics](https://docs.spring.io/spring-boot/reference/actuator/metrics.html)). `MeterFilter.maximumAllowableTags` is the Micrometer API for a cap. It is not on the Boot page, so check it against the Micrometer docs before use.
- Tomcat metrics need `server.tomcat.mbeanregistry.enabled=true`. Virtual-thread metrics need `io.micrometer:micrometer-java21` on the classpath. Source: [Metrics](https://docs.spring.io/spring-boot/reference/actuator/metrics.html).

### Tracing and sampling

- Default sampling is 10%: "By default, Spring Boot samples only 10% of requests to prevent overwhelming the trace backend." Set with `management.tracing.sampling.probability`. Source: [Tracing](https://docs.spring.io/spring-boot/reference/actuator/tracing.html).
- OpenTelemetry sampler default: `parent-based-trace-id-ratio`. Set with `management.opentelemetry.tracing.sampler`. Same source.
- OTLP tracing needs `org.springframework.boot:spring-boot-starter-opentelemetry`. Same source. This is the Boot 4 modular starter.
- Span limits: `management.opentelemetry.tracing.limits.max-attributes`, `management.opentelemetry.tracing.limits.max-attribute-value-length`. Same source.
- Exemplars: only sampled traces by default. `management.tracing.exemplars.include`. The value `all` is not supported with Prometheus. Source: [Metrics](https://docs.spring.io/spring-boot/reference/actuator/metrics.html).
- Boot 4 splits the keys. Sampling probability is `management.tracing.sampling.probability`. The OpenTelemetry sampler and OTLP export are `management.opentelemetry.tracing.*`. OTLP metrics are `management.otlp.metrics.export.url`. Source: [Observability](https://docs.spring.io/spring-boot/reference/actuator/observability.html). Code written for 3.x keys will fail the key check, which is the right outcome.

```properties
management.tracing.sampling.probability=0.1
management.opentelemetry.tracing.export.otlp.endpoint=http://collector:4318/v1/traces
management.observations.key-values.stack=prod
```

Checked: the first key and default are on the tracing page. The second is the documented property name, but the fetched page did not show whether the explicit property expects the `/v1/traces` suffix. Prefer the environment variable below, which the docs describe: `OTEL_EXPORTER_OTLP_ENDPOINT=http://collector:4318` yields `/v1/traces` for traces ([Observability](https://docs.spring.io/spring-boot/reference/actuator/observability.html)).

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://collector:4318
OTEL_TRACES_SAMPLER_ARG=0.1
```

Checked: the env-to-property mapping table is on the observability page. `OTEL_TRACES_SAMPLER_ARG` maps to `management.tracing.sampling.probability`.

### Trace-context propagation

- Use the auto-configured `RestClient.Builder`, `RestTemplateBuilder` or `WebClient.Builder`. "If you create the `RestTemplate`, the `RestClient` or the `WebClient` without using the auto-configured builders, automatic trace propagation won't work!" Source: [Tracing](https://docs.spring.io/spring-boot/reference/actuator/tracing.html). The harness's `httpClientsComeFromTheBuilder` rule enforces the same thing (CodeRulesTests.java:244).
- `@Async`: `spring.task.execution.propagate-context` for the auto-configured executor. Custom executors need a `ContextPropagatingTaskDecorator` bean. Source: [Observability](https://docs.spring.io/spring-boot/reference/actuator/observability.html).
- Reactor: `spring.reactor.context-propagation=auto`. Same source.
- Trace context across virtual threads and `@Scheduled`: UNVERIFIED. Not in the fetched pages.
- JDBC and R2DBC: R2DBC is built in with `io.r2dbc:r2dbc-proxy`. JDBC is not built in and needs the Datasource Micrometer project's starter. Source: [Observability](https://docs.spring.io/spring-boot/reference/actuator/observability.html).
- Kafka: observation is off by default. `observationEnabled` must be set on both `KafkaTemplate` and `ContainerProperties`, so a trace stops at the topic until it is. Batch-listener behaviour differs by Spring Kafka version. Source: [Spring Kafka monitoring](https://docs.spring.io/spring-kafka/reference/kafka/micrometer.html), read from search excerpts. The Boot key `spring.kafka.listener.observation-enabled` is inferred from `KafkaProperties.Listener.setObservationEnabled`, so the key itself is UNVERIFIED.
- Baggage: W3C propagates automatically. B3 does not. Use `management.tracing.baggage.remote-fields`. Copy to MDC with `management.tracing.baggage.correlation.fields`. Source: [Tracing](https://docs.spring.io/spring-boot/reference/actuator/tracing.html).

### Logging, correlation and structured output

- Structured logs: `logging.structured.format.console` and `logging.structured.format.file`. Format IDs: `ecs`, `gelf`, `logstash`. Source: [Logging](https://docs.spring.io/spring-boot/reference/features/logging.html).
- Every format adds the MDC key-values. The SLF4J fluent API adds them with `addKeyValue`. Same source.
- Default correlation ID is `traceId-spanId` from MDC, from Micrometer Tracing. Custom: `logging.pattern.correlation` with `logging.include-application-name=false`. Source: [Tracing](https://docs.spring.io/spring-boot/reference/actuator/tracing.html).
- The Boot logging page does not say which version introduced structured logging. UNVERIFIED.

```properties
logging.structured.format.console=ecs
```

Checked: key and `ecs` ID are on the logging page.

### Database and connection pool

- DataSource metrics use the `jdbc.connections` prefix. Hikari metrics use the `hikaricp` prefix, tagged by pool name. Pool name is `spring.datasource.name`. Source: [Metrics](https://docs.spring.io/spring-boot/reference/actuator/metrics.html).

### Shutdown

- Graceful shutdown is on by default for Tomcat, Jetty and Reactor Netty. Disable with `server.shutdown=immediate`. Source: [Graceful shutdown](https://docs.spring.io/spring-boot/reference/web/graceful-shutdown.html).
- Timeout per phase: `spring.lifecycle.timeout-per-shutdown-phase`. Example in the docs is `20s`. The default is not stated on the page. UNVERIFIED default. Same source.
- It runs in the earliest `SmartLifecycle` phase: "existing requests will be allowed to complete but no new requests will be permitted." Same source.

```properties
server.shutdown=graceful
spring.lifecycle.timeout-per-shutdown-phase=20s
```

### Testing observability

- `TestObservationRegistry` for unit tests: "To unit-test this code, you can use the `TestObservationRegistry` class". It registers an `ObservationValidator` automatically. Source: [Micrometer testing](https://docs.micrometer.io/micrometer/reference/observation/testing.html).
- Assertions include `hasObservationWithNameEqualTo`, `hasLowCardinalityKeyValue`, `hasHighCardinalityKeyValue`, `hasBeenStopped`. Same source.

### Not verified

- Spring Modulith, now verified ([Production-ready features](https://docs.spring.io/spring-modulith/reference/production-ready.html), 2.1.1): `spring-modulith-starter-insight` (runtime scope) adds actuator and observability support. API components of a module get spans tagged `module.name`, `module.identifier`, `module.method` and `module.invocation-type`. `GET /actuator/modulith` returns the module structure. `module.events.published` counts event publications. No Modulith health indicator is documented.
- Prometheus: a `micrometer-registry-{system}` runtime dependency is enough, so `io.micrometer:micrometer-registry-prometheus`, version managed by Boot, plus exposing `prometheus` ([Metrics](https://docs.spring.io/spring-boot/reference/actuator/metrics.html)). `management.prometheus.metrics.export.enabled` is still not on the fetched page: UNVERIFIED.
- `spring-boot-starter-actuator` Boot 4 artifact details: UNVERIFIED beyond its presence in the harness.
- Which Boot version introduced structured logging: UNVERIFIED.

---

## AWS ECS

Kept outside this repository, with the team's ECS notes. The harness is Maven-only, and task definitions are not part of it.

---

## Proposals for the harness

Each entry gives: the mechanism, what it catches, how to test it without a container, false-positive risk, cost in `./mvnw verify`, and the verdict.

Cost figures are not measured. "Negligible" means it reads files the test already reads or adds one ArchUnit rule to a suite that already imports every main class.

### P1. Actuator exposure and detail values in shipped config

- **Mechanism:** extend `ConfigurationKeysTests` with a value check, not only a name check. Scan `application.properties`, `application.yml` and `application-*.properties|yml`, skipping profiles named `local`, `dev` or `test`. Flag `management.endpoints.web.exposure.include` values containing `*`, `env`, `beans`, `heapdump`, `threaddump`, `loggers` or `shutdown`, and `management.endpoint.health.show-details=always`. Assumption: when `management.server.port` is set to a port other than `server.port`, the actuator is on a separate port, and the rule permits any exposure there. Whether that port is private is a network fact the file cannot prove, so the message must say so and the review rule (P4 wording) covers the rest.
- **Catches:** `/actuator/env`, `/actuator/heapdump` or `show-details=always` reachable on the public port. Docs: default is `never` and only `health` exposed (verified).
- **Deterministic test:** unit tests with fixture properties strings, the same way `ConfigurationKeysTests` already reads files. Good and bad fixtures. No container.
- **False-positive risk:** medium. A team may expose `info,metrics` on the public port behind an ingress rule, or use `*` on a private port. Those cases need the allow rule above, or a documented exception. Keep the banned list short.
- **Cost:** negligible.
- **Verdict: gate.** Put the message in the existing key-check failure style, and name the Boot default.

### P2. No hand-built OpenTelemetry SDK bean

- **Mechanism:** ArchUnit rule in `CodeRulesTests`: no `@Bean` method whose return type is `io.opentelemetry.api.OpenTelemetry`, and no main-code class depends on `io.opentelemetry.sdk..`. Message: use `spring-boot-starter-opentelemetry` and the `management.opentelemetry.*` properties.
- **Catches:** the Boot docs say that supplying your own `OpenTelemetry` bean "disables Boot's OpenTelemetry auto-configuration and may break built-in observability" ([Observability](https://docs.spring.io/spring-boot/reference/actuator/observability.html)). The result is silent loss of traces.
- **Deterministic test:** the rule runs on the compiled main classes, the same as the other rules. Fixture: none needed for the harness itself, but the rule's behaviour needs a unit test with a fixture class, which the harness does not do today (UNVERIFIED that it is practical in `CodeRulesTests`).
- **False-positive risk:** low to medium. Teams that deliberately use the SDK extension (documented as possible) would hit it. The docs describe that case as an option, so the rule needs a documented escape: remove the rule by hand, which the guard hook already forces.
- **Cost:** negligible.
- **Verdict: gate.**

### P3. Printing stack traces

- **Mechanism:** add `Throwable.printStackTrace()` to the forbidden calls in `codeLogsInsteadOfPrinting`.
- **Catches:** `e.printStackTrace()` writes to stderr, skipping log levels, MDC and the structured fields that correlate the error to the trace.
- **Deterministic test:** same as the existing rule; it uses ArchUnit's call analysis.
- **False-positive risk:** very low.
- **Cost:** negligible.
- **Verdict: gate.** Small, obvious, same rule.

### P4. Sampling probability and shutdown mode in shipped config

- **Mechanism:** none in the harness. Write it as a line in REVIEW.md "Risk" and in the code-reviewer checklist.
- **Catches:** `management.tracing.sampling.probability=1` (docs: "switches it to 100%") in production config, which can exhaust the trace backend or the bill. `server.shutdown=immediate` (drops in-flight requests during deploys).
- **Why not a gate:** the right values depend on traffic and cost, which only a human knows. A gate would force a fixed number onto every team.
- **False-positive risk:** high if gated.
- **Cost:** none.
- **Verdict: review rule.**

### P5. Metric cardinality

- **Mechanism:** none that a gate can check reliably. ArchUnit can see the call `lowCardinalityKeyValue(...)` but not the value's source. Use guidance in AGENTS.md and the writing-springboot-tests skill: "Put IDs, emails and free text in high-cardinality key values, never in low-cardinality ones or meter tags."
- **Catches:** a user ID or order ID as a metric tag, which creates one series per value. The OTel default limit is 2000 per metric, after which the SDK folds measurements into `otel.metric.overflow=true` (verified). Whether Boot's Micrometer OTLP path uses this limit is UNVERIFIED.
- **Deterministic test:** none, as a gate. A test could assert that a specific endpoint's observation has no high-cardinality tags in the meter, using `TestObservationRegistry` (verified API). That is a per-endpoint test, so it belongs in the writing-springboot-tests skill.
- **False-positive risk:** a gate would be high. Guidance has none.
- **Cost:** none.
- **Verdict: guidance.** Not a gate.

### P6. Observation tests for endpoints that add observations

- **Mechanism:** guidance in `writing-springboot-tests`: when an endpoint or service adds an observation or a metric, assert it with `TestObservationRegistry` (`hasObservationWithNameEqualTo`, `hasLowCardinalityKeyValue`).
- **Catches:** a new endpoint with no observation, or a renamed one that breaks dashboards.
- **Why not a gate:** the harness cannot tell which code needs an observation. It can require a test only where a rule says so, and no rule says so.
- **False-positive risk:** high as a gate.
- **Cost:** none.
- **Verdict: guidance.**

### P7. Raw thread pools and `new Thread` in main code

- **Mechanism:** ArchUnit rule: no `new Thread(...)` and no `Executors.new*` in main code, except inside a class that wraps the executor with context propagation.
- **Catches:** the executor loses trace and MDC context, and skips Boot's executor configuration. Boot documents the opt-in for `@Async` only (verified): `spring.task.execution.propagate-context`.
- **Deterministic test:** ArchUnit call analysis. Fixture-based test needed.
- **False-positive risk:** medium. Wrapped executors are valid, and virtual-thread executors need their own context handling (UNVERIFIED). A rule on this would be a standing exception list.
- **Cost:** negligible.
- **Verdict: review rule.** The harness already gates `@Async` enablement (CodeRulesTests.java:224). That covers the common case.

### P8. Structured log format in shipped config

- **Mechanism:** review rule only. A gate would fail teams whose log shipper parses text.
- **Catches:** logs that CloudWatch Logs Insights or another backend cannot query by field. `logging.structured.format.console=ecs` is the documented switch (verified).
- **Verdict: review rule.**

### P9. Require actuator in every web app

- **Mechanism:** `BuildSetupTests` check for `spring-boot-starter-actuator` in a web app.
- **Catches:** an app with no health or metrics endpoint, which ECS and ALB then cannot check.
- **Why not:** some services do not need actuator, and a required dependency is a team decision. The key check already fails when a `management.*` key is present without actuator, which covers the inconsistent case.
- **False-positive risk:** medium.
- **Verdict: do not add.** Already covered for the inconsistent case by `ConfigurationKeysTests`.

### P10. `prometheus` exposed without a registry dependency

- **Mechanism:** `BuildSetupTests`: fail if `management.endpoints.web.exposure.include` lists `prometheus` and the classpath has no Prometheus registry.
- **Catches:** the endpoint silently missing, so the scrape gets 404.
- **Why now:** the registry is verified as `io.micrometer:micrometer-registry-prometheus` (see the Spring Boot section). The check is a key-value read plus a dependency check, in the shape of `BuildSetupTests`.
- **False-positive risk:** low.
- **Verdict: gate, low priority.** Build it once a team actually scrapes Prometheus.

### P11. ECS task-definition checks

- **Mechanism:** a CI step that validates `stopTimeout` against `spring.lifecycle.timeout-per-shutdown-phase`, `startPeriod` range, `logConfiguration.options.mode`, and the deployment circuit breaker.
- **Catches:** a stopTimeout shorter than the Spring shutdown budget (SIGKILL cuts off in-flight requests); a blocking log mode that can stall the app; no circuit breaker on a rolling deploy.
- **Deterministic test:** a parser over the task-definition JSON or Terraform. Requires that file to be in the repo.
- **False-positive risk:** low once the file is in the repo.
- **Cost:** a CI step, not `./mvnw verify`.
- **Verdict: do not add to this harness unless the ECS IaC lives in the same repo.** The harness is Maven-only (SKILL.md Limits section). If the IaC is elsewhere, put the check in the `aws-infrastructure-skills` pipeline. If the IaC is in this repo, add a CI step as a follow-up, after choosing the rule with the user.

### P12. Health probe groups and the ALB path

- **Mechanism:** none. Documentation only.
- **Why not a gate:** the ALB path lives in deployment config, which the repo may not hold.
- **Verdict: guidance** in the project's runbook, not in the harness. Say to keep probes on the main port, per the Boot docs.

### P13. Alarms, log retention and cost controls

- **Mechanism:** none in the harness.
- **Why not:** these are AWS account settings and dashboards. The harness cannot see them, and they belong in infrastructure.
- **Verdict: do not add.**

### P14. Modulith insight starter

- **Mechanism:** a line in AGENTS.md for projects with Modulith modules: add `spring-modulith-starter-insight` once the team has a tracing backend.
- **Gives:** per-module spans and event counters with no code. This is the one observability feature that fits the harness's module model.
- **Why not a gate:** spans cost money and need a backend.
- **Verdict: guidance.**

### P15. Kafka observation switched on

- **Mechanism:** a REVIEW.md line: a change adding `@KafkaListener` or `KafkaTemplate` must enable observation on both sides.
- **Catches:** traces that stop at the topic, because both flags default to false.
- **Why not a gate:** a template can be configured in code or properties, and the Boot key is unverified. Revisit as a value check once the key is confirmed.
- **Verdict: review rule.**

---

## Open decisions for the user

1. **Does ECS run from this repo?** If the task definitions, Terraform or CDK live here, P11 becomes a CI gate. If not, P11 belongs in `aws-infrastructure-skills`.
2. **Which backend?** CloudWatch with Application Signals and X-Ray OTLP, Amazon Managed Prometheus with Grafana, a self-hosted LGTM stack, or a vendor. The export properties differ, and the harness should not guess.
3. **Structured log format.** `ecs`, `logstash` or `gelf`. The ECS format fits CloudWatch Logs Insights, but the team must confirm its log pipeline first.
4. **Is `*` on a private management port acceptable?** P1 allows any exposure when `management.server.port` is set. Confirm the port is unreachable from outside the VPC.
5. **Should the harness require actuator?** P9 says no. The alternative is a required dependency for web apps.
6. **Gate or review for P4?** Sampling probability and shutdown mode are values. Gating them would fix a number for every team.
7. **Verify the remaining UNVERIFIED items before a proposal ships.** They are marked in the sections above.

---

## Sources

Fetched and quoted:

- Spring Boot 4.1.2 reference, Observability: https://docs.spring.io/spring-boot/reference/actuator/observability.html
- Spring Boot 4.1.2 reference, Actuator endpoints: https://docs.spring.io/spring-boot/reference/actuator/endpoints.html
- Spring Boot 4.1.2 reference, Tracing: https://docs.spring.io/spring-boot/reference/actuator/tracing.html
- Spring Boot 4.1.2 reference, Metrics (partial, first 100000 characters): https://docs.spring.io/spring-boot/reference/actuator/metrics.html
- Spring Boot 4.1.2 reference, Logging: https://docs.spring.io/spring-boot/reference/features/logging.html
- Spring Boot 4.1.2 reference, Graceful shutdown: https://docs.spring.io/spring-boot/reference/web/graceful-shutdown.html
- Micrometer Observation introduction: https://docs.micrometer.io/micrometer/reference/observation/introduction.html
- Micrometer Observation testing: https://docs.micrometer.io/micrometer/reference/observation/testing.html
- OpenTelemetry metrics SDK specification: https://opentelemetry.io/docs/specs/otel/metrics/sdk/
- Amazon ECS task definition parameters: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html
- Amazon ECS rolling update deployments: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-type-ecs.html
- Amazon ECS Container Insights with enhanced observability: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/cloudwatch-container-insights.html
- Send Amazon ECS logs to CloudWatch: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/using_awslogs.html
- Send Amazon ECS logs to an AWS service or AWS Partner (FireLens): https://docs.aws.amazon.com/AmazonECS/latest/developerguide/using_firelens.html
- Monitor Amazon ECS containers with ECS Exec: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-exec.html
- Target groups for Application Load Balancers: https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html
- AWS X-Ray OpenTelemetry (OTLP) endpoint: https://docs.aws.amazon.com/xray/latest/devguide/xray-opentelemetry.html
- Java SE 25 `java` command (`MaxRAMPercentage`, container support): https://docs.oracle.com/en/java/javase/25/docs/specs/man/java.html

Caveat: the quoted text above came from WebFetch, which returns a model-written summary of each page. Re-check exact wording against the live page before quoting it in a published doc.

Seen in search results only, not fetched, so not relied on for exact wording:

- Micrometer high-cardinality tags detector, and the claim that only low-cardinality values become meter tags: https://docs.micrometer.io/micrometer/reference/concepts/high-cardinality-tags-detector.html

Added in a second pass, which corrected the shutdown, probe and SigV4 guidance:

- Amazon ECS task lifecycle: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-lifecycle-explanation.html
- CloudWatch OTLP endpoints: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-OTLPEndpoint.html
- ECS deployment alarms: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-alarm-failure.html
- ECS events: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_cwe_events.html
- Spring Modulith production-ready features: https://docs.spring.io/spring-modulith/reference/production-ready.html
- OpenTelemetry Spring Boot starter: https://opentelemetry.io/docs/zero-code/java/spring-boot-starter/
- Search excerpts only: ECS ClusterSetting (https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_ClusterSetting.html), Spring Kafka monitoring (https://docs.spring.io/spring-kafka/reference/kafka/micrometer.html)

Not fetched (ADOT specifics, AMP and AMG, stopped-task event detail, health-check defaults): listed as UNVERIFIED above, with no source cited.
