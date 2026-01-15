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

-- Required for @ApplicationModuleListener persistent events
-- Spring Modulith creates this automatically, but you can customize:

-- CREATE TABLE event_publication (
--     id UUID PRIMARY KEY,
--     listener_id VARCHAR(255) NOT NULL,
--     event_type VARCHAR(255) NOT NULL,
--     serialized_event TEXT NOT NULL,
--     publication_date TIMESTAMP NOT NULL,
--     completion_date TIMESTAMP
-- );


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
