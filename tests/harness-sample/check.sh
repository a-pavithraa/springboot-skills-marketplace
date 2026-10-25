#!/usr/bin/env bash
# Applies the team harness to the sample project and proves its gates work on the JDK in use:
# ./mvnw verify passes on clean code, and each gate fails on a mistake planted for it.
#   check.sh [all|marked]     NullAway mode passed to apply_harness.py --nullaway (default all)
# Maven comes from $MVN (default mvn); extra Maven options can go in MAVEN_ARGS.
set -euo pipefail
MODE=${1:-all}
MVN=${MVN:-mvn}
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../.." && pwd)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

cp -r "$HERE/project/." "$WORK/"
cd "$WORK"
git init -q && git add -A && git -c user.name=ci -c user.email=ci@example.com commit -qm sample
python3 "$REPO/plugins/springboot-architecture/skills/spring-boot-team-harness/scripts/apply_harness.py" . --nullaway "$MODE"
"$MVN" -B -q spotless:apply
git add -A && git -c user.name=ci -c user.email=ci@example.com commit -qm harness

failures=0
pass() { echo "ok   $1"; }
fail() { echo "FAIL $1"; failures=$((failures + 1)); }
reset() { git checkout -q -- . && git clean -qfd; }

# Runs Maven and expects it to fail with a line matching the pattern.
expect_failure() {
  local name=$1 pattern=$2; shift 2
  if "$MVN" -B "$@" > out.log 2>&1; then
    fail "$name: build passed"
  elif grep -Eq "$pattern" out.log; then
    pass "$name"
  else
    fail "$name: build failed for another reason"; tail -40 out.log
  fi
  reset
}

if "$MVN" -B verify > out.log 2>&1; then pass "clean project: verify passes"; else fail "clean project: verify failed"; tail -60 out.log; fi
reset

null_return() {  # package, class
  mkdir -p "src/main/java/com/acme/shop/$1"
  printf 'package com.acme.shop.%s;\n\npublic class %s {\n    public String name() {\n        return null;\n    }\n}\n' "$1" "$2" \
    > "src/main/java/com/acme/shop/$1/$2.java"
}

null_return catalog Broken
expect_failure "NullAway: null return in a @NullMarked package" '\[NullAway\]' compile

null_return orders Broken
if [ "$MODE" = marked ]; then
  if "$MVN" -B compile > out.log 2>&1; then pass "NullAway marked: package without @NullMarked is not checked"
  else fail "NullAway marked: unmarked package was checked"; tail -40 out.log; fi
  reset
else
  expect_failure "NullAway all: null return in a package without @NullMarked" '\[NullAway\]' compile
fi

perl -pi -e 's|return catalog|System.out.println(sku);\n        return catalog|' src/main/java/com/acme/shop/orders/Orders.java
expect_failure "CodeRulesTests: System.out" 'CodeRulesTests' test -Dtest=CodeRulesTests -Dsurefire.failIfNoSpecifiedTests=false

echo "spring.aplication.name=typo" >> src/main/resources/application.properties
expect_failure "ConfigurationKeysTests: unknown key" 'spring\.aplication\.name' test -Dtest=ConfigurationKeysTests -Dsurefire.failIfNoSpecifiedTests=false

mkdir -p src/main/java/com/acme/shop/catalog/internal
printf 'package com.acme.shop.catalog.internal;\n\npublic class Discounts {\n    public static int percent() {\n        return 5;\n    }\n}\n' \
  > src/main/java/com/acme/shop/catalog/internal/Discounts.java
perl -pi -e 's|return catalog|int unused = com.acme.shop.catalog.internal.Discounts.percent();\n        return catalog|' \
  src/main/java/com/acme/shop/orders/Orders.java
expect_failure "ModuleBoundariesTests: use of another module's internal package" 'ModuleBoundariesTests|Violations' \
  test -Dtest=ModuleBoundariesTests -Dsurefire.failIfNoSpecifiedTests=false

perl -pi -e 's|    private final Catalog catalog;|  private final Catalog catalog;|' src/main/java/com/acme/shop/orders/Orders.java
expect_failure "Spotless: unformatted code" 'spotless' verify -DskipTests

echo
if [ "$failures" -eq 0 ]; then echo "All harness gates work (JDK $(java -version 2>&1 | grep -v "Picked up" | head -1), NullAway $MODE)"; else echo "$failures check(s) failed"; exit 1; fi
