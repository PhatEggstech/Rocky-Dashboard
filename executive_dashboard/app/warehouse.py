"""Dual-source data access: Gold layer (PostgreSQL) or SQLite fallback.

Feature flag: EDP_USE_WAREHOUSE=1 → read from gold.* tables in warehouse PG.
Otherwise falls back to SQLite (existing behavior).
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Generator

logger = logging.getLogger(__name__)

EDP_USE_WAREHOUSE = os.getenv("EDP_USE_WAREHOUSE", "0") == "1"
WAREHOUSE_PG_DSN = os.getenv("WAREHOUSE_PG_DSN", "")

_pool = None


def _get_pool():
    """Lazy-initialize the connection pool for warehouse PG."""
    global _pool
    if _pool is not None:
        return _pool

    if not WAREHOUSE_PG_DSN:
        logger.warning("WAREHOUSE_PG_DSN not set, warehouse unavailable")
        return None

    try:
        from psycopg_pool import ConnectionPool

        _pool = ConnectionPool(
            conninfo=WAREHOUSE_PG_DSN,
            min_size=1,
            max_size=5,
            open=True,
        )
        logger.info("Warehouse connection pool initialized")
        return _pool
    except Exception as exc:
        logger.error("Failed to create warehouse pool: %s", exc)
        return None


@contextmanager
def warehouse_conn() -> Generator[Any, None, None]:
    """Context manager that yields a warehouse PG connection or None.

    Usage:
        with warehouse_conn() as conn:
            if conn is None:
                # Fallback to SQLite
                ...
            else:
                rows = conn.execute("SELECT ...").fetchall()
    """
    if not EDP_USE_WAREHOUSE:
        yield None
        return

    pool = _get_pool()
    if pool is None:
        yield None
        return

    try:
        with pool.connection() as conn:
            yield conn
    except Exception as exc:
        logger.error("Warehouse connection error: %s", exc)
        yield None


def warehouse_query(sql: str, params: tuple = ()) -> list[dict] | None:
    """Execute a query against the warehouse and return list of dicts.

    Returns None if warehouse is unavailable (caller should fallback to SQLite).
    """
    with warehouse_conn() as conn:
        if conn is None:
            return None
        try:
            cur = conn.execute(sql, params)
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]
        except Exception as exc:
            logger.error("Warehouse query failed: %s", exc)
            return None


def is_warehouse_available() -> bool:
    """Check if warehouse is enabled and reachable."""
    if not EDP_USE_WAREHOUSE:
        return False
    with warehouse_conn() as conn:
        return conn is not None
