#!/usr/bin/env bash
# Fails when a change leaves a source file larger than LIMIT bytes, about LIMIT/4 tokens. A file passes that size mostly
# when one class does several jobs, and agents add to the file that is already there, so the check makes the split
# happen when the file grows. Smaller files also cost fewer tokens to read and give an edit fewer similar blocks to hit.
#
# Usage: check-file-size.sh <base-commit>       checks the files a pull request adds or changes since <base-commit>
#        check-file-size.sh <commit> - < files   checks the files listed on stdin, one per line, against <commit>
#
# A file already over the limit at the base passes unless the change makes it larger, so old code needs no baseline.
# Generated code, build output, dependencies and Flyway migrations are skipped: nobody splits those by hand.

set -u
LIMIT=20000
base=${1:?usage: check-file-size.sh <base-commit> [-]}

checked() {
  case "$1" in
    target/* | */target/* | build/* | */build/* | node_modules/* | */node_modules/* | dist/* | */dist/*) return 1 ;;
    *generated* | */db/migration/* | *.min.js | *.d.ts) return 1 ;;
    *.java | *.kt | *.groovy | *.scala | *.ts | *.tsx | *.js | *.jsx | *.mjs | *.vue | *.svelte | *.py) return 0 ;;
  esac
  return 1
}

if [ "${2:-}" = - ]; then
  files=$(cat)
else
  base=$(git merge-base "$base" HEAD)
  files=$(git diff --name-only --diff-filter=AMR "$base" HEAD)
fi

over=()
while IFS= read -r file; do
  file=${file%$'\r'}
  [ -n "$file" ] && [ -f "$file" ] && checked "$file" || continue
  size=$(wc -c < "$file" | tr -d ' ')
  [ "$size" -gt "$LIMIT" ] || continue
  before=$(git cat-file -s "$base:./$file" 2> /dev/null || echo 0)
  [ "$size" -gt "$before" ] || continue
  over+=("$file is $((size / 1000)) KB, about $((size / 4)) tokens.")
done <<< "$files"

[ ${#over[@]} -eq 0 ] && exit 0
printf '%s\n' "${over[@]}"
cat << EOF

The limit is $((LIMIT / 1000)) KB, about $((LIMIT / 4)) tokens. Split by what changes together, not by line count:
- Code: group the methods by the fields and dependencies they use. Move whole groups, starting with the largest one
  that has its own dependencies (often the read-only queries), until the file is well under the limit. Each goes in
  a new class named for what it does (OrderReports, not OrderHelper, Util or a numbered copy), in the module's
  internal package unless another module calls it. Keep the methods other modules call on this class, and have them
  delegate. If two new classes need each other, the split is wrong: merge them back.
- Tests: first move repeated setup into a test-data builder, near-identical cases into a @ParameterizedTest, and large
  payloads into src/test/resources. Then split by behaviour. Give split Spring tests one shared base class and the
  same configuration (the same @MockitoBean fields, properties and annotations), so they reuse one cached context.
- To add code to a file that was already over the limit, put the new code in a new class.
EOF
exit 1
