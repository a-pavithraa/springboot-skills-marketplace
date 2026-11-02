"""Regression tests for tests/fixtures/scenario-27/telemetry.py.

Run from the repository root:
    python3 -m unittest discover -s tests/scripts -v
"""

import json
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "fixtures/scenario-27/telemetry.py"
TRACEPARENT = re.compile(r"00-([0-9a-f]{32})-[0-9a-f]{16}-01")


def line(level: str, message: str, trace_id: str | None = None, stack: str | None = None) -> dict:
    entry = {"@timestamp": "2026-10-31T00:00:00Z", "level": level, "logger_name": "com.acme.App",
             "thread_name": "main", "message": message}
    if trace_id:
        entry["traceId"] = trace_id
    if stack:
        entry["stack_trace"] = stack
    return entry


class FakeApp(BaseHTTPRequestHandler):
    """Answers like the verify profile: writes a line carrying the caller's trace id."""

    def do_GET(self):
        trace_id = TRACEPARENT.fullmatch(self.headers["traceparent"]).group(1)
        status, entries = self.server.routes.get(self.path, (200, []))
        if self.server.logging:
            self.server.write(line("DEBUG", "Completed", trace_id))
            for level, message, stack in entries:
                self.server.write(line(level, message, trace_id, stack))
        self.send_response(status)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *_):
        pass


class TelemetryTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.log = Path(directory.name) / "app.jsonl"
        self.log.write_text("", encoding="utf-8")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeApp)
        self.server.routes = {}
        self.server.logging = True
        self.server.write = self.write
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.app = f"http://127.0.0.1:{self.server.server_address[1]}"

    def write(self, entry: dict):
        with self.log.open("a", encoding="utf-8") as file:
            file.write(json.dumps(entry) + "\n")

    def run_tool(self, *args: str) -> tuple[int, str]:
        done = subprocess.run([sys.executable, str(SCRIPT), "--app", self.app, "--log", str(self.log), "--timeout", "1",
                               *args], capture_output=True, text=True)
        return done.returncode, done.stdout

    def test_doctor_passes_when_a_request_reaches_the_log(self):
        code, output = self.run_tool("doctor")
        self.assertEqual(code, 0, output)

    def test_doctor_reports_no_telemetry_when_the_app_does_not_log_the_trace(self):
        self.server.logging = False
        code, output = self.run_tool("doctor")
        self.assertEqual(code, 4)
        self.assertIn("do", json.loads(output))

    def test_doctor_reports_no_telemetry_when_nothing_answers(self):
        self.app = "http://127.0.0.1:1"
        code, _ = self.run_tool("doctor")
        self.assertEqual(code, 4)

    def test_call_passes_on_a_clean_request(self):
        code, output = self.run_tool("call", "--settle", "0", "GET", "/ok")
        self.assertEqual(code, 0, output)
        self.assertTrue(json.loads(output)["ok"])

    def test_call_fails_a_200_with_an_error_line(self):
        self.server.routes["/swallow"] = (200, [("ERROR", "fell back", "java.lang.IllegalStateException: x\n\tat a")])
        code, output = self.run_tool("call", "--settle", "0", "GET", "/swallow")
        result = json.loads(output)
        self.assertEqual((code, result["status"]), (1, 200))
        self.assertEqual(result["errors"][0]["stack"][0], "java.lang.IllegalStateException: x")

    def test_call_fails_a_500(self):
        self.server.routes["/down"] = (500, [])
        code, _ = self.run_tool("call", "--settle", "0", "GET", "/down")
        self.assertEqual(code, 1)

    def test_call_without_log_lines_is_no_telemetry_not_a_pass(self):
        self.server.logging = False
        code, _ = self.run_tool("call", "--settle", "0", "GET", "/ok")
        self.assertEqual(code, 4)

    def test_logs_filters_by_level_and_counts_the_rest(self):
        self.write(line("DEBUG", "noise", "a" * 32))
        self.write(line("WARN", "slow", "a" * 32))
        code, output = self.run_tool("logs", "a" * 32, "--level", "WARN")
        result = json.loads(output)
        self.assertEqual((code, result["total"], len(result["lines"])), (0, 2, 1))

    def test_logs_of_an_unknown_trace_is_no_telemetry(self):
        code, _ = self.run_tool("logs", "b" * 32)
        self.assertEqual(code, 4)

    def test_errors_needs_a_mark(self):
        code, output = self.run_tool("errors")
        self.assertEqual(code, 4)
        self.assertIn("mark", json.loads(output)["do"])

    def test_errors_ignores_what_came_before_the_mark(self):
        self.write(line("ERROR", "startup"))
        self.run_tool("mark")
        code, output = self.run_tool("errors")
        self.assertEqual(code, 0, output)

    def test_errors_finds_a_line_with_no_trace_id_and_groups_repeats(self):
        self.run_tool("mark")
        self.write(line("ERROR", "order 1234 failed"))
        self.write(line("ERROR", "order 5678 failed"))
        code, output = self.run_tool("errors")
        result = json.loads(output[:output.rindex("telemetry:")])
        self.assertEqual(code, 1)
        self.assertEqual([(group["count"], group["traceId"]) for group in result["groups"]], [(2, None)])
        self.assertIn("telemetry: scanned=2 error_groups=1 warn_groups=0", output)

    def test_warnings_alone_do_not_fail_errors(self):
        self.run_tool("mark")
        self.write(line("WARN", "slow"))
        code, output = self.run_tool("errors")
        self.assertEqual(code, 0, output)

    def test_errors_reads_the_whole_log_after_rotation(self):
        self.write(line("INFO", "padding" * 10))
        self.run_tool("mark")
        self.log.write_text(json.dumps(line("ERROR", "x")) + "\n", encoding="utf-8")
        code, _ = self.run_tool("errors")
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
