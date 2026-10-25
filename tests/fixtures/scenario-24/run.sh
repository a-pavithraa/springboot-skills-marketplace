#!/usr/bin/env bash
# Scenario 24: one persistence-fix session, then the hidden scorer.
#   run.sh <model> <arm> <out-dir>
#   arm: none | <git ref>   (the ref must contain skills/spring-data-jpa, e.g. 23a35a4^)
# Example: run.sh haiku 23a35a4^ /tmp/s24/skill
set -euo pipefail
MODEL=$1 ARM=$2 OUT=$3
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../../.." && pwd)

rm -rf "$OUT" && mkdir -p "$OUT/shop"
cp -r "$HERE/shop/." "$OUT/shop/"
cd "$OUT/shop"
git init -q && git add -A && git -c user.name=t -c user.email=t@t commit -qm fixture

if [ "$ARM" != none ]; then
  mkdir -p .claude/skills
  git -C "$REPO" archive "$ARM" plugins/springboot-architecture/skills/spring-data-jpa \
    | tar -x -C .claude/skills --strip-components=3
fi

claude -p --model "$MODEL" \
  --permission-mode acceptEdits \
  --allowedTools "Read" "Grep" "Glob" "Edit" "Write" "Bash(mvn:*)" "Bash(./mvnw:*)" \
  --output-format json \
  "Optimize the persistence code in this project." > "$OUT/session.json"

"$HERE/score.sh" "$OUT/shop" | tee "$OUT/score.txt"
