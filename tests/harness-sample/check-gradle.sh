#!/usr/bin/env bash
# Applies the team harness to the sample project built with Gradle and proves its gates work there: ./gradlew build
# passes on clean code, each gate fails on a mistake planted for it, the Stop hook and baseline.py work on a real
# build, and the integrity check guards gradle/harness.gradle.
#   check-gradle.sh [groovy|kotlin]     build script DSL (default groovy)
# Gradle comes from $GRADLE (default gradle).
set -euo pipefail
DSL=${1:-groovy}
GRADLE=${GRADLE:-gradle}
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../.." && pwd)
HARNESS="$REPO/plugins/springboot-architecture/skills/spring-boot-team-harness/scripts"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

cp -r "$HERE/project/." "$WORK/"
cd "$WORK"
rm pom.xml
if [ "$DSL" = kotlin ]; then
  BUILD=build.gradle.kts
  printf 'rootProject.name = "shop"\n' > settings.gradle.kts
  cat > build.gradle.kts <<'KTS'
plugins {
    java
    id("org.springframework.boot") version "4.1.1"
    id("io.spring.dependency-management") version "1.1.7"
}

group = "com.acme"
version = "0.0.1-SNAPSHOT"

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(25)
    }
}

repositories {
    mavenCentral()
}

dependencies {
    implementation("org.springframework.boot:spring-boot-starter")
    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}
KTS
  dependency() { perl -0pi -e "s|(dependencies \\{\\n)|\$1    $1(\"$2\")\\n|" "$BUILD"; }
else
  BUILD=build.gradle
  printf "rootProject.name = 'shop'\n" > settings.gradle
  cat > build.gradle <<'GROOVY'
plugins {
    id 'java'
    id 'org.springframework.boot' version '4.1.1'
    id 'io.spring.dependency-management' version '1.1.7'
}

group = 'com.acme'
version = '0.0.1-SNAPSHOT'

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(25)
    }
}

repositories {
    mavenCentral()
}

dependencies {
    implementation 'org.springframework.boot:spring-boot-starter'
    testImplementation 'org.springframework.boot:spring-boot-starter-test'
    testRuntimeOnly 'org.junit.platform:junit-platform-launcher'
}
GROOVY
  dependency() { perl -0pi -e "s|(dependencies \\{\\n)|\$1    $1 '$2'\\n|" "$BUILD"; }
fi
# The hooks and baseline.py call ./gradlew; this one runs the Gradle in use.
printf '#!/usr/bin/env bash\nexec %q "$@"\n' "$(command -v "$GRADLE")" > gradlew && chmod +x gradlew
printf '.gradle/\nbuild/\n' > .gitignore
git init -q && git add -A && git -c user.name=ci -c user.email=ci@example.com commit -qm sample
python3 "$HARNESS/apply_harness.py" . > apply.log
./gradlew -q spotlessApply
rm apply.log
git add -A && git -c user.name=ci -c user.email=ci@example.com commit -qm harness

failures=0
pass() { echo "ok   $1"; }
fail() { echo "FAIL $1"; failures=$((failures + 1)); }
reset() { git checkout -q -- . && git clean -qfd -e .gradle -e build; }

# Runs Gradle and expects it to fail with a line matching the pattern.
expect_failure() {
  local name=$1 pattern=$2; shift 2
  if ./gradlew "$@" > out.log 2>&1; then
    fail "$name: build passed"
  elif grep -Eq "$pattern" out.log; then
    pass "$name"
  else
    fail "$name: build failed for another reason"; tail -40 out.log
  fi
  reset
}

if grep -q 'gradle/harness.gradle' "$BUILD"; then pass "$BUILD applies gradle/harness.gradle"; else fail "$BUILD does not apply the script"; fi
if ./gradlew build > out.log 2>&1; then pass "clean project: build passes"; else fail "clean project: build failed"; tail -60 out.log; fi
reset

mkdir -p src/main/java/com/acme/shop/orders
printf 'package com.acme.shop.orders;\n\npublic class Broken {\n    public String name() {\n        return null;\n    }\n}\n' \
  > src/main/java/com/acme/shop/orders/Broken.java
expect_failure "NullAway: null return" '\.java:[0-9]+: error: \[NullAway\]' compileJava

perl -pi -e 's|return catalog|System.out.println(sku);\n        return catalog|' src/main/java/com/acme/shop/orders/Orders.java
expect_failure "CodeRulesTests: System.out" 'was violated' test --tests '*.CodeRulesTests'

echo "spring.aplication.name=typo" >> src/main/resources/application.properties
expect_failure "ConfigurationKeysTests: unknown key" 'spring\.aplication\.name' test --tests '*.ConfigurationKeysTests'

mkdir -p src/main/java/com/acme/shop/catalog/internal
printf 'package com.acme.shop.catalog.internal;\n\npublic class Discounts {\n    public static int percent() {\n        return 5;\n    }\n}\n' \
  > src/main/java/com/acme/shop/catalog/internal/Discounts.java
perl -pi -e 's|return catalog|int unused = com.acme.shop.catalog.internal.Discounts.percent();\n        return catalog|' \
  src/main/java/com/acme/shop/orders/Orders.java
expect_failure "ModuleBoundariesTests: use of another module's internal package" 'module-boundary violations are new|Violations' \
  test --tests '*.ModuleBoundariesTests'

dependency testImplementation org.springframework.boot:spring-boot-starter-restclient
if ./gradlew test --tests '*.BuildSetupTests' > out.log 2>&1; then
  pass "BuildSetupTests: a test-only HTTP client the application doesn't use is allowed"
else fail "BuildSetupTests: a test-only HTTP client the application doesn't use was rejected"; tail -40 out.log; fi
dependency implementation org.springframework:spring-web
printf 'package com.acme.shop.catalog;\n\nclass PriceFeed {\n    PriceFeed(org.springframework.web.client.RestClient.Builder builder) {}\n}\n' \
  > src/main/java/com/acme/shop/catalog/PriceFeed.java
expect_failure "BuildSetupTests: a test-only HTTP client, read from the Gradle build" \
  "$BUILD: spring-boot-starter-restclient is on the test classpath only" test --tests '*.BuildSetupTests'

cat > src/test/java/com/acme/shop/LeakyTests.java <<'JAVA'
package com.acme.shop;

class LeakyTests {
    @org.junit.jupiter.api.Test
    void logsAnEmail() {
        org.slf4j.LoggerFactory.getLogger(LeakyTests.class).info("signed in {}", "person@example.com");
    }
}
JAVA
expect_failure "LogLeakCheck: email in a log line" 'logged an email address' test --tests '*.LeakyTests'

perl -pi -e 's|    private final Catalog catalog;|  private final Catalog catalog;|' src/main/java/com/acme/shop/orders/Orders.java
expect_failure "Spotless: unformatted code" 'spotless' build -x test

python3 "$HARNESS/apply_harness.py" . > .git/apply.log
if [ -z "$(git status --porcelain)" ]; then pass "rerunning apply_harness.py changes nothing"
else fail "rerunning apply_harness.py changed files"; git status --porcelain; cat .git/apply.log; fi
reset

hook() {  # [--session-start] [stop_hook_active]; fails when the hook blocks the turn
  local args=() active=false
  [ "${1:-}" = --session-start ] && { args=(--session-start); shift; }
  [ -n "${1:-}" ] && active=$1
  printf '{"session_id":"e2e","stop_hook_active":%s}' "$active" \
    | CLAUDE_PROJECT_DIR="$WORK" bash .claude/hooks/verify-on-stop.sh "${args[@]}" > hook.out 2>&1 \
    && ! grep -q '^{"decision":"block"' hook.out
}
hook --session-start
perl -0pi -e 's|(public BigDecimal total\(String sku, int quantity\) \{\n)|    \@org.springframework.scheduling.annotation.Async\n    public void warm() {}\n\n$1        warm();\n|' \
  src/main/java/com/acme/shop/orders/Orders.java
printf 'package com.acme.shop.orders;\npublic class Spare {   int   x;}\n' > src/main/java/com/acme/shop/orders/Spare.java
if hook; then fail "Stop hook: passed a class that calls its own @Async method"; cat hook.out
elif grep -q "skips the proxy, so @Async does nothing" hook.out; then pass "Stop hook: blocks a self-invoked @Async method"
else fail "Stop hook: blocked for another reason"; tail -30 hook.out; fi
if grep -q '^    int x;' src/main/java/com/acme/shop/orders/Spare.java && git diff --quiet -- src/main/java/com/acme/shop/catalog; then
  pass "Stop hook: formats the session's files and no others"
else fail "Stop hook: did not format only the session's files"; cat src/main/java/com/acme/shop/orders/Spare.java; fi
perl -0pi -e 's|        warm\(\);\n||' src/main/java/com/acme/shop/orders/Orders.java
perl -0pi -e 's|    \@org.springframework.scheduling.annotation.Async\n    public void warm\(\) \{\}\n\n||' src/main/java/com/acme/shop/orders/Orders.java
if hook true; then pass "Stop hook: lets the fixed code through"; else fail "Stop hook: blocked the fixed code"; tail -30 hook.out; fi
rm -f hook.out
reset

# Existing code that breaks the rules: baseline.py records it, the build passes, and new violations still fail.
mkdir -p src/main/java/com/acme/shop/catalog/internal
printf 'package com.acme.shop.catalog;\n\npublic class Legacy {\n    public String name() {\n        return null;\n    }\n}\n' \
  > src/main/java/com/acme/shop/catalog/Legacy.java
perl -pi -e 's|return catalog|System.out.println(sku);\n        return catalog|' src/main/java/com/acme/shop/orders/Orders.java
printf 'package com.acme.shop.catalog.internal;\n\npublic class Discounts {\n    public static int percent() {\n        return 5;\n    }\n\n    public static int cap() {\n        return 50;\n    }\n}\n' \
  > src/main/java/com/acme/shop/catalog/internal/Discounts.java
perl -pi -e 's|return catalog|int legacy = com.acme.shop.catalog.internal.Discounts.percent();\n        return catalog|' \
  src/main/java/com/acme/shop/orders/Orders.java
git add -A && git -c user.name=ci -c user.email=ci@example.com commit -qm legacy
if python3 "$HARNESS/baseline.py" . > baseline.log 2>&1 && grep -q "marked 1 classes" baseline.log \
  && grep -q "recorded 1 module-boundary violations" baseline.log; then
  pass "baseline.py: marks the legacy class and records the legacy violations"
else fail "baseline.py failed"; tail -30 baseline.log; fi
rm -f baseline.log
if ./gradlew build > out.log 2>&1; then pass "baseline: build passes on the legacy code"
else fail "baseline: build failed on the legacy code"; tail -60 out.log; fi
rm -f out.log
git add -A && git -c user.name=ci -c user.email=ci@example.com commit -qm baseline
base=$(git rev-parse HEAD)
perl -pi -e 's|return catalog|System.out.println(quantity);\n        return catalog|' src/main/java/com/acme/shop/orders/Orders.java
expect_failure "baseline: a new violation still fails" 'was violated' test --tests '*.CodeRulesTests'
perl -pi -e 's|return catalog|int fresh = com.acme.shop.catalog.internal.Discounts.cap();\n        return catalog|' \
  src/main/java/com/acme/shop/orders/Orders.java
expect_failure "baseline: a new boundary violation still fails" '1 module-boundary violations are new' \
  test --tests '*.ModuleBoundariesTests'

perl -pi -e 's|option\("NullAway:JSpecifyMode", "true"\)|option("NullAway:JSpecifyMode", "false")|' gradle/harness.gradle
git add -A && git -c user.name=ci -c user.email=ci@example.com commit -qm "weaken the gates"
if bash .github/harness/check-protected.sh "$base" > out.log; then fail "integrity check: accepted a change to gradle/harness.gradle"; cat out.log
elif grep -q "::error file=gradle/harness.gradle::" out.log; then pass "integrity check: refuses a change to gradle/harness.gradle"
else fail "integrity check: failed for another reason"; cat out.log; fi
rm -f out.log

# The move-code skill's OpenRewrite init script, as the project skill gives it to the agent.
tmp=$(mktemp -d)
cat > "$tmp/move.yml" <<'YAML'
type: specs.openrewrite.org/v1beta/recipe
name: local.Move
recipeList:
  - org.openrewrite.java.ChangeType:
      oldFullyQualifiedTypeName: com.acme.shop.orders.Orders
      newFullyQualifiedTypeName: com.acme.shop.orders.sales.Orders
YAML
sed -n '/^   ```groovy$/,/^   ```$/p' .claude/skills/move-code/SKILL.md | sed '1d;$d; s/^   //' > "$tmp/rewrite.gradle"
if ./gradlew -q rewriteDryRun --init-script "$tmp/rewrite.gradle" -DmoveRecipe="$tmp/move.yml" > out.log 2>&1 \
  && grep -q "com.acme.shop.orders.sales" build/reports/rewrite/rewrite.patch; then
  pass "move-code: the init script previews the move without changing the build"
else fail "move-code: the init script dry run failed"; tail -30 out.log; fi
rm -rf "$tmp" out.log

echo
if [ "$failures" -eq 0 ]; then echo "All Gradle harness checks passed ($DSL DSL)."; else echo "$failures Gradle harness check(s) failed ($DSL DSL)."; exit 1; fi
