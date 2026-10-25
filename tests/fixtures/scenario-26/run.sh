#!/usr/bin/env bash
# Scenario 26: one persistence-fix session on the blog fixture, then the hidden scorer.
#   run.sh <model> <arm> <out-dir>
#   arm: none | current | <git ref>   (code-reviewer as a project skill; current = this working tree)
# Example: run.sh sonnet none /tmp/s26/none
set -euo pipefail
MODEL=$1 ARM=$2 OUT=$3
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../../.." && pwd)
SKILL=plugins/springboot-architecture/skills/code-reviewer

rm -rf "$OUT" && mkdir -p "$OUT/blog"
cp -r "$HERE/blog/." "$OUT/blog/"
cd "$OUT/blog"
git init -q && git add -A && git -c user.name=t -c user.email=t@t commit -qm fixture

if [ "$ARM" = current ]; then
  mkdir -p .claude/skills && cp -r "$REPO/$SKILL" .claude/skills/
elif [ "$ARM" != none ]; then
  mkdir -p .claude/skills
  git -C "$REPO" archive "$ARM" "$SKILL" | tar -x -C .claude/skills --strip-components=3
fi

claude -p --model "$MODEL" \
  --permission-mode acceptEdits \
  --allowedTools "Read" "Grep" "Glob" "Edit" "Write" "Skill" "Bash(mvn:*)" "Bash(./mvnw:*)" \
  --max-budget-usd 4 \
  --output-format stream-json --verbose \
  "Optimize the persistence code in this project." > "$OUT/session.jsonl"

"$HERE/score.sh" "$OUT/blog" | tee "$OUT/score.txt"
