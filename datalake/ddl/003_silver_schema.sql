-- 003_silver_schema.sql — Silver layer: aggregated marts

CREATE TABLE IF NOT EXISTS silver.dim_store (
    store_id    TEXT PRIMARY KEY,
    name        TEXT,
    code        TEXT,
    region      TEXT,
    province    TEXT,
    staff_count INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS silver.dim_product (
    product_id  TEXT PRIMARY KEY,
    name        TEXT,
    code        TEXT,
    category    TEXT,
    brand       TEXT,
    sell_price  FLOAT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS silver.daily_sales_finance (
    d           DATE NOT NULL,
    store_id    TEXT NOT NULL,
    revenue     FLOAT DEFAULT 0,
    cogs        FLOAT DEFAULT 0,
    gross_profit FLOAT DEFAULT 0,
    orders      INT DEFAULT 0,
    units       FLOAT DEFAULT 0,
    aov         FLOAT DEFAULT 0,
    upt         FLOAT DEFAULT 0,
    PRIMARY KEY (d, store_id)
);

CREATE TABLE IF NOT EXISTS silver.daily_customer_segments (
    d               DATE NOT NULL,
    store_id        TEXT NOT NULL,
    new_customers   INT DEFAULT 0,
    returning_customers INT DEFAULT 0,
    PRIMARY KEY (d, store_id)
);

CREATE TABLE IF NOT EXISTS silver.monthly_inventory (
    year_month      TEXT NOT NULL,
    store_id        TEXT NOT NULL,
    on_hand_units   FLOAT DEFAULT 0,
    inventory_value FLOAT DEFAULT 0,
    dead_stock_pct  FLOAT DEFAULT 0,
    stock_cover_days FLOAT DEFAULT 0,
    PRIMARY KEY (year_month, store_id)
);
