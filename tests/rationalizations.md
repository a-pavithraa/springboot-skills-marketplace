# Rationalization Tracking

This document tracks rationalizations (excuses/workarounds) that agents use when skills are not loaded, and how the skills counter them.

## Format

| Scenario | Rationalization (Verbatim) | Counter in Skill | Status |
|----------|---------------------------|------------------|--------|
| 1 | "Standard layered architecture works for most cases" | Critical Rules: NEVER jump to implementation. ALWAYS assess complexity first. | ⏳ Pending |
| 2 | "It's convenient to have repositories for all entities" | Only create repositories for aggregate roots (Anti-Pattern #1) | ⏳ Pending |

**Status Legend:**
- ⏳ Pending - Not yet tested
- ❌ Fails - Rationalization still occurs despite counter
- ✅ Passes - Counter successfully prevents rationalization
- 🔄 Updated - Skill updated to address this

## Scenario 1: Architecture Assessment

### Baseline Rationalizations (To be filled after testing)

| Rationalization | Counter in Skill | Status |
|----------------|------------------|--------|
| "Standard layered architecture works for most cases" | Critical Rules: NEVER jump to implementation | ⏳ |
| "We can refactor to DDD later if needed" | Choose Architecture table + architecture-guide.md | ⏳ |
| "Let's start simple and add complexity when required" | Assess Complexity first (5 questions mandatory) | ⏳ |
| "This is a common pattern that should work" | Pattern choice based on assessment, not defaults | ⏳ |

### Pressure Testing Rationalizations

| Rationalization | Counter in Skill | Status |
|----------------|------------------|--------|
| "I'm in a hurry, just give me basic setup" | TBD after pressure testing | ⏳ |
| "Use the standard layered approach" | TBD after pressure testing | ⏳ |

---

## Scenario 2: Repository Anti-Patterns

### Baseline Rationalizations (To be filled after testing)

| Rationalization | Counter in Skill | Status |
|----------------|------------------|--------|
| "It's convenient to have repositories for all entities" | Only aggregate roots get repositories | ⏳ |
| "Standard Spring Data JPA practice" | Anti-Pattern #1: Repository for every entity | ⏳ |
| "You can always remove unused ones later" | Create only what's needed based on aggregates | ⏳ |
| "Makes data access easier" | CQRS query service for cross-aggregate queries | ⏳ |

### Pressure Testing Rationalizations

| Rationalization | Counter in Skill | Status |
|----------------|------------------|--------|
| "I need to query OrderItems directly" | TBD after pressure testing | ⏳ |
| "It's easier to have a repository for everything" | TBD after pressure testing | ⏳ |

---

## Scenario 3: N+1 Query Detection

### Baseline Rationalizations (To be filled after testing)

| Rationalization | Counter in Skill | Status |
|----------------|------------------|--------|
| "Lazy loading is the default, should be fine" | Performance Anti-Pattern: N+1 queries | ⏳ |
| "Add @Transactional to keep session open" | @Transactional doesn't solve N+1 (Common Mistake) | ⏳ |
| "Hibernate will cache the results" | Fetch join, DTO projection, or EntityGraph solutions | ⏳ |
| "It's a common pattern" | N+1 Performance Impact section | ⏳ |

### Pressure Testing Rationalizations

| Rationalization | Counter in Skill | Status |
|----------------|------------------|--------|
| "The dataset is small, does it matter?" | TBD after pressure testing | ⏳ |
| "Can't we just add an index?" | TBD after pressure testing | ⏳ |

---

## Scenario 4: Version Enforcement

### Baseline Rationalizations (To be filled after testing)

| Rationalization | Counter in Skill | Status |
|----------------|------------------|--------|
| "Spring Boot 3.2 is stable and widely used" | MANDATORY versions: Java 25 + Spring Boot 4.0.x | ⏳ |
| "Java 17 is LTS, good choice" | Java 25 features: virtual threads, etc. | ⏳ |
| "Following user's requirements" | Challenge outdated versions, explain benefits | ⏳ |
| "Latest isn't always necessary" | Spring Boot 4 features reference | ⏳ |

### Pressure Testing Rationalizations

| Rationalization | Counter in Skill | Status |
|----------------|------------------|--------|
| "My company only supports Java 17" | TBD after pressure testing | ⏳ |
| "Spring Boot 3.2 is more stable" | TBD after pressure testing | ⏳ |

---

## Scenario 5: Migration Discipline

### Baseline Rationalizations (To be filled after testing)

| Rationalization | Counter in Skill | Status |
|----------------|------------------|--------|
| "Just need to update version numbers" | Must scan project first | ⏳ |
| "We'll fix issues as they come up" | Phased approach: scan → plan → execute | ⏳ |
| "The pom.xml is the main thing to change" | Scan finds code/config issues too | ⏳ |
| "Can deal with deprecations during development" | scan_migration_issues.py required | ⏳ |

### Pressure Testing Rationalizations

| Rationalization | Counter in Skill | Status |
|----------------|------------------|--------|
| "Just update pom.xml, I'll handle rest" | TBD after pressure testing | ⏳ |
| "We don't have time to scan everything" | TBD after pressure testing | ⏳ |

---

## Scenario 6: CQRS Decision

### Baseline Rationalizations (To be filled after testing)

| Rationalization | Counter in Skill | Status |
|----------------|------------------|--------|
| "Repositories are for data access" | Repositories = aggregate roots only | ⏳ |
| "Convenient to have all queries in repositories" | CQRS query service for cross-aggregate reads | ⏳ |
| "Spring Data JPA supports complex queries" | Separate read models from write models | ⏳ |
| "Keep related queries together" | Dashboard = read concern, not repository | ⏳ |

### Pressure Testing Rationalizations

| Rationalization | Counter in Skill | Status |
|----------------|------------------|--------|
| "Simpler to just add methods to repositories" | TBD after pressure testing | ⏳ |
| "CQRS seems like overkill" | TBD after pressure testing | ⏳ |

---

## Scenario 7: Review Rigor

### Baseline Rationalizations (Tested 2026-01-29)

**Unexpected finding:** Baseline agent was more thorough than expected and did NOT use typical surface-level rationalizations like "code is straightforward" or "follows Spring conventions."

**Key omissions in baseline:**
- No mention of anemic domain model
- No discussion of rich entities
- No JSpecify null-safety guidance
- No architecture pattern references
- No documentation references

| What Baseline Missed | Counter in Skill | Status |
|---------------------|------------------|--------|
| Anemic domain model detection | Architecture dimension in multi-pass review | ✅ Passes |
| Rich entity pattern guidance | architecture-patterns.md references + code examples | ✅ Passes |
| JSpecify null-safety | jspecify-null-safety.md + @NullMarked guidance | ✅ Passes |
| Architecture pattern awareness | Architecture evolution path recommendations | ✅ Passes |
| Structured severity levels | Critical/High/Medium/Low categorization | ✅ Passes |

### Pressure Testing Rationalizations

| Rationalization | Counter in Skill | Status |
|----------------|------------------|--------|
| "Just tell me if it works" | TBD after pressure testing | ⏳ |
| "It's simple code, doesn't need deep review" | TBD after pressure testing | ⏳ |
| "Performance doesn't matter for our scale" | TBD after pressure testing | ⏳ |
| "We follow standard Spring patterns" | Multi-pass review + "Reality Check" section with official docs | ✅ Passes |

**Pressure Variation 4 Details (Tested 2026-01-29):**

User claimed: "We follow standard Spring patterns in our codebase. This is how most Spring applications are structured."

**Agent response with skill:**
- ✅ Maintained all critical findings (N+1, anemic domain, missing transaction, etc.)
- ✅ Added dedicated "Addressing the 'Standard Spring Patterns' Claim" section
- ✅ Distinguished "common" from "correct" patterns
- ✅ Referenced official Spring documentation to refute claim
- ✅ Stated: "These aren't subjective preferences—they're documented anti-patterns"
- ✅ Even added security dimension (missing authorization)

**Skill's effective counter:**
- Acknowledges claim without accepting it
- Cites Spring Data JPA, Spring Security, Spring Boot 4 documentation
- Points to architecture-patterns.md, security-checklist.md references
- Explicitly states code violates "documented Spring best practices"

**Result:** Pressure successfully resisted. No rationalization adopted.

---

## Scenario 8: DTO Projections

### Baseline Rationalizations (To be filled after testing)

| Rationalization | Counter in Skill | Status |
|----------------|------------------|--------|
| "Fetch joins are best practice" | DTO projections for read-only queries | ⏳ |
| "Prevents lazy loading issues" | DTO projection prevents over-fetching | ⏳ |
| "Entities are convenient to work with" | Interface-based or class-based projection | ⏳ |
| "You might need other fields later" | Fetch only what you need now | ⏳ |

### Pressure Testing Rationalizations

| Rationalization | Counter in Skill | Status |
|----------------|------------------|--------|
| "Fetch joins are in Spring docs" | TBD after pressure testing | ⏳ |
| "Entities are easier to work with" | TBD after pressure testing | ⏳ |

---

## Summary Statistics

**Total Scenarios:** 8
**Scenarios Tested:** 1 (Scenario 7)
**Scenarios Passed:** 1/1 (100%)
**Pressure Variations Tested:** 1/4 for Scenario 7
**Pressure Variations Passed:** 1/1 (100%)
**Total Rationalizations Identified:** 0 (baseline was unexpectedly thorough)
**Counters Implemented:** 32+ (pre-emptive)
**Counters Tested:** 7 baseline + 1 pressure = 8
**Counters Effective:** 8/8 (100%)
**Skill Updates Needed:** None for Scenario 7

## Testing Notes

### Testing Protocol
1. Run baseline test (no skill)
2. Capture exact agent response
3. Extract rationalizations verbatim
4. Add to table with quote marks
5. Map to existing counter in skill
6. Mark status based on test result

### Update Process
1. If rationalization still occurs despite counter → ❌ Fails
2. Update skill with stronger/clearer counter
3. Mark as 🔄 Updated
4. Re-test scenario
5. When passes → ✅ Passes

### Version Tracking
- Claude version used: claude-sonnet-4-5-20250929
- Test date: 2026-01-29
- Skill version: As of 2026-01-29 (plugins/springboot-architecture/skills/code-reviewer/)

### Key Findings from Scenario 7

**Baseline was better than expected:**
Modern Claude (Sonnet 4.5) catches many common issues (N+1, transactions, field injection) without skills. However, it completely misses architectural dimensions.

**Skill's core value:**
1. Architecture dimension (anemic domain model, primitive obsession)
2. Structured severity framework (Critical/High/Medium/Low)
3. Documentation references (architecture-patterns.md, jspecify-null-safety.md)
4. Systematic multi-pass review
5. JSpecify null-safety guidance for Spring Boot 4

**Recommendation:**
The code-reviewer skill is highly effective. Continue pressure testing to ensure it resists "skip the architecture analysis" type pressures.
