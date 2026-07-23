"""PostgreSQL connection pool and schema initialisation for Rocky Lens Dashboard."""

from __future__ import annotations

import logging
import os

import psycopg
from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Connection pool
# ---------------------------------------------------------------------------

_pool: ConnectionPool | None = None


def _get_dsn() -> str:
    """Return dashboard PostgreSQL DSN from environment."""
    dsn = os.environ.get("DASHBOARD_PG_DSN")
    if not dsn:
        raise RuntimeError("DASHBOARD_PG_DSN is required")
    return dsn


def get_pool() -> ConnectionPool:
    """Return (or create) the shared connection pool."""
    global _pool
    if _pool is None:
        dsn = _get_dsn()
        _pool = ConnectionPool(
            dsn,
            min_size=2,
            max_size=10,
            open=True,
            kwargs={"autocommit": False},
        )
        logger.info("PostgreSQL pool created: %s", dsn.split("@")[-1])
    return _pool


def get_conn():
    """Return a connection from the pool (caller must close/return it)."""
    return get_pool().getconn()


def put_conn(conn):
    """Return a connection to the pool."""
    get_pool().putconn(conn)


def close_pool():
    """Close the connection pool (on shutdown)."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

_DDL = """
-- Master: stores
CREATE TABLE IF NOT EXISTS stores (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    code        TEXT,
    pos_site_id TEXT,
    province    TEXT,
    region      TEXT,
    staff_count INTEGER DEFAULT 0
);

-- Fact: daily sales (split by customer type: HMK vs retail)
CREATE TABLE IF NOT EXISTS daily_sales (
    store_id            TEXT NOT NULL,
    d                   TEXT NOT NULL,
    is_hmk              BOOLEAN NOT NULL DEFAULT FALSE,
    revenue             DOUBLE PRECISION DEFAULT 0,
    orders_n            INTEGER DEFAULT 0,
    completed_orders_n  INTEGER DEFAULT 0,
    units_sold          INTEGER DEFAULT 0,
    cogs                DOUBLE PRECISION DEFAULT 0,
    gross_profit        DOUBLE PRECISION DEFAULT 0,
    avg_order_value     DOUBLE PRECISION DEFAULT 0,
    unique_customers    INTEGER DEFAULT 0,
    subtotal            DOUBLE PRECISION DEFAULT 0,
    PRIMARY KEY (store_id, d, is_hmk)
);

-- Fact: daily customer segments
CREATE TABLE IF NOT EXISTS daily_customer_segments (
    store_id              TEXT NOT NULL,
    d                     TEXT NOT NULL,
    new_customers_n       INTEGER DEFAULT 0,
    returning_customers_n INTEGER DEFAULT 0,
    PRIMARY KEY (store_id, d)
);

-- Fact: monthly revenue
CREATE TABLE IF NOT EXISTS monthly_revenue (
    store_id   TEXT NOT NULL,
    year_month TEXT NOT NULL,
    revenue    DOUBLE PRECISION DEFAULT 0,
    orders_n   INTEGER DEFAULT 0,
    growth_pct DOUBLE PRECISION,
    PRIMARY KEY (store_id, year_month)
);

-- Snapshot: customer RFM
CREATE TABLE IF NOT EXISTS customer_rfm (
    customer_id  TEXT PRIMARY KEY,
    name         TEXT,
    recency_days INTEGER,
    frequency    INTEGER,
    monetary     DOUBLE PRECISION,
    segment      TEXT
);

-- Fact: product performance (monthly)
CREATE TABLE IF NOT EXISTS product_performance (
    product_id TEXT NOT NULL,
    name       TEXT,
    category   TEXT,
    revenue    DOUBLE PRECISION DEFAULT 0,
    units_sold INTEGER DEFAULT 0,
    avg_price  DOUBLE PRECISION DEFAULT 0,
    year_month TEXT NOT NULL,
    PRIMARY KEY (product_id, year_month)
);

-- Fact: payment methods
CREATE TABLE IF NOT EXISTS payment_methods (
    store_id    TEXT NOT NULL,
    d           TEXT NOT NULL,
    method_name TEXT NOT NULL,
    amount      DOUBLE PRECISION DEFAULT 0,
    count       INTEGER DEFAULT 0,
    PRIMARY KEY (store_id, d, method_name)
);

-- Snapshot: debt report (B2B) — from POS DebtReport table (daily per customer)
CREATE TABLE IF NOT EXISTS debt_report (
    customer_id          TEXT NOT NULL,
    customer_name        TEXT,
    start_at             TEXT NOT NULL,
    end_at               TEXT,
    previous_balance     DOUBLE PRECISION DEFAULT 0,
    debt_amount          DOUBLE PRECISION DEFAULT 0,
    total_receive_amount DOUBLE PRECISION DEFAULT 0,
    paid_amount          DOUBLE PRECISION DEFAULT 0,
    current_balance      DOUBLE PRECISION DEFAULT 0,
    recover_debt_rate    DOUBLE PRECISION DEFAULT 0,
    PRIMARY KEY (customer_id, start_at)
);

-- Legacy: customer debt (kept for backward compat)
CREATE TABLE IF NOT EXISTS customer_debt (
    customer_id        TEXT PRIMARY KEY,
    name               TEXT,
    debt_amount        DOUBLE PRECISION DEFAULT 0,
    need_pay           DOUBLE PRECISION DEFAULT 0,
    total_orders       INTEGER DEFAULT 0,
    last_transaction_at TEXT,
    left_amount        DOUBLE PRECISION DEFAULT 0,
    payment_state      INTEGER DEFAULT 0
);

-- Fact: monthly returns
CREATE TABLE IF NOT EXISTS monthly_returns (
    store_id      TEXT NOT NULL,
    year_month    TEXT NOT NULL,
    return_count  INTEGER DEFAULT 0,
    return_amount DOUBLE PRECISION DEFAULT 0,
    order_count   INTEGER DEFAULT 0,
    PRIMARY KEY (store_id, year_month)
);

-- Fact: WMS inventory (synced from rocky_wms_dev)
CREATE TABLE IF NOT EXISTS inventory_wms (
    store_id         TEXT NOT NULL,
    product_id       TEXT NOT NULL,
    product_name     TEXT,
    category         TEXT,
    on_hand          DOUBLE PRECISION DEFAULT 0,
    available        DOUBLE PRECISION DEFAULT 0,
    cost_price       DOUBLE PRECISION DEFAULT 0,
    inventory_value  DOUBLE PRECISION DEFAULT 0,
    stock_cover_days DOUBLE PRECISION DEFAULT 0,
    is_dead_stock    INTEGER DEFAULT 0,
    last_movement_at TEXT,
    synced_at        TEXT,
    PRIMARY KEY (store_id, product_id)
);

-- Meta: sync state
CREATE TABLE IF NOT EXISTS sync_state (
    section         TEXT PRIMARY KEY,
    last_success_at TEXT,
    rows_synced     INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'pending',
    error           TEXT
);

-- Staff directory
CREATE TABLE IF NOT EXISTS staff (
    id    TEXT PRIMARY KEY,
    name  TEXT NOT NULL,
    code  TEXT,
    phone TEXT,
    state INTEGER DEFAULT 0
);

-- Fact: daily staff revenue (revenue per staff per day)
CREATE TABLE IF NOT EXISTS daily_staff_revenue (
    staff_id   TEXT NOT NULL,
    store_id   TEXT NOT NULL,
    d          TEXT NOT NULL,
    revenue    DOUBLE PRECISION DEFAULT 0,
    orders_n   INTEGER DEFAULT 0,
    PRIMARY KEY (staff_id, store_id, d)
);

-- Fact: order list (recent orders for detail view)
CREATE TABLE IF NOT EXISTS order_list (
    order_id         TEXT PRIMARY KEY,
    store_id         TEXT,
    staff_id         TEXT,
    staff_name       TEXT,
    customer_name    TEXT,
    total_amount     DOUBLE PRECISION DEFAULT 0,
    paid_amount      DOUBLE PRECISION DEFAULT 0,
    payment_method   TEXT,
    status           TEXT,
    complete_at      TEXT,
    issue_at         TEXT
);

-- Fact: daily picker performance (WMS based)
CREATE TABLE IF NOT EXISTS daily_picker_performance (
    staff_id         TEXT NOT NULL,
    staff_name       TEXT,
    d                TEXT NOT NULL,
    store_id         TEXT NOT NULL,
    orders_picked    INTEGER DEFAULT 0,
    items_picked     DOUBLE PRECISION DEFAULT 0,
    total_pick_time  DOUBLE PRECISION DEFAULT 0,
    avg_pick_time    DOUBLE PRECISION DEFAULT 0,
    PRIMARY KEY (staff_id, d, store_id)
);

-- Auth: users
CREATE TABLE IF NOT EXISTS users (
    username        TEXT PRIMARY KEY,
    hashed_password TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'store_manager',
    store_ids       TEXT,
    region_ids      TEXT,
    is_active       INTEGER DEFAULT 1,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Telegram: staff mapping
CREATE TABLE IF NOT EXISTS staff_telegram_mapping (
    staff_code        TEXT PRIMARY KEY,
    telegram_chat_id  TEXT NOT NULL,
    registered_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Telegram: manager mapping
CREATE TABLE IF NOT EXISTS manager_telegram_mapping (
    manager_code      TEXT PRIMARY KEY,
    telegram_chat_id  TEXT NOT NULL,
    region_id         TEXT DEFAULT 'All',
    registered_at     TIMESTAMPTZ DEFAULT NOW()
);

-- B2B: customer credit limit configuration
CREATE TABLE IF NOT EXISTS customer_credit_limit (
    customer_id      TEXT PRIMARY KEY,
    customer_code    TEXT,
    credit_limit     DOUBLE PRECISION NOT NULL DEFAULT 0,
    debt_period_days INTEGER NOT NULL DEFAULT 30,
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);
"""

_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_daily_sales_store_d ON daily_sales(store_id, d);
CREATE INDEX IF NOT EXISTS idx_daily_sales_hmk ON daily_sales(is_hmk);
CREATE INDEX IF NOT EXISTS idx_daily_cust_seg_store_d ON daily_customer_segments(store_id, d);
CREATE INDEX IF NOT EXISTS idx_monthly_rev_store_ym ON monthly_revenue(store_id, year_month);
CREATE INDEX IF NOT EXISTS idx_product_perf_ym ON product_performance(year_month);
CREATE INDEX IF NOT EXISTS idx_payment_methods_store_d ON payment_methods(store_id, d);
CREATE INDEX IF NOT EXISTS idx_monthly_returns_store_ym ON monthly_returns(store_id, year_month);
CREATE INDEX IF NOT EXISTS idx_inventory_wms_store ON inventory_wms(store_id);
CREATE INDEX IF NOT EXISTS idx_staff_rev_store_d ON daily_staff_revenue(store_id, d);
CREATE INDEX IF NOT EXISTS idx_staff_rev_staff ON daily_staff_revenue(staff_id);
CREATE INDEX IF NOT EXISTS idx_order_list_store ON order_list(store_id);
CREATE INDEX IF NOT EXISTS idx_order_list_complete ON order_list(complete_at);
CREATE INDEX IF NOT EXISTS idx_debt_report_dates ON debt_report(start_at, end_at);
CREATE INDEX IF NOT EXISTS idx_picker_perf_staff ON daily_picker_performance(staff_id);
CREATE INDEX IF NOT EXISTS idx_picker_perf_d ON daily_picker_performance(d);
"""


def init_schema(conn=None) -> None:
    """Create all tables and indexes if they don't exist."""
    own_conn = conn is None
    if own_conn:
        conn = get_conn()
    try:
        cur = conn.cursor()
        # Execute DDL and indexes as a single script
        full_ddl = _DDL + "\n" + _INDEXES
        cur.execute(full_ddl)
        conn.commit()
        logger.info("PostgreSQL schema initialised / verified.")
    except Exception as e:
        conn.rollback()
        logger.error("Schema init failed: %s", e)
        raise
    finally:
        if own_conn:
            put_conn(conn)
