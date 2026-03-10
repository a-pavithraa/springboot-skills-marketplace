---
name: spring-data-jpa
description: Designs and implements Spring Data JPA repositories, projections, query patterns, custom repositories, CQRS read models, entity relationships, and persistence performance fixes for Java 25 and Spring Boot 4 projects. Use when the task needs repository-boundary decisions or concrete JPA implementation patterns from this skill. Do not use for generic SQL help or project-wide migration work that belongs in another skill.
---

# Spring Data JPA Implementation

## Purpose

Use this skill when the task is specifically about persistence design or implementation in a Spring Boot codebase. This skill adds value through aggregate-root guidance, query-pattern selection, CQRS read-model decisions, and the bundled repository and relationship templates.

## Critical rules

- Never create repositories for every entity. Create repositories only for aggregate roots.
- Never rely on long derived query method names when the query has become non-trivial.
- Never use `save()` blindly when entity state transitions matter; understand persist versus merge behavior.
- Prefer projections or dedicated query services for read-heavy paths.
- Keep transaction boundaries in the service layer unless the existing architecture intentionally does otherwise.

## Workflow

### Step 1: Identify the persistence problem

Collect the minimum context first:

1. Is the type an aggregate root or an internal entity?
2. Is the task primarily read-side, write-side, or both?
3. Is the query simple lookup, filtered search, aggregation, projection, or dynamic criteria?
4. Is the path performance-sensitive?
5. Are there module-boundary or loose-coupling constraints that affect relationship modeling?

### Step 2: Choose the implementation pattern

Use this table to decide what to load next.

| Pattern | Use when | Read |
|---------|----------|------|
| Simple repository | Basic CRUD and 1-2 simple lookups | Existing code or none |
| `@Query` repository | Multiple filters, joins, sorting, readable JPQL | `references/query-patterns.md` |
| DTO projection | Read-only and performance-critical responses | `references/dto-projections.md` |
| Custom repository | Criteria API, bulk operations, EntityManager logic | `references/custom-repositories.md` |
| CQRS query service | Separate read and write models, reporting, specialized read paths | `references/cqrs-query-service.md` |

Use this decision guide:

| Need | Simple | `@Query` | DTO | Custom | CQRS |
|------|--------|----------|-----|--------|------|
| Basic CRUD | Yes | Yes | No | Yes | Yes |
| Custom filters | No | Yes | Yes | Yes | Yes |
| Best read performance | No | Sometimes | Yes | Sometimes | Yes |
| Complex dynamic logic | No | No | No | Yes | Yes |
| Clear read/write split | No | No | Sometimes | Sometimes | Yes |

### Step 3: Load the matching reference

Load only the references needed for the current task:

- `references/query-patterns.md`
- `references/dto-projections.md`
- `references/custom-repositories.md`
- `references/cqrs-query-service.md`
- `references/relationships.md`
- `references/performance-guide.md`

### Step 4: Apply the matching asset

Use the bundled templates in `assets/` instead of rebuilding the pattern from scratch:

- `assets/query-repository.java`
- `assets/dto-projection.java`
- `assets/custom-repository.java`
- `assets/query-service.java`
- `assets/relationship-patterns.java`

### Step 5: Validate relationships and transaction boundaries

Before finalizing the change, check:

- repository exists only at the aggregate-root boundary
- lazy-loading behavior is intentional
- pagination or projections are used where row counts can grow
- `@ManyToMany` has not been introduced when a join entity is more appropriate
- read services use `@Transactional(readOnly = true)` where appropriate
- write operations stay in service-layer transactions

### Step 6: Validate performance-sensitive paths

Read `references/performance-guide.md` when the task includes:

- N+1 risks
- fetch-plan problems
- unbounded queries
- batch operations
- heavy read views that should use projections

## High-value patterns to prefer

### Repository boundaries

- Aggregate roots get repositories.
- Internal child entities usually do not.

### Query style

- Use derived query methods for simple lookups.
- Use `@Query` for joins, readable text blocks, or multiple filters.
- Use DTO projections when the response does not need entities.
- Use a CQRS query service when the read model differs from the write model.

### Relationships

- Prefer `@ManyToOne` over `@OneToMany` when possible.
- Use IDs instead of entity references when loose coupling is more important than navigation.
- Treat `@ManyToMany` as a warning sign; prefer an explicit join entity.

## Output format

When proposing or implementing a persistence change, return:

```markdown
## Recommended pattern
- Pattern:
- Why:

## Files to change
- `path/to/file`

## References used
- `references/...`

## Risks to verify
- ...
```

## When not to use this skill

- Generic SQL or database administration work outside Spring Data JPA
- Whole-project migration planning
- Broad project scaffolding that belongs in `creating-springboot-projects`
