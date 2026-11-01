#!/usr/bin/env python3
"""Align a new progen project with the harness rules, before the harness gates run on it.

  python3 align_progen_project.py /path/to/project

Each edit matches exact generated text: an edit that no longer matches is reported and skipped, because a later
progen may generate different code.
Run it on a new project only. Exit codes: 0 every edit applied or already done, 1 at least one didn't match.
"""

import re
import sys
from pathlib import Path

NULLABLE_IMPORT = "import org.jspecify.annotations.Nullable;\n"
NULLABLE_RETURNS = {
    "AuthUtils.java": ("public static Long getCurrentUserId()",),
    "TokenHelper.java": ("public String getToken(HttpServletRequest request)",
                         "public String getUsernameFromToken(String token)"),
}
EMAIL_LOGS = {
    "AuthController.java": ('LOG.info("Login request for email: {}", req.email());', 'LOG.info("Login request");'),
    "UserRestController.java": ('LOG.info("Registration request for email: {}", req.email());',
                                'LOG.info("Registration request");'),
}
CATCH_ALL = re.compile(r'return handleException\(e, "Internal Server Error", List\.of\(e\.getMessage\(\)\),\s*'
                       r'HttpStatus\.INTERNAL_SERVER_ERROR\);')
GENERIC_RESPONSE = ('return ProblemDetail.forStatusAndDetail(HttpStatus.INTERNAL_SERVER_ERROR, '
                    '"Something went wrong");')
DUPLICATE_LOG = '        LOG.error("Error:", e);\n'
HANDLER_LOGGER = '    private static final Logger LOG = LoggerFactory.getLogger(GlobalExceptionHandler.class);\n\n'
HANDLER_IMPORTS = "import org.slf4j.Logger;\nimport org.slf4j.LoggerFactory;\n"


def nullable_returns(text: str, signatures: tuple[str, ...]) -> tuple[str, list[str]]:
    missed = []
    for signature in signatures:
        declared = re.sub(r"(public (?:static )?)", r"\1@Nullable ", signature, count=1)
        if signature in text:
            text = text.replace(signature, declared)
        elif declared not in text:
            missed.append(signature)
    if "@Nullable" in text and NULLABLE_IMPORT not in text:
        text = re.sub(r"^import (?!static)", NULLABLE_IMPORT + "import ", text, count=1, flags=re.M)
    return text, missed


def replaced(text: str, old: str, new: str) -> tuple[str, list[str]]:
    if old in text:
        return text.replace(old, new), []
    return text, [] if new in text else [old]


def safe_handler(text: str) -> tuple[str, list[str]]:
    if GENERIC_RESPONSE in text:
        return text, []
    if not CATCH_ALL.search(text):
        return text, ["the catch-all handler"]
    text = CATCH_ALL.sub(GENERIC_RESPONSE, text)
    for line in (DUPLICATE_LOG, HANDLER_LOGGER, HANDLER_IMPORTS):
        text = text.replace(line, "")
    return text, []


def fix(project: Path) -> int:
    sources = {path.name: path for path in (project / "src" / "main" / "java").rglob("*.java")}
    fixes = {name: (lambda text, wanted=signatures: nullable_returns(text, wanted))
             for name, signatures in NULLABLE_RETURNS.items()}
    fixes |= {name: (lambda text, edit=edit: replaced(text, *edit)) for name, edit in EMAIL_LOGS.items()}
    fixes["GlobalExceptionHandler.java"] = safe_handler
    skipped = 0
    for name, apply_fix in fixes.items():
        path = sources.get(name)
        if path is None:
            print(f"skipped  {name} (not found)")
            skipped += 1
            continue
        original = path.read_text(encoding="utf-8")
        text, missed = apply_fix(original.replace("\r\n", "\n"))
        if text != original.replace("\r\n", "\n"):
            path.write_text(text, encoding="utf-8", newline="\n")
            print(f"changed  {path.relative_to(project).as_posix()}")
        for item in missed:
            print(f"skipped  {name}: no match for {item}")
            skipped += 1
    return 1 if skipped else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(fix(Path(sys.argv[1]).resolve()))
