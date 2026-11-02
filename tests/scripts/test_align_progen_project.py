"""Regression tests for creating-springboot-projects/scripts/align_progen_project.py.

Run from the repository root:
    python3 -m unittest discover -s tests/scripts -v
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = (Path(__file__).resolve().parents[2] / "plugins/springboot-architecture/skills"
          / "creating-springboot-projects/scripts/align_progen_project.py")

AUTH_UTILS = """package com.acme.users;

import org.springframework.security.core.Authentication;

public final class AuthUtils {
    public static Long getCurrentUserId() {
        return null;
    }
}
"""
TOKEN_HELPER = """package com.acme.users;

import jakarta.servlet.http.HttpServletRequest;

public class TokenHelper {
    public String getToken(HttpServletRequest request) {
        return null;
    }

    public String getUsernameFromToken(String token) {
        return null;
    }
}
"""
HANDLER = """package com.acme.config;

import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

class GlobalExceptionHandler {
    private static final Logger LOG = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    ProblemDetail handle(Exception e) {
        return handleException(e, "Internal Server Error", List.of(e.getMessage()), HttpStatus.INTERNAL_SERVER_ERROR);
    }

    private ProblemDetail handleException(Exception e, String title) {
        LOG.error("Error:", e);
        return null;
    }
}
"""
AUTH_CONTROLLER = 'class AuthController { void a() { LOG.info("Login request for email: {}", req.email()); } }\n'
USER_CONTROLLER = 'class UserRestController { void a() { LOG.info("Registration request for email: {}", req.email()); } }\n'


class AlignProgenProjectTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.base = self.root / "src/main/java/com/acme"
        for name, text in (("users/AuthUtils.java", AUTH_UTILS), ("users/TokenHelper.java", TOKEN_HELPER),
                           ("config/GlobalExceptionHandler.java", HANDLER),
                           ("users/AuthController.java", AUTH_CONTROLLER),
                           ("users/UserRestController.java", USER_CONTROLLER)):
            path = self.base / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    def run_script(self):
        return subprocess.run([sys.executable, str(SCRIPT), str(self.root)], capture_output=True, text=True)

    def read(self, name):
        return (self.base / name).read_text(encoding="utf-8")

    def test_every_edit_is_applied(self):
        self.assertEqual(self.run_script().returncode, 0)
        self.assertIn("public static @Nullable Long getCurrentUserId()", self.read("users/AuthUtils.java"))
        helper = self.read("users/TokenHelper.java")
        self.assertEqual(helper.count("public @Nullable String"), 2)
        self.assertEqual(helper.count("import org.jspecify.annotations.Nullable;"), 1)
        handler = self.read("config/GlobalExceptionHandler.java")
        self.assertNotIn("getMessage", handler)
        self.assertNotIn("LOG", handler)
        self.assertNotIn("slf4j", handler)
        self.assertNotIn("email", self.read("users/AuthController.java"))
        self.assertNotIn("email", self.read("users/UserRestController.java"))

    def test_a_second_run_changes_nothing(self):
        self.run_script()
        first = self.read("users/TokenHelper.java") + self.read("config/GlobalExceptionHandler.java")
        result = self.run_script()
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("changed", result.stdout)
        self.assertEqual(first, self.read("users/TokenHelper.java") + self.read("config/GlobalExceptionHandler.java"))

    def test_changed_code_is_reported_and_left_alone(self):
        changed = "class TokenHelper { Optional<String> getToken() { return Optional.empty(); } }\n"
        (self.base / "users/TokenHelper.java").write_text(changed, encoding="utf-8")
        result = self.run_script()
        self.assertEqual(result.returncode, 1)
        self.assertIn("skipped  TokenHelper.java", result.stdout)
        self.assertEqual(self.read("users/TokenHelper.java"), changed)


if __name__ == "__main__":
    unittest.main()
