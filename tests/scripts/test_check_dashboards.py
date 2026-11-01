"""Regression tests for spring-boot-team-harness/assets/observability/check_dashboards.py.

Run from the repository root:
    python3 -m unittest discover -s tests/scripts -v
"""

import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ASSETS = (Path(__file__).resolve().parents[2] / "plugins/springboot-architecture/skills/spring-boot-team-harness"
          / "assets/observability")


def stack(traces: dict[str, list]):
    """A stand-in for Prometheus, Loki and Tempo. traces maps a substring of the TraceQL query to what search returns."""
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            url = urllib.parse.urlparse(self.path)
            if url.path == "/api/search":
                query = urllib.parse.parse_qs(url.query)["q"][0]
                seen.append(query)
                body = {"traces": next((found for part, found in traces.items() if part in query), [])}
            else:
                body = {"data": {"result": [1]}}
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(body).encode())

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, seen


class CheckDashboardsTests(unittest.TestCase):

    def run_check(self, traces):
        server, seen = stack(traces)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        url = f"http://127.0.0.1:{server.server_port}"
        with tempfile.TemporaryDirectory() as folder:
            shutil.copy(ASSETS / "check_dashboards.py", folder)
            shutil.copytree(ASSETS / "dashboards", Path(folder) / "dashboards")
            result = subprocess.run([sys.executable, str(Path(folder) / "check_dashboards.py"), "--service", "orders",
                                     "--environment", "staging", "--prometheus", url, "--tempo", url, "--loki", url],
                                    capture_output=True, text=True)
        return result, seen

    def test_a_healthy_service_with_no_slow_requests_passes(self):
        result, _ = self.run_check({'"staging" }': [{"traceID": "1"}]})
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("skip  service-health: Slow or failed requests", result.stdout)
        self.assertIn("ok    traces arrive", result.stdout)

    def test_no_traces_at_all_fails(self):
        result, _ = self.run_check({})
        self.assertEqual(result.returncode, 1)
        self.assertIn("EMPTY no traces for orders in staging", result.stdout)

    def test_every_trace_query_is_limited_to_the_environment(self):
        _, seen = self.run_check({})
        self.assertEqual(len(seen), 2)
        for query in seen:
            self.assertIn('resource.deployment.environment.name = "staging"', query)


if __name__ == "__main__":
    unittest.main()
