# JSpecify Null-Safety (Spring Boot 4 / Spring Framework 7)

## Purpose

Use JSpecify annotations to make nullability explicit in Spring applications and libraries. Spring Framework 7 and the Spring Boot 4 portfolio expose null-safe APIs with JSpecify; application code should align with those contracts and avoid deprecated Spring null-safety annotations.

## Important: Optional for Applications

**JSpecify is OPTIONAL for application code.** While Spring Boot 4 and Spring Framework 7 internally use JSpecify annotations, applications can:

1. **Adopt JSpecify** (recommended for new projects) - Full type-safety with modern tooling
2. **Keep using Spring's `org.springframework.lang` annotations** (acceptable during transition) - Will work but are deprecated
3. **Use no null-safety annotations** (not recommended but supported) - No compile-time null checking

**When to use JSpecify:**
- New Spring Boot 4 projects
- Projects wanting modern IDE/tooling support
- Libraries that need to interoperate with Spring's null-safe APIs

**When Spring's annotations are acceptable:**
- Existing Spring Boot 3 applications migrating gradually
- Teams not yet ready for type-use annotation syntax
- Legacy codebases with extensive Spring annotation usage

## Core Rules

- **Default non-null** via `@NullMarked` in `package-info.java`.
- **Explicit nullable** with `@Nullable` at the type-use site.
- **Avoid deprecated Spring annotations** from `org.springframework.lang` (`@Nullable`, `@NonNull`, `@NonNullApi`, `@NonNullFields`).
- **Copy nullability annotations on overrides** (JSpecify annotations are not inherited).

## Annotation Placement (Type-Use)

JSpecify annotations are `TYPE_USE`, so place them directly before the type.

```java
// field
private @Nullable String fileEncoding;

// parameter + return type
public @Nullable String buildMessage(@Nullable String message) { ... }
```

### Arrays and Varargs

Type-use syntax matters:

```java
@Nullable Object[] array;          // elements nullable, array non-null
Object @Nullable [] array;         // elements non-null, array nullable
@Nullable Object @Nullable [] arr; // both nullable
```

### Generics

```java
List<String>            // non-null elements
List<@Nullable String>  // nullable elements
```

### Nested and Fully-Qualified Types

Type-use annotations appear after the last dot:

```java
Cache.@Nullable ValueWrapper
jakarta.validation.@Nullable Validator
```

## Migration from org.springframework.lang

Spring’s legacy null-safety annotations are deprecated in Spring Framework 7 in favor of JSpecify. JSpecify is type-use only, so array/varargs declarations must be updated to preserve semantics (for example, `@Nullable Object[]` becomes `Object @Nullable []`).

Place annotations next to the type instead of at the far left:

```java
// before (legacy style)
@Nullable private String field;
@Nullable public String method();

// after (JSpecify style)
private @Nullable String field;
public @Nullable String method();
```

## NullAway (Build-Time Checking)

If the goal is application-wide null-safety, use NullAway:

- Recommended: `NullAway:OnlyNullMarked=true` (checks only `@NullMarked` packages)
- Optional: `NullAway:CustomContractAnnotations=org.springframework.lang.Contract`
- Optional (second step): `NullAway:JSpecifyMode=true` for full JSpecify semantics

## Tooling Guidance

- IDEs can surface nullability issues when JSpecify annotations are present.
- NullAway JSpecify mode requires a recent javac (Spring docs mention JDK 22+). Spring Boot 4 guidance recommends Java 25, or a recent JDK 21.0.8+ with `-XDaddTypeAnnotationsToSymbol=true` if Java 25 is not possible.
- If you must keep a Java 17 baseline, use a Java 25 toolchain with `--release 17`.

---

## Official Documentation

- [JSpecify Reference Documentation](https://jspecify.dev/)
- [JSpecify User Guide](https://jspecify.dev/docs/user-guide)
- [Spring Framework Null-Safety](https://docs.spring.io/spring-framework/reference/core/null-safety.html)
- [NullAway - Uber's Null-Safety Tool](https://github.com/uber/NullAway)
- [JSpecify GitHub Repository](https://github.com/jspecify/jspecify)
- [Spring Boot 4 Migration Guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide)
