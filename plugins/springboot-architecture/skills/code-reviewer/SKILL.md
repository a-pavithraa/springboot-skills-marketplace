---
name: code-reviewer
description: Use when reviewing Spring Boot 4 / Java 17+ code with concrete files or diffs (pull requests, modules, or pasted Java and Spring sources) for migration risks, architecture boundary leaks, JSpecify null-safety gaps, security flaws, performance regressions, Spring Data pitfalls, or tests that pass without catching bugs. A test review reports which bugs the suite would let through and which tests fail on correct code, and proves each finding by running it. Not for Kotlin-only code, non-Spring frameworks, or generic review advice without code context.
---

# Spring Boot 4 Reviewer (Java 17+)

## Rules

- Review only code you have. If no files, diff, or module were given, ask for them.
- Cite a file path and line for every finding.
- Read the Java version from `pom.xml` or `build.gradle`. Boot 4 supports Java 17 and later, so Java 17 and 21 are not findings. Java 26 and 27 targets: `../creating-springboot-projects/references/java-version-policy.md`.
- Recommend virtual threads, reactive code, or a new architecture only with evidence from the code: blocking I/O on request threads, a saturated pool, or a boundary that already leaks.
- Use JSpecify as the null-safety baseline for new Boot 4 code. If the codebase is part way through moving to it, report the plan, not every legacy annotation.

## Before Step 1: say who wrote the code

If you wrote or changed the code under review in this session, tell the user that a review from a fresh context is less biased and offer to run it in a general-purpose subagent, giving it the commits and uncommitted changes to review and telling it to follow this skill (`code-reviewer`). Continue only if they decline. Otherwise, review inline.

## Step 1: Load only the references the review needs

| Focus | Read |
|------|------|
| Spring Boot 4 migration patterns and framework changes | `references/spring-boot-4-patterns.md` |
| Java 25 language and concurrency adoption | `references/java-25-features.md` |
| Security | `references/security-checklist.md` |
| Performance | `references/performance-patterns.md` |
| JPA and Hibernate 7 | `references/jpa-performance.md` |
| Architecture boundaries and packaging | `references/architecture-patterns.md` |
| Domain model shape | `references/domain-modeling.md`, `references/value-objects-patterns.md` |
| Null safety | `references/jspecify-null-safety.md` |
| Tests: what they can catch, what they let through | `references/test-review.md` |

For a phased upgrade plan rather than a review, use the `springboot-migration` skill.

## Step 2: Run the passes that match the request

For a full review, run them in this order.

### Pass A: Build and configuration

- Run `../springboot-migration/scripts/scan_migration_issues.py <project>` and cite its CRITICAL lines: old starter names, moved imports, old test annotations, Testcontainers 1.x classes.
- Check for version drift: dependencies pinned by hand that the Boot BOM already manages.

### Pass B: Architecture

- Name the architecture style in use, then report packages and calls that break it.
- Run the architecture tests if they exist (Taikai, ArchUnit, or Spring Modulith's `ApplicationModules.verify()`) and cite their failures. If none exist, recommend `../creating-springboot-projects/assets/architecture-rules-test.java`. A review catches a boundary leak once. A failing build catches it every time.

### Pass C: Security, data access, and performance

Read the matching reference from Step 1 and report against it. Report the affected entry points and how a caller reaches the flaw, not only the rule it breaks.

### Pass D: Null safety

Check public APIs and method overrides against `references/jspecify-null-safety.md`.

### Pass E: Tests

Follow `references/test-review.md`:

1. Run the suite first, so you know what is red before you change anything.
2. Map each class's contract to the test that guards it.
3. Check each test against the "runs the real thing" table.
4. Prove each finding by running it. Restore every file you break with `git checkout -- <file>`.
5. Report in the test-review format, with the bugs the suite would let through first.

## Boot 4 findings the model often misses

- `TestRestTemplate` where `RestTestClient` is available.
- Hand-built `HttpServiceProxyFactory` code where `@ImportHttpServices` does the same.
- Custom API versioning where `spring.mvc.apiversion.*` does the same.
- Jackson 2 imports or types in a Boot 4 codebase.
- `@ConcurrencyLimit` or `@Retryable` that never applies: no `@EnableResilientMethods`; a class that implements an interface without `proxyTargetClass = true`; or a call from inside the same class, which skips the proxy.
- No `package-info.java` where the project uses JSpecify.
- `org.springframework.lang` annotations left in code that has moved to JSpecify.
- An override that drops the nullability annotations of the method it overrides.

## Report format

Order findings by severity:

```markdown
## Critical
- **[Category]**: Issue summary
  - **File**: `path/to/File.java:123`
  - **Impact**: What can fail, leak, or regress
  - **Fix**: Specific change to make

## High
- ...

## Medium
- ...

## Low
- ...
```

If there are no findings, say so. Then name what the review could not see, such as modules not read, missing tests, or runtime behavior.
