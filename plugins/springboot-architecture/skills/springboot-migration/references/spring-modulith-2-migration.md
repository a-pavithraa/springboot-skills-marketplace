# Spring Modulith 2.0 Migration Guide

> **Official Documentation**: [Spring Modulith 2.0 Reference](https://docs.spring.io/spring-modulith/reference/)

## Table of Contents

1. [Overview](#overview)
2. [Version Update](#version-update)
3. [Breaking Changes](#breaking-changes)
4. [Event Store Schema Migration](#event-store-schema-migration)
5. [Configuration Changes](#configuration-changes)
6. [Verification](#verification)

---

## Overview

**IMPORTANT:** Spring Modulith 2.0 migration is **separate** from Spring Boot 4.0 migration. However, Spring Modulith 2.0 **requires** Spring Boot 4.0.

**Migration order:**
1. Spring Boot 4.0 first
2. Spring Modulith 2.0 second

---

## Version Update

### Update Property

```xml
<properties>
    <spring-modulith.version>2.0.0</spring-modulith.version>
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
- Updated table structure with new columns:
  - `STATUS` (VARCHAR 20) - new status tracking
  - `COMPLETION_ATTEMPTS` (INT) - retry tracking
  - `LAST_RESUBMISSION_DATE` (TIMESTAMP)
- Changes to how events transition between states

**Impact:**
- **CRITICAL:** You MUST create database migrations to update existing `event_publication` tables
- Existing applications will fail to start without schema updates
- Affects JDBC, JPA, MongoDB, and Neo4j event stores

**Migration requirement:**
```sql
-- Example: Update existing event_publication table
ALTER TABLE event_publication
  ADD COLUMN status VARCHAR(20),
  ADD COLUMN completion_attempts INT,
  ADD COLUMN last_resubmission_date TIMESTAMP WITH TIME ZONE;

-- See official Spring Modulith reference for complete schema
```

**Reference:** [Spring Modulith Appendix - Event Publication Registry Schemas](https://docs.spring.io/spring-modulith/reference/appendix.html)

### 2. Spring Boot 4.0 Baseline Requirement

**CRITICAL:** Spring Modulith 2.0 requires Spring Boot 4.0+

**Migration order:**
1. Migrate to Spring Boot 4.0 first
2. Update event publication table schema
3. Upgrade Spring Modulith to 2.0

### 3. Configuration Property Defaults

**All event-related properties default to `false`** - no automatic behavior changes unless explicitly configured.

**Most applications:** No configuration changes needed unless you want to enable specific features.

---

## Event Publication Table Migration (REQUIRED)

### Step 1: Update Event Publication Table Schema

**CRITICAL:** You MUST update the `event_publication` table structure to match Spring Modulith 2.0 schema.

**Migration example (adjust for your database):**

```sql
-- PostgreSQL example
ALTER TABLE event_publication
  ADD COLUMN IF NOT EXISTS status VARCHAR(20),
  ADD COLUMN IF NOT EXISTS completion_attempts INT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS last_resubmission_date TIMESTAMP WITH TIME ZONE;

-- Update existing rows to set default status
UPDATE event_publication SET status = 'PUBLISHED' WHERE status IS NULL;
```

**Complete schema reference:** See [Spring Modulith Reference - Event Publication Registry](https://docs.spring.io/spring-modulith/reference/appendix.html)

**Expected columns in event_publication table:**
- `id` (UUID/VARCHAR primary key)
- `listener_id` (VARCHAR 512)
- `event_type` (VARCHAR 512)
- `serialized_event` (TEXT/VARCHAR)
- `publication_date` (TIMESTAMP WITH TIME ZONE)
- `completion_date` (TIMESTAMP WITH TIME ZONE, nullable)
- `status` (VARCHAR 20) - **NEW in 2.0**
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

**Spring Modulith 2.0 works out of the box with no configuration changes.** All event-related properties default to `false`.

### Optional Configurations

**Only configure these if you need specific features:**

#### 1. Dedicated Schema (Optional)

```properties
# Use a dedicated schema for event tables
# Default: false (uses default schema)
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

**Solution:**
```sql
-- Add missing columns
ALTER TABLE event_publication
  ADD COLUMN IF NOT EXISTS status VARCHAR(20),
  ADD COLUMN IF NOT EXISTS completion_attempts INT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS last_resubmission_date TIMESTAMP WITH TIME ZONE;
```

### Issue 2: Application Won't Start

**Error:**
```
Failed to configure a DataSource: 'url' attribute is not specified
```

**Cause:** Spring Boot 4.0 baseline - check Spring Boot migration first

**Solution:**
1. Complete Spring Boot 4.0 migration first
2. Ensure database configuration is correct
3. Update event_publication table schema

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

---

## Migration Checklist

### Prerequisites
- [ ] Spring Boot 4.0 migration complete
- [ ] Database migrations tool configured (Flyway/Liquibase)
- [ ] Backup production database before migration

### Phase 1: Update Event Publication Table Schema (CRITICAL)
- [ ] Create database migration to add new columns:
  - `status` (VARCHAR 20)
  - `completion_attempts` (INT)
  - `last_resubmission_date` (TIMESTAMP WITH TIME ZONE)
- [ ] Run migration on development database
- [ ] Test event publication works
- [ ] Run migration on staging/production

### Phase 2: Update Spring Modulith Version
- [ ] Update `spring-modulith.version` to 2.0.0 in pom.xml
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
