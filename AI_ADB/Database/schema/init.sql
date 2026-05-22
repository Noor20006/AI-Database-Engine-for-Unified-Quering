-- ============================================================
--  SmartCRM  |  PostgreSQL Schema
--  Member 1 — Database Engineer
-- ============================================================

-- Clean slate
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS products CASCADE;

-- ── Customers ──────────────────────────────────────────────
CREATE TABLE customers (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(100)        NOT NULL,
    email         VARCHAR(150) UNIQUE NOT NULL,
    last_active   DATE                NOT NULL,
    total_spent   NUMERIC(10, 2)      NOT NULL DEFAULT 0,
    order_count   INT                 NOT NULL DEFAULT 0,
    created_at    TIMESTAMP           NOT NULL DEFAULT NOW()
);

-- ── Products ───────────────────────────────────────────────
CREATE TABLE products (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(150)        NOT NULL,
    category      VARCHAR(100)        NOT NULL,
    price         NUMERIC(10, 2)      NOT NULL
);

-- ── Orders ─────────────────────────────────────────────────
CREATE TABLE orders (
    id            SERIAL PRIMARY KEY,
    customer_id   INT REFERENCES customers(id) ON DELETE CASCADE,
    product_id    INT REFERENCES products(id)  ON DELETE CASCADE,
    amount        NUMERIC(10, 2)      NOT NULL,
    date          DATE                NOT NULL
);

-- ── Churn Feature View (used by ML model) ──────────────────
CREATE OR REPLACE VIEW churn_features AS
SELECT
    c.id,
    c.name,
    c.email,
    c.total_spent,
    c.order_count,
    EXTRACT(DAY FROM NOW() - c.last_active::TIMESTAMP)::INT  AS days_inactive,
    CASE
        WHEN EXTRACT(DAY FROM NOW() - c.last_active::TIMESTAMP) > 90
             AND c.total_spent < 100   THEN 'high'
        WHEN EXTRACT(DAY FROM NOW() - c.last_active::TIMESTAMP) > 60
             AND c.total_spent < 300   THEN 'medium'
        ELSE                                'low'
    END AS churn_risk
FROM customers c;

-- ── Indexes ────────────────────────────────────────────────
CREATE INDEX idx_orders_customer  ON orders(customer_id);
CREATE INDEX idx_orders_product   ON orders(product_id);
CREATE INDEX idx_customers_active ON customers(last_active);
