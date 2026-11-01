#!/usr/bin/env python3
"""Fail when a dashboard panel returns nothing, which a renamed metric would otherwise cause silently.

  python3 observability/check_dashboards.py --service <spring.application.name> [--environment local]

Run it against a stack that has received traffic for a few minutes. A panel marked "optional" only warns: an app
with no database has nothing to show on a database panel, and a healthy one has no slow or failed requests. Traces
are checked separately, so that an empty trace panel can't hide a trace pipeline that isn't working.
Exit codes: 0 every required panel has data and traces arrive, 1 something is empty.
"""

import argparse
import json
import math
import sys
import urllib.parse
import urllib.request
from pathlib import Path

DASHBOARDS = Path(__file__).resolve().parent / "dashboards"
ANY_TRACE = {"queryType": "traceql",
             "query": '{ resource.service.name = "$service" && resource.deployment.environment.name = "$environment" }'}


def get(url: str, **params) -> dict:
    with urllib.request.urlopen(f"{url}?{urllib.parse.urlencode(params)}", timeout=15) as response:
        return json.load(response)


def fill(query: str, args) -> str:
    return (query.replace("$service", args.service).replace("$environment", args.environment)
            .replace("$__rate_interval", "2m"))


def result(target: dict, args) -> str:
    if target.get("queryType") == "traceql":
        found = get(f"{args.tempo}/api/search", q=fill(target["query"], args), limit=1).get("traces")
    elif "expr" not in target or target.get("queryType") == "range" or target.get("logql"):
        found = get(f"{args.loki}/loki/api/v1/query_range", query=fill(target["expr"], args), since="1h",
                    limit=1)["data"]["result"]
    else:
        found = get(f"{args.prometheus}/api/v1/query", query=fill(target["expr"], args))["data"]["result"]
        if found and not any(math.isfinite(float(series["value"][1])) for series in found):
            return "no number"
    return "data" if found else "empty"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--prometheus", default="http://localhost:9090")
    parser.add_argument("--tempo", default="http://localhost:3200")
    parser.add_argument("--loki", default="http://localhost:3100")
    parser.add_argument("--service", required=True)
    parser.add_argument("--environment", default="local")
    args = parser.parse_args()
    empty = 0
    for path in sorted(DASHBOARDS.glob("*.json")):
        for panel in json.loads(path.read_text(encoding="utf-8"))["panels"]:
            for target in panel["targets"]:
                found = result(target, args)
                if found == "data":
                    print(f"ok    {path.stem}: {panel['title']}")
                elif found == "no number":
                    empty += 1
                    print(f"NaN   {path.stem}: {panel['title']} (no recent traffic, or its histogram is off)")
                elif panel.get("optional"):
                    print(f"skip  {path.stem}: {panel['title']} (optional, no data)")
                else:
                    empty += 1
                    print(f"EMPTY {path.stem}: {panel['title']}")
    if result(ANY_TRACE, args) == "data":
        print("ok    traces arrive")
    else:
        empty += 1
        print(f"EMPTY no traces for {args.service} in {args.environment}")
    return 1 if empty else 0


if __name__ == "__main__":
    sys.exit(main())
