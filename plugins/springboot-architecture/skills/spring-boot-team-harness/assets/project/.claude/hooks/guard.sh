#!/usr/bin/env bash
# PreToolUse hook for Claude Code and Codex. Refuses actions the team never wants an agent to take: it prints a deny
# decision as JSON, which both tools honour and show to the agent. Codex 0.166 let an apply_patch edit through on exit 2.
#
# Each refusal appends one JSON line to .git/harness/events.jsonl (time, session, rule; no command or path), which the
# harness's report.py summarises.
set -u
input=$(cat)
# Codex sets no project folder variable and runs hooks in the session's folder, which can be a subfolder.
root=${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2> /dev/null || pwd)}
rule_tests='CodeRulesTests|ConfigurationKeysTests|BuildSetupTests|UnusedCodeTests|ModuleBoundariesTests|ModularityTests|ArchUnitTests|ArchitectureRulesTest|LogLeakCheck'

# block <reason> <rule>
block() {
  local dir session
  if dir=$(cd "$root" 2> /dev/null && git rev-parse --absolute-git-dir 2> /dev/null); then
    session=$(printf '%s' "$input" | grep -o '"session_id" *: *"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/' \
      | tr -cd 'A-Za-z0-9_-')
    mkdir -p "$dir/harness" 2> /dev/null && printf '{"ts":"%s","hook":"guard","session":"%s","result":"refused","rule":"%s"}\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${session:-unknown}" "$2" >> "$dir/harness/events.jsonl" 2> /dev/null
  fi
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' \
    "$(printf '%s' "Blocked by the team harness: $1" | sed 's/\\/\\\\/g; s/"/\\"/g')"
  exit 0
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
  printf '%s' "$command" | grep -Eq 'allowStoreCreation=true|freeze\.refreeze=true|modulith\.store\.record=true|harness\.record=true' \
    && block "that setting records today's ArchUnit or Spring Modulith violations as accepted. Fix the violation instead; to record a baseline on purpose, ask the user to run the harness's baseline.py." archunit-record
  # Writing commands that name a protected file. Not exhaustive: the Harness integrity CI check is the backstop.
  printf '%s' "$command" | grep -Eq "archunit_store|modulith_store|archunit\.properties|package-info\.java|($rule_tests)\.java" \
    && printf '%s' "$command" | grep -Eq '(^|[^0-9&])>|(^|[[:space:];&|])(sed|perl)([[:space:]]+-[^[:space:]]+)*[[:space:]]+(-[a-zA-Z]*i|--in-place)|(^|[[:space:];&|])(tee|truncate|rm|mv|cp|python3?|node|ruby)([[:space:]]|$)' \
    && block "that command writes to a file holding the team's build rules or a record of tolerated violations. Fix the code the rule reports. To change a rule, ask the user." bash-protected-file
  exit 0
fi

# check_path <path>: refuses an edit to a protected file, and returns when the edit is fine.
check_path() {
  local path=$1 relative ref
  case "$path" in
    /* | [A-Za-z]:/*) ;;
    *) path="$PWD/$path" ;;
  esac
  case "$path" in
    */archunit_store/*)
      block "src/test/resources/archunit_store records the rule violations that existed before the harness, so they're frozen. Fix the new violation instead. To accept one on purpose, ask the user." archunit-store ;;
    */modulith_store)
      block "src/test/resources/modulith_store records the module-boundary violations that existed before the harness, so they're tolerated. Fix the new violation instead. To accept one on purpose, ask the user." modulith-store ;;
    */archunit.properties)
      block "archunit.properties sets how the freeze record works; with store creation allowed, new violations would be recorded as accepted. Fix the violation instead, or ask the user." archunit-properties ;;
    */CodeRulesTests.java | */ConfigurationKeysTests.java | */BuildSetupTests.java | */UnusedCodeTests.java | */ModuleBoundariesTests.java \
      | */ModularityTests.java | */ArchUnitTests.java | */ArchitectureRulesTest.java | */LogLeakCheck.java)
      [ -e "$path" ] && block "${path##*/} holds the team's build rules, and a change to it changes what every developer's build accepts. Fix the code the rule reports. To change a rule, ask the user." rule-test
      return 0 ;;
    */package-info.java)
      # A module's allowedDependencies and type are its boundary rules: widening them would get any breach past the
      # boundary test. Telling a widening edit from a harmless one takes parsing Java, so every edit to a module's
      # package-info.java is refused; creating one for a new module is fine.
      [ -e "$path" ] && grep -q 'ApplicationModule' "$path" \
        && block "${path%/*}/package-info.java declares the module's boundary rules (allowedDependencies, OPEN). Call the other module through an allowed dependency, or ask the user to change the rule." module-rules
      return 0 ;;
    */db/migration/*.sql) ;;
    *) return 0 ;;
  esac

  relative=$(git -C "$root" ls-files --full-name -- "$path" 2> /dev/null)
  [ -n "$relative" ] || return 0
  for ref in origin/main origin/master main master; do
    if git -C "$root" rev-parse --verify -q "$ref" > /dev/null; then
      git -C "$root" cat-file -e "$ref:$relative" 2> /dev/null \
        && block "$relative is on $ref, so it may already have run on a shared database, and Flyway fails when its checksum changes. Write a new migration instead (see the db-migration skill)." applied-migration
      return 0
    fi
  done
}

# Codex edits files with apply_patch: the patch text names each file it updates, deletes or moves to. Adding a file
# passes, as Write does for a file that doesn't exist yet.
if printf '%s' "$input" | grep -q '"tool_name" *: *"apply_patch"'; then
  # The patch is a JSON string: an escaped backslash in a Windows path becomes /, then each \n ends a line.
  printf '%s' "$input" | awk '{ gsub(/\\\\/, "/"); gsub(/\\n/, "\n"); print }' \
    | sed -n -E 's/^\*\*\* (Update File|Delete File|Move to): (.*[^[:space:]])[[:space:]]*$/\2/p' \
    | while IFS= read -r file; do
      check_path "$file"
    done
  exit $?
fi

path=$(printf '%s' "$input" | grep -o '"file_path" *: *"[^"]*"' | head -1 | sed 's/.*: *"//; s/"$//; s#\\\\#/#g')
[ -n "$path" ] && check_path "$path"
exit 0
