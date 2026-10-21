# -*- coding: utf-8 -*-
"""Resilience and reconciliation checks for Rocky WMS tools."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(os.environ.get("MCP_ROOT", Path(__file__).resolve().parent.parent))
ENV_FILE = Path(os.environ.get("MCP_ENV_FILE", ROOT / ".env"))
load_dotenv(ENV_FILE)
sys.path.insert(0, str(ROOT))

from mcp_server.config import DASHBOARD_PG_DSN  # noqa: E402
import mcp_server.wms_tools as wms  # noqa: E402


def inventory_reconciliation() -> dict:
    live: dict[tuple[str, str], float] = {}
    cached: dict[tuple[str, str], float] = {}

    with wms._get_wms_conn() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """SELECT COALESCE(w."SiteId", i."WarehouseId")::text,
                          i."ProductId"::text,
                          COALESCE(SUM(i."StockQuantity"), 0)
                   FROM "ProductItemWarehouseInventory" i
                   LEFT JOIN "Warehouse" w
                          ON w."Id" = i."WarehouseId" AND w."DeleteAt" IS NULL
                   WHERE i."DeleteAt" IS NULL
                   GROUP BY COALESCE(w."SiteId", i."WarehouseId"), i."ProductId"
                """
            )
            live = {(site, product): float(quantity) for site, product, quantity in cursor.fetchall()}

    with psycopg.connect(DASHBOARD_PG_DSN, connect_timeout=5) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """SELECT store_id, product_id, COALESCE(SUM(on_hand), 0)
                   FROM inventory_wms
                   GROUP BY store_id, product_id"""
            )
            cached = {(site, product): float(quantity) for site, product, quantity in cursor.fetchall()}
            cursor.execute("SELECT MAX(synced_at) FROM inventory_wms")
            cache_as_of = cursor.fetchone()[0]

    all_keys = set(live) | set(cached)
    mismatches = [key for key in all_keys if abs(live.get(key, 0) - cached.get(key, 0)) > 0.0001]
    live_total = sum(live.values())
    cache_total = sum(cached.values())
    return {
        "live_keys": len(live),
        "cache_keys": len(cached),
        "matching_keys": len(all_keys) - len(mismatches),
        "mismatched_keys": len(mismatches),
        "live_total_on_hand": round(live_total, 4),
        "cache_total_on_hand": round(cache_total, 4),
        "total_difference": round(cache_total - live_total, 4),
        "cache_as_of": (
            cache_as_of.isoformat() if hasattr(cache_as_of, "isoformat") else cache_as_of
        ),
    }


def main() -> int:
    original_dsn = wms.WMS_PG_DSN
    wms.WMS_PG_DSN = "postgresql://invalid:invalid@127.0.0.1:1/invalid"
    try:
        fallback = wms.query_inventory_live(limit=3)
        warehouse_fallback = wms.query_inventory_live(warehouse_code="TEST", limit=3)
    finally:
        wms.WMS_PG_DSN = original_dsn

    write_block = wms.query_raw_wms_sql('DELETE FROM "Warehouse"')
    excessive_range = wms.query_inventory_movements("2024-01-01", "2026-07-20")
    reconciliation = inventory_reconciliation()

    output = {
        "fallback": {
            "passed": fallback.get("source") == "dashboard_cache" and fallback.get("is_live") is False,
            "source": fallback.get("source"),
            "count": fallback.get("count"),
            "data_as_of": fallback.get("data_as_of"),
            "error": fallback.get("error"),
        },
        "warehouse_fallback_blocked": (
            warehouse_fallback.get("source") == "unavailable"
            and "warehouse-specific" in warehouse_fallback.get("error", "")
        ),
        "write_blocked": "error" in write_block,
        "excessive_range_blocked": "error" in excessive_range,
        "reconciliation": reconciliation,
    }
    print(json.dumps(output, ensure_ascii=True, separators=(",", ":")))
    return 0 if all((
        output["fallback"]["passed"],
        output["warehouse_fallback_blocked"],
        output["write_blocked"],
        output["excessive_range_blocked"],
    )) else 1


if __name__ == "__main__":
    raise SystemExit(main())
