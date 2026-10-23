---
name: db-migration
description: Writes a Flyway database migration for this project following the team's rules for naming, editing and renaming, so migrations from different developers don't collide and deployed databases stay valid. Use whenever a change needs a new table, column, index or data fix, or the user mentions a schema change or migration.
---

# Write a database migration

Migrations live in `src/main/resources/db/migration`.

1. Follow the naming the folder already uses. In a folder with no migrations yet, use `V<yyyyMMddHHmm>__<what_it_does>.sql` in UTC: unlike `V7`, `V8`, timestamps don't collide when two developers add a migration on different branches. With numbered names, take the next number after the highest one on the main branch, and renumber yours if someone merges first.
2. Never edit a migration that is on the main branch. It may already have run on a shared database, and Flyway fails validation when the checksum changes. Write a new migration instead.
3. Make destructive changes in two releases. To rename or drop a column, first add the new column and write to both, and drop the old one in a later migration once no running version reads it.
4. Keep each migration to one purpose. Put data fixes in their own file, and make them safe to run on a database where the fix is already done.
5. Don't let Hibernate create the schema: `spring.jpa.hibernate.ddl-auto` stays `validate` or `none`.
6. Run `./mvnw verify`. If the project has Testcontainers integration tests, they apply every migration to a real database; if it has none, say that the migration is untested.
