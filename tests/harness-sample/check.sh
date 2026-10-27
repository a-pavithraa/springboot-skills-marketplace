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
HARNESS="$REPO/plugins/springboot-architecture/skills/spring-boot-team-harness/scripts"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

cp -r "$HERE/project/." "$WORK/"
cd "$WORK"
# The hooks and baseline.py call ./mvnw; this one runs the Maven in use.
printf '#!/usr/bin/env bash\nexec %q "$@"\n' "$(command -v "$MVN")" > mvnw && chmod +x mvnw
git init -q && git add -A && git -c user.name=ci -c user.email=ci@example.com commit -qm sample
python3 "$HARNESS/apply_harness.py" . --nullaway "$MODE"
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

# One build with a mistake for each of the remaining code rules; every rule's test must fail.
perl -0pi -e 's|(<dependencies>)|$1\n    <dependency><groupId>org.springframework</groupId><artifactId>spring-web</artifactId></dependency>\n    <dependency><groupId>org.springframework</groupId><artifactId>spring-tx</artifactId></dependency>\n    <dependency><groupId>jakarta.persistence</groupId><artifactId>jakarta.persistence-api</artifactId></dependency>|' pom.xml
cat > src/main/java/com/acme/shop/orders/Shipping.java <<'JAVA'
package com.acme.shop.orders;

import org.springframework.http.HttpStatus;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestClient;
import org.springframework.web.server.ResponseStatusException;

@Service
public class Shipping {
    private final RestClient carrier = RestClient.create();

    @Transactional
    public void book() {
        carrier.post().uri("/bookings").retrieve().toBodilessEntity();
    }

    @Transactional
    private void cancel() {}

    @Transactional
    public void rebook(Dispatch dispatch) {
        dispatch.send();
    }

    @Scheduled(fixedDelay = 60000)
    public void poll() {}

    @Deprecated
    public void bookOld() {}

    public void refuse() {
        throw new ResponseStatusException(HttpStatus.BAD_REQUEST);
    }
}
JAVA
cat > src/main/java/com/acme/shop/orders/Dispatch.java <<'JAVA'
package com.acme.shop.orders;

import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class Dispatch {
    private final RestClient carrier = RestClient.builder().baseUrl("https://carrier.example.com").build();

    public void send() {
        carrier.post().uri("/pickups").retrieve().toBodilessEntity();
    }
}
JAVA
cat > src/main/java/com/acme/shop/orders/Parcel.java <<'JAVA'
package com.acme.shop.orders;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.ManyToOne;
import org.jspecify.annotations.Nullable;

@Entity
public class Parcel {
    @Id
    @Nullable Long id;

    @ManyToOne
    @Nullable Parcel container;

    Size size = Size.SMALL;

    public enum Size {
        SMALL
    }
}
JAVA
"$MVN" -B test -Dtest=CodeRulesTests -Dsurefire.failIfNoSpecifiedTests=false > out.log 2>&1 || true
for rule in httpClientsComeFromTheBuilder transactionsDontWaitOnRemoteCalls proxiedMethodsCanBeIntercepted \
    asyncAndSchedulingAreSwitchedOn oldCodeIsDeletedNotDeprecated servicesDontUseHttpTypes toOneAssociationsAreLazy \
    enumColumnsAreStoredByName; do
  if grep -q "CodeRulesTests.$rule" out.log; then pass "CodeRulesTests: $rule"; else fail "CodeRulesTests: $rule did not fail"; fi
done
for case in "RestClient.builder()" "which makes a remote call, inside a transaction"; do
  if grep -qF "$case" out.log; then pass "CodeRulesTests: $case"; else fail "CodeRulesTests: no violation for $case"; fi
done
if ! grep -q "Tests run:" out.log; then tail -40 out.log; fi
reset

echo "spring.aplication.name=typo" >> src/main/resources/application.properties
expect_failure "ConfigurationKeysTests: unknown key" 'spring\.aplication\.name' test -Dtest=ConfigurationKeysTests -Dsurefire.failIfNoSpecifiedTests=false

mkdir -p src/main/java/com/acme/shop/catalog/internal
printf 'package com.acme.shop.catalog.internal;\n\npublic class Discounts {\n    public static int percent() {\n        return 5;\n    }\n}\n' \
  > src/main/java/com/acme/shop/catalog/internal/Discounts.java
perl -pi -e 's|return catalog|int unused = com.acme.shop.catalog.internal.Discounts.percent();\n        return catalog|' \
  src/main/java/com/acme/shop/orders/Orders.java
expect_failure "ModuleBoundariesTests: use of another module's internal package" 'ModuleBoundariesTests|Violations' \
  test -Dtest=ModuleBoundariesTests -Dsurefire.failIfNoSpecifiedTests=false

perl -0pi -e 's|(\n\}\s*)$|\n    public int size() {\n        return prices.size();\n    }$1|' src/main/java/com/acme/shop/catalog/Catalog.java
printf 'package com.acme.shop;\n\nclass CatalogSizeTests {\n    @org.junit.jupiter.api.Test\n    void counts() {\n        new com.acme.shop.catalog.Catalog().size();\n    }\n}\n' > src/test/java/com/acme/shop/CatalogSizeTests.java
expect_failure "UnusedCodeTests: a method only a test calls" 'is called only from tests' test -Dtest=UnusedCodeTests -Dsurefire.failIfNoSpecifiedTests=false

perl -pi -e 's|    private final Catalog catalog;|  private final Catalog catalog;|' src/main/java/com/acme/shop/orders/Orders.java
expect_failure "Spotless: unformatted code" 'spotless' verify -DskipTests

# The rest of the cycle, as a team meets it: rerunning the harness changes nothing, the Stop hook catches a mistake
# on a real build and lets the fixed code through, and an existing codebase adopts the harness with baseline.py.
python3 "$HARNESS/apply_harness.py" . --nullaway "$MODE" > .git/apply.log
if [ -z "$(git status --porcelain)" ]; then pass "rerunning apply_harness.py changes nothing"
else fail "rerunning apply_harness.py changed files"; git status --porcelain; cat .git/apply.log; fi
reset

hook() {  # [--session-start] [stop_hook_active]
  local args=() active=false
  [ "${1:-}" = --session-start ] && { args=(--session-start); shift; }
  [ -n "${1:-}" ] && active=$1
  printf '{"session_id":"e2e","stop_hook_active":%s}' "$active" \
    | CLAUDE_PROJECT_DIR="$WORK" bash .claude/hooks/verify-on-stop.sh "${args[@]}" > hook.out 2>&1
}
hook --session-start
perl -0pi -e 's|(public BigDecimal total\(String sku, int quantity\) \{\n)|    \@org.springframework.scheduling.annotation.Async\n    public void warm() {}\n\n$1        warm();\n|' \
  src/main/java/com/acme/shop/orders/Orders.java
if hook; then fail "Stop hook: passed a class that calls its own @Async method"; cat hook.out
elif grep -q "skips the proxy, so @Async does nothing" hook.out; then pass "Stop hook: blocks a self-invoked @Async method"
else fail "Stop hook: blocked for another reason"; tail -30 hook.out; fi
perl -0pi -e 's|        warm\(\);\n||' src/main/java/com/acme/shop/orders/Orders.java
perl -0pi -e 's|    \@org.springframework.scheduling.annotation.Async\n    public void warm\(\) \{\}\n\n||' src/main/java/com/acme/shop/orders/Orders.java
if hook true; then pass "Stop hook: lets the fixed code through"; else fail "Stop hook: blocked the fixed code"; tail -30 hook.out; fi
rm -f hook.out
reset

# Existing code that breaks the rules before the harness arrives: baseline.py records it, verify passes, and new
# violations still fail. The integrity check then refuses a pull request that adds to the record.
null_return catalog Legacy
perl -pi -e 's|return catalog|System.out.println(sku);\n        return catalog|' src/main/java/com/acme/shop/orders/Orders.java
git add -A && git -c user.name=ci -c user.email=ci@example.com commit -qm legacy
if python3 "$HARNESS/baseline.py" . > baseline.log 2>&1 && grep -q "marked 1 classes" baseline.log; then
  pass "baseline.py: marks the legacy class and records the legacy violation"
else fail "baseline.py failed"; tail -30 baseline.log; fi
rm -f baseline.log
if "$MVN" -B verify > out.log 2>&1; then pass "baseline: verify passes on the legacy code"
else fail "baseline: verify failed on the legacy code"; tail -60 out.log; fi
rm -f out.log
git add -A && git -c user.name=ci -c user.email=ci@example.com commit -qm baseline
base=$(git rev-parse HEAD)
perl -pi -e 's|return catalog|System.out.println(quantity);\n        return catalog|' src/main/java/com/acme/shop/orders/Orders.java
expect_failure "baseline: a new violation still fails" 'CodeRulesTests' test -Dtest=CodeRulesTests -Dsurefire.failIfNoSpecifiedTests=false

record=$(git ls-files src/test/resources/archunit_store | grep -v stored.rules | head -1)
echo "Method <com.acme.shop.orders.Orders.total(java.lang.String, int)> calls System.out" >> "$record"
git add -A && git -c user.name=ci -c user.email=ci@example.com commit -qm "sneak a violation into the record"
if bash .github/harness/check-protected.sh "$base" > out.log; then fail "integrity check: accepted an addition to the record"; cat out.log
elif grep -q "::error file=$record::" out.log; then pass "integrity check: refuses an addition to the freeze record"
else fail "integrity check: failed for another reason"; cat out.log; fi
rm -f out.log

echo
if [ "$failures" -eq 0 ]; then echo "All harness gates work (JDK $(java -version 2>&1 | grep -v "Picked up" | head -1), NullAway $MODE)"; else echo "$failures check(s) failed"; exit 1; fi
