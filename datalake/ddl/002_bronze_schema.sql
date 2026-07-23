-- 002_bronze_schema.sql — Bronze layer tables (1:1 from POS, snake_case)

CREATE TABLE IF NOT EXISTS bronze.orders (
    id              TEXT PRIMARY KEY,
    customer_id     TEXT,
    site_id         TEXT,
    need_pay_amount FLOAT DEFAULT 0,
    total_cost_price FLOAT DEFAULT 0,
    complete_at     TIMESTAMPTZ,
    delete_at       TIMESTAMPTZ,
    _batch_id       TEXT,
    _extracted_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bronze.order_items (
    id              TEXT PRIMARY KEY,
    order_id        TEXT,
    product_id      TEXT,
    quantity        FLOAT DEFAULT 0,
    unit_price      FLOAT DEFAULT 0,
    total_cost_price FLOAT DEFAULT 0,
    delete_at       TIMESTAMPTZ,
    _batch_id       TEXT,
    _extracted_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bronze.customers (
    id              TEXT PRIMARY KEY,
    name            TEXT,
    phone           TEXT,
    email           TEXT,
    gender          TEXT,
    date_of_birth   TIMESTAMPTZ,
    site_id         TEXT,
    create_at       TIMESTAMPTZ,
    delete_at       TIMESTAMPTZ,
    _batch_id       TEXT,
    _extracted_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bronze.products (
    id              TEXT PRIMARY KEY,
    name            TEXT,
    code            TEXT,
    category_id     TEXT,
    brand_id        TEXT,
    sell_price      FLOAT DEFAULT 0,
    cost_price      FLOAT DEFAULT 0,
    delete_at       TIMESTAMPTZ,
    _batch_id       TEXT,
    _extracted_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bronze.sites (
    id              TEXT PRIMARY KEY,
    name            TEXT,
    code            TEXT,
    province_code   TEXT,
    district_code   TEXT,
    address         TEXT,
    delete_at       TIMESTAMPTZ,
    _batch_id       TEXT,
    _extracted_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bronze.stock_history (
    id              TEXT PRIMARY KEY,
    warehouse_id    TEXT,
    product_id      TEXT,
    quantity        FLOAT DEFAULT 0,
    end_stock       FLOAT DEFAULT 0,
    cost_price      FLOAT DEFAULT 0,
    create_at       TIMESTAMPTZ,
    _batch_id       TEXT,
    _extracted_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bronze.warehouses (
    id              TEXT PRIMARY KEY,
    name            TEXT,
    site_id         TEXT,
    delete_at       TIMESTAMPTZ,
    _batch_id       TEXT,
    _extracted_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bronze.product_categories (
    id              TEXT PRIMARY KEY,
    name            TEXT,
    parent_id       TEXT,
    delete_at       TIMESTAMPTZ,
    _batch_id       TEXT,
    _extracted_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bronze.payment_orders (
    id              TEXT PRIMARY KEY,
    order_id        TEXT,
    amount          FLOAT DEFAULT 0,
    payment_method_id TEXT,
    create_at       TIMESTAMPTZ,
    delete_at       TIMESTAMPTZ,
    _batch_id       TEXT,
    _extracted_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bronze.return_orders (
    id              TEXT PRIMARY KEY,
    order_id        TEXT,
    site_id         TEXT,
    total_amount    FLOAT DEFAULT 0,
    reason          TEXT,
    complete_at     TIMESTAMPTZ,
    delete_at       TIMESTAMPTZ,
    _batch_id       TEXT,
    _extracted_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bronze.inventory (
    id              TEXT PRIMARY KEY,
    product_id      TEXT,
    warehouse_id    TEXT,
    on_hand         FLOAT DEFAULT 0,
    available       FLOAT DEFAULT 0,
    cost_price      FLOAT DEFAULT 0,
    update_at       TIMESTAMPTZ,
    _batch_id       TEXT,
    _extracted_at   TIMESTAMPTZ DEFAULT NOW()
);
