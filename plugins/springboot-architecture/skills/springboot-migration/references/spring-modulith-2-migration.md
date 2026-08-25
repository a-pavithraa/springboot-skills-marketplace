# Spring Modulith 2.0 Migration Guide

> **Official Documentation**: [Spring Modulith 2.0 Reference](https://docs.spring.io/spring-modulith/reference/)

## Table of Contents

1. [Overview](#overview)
2. [Version Update](#version-update)
3. [Breaking Changes](#breaking-changes)
4. [Event Publication Table Migration](#event-publication-table-migration-required)
5. [Configuration Changes](#configuration-changes)
6. [Verification](#verification)

---

## Overview

**IMPORTANT:** Migrating to Spring Modulith 2.x is **separate** from the Spring Boot 4 migration, but the versions are paired: **Spring Modulith 2.1 requires Spring Boot 4.1** (the original 2.0.x line pairs with Spring Boot 4.0). Match the Modulith minor to your Boot minor.

**Migration order:**
1. Spring Boot 4.1 first
2. Spring Modulith 2.1 second

---

## Version Update

### Update Property

```xml
<properties>
    <spring-modulith.version>2.1.0</spring-modulith.version>
</properties>
```

### Dependencies

**Core dependencies** (no changes needed):

```xml
<dependency>
    <groupId>org.springframework.modulith</groupId>
    <artifactId>spring-modulith-starter-core</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.modulith</groupId>
    <artifactId>spring-modulith-starter-jdbc</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.modulith</groupId>
    <artifactId>spring-modulith-events-amqp</artifactId>
    <scope>runtime</scope>
</dependency>
<dependency>
    <groupId>org.springframework.modulith</groupId>
    <artifactId>spring-modulith-starter-test</artifactId>
    <scope>test</scope>
</dependency>
```

---

## Breaking Changes

### 1. Event Publication Table Schema Changes (CRITICAL)

**The ACTUAL breaking change:** Spring Modulith 2.0 overhauled the event publication lifecycle, introducing a **new database schema structure** for event publication tables.

**What changed:**
- New event publication status model
- Updated table structure with three new columns (types are dialect-specific — use the shipped schema for your database from the [appendix](https://docs.spring.io/spring-modulith/reference/appendix.html)):
  - `status` — H2 / HSQLDB / MySQL / MSSQL use `VARCHAR(20)`; PostgreSQL uses `TEXT`
  - `completion_attempts` — `INT` (no DEFAULT in the shipped schema)
  - `last_resubmission_date` — `TIMESTAMP WITH TIME ZONE` on dialects that support it, else `TIMESTAMP(6)`
- Changes to how events transition between states

**Impact:**
- **CRITICAL:** if your project uses the **JDBC/JPA** event publication registry, you MUST create database migrations to update the existing `event_publication` table to the 2.x shape.
- The lifecycle changes (new `status` / `completion_attempts` / `last_resubmission_date` semantics) span all four supported registry backends — JDBC, JPA, MongoDB, and Neo4j — but the SQL `event_publication` table only exists for the JDBC/JPA backends. MongoDB and Neo4j backends use their own native storage shapes; consult the [appendix](https://docs.spring.io/spring-modulith/reference/appendix.html) for those.
- Without the schema update, applications using the JDBC/JPA registry will fail to start.

**Migration requirement:**
```sql
-- PostgreSQL example. Modulith 2.x ships PostgreSQL schemas that use TEXT
-- for status / listener_id / event_type / serialized_event. Other dialects
-- (H2, HSQLDB, MySQL, etc.) use VARCHAR — match your dialect's shipped schema.
ALTER TABLE event_publication
  ADD COLUMN status TEXT,
  ADD COLUMN completion_attempts INT,
  ADD COLUMN last_resubmission_date TIMESTAMP WITH TIME ZONE;

-- See official Spring Modulith reference for complete schema
```

**Reference:** [Spring Modulith Appendix - Event Publication Registry Schemas](https://docs.spring.io/spring-modulith/reference/appendix.html)

### 2. Spring Boot Baseline Requirement

**CRITICAL:** Spring Modulith 2.1 requires Spring Boot 4.1 (the 2.0.x line pairs with Spring Boot 4.0). Keep the Modulith minor aligned with the Boot minor.

**Migration order:**
1. Migrate to Spring Boot 4.1 first
2. Update event publication table schema
3. Upgrade Spring Modulith to 2.1

### 3. Configuration Property Defaults

Most event-related toggles **default off** so existing applications don't change behavior on upgrade — but a few defaults are deliberately `true` and one is a string:

| Property | Default | Notes |
|----------|---------|-------|
| `spring.modulith.events.jdbc.schema-initialization.enabled` | `false` | Off by default; use Flyway/Liquibase in production |
| `spring.modulith.events.republish-outstanding-events-on-restart` | `false` | Risky for multi-instance deployments |
| `spring.modulith.runtime.flyway-enabled` | `false` | Module-ordered Flyway integration |
| `spring.modulith.events.jdbc.schema` | _unset_ (string) | Schema name; unset means the table is **not** schema-qualified |
| `spring.modulith.events.externalization.enabled` | `true` | Event externalization is enabled when the externalization starter is on the classpath |
| `spring.modulith.events.kafka.enable-json` | `true` | JSON externalization with Kafka |
| `spring.modulith.events.rabbitmq.enable-json` | `true` | JSON externalization with RabbitMQ |
| `spring.modulith.events.mongodb.transaction-management.enabled` | `true` | Enables transactional event handling on MongoDB |
| `spring.modulith.events.completion-mode` | `update` | One of `update` / `delete` / `archive` |

**Most applications:** the schema migration is the only required step. The other properties are opt-in feature flags — review the appendix before turning them on.

---

## Event Publication Table Migration (REQUIRED)

### Step 1: Update Event Publication Table Schema

**CRITICAL:** You MUST update the `event_publication` table structure to match Spring Modulith 2.0 schema.

**Pre-reqs before running ALTER migration:**
- The `event_publication` table already exists (from Spring Modulith 1.x or a prior create migration).
- If you configured `spring.modulith.events.jdbc.schema=events`, the `events` schema exists and the table is in that schema.
- `spring-modulith-starter-jdbc` is on the classpath (otherwise the table is never created).

**Migration example (adjust for your database):**

```sql
-- PostgreSQL example. Modulith's PostgreSQL v2 schema uses TEXT for the
-- string columns (status / listener_id / event_type / serialized_event);
-- check your dialect's shipped schema if you're not on PostgreSQL.
-- The shipped schema declares completion_attempts as INT with NO DEFAULT —
-- match the appendix exactly. Use the UPDATE below to backfill existing rows.
ALTER TABLE event_publication
  ADD COLUMN IF NOT EXISTS status TEXT,
  ADD COLUMN IF NOT EXISTS completion_attempts INT,
  ADD COLUMN IF NOT EXISTS last_resubmission_date TIMESTAMP WITH TIME ZONE;

-- Backfill existing rows: legacy 1.x rows have neither a status nor a
-- completion-attempt count. Modulith treats a completed publication as one
-- whose completion_date is non-null; mark legacy rows as PUBLISHED with
-- zero attempts. Verify against the official migration guidance for your
-- exact 1.x → 2.x state if you are upgrading a real production table.
UPDATE event_publication
   SET status = COALESCE(status, 'PUBLISHED'),
       completion_attempts = COALESCE(completion_attempts, 0);
```

**Complete schema reference:** See [Spring Modulith Reference - Event Publication Registry](https://docs.spring.io/spring-modulith/reference/appendix.html)

**Expected columns in event_publication table** (types are dialect-specific — values shown are PostgreSQL; other dialects use sized VARCHAR — see the official schema files):
- `id` (UUID primary key)
- `listener_id` (TEXT)
- `event_type` (TEXT)
- `serialized_event` (TEXT)
- `publication_date` (TIMESTAMP WITH TIME ZONE)
- `completion_date` (TIMESTAMP WITH TIME ZONE, nullable)
- `status` (TEXT) - **NEW in 2.0**
- `completion_attempts` (INT) - **NEW in 2.0**
- `last_resubmission_date` (TIMESTAMP WITH TIME ZONE) - **NEW in 2.0**

### Step 2: Optional - Use Dedicated Schema for Events

**This is OPTIONAL, not required.** You can keep event tables in your default schema or separate them.

**To use a dedicated schema (recommended for larger applications):**

**File:** `src/main/resources/db/migration/V1__create_events_schema.sql`

```sql
-- Create dedicated schema for events
CREATE SCHEMA IF NOT EXISTS events;

-- Move event_publication table to events schema (if desired)
ALTER TABLE event_publication SET SCHEMA events;
```

**Then configure the schema in application.properties:**

```properties
spring.modulith.events.jdbc.schema=events
```

**Benefits of dedicated schema:**
- Separates event storage from application data
- Prevents table name conflicts
- Allows independent event store management
- Easier to apply different backup/retention policies

**When to use:**
- Large applications with many tables
- Multi-tenant applications
- When you want separate permissions for event tables

**When NOT needed:**
- Small/medium applications
- Single schema is simpler to manage
- Default schema works fine

---

## Configuration Changes

### No Configuration Required by Default

**Spring Modulith 2.0 works out of the box for the standard case.** Most opt-in toggles (schema init, restart republishing, module-ordered Flyway) default to `false`. A few defaults are deliberately set — see the table in [Configuration Property Defaults](#3-configuration-property-defaults) above before assuming a property is off.

### Optional Configurations

**Only configure these if you need specific features:**

#### 1. Dedicated Schema (Optional)

```properties
# Use a dedicated schema for event tables.
# This property holds a schema NAME (string). If unset, the event_publication
# table is NOT schema-qualified — it lives in the default schema.
spring.modulith.events.jdbc.schema=events
```

**When to use:**
- Large applications with many tables
- You want to separate event tables from application tables
- Multi-tenant applications

**When NOT needed:**
- Small/medium applications (default schema is fine)

#### 2. Automatic Schema Initialization (Optional)

```properties
# Let Spring Modulith create event tables automatically
# Default: false
spring.modulith.events.jdbc.schema-initialization.enabled=true
```

**When to use:**
- Development/testing environments
- Prototyping
- You don't want to manage event table creation manually

**When NOT to use:**
- **Production** - Use Flyway/Liquibase migrations instead
- When you need full control over schema

#### 3. Event Republishing on Restart (Optional)

```properties
# Republish outstanding events when application restarts
# Default: false
spring.modulith.events.republish-outstanding-events-on-restart=true
```

**When to use:**
- Single-instance deployments
- You want automatic event recovery on restart

**When NOT to use:**
- **Multi-instance deployments** - Can cause duplicate event processing
- When using message brokers for event externalization

**Behavior when enabled:**
- On startup, checks for incomplete events
- Republishes events that didn't complete
- Maintains event ordering

#### 4. Flyway Integration (Optional)

```properties
# Enable module-specific Flyway migrations in dependency order
# Default: false
spring.modulith.runtime.flyway-enabled=true
```

**When to use:**
- Using Spring Modulith's modular Flyway support
- Want migrations executed in module dependency order
- Organizing migrations by module

**When NOT needed:**
- Standard Flyway usage (works without this property)
- Migrations in single directory

### Example Production Configuration

**Minimal (recommended for most projects):**

```properties
# No Spring Modulith config needed - all defaults are fine
# Just ensure your event_publication table has correct schema
```

**With dedicated schema (larger projects):**

```properties
# Only if using dedicated events schema
spring.modulith.events.jdbc.schema=events
```

**Complete configuration (if you need all features):**

```properties
#### Events Config (all optional) ######
spring.modulith.events.jdbc.schema=events
# Do NOT use schema-initialization in production - use Flyway instead
spring.modulith.events.republish-outstanding-events-on-restart=true
spring.modulith.runtime.flyway-enabled=true
```

---

## Verification

### 1. Check Event Publication Table Structure

**CRITICAL:** Verify the `event_publication` table has the new Spring Modulith 2.0 columns:

```sql
-- Check table structure
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'event_publication'
ORDER BY ordinal_position;
```

**Required columns (Spring Modulith 2.0):**
- `id`
- `listener_id`
- `event_type`
- `serialized_event`
- `publication_date`
- `completion_date`
- `status` - **NEW in 2.0**
- `completion_attempts` - **NEW in 2.0**
- `last_resubmission_date` - **NEW in 2.0**

### 2. Test Event Publication

```java
@SpringBootTest
class EventPublicationTest {

    @Autowired
    private ApplicationEventPublisher events;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Test
    void shouldStoreEventWithNewColumns() {
        // Publish event
        events.publishEvent(new OrderPlaced(orderId));

        // Verify event stored with new status column
        Integer count = jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM event_publication WHERE status IS NOT NULL",
            Integer.class
        );

        assertThat(count).isGreaterThan(0);
    }
}
```

### 3. Verify Application Startup

```bash
# Start application
./mvnw spring-boot:run

# Check logs for Spring Modulith initialization
# Should see: "Spring Modulith initialized"
# Should NOT see: schema-related errors
```

### 4. (Optional) Verify Dedicated Schema

**Only if you configured `spring.modulith.events.jdbc.schema=events`:**

```sql
-- Check schema exists
SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'events';

-- Check event_publication table location
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_name = 'event_publication';
```

---

## Common Issues

### Issue 1: Missing Table Columns (CRITICAL)

**Error:**
```
ERROR: column "status" does not exist
ERROR: column "completion_attempts" does not exist
```

**Cause:** Event publication table not migrated to Spring Modulith 2.0 schema

**Solution:** (PostgreSQL — match your dialect's shipped schema for the string types; the shipped schema has no DEFAULT on `completion_attempts`)
```sql
ALTER TABLE event_publication
  ADD COLUMN IF NOT EXISTS status TEXT,
  ADD COLUMN IF NOT EXISTS completion_attempts INT,
  ADD COLUMN IF NOT EXISTS last_resubmission_date TIMESTAMP WITH TIME ZONE;
```

### Issue 2: Application Won't Start

**Error:**
```
Failed to configure a DataSource: 'url' attribute is not specified
```

**Cause:** This is the generic Spring Boot DataSource auto-configuration failure — it fires whenever Boot finds JDBC on the classpath but no usable `spring.datasource.url` (and no embedded driver to fall back to). It is not specific to Spring Modulith 2 or the Boot 4 baseline, but Modulith projects hit it more often because adding `spring-modulith-starter-jdbc` pulls JDBC onto the classpath even when the rest of the application uses JPA or no DB at all.

**Solution:**
1. Set `spring.datasource.url` (and credentials) for the database that should hold `event_publication`.
2. If you do not want Modulith to need a DataSource at all, remove `spring-modulith-starter-jdbc` and switch to a different event registry starter (`-jpa`, `-mongodb`, `-neo4j`) or drop the registry entirely (`@ApplicationModuleListener` still works, just without durability — see the Best Practices section above).
3. Once the DataSource resolves, apply the `event_publication` schema migration described in [Step 1](#step-1-update-event-publication-table-schema).

### Issue 3: Events Not Persisting

**Symptom:** Events published but not stored in database

**Possible causes:**
1. JDBC event store not configured
2. Missing `spring-modulith-starter-jdbc` dependency
3. Transaction not committing

**Solution:**
```xml
<!-- Verify dependency -->
<dependency>
    <groupId>org.springframework.modulith</groupId>
    <artifactId>spring-modulith-starter-jdbc</artifactId>
</dependency>
```

Check event publication in database:
```sql
SELECT * FROM event_publication ORDER BY publication_date DESC LIMIT 10;
```

### Issue 4: Schema "events" Not Found

**Error:**
```
ERROR: schema "events" does not exist
```

**Cause:** Configured `spring.modulith.events.jdbc.schema=events` but schema doesn't exist

**Solution:**

**Option A:** Create the schema
```sql
CREATE SCHEMA IF NOT EXISTS events;
```

**Option B:** Remove the property (use default schema)
```properties
# Remove this line to use default schema
# spring.modulith.events.jdbc.schema=events
```

### Issue 5: ALTER migration fails with "relation event_publication does not exist"

**Error:**
```
ERROR: relation "event_publication" does not exist
```

**Cause:** Running the Spring Modulith 2.0 ALTER migration before the table exists.

**Fix:**
- Create the `event_publication` table first (use the official schema from the appendix), then apply the ALTER migration.
- If you intended to let Modulith initialize tables in dev/test, set:
  `spring.modulith.events.jdbc.schema-initialization.enabled=true`
  and remove/skip the ALTER migration.

---

## Migration Checklist

### Prerequisites
- [ ] Spring Boot 4.1 migration complete
- [ ] Database migrations tool configured (Flyway/Liquibase)
- [ ] Backup production database before migration

### Phase 1: Update Event Publication Table Schema (CRITICAL)
- [ ] Verify pre-reqs before ALTER migration:
  - [ ] `event_publication` table exists
  - [ ] If using `spring.modulith.events.jdbc.schema=events`, the `events` schema exists
  - [ ] `spring-modulith-starter-jdbc` dependency is present
- [ ] Create database migration to add new columns (types are dialect-specific — match the [shipped schema](https://docs.spring.io/spring-modulith/reference/appendix.html)):
  - `status` — PostgreSQL: `TEXT`; H2 / HSQLDB / MySQL / MSSQL: `VARCHAR(20)`
  - `completion_attempts` (`INT`, no DEFAULT in the shipped schema)
  - `last_resubmission_date` — `TIMESTAMP WITH TIME ZONE` (or `TIMESTAMP(6)` on dialects that lack `WITH TIME ZONE`)
- [ ] Run migration on development database
- [ ] Test event publication works
- [ ] Run migration on staging/production

### Phase 2: Update Spring Modulith Version
- [ ] Update `spring-modulith.version` to 2.1.0 in pom.xml
- [ ] Run `./mvnw clean install` to download new version
- [ ] Verify no compilation errors

### Phase 3: (Optional) Configure Features
- [ ] Decide if you need dedicated events schema
  - If yes: Create schema and set `spring.modulith.events.jdbc.schema=events`
  - If no: Skip this step (use default schema)
- [ ] Decide if you need event republishing on restart
  - If yes: Set `spring.modulith.events.republish-outstanding-events-on-restart=true`
  - If no: Skip this step (default is false)
- [ ] Decide if you need module-specific Flyway migrations
  - If yes: Set `spring.modulith.runtime.flyway-enabled=true`
  - If no: Skip this step (default is false)

### Phase 4: Verification
- [ ] Build succeeds: `./mvnw clean package`
- [ ] Application starts successfully
- [ ] Check event_publication table has new columns
- [ ] Test event publication
- [ ] Verify events stored correctly
- [ ] Check application logs for errors
- [ ] Review custom event handling code for API changes

### Phase 5: Testing
- [ ] Run all unit tests
- [ ] Run all integration tests
- [ ] Test event-driven workflows
- [ ] Performance testing (if applicable)

---

## Best Practices

### 1. Event Schema Isolation

**DO:**
- Keep event tables in dedicated `events` schema
- Never create application tables in events schema
- Never reference event tables directly from application code

**DON'T:**
- Mix event and application tables
- Manually modify event store tables
- Query event store directly (use Spring Modulith APIs)

### 2. Event Republishing Strategy

**Configure based on requirements:**

```properties
# For critical business events
spring.modulith.events.republish-outstanding-events-on-restart=true

# For non-critical or idempotent events (if performance is concern)
spring.modulith.events.republish-outstanding-events-on-restart=false
```

### 3. Monitoring Event Store

**Add actuator endpoint:**

```properties
management.endpoints.web.exposure.include=health,modulith
```

**Monitor:**
- Event publication rate
- Outstanding events count
- Event processing failures

### 4. Database Permissions

**Minimum required permissions:**
```sql
-- Create events schema (one-time)
GRANT CREATE ON DATABASE app_db TO app_user;

-- Access events schema (runtime)
GRANT USAGE ON SCHEMA events TO app_user;
GRANT ALL ON ALL TABLES IN SCHEMA events TO app_user;
```

---

## References

- [Spring Modulith 2.0 Reference Documentation](https://docs.spring.io/spring-modulith/reference/)
- [Spring Modulith Release Notes](https://github.com/spring-projects/spring-modulith/releases)
- [Event Externalization Guide](https://docs.spring.io/spring-modulith/reference/events.html)
