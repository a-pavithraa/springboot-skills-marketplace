# Spring Modulith 1.x → 2.x Migration

Official: [Spring Modulith Reference](https://docs.spring.io/spring-modulith/reference/), [Appendix (properties, schemas)](https://docs.spring.io/spring-modulith/reference/appendix.html). Checked against Spring Modulith 2.1.0 jars on 2026-10-17.

## Versions

| Spring Boot | Spring Modulith |
|-------------|-----------------|
| 3.x | 1.x |
| 4.0 | 2.0.x |
| 4.1 | 2.1.x |

Upgrade Boot first, then Modulith, in the same release. Import the BOM:

```xml
<properties>
    <spring-modulith.version>2.1.0</spring-modulith.version>
</properties>
<!-- dependencyManagement: org.springframework.modulith:spring-modulith-bom:${spring-modulith.version}, type pom, scope import -->
```

Starter names (`spring-modulith-starter-core`, `-jdbc`, `-jpa`, `-mongodb`, `-neo4j`, `-test`) do not change.

---

## The breaking change: event publication lifecycle

Modulith 2 adds a status model to the Event Publication Registry. For the JDBC and JPA registries, the `event_publication` table gets three columns:

| Column | PostgreSQL type | Other databases |
|--------|-----------------|-----------------|
| `status` | `TEXT` | `VARCHAR(20)` |
| `completion_attempts` | `INT` (no default) | `INT` |
| `last_resubmission_date` | `TIMESTAMP WITH TIME ZONE` | `TIMESTAMP(6)` where time zones are not supported |

Status values: `PUBLISHED`, `PROCESSING`, `COMPLETED`, `FAILED`, `RESUBMITTED`.

Only projects with a JDBC/JPA registry (`spring-modulith-starter-jdbc` or `-jpa`) have this table. MongoDB and Neo4j registries use their own storage; see the appendix.

### Option A: migrate the table (recommended)

Add a Flyway/Liquibase migration. PostgreSQL:

```sql
ALTER TABLE event_publication
  ADD COLUMN IF NOT EXISTS status TEXT,
  ADD COLUMN IF NOT EXISTS completion_attempts INT,
  ADD COLUMN IF NOT EXISTS last_resubmission_date TIMESTAMP WITH TIME ZONE;

-- Backfill 1.x rows. Completed rows have a completion_date; the rest are outstanding.
UPDATE event_publication
   SET status = CASE WHEN completion_date IS NULL THEN 'PUBLISHED' ELSE 'COMPLETED' END,
       completion_attempts = COALESCE(completion_attempts, 0)
 WHERE status IS NULL;
```

For other databases, use the column types from the shipped schema: `org/springframework/modulith/events/jdbc/schemas/v2/schema-<db>.sql` inside `spring-modulith-events-jdbc`. If you use `completion-mode=archive`, migrate the archive table the same way (`schema-<db>-archive.sql`).

Before the migration runs:

- Back up the table, or at least check how many rows are outstanding (`completion_date IS NULL`).
- Stop all instances of the old version, or make sure none of them writes publications during the change.

### Option B: keep the 1.x table for now

```properties
spring.modulith.events.jdbc.use-legacy-structure=true
```

Modulith 2 then uses the 1.x table shape (`schemas/v1/...`). Use this to separate the library upgrade from the schema change. Plan Option A later; the status features (staleness, failed publications) need the new columns.

---

## Properties (Modulith 2.1 defaults)

| Property | Default | Notes |
|----------|---------|-------|
| `spring.modulith.events.jdbc.schema-initialization.enabled` | `false` | Creates the table at startup. Dev/test only; use Flyway/Liquibase in production |
| `spring.modulith.events.jdbc.schema` | unset | Schema name for the table. **Only H2, HSQLDB, and PostgreSQL support it.** On MySQL, MariaDB, SQL Server, or Oracle, startup fails with `Setting the schema name is not supported!` |
| `spring.modulith.events.jdbc.use-legacy-structure` | `false` | `true` keeps the 1.x table (Option B) |
| `spring.modulith.events.completion-mode` | `update` | `update` sets `completion_date`; `delete` removes the row; `archive` moves it to an archive table |
| `spring.modulith.events.republish-outstanding-events-on-restart` | `false` | Not recommended with several instances: another instance may still be processing the event |
| `spring.modulith.events.staleness.published` / `.processing` / `.resubmitted` | `0` (`Duration.ZERO`) | New in 2.x. Set a duration per state so the staleness monitor marks stuck publications `FAILED`. The check runs every `spring.modulith.events.staleness.check-interval` (default 1 minute) |
| `spring.modulith.events.externalization.enabled` | `true` | Applies when an externalization module (Kafka, AMQP, JMS, SQS, SNS) is present |
| `spring.modulith.events.externalization.mode` | `module-listener` | New in 2.x: `outbox` uses a real outbox implementation |
| `spring.modulith.runtime.flyway-enabled` | `false` | Runs module-specific Flyway migrations in module order |

Most projects need no property changes beyond the schema migration.

### Optional: dedicated schema (PostgreSQL, H2, HSQLDB only)

```sql
CREATE SCHEMA IF NOT EXISTS events;
ALTER TABLE event_publication SET SCHEMA events;
```

```properties
spring.modulith.events.jdbc.schema=events
```

The application user needs `USAGE` on the schema and read/write rights on the table. Do not query or edit the table from application code. Use the Modulith APIs (`IncompleteEventPublications`, `CompletedEventPublications`).

---

## Verification

1. Check the columns:

   ```sql
   SELECT column_name, data_type FROM information_schema.columns
    WHERE table_name = 'event_publication' ORDER BY ordinal_position;
   ```

2. Run the modularity test (`ApplicationModules.of(App.class).verify()`) and `@ApplicationModuleTest` tests.
3. Publish an event in an integration test and check that the row has a `status` (`COMPLETED` after the listener finishes with `completion-mode=update`).
4. Check `/actuator/modulith` (needs `spring-modulith-actuator`) for the module structure.

## Common failures

| Error | Cause | Fix |
|-------|-------|-----|
| `column "status" does not exist` | 1.x table, Modulith 2 | Run the Option A migration, or set `use-legacy-structure=true` |
| `relation "event_publication" does not exist` | ALTER ran before the table existed, or the table was never created | Create the table from the shipped v2 schema (or enable schema initialization in dev), then skip the ALTER |
| `Setting the schema name is not supported!` | `spring.modulith.events.jdbc.schema` on MySQL, MariaDB, SQL Server, or Oracle | Remove the property |
| `schema "events" does not exist` | Schema configured but not created | Create it in a migration, or remove the property |
| `Failed to configure a DataSource` | `spring-modulith-starter-jdbc` brings JDBC, but no datasource is set | Configure `spring.datasource.*`, or use another registry starter, or remove the registry (listeners still run, without durability) |
| Events not stored | No registry starter on the classpath, or the publishing method is not transactional | Add `spring-modulith-starter-jdbc`/`-jpa`; publish inside `@Transactional` |

## Checklist

- [ ] Boot 4.1 migration done; Modulith BOM 2.1.x
- [ ] Registry type known (JDBC/JPA/MongoDB/Neo4j)
- [ ] JDBC/JPA: migration adds the three columns and backfills `PUBLISHED`/`COMPLETED`; archive table too if used
- [ ] Or: `use-legacy-structure=true`, with a follow-up task for the migration
- [ ] `spring.modulith.events.jdbc.schema` only on PostgreSQL/H2/HSQLDB
- [ ] `republish-outstanding-events-on-restart` stays `false` with several instances
- [ ] Modularity tests and an event round-trip test pass
