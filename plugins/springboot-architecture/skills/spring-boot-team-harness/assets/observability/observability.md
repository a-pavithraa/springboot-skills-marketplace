# Observability

The app sends traces, metrics and logs over OTLP to whatever endpoint it is given. It knows nothing about Grafana, ECS or EKS, so moving platforms changes where the collector runs, not the app or the dashboards.

Export is off unless `OTLP_EXPORT_ENABLED=true`.

## The contract

These variables are the whole interface. They are the same on a laptop, ECS and EKS.

| Variable | Default | Meaning |
| --- | --- | --- |
| `OTLP_EXPORT_ENABLED` | `false` | Sends traces, metrics and logs |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4318` | Base URL of the collector, with no path |
| `TRACING_SAMPLE_RATE` | `0.1` | Share of requests traced |
| `DEPLOYMENT_ENVIRONMENT` | `local` | Label on all telemetry, and the dashboard's Environment filter |

The settings are in `src/main/resources/application-observability-defaults.yml`, which the main config file imports. Its values win over that file. To change one, set the variable, or set the key in a profile file such as `application-prod.yml`.

## Run it locally

```bash
docker compose -f compose.observability.yml up -d
{{RUN_WITH_PROFILE}}
```

Add the profile to any you already use. Then open <http://localhost:3000>, Dashboards, Project: Service health for requests and logs, JVM and resources for the process. The stack listens on this machine only. Metrics arrive every 10 seconds and rates need two samples, so panels take about 30 seconds to fill. The stack loses its data when the container is removed.

## Check a change

Each dashboard panel is a query, so developers and coding agents ask the same questions. To see the query behind a panel, read it in `observability/dashboards/`.

```bash
# Prometheus: p95 latency for one route
curl -G localhost:9090/api/v1/query --data-urlencode \
  'query=histogram_quantile(0.95, sum by (le) (rate(http_server_requests_milliseconds_bucket{uri="/api/orders"}[5m])))'

# Tempo: failed requests, then one trace with its spans and SQL
curl -G localhost:3200/api/search --data-urlencode 'q={ span.outcome = "SERVER_ERROR" }'
curl localhost:3200/api/traces/<traceId>

# Loki: ERROR lines in the last hour
curl -G localhost:3100/loki/api/v1/query_range --data-urlencode 'query={service_name="{{PROJECT_NAME}}"} | detected_level="error"' --data-urlencode since=1h

# Loki: every log line from one request
curl -G localhost:3100/loki/api/v1/query_range --data-urlencode 'query={service_name="{{PROJECT_NAME}}"} | trace_id="<traceId>"' --data-urlencode since=1h
```

A page that looks right can hide a failure behind it, so read the errors as well as the response.

To check a change, follow one request you sent. Older data can't prove anything about it, and a passing test doesn't show the running app did it. Do this for any change to runtime behaviour:

```bash
python3 observability/check_request.py --service {{PROJECT_NAME}} http://localhost:8080/api/orders
python3 observability/check_request.py --service {{PROJECT_NAME}} --expect 404 http://localhost:8080/api/orders/0
python3 observability/check_request.py --service {{PROJECT_NAME}} -X POST -H 'Content-Type: application/json' -d '{}' <url>
```

It sends the request with a fresh trace id, waits for that trace, and reports the status, spans and ERROR lines. It fails on a 5xx, on a failed span, on an ERROR line, and when no trace arrives. No trace usually means another process answered on that port, or the app runs without the `observability` profile. With `--expect`, failed spans are reported but don't fail the check, because a refused request marks its security span as failed. ERROR lines still fail it unless the expected status is a 5xx. Exit 2 means the app or the stack is down, so nothing was proved.

A request that needs a signed-in session can't be sent this way. Set the header in the browser test that sends it, then read the result with `--trace`:

```text
traceparent: 00-<32 hex trace id>-<16 hex span id>-01
python3 observability/check_request.py --service {{PROJECT_NAME}} --trace <trace id>
```

The check proves the request ran here and hid no failure. It doesn't know what the change was meant to do, so say what in the trace or response shows it worked.

After adding a panel, or upgrading Boot or the image, run this while traffic is flowing. An unknown metric gives an empty panel and no error, and a missing histogram gives `NaN`. It proves the pipeline and the queries work. It doesn't prove a change behaved: it passes while errors exist, and on data left by an app that has stopped. The Slow or failed requests panel may be empty on a healthy service, so the script checks separately that traces arrive.

```bash
python3 observability/check_dashboards.py --service <spring.application.name>
```

## Sensitive data

- `include-parameter-values` is `false`, so spans hold SQL with `?` placeholders. Never turn it on.
- Don't build SQL by joining strings: the values would reach `jdbc.query[n]` span attributes.
- Span `http.url` holds raw paths, so keep personal data out of URLs.
- Only INFO and above is exported, whatever level a profile sets, because framework DEBUG lines can hold sign-in tokens. The console and log file still get DEBUG.
- Log lines, exception messages and `addKeyValue` pairs are exported as they are, so keep personal data out of them.
- A deployed collector and its stores need the same access rules and retention as the logs.
- Only Boot's own `@Async` executor carries the trace id. A pool you build yourself needs `ContextPropagatingTaskDecorator`, or its log lines have none.
- `LogLeakCheck` fails a test when app code logs an email address or a credential, but it only sees tested paths. As a second line, add the collector's `redaction` or `transform` processor before any export. Hashing doesn't protect values that are easy to guess, such as numeric ids.

<!-- failure-filter:begin -->
## Failed requests

`HandledFailureFilter` logs every 5xx that an `@ExceptionHandler` answered, including `Callable` and `DeferredResult` failures, with its stack trace, and records the error on the observation. Without it Spring treats those requests as dealt with. Find them in Tempo with `{ span.outcome = "SERVER_ERROR" }`, not `{ status = error }`: in testing, a 500 answered by a handler left the span status unset. New traces can take up to a minute to appear in search. Handlers return a generic `ProblemDetail` and leave the exception out of the response. The filter only sees handlers that write the response body: one that returns an error view isn't covered, so it must log the exception itself.

<!-- failure-filter:end -->
## Move to ECS

1. Add a collector container to the task. It shares the task's network, so the default endpoint already fits.
2. Set `OTLP_EXPORT_ENABLED=true` and `DEPLOYMENT_ENVIRONMENT=<env>`.
3. Give the task role what the collector's exporters need. The app needs nothing.

## Move to EKS

1. Run the collector as a DaemonSet, or a Deployment with a Service.
2. Set the same variables, with `OTEL_EXPORTER_OTLP_ENDPOINT=http://<collector-service>.<namespace>:4318`.
3. Use `/actuator/health/liveness` and `/actuator/health/readiness` for probes.

## On any deployed platform

CloudWatch and X-Ray OTLP endpoints take SigV4 or a bearer token. This harness sends through a collector so that the app holds no cloud credentials; direct export is possible, but you'd have to add that authentication yourself. After the first deployment, run `check_dashboards.py` with `--prometheus`, `--tempo`, `--loki` and `--environment`, because a collector can rename metrics.
