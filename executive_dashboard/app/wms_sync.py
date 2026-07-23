"""WMS (rocky_wms_dev) → Dashboard PostgreSQL sync for inventory KPIs.

Connects to the WMS PostgreSQL database and syncs real inventory data
(stock levels, stock cover days, dead stock) into the dashboard PostgreSQL.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from decimal import Decimal

logger = logging.getLogger(__name__)

WMS_PG_DSN = os.getenv("WMS_PG_DSN", "")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _to_float(val) -> float:
    """Convert Decimal/None to float safely."""
    if val is None:
        return 0.0
    if isinstance(val, Decimal):
        return float(val)
    return float(val)


def _to_str(val) -> str:
    """Convert UUID/None to str safely."""
    if val is None:
        return ""
    if hasattr(val, "hex"):  # UUID
        return str(val)
    return str(val)


def sync_inventory(dashboard_conn=None) -> dict:
    """Sync WMS Inventory + InventoryHistory → dashboard inventory_wms table.

    Returns dict with status and row count.
    If dashboard_conn is provided, uses it directly. Otherwise gets one from pool.
    """
    dsn = os.environ.get("WMS_PG_DSN", "")
    if not dsn:
        logger.warning("WMS_PG_DSN not set — skipping inventory sync")
        return {"status": "skipped", "reason": "WMS_PG_DSN not configured"}

    try:
        import psycopg
    except ImportError:
        logger.error("psycopg not installed — cannot sync WMS")
        return {"status": "error", "reason": "psycopg not installed"}

    try:
        from .db import get_conn, put_conn
    except ImportError:
        from db import get_conn, put_conn

    own_conn = dashboard_conn is None
    if own_conn:
        dashboard_conn = get_conn()

    try:
        pg = psycopg.connect(dsn, autocommit=True)
    except Exception as e:
        logger.error("Cannot connect to WMS: %s", e)
        if own_conn:
            put_conn(dashboard_conn)
        return {"status": "error", "reason": f"WMS connection failed: {e}"}

    try:
        rows_synced = _do_sync(dashboard_conn, pg)
        _update_sync_state(dashboard_conn, "inventory_wms", rows_synced, "ok")
        logger.info("WMS inventory sync complete: %d rows", rows_synced)
        
        # Sync picker performance as well
        try:
            picker_res = sync_picker_performance(dashboard_conn)
            logger.info("WMS picker performance sync complete: %s", picker_res)
        except Exception as pe:
            logger.error("WMS picker performance sync failed: %s", pe)
            
        return {"status": "ok", "rows_synced": rows_synced}
    except Exception as e:
        logger.error("WMS sync failed: %s", e)
        dashboard_conn.rollback()
        _update_sync_state(dashboard_conn, "inventory_wms", 0, "error", str(e))
        return {"status": "error", "reason": str(e)}
    finally:
        pg.close()
        if own_conn:
            put_conn(dashboard_conn)


def sync_picker_performance(dashboard_conn=None) -> dict:
    """Sync WMS OutboundDelivery -> dashboard daily_picker_performance table."""
    dsn = os.environ.get("WMS_PG_DSN", "")
    if not dsn:
        return {"status": "skipped", "reason": "WMS_PG_DSN not configured"}

    try:
        import psycopg
    except ImportError:
        return {"status": "error", "reason": "psycopg not installed"}

    try:
        from .db import get_conn, put_conn
    except ImportError:
        from db import get_conn, put_conn

    own_conn = dashboard_conn is None
    if own_conn:
        dashboard_conn = get_conn()

    try:
        pg = psycopg.connect(dsn, autocommit=True)
    except Exception as e:
        if own_conn:
            put_conn(dashboard_conn)
        return {"status": "error", "reason": f"WMS connection failed: {e}"}

    try:
        # Fetch picker performance from WMS Staging
        cur = pg.execute("""
            SELECT 
                o."StaffId"::text AS staff_id,
                COALESCE(a."Name", 'Unknown') AS staff_name,
                DATE(o."CompleteAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::text AS d,
                COALESCE(o."SiteId"::text, '') AS store_id,
                COUNT(DISTINCT o."Id")::int AS orders_picked,
                SUM(o."TotalQuantity")::float AS items_picked,
                SUM(EXTRACT(epoch FROM (o."CompleteAt" - o."IssueAt")))::float AS total_pick_time
            FROM "OutboundDelivery" o
            LEFT JOIN "Account" a ON a."Id" = o."StaffId"
            WHERE o."DeleteAt" IS NULL 
              AND o."CompleteAt" IS NOT NULL
              AND o."StaffId" IS NOT NULL
            GROUP BY o."StaffId", a."Name", d, o."SiteId"
        """)
        rows = cur.fetchall()

        rows_synced = 0
        with dashboard_conn.cursor() as c:
            for r in rows:
                staff_id, staff_name, d, store_id, orders_picked, items_picked, total_pick_time = r
                if not store_id:
                    continue
                avg_pick_time = total_pick_time / orders_picked if orders_picked > 0 else 0.0
                
                c.execute(
                    """INSERT INTO daily_picker_performance
                       (staff_id, staff_name, d, store_id, orders_picked, items_picked, total_pick_time, avg_pick_time)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (staff_id, d, store_id) DO UPDATE SET
                         staff_name=EXCLUDED.staff_name,
                         orders_picked=EXCLUDED.orders_picked,
                         items_picked=EXCLUDED.items_picked,
                         total_pick_time=EXCLUDED.total_pick_time,
                         avg_pick_time=EXCLUDED.avg_pick_time""",
                    (staff_id, staff_name, d, store_id, orders_picked, items_picked, total_pick_time, avg_pick_time)
                )
                rows_synced += 1
        dashboard_conn.commit()
        _update_sync_state(dashboard_conn, "daily_picker_performance", rows_synced, "ok")
        return {"status": "ok", "rows_synced": rows_synced}
    except Exception as e:
        dashboard_conn.rollback()
        _update_sync_state(dashboard_conn, "daily_picker_performance", 0, "error", str(e))
        return {"status": "error", "reason": str(e)}
    finally:
        pg.close()
        if own_conn:
            put_conn(dashboard_conn)


def _do_sync(conn, pg) -> int:
    """Execute the actual sync logic."""
    now_iso = _now_iso()

    # Fetch inventory from WMS
    cur = pg.execute("""
        SELECT
            i."ProductId",
            COALESCE(w."SiteId", i."WarehouseId") AS "StoreId",
            SUM(i."StockQuantity") AS "OnHand",
            SUM(i."StockQuantity") AS "Available",
            CASE WHEN SUM(i."StockQuantity") <> 0
                 THEN SUM(i."StockQuantity" * COALESCE(i."CostPrice", 0))
                      / SUM(i."StockQuantity")
                 ELSE AVG(i."CostPrice")
            END AS "CostPrice"
        FROM "ProductItemWarehouseInventory" i
        LEFT JOIN "Warehouse" w
               ON w."Id" = i."WarehouseId" AND w."DeleteAt" IS NULL
        WHERE i."DeleteAt" IS NULL
          AND i."StockQuantity" IS NOT NULL
        GROUP BY i."ProductId", COALESCE(w."SiteId", i."WarehouseId")
    """)
    wms_rows = cur.fetchall()

    if not wms_rows:
        logger.warning("No inventory rows found in WMS")
        return 0

    # Fetch last movement dates from InventoryHistory
    last_movements = {}
    try:
        cur_hist = pg.execute("""
            SELECT
                h."ProductId",
                COALESCE(w."SiteId", h."WarehouseId") AS "StoreId",
                MAX(h."IssueAt") as last_movement
            FROM "InventoryHistory" h
            LEFT JOIN "Warehouse" w
                   ON w."Id" = h."WarehouseId" AND w."DeleteAt" IS NULL
            WHERE h."DeleteAt" IS NULL
            GROUP BY h."ProductId", COALESCE(w."SiteId", h."WarehouseId")
        """)
        for row in cur_hist.fetchall():
            key = (_to_str(row[0]), _to_str(row[1]))
            last_movements[key] = row[2].isoformat() if row[2] else None
    except Exception as e:
        logger.warning("Could not fetch InventoryHistory: %s", e)

    # Fetch product info from WMS
    product_info = {}
    try:
        # Try production first: join Product -> ProductCategory via ProductCategoryId
        cur_prod = pg.execute("""
            SELECT p."Id", p."Name", pc."Name" AS cat_name
            FROM "Product" p
            LEFT JOIN "ProductCategory" pc ON pc."Id" = p."ProductCategoryId"
            WHERE p."DeleteAt" IS NULL
        """)
        for row in cur_prod.fetchall():
            product_info[_to_str(row[0])] = {
                "name": row[1] or "",
                "category": row[2] or "",
            }
    except Exception as e:
        logger.warning("Could not fetch Product info via ProductCategoryId: %s. Trying dev fallbacks...", e)
        try:
            cur_prod = pg.execute("""
                SELECT "Id", "Name", "CategoryName"
                FROM "Product"
                WHERE "DeleteAt" IS NULL
            """)
            for row in cur_prod.fetchall():
                product_info[_to_str(row[0])] = {
                    "name": row[1] or "",
                    "category": row[2] or "",
                }
        except Exception as e2:
            logger.warning("Could not fetch Product info via CategoryName: %s. Trying legacy Category join...", e2)
            try:
                cur_prod2 = pg.execute("""
                    SELECT p."Id", p."Name", c."Name" as cat_name
                    FROM "Product" p
                    LEFT JOIN "Category" c ON c."Id" = p."CategoryId"
                    WHERE p."DeleteAt" IS NULL
                """)
                for row in cur_prod2.fetchall():
                    product_info[_to_str(row[0])] = {
                        "name": row[1] or "",
                        "category": row[2] or "",
                    }
            except Exception as e3:
                logger.warning("All Product info sync attempts failed: %s", e3)

    # Compute daily sales rate from dashboard PG
    daily_sales_rate = _compute_daily_sales_rate(conn)

    # Build insert rows
    insert_rows = []
    for row in wms_rows:
        product_id = _to_str(row[0])
        store_id = _to_str(row[1])
        on_hand = _to_float(row[2])
        available = _to_float(row[3])
        cost_price = _to_float(row[4])

        # Resolve product name/category
        prod = product_info.get(product_id, {})
        product_name = prod.get("name", "")
        category = prod.get("category", "")

        # Compute inventory value
        inventory_value = on_hand * cost_price

        # Stock cover days = on_hand / avg_daily_sales (cap 3650)
        avg_daily = daily_sales_rate.get((store_id, product_id), 0.0)
        if avg_daily > 0:
            stock_cover_days = min(on_hand / avg_daily, 3650.0)
        else:
            stock_cover_days = 3650.0 if on_hand > 0 else 0.0

        # Dead stock: on_hand > 0 and no movement in 90 days
        last_move_key = (product_id, store_id)
        last_move = last_movements.get(last_move_key)
        is_dead_stock = 0
        if on_hand > 0 and last_move:
            try:
                move_dt = datetime.fromisoformat(last_move.replace("Z", "+00:00"))
                days_since = (datetime.now(timezone.utc) - move_dt).days
                if days_since >= 90:
                    is_dead_stock = 1
            except (ValueError, TypeError):
                pass
        elif on_hand > 0 and not last_move:
            is_dead_stock = 1

        insert_rows.append((
            store_id,
            product_id,
            product_name,
            category,
            on_hand,
            available,
            cost_price,
            inventory_value,
            stock_cover_days,
            is_dead_stock,
            last_move,
            now_iso,
        ))

    # Write to dashboard PostgreSQL
    with conn.cursor() as c:
        c.execute("DELETE FROM inventory_wms")
        for row_data in insert_rows:
            c.execute(
                """INSERT INTO inventory_wms
                   (store_id, product_id, product_name, category, on_hand, available,
                    cost_price, inventory_value, stock_cover_days, is_dead_stock,
                    last_movement_at, synced_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (store_id, product_id) DO UPDATE SET
                    product_name=EXCLUDED.product_name, category=EXCLUDED.category,
                    on_hand=EXCLUDED.on_hand, available=EXCLUDED.available,
                    cost_price=EXCLUDED.cost_price, inventory_value=EXCLUDED.inventory_value,
                    stock_cover_days=EXCLUDED.stock_cover_days, is_dead_stock=EXCLUDED.is_dead_stock,
                    last_movement_at=EXCLUDED.last_movement_at, synced_at=EXCLUDED.synced_at""",
                row_data,
            )
    conn.commit()

    return len(insert_rows)


def _compute_daily_sales_rate(conn) -> dict:
    """Compute avg daily sales per (store_id, product_id) from product_performance.

    Returns dict mapping (store_id, product_id) → avg_daily_units.
    Since product_performance is monthly, we estimate daily = units_sold / 30.
    """
    rates: dict[tuple[str, str], float] = {}
    try:
        rows = conn.execute("""
            SELECT product_id, SUM(units_sold) as total_units,
                   COUNT(DISTINCT year_month) as months
            FROM product_performance
            WHERE units_sold > 0
            GROUP BY product_id
        """).fetchall()
        for row in rows:
            product_id = row[0]
            total_units = row[1] or 0
            months = row[2] or 1
            avg_daily = total_units / (months * 30.0)
            rates[("", product_id)] = avg_daily
    except Exception as e:
        logger.warning("Could not compute sales rate: %s", e)
    return rates


def _update_sync_state(
    conn,
    section: str,
    rows: int,
    status: str = "ok",
    error: str | None = None,
) -> None:
    conn.execute(
        """INSERT INTO sync_state (section, last_success_at, rows_synced, status, error)
           VALUES (%s, %s, %s, %s, %s)
           ON CONFLICT (section) DO UPDATE SET
            last_success_at=EXCLUDED.last_success_at, rows_synced=EXCLUDED.rows_synced,
            status=EXCLUDED.status, error=EXCLUDED.error""",
        (section, _now_iso(), rows, status, error),
    )
    conn.commit()
