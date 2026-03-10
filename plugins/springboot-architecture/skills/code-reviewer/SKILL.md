---
name: code-reviewer
description: Reviews Java 25 and Spring Boot 4 codebases, pull requests, files, and modules for migration risks, architecture boundary violations, JSpecify null-safety issues, security flaws, performance regressions, and Spring Data pitfalls. Use when the task is a concrete Java or Spring code review with code context. Do not use for Kotlin-only code, non-Spring frameworks, or generic review advice without files or diffs.
---

# Java 25 and Spring Boot 4 Reviewer

## Purpose

Use this skill to run a structured review of Java 25 and Spring Boot 4 code. Keep findings grounded in the actual codebase and use the reference files only for the focus areas that apply.

## Critical rules

- Never review without code context. Ask for files, diffs, or the relevant module if none is provided.
- Always cite file paths and line numbers for findings.
- Treat Java 25 and Spring Boot 4 as the target baseline unless the build files show otherwise.
- Analyze workload before recommending virtual threads, reactive rewrites, or architecture changes.
- Use JSpecify as the preferred null-safety baseline for new Boot 4 code, but confirm whether the codebase is still in transition before flagging every legacy annotation.
- Prefer official Spring and Java guidance when a claim depends on framework behavior.

## Workflow

### Step 1: Confirm scope

Collect the minimum context required to review accurately:

1. Scope: single file, module, PR, or full codebase.
2. Target versions: confirm Java and Spring Boot versions from the build files when relevant.
3. Focus areas: migration, architecture, data access, security, performance, null-safety, or all.
4. Testing context: whether the user expects review findings only or also fix suggestions and test impact.

### Step 2: Load only the references that match the review

Load references just in time:

| Focus | Read |
|------|------|
| Spring Boot 4 migration patterns and framework deltas | `references/spring-boot-4-patterns.md` |
| Java 25 language and concurrency adoption | `references/java-25-features.md` |
| Security review | `references/security-checklist.md` |
| Performance review | `references/performance-patterns.md` |
| Architecture boundaries and packaging | `references/architecture-patterns.md` |
| Domain model shape | `references/domain-modeling.md` |
| Value-object-heavy designs | `references/value-objects-patterns.md` |
| Null-safety checks | `references/jspecify-null-safety.md` |

Escalate to another skill when needed:

- Use `spring-data-jpa` for deep repository, query, and relationship work.
- Use `springboot-migration` for phased upgrade planning or upgrade execution.

### Step 3: Run the review passes

Run only the passes that match the request. For a full review, use this order.

#### Pass A: Build and configuration

- Verify Java and Spring Boot versions in `pom.xml` or `build.gradle`.
- Check starter names and migration leftovers.
- Scan for Jackson 3 migration issues, outdated test annotations, and version drift.

#### Pass B: API correctness

- Check controller and service boundaries.
- Check validation and error handling.
- Check nullability in public APIs and method overrides.

#### Pass C: Architecture and packaging

- Identify the architecture style in use.
- Verify package structure is consistent with that style.
- Flag boundary leaks such as controller-to-repository shortcuts or infrastructure types in domain code.

#### Pass D: Data access

- Check repository placement and aggregate boundaries.
- Check for N+1 queries, missing pagination, projection mismatches, and transaction misuse.

#### Pass E: Security

- Check authentication and authorization.
- Check input validation and unsafe query patterns.
- Check secrets handling and sensitive logging.

#### Pass F: Performance and resilience

- Check caching strategy, unbounded reads, async usage, and remote call behavior.
- Evaluate virtual-thread usage only when the code and workload justify it.
- Check timeouts, retries, and connection-pool assumptions.

## Quick triggers for findings

Use these as review prompts, not as a substitute for code evidence.

### Spring Boot 4 and migration

- old starter names
- old Mockito test annotations
- Jackson 2 assumptions in a Boot 4 codebase

### Null-safety

- missing `package-info.java` where the project uses JSpecify
- lingering `org.springframework.lang` annotations in code that has already moved to JSpecify
- missing copied nullability annotations on overrides

### Architecture

- controllers calling repositories directly
- JPA entities exposed in APIs
- modulith boundary leaks
- business logic concentrated in controllers

### Performance

- entity traversal in loops
- missing pagination
- projection opportunities ignored on read-heavy paths
- virtual-thread recommendations with no workload evidence

### Security

- missing authorization on privileged actions
- SQL or NoSQL injection risk
- secrets in source or logs
- unsafe error exposure

## Report format

Order findings by severity and use this template:

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

If there are no findings, say so explicitly and call out any remaining blind spots such as unreviewed modules, missing tests, or unavailable runtime context.

## Common review modes

### Quick PR review

1. Read the changed files.
2. Load `references/spring-boot-4-patterns.md` and `references/java-25-features.md`.
3. Add `references/security-checklist.md` or `references/performance-patterns.md` if the diff touches those areas.
4. Report only concrete findings with file and line references.

### Security review

1. Read `references/security-checklist.md`.
2. Focus on controllers, service entry points, security configuration, and persistence boundaries.
3. Report exploitability and affected entry points, not just the violated rule.

### Architecture review

1. Read `references/architecture-patterns.md`.
2. Add `references/domain-modeling.md` or `references/value-objects-patterns.md` if the code suggests a rich-domain approach.
3. Report boundary mismatches and coupling problems tied to the current architecture style.

### Migration review

1. Read `references/spring-boot-4-patterns.md` and `references/java-25-features.md`.
2. Focus on migration leftovers, outdated APIs, and partial adoption problems.
3. Use `springboot-migration` if the user wants a phased upgrade plan rather than a review.

## When not to use this skill

- Kotlin-first codebases
- Non-Spring Java frameworks such as Micronaut or Quarkus
- Generic review coaching without code context
- Frontend-only changes
