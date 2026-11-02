#!/usr/bin/env python3
"""Show an agent what the running app did for its own request, from the verify profile's JSON log.

  telemetry.py doctor                 prove the app answers and its requests reach the log
  telemetry.py mark                   start a run: later `errors` calls look only after this point
  telemetry.py new-trace              print a trace id and traceparent header for a journey to send
  telemetry.py call GET /api/orders   send a request with a trace id, then report its status and log lines
  telemetry.py logs <traceId>         print the log lines of one trace
  telemetry.py errors                 group WARN and ERROR lines since the mark, traced or not

Every command prints JSON. Exit codes: 0 pass, 1 fail, 4 no telemetry, which never means no errors.
"""

import argparse
import json
import re
import secrets
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

PASS, FAIL, NO_TELEMETRY = 0, 1, 4
LEVELS = ("TRACE", "DEBUG", "INFO", "WARN", "ERROR")
STACK_LINES = 6
PROFILE_HINT = "start the app with --spring.profiles.active=verify from this checkout"


def traceparent() -> tuple[str, str]:
    trace_id = secrets.token_hex(16)
    return trace_id, f"00-{trace_id}-{secrets.token_hex(8)}-01"


def send(url: str, method: str, headers: dict, body: str | None, timeout: float) -> tuple[int | None, str, float]:
    started = time.monotonic()
    request = urllib.request.Request(url, method=method, headers=headers, data=body.encode() if body else None)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode(errors="replace"), time.monotonic() - started
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode(errors="replace"), time.monotonic() - started
    except (urllib.error.URLError, OSError) as error:
        return None, str(error), time.monotonic() - started


def mark_path(log: Path) -> Path:
    return log.with_name(log.name + ".mark")


def read_lines(log: Path, offset: int = 0) -> list[dict]:
    if not log.exists():
        return []
    lines = []
    with log.open("rb") as file:
        # A rotated log is shorter than the mark, so read all of it.
        file.seek(offset if offset <= log.stat().st_size else 0)
        for raw in file:
            try:
                lines.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    return lines


def shorten(line: dict) -> dict:
    short = {"time": line.get("@timestamp"), "level": line.get("level"), "logger": line.get("logger_name"),
             "thread": line.get("thread_name"), "message": line.get("message")}
    if "stack_trace" in line:
        short["stack"] = line["stack_trace"].splitlines()[:STACK_LINES]
    return short


def traced(log: Path, trace_id: str) -> list[dict]:
    return [line for line in read_lines(log) if line.get("traceId") == trace_id]


def finish(result: dict, code: int) -> int:
    print(json.dumps(result, indent=2))
    return code


def doctor(args) -> int:
    trace_id, header = traceparent()
    status, body, _ = send(f"{args.app}/actuator/health", "GET", {"traceparent": header}, None, args.timeout)
    if status != 200:
        return finish({"ok": False, "problem": f"{args.app}/actuator/health answered {status}: {body[:200]}",
                       "do": PROFILE_HINT}, NO_TELEMETRY)
    if not args.log.exists():
        return finish({"ok": False, "problem": f"no log at {args.log}", "do": PROFILE_HINT}, NO_TELEMETRY)
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        if traced(args.log, trace_id):
            return finish({"ok": True, "app": args.app, "log": str(args.log)}, PASS)
        time.sleep(0.1)
    return finish({"ok": False, "problem": f"trace {trace_id} reached the app but not {args.log}",
                   "do": f"another app may hold the port, or the verify profile is off; {PROFILE_HINT}"}, NO_TELEMETRY)


def mark(args) -> int:
    if not args.log.exists():
        return finish({"ok": False, "problem": f"no log at {args.log}", "do": PROFILE_HINT}, NO_TELEMETRY)
    size = args.log.stat().st_size
    mark_path(args.log).write_text(str(size), encoding="utf-8")
    return finish({"ok": True, "offset": size}, PASS)


def new_trace(_) -> int:
    trace_id, header = traceparent()
    return finish({"traceId": trace_id, "traceparent": header}, PASS)


def call(args) -> int:
    trace_id, header = traceparent()
    headers = {name.strip(): value.strip() for name, value in (item.split(":", 1) for item in args.header)}
    status, body, seconds = send(f"{args.app}/{args.path.lstrip('/')}", args.method.upper(),
                                 {**headers, "traceparent": header}, args.data, args.timeout)
    result = {"traceId": trace_id, "status": status, "ms": round(seconds * 1000)}
    if status is None:
        return finish({**result, "problem": body, "do": PROFILE_HINT}, NO_TELEMETRY)
    time.sleep(args.settle)
    lines = traced(args.log, trace_id)
    if not lines:
        return finish({**result, "problem": f"no line with this trace id in {args.log}",
                       "do": "run telemetry.py doctor"}, NO_TELEMETRY)
    found = {level: [shorten(line) for line in lines if line.get("level") == level] for level in ("ERROR", "WARN")}
    failed = status >= 500 or bool(found["ERROR"])
    return finish({**result, "ok": not failed, "lines": len(lines), "errors": found["ERROR"],
                   "warnings": found["WARN"], "body": body[:args.body_limit]}, FAIL if failed else PASS)


def logs(args) -> int:
    lines = traced(args.log, args.trace_id)
    if not lines:
        return finish({"problem": f"no line with trace {args.trace_id} in {args.log}",
                       "do": "check the id, or run telemetry.py doctor"}, NO_TELEMETRY)
    wanted = LEVELS[LEVELS.index(args.level):]
    return finish({"traceId": args.trace_id, "total": len(lines),
                   "lines": [shorten(line) for line in lines if line.get("level") in wanted]}, PASS)


def errors(args) -> int:
    marker = mark_path(args.log)
    if not args.log.exists():
        return finish({"ok": False, "problem": f"no log at {args.log}", "do": PROFILE_HINT}, NO_TELEMETRY)
    if not marker.exists():
        return finish({"ok": False, "problem": "no mark, so startup noise would count",
                       "do": "run telemetry.py mark before the run"}, NO_TELEMETRY)
    lines = read_lines(args.log, int(marker.read_text(encoding="utf-8")))
    groups, first_trace = Counter(), {}
    for line in lines:
        if line.get("level") not in ("WARN", "ERROR"):
            continue
        cause = line.get("stack_trace", "").split("\n", 1)[0]
        message = re.sub(r"\b[0-9a-f-]{8,}\b|\d+", "#", line.get("message", ""))
        key = (line["level"], line.get("logger_name"), message, cause)
        groups[key] += 1
        first_trace.setdefault(key, line.get("traceId"))
    found = [{"level": key[0], "logger": key[1], "message": key[2], "cause": key[3], "count": count,
              "traceId": first_trace[key]} for key, count in groups.most_common()]
    error_groups = sum(group["level"] == "ERROR" for group in found)
    print(json.dumps({"ok": not error_groups, "scanned": len(lines), "groups": found}, indent=2))
    print(f"telemetry: scanned={len(lines)} error_groups={error_groups} "
          f"warn_groups={len(found) - error_groups} log={args.log}")
    return FAIL if error_groups else PASS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--app", default="http://localhost:8080", help="Base URL of the running app")
    parser.add_argument("--log", type=Path, default=Path("target/verify/app.jsonl"), help="The verify profile's log")
    parser.add_argument("--timeout", type=float, default=10, help="Seconds to wait for a response")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Prove the app answers and its requests reach the log").set_defaults(run=doctor)
    commands.add_parser("mark", help="Start a run for later errors calls").set_defaults(run=mark)
    commands.add_parser("new-trace", help="Print a trace id and header for a journey").set_defaults(run=new_trace)
    sender = commands.add_parser("call", help="Send a traced request and report its log lines")
    sender.add_argument("method")
    sender.add_argument("path", help="Leave off the leading slash in Git Bash, which rewrites it into a Windows path")
    sender.add_argument("--data", help="Request body")
    sender.add_argument("--header", action="append", default=[], help="A 'Name: value' header; repeat for more")
    sender.add_argument("--settle", type=float, default=1, help="Seconds to wait for work after the response")
    sender.add_argument("--body-limit", type=int, default=500, help="Characters of the response body to print")
    sender.set_defaults(run=call)
    reader = commands.add_parser("logs", help="Print one trace's log lines")
    reader.add_argument("trace_id")
    reader.add_argument("--level", choices=LEVELS, default="INFO")
    reader.set_defaults(run=logs)
    commands.add_parser("errors", help="Group WARN and ERROR lines since the mark").set_defaults(run=errors)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.app = args.app.rstrip("/")
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
