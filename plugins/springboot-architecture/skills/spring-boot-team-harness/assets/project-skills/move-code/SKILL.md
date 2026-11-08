---
name: move-code
description: Moves a Java class or package to another package in this project with OpenRewrite, so every import, fully qualified reference, Javadoc link, properties value and META-INF/services entry follows, the same way each time. Use when the user asks to move, relocate or repackage a class or package, or to rename a package, to restructure code into modules, or when a fix would mean moving a type across modules.
---

# Move a class or package

Don't move Java files by hand or with text edits: imports and references in other files go stale, and names in resources are missed.

1. Decide whether a move is the fix. To clear a module-boundary violation, prefer a facade in the target module's top-level package or an event; moving an internal type into a module's top-level package publishes it to every module. A move fits when the type belongs to another module, or when restructuring into modules.
2. Write the recipe to a file in a temporary folder outside the repository, here `$TMPDIR/move.yml`, so nothing is left to commit:
   ```yaml
   type: specs.openrewrite.org/v1beta/recipe
   name: local.Move
   recipeList:
     - org.openrewrite.java.ChangeType:          # one class
         oldFullyQualifiedTypeName: {{BASE_PACKAGE}}.orders.internal.Discounts
         newFullyQualifiedTypeName: {{BASE_PACKAGE}}.catalog.internal.Discounts
     # or, for a whole package and its subpackages:
     # - org.openrewrite.java.ChangePackage:
     #     oldPackageName: {{BASE_PACKAGE}}.orders.internal
     #     newPackageName: {{BASE_PACKAGE}}.orders.pricing
     #     recursive: true
   ```
<!-- maven:begin -->
3. Preview, and read the patch in `target/rewrite/rewrite.patch` before applying it:
   ```bash
   ./mvnw -q org.openrewrite.maven:rewrite-maven-plugin:6.46.1:dryRun -Drewrite.configLocation=$TMPDIR/move.yml -Drewrite.activeRecipes=local.Move
   ```
4. Apply it with the same command and goal `run` instead of `dryRun`.
<!-- maven:end -->
<!-- gradle:begin -->
3. Write an init script next to the recipe, `$TMPDIR/rewrite.gradle`, so the build files stay unchanged:
   ```groovy
   initscript {
       repositories { gradlePluginPortal(); mavenCentral() }
       dependencies { classpath "org.openrewrite:plugin:7.39.0" }
   }
   rootProject {
       plugins.apply(org.openrewrite.gradle.RewritePlugin)
       rewrite {
           activeRecipe("local.Move")
           configFile = new File(System.getProperty("moveRecipe"))
       }
   }
   ```
   Preview, and read the patch in `build/reports/rewrite/rewrite.patch` before applying it:
   ```bash
   ./gradlew -q rewriteDryRun --init-script $TMPDIR/rewrite.gradle -DmoveRecipe=$TMPDIR/move.yml
   ```
4. Apply it with the same command and task `rewriteRun` instead of `rewriteDryRun`.
<!-- gradle:end -->
5. Find what the recipe can't see: `git grep -n '<old fully qualified name>'`. A class name inside a Java string literal is not updated. Change each hit only if it names the moved type.
6. Run `{{VERIFY}}`. A compile error naming a type from the old package means the moved class used package-private code there: move that code with it (move the whole package instead), or make it reachable on purpose. The module-boundary test reports a move that crosses a module boundary.
7. Commit the move on its own, with no other edits, so the review is mechanical and `git log --follow` keeps the file's history.
