-- 004_gold_schema.sql — Gold layer: API-ready tables (mirrors SQLite schema)

CREATE TABLE IF NOT EXISTS gold.stores (
    store_id    TEXT PRIMARY KEY,
    name        TEXT,
    code        TEXT,
    region      TEXT,
    province    TEXT,
    staff_count INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS gold.daily_sales (
    d           DATE NOT NULL,
    store_id    TEXT NOT NULL,
    store_name  TEXT,
    revenue     FLOAT DEFAULT 0,
    cogs        FLOAT DEFAULT 0,
    gross_profit FLOAT DEFAULT 0,
    orders      INT DEFAULT 0,
    units       FLOAT DEFAULT 0,
    aov         FLOAT DEFAULT 0,
    upt         FLOAT DEFAULT 0,
    PRIMARY KEY (d, store_id)
);

CREATE TABLE IF NOT EXISTS gold.monthly_revenue (
    year_month  TEXT NOT NULL,
    store_id    TEXT NOT NULL,
    store_name  TEXT,
    revenue     FLOAT DEFAULT 0,
    cogs        FLOAT DEFAULT 0,
    gross_profit FLOAT DEFAULT 0,
    orders      INT DEFAULT 0,
    PRIMARY KEY (year_month, store_id)
);
