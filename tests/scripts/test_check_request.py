"""Regression tests for spring-boot-team-harness/assets/observability/check_request.py.

Run from the repository root:
    python3 -m unittest discover -s tests/scripts -v
"""

import json
import re
import subprocess
import sys
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SCRIPT = (Path(__file__).resolve().parents[2] / "plugins/springboot-architecture/skills/spring-boot-team-harness"
          / "assets/observability/check_request.py")
SERVER_SPAN = {"name": "http get /api/orders", "kind": "SPAN_KIND_SERVER"}
FAILED_SPAN = {"name": "http get /api/orders", "kind": "SPAN_KIND_SERVER",
               "attributes": [{"key": "outcome", "value": {"stringValue": "SERVER_ERROR"}}]}


def trace_of(spans, service="orders"):
    resource = {"attributes": [{"key": "service.name", "value": {"stringValue": service}}]}
    return {"batches": [{"resource": resource, "scopeSpans": [{"spans": spans}]}]}


def serve(handler):
    server = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class CheckRequestTests(unittest.TestCase):

    def start(self, status=200, trace=None, streams=()):
        """A stand-in for the app and for Tempo and Loki. It records each header the app got, and each log query."""
        seen = {"sent": [], "logs": []}

        class Handler(BaseHTTPRequestHandler):
            def reply(self, code, body=b"{}"):
                self.send_response(code)
                self.end_headers()
                self.wfile.write(body)

            def app(self):
                length = int(self.headers.get("Content-Length") or 0)
                seen["sent"].append((self.command, dict(self.headers), self.rfile.read(length).decode()))
                self.reply(status)

            def do_POST(self):
                self.app()

            def do_GET(self):
                url = urllib.parse.urlparse(self.path)
                if url.path.startswith("/api/traces/"):
                    self.reply(404) if trace is None else self.reply(200, json.dumps(trace).encode())
                elif url.path == "/loki/api/v1/query_range":
                    seen["logs"].append(urllib.parse.parse_qs(url.query)["query"][0])
                    self.reply(200, json.dumps({"data": {"result": list(streams)}}).encode())
                else:
                    self.app()

            def log_message(self, *args):
                pass

        server = serve(Handler)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return f"http://127.0.0.1:{server.server_port}", seen

    def check(self, url, *extra, target="/api/orders"):
        return subprocess.run([sys.executable, str(SCRIPT), "--service", "orders", "--wait", "0", "--tempo", url,
                               "--loki", url, *extra, *([f"{url}{target}"] if target else [])],
                              capture_output=True, text=True)

    def test_a_request_with_a_clean_trace_passes(self):
        url, seen = self.start(trace=trace_of([SERVER_SPAN]))
        result = self.check(url)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("-> 200", result.stdout)
        self.assertIn("ok       request verified", result.stdout)

    def test_it_reads_back_the_trace_it_sent(self):
        url, seen = self.start(trace=trace_of([SERVER_SPAN]))
        result = self.check(url)
        trace = re.search(r"^trace +(\w{32})$", result.stdout, re.M).group(1)
        self.assertRegex(seen["sent"][0][1]["Traceparent"], f"^00-{trace}-[0-9a-f]{{16}}-01$")
        self.assertEqual(seen["logs"][0], f'{{service_name="orders"}} | trace_id="{trace}"')

    def test_data_makes_it_a_post_with_the_given_headers(self):
        url, seen = self.start(trace=trace_of([SERVER_SPAN]))
        self.check(url, "-H", "X-Token: a:b", "-d", '{"id":1}')
        method, headers, body = seen["sent"][0]
        self.assertEqual((method, headers["X-Token"], body), ("POST", "a:b", '{"id":1}'))

    def test_a_5xx_fails(self):
        url, _ = self.start(status=503, trace=trace_of([SERVER_SPAN]))
        result = self.check(url)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("FAIL     status 503", result.stdout)

    def test_a_status_other_than_the_expected_one_fails(self):
        url, _ = self.start(status=200, trace=trace_of([SERVER_SPAN]))
        result = self.check(url, "--expect", "404")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("FAIL     status 200, expected 404", result.stdout)

    def test_a_failed_span_behind_a_good_status_fails(self):
        url, _ = self.start(trace=trace_of([FAILED_SPAN]))
        result = self.check(url)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("FAIL     failed spans:", result.stdout)

    def test_an_error_log_behind_a_good_status_fails_without_printing_the_message(self):
        stream = {"stream": {"detected_level": "error", "scope_name": "com.acme.Orders",
                             "exception_type": "java.lang.IllegalStateException"},
                  "values": [["1", "lookup failed for someone@example.com"]]}
        url, _ = self.start(trace=trace_of([SERVER_SPAN]), streams=[stream])
        result = self.check(url)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("com.acme.Orders java.lang.IllegalStateException", result.stdout)
        self.assertIn("1 lines, 1 at ERROR", result.stdout)
        self.assertNotIn("someone@example.com", result.stdout)

    def test_an_expected_5xx_passes_and_still_shows_its_error(self):
        stream = {"stream": {"detected_level": "error"}, "values": [["1", "boom"]]}
        url, _ = self.start(status=500, trace=trace_of([FAILED_SPAN]), streams=[stream])
        result = self.check(url, "--expect", "500")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("1 at ERROR", result.stdout)

    def test_an_expected_refusal_passes_though_its_security_span_failed(self):
        denied = {"name": "authorize request", "status": {"code": "STATUS_CODE_ERROR"}}
        url, _ = self.start(status=401, trace=trace_of([SERVER_SPAN, denied]))
        result = self.check(url, "--expect", "401")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_an_error_log_behind_an_expected_refusal_fails(self):
        stream = {"stream": {"detected_level": "error"}, "values": [["1", "boom"]]}
        url, _ = self.start(status=401, trace=trace_of([SERVER_SPAN]), streams=[stream])
        result = self.check(url, "--expect", "401")
        self.assertEqual(result.returncode, 1, result.stdout)

    def test_no_trace_fails_even_with_a_good_status(self):
        url, _ = self.start()
        result = self.check(url)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("FAIL     no trace from orders", result.stdout)

    def test_a_trace_from_another_service_does_not_count(self):
        url, _ = self.start(trace=trace_of([SERVER_SPAN], service="billing"))
        result = self.check(url)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("FAIL     no trace from orders", result.stdout)

    def test_trace_mode_reads_a_request_something_else_sent(self):
        url, seen = self.start(trace=trace_of([SERVER_SPAN]))
        result = self.check(url, "--trace", "a" * 32, target=None)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(seen["sent"], [])

    def test_an_app_that_is_down_exits_2(self):
        url, _ = self.start(trace=trace_of([SERVER_SPAN]))
        result = subprocess.run([sys.executable, str(SCRIPT), "--service", "orders", "--tempo", url, "--loki", url,
                                 "http://127.0.0.1:9/api/orders"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("CANNOT RUN  app not reachable", result.stdout)

    def test_a_stack_that_is_down_exits_2(self):
        url, _ = self.start()
        result = subprocess.run([sys.executable, str(SCRIPT), "--service", "orders", "--wait", "0",
                                 "--tempo", "http://127.0.0.1:9", "--loki", "http://127.0.0.1:9", f"{url}/api/orders"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("CANNOT RUN  stack not reachable", result.stdout)


if __name__ == "__main__":
    unittest.main()
