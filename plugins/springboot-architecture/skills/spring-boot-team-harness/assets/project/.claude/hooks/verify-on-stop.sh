#!/usr/bin/env bash
# Claude Code Stop hook. When the code under src or pom.xml differs from what last passed, committed or not, it
# formats the code and runs the gates that need no Docker: compile with NullAway, then the rules,
# configuration-key and module tests. On failure it exits 2, which sends the errors back to Claude to fix before
# the turn ends. The full ./mvnw verify still runs in CI.
set -u
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
input=$(cat)
git rev-parse --git-dir > /dev/null 2>&1 || exit 0

FAST_TESTS="CodeRulesTests,ConfigurationKeysTests,ModuleBoundariesTests,ModularityTests,ArchUnitTests,ArchitectureRulesTest"
STAMPS="$(git rev-parse --git-dir)/harness"
mkdir -p "$STAMPS"
PASSED="$STAMPS/passed"
FAILED="$STAMPS/failed"

code_state() {
  {
    git rev-parse -q --verify HEAD:src 2> /dev/null
    git rev-parse -q --verify HEAD:pom.xml 2> /dev/null
    git diff HEAD -- src pom.xml 2> /dev/null || git diff -- src pom.xml
    git ls-files -o --exclude-standard -- src | while IFS= read -r file; do
      printf '%s\n' "$file"
      cat "$file"
    done
  } | git hash-object --stdin
}

fail() {
  printf '%s\n' "$state" > "$FAILED"
  {
    echo "$1"
    printf '%s\n' "$2" | grep -E '\[ERROR\]|was violated|^(Method|Field|Class|Constructor) <|is defined by no dependency|is deprecated' \
      | grep -vE 'Re-run Maven|-> \[Help|To see the full stack trace|^\[ERROR\] *$' | awk '!seen[$0]++' | head -60
  } >&2
  exit 2
}

state=$(code_state)
[ -f "$PASSED" ] && [ "$(cat "$PASSED")" = "$state" ] && exit 0
# Claude already tried once on this exact code and couldn't fix it: let it stop and report the failure.
if printf '%s' "$input" | grep -q '"stop_hook_active" *: *true' && [ -f "$FAILED" ] && [ "$(cat "$FAILED")" = "$state" ]; then
  exit 0
fi

output=$(./mvnw -q -B spotless:apply 2>&1) \
  || fail "Formatting with ./mvnw spotless:apply failed. Fix the cause, then finish:" "$output"
state=$(code_state)
output=$(./mvnw -q -B test -Dtest="$FAST_TESTS" -Dsurefire.failIfNoSpecifiedTests=false 2>&1) \
  || fail "The harness gates failed on your changes. Fix the cause (don't suppress or skip it), then finish:" "$output"
printf '%s\n' "$state" > "$PASSED"
rm -f "$FAILED"
exit 0
