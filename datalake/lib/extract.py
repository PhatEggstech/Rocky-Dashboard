"""Extract from POS PostgreSQL to Bronze layer.

Connects to POS via POS_PG_DSN, reads data incrementally using watermarks,
and loads into the warehouse bronze.* schema.
"""

from __future__ import annotations

import logging
import os
import re
import time
import uuid
from pathlib import Path

import psycopg

logger = logging.getLogger(__name__)

POS_PG_DSN = os.getenv("POS_PG_DSN", "")
WAREHOUSE_PG_DSN = os.getenv("WAREHOUSE_PG_DSN", "")

SQL_DIR = Path(__file__).resolve().parent.parent / "sql" / "bronze"

# Mapping: bronze SQL file -> watermark column in POS
EXTRACT_CONFIG = {
    "b_orders.sql": {"watermark_col": "CompleteAt", "table": "bronze.orders"},
    "b_order_items.sql": {"watermark_col": "UpdateAt", "table": "bronze.order_items"},
    "b_customers.sql": {"watermark_col": "UpdateAt", "table": "bronze.customers"},
    "b_products.sql": {"watermark_col": "UpdateAt", "table": "bronze.products"},
    "b_sites.sql": {"watermark_col": "UpdateAt", "table": "bronze.sites"},
    "b_stock_history.sql": {"watermark_col": "CreateAt", "table": "bronze.stock_history"},
}


def get_watermark(wh_conn: psycopg.Connection, table_name: str) -> str:
    """Read last watermark value for a table from meta.watermarks."""
    row = wh_conn.execute(
        "SELECT last_value FROM meta.watermarks WHERE table_name = %s",
        (table_name,),
    ).fetchone()
    if row and row[0]:
        return row[0]
    return "1970-01-01T00:00:00"


def set_watermark(wh_conn: psycopg.Connection, table_name: str, value: str) -> None:
    """Update watermark for a table."""
    wh_conn.execute(
        """INSERT INTO meta.watermarks (table_name, last_value, updated_at)
           VALUES (%s, %s, NOW())
           ON CONFLICT (table_name) DO UPDATE SET
               last_value = EXCLUDED.last_value,
               updated_at = EXCLUDED.updated_at""",
        (table_name, value),
    )


def extract_table(
    pos_conn: psycopg.Connection,
    wh_conn: psycopg.Connection,
    sql_file: str,
    batch_id: str,
) -> int:
    """Extract data from POS and load into warehouse bronze layer.

    Bronze SQL files use INSERT INTO bronze.X SELECT FROM "POS_TABLE".
    Since POS and warehouse are separate databases, we:
      1. Parse the SQL to extract the SELECT portion
      2. Execute SELECT on POS connection
      3. Execute INSERT on warehouse connection using fetched data

    Returns number of rows extracted.
    """
    config = EXTRACT_CONFIG.get(sql_file)
    if not config:
        logger.warning("No config for %s, skipping", sql_file)
        return 0

    table_name = config["table"]
    watermark = get_watermark(wh_conn, table_name)

    sql_path = SQL_DIR / sql_file
    if not sql_path.exists():
        logger.error("SQL file not found: %s", sql_path)
        return 0

    sql = sql_path.read_text(encoding="utf-8")
    logger.info("Extracting %s (watermark=%s)", table_name, watermark)

    # Parse: split INTO <columns> from SELECT ... FROM "Table" WHERE ...
    # SQL format: INSERT INTO bronze.X (cols) SELECT ... FROM "Table" WHERE ... ON CONFLICT ...

    # Extract the SELECT portion (between INSERT INTO ... and ON CONFLICT)
    match = re.search(
        r"INSERT\s+INTO\s+\S+\s*\(([^)]+)\)\s*(SELECT\s+.+?)(?:\s+ON\s+CONFLICT|$)",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        logger.error("Cannot parse SQL for %s", sql_file)
        return 0

    target_cols = match.group(1).strip()
    select_sql = match.group(2).strip()

    # The ON CONFLICT clause for upsert
    conflict_match = re.search(r"(ON\s+CONFLICT\s+.+)$", sql, re.IGNORECASE | re.DOTALL)
    conflict_clause = conflict_match.group(1).strip().rstrip(";") if conflict_match else ""

    # Replace :batch_id and :watermark with psycopg placeholders
    select_sql_parameterized = select_sql.replace(":batch_id", "%(batch_id)s").replace(":watermark", "%(watermark)s")

    params = {"batch_id": batch_id, "watermark": watermark}

    # Step 1: Execute SELECT on POS connection
    with pos_conn.cursor() as pos_cur:
        pos_cur.execute(select_sql_parameterized, params)
        rows_data = pos_cur.fetchall()

    if not rows_data:
        logger.info("No new rows for %s", table_name)
        set_watermark(wh_conn, table_name, time.strftime("%Y-%m-%dT%H:%M:%S"))
        return 0

    # Step 2: INSERT into warehouse
    col_list = [c.strip() for c in target_cols.split(",")]
    placeholders = ", ".join(["%s"] * len(col_list))
    insert_sql = f"INSERT INTO {table_name} ({target_cols}) VALUES ({placeholders})"
    if conflict_clause:
        insert_sql += f" {conflict_clause}"

    with wh_conn.cursor() as wh_cur:
        wh_cur.executemany(insert_sql, rows_data)
        rows = len(rows_data)

    # Update watermark
    set_watermark(wh_conn, table_name, time.strftime("%Y-%m-%dT%H:%M:%S"))
    logger.info("Extracted %d rows into %s", rows, table_name)
    return rows


def extract_all() -> dict:
    """Run full bronze extraction for all configured tables.

    Returns summary dict with table -> row counts.
    """
    if not POS_PG_DSN:
        raise RuntimeError("POS_PG_DSN not set")
    if not WAREHOUSE_PG_DSN:
        raise RuntimeError("WAREHOUSE_PG_DSN not set")

    batch_id = str(uuid.uuid4())
    results: dict[str, int] = {}

    with (
        psycopg.connect(POS_PG_DSN) as pos_conn,
        psycopg.connect(WAREHOUSE_PG_DSN, autocommit=False) as wh_conn,
    ):
        for sql_file in sorted(EXTRACT_CONFIG.keys()):
            try:
                rows = extract_table(pos_conn, wh_conn, sql_file, batch_id)
                results[sql_file] = rows
            except Exception as exc:
                logger.error("Failed extracting %s: %s", sql_file, exc)
                results[sql_file] = -1
                wh_conn.rollback()
                continue
        wh_conn.commit()

    return results
