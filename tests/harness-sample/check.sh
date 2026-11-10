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

# A generator's output compiles beside the team's code; the rules name it from its source under target/generated-sources.
printf 'package com.acme.shop.orders;\n\npublic class OrderDto {\n    public void print() {\n        System.out.println("dto");\n    }\n}\n' \
  > src/main/java/com/acme/shop/orders/OrderDto.java
mkdir -p target/generated-sources/openapi/com/acme/shop/orders
cp src/main/java/com/acme/shop/orders/OrderDto.java target/generated-sources/openapi/com/acme/shop/orders/
if "$MVN" -B test -Dtest=CodeRulesTests,UnusedCodeTests -Dsurefire.failIfNoSpecifiedTests=false > out.log 2>&1; then
  pass "CodeRulesTests: generated sources are left out"
else
  fail "CodeRulesTests: a rule fired on generated sources"; tail -40 out.log
fi
rm -rf target/generated-sources/openapi
reset

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
cat > src/main/java/com/acme/shop/orders/CatchAll.java <<'JAVA'
package com.acme.shop.orders;

import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
class CatchAll {
    @ExceptionHandler(Exception.class)
    String handle(Exception e) {
        return String.valueOf(e.getMessage());
    }
}
JAVA
cat > src/main/java/com/acme/shop/orders/ParcelStore.java <<'JAVA'
package com.acme.shop.orders;

public interface ParcelStore {
    int count();
}
JAVA
cat > src/main/java/com/acme/shop/orders/JdbcParcelStore.java <<'JAVA'
package com.acme.shop.orders;

import org.springframework.stereotype.Repository;

@Repository
class JdbcParcelStore implements ParcelStore {
    @Override
    public int count() {
        return 0;
    }
}
JAVA
cat > src/main/java/com/acme/shop/orders/ParcelController.java <<'JAVA'
package com.acme.shop.orders;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
class ParcelController {
    private final ParcelStore parcels;

    ParcelController(ParcelStore parcels) {
        this.parcels = parcels;
    }

    @GetMapping("/parcels/count")
    int count() {
        return parcels.count();
    }
}
JAVA
"$MVN" -B test -Dtest=CodeRulesTests -Dsurefire.failIfNoSpecifiedTests=false > out.log 2>&1 || true
for rule in catchAllHandlersKeepTheExceptionServerSide httpClientsComeFromTheBuilder transactionsDontWaitOnRemoteCalls proxiedMethodsCanBeIntercepted \
    asyncAndSchedulingAreSwitchedOn oldCodeIsDeletedNotDeprecated servicesDontUseHttpTypes toOneAssociationsAreLazy \
    enumColumnsAreStoredByName controllersDontUseRepositories; do
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

perl -0pi -e 's|(\n\}\s*)$|\n    public void setCurrency(String currency) {}$1|' src/main/java/com/acme/shop/catalog/Catalog.java
printf 'package com.acme.shop;\n\nclass CatalogCurrencyTests {\n    @org.junit.jupiter.api.Test\n    void sets() {\n        new com.acme.shop.catalog.Catalog().setCurrency("EUR");\n    }\n}\n' > src/test/java/com/acme/shop/CatalogCurrencyTests.java
if "$MVN" -B test -Dtest=UnusedCodeTests -Dsurefire.failIfNoSpecifiedTests=false > out.log 2>&1; then pass "UnusedCodeTests: a setter only a test calls is allowed, since binding calls it"
else fail "UnusedCodeTests: a setter only a test calls was rejected"; tail -40 out.log; fi
reset

perl -0pi -e 's|(<dependencies>)|$1\n    <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-restclient</artifactId><scope>test</scope></dependency>|' pom.xml
if "$MVN" -B test -Dtest=BuildSetupTests -Dsurefire.failIfNoSpecifiedTests=false > out.log 2>&1; then pass "BuildSetupTests: a test-only HTTP client the application doesn't use is allowed"
else fail "BuildSetupTests: a test-only HTTP client the application doesn't use was rejected"; tail -40 out.log; fi
perl -0pi -e 's|(<dependencies>)|$1\n    <dependency><groupId>org.springframework</groupId><artifactId>spring-web</artifactId></dependency>|' pom.xml
printf 'package com.acme.shop.catalog;\n\nclass PriceFeed {\n    PriceFeed(org.springframework.web.client.RestClient.Builder builder) {}\n}\n' > src/main/java/com/acme/shop/catalog/PriceFeed.java
expect_failure "BuildSetupTests: a test-only HTTP client the application builds a client with" 'spring-boot-starter-restclient is on the test classpath only' \
  test -Dtest=BuildSetupTests -Dsurefire.failIfNoSpecifiedTests=false

printf 'management.endpoints.web.exposure.include=health,env\n' >> src/main/resources/application.properties
expect_failure "ConfigurationKeysTests: env exposed on the public port" 'exposes env' test -Dtest=ConfigurationKeysTests -Dsurefire.failIfNoSpecifiedTests=false

printf 'server.port=8080\nmanagement.server.port=8080\nmanagement.endpoints.web.exposure.include=health,env\n' >> src/main/resources/application.properties
expect_failure "ConfigurationKeysTests: management port equal to server port" 'exposes env' test -Dtest=ConfigurationKeysTests -Dsurefire.failIfNoSpecifiedTests=false

printf 'management.server.port=${MANAGEMENT_PORT}\nmanagement.endpoints.web.exposure.include=health,env\n' >> src/main/resources/application.properties
expect_failure "ConfigurationKeysTests: management port the file doesn't decide" 'exposes env' test -Dtest=ConfigurationKeysTests -Dsurefire.failIfNoSpecifiedTests=false

printf 'server.port=${PORT}\nmanagement.server.port=9090\nmanagement.endpoints.web.exposure.include=health,env\n' >> src/main/resources/application.properties
expect_failure "ConfigurationKeysTests: server port the file doesn't decide" 'exposes env' test -Dtest=ConfigurationKeysTests -Dsurefire.failIfNoSpecifiedTests=false

printf 'management.server.port=9090\nmanagement.endpoints.web.exposure.include=health,env\n' >> src/main/resources/application.properties
if "$MVN" -B test -Dtest=ConfigurationKeysTests -Dsurefire.failIfNoSpecifiedTests=false > out.log 2>&1; then pass "ConfigurationKeysTests: a separate management port is allowed"
else fail "ConfigurationKeysTests: a separate management port was rejected"; tail -40 out.log; fi
reset

cat > src/test/java/com/acme/shop/LeakyTests.java <<'JAVA'
package com.acme.shop;

class LeakyTests {
    @org.junit.jupiter.api.Test
    void logsAnEmail() {
        org.slf4j.LoggerFactory.getLogger(LeakyTests.class).info("signed in {}", "person@example.com");
    }
}
JAVA
expect_failure "LogLeakCheck: email in a log line" 'logged an email address' test -Dtest=LeakyTests -Dsurefire.failIfNoSpecifiedTests=false

perl -pi -e 's|return catalog|new IllegalStateException().printStackTrace();\n        return catalog|' src/main/java/com/acme/shop/orders/Orders.java
expect_failure "CodeRulesTests: printStackTrace" 'printStackTrace' test -Dtest=CodeRulesTests -Dsurefire.failIfNoSpecifiedTests=false

cat > src/main/java/com/acme/shop/orders/TelemetryConfig.java <<'JAVA'
package com.acme.shop.orders;

import io.opentelemetry.api.OpenTelemetry;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
class TelemetryConfig {
    @Bean
    OpenTelemetry openTelemetry() {
        return OpenTelemetry.noop();
    }
}
JAVA
expect_failure "CodeRulesTests: hand-built OpenTelemetry bean" 'openTelemetry' test -Dtest=CodeRulesTests -Dsurefire.failIfNoSpecifiedTests=false

perl -pi -e 's|    private final Catalog catalog;|  private final Catalog catalog;|' src/main/java/com/acme/shop/orders/Orders.java
expect_failure "Spotless: unformatted code" 'spotless' verify -DskipTests

# The rest of the cycle, as a team meets it: rerunning the harness changes nothing, the Stop hook catches a mistake
# on a real build and lets the fixed code through, and an existing codebase adopts the harness with baseline.py.
python3 "$HARNESS/apply_harness.py" . --nullaway "$MODE" > .git/apply.log
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
mkdir -p src/main/java/com/acme/shop/catalog/internal
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
if "$MVN" -B verify > out.log 2>&1; then pass "baseline: verify passes on the legacy code"
else fail "baseline: verify failed on the legacy code"; tail -60 out.log; fi
rm -f out.log
git add -A && git -c user.name=ci -c user.email=ci@example.com commit -qm baseline
base=$(git rev-parse HEAD)
perl -pi -e 's|return catalog|System.out.println(quantity);\n        return catalog|' src/main/java/com/acme/shop/orders/Orders.java
expect_failure "baseline: a new violation still fails" 'CodeRulesTests' test -Dtest=CodeRulesTests -Dsurefire.failIfNoSpecifiedTests=false

perl -pi -e 's|^(\s*)(int legacy = )|$1// moved down a line\n$1$2|' src/main/java/com/acme/shop/orders/Orders.java
if "$MVN" -B test -Dtest=ModuleBoundariesTests -Dsurefire.failIfNoSpecifiedTests=false > out.log 2>&1; then
  pass "baseline: a recorded boundary violation on another line still passes"
else fail "baseline: a recorded boundary violation on another line failed"; tail -40 out.log; fi
reset
perl -pi -e 's|return catalog|int fresh = com.acme.shop.catalog.internal.Discounts.cap();\n        return catalog|' \
  src/main/java/com/acme/shop/orders/Orders.java
expect_failure "baseline: a new boundary violation still fails" '1 module-boundary violations are new' \
  test -Dtest=ModuleBoundariesTests -Dsurefire.failIfNoSpecifiedTests=false

record=$(git ls-files src/test/resources/archunit_store | grep -v stored.rules | head -1)
echo "Method <com.acme.shop.orders.Orders.total(java.lang.String, int)> calls System.out" >> "$record"
git add -A && git -c user.name=ci -c user.email=ci@example.com commit -qm "sneak a violation into the record"
if bash .github/harness/check-protected.sh "$base" > out.log; then fail "integrity check: accepted an addition to the record"; cat out.log
elif grep -q "::error file=$record::" out.log; then pass "integrity check: refuses an addition to the freeze record"
else fail "integrity check: failed for another reason"; cat out.log; fi
rm -f out.log
echo "cycle|catalog,orders" >> src/test/resources/modulith_store
git add -A && git -c user.name=ci -c user.email=ci@example.com commit -qm "sneak a cycle into the module record"
if bash .github/harness/check-protected.sh "$base" > out.log; then fail "integrity check: accepted an addition to modulith_store"; cat out.log
elif grep -q "::error file=src/test/resources/modulith_store::" out.log; then pass "integrity check: refuses an addition to modulith_store"
else fail "integrity check: failed for another reason"; cat out.log; fi
rm -f out.log
{ echo "package com.acme.shop.orders;"; echo "class Huge {"; for n in $(seq 1500); do echo "  int f$n = $n;"; done; echo "}"; } \
  > src/main/java/com/acme/shop/orders/Huge.java
git add -A && git -c user.name=ci -c user.email=ci@example.com commit -qm "add a file over the size limit"
if bash .github/harness/check-file-size.sh "$base" > out.log; then fail "file-size check: accepted a 20 KB file"; cat out.log
elif grep -q "orders/Huge.java is" out.log; then pass "file-size check: refuses a new file over the limit"
else fail "file-size check: failed for another reason"; cat out.log; fi
rm -f out.log
git reset -q --hard HEAD~1

echo
perl -0pi -e 's|<artifactId>spring-boot-starter</artifactId>|<artifactId>spring-boot-starter-webmvc</artifactId>|' pom.xml
python3 "$REPO/plugins/springboot-architecture/skills/spring-boot-team-harness/scripts/apply_harness.py" . --nullaway "$MODE" > /dev/null
cat > src/test/java/com/acme/shop/HandledFailureTests.java <<'JAVA'
package com.acme.shop;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

import io.micrometer.observation.Observation;
import io.micrometer.observation.ObservationHandler;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.CopyOnWriteArrayList;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.server.observation.ServerRequestObservationContext;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Import(HandledFailureTests.Setup.class)
@ExtendWith(OutputCaptureExtension.class)
class HandledFailureTests {

    static final List<Throwable> ERRORS = new CopyOnWriteArrayList<>();

    @Value("${local.server.port}")
    int port;

    @Test
    void aHandledSynchronousFailureIsLoggedOnceAndOnTheObservation(CapturedOutput output) throws Exception {
        assertFailureIsRecorded("/sync", "sync boom", output);
    }

    @Test
    void aHandledAsyncFailureIsLoggedOnceAndOnTheObservation(CapturedOutput output) throws Exception {
        assertFailureIsRecorded("/async", "async boom", output);
    }

    private void assertFailureIsRecorded(String path, String cause, CapturedOutput output) throws Exception {
        ERRORS.clear();
        var request = HttpRequest.newBuilder(URI.create("http://localhost:" + port + path)).build();
        var response = HttpClient.newHttpClient().send(request, HttpResponse.BodyHandlers.ofString());
        assertThat(response.statusCode()).isEqualTo(500);
        await().untilAsserted(() -> assertThat(ERRORS).extracting(Throwable::getMessage).containsExactly(cause));
        assertThat(output.getOut().split("Request failed with status 500", -1)).hasSize(2);
        assertThat(output.getOut()).contains(cause);
    }

    @TestConfiguration
    @Import({Failing.class, Handler.class})
    static class Setup {
        @Bean
        ObservationHandler<ServerRequestObservationContext> errorRecorder() {
            return new ObservationHandler<>() {
                @Override
                public void onStop(ServerRequestObservationContext context) {
                    if (context.getError() != null) {
                        ERRORS.add(context.getError());
                    }
                }

                @Override
                public boolean supportsContext(Observation.Context context) {
                    return context instanceof ServerRequestObservationContext;
                }
            };
        }
    }

    @RestController
    static class Failing {
        @GetMapping("/sync")
        String sync() {
            throw new IllegalStateException("sync boom");
        }

        @GetMapping("/async")
        Callable<String> async() {
            return () -> {
                throw new IllegalStateException("async boom");
            };
        }
    }

    @RestControllerAdvice
    static class Handler {
        @ExceptionHandler(IllegalStateException.class)
        ProblemDetail handle() {
            return ProblemDetail.forStatusAndDetail(HttpStatus.INTERNAL_SERVER_ERROR, "Something went wrong");
        }
    }
}
JAVA
if "$MVN" -B test -Dtest=HandledFailureTests -Dsurefire.failIfNoSpecifiedTests=false > out.log 2>&1; then pass "HandledFailureFilter: sync and async failures on a real server"
else fail "HandledFailureFilter: sync or async failure missed"; grep -E "Tests run|ERROR|Expect" out.log | head -30; fi
perl -pi -e 's|return false;|return true;|' src/main/java/com/acme/shop/HandledFailureFilter.java
expect_failure "HandledFailureTests: a filter that skips async dispatches" 'aHandledAsyncFailure' test -Dtest=HandledFailureTests -Dsurefire.failIfNoSpecifiedTests=false

# A project on Spring Java Format keeps it: the harness adds no Spotless, and its formatter's own check passes.
FORMATTED=$(mktemp -d)
cp -r "$HERE/project/." "$FORMATTED/"
cp mvnw "$FORMATTED/"
if (
  # set -e doesn't apply inside an if condition, so each step is chained.
  cd "$FORMATTED" \
    && perl -0pi -e 's|(<plugins>)|$1\n      <plugin><groupId>io.spring.javaformat</groupId><artifactId>spring-javaformat-maven-plugin</artifactId><version>0.0.48</version><executions><execution><phase>validate</phase><goals><goal>validate</goal></goals></execution></executions></plugin>|' pom.xml \
    && git init -q && git add -A && git -c user.name=ci -c user.email=ci@example.com commit -qm sample \
    && python3 "$HARNESS/apply_harness.py" . --nullaway "$MODE" | tee apply.log \
    && grep -q "Next: ./mvnw spring-javaformat:apply" apply.log \
    && ! grep -q spotless pom.xml \
    && "$MVN" -B -q spring-javaformat:apply \
    && "$MVN" -B verify
) > format.log 2>&1; then pass "Spring Java Format: kept instead of Spotless, and verify passes"
else fail "Spring Java Format: Spotless added or verify failed"; tail -40 format.log; fi
rm -rf "$FORMATTED" format.log

if [ "$failures" -eq 0 ]; then echo "All harness gates work (JDK $(java -version 2>&1 | grep -v "Picked up" | head -1), NullAway $MODE)"; else echo "$failures check(s) failed"; exit 1; fi
