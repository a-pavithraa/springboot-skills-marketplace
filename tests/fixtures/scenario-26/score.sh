#!/usr/bin/env bash
# Runs the hidden scorer against a project, without changing it.
#   score.sh <project-dir>
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
WORK=$(mktemp -d)
cp -r "$1/." "$WORK/"
rm -rf "$WORK/.claude" "$WORK/target"
cp "$HERE/scorer/ZScoreTest.java" "$WORK/src/test/java/com/blog/"
cd "$WORK"
if mvn -q test > score.log 2>&1; then echo "Existing tests and scorer: pass"; else echo "Build or tests FAILED, see $WORK/score.log"; fi
grep 'SCORE|' score.log | sed 's/^SCORE| //'
grep -q 'MultipleBagFetchException' score.log && echo "MultipleBagFetchException thrown"
for field in comments tags; do
  echo "Post.$field: $(grep -hE "^[^/]*[A-Za-z]+<(Comment|Tag)> +$field\b" src/main/java/com/blog/Post.java | sed -E 's/^ *//; s/ *=.*//')"
done
echo "Post.tags cascade: $(grep -B3 -E "<Tag> +tags" src/main/java/com/blog/Post.java | grep -oE '@ManyToMany[^)]*\)?' | head -1)"
echo "Tag equals/hashCode: $(grep -cE 'boolean equals|int hashCode' src/main/java/com/blog/Tag.java)"
