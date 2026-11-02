#!/usr/bin/env python3
"""Prove what one request or job did: send it with a fresh trace id, or find its run, then read the trace and its logs.

  python3 observability/check_request.py --service <spring.application.name> http://localhost:8080/api/orders
  python3 observability/check_request.py --service <name> -X POST -H 'Content-Type: application/json' -d '{}' <url>
  python3 observability/check_request.py --service <name> --expect 404 <url>
  python3 observability/check_request.py --service <name> --trace <id>
  python3 observability/check_request.py --service <name> --job <text in the span name> --since 120

A redirect is reported, not followed. The check waits until the trace stops growing, so it includes work an event
listener did on another thread after the response. Use --trace for a request something else sent, such as a browser
test that set its own traceparent header. Use --job for work no request starts, such as a @Scheduled method or a
message listener: it reads the newest run whose span name holds the text, so keep --since shorter than the time since
the app restarted. Log messages aren't printed, so the report is safe to paste: it shows levels, loggers and exception
types.
Exit codes: 0 the work succeeded and its trace arrived, 1 it failed or left no trace, 2 the app or the stack is down.
"""

import argparse
import json
import re
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ERROR_LEVELS = {"error", "fatal", "critical"}
LOG_WAIT_SECONDS = 15
JOB_RUNS = 20
TRACE_ID_LENGTH = 32
SETTLE_SECONDS = 3
# Spring Modulith logs a listener that threw at INFO, and leaves its event publication incomplete.
LISTENER_FAILURE_LOGGER = "org.springframework.modulith.events.support.CompletionRegisteringAdvisor"


def get(url: str, **params) -> dict | None:
    query = f"?{urllib.parse.urlencode(params)}" if params else ""
    request = urllib.request.Request(f"{url}{query}", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


class KeepRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def send(args, trace: str) -> int:
    """Reads the whole body: closing early aborts the app's write, which records an error on its span."""
    headers = dict(header.split(":", 1) for header in args.header)
    headers = {name.strip(): value.strip() for name, value in headers.items()}
    headers["traceparent"] = f"00-{trace}-{secrets.token_hex(8)}-01"
    body = args.data.encode() if args.data is not None else None
    method = args.request or ("POST" if body is not None else "GET")
    request = urllib.request.Request(args.url, data=body, headers=headers, method=method)
    try:
        with urllib.request.build_opener(KeepRedirects).open(request, timeout=30) as response:
            response.read()
            return response.status
    except urllib.error.HTTPError as error:
        error.read()
        return error.code


def spans_of(trace: dict, service: str) -> list[dict]:
    spans = []
    for batch in trace.get("batches") or trace.get("resourceSpans") or []:
        attributes = batch.get("resource", {}).get("attributes", [])
        names = [a["value"].get("stringValue") for a in attributes if a["key"] == "service.name"]
        if service in names:
            spans += [span for scope in batch.get("scopeSpans", []) for span in scope.get("spans", [])]
    return spans


def read_trace(args, trace: str) -> list[dict]:
    """Waits for the server span, then until no span has arrived for a few seconds: an event listener runs after the
    response, on another thread, and its spans join the same trace."""
    deadline = time.monotonic() + args.wait
    settle = min(SETTLE_SECONDS, args.wait)
    spans, changed = [], time.monotonic()
    while True:
        found = get(f"{args.tempo}/api/traces/{trace}")
        latest = spans_of(found, args.service) if found else []
        if len(latest) != len(spans):
            spans, changed = latest, time.monotonic()
        finished = args.job or any(span.get("kind") == "SPAN_KIND_SERVER" for span in spans)
        if (spans and finished and time.monotonic() - changed >= settle) or time.monotonic() >= deadline:
            return spans
        time.sleep(1)


def find_job(args) -> str | None:
    """Waits for a span with the name, and returns the newest trace that has one. Tempo drops an id's leading zeros."""
    name = re.escape(args.job).replace("\\", "\\\\")
    query = '{ resource.service.name = "%s" && name =~ "(?i).*%s.*" }' % (args.service, name)
    deadline = time.monotonic() + args.wait
    while True:
        now = int(time.time())
        found = get(f"{args.tempo}/api/search", q=query, start=now - args.since, end=now, limit=JOB_RUNS)
        runs = (found or {}).get("traces") or []
        if runs:
            return max(runs, key=lambda run: int(run.get("startTimeUnixNano", 0)))["traceID"].zfill(TRACE_ID_LENGTH)
        if time.monotonic() >= deadline:
            return None
        time.sleep(1)


def read_logs(args, trace: str) -> list[dict]:
    query = '{service_name="%s"} | trace_id="%s"' % (args.service, trace)
    deadline = time.monotonic() + min(args.wait, LOG_WAIT_SECONDS)
    while True:
        streams = get(f"{args.loki}/loki/api/v1/query_range", query=query, since="1h")["data"]["result"]
        if streams or time.monotonic() >= deadline:
            return streams
        time.sleep(1)


def failed(span: dict) -> bool:
    outcome = [a["value"].get("stringValue") for a in span.get("attributes", []) if a["key"] == "outcome"]
    return span.get("status", {}).get("code") == "STATUS_CODE_ERROR" or "SERVER_ERROR" in outcome


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("url", nargs="?")
    parser.add_argument("--service", required=True)
    parser.add_argument("--trace", help="Read this trace instead of sending a request")
    parser.add_argument("--job", help="Read the newest run of a job whose span name holds this text")
    parser.add_argument("--since", type=int, default=300, help="Seconds back to look for the job's run")
    parser.add_argument("--expect", type=int, help="The status the request should get. Default: anything below 500")
    parser.add_argument("-X", "--request", help="Method. Default: GET, or POST with -d")
    parser.add_argument("-H", "--header", action="append", default=[])
    parser.add_argument("-d", "--data")
    parser.add_argument("--wait", type=int, default=60, help="Seconds to wait for the trace")
    parser.add_argument("--tempo", default="http://localhost:3200")
    parser.add_argument("--loki", default="http://localhost:3100")
    args = parser.parse_args()
    if sum(map(bool, (args.url, args.trace, args.job))) != 1:
        parser.error("give one of a URL, --trace or --job")

    trace = args.trace or secrets.token_hex(16)
    problems = []
    expected_failure = args.expect is not None and args.expect >= 500
    try:
        if args.url:
            status = send(args, trace)
            print(f"request  {args.url} -> {status}")
            if args.expect is not None and status != args.expect:
                problems.append(f"status {status}, expected {args.expect}")
            elif args.expect is None and status >= 500:
                problems.append(f"status {status}")
    except OSError as error:
        print(f"CANNOT RUN  app not reachable at {args.url}: {error}")
        return 2
    try:
        if args.job:
            trace = find_job(args)
            if trace is None:
                print(f"FAIL     no run of {args.job} from {args.service} in the last {args.since}s: it didn't run, "
                      "its span has another name, or the app runs without the observability profile")
                return 1
        spans = read_trace(args, trace)
        streams = read_logs(args, trace)
    except OSError as error:
        print(f"CANNOT RUN  stack not reachable: {error}")
        return 2

    print(f"trace    {trace}")
    print(f"spans    {len(spans)}: {', '.join(sorted({span.get('name', '?') for span in spans})[:10])}")
    if not spans:
        problems.append(f"no trace from {args.service}: another process answered, the app runs without the "
                        "observability profile, or the trace is still on its way")
    failures = [span.get("name", "?") for span in spans if failed(span)]
    if failures and args.expect is None:
        problems.append(f"failed spans: {', '.join(sorted(set(failures)))}")

    errors = [stream for stream in streams if stream["stream"].get("detected_level", "").lower() in ERROR_LEVELS]
    print(f"logs     {sum(len(stream['values']) for stream in streams)} lines, "
          f"{sum(len(stream['values']) for stream in errors)} at ERROR")
    for stream in errors:
        labels = stream["stream"]
        print(f"  ERROR  {labels.get('scope_name', '?')} {labels.get('exception_type', '')}".rstrip())
    if errors and not expected_failure:
        problems.append("ERROR log lines")
    if any(stream["stream"].get("scope_name", "").startswith(LISTENER_FAILURE_LOGGER) for stream in streams):
        problems.append("an event listener failed, so its event publication is incomplete")

    for problem in problems:
        print(f"FAIL     {problem}")
    if not problems:
        print(f"ok       {'job' if args.job else 'request'} verified")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
