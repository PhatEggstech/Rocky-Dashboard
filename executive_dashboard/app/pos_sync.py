"""POS PostgreSQL → Dashboard PostgreSQL sync module for Rocky Lens B2B Dashboard.

Connects to rocky_dev PostgreSQL (remote POS) and syncs denormalised data into the
local PostgreSQL dashboard database that the FastAPI dashboard reads from.

Schema mapping (rocky_dev):
  Order → Site: Order.WarehouseId → Warehouse.SiteId
  OrderItem → Order: OrderItem.OrderItemGroupId → OrderItemGroup.Id → OrderItemGroup.OrderId
  PaymentOrder → Order: via PaymentOrderItem (PaymentOrderId, OrderId)
  ReturnOrder → Order: ReturnOrder.OriginalOrderId
  ReturnOrder timestamps: CreateAt (not CreatedAt), CompleteAt
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


def resolve_pos_dsn() -> str | None:
    """Return POS DSN from environment or None."""
    return os.environ.get("POS_PG_DSN")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _pg_connect(dsn: str):
    """Create a psycopg connection and configure it to avoid parallel worker shared memory issues."""
    import psycopg

    conn = psycopg.connect(dsn, autocommit=True)
    orig_execute = conn.execute

    def safe_execute(query, params=None, **kwargs):
        with conn.transaction():
            try:
                orig_execute("SET LOCAL max_parallel_workers_per_gather = 0;")
                orig_execute("SET LOCAL max_parallel_workers = 0;")
            except Exception as e:
                logger.warning("Could not disable parallel query execution on POS connection: %s", e)
            return orig_execute(query, params, **kwargs)

    conn.execute = safe_execute
    return conn


def _to_tuple(row) -> tuple:
    """Convert a psycopg row to a tuple with Decimals→floats and UUIDs→str."""
    result = []
    for val in row:
        if isinstance(val, Decimal):
            result.append(float(val))
        elif hasattr(val, "hex"):  # UUID
            result.append(str(val))
        else:
            result.append(val)
    return tuple(result)


# ---------------------------------------------------------------------------
# Sync: stores
# ---------------------------------------------------------------------------


def sync_stores(conn, pg) -> int:
    """Sync Site table → stores."""
    cur = pg.execute("""
        SELECT "Id"::text, "Name", "Code"
        FROM "Site"
        WHERE "DeleteAt" IS NULL
        ORDER BY "Name"
    """)
    rows = cur.fetchall()

    with conn.cursor() as c:
        c.execute("DELETE FROM stores")
        for r in rows:
            c.execute(
                """INSERT INTO stores (id, name, code, pos_site_id)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, code=EXCLUDED.code""",
                (str(r[0]), r[1], r[2], str(r[0])),
            )
    conn.commit()
    _update_sync_state(conn, "stores", len(rows))
    logger.info("sync_stores: %d rows", len(rows))
    return len(rows)


# ---------------------------------------------------------------------------
# Sync: daily_sales — Order aggregated by site and day
# Uses: Order.WarehouseId → Warehouse.SiteId for site mapping
# ---------------------------------------------------------------------------


def sync_daily_sales(conn, pg) -> int:
    """Sync daily sales aggregated per site per day.

    Revenue (Doanh thu) = SUM(Order.ProductAmount) — total product value of all orders
    Subtotal (Doanh số) = SUM(Order.PaidAmount) WHERE PaymentState=3 — actual collected revenue
    DS trả lại = Revenue - Subtotal (outstanding/unpaid, computed not stored)

    Both grouped by Order.IssueAt (ngày phát hành đơn).
    Aligned with POS admin dashboard (admin.rocky.endpoint.eggstech.io).
    """
    # Revenue = Order.ProductAmount (tổng giá trị hàng đặt)
    # All orders: not deleted, not cancelled, by IssueAt
    # Also fetch orders_n, cogs, unique_customers from same query
    revenue_sql = """
        SELECT
            COALESCE(w."SiteId", (SELECT "Id" FROM "Site" WHERE "DeleteAt" IS NULL LIMIT 1))::text AS site_id,
            (o."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date::text AS d,
            COALESCE(SUM(o."ProductAmount"::float), 0) AS revenue,
            COUNT(DISTINCT o."Id")::int AS orders_n,
            COALESCE(SUM(o."TotalCostPrice"::float), 0) AS cogs,
            COUNT(DISTINCT o."CustomerId")::int AS unique_customers
        FROM "Order" o
        LEFT JOIN "Warehouse" w ON w."Id" = o."WarehouseId"
        WHERE o."DeleteAt" IS NULL
          AND o."CancelAt" IS NULL
          AND o."IssueAt" IS NOT NULL
          AND o."IssueAt" > '2020-01-01'
        GROUP BY COALESCE(w."SiteId", (SELECT "Id" FROM "Site" WHERE "DeleteAt" IS NULL LIMIT 1)),
                 (o."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
        ORDER BY d
    """

    # Subtotal (Doanh số) = Order.PaidAmount WHERE PaymentState = 3 (đã thanh toán hoàn tất)
    # Tiền thực thu — only fully-paid orders count
    subtotal_sql = """
        SELECT
            COALESCE(w."SiteId", (SELECT "Id" FROM "Site" WHERE "DeleteAt" IS NULL LIMIT 1))::text AS site_id,
            (o."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date::text AS d,
            COALESCE(SUM(o."PaidAmount"::float), 0) AS subtotal
        FROM "Order" o
        LEFT JOIN "Warehouse" w ON w."Id" = o."WarehouseId"
        WHERE o."DeleteAt" IS NULL
          AND o."CancelAt" IS NULL
          AND o."PaymentState" = 3
          AND o."IssueAt" IS NOT NULL
          AND o."IssueAt" > '2020-01-01'
        GROUP BY COALESCE(w."SiteId", (SELECT "Id" FROM "Site" WHERE "DeleteAt" IS NULL LIMIT 1)),
                 (o."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
        ORDER BY d
    """

    # Fetch revenue + order metrics
    cur = pg.execute(revenue_sql)
    revenue_rows = cur.fetchall()

    # Build revenue lookup: (site_id, d) → (revenue, orders_n, cogs, unique_customers)
    data_map: dict[tuple[str, str], dict] = {}
    for r in revenue_rows:
        row = _to_tuple(r)
        key = (str(row[0]), str(row[1]))
        data_map[key] = {
            "revenue": float(row[2]),
            "orders_n": int(row[3]),
            "cogs": float(row[4]),
            "unique_customers": int(row[5]),
        }

    # Fetch subtotal data
    cur = pg.execute(subtotal_sql)
    subtotal_rows = cur.fetchall()
    subtotal_map: dict[tuple[str, str], float] = {}
    for r in subtotal_rows:
        row = _to_tuple(r)
        subtotal_map[(str(row[0]), str(row[1]))] = float(row[2])

    # Write to daily_sales
    with conn.cursor() as c:
        c.execute("DELETE FROM daily_sales")

        for key, data in data_map.items():
            site_id, d = key
            revenue = data["revenue"]
            orders_n = data["orders_n"]
            cogs = data["cogs"]
            unique_customers = data["unique_customers"]
            subtotal = subtotal_map.get(key, 0.0)
            gross_profit = revenue - cogs
            avg_order_value = revenue / orders_n if orders_n > 0 else 0.0

            c.execute(
                """INSERT INTO daily_sales
                   (store_id, d, revenue, orders_n, units_sold, cogs,
                    gross_profit, avg_order_value, unique_customers, subtotal)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (store_id, d) DO UPDATE SET
                    revenue=EXCLUDED.revenue, orders_n=EXCLUDED.orders_n,
                    units_sold=EXCLUDED.units_sold, cogs=EXCLUDED.cogs,
                    gross_profit=EXCLUDED.gross_profit, avg_order_value=EXCLUDED.avg_order_value,
                    unique_customers=EXCLUDED.unique_customers, subtotal=EXCLUDED.subtotal""",
                (site_id, d, revenue, orders_n, 0, cogs,
                 gross_profit, avg_order_value, unique_customers, subtotal),
            )

    conn.commit()

    # Patch units_sold from OrderItem
    _patch_units_sold(conn, pg)

    total_rows = len(data_map)
    _update_sync_state(conn, "daily_sales", total_rows)
    logger.info("sync_daily_sales: %d rows (revenue=Order.ProductAmount, subtotal=Order.PaidAmount@State3)", total_rows)
    return total_rows


def _patch_units_sold(conn, pg) -> None:
    """Update units_sold from OrderItem via OrderItemGroup → Order."""
    sql = """
        SELECT
            COALESCE(w."SiteId",
                (SELECT "Id" FROM "Site" WHERE "DeleteAt" IS NULL LIMIT 1))::text AS site_id,
            (o."CompleteAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date::text AS d,
            COALESCE(SUM(oi."Quantity"::float), 0)::int AS units_sold
        FROM "OrderItem" oi
        JOIN "OrderItemGroup" oig ON oig."Id" = oi."OrderItemGroupId"
        JOIN "Order" o ON o."Id" = oig."OrderId"
            AND o."DeleteAt" IS NULL
            AND o."CompleteAt" IS NOT NULL
        LEFT JOIN "Warehouse" w ON w."Id" = o."WarehouseId"
        WHERE oi."DeleteAt" IS NULL
        GROUP BY site_id, (o."CompleteAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
    """
    try:
        cur = pg.execute(sql)
        with conn.cursor() as c:
            for r in cur.fetchall():
                c.execute(
                    "UPDATE daily_sales SET units_sold = %s WHERE store_id = %s AND d = %s",
                    (int(r[2]), str(r[0]), r[1]),
                )
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.warning("_patch_units_sold failed: %s", e)


# ---------------------------------------------------------------------------
# Sync: customer segments (new vs returning)
# ---------------------------------------------------------------------------


def sync_customer_segments(conn, pg) -> int:
    """Identify new vs returning customers per day."""
    sql = """
        WITH first_purchase AS (
            SELECT
                "CustomerId",
                MIN(("CompleteAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date) AS first_d
            FROM "Order"
            WHERE "DeleteAt" IS NULL
              AND "CompleteAt" IS NOT NULL
              AND "CustomerId" IS NOT NULL
            GROUP BY "CustomerId"
        ),
        daily_customers AS (
            SELECT
                COALESCE(w."SiteId",
                    (SELECT "Id" FROM "Site" WHERE "DeleteAt" IS NULL LIMIT 1))::text AS site_id,
                (o."CompleteAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date AS d,
                o."CustomerId",
                fp.first_d
            FROM "Order" o
            LEFT JOIN "Warehouse" w ON w."Id" = o."WarehouseId"
            JOIN first_purchase fp ON fp."CustomerId" = o."CustomerId"
            WHERE o."DeleteAt" IS NULL
              AND o."CompleteAt" IS NOT NULL
              AND o."CustomerId" IS NOT NULL
              AND o."NeedPayAmount" > 0
              AND o."NeedPayAmount" < 100000000000
        )
        SELECT
            site_id,
            d::text,
            COUNT(DISTINCT CASE WHEN d = first_d THEN "CustomerId" END)::int AS new_customers_n,
            COUNT(DISTINCT CASE WHEN d > first_d THEN "CustomerId" END)::int AS returning_customers_n
        FROM daily_customers
        GROUP BY site_id, d
        ORDER BY d
    """
    cur = pg.execute(sql)
    rows = cur.fetchall()

    with conn.cursor() as c:
        c.execute("DELETE FROM daily_customer_segments")
        for r in rows:
            c.execute(
                """INSERT INTO daily_customer_segments
                   (store_id, d, new_customers_n, returning_customers_n)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (store_id, d) DO UPDATE SET
                    new_customers_n=EXCLUDED.new_customers_n,
                    returning_customers_n=EXCLUDED.returning_customers_n""",
                _to_tuple(r),
            )
    conn.commit()
    _update_sync_state(conn, "customer_segments", len(rows))
    logger.info("sync_customer_segments: %d rows", len(rows))
    return len(rows)


# ---------------------------------------------------------------------------
# Sync: customer RFM
# ---------------------------------------------------------------------------


def sync_customer_rfm(conn, pg) -> int:
    """Compute RFM scores for all customers with completed orders."""
    sql = """
        SELECT
            c."Id"::text AS customer_id,
            c."Name" AS name,
            EXTRACT(day FROM NOW() - MAX(o."CompleteAt"))::int AS recency_days,
            COUNT(DISTINCT o."Id")::int AS frequency,
            COALESCE(SUM(o."NeedPayAmount"::float), 0) AS monetary
        FROM "Customer" c
        JOIN "Order" o ON o."CustomerId" = c."Id"
            AND o."DeleteAt" IS NULL
            AND o."CompleteAt" IS NOT NULL
            AND o."NeedPayAmount" > 0
            AND o."NeedPayAmount" < 100000000000
        WHERE c."DeleteAt" IS NULL
        GROUP BY c."Id", c."Name"
        HAVING COUNT(DISTINCT o."Id") >= 1
        ORDER BY monetary DESC
    """
    cur = pg.execute(sql)
    rows = cur.fetchall()

    with conn.cursor() as c:
        c.execute("DELETE FROM customer_rfm")
        for r in rows:
            customer_id, name, recency_days, frequency, monetary = _to_tuple(r)
            segment = _rfm_segment(int(recency_days), int(frequency))
            c.execute(
                """INSERT INTO customer_rfm
                   (customer_id, name, recency_days, frequency, monetary, segment)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (customer_id) DO UPDATE SET
                    name=EXCLUDED.name, recency_days=EXCLUDED.recency_days,
                    frequency=EXCLUDED.frequency, monetary=EXCLUDED.monetary,
                    segment=EXCLUDED.segment""",
                (customer_id, name, int(recency_days), int(frequency), float(monetary), segment),
            )
    conn.commit()
    _update_sync_state(conn, "customer_rfm", len(rows))
    logger.info("sync_customer_rfm: %d rows", len(rows))
    return len(rows)


def _rfm_segment(recency_days: int, frequency: int) -> str:
    """Assign RFM segment based on recency and frequency thresholds."""
    if recency_days <= 30 and frequency >= 3:
        return "Champion"
    elif recency_days <= 60 and frequency >= 2:
        return "Loyal"
    elif recency_days <= 120:
        return "At-Risk"
    elif recency_days <= 365:
        return "Hibernating"
    else:
        return "Lost"


# ---------------------------------------------------------------------------
# Sync: product performance
# Uses: OrderItem → OrderItemGroup.OrderId → Order
# ---------------------------------------------------------------------------


def sync_product_performance(conn, pg) -> int:
    """Monthly product performance: revenue, units by product variant (ProductItem).

    Uses ProductItemId as the primary key to match POS admin which counts
    variants/SKUs (6000+) not just base products (144).
    Grouped by Order.IssueAt (aligned with revenue/subtotal timeline).
    """
    sql = """
        SELECT
            COALESCE(oi."ProductItemId", oi."ProductId")::text AS product_id,
            COALESCE(p."Name", 'Unknown') AS name,
            COALESCE(pc."Name", 'Uncategorized') AS category,
            COALESCE(SUM(oi."SubTotalIncludeDiscount"::float), 0) AS revenue,
            COALESCE(SUM(oi."Quantity"::float), 0)::int AS units_sold,
            CASE WHEN SUM(oi."Quantity") > 0
                 THEN SUM(oi."SubTotalIncludeDiscount"::float) / SUM(oi."Quantity"::float)
                 ELSE 0 END AS avg_price,
            TO_CHAR((o."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh'), 'YYYY-MM') AS year_month
        FROM "OrderItem" oi
        JOIN "OrderItemGroup" oig ON oig."Id" = oi."OrderItemGroupId"
        JOIN "Order" o ON o."Id" = oig."OrderId"
            AND o."DeleteAt" IS NULL
            AND o."CancelAt" IS NULL
            AND o."IssueAt" IS NOT NULL
        JOIN "Product" p ON p."Id" = oi."ProductId" AND p."DeleteAt" IS NULL
        LEFT JOIN "ProductCategory" pc ON pc."Id" = p."ProductCategoryId"
        WHERE oi."DeleteAt" IS NULL
        GROUP BY COALESCE(oi."ProductItemId", oi."ProductId"), p."Name", pc."Name",
                 TO_CHAR((o."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh'), 'YYYY-MM')
        ORDER BY year_month, revenue DESC
    """
    cur = pg.execute(sql)
    rows = cur.fetchall()

    with conn.cursor() as c:
        c.execute("DELETE FROM product_performance")
        for r in rows:
            c.execute(
                """INSERT INTO product_performance
                   (product_id, name, category, revenue, units_sold, avg_price, year_month)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (product_id, year_month) DO UPDATE SET
                    name=EXCLUDED.name, category=EXCLUDED.category,
                    revenue=EXCLUDED.revenue, units_sold=EXCLUDED.units_sold,
                    avg_price=EXCLUDED.avg_price""",
                _to_tuple(r),
            )
    conn.commit()
    _update_sync_state(conn, "product_performance", len(rows))
    logger.info("sync_product_performance: %d rows", len(rows))
    return len(rows)


# ---------------------------------------------------------------------------
# Sync: payment methods
# Uses: PaymentOrderItem to link PaymentOrder → Order
# ---------------------------------------------------------------------------


def sync_payment_methods(conn, pg) -> int:
    """Daily payment method breakdown."""
    sql = """
        SELECT
            COALESCE(w."SiteId",
                     (SELECT "Id" FROM "Site" WHERE "DeleteAt" IS NULL LIMIT 1))::text AS store_id,
            (po."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date::text AS d,
            pm."Name" AS method_name,
            COALESCE(SUM(po."PaidAmount"::float), 0) AS amount,
            COUNT(po."Id")::int AS count
        FROM "PaymentOrder" po
        JOIN "PaymentMethod" pm ON pm."Id" = po."PaymentMethodId"
        LEFT JOIN "Warehouse" w ON w."Id" = (
            SELECT o."WarehouseId" FROM "PaymentOrderItem" poi
            JOIN "Order" o ON o."Id" = poi."OrderId"
            WHERE poi."PaymentOrderId" = po."Id" AND poi."DeleteAt" IS NULL
            LIMIT 1
        )
        WHERE po."DeleteAt" IS NULL
          AND po."CompleteAt" IS NOT NULL
        GROUP BY store_id, d, pm."Name"
        ORDER BY d
    """
    cur = pg.execute(sql)
    rows = cur.fetchall()

    with conn.cursor() as c:
        c.execute("DELETE FROM payment_methods")
        for r in rows:
            c.execute(
                """INSERT INTO payment_methods
                   (store_id, d, method_name, amount, count)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (store_id, d, method_name) DO UPDATE SET
                    amount=EXCLUDED.amount, count=EXCLUDED.count""",
                _to_tuple(r),
            )
    conn.commit()
    _update_sync_state(conn, "payment_methods", len(rows))
    logger.info("sync_payment_methods: %d rows", len(rows))
    return len(rows)


# ---------------------------------------------------------------------------
# Sync: customer debt (B2B) — legacy from CustomerDebt table
# ---------------------------------------------------------------------------


def sync_customer_debt(conn, pg) -> int:
    """Sync customer debt from POS CustomerDebt table (pre-calculated by POS system)."""
    sql = """
        SELECT
            c."Id"::text AS customer_id,
            c."Name" AS name,
            COALESCE(cd."CurrentDebtAmount"::float, 0) AS debt_amount,
            COALESCE(cd."NeedPayAmount"::float, 0) AS need_pay,
            COALESCE(c."TotalNumberOrder", 0)::int AS total_orders,
            c."LastTransactionAt"::text AS last_transaction_at,
            COALESCE(cd."LeftAmount"::float, 0) AS left_amount,
            COALESCE(cd."PaymentState", 0)::int AS payment_state
        FROM "CustomerDebt" cd
        JOIN "Customer" c ON c."Id" = cd."CustomerId"
        WHERE cd."DeleteAt" IS NULL
          AND c."DeleteAt" IS NULL
        ORDER BY cd."CurrentDebtAmount" DESC
        LIMIT 500
    """
    cur = pg.execute(sql)
    rows = cur.fetchall()

    with conn.cursor() as c:
        c.execute("DELETE FROM customer_debt")
        for r in rows:
            c.execute(
                """INSERT INTO customer_debt
                   (customer_id, name, debt_amount, need_pay, total_orders,
                    last_transaction_at, left_amount, payment_state)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (customer_id) DO UPDATE SET
                    name=EXCLUDED.name, debt_amount=EXCLUDED.debt_amount,
                    need_pay=EXCLUDED.need_pay, total_orders=EXCLUDED.total_orders,
                    last_transaction_at=EXCLUDED.last_transaction_at,
                    left_amount=EXCLUDED.left_amount, payment_state=EXCLUDED.payment_state""",
                _to_tuple(r),
            )
    conn.commit()
    _update_sync_state(conn, "customer_debt", len(rows))
    logger.info("sync_customer_debt: %d rows", len(rows))
    return len(rows)


# ---------------------------------------------------------------------------
# Sync: debt report (B2B) — from DebtReport table (daily snapshots)
# ---------------------------------------------------------------------------


def sync_debt_report(conn, pg) -> int:
    """Sync debt report from POS DebtReport table.

    Only syncs the LATEST snapshot per customer (most recent StartAt).
    This matches POS admin which shows current balance, not historical.
    """
    sql = """
        SELECT
            dr."CustomerId"::text AS customer_id,
            COALESCE(c."Name", 'Unknown') AS customer_name,
            (dr."StartAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date::text AS start_at,
            (dr."EndAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date::text AS end_at,
            COALESCE(dr."PreviousBalance"::float, 0) AS previous_balance,
            COALESCE(dr."DebtAmount"::float, 0) AS debt_amount,
            COALESCE(dr."TotalReceiveAmount"::float, 0) AS total_receive_amount,
            COALESCE(dr."PaidAmount"::float, 0) AS paid_amount,
            COALESCE(dr."CurrentBalance"::float, 0) AS current_balance,
            COALESCE(dr."RecoverDebtRate"::float, 0) AS recover_debt_rate
        FROM "DebtReport" dr
        JOIN "Customer" c ON c."Id" = dr."CustomerId"
        WHERE dr."DeleteAt" IS NULL
          AND c."DeleteAt" IS NULL
          AND dr."StartAt" = (
              SELECT MAX(dr2."StartAt")
              FROM "DebtReport" dr2
              WHERE dr2."CustomerId" = dr."CustomerId"
              AND dr2."DeleteAt" IS NULL
          )
        ORDER BY dr."CurrentBalance" ASC
    """
    cur = pg.execute(sql)
    rows = cur.fetchall()

    with conn.cursor() as c:
        c.execute("DELETE FROM debt_report")
        for r in rows:
            c.execute(
                """INSERT INTO debt_report
                   (customer_id, customer_name, start_at, end_at,
                    previous_balance, debt_amount, total_receive_amount,
                    paid_amount, current_balance, recover_debt_rate)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (customer_id, start_at) DO UPDATE SET
                    customer_name=EXCLUDED.customer_name, end_at=EXCLUDED.end_at,
                    previous_balance=EXCLUDED.previous_balance, debt_amount=EXCLUDED.debt_amount,
                    total_receive_amount=EXCLUDED.total_receive_amount, paid_amount=EXCLUDED.paid_amount,
                    current_balance=EXCLUDED.current_balance, recover_debt_rate=EXCLUDED.recover_debt_rate""",
                _to_tuple(r),
            )
    conn.commit()
    _update_sync_state(conn, "debt_report", len(rows))
    logger.info("sync_debt_report: %d rows", len(rows))
    return len(rows)


# ---------------------------------------------------------------------------
# Sync: monthly returns
# Uses: ReturnOrder.CreateAt, ReturnOrder.OriginalOrderId
# ---------------------------------------------------------------------------


def sync_monthly_returns(conn, pg) -> int:
    """Monthly return orders aggregated."""
    sql = """
        SELECT
            COALESCE(
                (SELECT w."SiteId"::text FROM "Order" o
                 JOIN "Warehouse" w ON w."Id" = o."WarehouseId"
                 WHERE o."Id" = ro."OriginalOrderId" LIMIT 1),
                (SELECT "Id"::text FROM "Site" WHERE "DeleteAt" IS NULL LIMIT 1)
            ) AS store_id,
            TO_CHAR((ro."CompleteAt" AT TIME ZONE 'Asia/Ho_Chi_Minh'), 'YYYY-MM') AS year_month,
            COUNT(ro."Id")::int AS return_count,
            COALESCE(SUM(ro."TotalAmount"::float), 0) AS return_amount,
            0::int AS order_count
        FROM "ReturnOrder" ro
        WHERE ro."DeleteAt" IS NULL
          AND ro."CompleteAt" IS NOT NULL
        GROUP BY store_id, year_month
        ORDER BY year_month
    """
    cur = pg.execute(sql)
    rows = cur.fetchall()

    with conn.cursor() as c:
        c.execute("DELETE FROM monthly_returns")
        for r in rows:
            c.execute(
                """INSERT INTO monthly_returns
                   (store_id, year_month, return_count, return_amount, order_count)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (store_id, year_month) DO UPDATE SET
                    return_count=EXCLUDED.return_count, return_amount=EXCLUDED.return_amount""",
                _to_tuple(r),
            )
    conn.commit()

    # Patch order_count from Order table
    _patch_monthly_order_count(conn, pg)

    _update_sync_state(conn, "monthly_returns", len(rows))
    logger.info("sync_monthly_returns: %d rows", len(rows))
    return len(rows)


def _patch_monthly_order_count(conn, pg) -> None:
    """Fill in order_count for monthly_returns from the Order table."""
    sql = """
        SELECT
            TO_CHAR((o."CompleteAt" AT TIME ZONE 'Asia/Ho_Chi_Minh'), 'YYYY-MM') AS year_month,
            COUNT(o."Id")::int AS order_count
        FROM "Order" o
        WHERE o."DeleteAt" IS NULL AND o."CompleteAt" IS NOT NULL
          AND o."NeedPayAmount" > 0 AND o."NeedPayAmount" < 100000000000
        GROUP BY year_month
    """
    try:
        cur = pg.execute(sql)
        with conn.cursor() as c:
            for r in cur.fetchall():
                c.execute(
                    "UPDATE monthly_returns SET order_count = %s WHERE year_month = %s",
                    (int(r[1]), r[0]),
                )
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.warning("_patch_monthly_order_count failed: %s", e)


# ---------------------------------------------------------------------------
# Sync: monthly revenue (aggregated from daily_sales after daily sync)
# ---------------------------------------------------------------------------


def sync_monthly_revenue(conn) -> int:
    """Compute monthly_revenue from daily_sales already in dashboard PG."""
    with conn.cursor() as c:
        c.execute("DELETE FROM monthly_revenue")
        c.execute("""
            INSERT INTO monthly_revenue (store_id, year_month, revenue, orders_n)
            SELECT
                store_id,
                LEFT(d, 7) AS year_month,
                SUM(revenue),
                SUM(orders_n)
            FROM daily_sales
            GROUP BY store_id, LEFT(d, 7)
        """)
    conn.commit()

    # Compute growth_pct
    with conn.cursor() as c:
        c.execute("""
            SELECT store_id, year_month, revenue FROM monthly_revenue
            ORDER BY store_id, year_month
        """)
        rows = c.fetchall()

    prev_rev: dict[str, float] = {}
    with conn.cursor() as c:
        for r in rows:
            store_id, ym, rev = r[0], r[1], r[2]
            if store_id in prev_rev and prev_rev[store_id] > 0:
                growth = (rev - prev_rev[store_id]) / prev_rev[store_id] * 100
                c.execute(
                    "UPDATE monthly_revenue SET growth_pct = %s WHERE store_id = %s AND year_month = %s",
                    (round(growth, 2), store_id, ym),
                )
            prev_rev[store_id] = rev
    conn.commit()

    with conn.cursor() as c:
        c.execute("SELECT COUNT(*) FROM monthly_revenue")
        count = c.fetchone()[0]
    _update_sync_state(conn, "monthly_revenue", count)
    logger.info("sync_monthly_revenue: %d rows", count)
    return count


# ---------------------------------------------------------------------------
# Sync: staff directory
# ---------------------------------------------------------------------------


def sync_staff(conn, pg) -> int:
    """Sync Staff table."""
    sql = """
        SELECT "Id"::text, "Name", "Code", "Phone", "State"
        FROM "Staff"
        WHERE "DeleteAt" IS NULL
        ORDER BY "Name"
    """
    cur = pg.execute(sql)
    rows = cur.fetchall()

    with conn.cursor() as c:
        c.execute("DELETE FROM staff")
        for r in rows:
            c.execute(
                """INSERT INTO staff (id, name, code, phone, state)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (id) DO UPDATE SET
                    name=EXCLUDED.name, code=EXCLUDED.code,
                    phone=EXCLUDED.phone, state=EXCLUDED.state""",
                _to_tuple(r),
            )
    conn.commit()
    _update_sync_state(conn, "staff", len(rows))
    logger.info("sync_staff: %d rows", len(rows))
    return len(rows)


# ---------------------------------------------------------------------------
# Sync: staff revenue (DT per staff per day)
# ---------------------------------------------------------------------------


def sync_staff_revenue(conn, pg) -> int:
    """Sync revenue per staff per day from PaymentOrderItem."""
    sql = """
        SELECT
            COALESCE(o."StaffId", po."StaffId")::text AS staff_id,
            COALESCE(w."SiteId",
                (SELECT "Id" FROM "Site" WHERE "DeleteAt" IS NULL LIMIT 1))::text AS store_id,
            (po."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date::text AS d,
            COALESCE(SUM(poi."PaidAmount"::float), 0) AS revenue,
            COUNT(DISTINCT poi."OrderId")::int AS orders_n
        FROM "PaymentOrderItem" poi
        JOIN "PaymentOrder" po ON po."Id" = poi."PaymentOrderId"
        LEFT JOIN "Order" o ON o."Id" = poi."OrderId"
        LEFT JOIN "Warehouse" w ON w."Id" = o."WarehouseId"
        WHERE po."CompleteAt" IS NOT NULL
          AND po."CancelAt" IS NULL
          AND po."DocumentType" = 1
          AND poi."PaidAmount" > 0
          AND po."DeleteAt" IS NULL
          AND poi."DeleteAt" IS NULL
          AND po."IssueAt" IS NOT NULL
          AND po."IssueAt" > '2020-01-01'
          AND COALESCE(o."StaffId", po."StaffId") IS NOT NULL
        GROUP BY COALESCE(o."StaffId", po."StaffId"),
                 COALESCE(w."SiteId", (SELECT "Id" FROM "Site" WHERE "DeleteAt" IS NULL LIMIT 1)),
                 (po."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
        ORDER BY d
    """
    cur = pg.execute(sql)
    rows = cur.fetchall()

    with conn.cursor() as c:
        c.execute("DELETE FROM daily_staff_revenue")
        for r in rows:
            c.execute(
                """INSERT INTO daily_staff_revenue
                   (staff_id, store_id, d, revenue, orders_n)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (staff_id, store_id, d) DO UPDATE SET
                    revenue=EXCLUDED.revenue, orders_n=EXCLUDED.orders_n""",
                _to_tuple(r),
            )
    conn.commit()
    _update_sync_state(conn, "staff_revenue", len(rows))
    logger.info("sync_staff_revenue: %d rows", len(rows))
    return len(rows)


# ---------------------------------------------------------------------------
# Sync: order list (recent orders for detail table)
# ---------------------------------------------------------------------------


def sync_order_list(conn, pg) -> int:
    """Sync recent order list with staff, payment method info."""
    sql = """
        SELECT
            o."Id"::text AS order_id,
            COALESCE(w."SiteId",
                (SELECT "Id" FROM "Site" WHERE "DeleteAt" IS NULL LIMIT 1))::text AS store_id,
            o."StaffId"::text AS staff_id,
            s."Name" AS staff_name,
            c."Name" AS customer_name,
            COALESCE(o."TotalAmount"::float, 0) AS total_amount,
            COALESCE((
                SELECT SUM(poi2."PaidAmount"::float)
                FROM "PaymentOrderItem" poi2
                JOIN "PaymentOrder" po2 ON po2."Id" = poi2."PaymentOrderId"
                WHERE poi2."OrderId" = o."Id"
                  AND po2."CompleteAt" IS NOT NULL
                  AND po2."CancelAt" IS NULL
                  AND po2."DocumentType" = 1
                  AND poi2."DeleteAt" IS NULL
            ), 0) AS paid_amount,
            COALESCE((
                SELECT pm."Name"
                FROM "PaymentOrderItem" poi3
                JOIN "PaymentOrder" po3 ON po3."Id" = poi3."PaymentOrderId"
                JOIN "PaymentMethod" pm ON pm."Id" = po3."PaymentMethodId"
                WHERE poi3."OrderId" = o."Id"
                  AND po3."CompleteAt" IS NOT NULL
                  AND po3."CancelAt" IS NULL
                  AND poi3."DeleteAt" IS NULL
                LIMIT 1
            ), 'Unknown') AS payment_method,
            CASE
                WHEN o."CancelAt" IS NOT NULL THEN 'cancelled'
                WHEN o."CompleteAt" IS NOT NULL THEN 'completed'
                ELSE 'processing'
            END AS status,
            (o."CompleteAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::text AS complete_at,
            (o."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::text AS issue_at
        FROM "Order" o
        LEFT JOIN "Warehouse" w ON w."Id" = o."WarehouseId"
        LEFT JOIN "Staff" s ON s."Id" = o."StaffId"
        LEFT JOIN "Customer" c ON c."Id" = o."CustomerId"
        WHERE o."DeleteAt" IS NULL
          AND o."CompleteAt" IS NOT NULL
        ORDER BY o."CompleteAt" DESC
        LIMIT 500
    """
    cur = pg.execute(sql)
    rows = cur.fetchall()

    with conn.cursor() as c:
        c.execute("DELETE FROM order_list")
        for r in rows:
            c.execute(
                """INSERT INTO order_list
                   (order_id, store_id, staff_id, staff_name, customer_name,
                    total_amount, paid_amount, payment_method, status, complete_at, issue_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (order_id) DO UPDATE SET
                    store_id=EXCLUDED.store_id, staff_id=EXCLUDED.staff_id,
                    staff_name=EXCLUDED.staff_name, customer_name=EXCLUDED.customer_name,
                    total_amount=EXCLUDED.total_amount, paid_amount=EXCLUDED.paid_amount,
                    payment_method=EXCLUDED.payment_method, status=EXCLUDED.status,
                    complete_at=EXCLUDED.complete_at, issue_at=EXCLUDED.issue_at""",
                _to_tuple(r),
            )
    conn.commit()
    _update_sync_state(conn, "order_list", len(rows))
    logger.info("sync_order_list: %d rows", len(rows))
    return len(rows)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

_SECTIONS = [
    "stores",
    "staff",
    "daily_sales",
    "staff_revenue",
    "order_list",
    "customer_segments",
    "customer_rfm",
    "product_performance",
    "payment_methods",
    "customer_debt",
    "debt_report",
    "monthly_returns",
]


def sync_from_postgres(conn, sections: list[str] | None = None) -> dict[str, Any]:
    """Run full or partial sync from POS PostgreSQL.

    Returns dict of {section: {status, rows, error?}}.
    """
    dsn = resolve_pos_dsn()
    if not dsn:
        logger.warning("POS_PG_DSN not set — skipping sync")
        return {"error": "POS_PG_DSN not configured"}

    results: dict[str, Any] = {}
    sections_to_run = sections or _SECTIONS

    try:
        pg = _pg_connect(dsn)
    except Exception as e:
        logger.error("Cannot connect to POS PG: %s", e)
        return {"error": f"PG connection failed: {e}"}

    dispatch = {
        "stores": sync_stores,
        "staff": sync_staff,
        "daily_sales": sync_daily_sales,
        "staff_revenue": sync_staff_revenue,
        "order_list": sync_order_list,
        "customer_segments": sync_customer_segments,
        "customer_rfm": sync_customer_rfm,
        "product_performance": sync_product_performance,
        "payment_methods": sync_payment_methods,
        "customer_debt": sync_customer_debt,
        "debt_report": sync_debt_report,
        "monthly_returns": sync_monthly_returns,
    }

    for section in sections_to_run:
        fn = dispatch.get(section)
        if not fn:
            results[section] = {"status": "skipped", "error": "unknown section"}
            continue
        try:
            n = fn(conn, pg)
            results[section] = {"status": "ok", "rows": n}
        except Exception as e:
            logger.error("sync %s failed: %s", section, e, exc_info=True)
            results[section] = {"status": "error", "error": str(e)}
            _update_sync_state(conn, section, 0, status="error", error=str(e))

    pg.close()

    # Derived tables (computed from dashboard PG data)
    try:
        n = sync_monthly_revenue(conn)
        results["monthly_revenue"] = {"status": "ok", "rows": n}
    except Exception as e:
        results["monthly_revenue"] = {"status": "error", "error": str(e)}

    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _update_sync_state(
    conn,
    section: str,
    rows: int,
    status: str = "ok",
    error: str | None = None,
) -> None:
    with conn.cursor() as c:
        c.execute(
            """INSERT INTO sync_state (section, last_success_at, rows_synced, status, error)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (section) DO UPDATE SET
                last_success_at=EXCLUDED.last_success_at, rows_synced=EXCLUDED.rows_synced,
                status=EXCLUDED.status, error=EXCLUDED.error""",
            (section, _now_iso(), rows, status, error),
        )
    conn.commit()


def get_sync_status(conn) -> list[dict]:
    """Return current sync state for all sections."""
    with conn.cursor() as c:
        c.execute("SELECT section, last_success_at, rows_synced, status, error FROM sync_state")
        rows = c.fetchall()
    return [
        {
            "section": r[0],
            "last_success_at": r[1],
            "rows_synced": r[2],
            "status": r[3],
            "error": r[4],
        }
        for r in rows
    ]
