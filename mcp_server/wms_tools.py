# -*- coding: utf-8 -*-
"""Read-only tools for the Rocky WMS database."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import psycopg

from .config import DASHBOARD_PG_DSN, WMS_PG_DSN, WMS_QUERY_TIMEOUT_MS

_MAX_LIMIT = 200
_RAW_MAX_ROWS = 200
_FORBIDDEN_SQL = re.compile(
    r"\b(insert|update|delete|merge|drop|alter|truncate|create|copy|call|do|"
    r"grant|revoke|refresh|vacuum|analyze|set|reset|listen|notify|unlisten|"
    r"into|for\s+update|for\s+share)\b|pg_sleep|dblink|lo_import|lo_export",
    re.IGNORECASE,
)


def _get_wms_conn():
    if not WMS_PG_DSN:
        raise RuntimeError("WMS_PG_DSN is not configured")
    options = (
        "-c default_transaction_read_only=on "
        f"-c statement_timeout={max(1000, WMS_QUERY_TIMEOUT_MS)} "
        "-c idle_in_transaction_session_timeout=20000"
    )
    return psycopg.connect(
        WMS_PG_DSN,
        connect_timeout=5,
        options=options,
        application_name="rocky-mcp-wms",
    )


def _limit(value: int) -> int:
    return max(1, min(int(value), _MAX_LIMIT))


def _date_range(date_from: str, date_to: str, max_days: int = 366) -> tuple[date, date]:
    start = date.fromisoformat(date_from)
    end = date.fromisoformat(date_to)
    if end < start:
        raise ValueError("date_to must be on or after date_from")
    if (end - start).days > max_days:
        raise ValueError(f"Date range cannot exceed {max_days} days")
    return start, end


def _value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "hex"):
        return str(value)
    return value


def _rows(cursor) -> list[dict[str, Any]]:
    columns = [column.name for column in cursor.description]
    return [dict(zip(columns, (_value(value) for value in row))) for row in cursor.fetchall()]


def _cache_inventory(
    warehouse_code: str | None,
    product_search: str | None,
    low_stock_only: bool,
    limit: int,
    live_error: str,
) -> dict:
    """Graceful fallback for summary inventory when live WMS is unavailable."""
    if not DASHBOARD_PG_DSN:
        return {"error": "WMS unavailable and dashboard cache is not configured", "source": "unavailable"}

    if warehouse_code:
        return {
            "error": "Live WMS is unavailable; warehouse-specific cache fallback is not supported",
            "source": "unavailable",
            "details": "Live WMS connection failed; retry when the direct route is healthy.",
        }

    conditions: list[str] = []
    params: list[Any] = []
    if product_search:
        conditions.append("(product_name ILIKE %s OR product_id ILIKE %s)")
        params.extend([f"%{product_search}%", f"%{product_search}%"])
    if low_stock_only:
        conditions.append("available <= 0")
    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    try:
        with psycopg.connect(DASHBOARD_PG_DSN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""SELECT store_id AS site_id, product_id, product_name, category,
                               on_hand, available, cost_price, inventory_value,
                               last_movement_at, synced_at
                        FROM inventory_wms {where}
                        ORDER BY inventory_value DESC NULLS LAST
                        LIMIT %s""",
                    params + [_limit(limit)],
                )
                rows = _rows(cur)
                cur.execute("SELECT MAX(synced_at) FROM inventory_wms")
                data_as_of = _value(cur.fetchone()[0])
        return {
            "metric": "wms_live_inventory",
            "source": "dashboard_cache",
            "is_live": False,
            "data_as_of": data_as_of,
            "warning": f"Live WMS unavailable; returned cached inventory ({live_error}).",
            "rows": rows,
            "count": len(rows),
        }
    except Exception as cache_error:
        return {
            "error": "Both live WMS and dashboard cache are unavailable",
            "source": "unavailable",
            "details": f"live={live_error}; cache={type(cache_error).__name__}",
        }


def query_wms_health() -> dict:
    """Check the direct read-only WMS route and report non-sensitive metadata."""
    try:
        with _get_wms_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT current_database(), NOW(),
                              (SELECT COUNT(*) FROM "Warehouse" WHERE "DeleteAt" IS NULL),
                              (SELECT COUNT(*) FROM "Site" WHERE "DeleteAt" IS NULL)"""
                )
                database, checked_at, warehouses, sites = cur.fetchone()
        return {
            "metric": "wms_health",
            "status": "ok",
            "source": "wms_live",
            "database": database,
            "checked_at": _value(checked_at),
            "warehouses": warehouses,
            "sites": sites,
            "read_only": True,
        }
    except Exception as error:
        return {
            "metric": "wms_health",
            "status": "error",
            "source": "wms_live",
            "error": f"{type(error).__name__}: {str(error).splitlines()[0]}",
        }


def query_warehouses_live() -> dict:
    """List active warehouses/sites with live stock totals."""
    try:
        with _get_wms_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT w."Id" AS warehouse_id, w."Code" AS warehouse_code,
                              w."Name" AS warehouse_name, s."Id" AS site_id,
                              s."Code" AS site_code, s."Name" AS site_name,
                              COUNT(DISTINCT i."ProductId") AS product_count,
                              COALESCE(SUM(i."StockQuantity"), 0) AS on_hand
                       FROM "Warehouse" w
                       LEFT JOIN "Site" s ON s."Id" = w."SiteId" AND s."DeleteAt" IS NULL
                       LEFT JOIN "ProductItemWarehouseInventory" i
                              ON i."WarehouseId" = w."Id" AND i."DeleteAt" IS NULL
                       WHERE w."DeleteAt" IS NULL
                       GROUP BY w."Id", w."Code", w."Name", s."Id", s."Code", s."Name"
                       ORDER BY s."Name", w."Name"
                    """
                )
                rows = _rows(cur)
        return {"metric": "wms_warehouses", "source": "wms_live", "rows": rows, "count": len(rows)}
    except Exception as error:
        return {"error": f"WMS query failed: {type(error).__name__}: {str(error).splitlines()[0]}", "source": "wms_live"}


def query_inventory_live(
    warehouse_code: str | None = None,
    product_search: str | None = None,
    low_stock_only: bool = False,
    limit: int = 50,
) -> dict:
    """Query current stock directly from WMS, with dashboard-cache fallback."""
    conditions = ['i."DeleteAt" IS NULL', 'w."DeleteAt" IS NULL', 'p."DeleteAt" IS NULL']
    params: list[Any] = []
    if warehouse_code:
        conditions.append('(w."Code" ILIKE %s OR w."Name" ILIKE %s)')
        params.extend([f"%{warehouse_code}%", f"%{warehouse_code}%"])
    if product_search:
        conditions.append('(p."Code" ILIKE %s OR p."Name" ILIKE %s OR p."Barcode" ILIKE %s)')
        params.extend([f"%{product_search}%"] * 3)
    if low_stock_only:
        conditions.append('i."StockQuantity" <= COALESCE(p."StockLimitMin", 0)')
    where = " AND ".join(conditions)

    try:
        with _get_wms_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""SELECT w."Id" AS warehouse_id, w."Code" AS warehouse_code,
                               w."Name" AS warehouse_name, s."Name" AS site_name,
                               p."Id" AS product_id, p."Code" AS product_code,
                               p."Name" AS product_name, pc."Name" AS category,
                               SUM(i."StockQuantity") AS on_hand,
                               AVG(i."CostPrice") AS avg_cost_price,
                               SUM(i."StockQuantity" * COALESCE(i."CostPrice", 0)) AS inventory_value,
                               p."StockLimitMin" AS stock_limit_min,
                               p."StockLimitMax" AS stock_limit_max,
                               MAX(i."UpdateAt") AS updated_at
                        FROM "ProductItemWarehouseInventory" i
                        JOIN "Warehouse" w ON w."Id" = i."WarehouseId"
                        LEFT JOIN "Site" s ON s."Id" = w."SiteId" AND s."DeleteAt" IS NULL
                        JOIN "Product" p ON p."Id" = i."ProductId"
                        LEFT JOIN "ProductCategory" pc ON pc."Id" = p."ProductCategoryId"
                        WHERE {where}
                        GROUP BY w."Id", w."Code", w."Name", s."Name", p."Id", p."Code",
                                 p."Name", pc."Name", p."StockLimitMin", p."StockLimitMax"
                        ORDER BY inventory_value DESC NULLS LAST
                        LIMIT %s""",
                    params + [_limit(limit)],
                )
                rows = _rows(cur)
        return {
            "metric": "wms_live_inventory",
            "source": "wms_live",
            "is_live": True,
            "rows": rows,
            "count": len(rows),
        }
    except Exception as error:
        message = f"{type(error).__name__}: {str(error).splitlines()[0]}"
        return _cache_inventory(warehouse_code, product_search, low_stock_only, limit, message)


def query_inventory_movements(
    date_from: str,
    date_to: str,
    warehouse_code: str | None = None,
    product_search: str | None = None,
    include_cancelled: bool = False,
    limit: int = 100,
) -> dict:
    """Query WMS stock movement history for a bounded date range."""
    try:
        start, end = _date_range(date_from, date_to)
    except ValueError as error:
        return {"error": str(error)}

    conditions = ['h."DeleteAt" IS NULL', 'h."IssueAt" >= %s', 'h."IssueAt" < %s']
    params: list[Any] = [start, end + timedelta(days=1)]
    if not include_cancelled:
        conditions.append('COALESCE(h."IsCancel", FALSE) = FALSE')
    if warehouse_code:
        conditions.append('(w."Code" ILIKE %s OR w."Name" ILIKE %s)')
        params.extend([f"%{warehouse_code}%", f"%{warehouse_code}%"])
    if product_search:
        conditions.append('(p."Code" ILIKE %s OR p."Name" ILIKE %s OR h."ProductId"::text = %s)')
        params.extend([f"%{product_search}%", f"%{product_search}%", product_search])

    try:
        with _get_wms_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""SELECT h."IssueAt" AS issue_at, w."Code" AS warehouse_code,
                               w."Name" AS warehouse_name, s."Name" AS site_name,
                               p."Code" AS product_code, p."Name" AS product_name,
                               h."Quantity" AS quantity, h."StartStock" AS start_stock,
                               h."EndStock" AS end_stock, h."RefType" AS ref_type,
                               h."RefCode" AS reference_code, h."SubRefCode" AS sub_reference_code,
                               h."ActorCode" AS actor_code, h."IsCancel" AS is_cancelled
                        FROM "InventoryHistory" h
                        LEFT JOIN "Warehouse" w ON w."Id" = h."WarehouseId"
                        LEFT JOIN "Site" s ON s."Id" = h."SiteId"
                        LEFT JOIN "Product" p ON p."Id" = h."ProductId"
                        WHERE {' AND '.join(conditions)}
                        ORDER BY h."IssueAt" DESC
                        LIMIT %s""",
                    params + [_limit(limit)],
                )
                rows = _rows(cur)
        return {"metric": "wms_inventory_movements", "source": "wms_live", "rows": rows, "count": len(rows), "period": f"{date_from} to {date_to}"}
    except Exception as error:
        return {"error": f"WMS query failed: {type(error).__name__}: {str(error).splitlines()[0]}", "source": "wms_live"}


def query_outbound_deliveries(
    date_from: str,
    date_to: str,
    warehouse_code: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> dict:
    """Query outbound deliveries directly from WMS."""
    try:
        start, end = _date_range(date_from, date_to)
    except ValueError as error:
        return {"error": str(error)}

    conditions = ['d."DeleteAt" IS NULL', 'd."IssueAt" >= %s', 'd."IssueAt" < %s']
    params: list[Any] = [start, end + timedelta(days=1)]
    if warehouse_code:
        conditions.append('(w."Code" ILIKE %s OR w."Name" ILIKE %s)')
        params.extend([f"%{warehouse_code}%", f"%{warehouse_code}%"])
    status_key = status.lower().strip() if status else None
    if status_key == "completed":
        conditions.extend(['d."CompleteAt" IS NOT NULL', 'd."CancelAt" IS NULL'])
    elif status_key == "cancelled":
        conditions.append('d."CancelAt" IS NOT NULL')
    elif status_key == "processing":
        conditions.extend(['d."CompleteAt" IS NULL', 'd."CancelAt" IS NULL'])
    elif status_key:
        return {"error": "status must be completed, cancelled, or processing"}

    try:
        with _get_wms_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""SELECT d."Code" AS delivery_code, d."IssueAt" AS issue_at,
                               d."CompleteAt" AS completed_at, d."CancelAt" AS cancelled_at,
                               CASE WHEN d."CancelAt" IS NOT NULL THEN 'cancelled'
                                    WHEN d."CompleteAt" IS NOT NULL THEN 'completed'
                                    ELSE 'processing' END AS status,
                               w."Code" AS warehouse_code, w."Name" AS warehouse_name,
                               s."Name" AS site_name, d."TotalQuantity" AS total_quantity,
                               d."SubQuantity" AS line_count, d."TotalAmount" AS total_amount,
                               d."TotalCostPrice" AS total_cost_price,
                               d."OrderId" AS order_id, d."StockTransferOrderId" AS stock_transfer_order_id
                        FROM "OutboundDelivery" d
                        LEFT JOIN "Warehouse" w ON w."Id" = d."WarehouseId"
                        LEFT JOIN "Site" s ON s."Id" = d."SiteId"
                        WHERE {' AND '.join(conditions)}
                        ORDER BY d."IssueAt" DESC
                        LIMIT %s""",
                    params + [_limit(limit)],
                )
                rows = _rows(cur)
        return {"metric": "wms_outbound_deliveries", "source": "wms_live", "rows": rows, "count": len(rows), "period": f"{date_from} to {date_to}"}
    except Exception as error:
        return {"error": f"WMS query failed: {type(error).__name__}: {str(error).splitlines()[0]}", "source": "wms_live"}


def query_raw_wms_sql(sql: str) -> dict:
    """Execute one bounded SELECT/CTE against WMS in a read-only transaction."""
    statement = sql.strip()
    if not re.match(r"^(select|with)\b", statement, re.IGNORECASE):
        return {"error": "Only SELECT or read-only WITH queries are allowed."}
    if ";" in statement or "--" in statement or "/*" in statement or _FORBIDDEN_SQL.search(statement):
        return {"error": "The query contains a forbidden statement or token."}

    wrapped = f'SELECT * FROM ({statement}) AS "_rocky_wms_query" LIMIT {_RAW_MAX_ROWS + 1}'
    try:
        with _get_wms_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(wrapped)
                rows = _rows(cur)
        truncated = len(rows) > _RAW_MAX_ROWS
        return {
            "metric": "raw_wms_sql",
            "source": "wms_live",
            "rows": rows[:_RAW_MAX_ROWS],
            "count": min(len(rows), _RAW_MAX_ROWS),
            "truncated": truncated,
            "read_only": True,
        }
    except Exception as error:
        return {"error": f"WMS query failed: {type(error).__name__}: {str(error).splitlines()[0]}", "source": "wms_live"}
