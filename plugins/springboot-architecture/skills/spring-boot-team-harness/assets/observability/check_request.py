#!/usr/bin/env python3
"""Prove what one request did: send it with a fresh trace id, then read that trace and its log lines.

  python3 observability/check_request.py --service <spring.application.name> http://localhost:8080/api/orders
  python3 observability/check_request.py --service <name> -X POST -H 'Content-Type: application/json' -d '{}' <url>
  python3 observability/check_request.py --service <name> --expect 404 <url>
  python3 observability/check_request.py --service <name> --trace <id>

Use --trace for a request something else sent, such as a browser test that set its own traceparent header. Log
messages aren't printed, so the report is safe to paste: it shows levels, loggers and exception types.
Exit codes: 0 the request worked and its trace arrived, 1 it failed or left no trace, 2 the app or the stack is down.
"""

import argparse
import json
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ERROR_LEVELS = {"error", "fatal", "critical"}
LOG_WAIT_SECONDS = 15


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


def send(args, trace: str) -> int:
    headers = dict(header.split(":", 1) for header in args.header)
    headers = {name.strip(): value.strip() for name, value in headers.items()}
    headers["traceparent"] = f"00-{trace}-{secrets.token_hex(8)}-01"
    body = args.data.encode() if args.data is not None else None
    method = args.request or ("POST" if body is not None else "GET")
    request = urllib.request.Request(args.url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status
    except urllib.error.HTTPError as error:
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
    """Waits for the server span, which is the last to arrive: its parent ends after its children."""
    deadline = time.monotonic() + args.wait
    spans = []
    while True:
        found = get(f"{args.tempo}/api/traces/{trace}")
        spans = spans_of(found, args.service) if found else []
        if any(span.get("kind") == "SPAN_KIND_SERVER" for span in spans) or time.monotonic() >= deadline:
            return spans
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
    parser.add_argument("--expect", type=int, help="The status the request should get. Default: anything below 500")
    parser.add_argument("-X", "--request", help="Method. Default: GET, or POST with -d")
    parser.add_argument("-H", "--header", action="append", default=[])
    parser.add_argument("-d", "--data")
    parser.add_argument("--wait", type=int, default=60, help="Seconds to wait for the trace")
    parser.add_argument("--tempo", default="http://localhost:3200")
    parser.add_argument("--loki", default="http://localhost:3100")
    args = parser.parse_args()
    if bool(args.url) == bool(args.trace):
        parser.error("give a URL or --trace, not both")

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

    for problem in problems:
        print(f"FAIL     {problem}")
    if not problems:
        print("ok       request verified")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
