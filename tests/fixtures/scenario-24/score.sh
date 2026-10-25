#!/usr/bin/env bash
# Runs the hidden scorer against a project, without changing it.
#   score.sh <project-dir>
# Untouched fixture: P1 482, P2 200, P3 3, P4 product kept false, P5 32.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
WORK=$(mktemp -d)
cp -r "$1/." "$WORK/"
cp "$HERE/scorer/ZScoreTest.java" "$WORK/src/test/java/com/shop/"
cd "$WORK"
if mvn -q test > score.log 2>&1; then echo "Existing tests and scorer: pass"; else echo "Build or tests FAILED, see $WORK/score.log"; fi
grep 'SCORE|' score.log | sed 's/^SCORE| //'
grep -c 'OrderLineRepository' -r src/main/java >/dev/null && echo "P6 OrderLineRepository still present" || echo "P6 OrderLineRepository removed"
grep -h '@ManyToOne' src/main/java/com/shop/OrderLine.java | sed 's/^ */P3 mapping: /'
