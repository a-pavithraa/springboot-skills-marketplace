#!/usr/bin/env bash
# Scenario 23: one seeded PR review in a fresh headless session.
#   run.sh <model> <arm> <out-dir>
#   arm: none | current | <git ref>   (a ref swaps in code-reviewer/SKILL.md from that commit;
#                                      references/ stay as on the current checkout)
# Example: run.sh haiku 0be0bbb /tmp/s23/a1
set -euo pipefail
MODEL=$1 ARM=$2 OUT=$3
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../../.." && pwd)
SKILLS=$REPO/plugins/springboot-architecture/skills

rm -rf "$OUT" && mkdir -p "$OUT/shop"
cd "$OUT/shop"
cp -r "$HERE/main/." .
git init -q -b main && git add -A && git -c user.name=t -c user.email=t@t commit -qm "Shop baseline"
git checkout -qb feature/admin-and-history
cp -r "$HERE/feature/." .
git add -A && git -c user.name=t -c user.email=t@t commit -qm "Admin customer endpoints, order history, refunds"

if [ "$ARM" != none ]; then
  mkdir -p .claude/skills
  cp -r "$SKILLS/code-reviewer" "$SKILLS/springboot-migration" .claude/skills/
  if [ "$ARM" != current ]; then
    git -C "$REPO" show "$ARM:plugins/springboot-architecture/skills/code-reviewer/SKILL.md" > .claude/skills/code-reviewer/SKILL.md
  fi
  # Keep the skills out of the reviewed diff.
  echo ".claude/" >> .git/info/exclude
fi

claude -p --model "$MODEL" \
  --allowedTools "Read" "Grep" "Glob" "Bash(git:*)" \
  --output-format json \
  "Please review this PR before I merge it." > "$OUT/session.json"

python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("result",""))' "$OUT/session.json" > "$OUT/review.md"
echo "Review: $OUT/review.md  (score it against $HERE/key.md)"
