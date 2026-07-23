"""CLI entrypoint for the Rocky Lens datalake pipeline.

Usage:
    python -m datalake.scripts.run_pipeline init    -- Create schemas/tables in warehouse PG
    python -m datalake.scripts.run_pipeline full    -- Extract + Silver + Gold
    python -m datalake.scripts.run_pipeline silver  -- Only silver transforms
    python -m datalake.scripts.run_pipeline gold    -- Only gold transforms
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import psycopg

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("datalake.pipeline")

WAREHOUSE_PG_DSN = os.getenv("WAREHOUSE_PG_DSN", "")
DDL_DIR = Path(__file__).resolve().parent.parent / "ddl"


def cmd_init() -> None:
    """Initialize warehouse database with schemas and tables."""
    if not WAREHOUSE_PG_DSN:
        logger.error("WAREHOUSE_PG_DSN not set")
        sys.exit(1)

    ddl_files = sorted(DDL_DIR.glob("*.sql"))
    if not ddl_files:
        logger.error("No DDL files found in %s", DDL_DIR)
        sys.exit(1)

    with psycopg.connect(WAREHOUSE_PG_DSN, autocommit=True) as conn:
        for ddl_path in ddl_files:
            logger.info("Executing %s", ddl_path.name)
            sql = ddl_path.read_text(encoding="utf-8")
            conn.execute(sql)
            logger.info("  ✓ %s done", ddl_path.name)

    logger.info("Database initialized successfully")


def cmd_full() -> None:
    """Run full pipeline: extract → silver → gold."""
    from ..lib.extract import extract_all
    from ..lib.transform import transform_all

    logger.info("=== FULL PIPELINE START ===")

    logger.info("--- Extract (POS → Bronze) ---")
    extract_results = extract_all()
    for table, rows in extract_results.items():
        status = "OK" if rows >= 0 else "FAILED"
        logger.info("  %s: %d rows [%s]", table, abs(rows), status)

    logger.info("--- Transform (Silver + Gold) ---")
    transform_results = transform_all()
    for layer, steps in transform_results.items():
        for step in steps:
            logger.info("  [%s] %s: %d rows [%s]", layer, step["file"], step["rows"], step["status"])

    logger.info("=== FULL PIPELINE COMPLETE ===")


def cmd_silver() -> None:
    """Run only silver transforms."""
    from ..lib.transform import transform_silver

    logger.info("--- Transform Silver ---")
    results = transform_silver()
    for step in results:
        logger.info("  %s: %d rows [%s]", step["file"], step["rows"], step["status"])


def cmd_gold() -> None:
    """Run only gold transforms."""
    from ..lib.transform import transform_gold

    logger.info("--- Transform Gold ---")
    results = transform_gold()
    for step in results:
        logger.info("  %s: %d rows [%s]", step["file"], step["rows"], step["status"])


COMMANDS = {
    "init": cmd_init,
    "full": cmd_full,
    "silver": cmd_silver,
    "gold": cmd_gold,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        print(f"Available commands: {', '.join(COMMANDS.keys())}")
        sys.exit(1)

    cmd = sys.argv[1]
    COMMANDS[cmd]()


if __name__ == "__main__":
    main()
