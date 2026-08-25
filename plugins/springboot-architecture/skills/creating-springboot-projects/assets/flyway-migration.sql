-- Flyway Migration Template
-- Location: src/main/resources/db/migration/V1__create_{{TABLE}}_table.sql
--
-- Naming convention: V{version}__{description}.sql
-- Examples:
--   V1__create_products_table.sql
--   V2__add_category_column.sql
--   V3__create_orders_table.sql

-- ============================================================
-- BASIC TABLE (Layered/Package-by-Module)
-- ============================================================

CREATE TABLE {{TABLE}} (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_{{TABLE}}_status ON {{TABLE}}(status);


-- ============================================================
-- RICH TABLE WITH VALUE OBJECTS (Tomato/DDD)
-- ============================================================

-- Example: Products table with embedded Value Objects
CREATE TABLE products (
    -- TSID as primary key (application-generated)
    id BIGINT PRIMARY KEY,

    -- Value Object: ProductSKU
    sku VARCHAR(50) NOT NULL UNIQUE,

    -- Value Object: ProductDetails (embedded)
    name VARCHAR(200) NOT NULL,
    description TEXT,
    image_url VARCHAR(500),

    -- Value Object: Price
    price DECIMAL(10, 2) NOT NULL CHECK (price >= 0),

    -- Value Object: Quantity
    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),

    -- Enum
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',

    -- Optimistic locking
    version INTEGER NOT NULL DEFAULT 0,

    -- Audit fields (BaseEntity)
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_status ON products(status);
CREATE INDEX idx_products_created_at ON products(created_at);


-- ============================================================
-- EVENTS TABLE (Modular Monolith with Spring Modulith)
-- ============================================================

-- @ApplicationModuleListener always runs as
-- @Async + @Transactional(REQUIRES_NEW) + @TransactionalEventListener — i.e.
-- async, after the publishing transaction commits, in its own new transaction.
-- To make these publications PERSISTENT and REPLAYABLE you must:
--   1. add a Modulith event registry starter to your build, one of:
--        spring-modulith-starter-jdbc
--        spring-modulith-starter-jpa
--        spring-modulith-starter-mongodb
--        spring-modulith-starter-neo4j
--   2. provision the registry's backing storage. For the JDBC/JPA starters
--      that is the event_publication table (this file).
-- Without a registry starter, @ApplicationModuleListener still runs the same
-- async-after-commit transaction, but in-flight publications are not durable
-- across restarts and cannot be replayed.
--
-- Modulith ships a dialect-specific schema for each store — copy the one
-- that matches your database from:
--   https://docs.spring.io/spring-modulith/reference/appendix.html
-- The schema below is the PostgreSQL variant for Modulith 2.x. Other
-- dialects use sized VARCHAR instead of TEXT — check the appendix.

-- CREATE TABLE event_publication (
--     id                     UUID                     NOT NULL,
--     listener_id            TEXT                     NOT NULL,
--     event_type             TEXT                     NOT NULL,
--     serialized_event       TEXT                     NOT NULL,
--     publication_date       TIMESTAMP WITH TIME ZONE NOT NULL,
--     completion_date        TIMESTAMP WITH TIME ZONE,
--     status                 TEXT,
--     completion_attempts    INT,
--     last_resubmission_date TIMESTAMP WITH TIME ZONE,
--     PRIMARY KEY (id)
-- );
-- CREATE INDEX event_publication_by_completion_date_idx
--     ON event_publication (completion_date);
-- CREATE INDEX event_publication_serialized_event_hash_idx
--     ON event_publication (listener_id, serialized_event);


-- ============================================================
-- EXAMPLE: Orders with Foreign Key
-- ============================================================

-- CREATE TABLE orders (
--     id BIGINT PRIMARY KEY,
--     order_code VARCHAR(50) NOT NULL UNIQUE,
--     customer_email VARCHAR(255) NOT NULL,
--     total_amount DECIMAL(10, 2) NOT NULL,
--     status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
--     version INTEGER NOT NULL DEFAULT 0,
--     created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
--     updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
-- );
--
-- CREATE TABLE order_items (
--     id BIGINT PRIMARY KEY,
--     order_id BIGINT NOT NULL REFERENCES orders(id),
--     product_id BIGINT NOT NULL,
--     quantity INTEGER NOT NULL CHECK (quantity > 0),
--     unit_price DECIMAL(10, 2) NOT NULL,
--     created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
-- );
--
-- CREATE INDEX idx_order_items_order_id ON order_items(order_id);


-- ============================================================
-- MYSQL SYNTAX DIFFERENCES
-- ============================================================

-- MySQL uses AUTO_INCREMENT instead of BIGSERIAL:
-- id BIGINT PRIMARY KEY AUTO_INCREMENT

-- MySQL uses DATETIME instead of TIMESTAMP for wider range:
-- created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP

-- MySQL TEXT doesn't need explicit length but has 64KB limit
-- Use MEDIUMTEXT (16MB) or LONGTEXT (4GB) for larger content
