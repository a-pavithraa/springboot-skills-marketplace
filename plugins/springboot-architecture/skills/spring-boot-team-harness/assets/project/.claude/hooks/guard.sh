#!/usr/bin/env bash
# Claude Code PreToolUse hook. Refuses actions the team never wants an agent to take; exit 2 blocks the tool call
# and shows the reason to Claude.
set -u
input=$(cat)

block() {
  echo "Blocked by the team harness: $1" >&2
  exit 2
}

if printf '%s' "$input" | grep -q '"tool_name" *: *"Bash"'; then
  command=$(printf '%s' "$input" | grep -oE '"command" *: *"(\\.|[^"\\])*"' | head -1 \
    | sed -E 's/^"command" *: *"//; s/"$//; s/\\"/"/g; s/\\\\/\\/g')
  printf '%s' "$command" | grep -Eq 'git[[:space:]].*push([[:space:]].*)?[[:space:]](--force|-f)([[:space:]]|$)' \
    && block "force-pushing rewrites shared history. Push normally, or ask the user to force-push themselves."
  printf '%s' "$command" | grep -Eq 'git[[:space:]].*reset([[:space:]].*)?[[:space:]]--hard' \
    && block "git reset --hard discards uncommitted work. Use git stash, or ask the user."
  printf '%s' "$command" | grep -Eq 'git[[:space:]].*clean([[:space:]].*)?[[:space:]]-[a-zA-Z]*f' \
    && block "git clean -f deletes untracked files for good. Ask the user."
  exit 0
fi

path=$(printf '%s' "$input" | grep -o '"file_path" *: *"[^"]*"' | head -1 | sed 's/.*: *"//; s/"$//; s#\\\\#/#g')
case "$path" in
  */db/migration/*.sql) ;;
  *) exit 0 ;;
esac

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
relative=$(git ls-files --full-name -- "$path" 2>/dev/null)
[ -n "$relative" ] || exit 0
for ref in origin/main origin/master main master; do
  if git rev-parse --verify -q "$ref" > /dev/null; then
    git cat-file -e "$ref:$relative" 2> /dev/null \
      && block "$relative is on $ref, so it may already have run on a shared database, and Flyway fails when its checksum changes. Write a new migration instead (see the db-migration skill)."
    exit 0
  fi
done
exit 0
