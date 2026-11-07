#!/usr/bin/env bash
# Claude Code and Codex hook that checks the agent's own changes before a turn ends.
#
#   verify-on-stop.sh --session-start [folder]   SessionStart: records the code the session starts from.
#   verify-on-stop.sh [folder]                   Stop: if this session changed the code, formats it (checks it on
#                                                Spring Java Format) and runs the gates that need no Docker (compile
#                                                with NullAway, then the rules, configuration-key and module tests).
#
# It blocks the turn only on errors in files this session changed, so the agent fixes its own mistakes and
# never code it didn't touch. When the build fails only elsewhere, it tells the user the change couldn't be fully
# verified. The full build still runs in CI. folder is the Maven or Gradle project, relative to the repository root.
#
# Each run appends one JSON line to .git/harness/events.jsonl (time, session, result, gates, seconds, number of changed
# files; no paths or contents), which the harness's report.py summarises.
set -u
start=false
if [ "${1:-}" = "--session-start" ]; then
  start=true
  shift
fi
# Codex sets no project folder variable and runs hooks in the session's folder, which can be a subfolder.
cd "${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2> /dev/null || pwd)}/${1:-.}" || exit 0
input=$(cat)
git rev-parse --git-dir > /dev/null 2>&1 || exit 0

FAST_TESTS="CodeRulesTests,ConfigurationKeysTests,BuildSetupTests,ModuleBoundariesTests,ModularityTests,ArchUnitTests,ArchitectureRulesTest"
# gradle/harness.gradle holds the same gates for a Gradle build, and harnessCheck runs FAST_TESTS there.
if [ ! -f pom.xml ] && { [ -f build.gradle ] || [ -f build.gradle.kts ]; }; then
  GRADLE=true
  VERIFY="./gradlew build"
  BUILD_FILES="build.gradle build.gradle.kts settings.gradle settings.gradle.kts gradle/libs.versions.toml gradle/harness.gradle"
  # How BuildSetupTests names the build file in its messages.
  BUILD_FILE_LINE='build\.gradle(\.kts)?: '
else
  GRADLE=false
  VERIFY="./mvnw verify"
  BUILD_FILES="pom.xml"
  BUILD_FILE_LINE='pom\.xml: '
fi
STAMPS="$(git rev-parse --git-dir)/harness"
mkdir -p "$STAMPS"
session=$(printf '%s' "$input" | grep -o '"session_id" *: *"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
SESSION="$STAMPS/session-${session:-unknown}"
START="$STAMPS/start-${session:-unknown}"
PASSED="$STAMPS/passed"
FAILED="$STAMPS/failed"
EVENTS="$STAMPS/events.jsonl"

# record <result> [gates] [changed files]: one line per run, capped at the last 2000.
record() {
  printf '{"ts":"%s","hook":"stop","session":"%s","result":"%s","gates":"%s","seconds":%d,"files":%d}\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(printf '%s' "${session:-unknown}" | tr -cd 'A-Za-z0-9_-')" "$1" "${2:-}" \
    "$SECONDS" "${3:-0}" >> "$EVENTS" 2> /dev/null || return 0
  if [ "$(wc -l < "$EVENTS")" -gt 2500 ]; then
    tail -n 2000 "$EVENTS" > "$EVENTS.tmp" && mv "$EVENTS.tmp" "$EVENTS"
  fi
}

# Which gates a set of diagnostics comes from.
gates() {
  local text
  text=$(cat)
  {
    printf '%s\n' "$text" | grep -q '\[NullAway\]' && echo nullaway
    printf '%s\n' "$text" | grep -qE 'was violated|^[[:space:]]*(Method|Field|Class|Constructor) <|CodeRulesTests' && echo rules
    printf '%s\n' "$text" | grep -qE 'is defined by no dependency|is deprecated|ConfigurationKeysTests' && echo config-keys
    printf '%s\n' "$text" | grep -qE "$BUILD_FILE_LINE|lets Hibernate change the schema|writes Flyway|BuildSetupTests" && echo build-setup
    printf '%s\n' "$text" | grep -qE 'ModuleBoundariesTests|ModularityTests|Modulith' && echo modules
    printf '%s\n' "$text" | grep -v '\[NullAway\]' | grep -qE '\[ERROR\] .*\.java:\[[0-9]+|\.java:[0-9]+: error:' && echo compile
  } | paste -sd, -
}

# One line per file under src plus the build files, committed or not: "<content hash> <path>".
manifest() {
  local files
  # shellcheck disable=SC2086 # BUILD_FILES is a list of paths without spaces.
  files=$(git ls-files -co --exclude-standard -- src $BUILD_FILES | sort -u | while IFS= read -r file; do
    [ -f "$file" ] && printf '%s\n' "$file"
  done)
  [ -n "$files" ] || return 0
  # --stdin-paths reads paths from the repository root, not from this folder.
  paste -d ' ' <(printf '%s\n' "$files" | sed "s#^#$(git rev-parse --show-prefix)#" | git hash-object --stdin-paths) \
    <(printf '%s\n' "$files")
}

current=$(manifest)
if $start || [ ! -f "$SESSION" ]; then
  printf '%s\n' "$current" > "$SESSION"
  # The commit the session starts from, so the file-size check still treats a file the session commits as new.
  git rev-parse -q --verify HEAD > "$START" || rm -f "$START"
  ls -t "$STAMPS"/session-* 2> /dev/null | tail -n +21 | while IFS= read -r old; do
    rm -f "$old" "$STAMPS/start-${old##*/session-}"
  done
  if $start; then
    record started
    exit 0
  fi
  # The session began before the hooks were installed, or its starting point was pruned: this turn's changes are
  # unknown, so say so instead of passing them silently. Later turns compare with what this turn left.
  record no-baseline
  echo '{"systemMessage": "Harness: this session has no recorded starting point, so this turn'"'"'s changes were not checked. Later turns are. Run '"$VERIFY"' to check them now."}'
  exit 0
fi
# Pruning keeps the 20 most recently used session files, so a long session isn't pruned while it runs.
touch "$SESSION"
if [ "$(cat "$SESSION")" = "$current" ]; then
  record no-change
  exit 0
fi

state=$(printf '%s\n' "$current" | git hash-object --stdin)
if [ -f "$PASSED" ] && [ "$(cat "$PASSED")" = "$state" ]; then
  record already-passed
  exit 0
fi
# Claude already tried once on this exact code and couldn't fix it: let it stop and report the failure.
if printf '%s' "$input" | grep -q '"stop_hook_active" *: *true' && [ -f "$FAILED" ] && [ "$(cat "$FAILED")" = "$state" ]; then
  record gave-up
  exit 0
fi

# Gradle indents test failures, and repeats compiler errors indented under "What went wrong".
errors() {
  sed 's/^[[:space:]]*//' \
    | grep -E "\[ERROR\]|\.java:[0-9]+: error:|was violated|^(Method|Field|Class|Constructor) <|is defined by no dependency|is deprecated|$BUILD_FILE_LINE|lets Hibernate change the schema|writes Flyway" \
    | grep -vE 'Re-run Maven|-> \[Help|To see the full stack trace|^\[ERROR\] *$|^\[ERROR\] +[A-Za-z_$][A-Za-z0-9_$]*\.[A-Za-z_$][A-Za-z0-9_$]*:[0-9]+ ' \
    | awk '!seen[$0]++'
}

block() {
  printf '%s\n' "$state" > "$FAILED"
  record blocked "$3" "$count"
  { echo "$1"; printf '%s\n' "$2" | head -60; } \
    | awk 'BEGIN { ORS = ""; printf "{\"decision\":\"block\",\"reason\":\"" }
           { gsub(/\r/, ""); gsub(/\\/, "\\\\"); gsub(/"/, "\\\""); gsub(/\t/, "\\t"); if (NR > 1) print "\\n"; print }
           END { print "\"}\n" }'
  exit 0
}

# The session owns the files that differ from its starting point before formatting, so a legacy file that Spotless
# would touch never becomes the session's.
changed=$(diff <(cat "$SESSION") <(printf '%s\n' "$current") | sed -n 's/^[<>] [0-9a-f]* //p' | sort -u | grep . || true)
count=$(printf '%s\n' "$changed" | grep -c . || true)

# Spotless matches these regexes against absolute paths: only the session's Java files get formatted.
# The case loops live in functions because Bash 3.2, the macOS default, can't parse case inside $( ).
format_patterns() {
  while IFS= read -r file; do
    case "$file" in
      *.java) [ -f "$file" ] && printf '.*%s\n' "$(printf '%s' "$file" | sed 's/[.^$*+?()[{|\\]/\\&/g; s#/#[\\\\/]#g')" ;;
    esac
  done
}
to_format=$(printf '%s\n' "$changed" | format_patterns | paste -sd, -)
session_unformatted() {
  printf '%s\n' "$changed" | grep '\.java$' | while IFS= read -r file; do
    printf '%s\n' "$1" | tr '\\' '/' | grep -F "$file"
  done
}
# Gradle's Spotless takes the session's files by path, through the harness script's harnessFiles property.
java_files=$(printf '%s\n' "$changed" | grep '\.java$' | while IFS= read -r file; do
  [ -f "$file" ] && printf '%s\n' "$file"
done | paste -sd, -)
if $GRADLE; then
  if [ -z "$java_files" ]; then
    :
  # apply_harness.py resolved the formatter, catalog aliases included, and configured Spotless only for it.
  elif ! grep -Eqs '^[[:space:]]*spotless[[:space:]]*\{' gradle/harness.gradle; then
    if ! output=$(./gradlew -q checkFormat 2>&1); then
      mine=$(session_unformatted "$output")
      [ -z "$mine" ] || block "Code isn't formatted. Run ./gradlew format, then finish:" "$mine" format
    fi
  else
    output=$(./gradlew -q spotlessApply -PharnessFiles="$java_files" 2>&1) \
      || block "Formatting with ./gradlew spotlessApply failed. Fix the cause, then finish:" \
        "$(printf '%s\n' "$output" | errors)" format
  fi
elif [ -n "$to_format" ] && grep -Eq '<artifactId>[[:space:]]*spring-javaformat-maven-plugin' pom.xml 2> /dev/null; then
  # Spring Java Format formats the whole project or nothing, so the session's files are only checked.
  if ! output=$(./mvnw -q -B spring-javaformat:validate 2>&1); then
    mine=$(session_unformatted "$output")
    [ -z "$mine" ] || block "Code isn't formatted. Run ./mvnw spring-javaformat:apply, then finish:" "$mine" format
  fi
elif [ -n "$to_format" ]; then
  output=$(./mvnw -q -B spotless:apply -DspotlessFiles="$to_format" 2>&1) \
    || block "Formatting with ./mvnw spotless:apply failed. Fix the cause, then finish:" "$(printf '%s\n' "$output" | errors)" \
      format
fi
state=$(manifest | git hash-object --stdin)
size_check="$(git rev-parse --show-toplevel)/.github/harness/check-file-size.sh"
started=$(cat "$START" 2> /dev/null)
if [ -f "$size_check" ] && ! output=$(printf '%s\n' "$changed" | bash "$size_check" "${started:-HEAD}" -); then
  block "The file-size check failed on files you changed. Fix them as it says, then finish:" "$output" file-size
fi
if $GRADLE; then
  run_gates() { ./gradlew -q harnessCheck; }
else
  run_gates() { ./mvnw -q -B test -Dtest="$FAST_TESTS" -Dsurefire.failIfNoSpecifiedTests=false; }
fi
if output=$(run_gates 2>&1); then
  printf '%s\n' "$state" > "$PASSED"
  rm -f "$FAILED"
  record passed "" "$count"
  exit 0
fi

# How a diagnostic names a file: compiler errors by path, ArchUnit by class name, other checks by file name.
names() {
  while IFS= read -r file; do
    case "$file" in
      src/main/java/*.java | src/test/java/*.java)
        class=$(printf '%s' "$file" | sed -E 's#^src/(main|test)/java/##; s#\.java$##; s#/#.#g')
        printf '%s\n<%s.\n<%s>\n<%s$\n' "$file" "$class" "$class" "$class" ;;
      *.java) printf '%s\n' "$file" ;;
      pom.xml | build.gradle | build.gradle.kts) printf '%s: \n' "$file" ;;
      *) printf '%s:\n' "${file##*/}" ;;
    esac
  done
}
owned=$(printf '%s\n' "$changed" | names)
found=$(printf '%s\n' "$output" | errors)
mine=$( [ -n "$owned" ] && printf '%s\n' "$found" | grep -F -f <(printf '%s\n' "$owned") || true)
if [ -n "$mine" ]; then
  block "The harness gates failed on code you changed. Fix the cause (don't suppress or skip it), then finish:" \
    "$(printf '%s\n' "$found" | grep -F -e 'was violated' -f <(printf '%s\n' "$mine"))" "$(printf '%s\n' "$mine" | gates)"
fi
printf '%s\n' "$state" > "$FAILED"
record unverified "$(printf '%s\n' "$output" | gates)" "$count"
# shellcheck disable=SC2086 # BUILD_FILES is a list of paths without spaces.
build_change=$(printf '%s\n' "$changed" | grep -xF -f <(printf '%s\n' $BUILD_FILES) | head -1)
if [ "$build_change" = pom.xml ]; then
  echo '{"systemMessage": "Harness: this session changed pom.xml and the build now fails only in files the session did not change. The change could not be fully verified: check whether the pom change caused it with ./mvnw verify."}'
elif [ -n "$build_change" ]; then
  echo '{"systemMessage": "Harness: this session changed '"$build_change"' and the build now fails only in files the session did not change. The change could not be fully verified: check whether that change caused it with '"$VERIFY"'."}'
else
  echo '{"systemMessage": "Harness: the build already fails on code this session did not change, so the change could not be fully verified. Run '"$VERIFY"' to see the failures."}'
fi
exit 0
