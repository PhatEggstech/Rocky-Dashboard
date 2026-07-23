"""Transform — Execute Silver and Gold SQL transforms against warehouse PG.

Reads SQL files in prefix order (s_00_* first for dimensions, then s_daily_*, etc.)
and executes them against the WAREHOUSE_PG_DSN connection.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import psycopg

logger = logging.getLogger(__name__)

WAREHOUSE_PG_DSN = os.getenv("WAREHOUSE_PG_DSN", "")

SQL_BASE = Path(__file__).resolve().parent.parent / "sql"
SILVER_DIR = SQL_BASE / "silver"
GOLD_DIR = SQL_BASE / "gold"


def _execute_sql_dir(conn: psycopg.Connection, sql_dir: Path, layer: str) -> list[dict]:
    """Execute all SQL files in a directory, sorted by filename (prefix order).

    Returns list of execution results.
    """
    results = []
    sql_files = sorted(sql_dir.glob("*.sql"))

    if not sql_files:
        logger.warning("No SQL files found in %s", sql_dir)
        return results

    for sql_path in sql_files:
        start = time.time()
        try:
            sql = sql_path.read_text(encoding="utf-8")
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.rowcount or 0
            duration_ms = int((time.time() - start) * 1000)

            # Log to meta.pipeline_runs
            conn.execute(
                """INSERT INTO meta.pipeline_runs (layer, step, status, rows_affected, duration_ms)
                   VALUES (%s, %s, %s, %s, %s)""",
                (layer, sql_path.name, "success", rows, duration_ms),
            )

            logger.info("[%s] %s → %d rows (%dms)", layer, sql_path.name, rows, duration_ms)
            results.append({"file": sql_path.name, "rows": rows, "duration_ms": duration_ms, "status": "success"})

        except Exception as exc:
            duration_ms = int((time.time() - start) * 1000)
            logger.error("[%s] %s FAILED: %s", layer, sql_path.name, exc)
            conn.rollback()

            conn.execute(
                """INSERT INTO meta.pipeline_runs (layer, step, status, rows_affected, duration_ms, error_message)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (layer, sql_path.name, "failed", 0, duration_ms, str(exc)),
            )
            conn.commit()

            results.append({"file": sql_path.name, "rows": 0, "duration_ms": duration_ms, "status": "failed", "error": str(exc)})

    return results


def transform_silver() -> list[dict]:
    """Execute all silver transforms in order."""
    if not WAREHOUSE_PG_DSN:
        raise RuntimeError("WAREHOUSE_PG_DSN not set")

    with psycopg.connect(WAREHOUSE_PG_DSN, autocommit=False) as conn:
        results = _execute_sql_dir(conn, SILVER_DIR, "silver")
        conn.commit()
    return results


def transform_gold() -> list[dict]:
    """Execute all gold transforms in order."""
    if not WAREHOUSE_PG_DSN:
        raise RuntimeError("WAREHOUSE_PG_DSN not set")

    with psycopg.connect(WAREHOUSE_PG_DSN, autocommit=False) as conn:
        results = _execute_sql_dir(conn, GOLD_DIR, "gold")
        conn.commit()
    return results


def transform_all() -> dict:
    """Run silver then gold transforms. Returns combined results."""
    silver = transform_silver()
    gold = transform_gold()
    return {"silver": silver, "gold": gold}
