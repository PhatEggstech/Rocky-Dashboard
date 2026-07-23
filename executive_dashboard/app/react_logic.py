"""Business logic for React dashboard payloads.

Each function reads from the local PostgreSQL dashboard database and returns a dict
suitable for JSON serialisation by FastAPI.
"""

from __future__ import annotations

import os
from datetime import date


def _store_filter_clause(store_ids: list[str] | None) -> tuple[str, list]:
    """Return SQL WHERE clause fragment and params for store filtering."""
    if not store_ids:
        return "", []
    placeholders = ",".join("%s" for _ in store_ids)
    return f"AND store_id IN ({placeholders})", list(store_ids)


# ---------------------------------------------------------------------------
# Executive Summary
# ---------------------------------------------------------------------------


def executive_summary_payload(
    conn,
    start: str,
    end: str,
    store_ids: list[str] | None = None,
) -> dict:
    """Main executive summary: scorecards + charts."""
    sf, sp = _store_filter_clause(store_ids)

    # --- Scorecards ---
    row = conn.execute(
        f"""SELECT
                COALESCE(SUM(revenue), 0),
                COALESCE(SUM(orders_n), 0),
                COALESCE(SUM(unique_customers), 0),
                COALESCE(SUM(gross_profit), 0),
                COALESCE(SUM(revenue), 0),
                COALESCE(SUM(cogs), 0),
                COALESCE(SUM(CASE WHEN NOT is_hmk THEN revenue ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN is_hmk THEN revenue ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN is_hmk THEN subtotal ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN NOT is_hmk THEN orders_n ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN is_hmk THEN orders_n ELSE 0 END), 0)
            FROM daily_sales
            WHERE d BETWEEN %s AND %s {sf}""",
        [start, end] + sp,
    ).fetchone()

    revenue = row[0]
    orders = row[1]
    unique_customers = row[2]
    gross_profit = row[3]
    total_rev = row[4]
    total_cogs = row[5]
    retail_revenue = row[6]
    hmk_revenue = row[7]
    hmk_subtotal = row[8]       # Doanh số HMK chưa thu tiền (ghi nợ)
    retail_orders = row[9]
    hmk_orders = row[10]
    aov = revenue / orders if orders > 0 else 0
    # GPM = None when cost data is missing (cogs=0 means no cost prices entered)
    if total_cogs == 0 and total_rev > 0:
        gpm = None
    elif total_rev > 0:
        gpm = gross_profit / total_rev * 100
    else:
        gpm = 0

    # NPM% = (revenue - cogs - opex_proxy) / revenue * 100
    opex_pct = float(os.getenv("EDP_OPEX_PROXY_PCT", "0.12"))
    if total_rev > 0 and gpm is not None:
        opex = total_rev * opex_pct
        net_profit = gross_profit - opex
        npm = net_profit / total_rev * 100
    else:
        npm = None

    # Revenue growth vs previous period of same length
    from datetime import datetime, timedelta

    start_dt = datetime.strptime(start, "%Y-%m-%d").date()
    end_dt = datetime.strptime(end, "%Y-%m-%d").date()
    period_days = (end_dt - start_dt).days + 1
    prev_start = (start_dt - timedelta(days=period_days)).isoformat()
    prev_end = (start_dt - timedelta(days=1)).isoformat()

    prev_rev = conn.execute(
        f"SELECT COALESCE(SUM(revenue), 0) FROM daily_sales WHERE d BETWEEN %s AND %s {sf}",
        [prev_start, prev_end] + sp,
    ).fetchone()[0]

    if prev_rev > 0:
        revenue_growth = (revenue - prev_rev) / prev_rev * 100
        # Cap extreme growth values when previous period has very low volume
        revenue_growth = max(-100, min(revenue_growth, 999))
    else:
        revenue_growth = 0

    # Subtotal (doanh số)
    subtotal_row = conn.execute(
        f"SELECT COALESCE(SUM(subtotal), 0) FROM daily_sales WHERE d BETWEEN %s AND %s {sf}",
        [start, end] + sp,
    ).fetchone()
    subtotal = subtotal_row[0]

    scorecards = {
        "revenue": round(revenue, 0),
        "subtotal": round(subtotal, 0),
        "orders": orders,
        "aov": round(aov, 0),
        "gpm_pct": round(gpm, 2) if gpm is not None else None,
        "npm_pct": round(npm, 2) if npm is not None else None,
        "unique_customers": unique_customers,
        "revenue_growth_pct": round(revenue_growth, 2),
        "gross_profit": round(gross_profit, 0),
        # B2B / Retail breakdown
        "retail_revenue": round(retail_revenue, 0),
        "hmk_revenue": round(hmk_revenue, 0),
        "hmk_subtotal_chua_thu": round(hmk_subtotal, 0),
        "retail_orders": int(retail_orders),
        "hmk_orders": int(hmk_orders),
    }

    # --- Revenue trend (daily) ---
    trend_rows = conn.execute(
        f"""SELECT d, SUM(revenue), SUM(orders_n)
            FROM daily_sales
            WHERE d BETWEEN %s AND %s {sf}
            GROUP BY d ORDER BY d""",
        [start, end] + sp,
    ).fetchall()

    revenue_trend = [
        {"date": r[0], "revenue": round(r[1], 0), "orders": r[2]} for r in trend_rows
    ]

    # --- Top products ---
    top_products = conn.execute(
        f"""SELECT name, SUM(revenue) as rev, SUM(units_sold) as units
            FROM product_performance
            WHERE year_month >= LEFT(%s, 7) AND year_month <= LEFT(%s, 7)
            GROUP BY product_id, name
            ORDER BY rev DESC LIMIT 10""",
        [start, end],
    ).fetchall()

    top_products_list = [
        {"name": r[0], "revenue": round(r[1], 0), "units_sold": r[2]}
        for r in top_products
    ]

    # --- Customer segments ---
    seg_row = conn.execute(
        f"""SELECT
                COALESCE(SUM(new_customers_n), 0),
                COALESCE(SUM(returning_customers_n), 0)
            FROM daily_customer_segments
            WHERE d BETWEEN %s AND %s {sf}""",
        [start, end] + sp,
    ).fetchone()

    customer_segments = {
        "new_customers": seg_row[0],
        "returning_customers": seg_row[1],
    }

    # --- Stores count ---
    stores_count = conn.execute("SELECT COUNT(*) FROM stores").fetchone()[0]

    return {
        "ok": True,
        "scorecards": scorecards,
        "charts": {
            "revenue_trend": revenue_trend,
            "top_products": top_products_list,
            "customer_segments": customer_segments,
        },
        "metadata": {
            "period": {"start": start, "end": end},
            "stores_count": stores_count,
            "data_source": "postgresql",
        },
    }


# ---------------------------------------------------------------------------
# Sales & Marketing
# ---------------------------------------------------------------------------


def sales_marketing_payload(
    conn,
    start: str,
    end: str,
    store_ids: list[str] | None = None,
) -> dict:
    """Sales & marketing page payload."""
    sf, sp = _store_filter_clause(store_ids)

    # Daily revenue trend
    daily = conn.execute(
        f"""SELECT d, SUM(revenue), SUM(orders_n), SUM(unique_customers)
            FROM daily_sales
            WHERE d BETWEEN %s AND %s {sf}
            GROUP BY d ORDER BY d""",
        [start, end] + sp,
    ).fetchall()

    daily_trend = [
        {"date": r[0], "revenue": round(r[1], 0), "orders": r[2], "customers": r[3]}
        for r in daily
    ]

    # Payment method breakdown
    payments = conn.execute(
        f"""SELECT method_name, SUM(amount), SUM(count)
            FROM payment_methods
            WHERE d BETWEEN %s AND %s {sf}
            GROUP BY method_name
            ORDER BY SUM(amount) DESC""",
        [start, end] + sp,
    ).fetchall()

    payment_mix = [
        {"method": r[0], "amount": round(r[1], 0), "count": r[2]} for r in payments
    ]

    # Monthly revenue with growth
    monthly = conn.execute(
        f"""SELECT year_month, SUM(revenue), SUM(orders_n)
            FROM monthly_revenue
            WHERE year_month >= LEFT(%s, 7) AND year_month <= LEFT(%s, 7) {sf}
            GROUP BY year_month ORDER BY year_month""",
        [start, end] + sp,
    ).fetchall()

    monthly_trend = [
        {"month": r[0], "revenue": round(r[1], 0), "orders": r[2]} for r in monthly
    ]

    # Customer segments
    seg_row = conn.execute(
        f"""SELECT
                COALESCE(SUM(new_customers_n), 0),
                COALESCE(SUM(returning_customers_n), 0)
            FROM daily_customer_segments
            WHERE d BETWEEN %s AND %s {sf}""",
        [start, end] + sp,
    ).fetchone()

    return {
        "ok": True,
        "daily_trend": daily_trend,
        "payment_mix": payment_mix,
        "monthly_trend": monthly_trend,
        "customer_mix": {
            "new": seg_row[0],
            "returning": seg_row[1],
        },
    }


# ---------------------------------------------------------------------------
# Quality & CLV
# ---------------------------------------------------------------------------


def quality_payload(
    conn,
    start: str,
    end: str,
    store_ids: list[str] | None = None,
) -> dict:
    """Quality & CLV page: returns, RFM."""
    sf, sp = _store_filter_clause(store_ids)

    # Monthly returns
    returns = conn.execute(
        f"""SELECT year_month, SUM(return_count), SUM(return_amount), SUM(order_count)
            FROM monthly_returns
            WHERE year_month >= LEFT(%s, 7) AND year_month <= LEFT(%s, 7) {sf}
            GROUP BY year_month ORDER BY year_month""",
        [start, end] + sp,
    ).fetchall()

    returns_trend = []
    for r in returns:
        ym, ret_count, ret_amount, ord_count = r
        rate = (ret_count / ord_count * 100) if ord_count > 0 else 0
        returns_trend.append({
            "month": ym,
            "return_count": ret_count,
            "return_amount": round(ret_amount, 0),
            "order_count": ord_count,
            "return_rate_pct": round(rate, 2),
        })

    # RFM distribution
    rfm = conn.execute(
        "SELECT segment, COUNT(*), SUM(monetary) FROM customer_rfm GROUP BY segment"
    ).fetchall()

    rfm_segments = [
        {"segment": r[0], "count": r[1], "total_monetary": round(r[2], 0)}
        for r in rfm
    ]

    # Top customers by monetary
    top_customers = conn.execute(
        "SELECT name, monetary, frequency, recency_days, segment FROM customer_rfm ORDER BY monetary DESC LIMIT 10"
    ).fetchall()

    top_list = [
        {
            "name": r[0],
            "monetary": round(r[1], 0),
            "frequency": r[2],
            "recency_days": r[3],
            "segment": r[4],
        }
        for r in top_customers
    ]

    return {
        "ok": True,
        "returns_trend": returns_trend,
        "rfm_segments": rfm_segments,
        "top_customers": top_list,
    }


# ---------------------------------------------------------------------------
# B2B Analytics
# ---------------------------------------------------------------------------


def b2b_payload(
    conn,
    start: str,
    end: str,
    store_ids: list[str] | None = None,
) -> dict:
    """B2B analytics: debt report + customer overview."""

    # Try debt_report first (new approach from DebtReport table)
    debt_list = []
    try:
        debtors = conn.execute(
            """SELECT customer_id, customer_name, previous_balance, debt_amount,
                      total_receive_amount, paid_amount, current_balance, recover_debt_rate,
                      start_at, end_at
               FROM debt_report
               WHERE start_at >= %s AND end_at <= %s
                 AND (previous_balance != 0 OR debt_amount != 0 OR current_balance != 0)
               ORDER BY current_balance ASC
               LIMIT 50""",
            [start, end],
        ).fetchall()

        for r in debtors:
            debt_list.append({
                "customer_id": r[0],
                "name": r[1],
                "previous_balance": round(r[2], 0),
                "debt_amount": round(r[3], 0),
                "total_receive_amount": round(r[4], 0),
                "paid_amount": round(r[5], 0),
                "current_balance": round(r[6], 0),
                "recover_debt_rate": round(r[7], 2),
                "start_at": r[8],
                "end_at": r[9],
            })
    except Exception:
        pass

    # Summary from debt_report
    summary_row = conn.execute(
        """SELECT
            COUNT(DISTINCT customer_id),
            COALESCE(SUM(current_balance), 0),
            COALESCE(SUM(total_receive_amount), 0),
            COALESCE(SUM(debt_amount), 0)
        FROM debt_report
        WHERE start_at >= %s AND end_at <= %s""",
        [start, end],
    ).fetchone()

    # Fallback: legacy customer_debt table
    legacy_debtors = conn.execute(
        "SELECT customer_id, name, debt_amount, need_pay, total_orders, last_transaction_at, left_amount, payment_state "
        "FROM customer_debt WHERE debt_amount > 0 ORDER BY debt_amount DESC LIMIT 20"
    ).fetchall()

    legacy_debt_list = [
        {
            "customer_id": r[0],
            "name": r[1],
            "debt_amount": round(r[2], 0),
            "need_pay": round(r[3], 0),
            "total_orders": r[4],
            "last_transaction_at": r[5],
            "left_amount": round(r[6], 0) if r[6] else 0,
            "payment_state": r[7] if r[7] else 0,
        }
        for r in legacy_debtors
    ]

    # Top customers by order value (legacy)
    top_b2b = conn.execute(
        "SELECT customer_id, name, need_pay, total_orders, last_transaction_at "
        "FROM customer_debt ORDER BY need_pay DESC LIMIT 10"
    ).fetchall()

    top_b2b_list = [
        {
            "customer_id": r[0],
            "name": r[1],
            "total_revenue": round(r[2], 0),
            "total_orders": r[3],
            "last_transaction_at": r[4],
        }
        for r in top_b2b
    ]

    return {
        "ok": True,
        "debt_report": debt_list,
        "debt_summary": {
            "total_customers_with_debt": summary_row[0] if summary_row else 0,
            "total_current_balance": round(summary_row[1], 0) if summary_row else 0,
            "total_receive_amount": round(summary_row[2], 0) if summary_row else 0,
            "total_debt_amount": round(summary_row[3], 0) if summary_row else 0,
            # Frontend B2BAnalytics.tsx compatibility keys
            "total_debt": round(summary_row[3], 0) if summary_row else 0,
            "total_left_amount": round(summary_row[1], 0) if summary_row else 0,
            "total_revenue": round(summary_row[2], 0) if summary_row else 0,
            "total_orders": 0,
        },
        "top_debtors": legacy_debt_list,
        "top_customers": top_b2b_list,
    }


# ---------------------------------------------------------------------------
# Store Leaderboard
# ---------------------------------------------------------------------------


def store_leaderboard_payload(
    conn,
    start: str,
    end: str,
    store_ids: list[str] | None = None,
) -> dict:
    """Store ranking by revenue, orders, growth."""
    sf, sp = _store_filter_clause(store_ids)

    stores = conn.execute(
        f"""SELECT
                s.id, s.name, s.code, s.staff_count,
                COALESCE(SUM(ds.revenue), 0) AS revenue,
                COALESCE(SUM(ds.orders_n), 0) AS orders_n,
                COALESCE(SUM(ds.gross_profit), 0) AS gross_profit,
                COALESCE(SUM(ds.unique_customers), 0) AS customers
            FROM stores s
            LEFT JOIN daily_sales ds ON ds.store_id = s.id
                AND ds.d BETWEEN %s AND %s
            WHERE 1=1 {sf.replace('store_id', 's.id') if sf else ''}
            GROUP BY s.id, s.name, s.code, s.staff_count
            ORDER BY revenue DESC""",
        [start, end] + sp,
    ).fetchall()

    # Compute previous period for growth
    from datetime import datetime, timedelta
    start_dt = datetime.strptime(start, "%Y-%m-%d").date()
    end_dt = datetime.strptime(end, "%Y-%m-%d").date()
    period_days = (end_dt - start_dt).days + 1
    prev_start = (start_dt - timedelta(days=period_days)).isoformat()
    prev_end = (start_dt - timedelta(days=1)).isoformat()

    prev_revenues = {}
    prev_rows = conn.execute(
        f"""SELECT store_id, COALESCE(SUM(revenue), 0)
            FROM daily_sales
            WHERE d BETWEEN %s AND %s {sf}
            GROUP BY store_id""",
        [prev_start, prev_end] + sp,
    ).fetchall()
    for r in prev_rows:
        prev_revenues[r[0]] = r[1]

    leaderboard = []
    for rank, s in enumerate(stores, 1):
        store_id, name, code, staff_count, revenue, orders, gp, customers = s
        prev_rev = prev_revenues.get(store_id, 0)
        growth = ((revenue - prev_rev) / prev_rev * 100) if prev_rev > 0 else 0
        rev_per_staff = revenue / staff_count if staff_count and staff_count > 0 else 0

        leaderboard.append({
            "rank": rank,
            "store_id": store_id,
            "name": name,
            "code": code,
            "revenue": round(revenue, 0),
            "orders": orders,
            "gross_profit": round(gp, 0),
            "customers": customers,
            "growth_pct": round(growth, 2),
            "revenue_per_staff": round(rev_per_staff, 0),
            "staff_count": staff_count or 0,
        })

    return {
        "ok": True,
        "leaderboard": leaderboard,
        "metadata": {"period": {"start": start, "end": end}},
    }


# ---------------------------------------------------------------------------
# CSAT by Store (placeholder — actual data from ZNS PostgreSQL)
# ---------------------------------------------------------------------------


def csat_by_store_payload(
    conn,
    start: str,
    end: str,
    store_ids: list[str] | None = None,
) -> dict:
    """CSAT scores by store. Returns store-level satisfaction metrics."""
    sf, sp = _store_filter_clause(store_ids)

    # Proxy CSAT from return rates (lower returns = higher satisfaction)
    stores = conn.execute(
        f"""SELECT
                s.id, s.name, s.code,
                COALESCE(SUM(mr.return_count), 0) AS returns,
                COALESCE(SUM(mr.order_count), 0) AS orders
            FROM stores s
            LEFT JOIN monthly_returns mr ON mr.store_id = s.id
                AND mr.year_month >= LEFT(%s, 7)
                AND mr.year_month <= LEFT(%s, 7)
            WHERE 1=1 {sf.replace('store_id', 's.id') if sf else ''}
            GROUP BY s.id, s.name, s.code
            ORDER BY s.name""",
        [start, end] + sp,
    ).fetchall()

    csat_list = []
    for s in stores:
        store_id, name, code, returns, orders = s
        # Proxy: CSAT = 100 - (return_rate * 10), capped at 50-100
        return_rate = (returns / orders * 100) if orders > 0 else 0
        csat_score = max(50, min(100, 100 - return_rate * 10))
        csat_list.append({
            "store_id": store_id,
            "name": name,
            "code": code,
            "csat_score": round(csat_score, 1),
            "return_rate_pct": round(return_rate, 2),
            "total_orders": orders,
            "total_returns": returns,
            "data_source": "proxy_from_returns",
        })

    return {
        "ok": True,
        "stores": csat_list,
        "note": "CSAT proxy from return rates. Connect ZNS_PG_DSN for real survey data.",
    }


# ---------------------------------------------------------------------------
# Inventory & Supply Chain
# ---------------------------------------------------------------------------


def inventory_payload(
    conn,
    start: str,
    end: str,
    store_ids: list[str] | None = None,
) -> dict:
    """Inventory analytics derived from product_performance table."""
    start_ym = start[:7]
    end_ym = end[:7]

    totals = conn.execute(
        """SELECT COUNT(DISTINCT product_id), COALESCE(SUM(revenue), 0),
                  COALESCE(SUM(units_sold), 0), COALESCE(AVG(avg_price), 0)
           FROM product_performance
           WHERE year_month >= %s AND year_month <= %s""",
        [start_ym, end_ym],
    ).fetchone()

    total_skus = totals[0] or 0
    total_revenue = totals[1] or 0
    total_units = totals[2] or 0
    avg_price = totals[3] or 0

    categories = conn.execute(
        """SELECT category, SUM(revenue) as rev, SUM(units_sold) as units
           FROM product_performance
           WHERE year_month >= %s AND year_month <= %s
           GROUP BY category ORDER BY rev DESC""",
        [start_ym, end_ym],
    ).fetchall()

    category_mix = [
        {"category": r[0], "revenue": round(r[1] or 0, 0), "units_sold": r[2] or 0}
        for r in categories
    ]

    top_products = conn.execute(
        """SELECT name, category, SUM(revenue) as rev, SUM(units_sold) as units, AVG(avg_price) as price
           FROM product_performance
           WHERE year_month >= %s AND year_month <= %s
           GROUP BY product_id, name, category ORDER BY rev DESC LIMIT 10""",
        [start_ym, end_ym],
    ).fetchall()

    top_list = [
        {"name": r[0], "category": r[1], "revenue": round(r[2] or 0, 0), "units_sold": r[3] or 0, "avg_price": round(r[4] or 0, 0)}
        for r in top_products
    ]

    bottom_products = conn.execute(
        """SELECT name, category, SUM(revenue) as rev, SUM(units_sold) as units, AVG(avg_price) as price
           FROM product_performance
           WHERE year_month >= %s AND year_month <= %s
           GROUP BY product_id, name, category HAVING SUM(units_sold) > 0 ORDER BY units ASC LIMIT 10""",
        [start_ym, end_ym],
    ).fetchall()

    bottom_list = [
        {"name": r[0], "category": r[1], "revenue": round(r[2] or 0, 0), "units_sold": r[3] or 0, "avg_price": round(r[4] or 0, 0)}
        for r in bottom_products
    ]

    monthly = conn.execute(
        """SELECT year_month, category, SUM(revenue) as rev
           FROM product_performance
           WHERE year_month >= %s AND year_month <= %s
           GROUP BY year_month, category ORDER BY year_month, category""",
        [start_ym, end_ym],
    ).fetchall()

    monthly_trend = [
        {"month": r[0], "category": r[1], "revenue": round(r[2] or 0, 0)}
        for r in monthly
    ]

    top_category = category_mix[0]["category"] if category_mix else "N/A"

    # WMS inventory scorecards (if inventory_wms has data)
    wms_scorecards = _get_wms_scorecards(conn, store_ids)

    result = {
        "ok": True,
        "scorecards": {
            "total_skus": total_skus,
            "total_revenue": round(total_revenue, 0),
            "total_units": total_units,
            "avg_price": round(avg_price, 0),
            "top_category": top_category,
        },
        "category_mix": category_mix,
        "top_products": top_list,
        "bottom_products": bottom_list,
        "monthly_trend": monthly_trend,
    }

    if wms_scorecards:
        result["wms_scorecards"] = wms_scorecards

    return result


def _get_wms_scorecards(
    conn, store_ids: list[str] | None = None
) -> dict | None:
    """Return WMS-sourced inventory scorecards if data exists."""
    sf, sp = _store_filter_clause(store_ids)

    # Check if inventory_wms table has data
    try:
        count = conn.execute("SELECT COUNT(*) FROM inventory_wms").fetchone()[0]
    except Exception:
        return None

    if count == 0:
        return None

    where_clause = "WHERE 1=1 " + sf if sf else ""

    totals = conn.execute(
        f"""SELECT
                COALESCE(SUM(inventory_value), 0),
                COALESCE(AVG(CASE WHEN on_hand > 0 THEN stock_cover_days END), 0),
                COUNT(CASE WHEN is_dead_stock = 1 THEN 1 END),
                COUNT(*),
                COUNT(CASE WHEN on_hand <= 0 THEN 1 END)
            FROM inventory_wms
            {where_clause}""",
        sp,
    ).fetchone()

    total_inventory_value = totals[0] or 0
    stock_cover_days_avg = totals[1] or 0
    dead_stock_count = totals[2] or 0
    total_products = totals[3] or 1
    oos_count = totals[4] or 0

    dead_stock_pct = min(dead_stock_count / total_products * 100, 100.0)
    oos_pct = min(oos_count / total_products * 100, 100.0)

    return {
        "total_inventory_value": round(total_inventory_value, 0),
        "stock_cover_days_avg": round(stock_cover_days_avg, 1),
        "dead_stock_pct": round(dead_stock_pct, 1),
        "oos_pct": round(oos_pct, 1),
    }


# ---------------------------------------------------------------------------
# Drill-down handlers
# ---------------------------------------------------------------------------


def _drill_revenue_by_store(conn, start, end, sf, sp, clicked_value=None):
    rows = conn.execute(
        f"""SELECT s.name, SUM(ds.revenue), SUM(ds.orders_n),
                   SUM(ds.gross_profit), SUM(ds.unique_customers)
            FROM stores s
            LEFT JOIN daily_sales ds ON ds.store_id = s.id AND ds.d BETWEEN %s AND %s
            WHERE 1=1 {sf.replace('store_id', 's.id') if sf else ''}
            GROUP BY s.id, s.name ORDER BY SUM(ds.revenue) DESC""",
        [start, end] + sp,
    ).fetchall()
    total = sum(r[1] or 0 for r in rows)
    return {
        "columns": [
            {"key": "name", "label": "Cửa hàng", "type": "text"},
            {"key": "revenue", "label": "Doanh thu", "type": "currency"},
            {"key": "orders", "label": "Đơn hàng", "type": "number"},
            {"key": "gross_profit", "label": "Lợi nhuận gộp", "type": "currency"},
            {"key": "customers", "label": "Khách hàng", "type": "number"},
            {"key": "share_pct", "label": "Tỷ trọng", "type": "percent"},
        ],
        "rows": [
            {
                "name": r[0],
                "revenue": round(r[1] or 0, 0),
                "orders": r[2] or 0,
                "gross_profit": round(r[3] or 0, 0),
                "customers": r[4] or 0,
                "share_pct": round((r[1] or 0) / total * 100, 1) if total > 0 else 0,
            }
            for r in rows
        ],
        "summary": {"total_revenue": round(total, 0), "stores_count": len(rows)},
    }


def _drill_revenue_by_day(conn, start, end, sf, sp, clicked_value=None):
    rows = conn.execute(
        f"""SELECT d, SUM(revenue), SUM(orders_n), SUM(gross_profit), SUM(unique_customers)
            FROM daily_sales WHERE d BETWEEN %s AND %s {sf}
            GROUP BY d ORDER BY d""",
        [start, end] + sp,
    ).fetchall()
    return {
        "columns": [
            {"key": "date", "label": "Ngày", "type": "text"},
            {"key": "revenue", "label": "Doanh thu", "type": "currency"},
            {"key": "orders", "label": "Đơn hàng", "type": "number"},
            {"key": "gross_profit", "label": "Lợi nhuận gộp", "type": "currency"},
            {"key": "customers", "label": "Khách hàng", "type": "number"},
        ],
        "rows": [
            {
                "date": r[0],
                "revenue": round(r[1] or 0, 0),
                "orders": r[2] or 0,
                "gross_profit": round(r[3] or 0, 0),
                "customers": r[4] or 0,
            }
            for r in rows
        ],
        "summary": {"total_days": len(rows)},
    }


def _drill_orders_by_store(conn, start, end, sf, sp, clicked_value=None):
    rows = conn.execute(
        f"""SELECT s.name, SUM(ds.orders_n), SUM(ds.revenue), SUM(ds.units_sold)
            FROM stores s
            LEFT JOIN daily_sales ds ON ds.store_id = s.id AND ds.d BETWEEN %s AND %s
            WHERE 1=1 {sf.replace('store_id', 's.id') if sf else ''}
            GROUP BY s.id, s.name ORDER BY SUM(ds.orders_n) DESC""",
        [start, end] + sp,
    ).fetchall()
    total = sum(r[1] or 0 for r in rows)
    return {
        "columns": [
            {"key": "name", "label": "Cửa hàng", "type": "text"},
            {"key": "orders", "label": "Đơn hàng", "type": "number"},
            {"key": "revenue", "label": "Doanh thu", "type": "currency"},
            {"key": "units_sold", "label": "SP bán ra", "type": "number"},
            {"key": "share_pct", "label": "Tỷ trọng", "type": "percent"},
        ],
        "rows": [
            {
                "name": r[0],
                "orders": r[1] or 0,
                "revenue": round(r[2] or 0, 0),
                "units_sold": r[3] or 0,
                "share_pct": round((r[1] or 0) / total * 100, 1) if total > 0 else 0,
            }
            for r in rows
        ],
        "summary": {"total_orders": total, "stores_count": len(rows)},
    }


def _drill_aov_by_store(conn, start, end, sf, sp, clicked_value=None):
    rows = conn.execute(
        f"""SELECT s.name, SUM(ds.revenue), SUM(ds.orders_n)
            FROM stores s
            LEFT JOIN daily_sales ds ON ds.store_id = s.id AND ds.d BETWEEN %s AND %s
            WHERE 1=1 {sf.replace('store_id', 's.id') if sf else ''}
            GROUP BY s.id, s.name ORDER BY SUM(ds.revenue) / GREATEST(1, SUM(ds.orders_n)) DESC""",
        [start, end] + sp,
    ).fetchall()
    return {
        "columns": [
            {"key": "name", "label": "Cửa hàng", "type": "text"},
            {"key": "aov", "label": "AOV", "type": "currency"},
            {"key": "revenue", "label": "Doanh thu", "type": "currency"},
            {"key": "orders", "label": "Đơn hàng", "type": "number"},
        ],
        "rows": [
            {
                "name": r[0],
                "aov": round(r[1] / r[2], 0) if r[2] and r[2] > 0 else 0,
                "revenue": round(r[1] or 0, 0),
                "orders": r[2] or 0,
            }
            for r in rows
        ],
        "summary": {"stores_count": len(rows)},
    }


def _drill_gpm_by_store(conn, start, end, sf, sp, clicked_value=None):
    rows = conn.execute(
        f"""SELECT s.name, SUM(ds.gross_profit), SUM(ds.revenue)
            FROM stores s
            LEFT JOIN daily_sales ds ON ds.store_id = s.id AND ds.d BETWEEN %s AND %s
            WHERE 1=1 {sf.replace('store_id', 's.id') if sf else ''}
            GROUP BY s.id, s.name ORDER BY SUM(ds.gross_profit) DESC""",
        [start, end] + sp,
    ).fetchall()
    return {
        "columns": [
            {"key": "name", "label": "Cửa hàng", "type": "text"},
            {"key": "gpm_pct", "label": "Biên LN gộp %", "type": "percent"},
            {"key": "gross_profit", "label": "Lợi nhuận gộp", "type": "currency"},
            {"key": "revenue", "label": "Doanh thu", "type": "currency"},
        ],
        "rows": [
            {
                "name": r[0],
                "gpm_pct": round(r[1] / r[2] * 100, 1) if r[2] and r[2] > 0 else 0,
                "gross_profit": round(r[1] or 0, 0),
                "revenue": round(r[2] or 0, 0),
            }
            for r in rows
        ],
        "summary": {"stores_count": len(rows)},
    }


def _drill_customers_by_store(conn, start, end, sf, sp, clicked_value=None):
    rows = conn.execute(
        f"""SELECT s.name, SUM(ds.unique_customers),
                   SUM(cs.new_customers_n), SUM(cs.returning_customers_n)
            FROM stores s
            LEFT JOIN daily_sales ds ON ds.store_id = s.id AND ds.d BETWEEN %s AND %s
            LEFT JOIN daily_customer_segments cs ON cs.store_id = s.id AND cs.d BETWEEN %s AND %s
            WHERE 1=1 {sf.replace('store_id', 's.id') if sf else ''}
            GROUP BY s.id, s.name ORDER BY SUM(ds.unique_customers) DESC""",
        [start, end, start, end] + sp,
    ).fetchall()
    return {
        "columns": [
            {"key": "name", "label": "Cửa hàng", "type": "text"},
            {"key": "customers", "label": "Khách hàng", "type": "number"},
            {"key": "new_customers", "label": "Khách mới", "type": "number"},
            {"key": "returning", "label": "Khách quay lại", "type": "number"},
        ],
        "rows": [
            {
                "name": r[0],
                "customers": r[1] or 0,
                "new_customers": r[2] or 0,
                "returning": r[3] or 0,
            }
            for r in rows
        ],
        "summary": {"stores_count": len(rows)},
    }


def _drill_revenue_trend_point(conn, start, end, sf, sp, clicked_value=None):
    """Clicked a specific date on revenue trend → show per-store for that day."""
    target_date = clicked_value or start
    rows = conn.execute(
        f"""SELECT s.name, ds.revenue, ds.orders_n, ds.gross_profit, ds.unique_customers
            FROM stores s
            LEFT JOIN daily_sales ds ON ds.store_id = s.id AND ds.d = %s
            WHERE 1=1 {sf.replace('store_id', 's.id') if sf else ''}
            ORDER BY ds.revenue DESC""",
        [target_date] + sp,
    ).fetchall()
    total = sum(r[1] or 0 for r in rows)
    return {
        "columns": [
            {"key": "name", "label": "Cửa hàng", "type": "text"},
            {"key": "revenue", "label": "Doanh thu", "type": "currency"},
            {"key": "orders", "label": "Đơn hàng", "type": "number"},
            {"key": "gross_profit", "label": "Lợi nhuận gộp", "type": "currency"},
            {"key": "customers", "label": "Khách hàng", "type": "number"},
        ],
        "rows": [
            {
                "name": r[0],
                "revenue": round(r[1] or 0, 0),
                "orders": r[2] or 0,
                "gross_profit": round(r[3] or 0, 0),
                "customers": r[4] or 0,
            }
            for r in rows
        ],
        "summary": {"date": target_date, "total_revenue": round(total, 0)},
    }


def _drill_top_product(conn, start, end, sf, sp, clicked_value=None):
    """Clicked a product → show monthly breakdown."""
    product_name = clicked_value or ""
    rows = conn.execute(
        """SELECT year_month, revenue, units_sold, avg_price
           FROM product_performance
           WHERE name = %s AND year_month >= LEFT(%s, 7) AND year_month <= LEFT(%s, 7)
           ORDER BY year_month""",
        [product_name, start, end],
    ).fetchall()
    return {
        "columns": [
            {"key": "month", "label": "Tháng", "type": "text"},
            {"key": "revenue", "label": "Doanh thu", "type": "currency"},
            {"key": "units_sold", "label": "SL bán", "type": "number"},
            {"key": "avg_price", "label": "Giá TB", "type": "currency"},
        ],
        "rows": [
            {
                "month": r[0],
                "revenue": round(r[1] or 0, 0),
                "units_sold": r[2] or 0,
                "avg_price": round(r[3] or 0, 0),
            }
            for r in rows
        ],
        "summary": {"product_name": product_name, "months": len(rows)},
    }


def _drill_customer_segment(conn, start, end, sf, sp, clicked_value=None):
    """Clicked a customer segment → per-store breakdown."""
    segment = clicked_value or "new"
    col = "new_customers_n" if "mới" in segment.lower() or segment == "new" else "returning_customers_n"
    rows = conn.execute(
        f"""SELECT s.name, SUM(cs.{col})
            FROM stores s
            LEFT JOIN daily_customer_segments cs ON cs.store_id = s.id AND cs.d BETWEEN %s AND %s
            WHERE 1=1 {sf.replace('store_id', 's.id') if sf else ''}
            GROUP BY s.id, s.name ORDER BY SUM(cs.{col}) DESC""",
        [start, end] + sp,
    ).fetchall()
    total = sum(r[1] or 0 for r in rows)
    return {
        "columns": [
            {"key": "name", "label": "Cửa hàng", "type": "text"},
            {"key": "count", "label": "Số lượng", "type": "number"},
            {"key": "share_pct", "label": "Tỷ trọng", "type": "percent"},
        ],
        "rows": [
            {
                "name": r[0],
                "count": r[1] or 0,
                "share_pct": round((r[1] or 0) / total * 100, 1) if total > 0 else 0,
            }
            for r in rows
        ],
        "summary": {"segment": segment, "total": total},
    }


def _drill_payment_method(conn, start, end, sf, sp, clicked_value=None):
    """Clicked a payment method → per-store breakdown."""
    method = clicked_value or ""
    rows = conn.execute(
        f"""SELECT s.name, SUM(pm.amount), SUM(pm.count)
            FROM stores s
            LEFT JOIN payment_methods pm ON pm.store_id = s.id
                AND pm.d BETWEEN %s AND %s AND pm.method_name = %s
            WHERE 1=1 {sf.replace('store_id', 's.id') if sf else ''}
            GROUP BY s.id, s.name ORDER BY SUM(pm.amount) DESC""",
        [start, end, method] + sp,
    ).fetchall()
    total = sum(r[1] or 0 for r in rows)
    return {
        "columns": [
            {"key": "name", "label": "Cửa hàng", "type": "text"},
            {"key": "amount", "label": "Giá trị", "type": "currency"},
            {"key": "count", "label": "Giao dịch", "type": "number"},
            {"key": "share_pct", "label": "Tỷ trọng", "type": "percent"},
        ],
        "rows": [
            {
                "name": r[0],
                "amount": round(r[1] or 0, 0),
                "count": r[2] or 0,
                "share_pct": round((r[1] or 0) / total * 100, 1) if total > 0 else 0,
            }
            for r in rows
        ],
        "summary": {"method": method, "total_amount": round(total, 0)},
    }


def _drill_monthly_revenue(conn, start, end, sf, sp, clicked_value=None):
    """Clicked a month bar → per-store breakdown for that month."""
    month = clicked_value or ""
    rows = conn.execute(
        f"""SELECT s.name, SUM(mr.revenue), SUM(mr.orders_n)
            FROM stores s
            LEFT JOIN monthly_revenue mr ON mr.store_id = s.id AND mr.year_month = %s
            WHERE 1=1 {sf.replace('store_id', 's.id') if sf else ''}
            GROUP BY s.id, s.name ORDER BY SUM(mr.revenue) DESC""",
        [month] + sp,
    ).fetchall()
    total = sum(r[1] or 0 for r in rows)
    return {
        "columns": [
            {"key": "name", "label": "Cửa hàng", "type": "text"},
            {"key": "revenue", "label": "Doanh thu", "type": "currency"},
            {"key": "orders", "label": "Đơn hàng", "type": "number"},
            {"key": "share_pct", "label": "Tỷ trọng", "type": "percent"},
        ],
        "rows": [
            {
                "name": r[0],
                "revenue": round(r[1] or 0, 0),
                "orders": r[2] or 0,
                "share_pct": round((r[1] or 0) / total * 100, 1) if total > 0 else 0,
            }
            for r in rows
        ],
        "summary": {"month": month, "total_revenue": round(total, 0)},
    }


def _drill_return_rate(conn, start, end, sf, sp, clicked_value=None):
    """Clicked return rate → per-store breakdown."""
    rows = conn.execute(
        f"""SELECT s.name, SUM(mr.return_count), SUM(mr.return_amount), SUM(mr.order_count)
            FROM stores s
            LEFT JOIN monthly_returns mr ON mr.store_id = s.id
                AND mr.year_month >= LEFT(%s, 7) AND mr.year_month <= LEFT(%s, 7)
            WHERE 1=1 {sf.replace('store_id', 's.id') if sf else ''}
            GROUP BY s.id, s.name ORDER BY SUM(mr.return_count) DESC""",
        [start, end] + sp,
    ).fetchall()
    return {
        "columns": [
            {"key": "name", "label": "Cửa hàng", "type": "text"},
            {"key": "return_count", "label": "Đơn trả", "type": "number"},
            {"key": "return_rate_pct", "label": "Tỷ lệ trả %", "type": "percent"},
            {"key": "return_amount", "label": "Giá trị trả", "type": "currency"},
            {"key": "order_count", "label": "Tổng đơn", "type": "number"},
        ],
        "rows": [
            {
                "name": r[0],
                "return_count": r[1] or 0,
                "return_rate_pct": round((r[1] or 0) / r[3] * 100, 2) if r[3] and r[3] > 0 else 0,
                "return_amount": round(r[2] or 0, 0),
                "order_count": r[3] or 0,
            }
            for r in rows
        ],
        "summary": {"stores_count": len(rows)},
    }


def _drill_rfm_segment(conn, start, end, sf, sp, clicked_value=None):
    """Clicked RFM segment → customer list in that segment."""
    segment = clicked_value or ""
    rows = conn.execute(
        "SELECT name, monetary, frequency, recency_days, segment FROM customer_rfm WHERE segment = %s ORDER BY monetary DESC LIMIT 50",
        [segment],
    ).fetchall()
    return {
        "columns": [
            {"key": "name", "label": "Khách hàng", "type": "text"},
            {"key": "monetary", "label": "Giá trị mua", "type": "currency"},
            {"key": "frequency", "label": "Số đơn", "type": "number"},
            {"key": "recency_days", "label": "Ngày gần nhất", "type": "number"},
        ],
        "rows": [
            {
                "name": r[0] or "N/A",
                "monetary": round(r[1] or 0, 0),
                "frequency": r[2] or 0,
                "recency_days": r[3] or 0,
            }
            for r in rows
        ],
        "summary": {"segment": segment, "total_customers": len(rows)},
    }


def _drill_leaderboard_store(conn, start, end, sf, sp, clicked_value=None):
    """Clicked a store in leaderboard → daily breakdown."""
    store_name = clicked_value or ""
    rows = conn.execute(
        """SELECT ds.d, ds.revenue, ds.orders_n, ds.gross_profit, ds.unique_customers
           FROM daily_sales ds
           JOIN stores s ON s.id = ds.store_id
           WHERE s.name = %s AND ds.d BETWEEN %s AND %s
           ORDER BY ds.d""",
        [store_name, start, end],
    ).fetchall()
    return {
        "columns": [
            {"key": "date", "label": "Ngày", "type": "text"},
            {"key": "revenue", "label": "Doanh thu", "type": "currency"},
            {"key": "orders", "label": "Đơn hàng", "type": "number"},
            {"key": "gross_profit", "label": "Lợi nhuận gộp", "type": "currency"},
            {"key": "customers", "label": "Khách hàng", "type": "number"},
        ],
        "rows": [
            {
                "date": r[0],
                "revenue": round(r[1] or 0, 0),
                "orders": r[2] or 0,
                "gross_profit": round(r[3] or 0, 0),
                "customers": r[4] or 0,
            }
            for r in rows
        ],
        "summary": {"store": store_name, "days": len(rows)},
    }


def _drill_csat_store(conn, start, end, sf, sp, clicked_value=None):
    """Clicked a store in CSAT → monthly return rate trend."""
    store_name = clicked_value or ""
    rows = conn.execute(
        """SELECT mr.year_month, mr.return_count, mr.order_count, mr.return_amount
           FROM monthly_returns mr
           JOIN stores s ON s.id = mr.store_id
           WHERE s.name = %s AND mr.year_month >= LEFT(%s, 7) AND mr.year_month <= LEFT(%s, 7)
           ORDER BY mr.year_month""",
        [store_name, start, end],
    ).fetchall()
    return {
        "columns": [
            {"key": "month", "label": "Tháng", "type": "text"},
            {"key": "return_rate_pct", "label": "Tỷ lệ trả %", "type": "percent"},
            {"key": "return_count", "label": "Đơn trả", "type": "number"},
            {"key": "order_count", "label": "Tổng đơn", "type": "number"},
            {"key": "csat_proxy", "label": "CSAT (proxy)", "type": "number"},
        ],
        "rows": [
            {
                "month": r[0],
                "return_rate_pct": round(r[1] / r[2] * 100, 2) if r[2] and r[2] > 0 else 0,
                "return_count": r[1] or 0,
                "order_count": r[2] or 0,
                "csat_proxy": round(max(50, min(100, 100 - (r[1] / r[2] * 100 * 10 if r[2] else 0))), 1),
            }
            for r in rows
        ],
        "summary": {"store": store_name, "months": len(rows)},
    }


def _drill_revenue_per_staff_store(conn, start, end, sf, sp, clicked_value=None):
    """Clicked a store in rev/staff → daily rev/staff trend."""
    store_name = clicked_value or ""
    rows = conn.execute(
        """SELECT ds.d, ds.revenue, ds.orders_n, s.staff_count
           FROM daily_sales ds
           JOIN stores s ON s.id = ds.store_id
           WHERE s.name = %s AND ds.d BETWEEN %s AND %s
           ORDER BY ds.d""",
        [store_name, start, end],
    ).fetchall()
    return {
        "columns": [
            {"key": "date", "label": "Ngày", "type": "text"},
            {"key": "revenue", "label": "Doanh thu", "type": "currency"},
            {"key": "revenue_per_staff", "label": "DT/Nhân viên", "type": "currency"},
            {"key": "orders", "label": "Đơn hàng", "type": "number"},
        ],
        "rows": [
            {
                "date": r[0],
                "revenue": round(r[1] or 0, 0),
                "revenue_per_staff": round((r[1] or 0) / r[3], 0) if r[3] and r[3] > 0 else 0,
                "orders": r[2] or 0,
            }
            for r in rows
        ],
        "summary": {"store": store_name, "days": len(rows)},
    }


def _drill_inventory_category(conn, start, end, sf, sp, clicked_value=None):
    """Clicked a category -> products in that category."""
    category = clicked_value or ""
    start_ym = start[:7]
    end_ym = end[:7]
    rows = conn.execute(
        """SELECT name, SUM(revenue), SUM(units_sold), AVG(avg_price)
           FROM product_performance
           WHERE category = %s AND year_month >= %s AND year_month <= %s
           GROUP BY product_id, name ORDER BY SUM(revenue) DESC""",
        [category, start_ym, end_ym],
    ).fetchall()
    return {
        "columns": [
            {"key": "name", "label": "Sản phẩm", "type": "text"},
            {"key": "revenue", "label": "Doanh thu", "type": "currency"},
            {"key": "units_sold", "label": "SL bán", "type": "number"},
            {"key": "avg_price", "label": "Giá TB", "type": "currency"},
        ],
        "rows": [
            {"name": r[0], "revenue": round(r[1] or 0, 0), "units_sold": r[2] or 0, "avg_price": round(r[3] or 0, 0)}
            for r in rows
        ],
        "summary": {"category": category, "products": len(rows)},
    }


def _drill_inventory_product(conn, start, end, sf, sp, clicked_value=None):
    """Drill-down to list of orders where a product was sold over time (from POS database directly)."""
    import psycopg
    from .pos_sync import resolve_pos_dsn
    
    pos_dsn = resolve_pos_dsn()
    if not pos_dsn:
        return {
            "columns": [],
            "rows": [],
            "summary": {"Error": "POS database DSN not configured."}
        }
        
    rows = []
    product_name = clicked_value or ""
    try:
        with psycopg.connect(pos_dsn, connect_timeout=10) as pg_conn:
            with pg_conn.cursor() as cur:
                # Query order details for the product
                cur.execute(
                    """SELECT 
                           o."Id"::text AS order_id,
                           COALESCE(c."Name", 'Khách vãng lai') AS customer_name,
                           oi."Quantity"::int AS quantity,
                           COALESCE(oi."SubTotalIncludeDiscount"::float, 0) AS subtotal,
                           CASE 
                               WHEN o."CancelAt" IS NOT NULL THEN 'Hủy'
                               WHEN o."CompleteAt" IS NOT NULL THEN 'Hoàn thành'
                               ELSE 'Đang xử lý'
                           END AS status,
                           COALESCE(
                               (o."CompleteAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::text,
                               (o."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::text
                           ) AS order_date
                       FROM "OrderItem" oi
                       JOIN "OrderItemGroup" oig ON oig."Id" = oi."OrderItemGroupId"
                       JOIN "Order" o ON o."Id" = oig."OrderId" AND o."DeleteAt" IS NULL
                       JOIN "Product" p ON p."Id" = oi."ProductId" AND p."DeleteAt" IS NULL
                       LEFT JOIN "Customer" c ON c."Id" = o."CustomerId"
                       WHERE p."Name" = %s AND oi."DeleteAt" IS NULL
                       ORDER BY order_date DESC
                       LIMIT 100""",
                    [product_name]
                )
                db_rows = cur.fetchall()
                for r in db_rows:
                    rows.append({
                        "order_id": r[0],
                        "order_date": r[5][:16] if r[5] else "N/A",
                        "customer_name": r[1],
                        "quantity": r[2],
                        "subtotal": round(r[3], 0),
                        "status": r[4]
                    })
    except Exception as e:
        return {
            "columns": [],
            "rows": [],
            "summary": {"Lỗi_kết_nối": str(e)}
        }
        
    return {
        "columns": [
            {"key": "order_id", "label": "Mã đơn hàng", "type": "text"},
            {"key": "order_date", "label": "Ngày bán", "type": "text"},
            {"key": "customer_name", "label": "Khách hàng", "type": "text"},
            {"key": "quantity", "label": "Số lượng", "type": "number"},
            {"key": "subtotal", "label": "Thành tiền", "type": "currency"},
            {"key": "status", "label": "Trạng thái", "type": "text"},
        ],
        "rows": rows,
        "summary": {
            "Sản_phẩm": product_name,
            "Tổng_đơn_bán": len(rows),
            "Tổng_số_lượng": sum(r["quantity"] for r in rows),
            "Tổng_doanh_thu": sum(r["subtotal"] for r in rows)
        }
    }


def _drill_b2b_customer_orders(conn, start, end, sf, sp, clicked_value=None):
    """Drill-down to B2B customer orders by connecting to remote POS database directly."""
    import psycopg
    from .pos_sync import resolve_pos_dsn
    
    pos_dsn = resolve_pos_dsn()
    if not pos_dsn:
        return {
            "columns": [],
            "rows": [],
            "summary": {"Error": "POS database DSN not configured."}
        }
        
    rows = []
    customer_name = "Đại lý"
    try:
        with psycopg.connect(pos_dsn, connect_timeout=10) as pg_conn:
            with pg_conn.cursor() as cur:
                # Query customer name
                if clicked_value:
                    try:
                        cur.execute('SELECT "Name" FROM "Customer" WHERE "Id" = %s', [clicked_value])
                        c_row = cur.fetchone()
                        if c_row:
                            customer_name = c_row[0]
                    except Exception:
                        pg_conn.rollback()
                        
                # Query order list for CustomerId
                cur.execute(
                    """SELECT 
                           o."Id"::text,
                           COALESCE(o."TotalAmount"::float, 0) AS total,
                           COALESCE(o."PaidAmount"::float, 0) AS paid,
                           COALESCE(o."LeftAmount"::float, 0) AS left_amt,
                           CASE 
                               WHEN o."CancelAt" IS NOT NULL THEN 'Hủy'
                               WHEN o."CompleteAt" IS NOT NULL THEN 'Hoàn thành'
                               ELSE 'Đang xử lý'
                           END AS status,
                           COALESCE(
                               (o."CompleteAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::text,
                               (o."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::text
                           ) AS order_date
                       FROM "Order" o
                       WHERE o."CustomerId" = %s AND o."DeleteAt" IS NULL
                       ORDER BY order_date DESC
                       LIMIT 100""",
                    [clicked_value]
                )
                db_rows = cur.fetchall()
                for r in db_rows:
                    rows.append({
                        "order_id": r[0],
                        "order_date": r[5][:16] if r[5] else "N/A",
                        "total_amount": round(r[1], 0),
                        "paid_amount": round(r[2], 0),
                        "left_amount": round(r[3], 0),
                        "status": r[4]
                    })
    except Exception as e:
        return {
            "columns": [],
            "rows": [],
            "summary": {"Lỗi_kết_nối": str(e)}
        }
        
    return {
        "columns": [
            {"key": "order_id", "label": "Mã đơn hàng", "type": "text"},
            {"key": "order_date", "label": "Ngày mua", "type": "text"},
            {"key": "total_amount", "label": "Tổng tiền", "type": "currency"},
            {"key": "paid_amount", "label": "Đã thanh toán", "type": "currency"},
            {"key": "left_amount", "label": "Còn nợ", "type": "currency"},
            {"key": "status", "label": "Trạng thái", "type": "text"},
        ],
        "rows": rows,
        "summary": {
            "Tên_đại_lý": customer_name,
            "Tổng_số_đơn": len(rows),
            "Tổng_công_nợ_đơn": sum(r["left_amount"] for r in rows)
        }
    }


def _drill_staff_orders(conn, start, end, sf, sp, clicked_value=None):
    """Drill-down to list of B2B/B2C customers served by a staff member (from POS database directly)."""
    import psycopg
    from .pos_sync import resolve_pos_dsn
    
    pos_dsn = resolve_pos_dsn()
    if not pos_dsn:
        return {
            "columns": [],
            "rows": [],
            "summary": {"Error": "POS database DSN not configured."}
        }
        
    rows = []
    staff_name = "Nhân viên"
    try:
        with psycopg.connect(pos_dsn, connect_timeout=10) as pg_conn:
            with pg_conn.cursor() as cur:
                # Query staff name
                if clicked_value:
                    try:
                        cur.execute('SELECT "Name" FROM "Staff" WHERE "Id" = %s', [clicked_value])
                        s_row = cur.fetchone()
                        if s_row:
                            staff_name = s_row[0]
                    except Exception:
                        pg_conn.rollback()
                        
                # Query customer purchase summary grouped under this staff
                cur.execute(
                    """SELECT 
                           c."Id"::text AS customer_id,
                           COALESCE(c."Name", 'Khách vãng lai') AS customer_name,
                           COUNT(DISTINCT o."Id")::int AS orders_count,
                           SUM(COALESCE(o."TotalAmount"::float, 0)) AS total_spent,
                           MAX(COALESCE(
                               (o."CompleteAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::text,
                               (o."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::text
                           )) AS last_date
                       FROM "Order" o
                       LEFT JOIN "Customer" c ON c."Id" = o."CustomerId"
                       WHERE o."StaffId" = %s AND o."DeleteAt" IS NULL
                       GROUP BY c."Id", c."Name"
                       ORDER BY total_spent DESC
                       LIMIT 100""",
                    [clicked_value]
                )
                db_rows = cur.fetchall()
                for r in db_rows:
                    rows.append({
                        "customer_id": r[0] if r[0] else "",
                        "customer_name": r[1],
                        "orders_count": r[2],
                        "total_spent": round(r[3], 0),
                        "last_date": r[4][:16] if r[4] else "N/A"
                    })
    except Exception as e:
        return {
            "columns": [],
            "rows": [],
            "summary": {"Lỗi_kết_nối": str(e)}
        }
        
    return {
        "columns": [
            {"key": "customer_name", "label": "Khách hàng", "type": "text"},
            {"key": "orders_count", "label": "Số đơn hàng", "type": "number"},
            {"key": "total_spent", "label": "Doanh số phục vụ", "type": "currency"},
            {"key": "last_date", "label": "Giao dịch gần nhất", "type": "text"},
        ],
        "rows": rows,
        "summary": {
            "Nhân_viên": staff_name,
            "Khách_hàng_phục_vụ": len(rows),
            "Tổng_doanh_số": sum(r["total_spent"] for r in rows)
        }
    }


# Dispatch table for drill-down
_DRILL_DOWN_DISPATCH = {
    "revenue": _drill_revenue_by_store,
    "revenue_by_day": _drill_revenue_by_day,
    "orders": _drill_orders_by_store,
    "aov": _drill_aov_by_store,
    "gpm": _drill_gpm_by_store,
    "customers": _drill_customers_by_store,
    "gross_profit": _drill_revenue_by_store,
    "revenue_trend_point": _drill_revenue_trend_point,
    "top_product": _drill_top_product,
    "customer_segment": _drill_customer_segment,
    "payment_method": _drill_payment_method,
    "monthly_revenue": _drill_monthly_revenue,
    "return_rate": _drill_return_rate,
    "rfm_segment": _drill_rfm_segment,
    "leaderboard_store": _drill_leaderboard_store,
    "csat_store": _drill_csat_store,
    "revenue_per_staff_store": _drill_revenue_per_staff_store,
    "inventory_category": _drill_inventory_category,
    "inventory_product": _drill_inventory_product,
    "b2b_customer_orders": _drill_b2b_customer_orders,
    "staff_orders": _drill_staff_orders,
}

_DRILL_DOWN_TITLES = {
    "revenue": "Chi tiết Doanh thu",
    "revenue_by_day": "Doanh thu theo ngày",
    "orders": "Chi tiết Đơn hàng",
    "aov": "Chi tiết AOV",
    "gpm": "Chi tiết Biên LN gộp",
    "customers": "Chi tiết Khách hàng",
    "gross_profit": "Chi tiết Lợi nhuận gộp",
    "revenue_trend_point": "Chi tiết ngày",
    "top_product": "Chi tiết sản phẩm",
    "customer_segment": "Chi tiết phân khúc",
    "payment_method": "Chi tiết phương thức TT",
    "monthly_revenue": "Chi tiết tháng",
    "return_rate": "Chi tiết tỷ lệ trả hàng",
    "rfm_segment": "Khách hàng trong nhóm",
    "leaderboard_store": "Chi tiết cửa hàng",
    "csat_store": "CSAT cửa hàng theo tháng",
    "revenue_per_staff_store": "DT/Nhân viên theo ngày",
    "inventory_category": "Sản phẩm trong danh mục",
    "inventory_product": "Đơn hàng bán sản phẩm",
    "b2b_customer_orders": "Danh sách đơn hàng đại lý",
    "staff_orders": "Khách hàng mua từ nhân viên",
}


def drill_down_payload(
    conn,
    metric_key: str,
    start: str,
    end: str,
    store_ids: list[str] | None = None,
    clicked_value: str | None = None,
) -> dict:
    """Generic drill-down: decompose an aggregated metric into detail rows."""
    handler = _DRILL_DOWN_DISPATCH.get(metric_key)
    if not handler:
        return {
            "ok": False,
            "error": f"Unknown metric_key: {metric_key}",
            "supported": list(_DRILL_DOWN_DISPATCH.keys()),
        }

    sf, sp = _store_filter_clause(store_ids)
    result = handler(conn, start, end, sf, sp, clicked_value)

    title = _DRILL_DOWN_TITLES.get(metric_key, f"Chi tiết {metric_key}")
    subtitle = f"{start} — {end}"
    if clicked_value:
        subtitle = f"{clicked_value} | {subtitle}"

    return {
        "ok": True,
        "metric_key": metric_key,
        "title": title,
        "subtitle": subtitle,
        "columns": result["columns"],
        "rows": result["rows"],
        "summary": result.get("summary", {}),
    }


# ---------------------------------------------------------------------------
# Revenue per Staff (DT / cửa hàng)
# ---------------------------------------------------------------------------


def revenue_per_staff_payload(
    conn,
    start: str,
    end: str,
    store_ids: list[str] | None = None,
) -> dict:
    """Revenue per staff member by store."""
    sf, sp = _store_filter_clause(store_ids)

    stores = conn.execute(
        f"""SELECT
                s.id, s.name, s.code, s.staff_count,
                COALESCE(SUM(ds.revenue), 0) AS revenue,
                COALESCE(SUM(ds.orders_n), 0) AS orders_n
            FROM stores s
            LEFT JOIN daily_sales ds ON ds.store_id = s.id
                AND ds.d BETWEEN %s AND %s
            WHERE 1=1 {sf.replace('store_id', 's.id') if sf else ''}
            GROUP BY s.id, s.name, s.code, s.staff_count
            ORDER BY revenue DESC""",
        [start, end] + sp,
    ).fetchall()

    result = []
    for s in stores:
        store_id, name, code, staff_count, revenue, orders = s
        staff = staff_count if staff_count and staff_count > 0 else 12
        rev_per_staff = revenue / staff
        orders_per_staff = orders / staff

        result.append({
            "store_id": store_id,
            "name": name,
            "code": code,
            "staff_count": staff_count or 0,
            "revenue": round(revenue, 0),
            "orders": orders,
            "revenue_per_staff": round(rev_per_staff, 0),
            "orders_per_staff": round(orders_per_staff, 1),
        })

    # Chain average
    total_rev = sum(r["revenue"] for r in result)
    total_staff = sum(r["staff_count"] for r in result)
    chain_avg = total_rev / total_staff if total_staff > 0 else 0

    return {
        "ok": True,
        "stores": result,
        "chain_average": {
            "revenue_per_staff": round(chain_avg, 0),
            "total_staff": total_staff,
            "total_revenue": round(total_rev, 0),
        },
    }


# ---------------------------------------------------------------------------
# Staff Revenue (DT / nhân viên)
# ---------------------------------------------------------------------------


def staff_revenue_payload(
    conn,
    start: str,
    end: str,
    store_ids: list[str] | None = None,
) -> dict:
    """Revenue breakdown by staff member."""
    sf, sp = _store_filter_clause(store_ids)

    rows = conn.execute(
        f"""SELECT
                sr.staff_id,
                COALESCE(s.name, 'Unknown') AS staff_name,
                COALESCE(s.code, '') AS staff_code,
                SUM(sr.revenue) AS revenue,
                SUM(sr.orders_n) AS orders_n,
                COUNT(DISTINCT sr.d) AS active_days
            FROM daily_staff_revenue sr
            LEFT JOIN staff s ON s.id = sr.staff_id
            WHERE sr.d BETWEEN %s AND %s {sf.replace('store_id', 'sr.store_id') if sf else ''}
            GROUP BY sr.staff_id, s.name, s.code
            ORDER BY revenue DESC""",
        [start, end] + sp,
    ).fetchall()

    staff_list = []
    for r in rows:
        staff_id, name, code, revenue, orders, active_days = r
        staff_list.append({
            "staff_id": staff_id,
            "name": name,
            "code": code,
            "revenue": round(revenue, 0),
            "orders": orders,
            "active_days": active_days,
            "revenue_per_day": round(revenue / active_days, 0) if active_days > 0 else 0,
        })

    total_rev = sum(s["revenue"] for s in staff_list)
    total_orders = sum(s["orders"] for s in staff_list)

    return {
        "ok": True,
        "staff": staff_list,
        "summary": {
            "total_revenue": round(total_rev, 0),
            "total_orders": total_orders,
            "staff_count": len(staff_list),
            "avg_revenue_per_staff": round(total_rev / len(staff_list), 0) if staff_list else 0,
        },
    }


# ---------------------------------------------------------------------------
# Order List (Danh sách đơn hàng)
# ---------------------------------------------------------------------------


def order_list_payload(
    conn,
    start: str,
    end: str,
    store_ids: list[str] | None = None,
) -> dict:
    """List of orders with staff, payment method, status."""
    sf, sp = _store_filter_clause(store_ids)

    rows = conn.execute(
        f"""SELECT
                order_id, store_id, staff_id, staff_name, customer_name,
                total_amount, paid_amount, payment_method, status,
                complete_at, issue_at
            FROM order_list
            WHERE LEFT(complete_at, 10) BETWEEN %s AND %s {sf}
            ORDER BY complete_at DESC
            LIMIT 200""",
        [start, end] + sp,
    ).fetchall()

    orders = []
    for r in rows:
        orders.append({
            "order_id": r[0],
            "store_id": r[1],
            "staff_id": r[2],
            "staff_name": r[3],
            "customer_name": r[4],
            "total_amount": round(r[5], 0),
            "paid_amount": round(r[6], 0),
            "payment_method": r[7],
            "status": r[8],
            "complete_at": r[9],
            "issue_at": r[10],
        })

    return {
        "ok": True,
        "orders": orders,
        "total": len(orders),
    }


# ---------------------------------------------------------------------------
# Inventory by Category (Tồn kho nhóm sản phẩm)
# ---------------------------------------------------------------------------


def inventory_by_category_payload(
    conn,
    store_ids: list[str] | None = None,
) -> dict:
    """Inventory grouped by product category."""
    sf, sp = _store_filter_clause(store_ids)

    rows = conn.execute(
        f"""SELECT
                COALESCE(category, 'Uncategorized') AS category,
                COUNT(*) AS sku_count,
                SUM(on_hand) AS total_on_hand,
                SUM(inventory_value) AS total_value,
                SUM(CASE WHEN is_dead_stock = 1 THEN 1 ELSE 0 END) AS dead_stock_count,
                AVG(stock_cover_days) AS avg_cover_days
            FROM inventory_wms
            WHERE 1=1 {sf}
            GROUP BY COALESCE(category, 'Uncategorized')
            ORDER BY total_value DESC""",
        sp,
    ).fetchall()

    categories = []
    for r in rows:
        categories.append({
            "category": r[0],
            "sku_count": r[1],
            "total_on_hand": round(r[2], 0),
            "total_value": round(r[3], 0),
            "dead_stock_count": r[4],
            "avg_cover_days": round(r[5], 1) if r[5] else 0,
        })

    total_value = sum(c["total_value"] for c in categories)
    total_skus = sum(c["sku_count"] for c in categories)

    return {
        "ok": True,
        "categories": categories,
        "summary": {
            "total_categories": len(categories),
            "total_skus": total_skus,
            "total_value": round(total_value, 0),
        },
    }
