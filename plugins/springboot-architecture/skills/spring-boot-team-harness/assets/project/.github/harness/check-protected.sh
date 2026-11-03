#!/usr/bin/env bash
# Fails a pull request that changes what the build accepts without saying so. The Claude Code guard hook refuses these
# edits during a session, but it is advisory: a Bash command, another agent or a person can make them anyway. This check
# is the backstop, and it runs the same way for every tool.
#
# Usage: check-protected.sh <base-commit>
# Set HARNESS_RULE_CHANGE=true (the harness-rule-change label on the pull request) to accept the changes on purpose;
# they are still listed, so the reviewer sees them.
#
# A pull request fails when it:
#   - adds lines or files to src/test/resources/archunit_store (removing fixed violations is fine)
#   - adds lines to src/test/resources/modulith_store, or creates it (removing fixed violations is fine)
#   - widens a module's boundary rules in package-info.java: adds to allowedDependencies, removes it, or changes
#     @ApplicationModule otherwise (removing entries from allowedDependencies is fine)
#   - changes archunit.properties
#   - changes or deletes an existing rule test (adding a new one is fine)
#   - changes or deletes a migration that is on the base branch (adding a new one is fine)
#   - changes or deletes the harness hooks, this script or its workflow
#   - stops LogLeakCheck running, by unregistering it or turning off JUnit's extension autodetection

set -u
base=${1:?usage: check-protected.sh <base-commit>}
rule_tests='CodeRulesTests|ConfigurationKeysTests|BuildSetupTests|UnusedCodeTests|ModuleBoundariesTests|ModularityTests|ArchUnitTests|ArchitectureRulesTest|LogLeakCheck'
extensions=META-INF/services/org.junit.jupiter.api.extension.Extension
fork=$(git merge-base "$base" HEAD)
problems=()

problem() {
  problems+=("$1"$'\t'"$2")
}

# log_leak_check_registered <commit> <services-file>
log_leak_check_registered() {
  git show "$1:$2" 2> /dev/null | grep -Eq '^[[:space:]]*[^#[:space:]]+\.LogLeakCheck[[:space:]]*$'
}

# autodetection_on <commit> <properties-file>. The last assignment wins, as in java.util.Properties.
autodetection_on() {
  git show "$1:$2" 2> /dev/null | grep -E '^[[:space:]]*junit\.jupiter\.extensions\.autodetection\.enabled[[:space:]=:]' \
    | tail -1 | grep -Eiq '[[:space:]=:]true[[:space:]]*$'
}

# module_rules <commit> <package-info>: the @ApplicationModule annotation on one line, without whitespace. Other
# annotations between it and the package line, such as @NullMarked, are left out.
module_rules() {
  git show "$1:$2" 2> /dev/null \
    | sed -n '/^[[:space:]]*@\(org\.springframework\.modulith\.\)\{0,1\}ApplicationModule\b/,/^[[:space:]]*package[[:space:]]/p' \
    | sed '$d' | awk 'NR == 1 || !/^[[:space:]]*@/' | tr -d '[:space:]'
}

allowed_value='allowedDependencies=(\{[^}]*\}|"[^"]*")'

# allowed_entries <rules>: the quoted entries of allowedDependencies, one per line, sorted.
allowed_entries() {
  printf '%s' "$1" | grep -oE "$allowed_value" | grep -o '"[^"]*"' | sort -u
}

# plain_names <rules>: true when allowedDependencies holds only quoted module names. A constant, a concatenation, a
# comment or a Unicode escape can name a module that the quoted entries don't show.
plain_names() {
  printf '%s' "$1" | grep -oE "$allowed_value" | sed 's/^allowedDependencies=//' \
    | grep -Eqx '\{("[^"\\]*"(,"[^"\\]*")*,?)?\}|"[^"\\]*"'
}

# narrowed <base-rules> <head-rules>: true when head only drops entries from a non-empty allowedDependencies.
narrowed() {
  local before after
  before=$(allowed_entries "$1")
  after=$(allowed_entries "$2")
  plain_names "$2" && [ -n "$before" ] && [ -n "$after" ] && [ -z "$(comm -13 <(echo "$before") <(echo "$after"))" ] \
    && [ "$(printf '%s' "$1" | sed -E "s/$allowed_value//")" = "$(printf '%s' "$2" | sed -E "s/$allowed_value//")" ]
}

while IFS=$'\t' read -r status path; do
  [ -n "$path" ] || continue
  case "$path" in
    */archunit_store/* | archunit_store/*)
      if [ "$status" = A ]; then
        problem "$path" "records rule violations as accepted. Fix the violation instead."
      elif [ "$status" = M ] && [ "$(git diff --numstat "$base"...HEAD -- "$path" | cut -f1)" != 0 ]; then
        problem "$path" "adds entries to the ArchUnit freeze record, which accepts new violations. Fix them instead."
      fi ;;
    */modulith_store | modulith_store)
      if [ "$status" = A ]; then
        problem "$path" "records module-boundary violations as accepted. Fix the violation instead."
      elif [ "$status" = M ] && [ "$(git diff --numstat "$base"...HEAD -- "$path" | cut -f1)" != 0 ]; then
        problem "$path" "adds entries to the module-boundary record, which accepts new violations. Fix them instead."
      fi ;;
    */package-info.java)
      before=$(module_rules "$fork" "$path")
      if [ -n "$before" ] && [ "$status" != A ]; then
        after=$(module_rules HEAD "$path")
        [ "$before" = "$after" ] || narrowed "$before" "$after" \
          || problem "$path" "changes the module's boundary rules (allowedDependencies or its type), which lets new dependencies through."
      fi ;;
    */archunit.properties | archunit.properties)
      problem "$path" "changes how the ArchUnit freeze record works." ;;
    */db/migration/*)
      [ "$status" = A ] || problem "$path" "is on the base branch, so it may already have run; Flyway fails when its checksum changes. Add a new migration instead." ;;
    */"$extensions")
      if log_leak_check_registered "$fork" "$path" && ! log_leak_check_registered HEAD "$path"; then
        problem "$path" "stops LogLeakCheck running, so nothing fails on personal data in logs."
      fi ;;
    */junit-platform.properties)
      if log_leak_check_registered "$fork" "${path%/*}/$extensions" && autodetection_on "$fork" "$path" \
        && ! autodetection_on HEAD "$path"; then
        problem "$path" "turns off extension autodetection, which stops LogLeakCheck running."
      fi ;;
    .claude/hooks/* | .github/harness/* | .github/workflows/harness-integrity.yml)
      problem "$path" "is part of the harness's own enforcement." ;;
    *)
      if [ "$status" != A ] && printf '%s' "${path##*/}" | grep -Eqx "($rule_tests)\.java"; then
        problem "$path" "holds the team's build rules; changing it changes what every build accepts."
      fi ;;
  esac
done < <(git diff --name-status --no-renames "$base"...HEAD) || true

if [ ${#problems[@]} -eq 0 ]; then
  echo "Harness integrity: no protected files changed."
  exit 0
fi

level=error
[ "${HARNESS_RULE_CHANGE:-false}" = true ] && level=warning
for entry in "${problems[@]}"; do
  echo "::$level file=${entry%%$'\t'*}::${entry%%$'\t'*} ${entry#*$'\t'}"
done
if [ "$level" = warning ]; then
  echo "Harness integrity: ${#problems[@]} protected file(s) changed, accepted by the harness-rule-change label."
  exit 0
fi
echo "Harness integrity: ${#problems[@]} protected file(s) changed. If the change is intended, a maintainer adds the" \
  "harness-rule-change label to the pull request."
exit 1
