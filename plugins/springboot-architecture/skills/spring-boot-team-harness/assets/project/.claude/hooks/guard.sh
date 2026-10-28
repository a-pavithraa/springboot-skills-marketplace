#!/usr/bin/env bash
# Claude Code PreToolUse hook. Refuses actions the team never wants an agent to take; exit 2 blocks the tool call
# and shows the reason to Claude.
#
# Each refusal appends one JSON line to .git/harness/events.jsonl (time, session, rule; no command or path), which the
# harness's report.py summarises.
set -u
input=$(cat)
rule_tests='CodeRulesTests|ConfigurationKeysTests|BuildSetupTests|UnusedCodeTests|ModuleBoundariesTests|ModularityTests|ArchUnitTests|ArchitectureRulesTest'

# block <reason> <rule>
block() {
  local dir session
  if dir=$(cd "${CLAUDE_PROJECT_DIR:-.}" 2> /dev/null && git rev-parse --absolute-git-dir 2> /dev/null); then
    session=$(printf '%s' "$input" | grep -o '"session_id" *: *"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/' \
      | tr -cd 'A-Za-z0-9_-')
    mkdir -p "$dir/harness" 2> /dev/null && printf '{"ts":"%s","hook":"guard","session":"%s","result":"refused","rule":"%s"}\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${session:-unknown}" "$2" >> "$dir/harness/events.jsonl" 2> /dev/null
  fi
  echo "Blocked by the team harness: $1" >&2
  exit 2
}

if printf '%s' "$input" | grep -q '"tool_name" *: *"Bash"'; then
  command=$(printf '%s' "$input" | grep -oE '"command" *: *"(\\.|[^"\\])*"' | head -1 \
    | sed -E 's/^"command" *: *"//; s/"$//; s/\\"/"/g; s/\\\\/\\/g')
  printf '%s' "$command" | grep -Eq 'git[[:space:]].*push([[:space:]].*)?[[:space:]](--force|-f)([[:space:]]|$)' \
    && block "force-pushing rewrites shared history. Push normally, or ask the user to force-push themselves." force-push
  printf '%s' "$command" | grep -Eq 'git[[:space:]].*reset([[:space:]].*)?[[:space:]]--hard' \
    && block "git reset --hard discards uncommitted work. Use git stash, or ask the user." reset-hard
  printf '%s' "$command" | grep -Eq 'git[[:space:]].*clean([[:space:]].*)?[[:space:]]-[a-zA-Z]*f' \
    && block "git clean -f deletes untracked files for good. Ask the user." clean-force
  printf '%s' "$command" | grep -Eq 'allowStoreCreation=true|freeze\.refreeze=true' \
    && block "that setting records today's ArchUnit violations as accepted. Fix the violation instead; to record a baseline on purpose, ask the user to run the harness's baseline.py." archunit-record
  # Writing commands that name a protected file. Not exhaustive: the Harness integrity CI check is the backstop.
  printf '%s' "$command" | grep -Eq "archunit_store|archunit\.properties|($rule_tests)\.java" \
    && printf '%s' "$command" | grep -Eq '(^|[^0-9&])>|(^|[[:space:];&|])(sed|perl)([[:space:]]+-[^[:space:]]+)*[[:space:]]+(-[a-zA-Z]*i|--in-place)|(^|[[:space:];&|])(tee|truncate|rm|mv|cp|python3?|node|ruby)([[:space:]]|$)' \
    && block "that command writes to a file holding the team's build rules or the ArchUnit freeze record. Fix the code the rule reports. To change a rule, ask the user." bash-protected-file
  exit 0
fi

path=$(printf '%s' "$input" | grep -o '"file_path" *: *"[^"]*"' | head -1 | sed 's/.*: *"//; s/"$//; s#\\\\#/#g')
case "$path" in
  */archunit_store/*)
    block "src/test/resources/archunit_store records the rule violations that existed before the harness, so they're frozen. Fix the new violation instead. To accept one on purpose, ask the user." archunit-store ;;
  */archunit.properties)
    block "archunit.properties sets how the freeze record works; with store creation allowed, new violations would be recorded as accepted. Fix the violation instead, or ask the user." archunit-properties ;;
  */CodeRulesTests.java | */ConfigurationKeysTests.java | */BuildSetupTests.java | */UnusedCodeTests.java | */ModuleBoundariesTests.java \
    | */ModularityTests.java | */ArchUnitTests.java | */ArchitectureRulesTest.java)
    [ -e "$path" ] && block "${path##*/} holds the team's build rules, and a change to it changes what every developer's build accepts. Fix the code the rule reports. To change a rule, ask the user." rule-test
    exit 0 ;;
  */db/migration/*.sql) ;;
  *) exit 0 ;;
esac

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
relative=$(git ls-files --full-name -- "$path" 2>/dev/null)
[ -n "$relative" ] || exit 0
for ref in origin/main origin/master main master; do
  if git rev-parse --verify -q "$ref" > /dev/null; then
    git cat-file -e "$ref:$relative" 2> /dev/null \
      && block "$relative is on $ref, so it may already have run on a shared database, and Flyway fails when its checksum changes. Write a new migration instead (see the db-migration skill)." applied-migration
    exit 0
  fi
done
exit 0
