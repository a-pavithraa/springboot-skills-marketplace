/**
 * JSpecify Null-Safety Configuration (Spring Boot 4).
 *
 * Spring Boot 4 includes jSpecify for compile-time null safety.
 * Apply @NullMarked at package level to enable null checking for the entire package.
 *
 * Benefits:
 * - Catch NullPointerExceptions at compile time
 * - Better IDE support (IntelliJ, Eclipse)
 * - Improved code documentation
 * - Works with Kotlin null safety
 * - Integrated with Spring's nullability annotations
 *
 * Usage:
 * 1. Add @NullMarked to package-info.java
 * 2. All types in package are non-null by default
 * 3. Use @Nullable for explicitly nullable types
 * 4. IDE shows warnings for potential null issues
 *
 * Best Practices:
 * - Enable null checking in your IDE/build tool
 * - Use Optional<T> for optional return values
 * - Validate inputs at API boundaries
 * - Don't suppress null warnings without fixing root cause
 *
 * Example violations caught:
 * - Assigning null to non-null field
 * - Returning null from non-null method
 * - Passing null to non-null parameter
 * - Dereferencing potentially null value
 */
@NullMarked
package {{PACKAGE}}.{{MODULE}};

import org.jspecify.annotations.NullMarked;

// ============================================================
// USING @Nullable FOR OPTIONAL FIELDS
// ============================================================

// package {{PACKAGE}}.{{MODULE}}.domain;
//
// import org.jspecify.annotations.Nullable;
//
// /**
//  * Entity with JSpecify null-safety.
//  *
//  * Fields are non-null by default due to package-level @NullMarked.
//  * Use @Nullable for optional fields.
//  */
// public class {{NAME}}Entity {
//     private Long id;                    // Non-null (required)
//     private String name;                // Non-null (required)
//     @Nullable private String description;  // Nullable (optional)
//     @Nullable private String imageUrl;     // Nullable (optional)
//
//     public {{NAME}}Entity(Long id, String name) {
//         this.id = id;
//         this.name = name;
//     }
//
//     // Getters are non-null by default
//     public Long getId() {
//         return id;
//     }
//
//     public String getName() {
//         return name;
//     }
//
//     // Mark getter as @Nullable for optional fields
//     public @Nullable String getDescription() {
//         return description;
//     }
//
//     // Setters accept @Nullable for optional fields
//     public void setDescription(@Nullable String description) {
//         this.description = description;
//     }
// }

// ============================================================
// COMBINING WITH OPTIONAL<T>
// ============================================================

// package {{PACKAGE}}.{{MODULE}}.repository;
//
// import java.util.Optional;
//
// /**
//  * Repository with JSpecify + Optional.
//  *
//  * Use Optional<T> for methods that might not return a value.
//  * This is more expressive than @Nullable for return types.
//  */
// public interface {{NAME}}Repository extends JpaRepository<{{NAME}}Entity, Long> {
//
//     // Good: Use Optional for potentially absent values
//     Optional<{{NAME}}Entity> findByName(String name);
//
//     // Avoid: Don't use @Nullable for return types when Optional is better
//     // @Nullable {{NAME}}Entity findByName(String name);
//
//     // Good: List is never null (returns empty list instead)
//     List<{{NAME}}Entity> findByStatus(String status);
//
//     // Good: Non-null parameters by default
//     boolean existsByName(String name);
// }

// ============================================================
// VALIDATION AT API BOUNDARIES
// ============================================================

// package {{PACKAGE}}.{{MODULE}}.rest;
//
// import jakarta.validation.Valid;
// import jakarta.validation.constraints.NotNull;
// import org.springframework.web.bind.annotation.*;
//
// /**
//  * Controller with JSpecify + Jakarta Validation.
//  *
//  * JSpecify handles compile-time checks.
//  * Jakarta Validation handles runtime validation.
//  */
// @RestController
// @RequestMapping("/api/{{MODULE}}")
// public class {{NAME}}Controller {
//
//     private final {{NAME}}Service service;
//
//     public {{NAME}}Controller({{NAME}}Service service) {
//         this.service = service;
//     }
//
//     // JSpecify ensures id parameter is non-null at compile time
//     // Spring validates path variable is present at runtime
//     @GetMapping("/{id}")
//     public {{NAME}}VM getById(@PathVariable @NotNull Long id) {
//         return service.findById(id);
//     }
//
//     // @Valid ensures request body validation
//     // JSpecify ensures no null request body at compile time
//     @PostMapping
//     public {{NAME}}VM create(@RequestBody @Valid Create{{NAME}}Request request) {
//         return service.create(request);
//     }
//
//     // Query parameter can be null - explicitly mark with @Nullable
//     @GetMapping("/search")
//     public List<{{NAME}}VM> search(
//             @RequestParam @Nullable String query,
//             @RequestParam(defaultValue = "0") int page
//     ) {
//         return service.search(query, page);
//     }
// }

// ============================================================
// SERVICE LAYER WITH NULL SAFETY
// ============================================================

// package {{PACKAGE}}.{{MODULE}}.service;
//
// import org.jspecify.annotations.Nullable;
// import java.util.List;
//
// /**
//  * Service with defensive null checking.
//  */
// @Service
// public class {{NAME}}Service {
//
//     private final {{NAME}}Repository repository;
//
//     public {{NAME}}Service({{NAME}}Repository repository) {
//         this.repository = repository;
//     }
//
//     // Non-null return guaranteed (throws if not found)
//     public {{NAME}}VM findById(Long id) {
//         return repository.findById(id)
//                 .map(this::toViewModel)
//                 .orElseThrow(() -> new NotFoundException("Not found: " + id));
//     }
//
//     // Search with optional query - explicitly marked @Nullable
//     public List<{{NAME}}VM> search(@Nullable String query, int page) {
//         if (query == null || query.isBlank()) {
//             return repository.findAll(PageRequest.of(page, 20))
//                     .map(this::toViewModel)
//                     .getContent();
//         }
//         return repository.searchByName(query, PageRequest.of(page, 20))
//                 .map(this::toViewModel)
//                 .getContent();
//     }
//
//     // Private helper - non-null guaranteed
//     private {{NAME}}VM toViewModel({{NAME}}Entity entity) {
//         return new {{NAME}}VM(
//                 entity.getId(),
//                 entity.getName(),
//                 entity.getDescription()  // Can be null, VM handles it
//         );
//     }
// }

// ============================================================
// RECORDS WITH JSPECIFY
// ============================================================

// package {{PACKAGE}}.{{MODULE}}.domain.models;
//
// import org.jspecify.annotations.Nullable;
//
// /**
//  * Record with null-safe fields.
//  *
//  * JSpecify works seamlessly with records.
//  */
// public record {{NAME}}VM(
//         Long id,                      // Non-null
//         String name,                  // Non-null
//         @Nullable String description  // Nullable
// ) {
//     // Compact constructor for validation
//     public {{NAME}}VM {
//         if (id == null || id <= 0) {
//             throw new IllegalArgumentException("ID must be positive");
//         }
//         if (name == null || name.isBlank()) {
//             throw new IllegalArgumentException("Name is required");
//         }
//         // description can be null - no validation needed
//     }
// }

// ============================================================
// IDE CONFIGURATION
// ============================================================

// IntelliJ IDEA:
// 1. Settings → Editor → Inspections
// 2. Enable "Probable bugs → Nullability problems"
// 3. Configure → Use JSpecify annotations
// 4. IDE will show warnings for potential null issues
//
// Eclipse:
// 1. Preferences → Java → Compiler → Errors/Warnings
// 2. Enable "Null analysis"
// 3. Configure → Use external annotations
// 4. Add JSpecify to annotation path

// ============================================================
// BUILD CONFIGURATION (pom.xml)
// ============================================================

// <!-- JSpecify is included in Spring Boot 4 by default -->
// <!-- For additional null checking tools: -->
// <build>
//     <plugins>
//         <plugin>
//             <groupId>org.apache.maven.plugins</groupId>
//             <artifactId>maven-compiler-plugin</artifactId>
//             <configuration>
//                 <compilerArgs>
//                     <arg>-Xlint:all</arg>
//                     <arg>-Werror</arg>  <!-- Treat warnings as errors -->
//                 </compilerArgs>
//             </configuration>
//         </plugin>
//     </plugins>
// </build>

// ============================================================
// COMMON PATTERNS
// ============================================================

// 1. Use @Nullable sparingly - most things should be non-null
// 2. Prefer Optional<T> for return types over @Nullable
// 3. Use @Nullable for optional fields in entities/records
// 4. Validate at API boundaries (controllers, external integrations)
// 5. Fail fast - throw exceptions early for invalid nulls
// 6. Document null behavior in method contracts
