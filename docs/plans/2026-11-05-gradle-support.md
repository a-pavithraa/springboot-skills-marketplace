# Gradle support for the team harness

The harness runs on Maven only (`SKILL.md` Limits). This plan brings the same gates, hooks, baseline and CI to a
single-project Gradle build, in Groovy or Kotlin DSL.

## Design

**One owned script plugin, one line in the build.** `apply_harness.py` writes `gradle/harness.gradle` and appends
`apply from: "gradle/harness.gradle"` (Groovy) or `apply(from = "gradle/harness.gradle")` (Kotlin) to the build file.
The script carries its own `buildscript` classpath (`net.ltgt.errorprone` 5.2.0, `com.diffplug.spotless` 8.11.0), so
the team's `plugins {}` block is never edited. The harness owns the script through `.claude/harness.lock`, like its
tests and hooks, so a rerun updates versions and rules in a script nobody edited. On Maven, the pom is patched and
never updated; Gradle gets the better deal for free.

The script:

- applies Error Prone with NullAway on `compileJava` only (JSpecify mode, `AnnotatedPackages` or `OnlyNullMarked`),
  plus `-XDaddTypeAnnotationsToSymbol=true`. The Error Prone plugin forks javac with the `--add-exports` that Maven
  needs `.mvn/jvm.config` for.
- applies Spotless with palantir-java-format, `target` narrowed by `-PharnessFiles=a.java,b.java` for the Stop hook.
  Skipped when the build applies `io.spring.javaformat`.
- adds `jspecify`, `spring-modulith-starter-test` with the Modulith BOM as a `platform`, and ArchUnit when neither
  ArchUnit nor Taikai is declared. Observability dependencies come in a rendered block, as on Maven.
- registers `harnessCheck`, a `Test` task running the fast gates with `failOnNoMatchingTests = false`, which the
  Stop hook calls instead of Maven's `-Dtest=... -Dsurefire.failIfNoSpecifiedTests=false`.
- forwards `-Pharness.record` to the test JVM as ArchUnit's `allowStoreCreation` and Modulith's
  `modulith.store.record`, for `baseline.py` only. Gradle doesn't pass `-D` to tests.
- writes the declared dependencies (configuration, group, artifact) to `build/harness/declared-dependencies.txt`
  before `test`, and passes its path to the tests. `BuildSetupTests` reads it instead of parsing `pom.xml`: Gradle
  build files can't be parsed from Java, and the report sees version-catalog entries too.
- shows full exceptions for failed tests, so ArchUnit's `was violated` lines reach the console and the hook.

`apply_harness.py` stops, as it does for a configured `maven-compiler-plugin`, when the build already applies
Error Prone: two copies of a plugin on different classloaders fail at configuration time. A build's own Spotless is
kept, as on Maven (progen's Gradle projects apply it); the script only narrows its target to `-PharnessFiles` for the
Stop hook. It also stops on a multi-project build (`include` in `settings.gradle(.kts)`); multi-module is a separate
design for both tools.

Spike result (Gradle 9.8.2, JDK 25, Docker): the `buildscript` block in a script plugin works from both DSLs and
with the configuration cache; NullAway prints `path:line: error: [NullAway]`; Spotless formats only the named file;
`harnessCheck` passes with no matching tests; `-Pharness.record` reaches the test JVM. Under `-q`, failed tests print
only with `testLogging.quiet` set, and their lines are indented, so the hook strips leading space before matching.

**Build tool detected, not passed.** `pom.xml` means Maven, `build.gradle(.kts)` means Gradle; both present stops
with a message. The hook detects the same way at run time.

## Per piece

| Piece | Maven today | Gradle |
| --- | --- | --- |
| Build gates | pom fragments | `gradle/harness.gradle` + one `apply from` line |
| `.mvn/jvm.config` | Error Prone exports | none; the plugin forks javac |
| Stop hook format | `spotless:apply -DspotlessFiles=` | `spotlessApply -PharnessFiles=` |
| Stop hook gates | `test -Dtest=$FAST_TESTS` | `harnessCheck` |
| Hook error parsing | `[ERROR] path:[l,c]` | `path:l: error:` and Gradle's test failure lines |
| Build file as a changed file | `pom.xml` | `build.gradle(.kts)`, `settings.gradle(.kts)`, `gradle/libs.versions.toml` |
| `baseline.py` | `mvnw compile`, `-D` flags | `gradlew compileJava`, `-Pharness.record` |
| CI | `cache: maven`, `./mvnw -B verify` | `cache: gradle`, `./gradlew build` |
| Done means | `./mvnw verify` | `./gradlew build` |
| `move-code` skill | rewrite-maven-plugin | OpenRewrite through an init script, no build change |
| Settings permissions | `./mvnw *` | `./gradlew *` |
| Starter detection (observability, Flyway skill) | pom text | build file and `gradle/libs.versions.toml` text |

Templates take `{{VERIFY}}` (`./mvnw verify` or `./gradlew build`) and `{{BUILD_DIR}}` placeholders, and
`<!-- maven:begin -->` / `<!-- gradle:begin -->` blocks where whole steps differ, rendered like the module blocks.

## Phases

Each phase leaves Maven behaviour unchanged; the existing script tests and the Maven sample check prove that.

1. **Spike** (riskiest premise first). A minimal Gradle 9.8 project in Docker with a hand-written
   `gradle/harness.gradle`: NullAway fails a null return, Spotless formats one named file, `harnessCheck` passes with
   absent test classes, `-Pharness.record` reaches the test JVM. If `buildscript` in a script plugin fails, fall back
   to inserting `id` lines into `plugins {}`.
2. **Apply.** Build-tool detection, the script asset, the `apply from` line, the stop conditions, placeholders,
   CI template and detection of an existing Gradle workflow, settings permissions. Unit tests in
   `tests/scripts/test_apply_harness.py`.
3. **BuildSetupTests** reads the dependency report when present.
4. **Hooks and baseline.** Gradle branch in `verify-on-stop.sh` and `baseline.py`; hook tests with a fake `gradlew`.
5. **Docs.** `SKILL.md` (Apply steps name both commands; Limits names multi-project, Kotlin sources), `README.md`,
   `tests/README.md`.
6. **End to end.** `tests/harness-sample/check-gradle.sh groovy|kotlin` writes a Gradle build for the sample sources
   and checks each gate, the Stop hook, `baseline.py`, the integrity check and the `move-code` init script.
   `check-gradle-in-docker.sh` runs it in `gradle:9.8.2-jdk25`; `harness-build.yml` runs both DSLs in CI.

## Out of scope

Multi-project Gradle builds, Kotlin source code, Gradle Enterprise or build-cache tuning, and the Android plugin.
