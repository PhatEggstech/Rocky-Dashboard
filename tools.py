# -*- coding: utf-8 -*-
"""Business logic tools for MCP Server — queries Dashboard PostgreSQL."""
from __future__ import annotations

import psycopg
from .config import DASHBOARD_PG_DSN, POS_PG_DSN


def _get_conn():
    """Get dashboard PG connection."""
    if not DASHBOARD_PG_DSN:
        raise RuntimeError("DASHBOARD_PG_DSN is not configured")
    return psycopg.connect(DASHBOARD_PG_DSN, connect_timeout=10)


def _get_pos_conn():
    """Get POS PG connection (remote)."""
    if not POS_PG_DSN:
        raise RuntimeError("POS_PG_DSN is not configured")
    return psycopg.connect(POS_PG_DSN, connect_timeout=15)


def _anonymize_name(name: str | None) -> str:
    """Anonymize customer/staff names for privacy (e.g. 'Nguyễn Văn A' -> 'Nguyễn *** A')."""
    if not name:
        return "N/A"
    parts = name.strip().split()
    if len(parts) <= 1:
        return name
    if len(parts) == 2:
        return f"{parts[0]} ***"
    return f"{parts[0]} *** {parts[-1]}"


# ---------------------------------------------------------------------------
# Tool 1: Doanh thu (Revenue)
# ---------------------------------------------------------------------------

def query_revenue(date_from: str, date_to: str, store_id: str | None = None) -> dict:
    """Return the four order-overview KPIs used by the Rocky POS dashboard.

    - Order count: valid orders issued in the requested period.
    - Order value: SUM(Order.TotalAmount) for those orders.
    - Order collection: valid PaymentOrderItem.PaidAmount whose receipt was
      issued on the same Vietnam date as its linked order.
    - Outstanding: order value - order collection.

    This preserves the daily dashboard grain for multi-day ranges. A weekly
    result is the sum of its daily results, without later-day debt collections
    leaking into earlier order cohorts.
    """
    conn = _get_pos_conn()
    try:
        params = [date_from, date_to]
        store_filter = ""
        if store_id:
            store_filter = 'AND w."SiteId"::text = %s'
            params.append(store_id)
        params.extend([date_from, date_to])
        cur = conn.execute(
            f"""
            WITH order_base AS (
                SELECT
                    o."Id" AS order_id,
                    (o."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date::text AS d,
                    COALESCE(w."SiteId", o."WarehouseId")::text AS site_id,
                    COALESCE(s."Name", 'Unknown') AS store_name,
                    CASE WHEN c."Type" = 1 THEN TRUE ELSE FALSE END AS is_hmk,
                    COALESCE(o."TotalAmount"::numeric, 0) AS order_value
                FROM "Order" o
                LEFT JOIN "Warehouse" w ON w."Id" = o."WarehouseId"
                LEFT JOIN "Site" s ON s."Id" = w."SiteId"
                LEFT JOIN "Customer" c ON c."Id" = o."CustomerId"
                WHERE o."DeleteAt" IS NULL
                  AND o."ApproveAt" IS NOT NULL
                  AND o."CancelAt" IS NULL
                  AND o."IssueAt" IS NOT NULL
                  AND o."Type" IN (1, 2)
                  AND (o."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
                      BETWEEN %s AND %s
                  {store_filter}
            ),
            payment_by_order AS (
                SELECT
                    poi."OrderId" AS order_id,
                    (po."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date::text AS payment_d,
                    COALESCE(SUM(poi."PaidAmount"::numeric), 0) AS collected
                FROM "PaymentOrderItem" poi
                JOIN "PaymentOrder" po ON po."Id" = poi."PaymentOrderId"
                WHERE poi."DeleteAt" IS NULL
                  AND po."DeleteAt" IS NULL
                  AND po."CompleteAt" IS NOT NULL
                  AND po."CancelAt" IS NULL
                  AND po."DocumentType" = 1
                  AND poi."PaidAmount" > 0
                  AND (po."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
                      BETWEEN %s AND %s
                GROUP BY
                    poi."OrderId",
                    (po."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
            )
            SELECT
                ob.d,
                ob.site_id,
                ob.store_name,
                ob.is_hmk,
                COUNT(*)::int AS order_count,
                COALESCE(SUM(ob.order_value), 0) AS order_value,
                COALESCE(SUM(pbo.collected), 0) AS collected
            FROM order_base ob
            LEFT JOIN payment_by_order pbo
              ON pbo.order_id = ob.order_id
             AND pbo.payment_d = ob.d
            GROUP BY ob.d, ob.site_id, ob.store_name, ob.is_hmk
            ORDER BY ob.d, order_value DESC
            """,
            params,
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    totals = {"orders": 0, "value": 0.0, "collected": 0.0}
    hmk = {"value": 0.0, "collected": 0.0}
    retail = {"value": 0.0, "collected": 0.0}
    store_data: dict[str, dict] = {}
    daily_data: dict[str, dict] = {}

    for d, site_id, store_name, is_hmk, orders, value, collected in rows:
        orders = int(orders or 0)
        value = float(value or 0)
        collected = float(collected or 0)
        totals["orders"] += orders
        totals["value"] += value
        totals["collected"] += collected

        customer_type = hmk if is_hmk else retail
        customer_type["value"] += value
        customer_type["collected"] += collected

        store = store_data.setdefault(site_id, {
            "store_name": store_name,
            "store_id": site_id,
            "orders": 0,
            "value": 0.0,
            "collected": 0.0,
            "hmk_value": 0.0,
            "hmk_collected": 0.0,
            "retail_value": 0.0,
            "retail_collected": 0.0,
        })
        store["orders"] += orders
        store["value"] += value
        store["collected"] += collected
        prefix = "hmk" if is_hmk else "retail"
        store[f"{prefix}_value"] += value
        store[f"{prefix}_collected"] += collected

        day = daily_data.setdefault(d, {"orders": 0, "value": 0.0, "collected": 0.0})
        day["orders"] += orders
        day["value"] += value
        day["collected"] += collected

    total_outstanding = totals["value"] - totals["collected"]
    store_breakdown = []
    for store in sorted(store_data.values(), key=lambda item: item["value"], reverse=True):
        outstanding = store["value"] - store["collected"]
        store_breakdown.append({
            "store_name": store["store_name"],
            "store_id": store["store_id"],
            "so_don": store["orders"],
            "gia_tri_don": round(store["value"], 0),
            "thuc_thu": round(store["collected"], 0),
            "con_phai_thu": round(outstanding, 0),
            "hmk_gia_tri": round(store["hmk_value"], 0),
            "hmk_thuc_thu": round(store["hmk_collected"], 0),
            "retail_gia_tri": round(store["retail_value"], 0),
            "retail_thuc_thu": round(store["retail_collected"], 0),
            # Backward-compatible fields.
            "revenue": round(store["collected"], 0),
            "hmk_revenue": round(store["hmk_collected"], 0),
            "retail_revenue": round(store["retail_collected"], 0),
            "hmk_subtotal": round(store["hmk_value"], 0),
            "retail_subtotal": round(store["retail_value"], 0),
        })

    daily = [{
        "date": d,
        "so_don": values["orders"],
        "gia_tri_don_hang": round(values["value"], 0),
        "thuc_thu": round(values["collected"], 0),
        "con_phai_thu": round(values["value"] - values["collected"], 0),
        "revenue": round(values["collected"], 0),
    } for d, values in sorted(daily_data.items())]

    return {
        "metric": "doanh_thu_don_hang",
        "GIAI_THICH": (
            "Giá trị đơn hàng = SUM(Order.TotalAmount) của đơn phát hành trong kỳ. "
            "Thực thu đơn hàng = SUM(PaymentOrderItem.PaidAmount) của phiếu thu phát hành "
            "cùng ngày Việt Nam với đơn hàng liên kết. Báo cáo nhiều ngày bằng tổng từng ngày. "
            "Còn phải thu = Giá trị đơn hàng - Thực thu đơn hàng."
        ),
        "so_don": totals["orders"],
        "gia_tri_don_hang": round(totals["value"], 0),
        "thuc_thu": round(totals["collected"], 0),
        "con_phai_thu": round(total_outstanding, 0),
        "hmk_gia_tri": round(hmk["value"], 0),
        "hmk_thuc_thu": round(hmk["collected"], 0),
        "retail_gia_tri": round(retail["value"], 0),
        "retail_thuc_thu": round(retail["collected"], 0),
        "store_breakdown": store_breakdown,
        # Backward-compatible fields expected by existing clients.
        "total": round(totals["collected"], 0),
        "hmk_revenue": round(hmk["collected"], 0),
        "retail_revenue": round(retail["collected"], 0),
        "hmk_subtotal_chua_thu": round(hmk["value"] - hmk["collected"], 0),
        "retail_subtotal": round(retail["value"], 0),
        "hmk_total": round(hmk["collected"], 0),
        "other_total": round(retail["collected"], 0),
        "period": f"{date_from} to {date_to}",
        "days": len(daily),
        "daily": daily,
        "unit": "VND",
        "note": (
            "Khớp widget Tổng quan của Rocky POS theo grain ngày của Order.IssueAt. "
            "Không cộng chéo ngày tiền thu nợ của đơn phát hành trước đó."
        ),
    }


# ---------------------------------------------------------------------------
# Tool 2: Doanh số (Subtotal)
# ---------------------------------------------------------------------------

def query_subtotal(date_from: str, date_to: str, store_id: str | None = None) -> dict:
    """Query doanh số (giá trị đơn hàng) theo khoảng thời gian.

    Subtotal = SUM(OrderItem.SubTotalIncludeDiscount)
    - Order.ApproveAt IS NOT NULL
    - Order.Type IN (1, 2) — loại đơn tặng
    - KHÔNG bao gồm ShippingFee
    - Group by Order.ApproveAt (ngày duyệt đơn)
    - Split by is_hmk (Customer.Type=1 = đại lý B2B)
    """
    conn = _get_conn()
    try:
        params = [date_from, date_to]
        store_filter = ""
        if store_id:
            store_filter = "AND store_id = %s"
            params.append(store_id)

        # Total + HMK breakdown
        cur = conn.execute(
            f"""SELECT COALESCE(SUM(subtotal), 0),
                       COALESCE(SUM(CASE WHEN is_hmk THEN subtotal ELSE 0 END), 0),
                       COALESCE(SUM(CASE WHEN NOT is_hmk THEN subtotal ELSE 0 END), 0),
                       COUNT(DISTINCT d),
                       COALESCE(SUM(completed_orders_n), 0),
                       COALESCE(SUM(CASE WHEN is_hmk THEN completed_orders_n ELSE 0 END), 0),
                       COALESCE(SUM(CASE WHEN NOT is_hmk THEN completed_orders_n ELSE 0 END), 0)
                FROM daily_sales WHERE d BETWEEN %s AND %s {store_filter}""",
            params
        )
        total_sub, hmk_sub, other_sub, days, total_orders, hmk_orders, other_orders = cur.fetchone()

        # Daily breakdown
        cur = conn.execute(
            f"SELECT d, SUM(subtotal) FROM daily_sales WHERE d BETWEEN %s AND %s {store_filter} GROUP BY d ORDER BY d",
            params
        )
        daily = [{"date": r[0], "subtotal": round(r[1], 0)} for r in cur.fetchall()]

        return {
            "metric": "doanh_so",
            "total": round(total_sub, 0),
            "hmk_total": round(hmk_sub, 0),
            "other_total": round(other_sub, 0),
            "total_orders": int(total_orders),
            "hmk_orders": int(hmk_orders),
            "other_orders": int(other_orders),
            "period": f"{date_from} to {date_to}",
            "days": days,
            "daily": daily,
            "unit": "VND",
            "note": "Giá trị hàng hóa (OrderItem.SubTotalIncludeDiscount, ApproveAt, Type 1+2, không ship). hmk_total = đại lý B2B (Customer.Type=1), other_total = khách lẻ"
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool 2b: Doanh số theo loại khách hàng (HMK vs Khách lẻ)
# ---------------------------------------------------------------------------

def query_sales_by_customer_type(date_from: str, date_to: str) -> dict:
    """Phân loại doanh số NET theo loại khách hàng: HMK (B2B) vs Khách lẻ.

    ⚠️ QUAN TRỌNG: Tất cả giá trị doanh số trong kết quả ĐÃ LÀ NET (đã trừ đơn trả rồi).
    - hmk_net_sales   = Doanh số NET của HMK  (đã trừ đơn trả, KHÔNG trừ thêm)
    - other_net_sales = Doanh số NET của Khách lẻ (đã trừ đơn trả, KHÔNG trừ thêm)
    - total_net_sales = Tổng doanh số NET (đã trừ đơn trả, KHÔNG trừ thêm)

    Đây là dữ liệu CUỐI CÙNG để báo cáo doanh số net — không cần thêm bước nào.
    Chỉ report thẳng hmk_net_sales và other_net_sales.
    """
    conn = _get_conn()
    try:
        # Summary by customer type
        cur = conn.execute(
            """SELECT
                COALESCE(SUM(subtotal), 0) AS total_subtotal,
                COALESCE(SUM(CASE WHEN is_hmk THEN subtotal ELSE 0 END), 0) AS hmk_subtotal,
                COALESCE(SUM(CASE WHEN NOT is_hmk THEN subtotal ELSE 0 END), 0) AS other_subtotal,
                COALESCE(SUM(completed_orders_n), 0) AS total_orders,
                COALESCE(SUM(CASE WHEN is_hmk THEN completed_orders_n ELSE 0 END), 0) AS hmk_orders,
                COALESCE(SUM(CASE WHEN NOT is_hmk THEN completed_orders_n ELSE 0 END), 0) AS other_orders,
                COALESCE(SUM(units_sold), 0) AS total_units,
                COALESCE(SUM(CASE WHEN is_hmk THEN units_sold ELSE 0 END), 0) AS hmk_units,
                COALESCE(SUM(CASE WHEN NOT is_hmk THEN units_sold ELSE 0 END), 0) AS other_units
            FROM daily_sales WHERE d BETWEEN %s AND %s""",
            [date_from, date_to]
        )
        r = cur.fetchone()
        summary = {
            # ⚠️ TẤT CẢ GIÁ TRỊ SAU ĐÂY ĐÃ LÀ NET (gross - returns đã trừ sẵn)
            "DA_LA_NET": True,
            "total_net_sales": round(r[0], 0),
            "hmk_net_sales": round(r[1], 0),
            "other_net_sales": round(r[2], 0),
            "total_orders": int(r[3]),
            "hmk_orders": int(r[4]),
            "other_orders": int(r[5]),
            "total_units": int(r[6]),
            "hmk_units": int(r[7]),
            "other_units": int(r[8]),
        }

        # Return orders count (tham khảo - ĐÃ được trừ vào net_sales rồi, không trừ thêm)
        cur = conn.execute(
            """SELECT COALESCE(SUM(return_count), 0), COALESCE(SUM(return_amount), 0)
            FROM monthly_returns
            WHERE year_month BETWEEN LEFT(%s, 7) AND LEFT(%s, 7)""",
            [date_from, date_to]
        )
        ret_row = cur.fetchone()
        return_total_count = int(ret_row[0])
        return_total_amount = round(float(ret_row[1]), 0)

        # Daily breakdown
        cur = conn.execute(
            """SELECT d,
                SUM(subtotal) AS total_net,
                SUM(CASE WHEN is_hmk THEN subtotal ELSE 0 END) AS hmk_net,
                SUM(CASE WHEN NOT is_hmk THEN subtotal ELSE 0 END) AS other_net,
                SUM(completed_orders_n) AS orders
            FROM daily_sales WHERE d BETWEEN %s AND %s
            GROUP BY d ORDER BY d""",
            [date_from, date_to]
        )
        daily = [{
            "date": row[0],
            "total_net": round(row[1], 0),
            "hmk_net": round(row[2], 0),
            "other_net": round(row[3], 0),
            "orders": int(row[4]),
        } for row in cur.fetchall()]

        num_days = len(daily) if daily else 1
        avg_per_day = round(summary["total_net_sales"] / num_days, 0)

        return {
            "metric": "doanh_so_net_theo_loai_khach",
            "canh_bao": "DA_LA_NET=True: Tat ca gia tri doanh so DA TRU don tra. KHONG tru them lan nua.",
            "period": f"{date_from} to {date_to}",
            "summary": summary,
            "don_tra_tham_khao": {
                "luu_y": "Da duoc tru vao net_sales roi, KHONG tru them",
                "tong_so_don_tra": return_total_count,
                "tong_gia_tri_don_tra": return_total_amount,
            },
            "avg_net_per_day": avg_per_day,
            "daily": daily,
            "unit": "VND",
            "huong_dan_bao_cao": "Report thang hmk_net_sales va other_net_sales lam Doanh so Net. Day la so cuoi cung."
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool 3: Công nợ B2B (Debt)
# ---------------------------------------------------------------------------

def query_debt(customer_name: str | None = None, date_from: str | None = None, date_to: str | None = None) -> dict:
    """Query công nợ khách hàng B2B từ DebtReport.

    CurrentBalance = PreviousBalance + DebtAmount - TotalReceiveAmount + TotalPaymentAmount
    - Dấu âm thể hiện Rocky nợ khách hàng. Dấu dương thể hiện khách nợ Rocky.
    - Tuy nhiên, 100% dữ liệu nợ thực tế của đại lý đang lưu dấu âm dưới database.
    """
    conn = _get_conn()
    try:
        conditions = []
        params = []

        if customer_name:
            conditions.append("customer_name ILIKE %s")
            params.append(f"%{customer_name}%")
        if date_from:
            conditions.append("start_at >= %s")
            params.append(date_from)
        if date_to:
            conditions.append("end_at <= %s")
            params.append(date_to)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        # Summary
        cur = conn.execute(
            f"SELECT COUNT(DISTINCT customer_id), COALESCE(SUM(current_balance), 0), COALESCE(SUM(debt_amount), 0), COALESCE(SUM(total_receive_amount), 0) FROM debt_report {where}",
            params
        )
        r = cur.fetchone()
        summary = {
            "total_customers": r[0],
            "total_current_balance": round(r[1], 0),
            "total_debt_amount": round(r[2], 0),
            "total_received": round(r[3], 0),
        }

        # Top debtors (latest snapshot)
        cur = conn.execute(
            f"""SELECT customer_name, previous_balance, debt_amount, total_receive_amount, current_balance, start_at
                FROM debt_report {where}
                ORDER BY current_balance ASC LIMIT 10""",
            params
        )
        debtors = [{
            "customer": _anonymize_name(r[0]),
            "previous_balance": round(r[1], 0),
            "debt_amount": round(r[2], 0),
            "received": round(r[3], 0),
            "current_balance": round(r[4], 0),
            "date": r[5],
        } for r in cur.fetchall()]

        return {
            "metric": "cong_no",
            "summary": summary,
            "top_debtors": debtors,
            "formula": "CurrentBalance = PreviousBalance + DebtAmount - TotalReceiveAmount + TotalPaymentAmount",
            "note": "Quy ước dấu: Dấu âm thể hiện Rocky nợ khách hàng (theo thiết kế POS lưu vết ngược). Trị tuyệt đối thể hiện nợ thực tế."
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool 4: Doanh thu nhân viên (Staff Revenue)
# ---------------------------------------------------------------------------

def query_staff_revenue(date_from: str, date_to: str, staff_name: str | None = None) -> dict:
    """Query dashboard staff ranking directly from valid POS orders."""
    conn = _get_pos_conn()
    try:
        params = [date_from, date_to]
        name_filter = ""
        if staff_name:
            name_filter = 'AND s."Name" ILIKE %s'
            params.append(f"%{staff_name}%")

        cur = conn.execute(
            f"""
            SELECT
                s."Id"::text AS staff_id,
                TRIM(s."Name") AS staff_name,
                COALESCE(SUM(o."TotalAmount"::numeric), 0) AS revenue,
                COUNT(DISTINCT o."Id")::int AS orders_n,
                COUNT(DISTINCT (o."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date)::int AS active_days
            FROM "Order" o
            JOIN "Staff" s ON s."Id" = o."StaffId"
            WHERE o."DeleteAt" IS NULL
              AND o."ApproveAt" IS NOT NULL
              AND o."CancelAt" IS NULL
              AND o."IssueAt" IS NOT NULL
              AND o."Type" IN (1, 2)
              AND (o."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
                  BETWEEN %s AND %s
              {name_filter}
            GROUP BY s."Id", s."Name"
            ORDER BY revenue DESC
            LIMIT 20
            """,
            params
        )
        staff = [{
            "staff_id": r[0],
            "name": r[1] or "Unknown",
            "revenue": round(float(r[2] or 0), 0),
            "orders": int(r[3] or 0),
            "active_days": int(r[4] or 0),
            "revenue_per_day": round(float(r[2] or 0) / r[4], 0) if r[4] > 0 else 0,
        } for r in cur.fetchall()]

        total_rev = sum(s["revenue"] for s in staff)

        return {
            "metric": "doanh_thu_nhan_vien",
            "period": f"{date_from} to {date_to}",
            "staff": staff,
            "total_revenue": round(total_rev, 0),
            "staff_count": len(staff),
            "formula": "SUM(Order.TotalAmount), COUNT(DISTINCT Order.Id), grouped by Order.StaffId and Order.IssueAt",
            "note": "Đơn không gán Order.StaffId không xuất hiện trong xếp hạng."
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool 5: Đơn hàng (Orders)
# ---------------------------------------------------------------------------

def query_orders(date_from: str, date_to: str, status: str | None = None, payment_method: str | None = None, store_id: str | None = None) -> dict:
    """Query danh sách đơn hàng."""
    conn = _get_conn()
    try:
        conditions = ["LEFT(complete_at, 10) BETWEEN %s AND %s"]
        params = [date_from, date_to]

        if status:
            conditions.append("status = %s")
            params.append(status)
        if payment_method:
            conditions.append("payment_method ILIKE %s")
            params.append(f"%{payment_method}%")
        if store_id:
            conditions.append("store_id = %s")
            params.append(store_id)

        where = "WHERE " + " AND ".join(conditions)

        cur = conn.execute(
            f"""SELECT order_id, staff_name, customer_name, total_amount, paid_amount, payment_method, status, complete_at
                FROM order_list {where}
                ORDER BY complete_at DESC LIMIT 50""",
            params
        )
        orders = [{
            "order_id": r[0][:8] + "...",
            "staff": _anonymize_name(r[1]),
            "customer": _anonymize_name(r[2]),
            "total_amount": round(r[3], 0),
            "paid_amount": round(r[4], 0),
            "payment_method": r[5],
            "status": r[6],
            "complete_at": r[7],
        } for r in cur.fetchall()]

        total_amount = sum(o["total_amount"] for o in orders)
        total_paid = sum(o["paid_amount"] for o in orders)

        # Real order count from daily_sales (completed_orders_n) — not limited by order_list sync
        daily_sales_filter = ""
        daily_sales_params = [date_from, date_to]
        if store_id:
            daily_sales_filter = "AND store_id = %s"
            daily_sales_params.append(store_id)

        cur = conn.execute(
            f"""SELECT COALESCE(SUM(completed_orders_n), 0),
                       COALESCE(SUM(CASE WHEN is_hmk THEN completed_orders_n ELSE 0 END), 0),
                       COALESCE(SUM(CASE WHEN NOT is_hmk THEN completed_orders_n ELSE 0 END), 0)
                FROM daily_sales WHERE d BETWEEN %s AND %s {daily_sales_filter}""",
            daily_sales_params
        )
        real_total, hmk_orders, other_orders = cur.fetchone()

        # Try to get IssueAt order count (created orders) from POS production DB
        created_orders_count = None
        pos_store_filter = ""
        pos_params = [date_from, date_to]
        if store_id:
            pos_store_filter = 'AND w."SiteId" = %s'
            pos_params.append(store_id)

        try:
            with _get_pos_conn() as pos_conn:
                with pos_conn.cursor() as pos_cur:
                    pos_cur.execute(
                        f"""
                        SELECT COUNT(DISTINCT o."Id")::int 
                        FROM "Order" o
                        LEFT JOIN "Warehouse" w ON w."Id" = o."WarehouseId"
                        WHERE o."DeleteAt" IS NULL AND o."CancelAt" IS NULL AND o."Type" IN (1,2)
                          AND (o."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date BETWEEN %s AND %s {pos_store_filter}
                        """,
                        pos_params
                    )
                    created_orders_count = pos_cur.fetchone()[0]
        except Exception as e:
            # Fallback is silent
            pass

        return {
            "metric": "don_hang",
            "period": f"{date_from} to {date_to}",
            "orders": orders,
            "sample_size": len(orders),
            "total_orders": int(real_total),
            "hmk_orders": int(hmk_orders),
            "other_orders": int(other_orders),
            "created_orders_count": created_orders_count,
            "total_amount": round(total_amount, 0),
            "total_paid": round(total_paid, 0),
            "note": (
                "orders chi hien thi 50 don gan nhat. "
                "total_orders = tong don theo Order.ApproveAt (da duyet) trong khoang ngay. "
                f"created_orders_count = tong don theo Order.IssueAt (da tao) tu POS DB (hien tai la {created_orders_count if created_orders_count is not None else 'N/A'}). "
                "Neu tren Dashboard UI hien thi so lon hon (~1.68k), do la vi Dashboard hien thi theo ngay tao (IssueAt) thay vi ngay duyet (ApproveAt)."
            )
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool 6: Tồn kho (Inventory)
# ---------------------------------------------------------------------------

def query_inventory(category: str | None = None, dead_stock_only: bool = False) -> dict:
    """Query tồn kho từ WMS."""
    conn = _get_conn()
    try:
        conditions = []
        params = []

        if category:
            conditions.append("category ILIKE %s")
            params.append(f"%{category}%")
        if dead_stock_only:
            conditions.append("is_dead_stock = 1")

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        # Summary
        cur = conn.execute(
            f"""SELECT COUNT(*), COALESCE(SUM(on_hand), 0), COALESCE(SUM(inventory_value), 0),
                       COALESCE(AVG(stock_cover_days), 0), SUM(CASE WHEN is_dead_stock=1 THEN 1 ELSE 0 END)
                FROM inventory_wms {where}""",
            params
        )
        r = cur.fetchone()
        summary = {
            "total_skus": r[0],
            "total_on_hand": round(r[1], 0),
            "total_value": round(r[2], 0),
            "avg_stock_cover_days": round(r[3], 1),
            "dead_stock_count": r[4],
        }

        # By category
        cur = conn.execute(
            f"""SELECT COALESCE(category, 'N/A'), COUNT(*), SUM(on_hand), SUM(inventory_value)
                FROM inventory_wms {where}
                GROUP BY category ORDER BY SUM(inventory_value) DESC LIMIT 10""",
            params
        )
        categories = [{
            "category": r[0], "skus": r[1], "on_hand": round(r[2], 0), "value": round(r[3], 0)
        } for r in cur.fetchall()]

        return {
            "metric": "ton_kho",
            "summary": summary,
            "categories": categories,
            "note": "Source: WMS (rocky_wms_dev). Dead stock = không movement > 90 ngày"
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool 7: Khách hàng (Customers)
# ---------------------------------------------------------------------------

def query_customers(segment: str | None = None, top_n: int = 10) -> dict:
    """Query khách hàng RFM."""
    conn = _get_conn()
    try:
        params = []
        seg_filter = ""
        if segment:
            seg_filter = "WHERE segment = %s"
            params.append(segment)

        # Segments distribution
        cur = conn.execute("SELECT segment, COUNT(*), SUM(monetary) FROM customer_rfm GROUP BY segment ORDER BY SUM(monetary) DESC")
        segments = [{"segment": r[0], "count": r[1], "total_monetary": round(r[2], 0)} for r in cur.fetchall()]

        # Top customers
        cur = conn.execute(
            f"SELECT name, monetary, frequency, recency_days, segment FROM customer_rfm {seg_filter} ORDER BY monetary DESC LIMIT %s",
            params + [top_n]
        )
        top = [{
            "name": _anonymize_name(r[0]), "monetary": round(r[1], 0), "frequency": r[2], "recency_days": r[3], "segment": r[4]
        } for r in cur.fetchall()]

        return {
            "metric": "khach_hang",
            "segments": segments,
            "top_customers": top,
            "note": "RFM: Champion (<=30d, >=3 orders), Loyal, At-Risk, Hibernating, Lost"
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool 8: Sản phẩm (Products)
# ---------------------------------------------------------------------------

def query_products(date_from: str | None = None, date_to: str | None = None, top_n: int = 10) -> dict:
    """Query weekly/daily product rankings directly from valid POS order items."""
    date_from = date_from or "2026-01-01"
    date_to = date_to or "2026-12-31"
    top_n = max(1, min(int(top_n), 100))
    conn = _get_pos_conn()
    try:
        cur = conn.execute(
            """
            SELECT
                p."Id"::text AS product_id,
                p."Name" AS product_name,
                COALESCE(pc."Name", 'Uncategorized') AS category,
                COALESCE(SUM(oi."SubTotalIncludeDiscount"::numeric), 0) AS revenue,
                COALESCE(SUM(oi."Quantity"::numeric), 0) AS units_sold,
                COALESCE(SUM(SUM(oi."SubTotalIncludeDiscount"::numeric)) OVER (), 0) AS grand_total_revenue
            FROM "OrderItem" oi
            JOIN "OrderItemGroup" oig
              ON oig."Id" = oi."OrderItemGroupId"
             AND oig."DeleteAt" IS NULL
            JOIN "Order" o ON o."Id" = oig."OrderId"
            JOIN "Product" p
              ON p."Id" = oi."ProductId"
             AND p."DeleteAt" IS NULL
            LEFT JOIN "ProductCategory" pc ON pc."Id" = p."ProductCategoryId"
            WHERE oi."DeleteAt" IS NULL
              AND o."DeleteAt" IS NULL
              AND o."ApproveAt" IS NOT NULL
              AND o."CancelAt" IS NULL
              AND o."IssueAt" IS NOT NULL
              AND o."Type" IN (1, 2)
              AND (o."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
                  BETWEEN %s AND %s
            GROUP BY p."Id", p."Name", pc."Name"
            ORDER BY revenue DESC
            LIMIT %s
            """,
            [date_from, date_to, top_n],
        )
        top_by_revenue = [{
            "product_id": r[0],
            "name": r[1],
            "category": r[2],
            "revenue": round(float(r[3] or 0), 0),
            "units_sold": float(r[4] or 0),
            "share_pct": round(float(r[3] or 0) / float(r[5]) * 100, 2) if r[5] else 0,
        } for r in cur.fetchall()]

        cur = conn.execute(
            """
            SELECT
                COALESCE(oi."ProductItemId", oi."ProductId")::text AS product_item_id,
                MAX(COALESCE(NULLIF(oi."ProductName", ''), p."Name")) AS display_name,
                COALESCE(MAX(pc."Name"), 'Uncategorized') AS category,
                COALESCE(SUM(oi."Quantity"::numeric), 0) AS units_sold,
                COALESCE(SUM(oi."SubTotalIncludeDiscount"::numeric), 0) AS revenue
            FROM "OrderItem" oi
            JOIN "OrderItemGroup" oig
              ON oig."Id" = oi."OrderItemGroupId"
             AND oig."DeleteAt" IS NULL
            JOIN "Order" o ON o."Id" = oig."OrderId"
            JOIN "Product" p
              ON p."Id" = oi."ProductId"
             AND p."DeleteAt" IS NULL
            LEFT JOIN "ProductCategory" pc ON pc."Id" = p."ProductCategoryId"
            WHERE oi."DeleteAt" IS NULL
              AND o."DeleteAt" IS NULL
              AND o."ApproveAt" IS NOT NULL
              AND o."CancelAt" IS NULL
              AND o."IssueAt" IS NOT NULL
              AND o."Type" IN (1, 2)
              AND (o."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
                  BETWEEN %s AND %s
            GROUP BY COALESCE(oi."ProductItemId", oi."ProductId")
            ORDER BY units_sold DESC, revenue DESC
            LIMIT %s
            """,
            [date_from, date_to, top_n],
        )
        top_by_quantity = [{
            "product_item_id": r[0],
            "name": r[1],
            "category": r[2],
            "units_sold": float(r[3] or 0),
            "revenue": round(float(r[4] or 0), 0),
        } for r in cur.fetchall()]

        return {
            "metric": "san_pham",
            "period": f"{date_from} to {date_to}",
            "top_by_revenue": top_by_revenue,
            "top_by_quantity": top_by_quantity,
            # Backward-compatible alias used by current clients.
            "top_products": top_by_revenue,
            "formula": {
                "revenue": "SUM(OrderItem.SubTotalIncludeDiscount) grouped by ProductId",
                "quantity": "SUM(OrderItem.Quantity) grouped by ProductItemId",
            },
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool 9: Cửa hàng (Stores)
# ---------------------------------------------------------------------------

def query_stores(date_from: str, date_to: str) -> dict:
    """Query performance từng cửa hàng."""
    conn = _get_conn()
    try:
        cur = conn.execute(
            """SELECT s.name, COALESCE(SUM(ds.revenue), 0), COALESCE(SUM(ds.subtotal), 0),
                      COALESCE(SUM(ds.orders_n), 0), COALESCE(SUM(ds.unique_customers), 0)
               FROM stores s
               LEFT JOIN daily_sales ds ON ds.store_id = s.id AND ds.d BETWEEN %s AND %s
               GROUP BY s.id, s.name ORDER BY SUM(ds.revenue) DESC""",
            [date_from, date_to]
        )
        stores = [{
            "name": r[0], "revenue": round(r[1], 0), "subtotal": round(r[2], 0),
            "orders": r[3], "customers": r[4]
        } for r in cur.fetchall()]

        return {
            "metric": "cua_hang",
            "period": f"{date_from} to {date_to}",
            "stores": stores,
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool 10: Giải thích metric
# ---------------------------------------------------------------------------

METRIC_EXPLANATIONS = {
    "doanh_thu": {
        "name": "Tổng quan doanh thu đơn hàng",
        "definition": "Bốn KPI của widget Tổng quan cho cohort đơn phát hành trong kỳ",
        "formula": (
            "Số đơn = COUNT(Order.Id); Giá trị đơn = SUM(Order.TotalAmount); "
            "Thực thu = SUM(PaymentOrderItem.PaidAmount) của phiếu thu phát hành trong kỳ "
            "và thuộc các đơn cũng phát hành trong kỳ; Còn phải thu = Giá trị đơn - Thực thu"
        ),
        "group_by": "Order.IssueAt theo giờ Việt Nam; phiếu thu cũng lọc PaymentOrder.IssueAt cùng kỳ",
        "includes": "Order.Type IN (1,2), đơn đã duyệt, chưa hủy/xóa",
        "excludes": "Đơn tặng Type=3 và tiền thu nợ của đơn phát hành ở kỳ trước",
        "note": "Dùng get_revenue để khớp bốn thẻ Tổng quan trên Rocky POS.",
    },
    "doanh_so": {
        "name": "Doanh số (Subtotal)",
        "definition": "Giá trị HÀNG HÓA đã duyệt (không ship)",
        "formula": "SUM(OrderItem.SubTotalIncludeDiscount) WHERE Order.ApproveAt IS NOT NULL AND Order.Type IN (1,2)",
        "group_by": "Order.ApproveAt (ngày duyệt đơn)",
        "includes": "Tiền hàng sau chiết khấu",
        "excludes": "ShippingFee, Đơn tặng (Type=3)",
        "note": "Timeline khác doanh thu — có thể DT > DS (thu nợ cũ) hoặc DS > DT (chưa trả hết)",
    },
    "cong_no": {
        "name": "Công nợ (Debt)",
        "definition": "Số dư nợ khách B2B theo ngày",
        "formula": "CurrentBalance = PreviousBalance + DebtAmount - TotalReceiveAmount + TotalPaymentAmount",
        "source": "DebtReport table (daily snapshot per customer)",
        "note": "Âm = khách nợ. Customer.Type = 1 là đại lý B2B",
    },
    "order_type": {
        "name": "Loại đơn hàng",
        "types": "Type 1 = Bán thường, Type 2 = Đơn dây (B2B), Type 3 = Đơn tặng",
        "note": "Type 3 không tính vào doanh số/doanh thu",
    },
}


def explain_metric(metric_name: str) -> dict:
    """Giải thích chi tiết về một metric/KPI."""
    key = metric_name.lower().replace(" ", "_")
    if key in METRIC_EXPLANATIONS:
        return METRIC_EXPLANATIONS[key]

    # Fuzzy match
    for k, v in METRIC_EXPLANATIONS.items():
        if key in k or k in key:
            return v

    return {
        "error": f"Không tìm thấy metric '{metric_name}'",
        "available": list(METRIC_EXPLANATIONS.keys())
    }


def query_raw_sql(sql: str) -> dict:
    """Chạy câu lệnh SQL SELECT trực tiếp trên Database Gold (hmk_warehouse).
    
    Chỉ cho phép truy vấn READ-ONLY và KHÔNG được phép truy cập bảng 'users' bảo mật.
    """
    from decimal import Decimal
    import re
    
    sql_clean = sql.strip().lower()
    
    # 1. Security: Only allow SELECT
    if not sql_clean.startswith("select"):
        return {"error": "Chỉ được phép thực hiện câu lệnh SELECT (Read-only)."}
        
    # 2. Security: Do not allow accessing 'users' table
    if re.search(r"\busers\b", sql_clean):
        return {"error": "Không có quyền truy cập bảng 'users' chứa thông tin tài khoản."}
        
    conn = _get_conn()
    try:
        cur = conn.execute(sql)
        if cur.description is None:
            return {"metric": "raw_sql", "message": "Query executed successfully, no rows returned."}
            
        colnames = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        
        results = []
        for r in rows:
            formatted_row = []
            for val in r:
                if isinstance(val, Decimal):
                    formatted_row.append(float(val))
                elif hasattr(val, "hex"):  # UUID
                    formatted_row.append(str(val))
                else:
                    formatted_row.append(val)
            results.append(dict(zip(colnames, formatted_row)))
            
        return {
            "metric": "raw_sql",
            "columns": colnames,
            "rows": results[:100],  # Capped at 100 rows
            "total_rows": len(rows)
        }
    except Exception as e:
        return {"error": f"Lỗi truy vấn SQL: {str(e)}"}
    finally:
        conn.close()


def query_raw_pos_sql(sql: str) -> dict:
    """Chạy câu lệnh SQL SELECT trực tiếp trên Database POS gốc.
    
    Chỉ cho phép truy vấn READ-ONLY.
    """
    from decimal import Decimal
    import re
    
    sql_clean = sql.strip().lower()
    
    # 1. Security: Only allow SELECT
    if not sql_clean.startswith("select"):
        return {"error": "Chỉ được phép thực hiện câu lệnh SELECT (Read-only)."}
        
    conn = _get_pos_conn()
    try:
        cur = conn.execute(sql)
        if cur.description is None:
            return {"metric": "raw_pos_sql", "message": "Query executed successfully, no rows returned."}
            
        colnames = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        
        results = []
        for r in rows:
            formatted_row = []
            for val in r:
                if isinstance(val, Decimal):
                    formatted_row.append(float(val))
                elif hasattr(val, "hex"):  # UUID
                    formatted_row.append(str(val))
                else:
                    formatted_row.append(val)
            results.append(dict(zip(colnames, formatted_row)))
            
        return {
            "metric": "raw_pos_sql",
            "columns": colnames,
            "rows": results[:100],  # Capped at 100 rows
            "total_rows": len(rows)
        }
    except Exception as e:
        return {"error": f"Lỗi truy vấn SQL POS: {str(e)}"}
    finally:
        conn.close()



def list_tables() -> dict:
    """Liệt kê các bảng có sẵn trong database dashboard (ngoại trừ bảng users)."""
    conn = _get_conn()
    try:
        cur = conn.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
              AND table_name != 'users' 
              AND table_name != 'pg_stat_statements'
            ORDER BY table_name;
        """)
        tables = [r[0] for r in cur.fetchall()]
        return {
            "metric": "list_tables",
            "tables": tables,
            "count": len(tables)
        }
    except Exception as e:
        return {"error": f"Lỗi liệt kê bảng: {str(e)}"}
    finally:
        conn.close()


def describe_table(table_name: str) -> dict:
    """Xem cấu trúc cột và kiểu dữ liệu của một bảng cụ thể."""
    if table_name.lower().strip() == "users":
        return {"error": "Không có quyền truy cập thông tin cấu trúc bảng 'users'."}
        
    conn = _get_conn()
    try:
        cur = conn.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = %s 
              AND table_schema = 'public'
            ORDER BY ordinal_position;
        """, [table_name])
        columns = [{
            "column": r[0],
            "type": r[1],
            "nullable": r[2] == "YES"
        } for r in cur.fetchall()]
        
        if not columns:
            return {"error": f"Không tìm thấy bảng '{table_name}' hoặc bảng không có cột nào."}
            
        return {
            "metric": "describe_table",
            "table": table_name,
            "columns": columns,
            "count": len(columns)
        }
    except Exception as e:
        return {"error": f"Lỗi xem cấu trúc bảng: {str(e)}"}
    finally:
        conn.close()


def list_specs() -> dict:
    """Liệt kê danh sách các file tài liệu nghiệp vụ có sẵn."""
    import os
    SPECS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "specs")
    if not os.path.exists(SPECS_DIR):
        return {"specs": [], "message": f"Thư mục specs chưa được tạo hoặc trống tại {SPECS_DIR}."}
    
    descriptions = {
        "ROCKY_LENS_COMPLETE_SPEC.md": "Tài liệu đặc tả nghiệp vụ toàn diện của Rocky Lens Dashboard (KPI, luồng dữ liệu, phân quyền).",
        "DASHBOARD_FORMULAS.md": "Các công thức chi tiết để tính toán các chỉ số KPI doanh thu, doanh số, công nợ, đơn hàng.",
        "DATA_FIELDS_VALIDATION.md": "Quy tắc kiểm tra hợp lệ của các trường dữ liệu từ POS sang Gold layer.",
        "DATA_FLOW.md": "Mô tả luồng đi của dữ liệu từ POS PostgreSQL sang Lakehouse và FastAPI.",
        "PROJECT_ANALYSIS.md": "Phân tích toàn diện dự án (phần cứng, hạ tầng, cơ sở dữ liệu và API).",
        "database_dictionary.md": "Từ điển dữ liệu chi tiết của cơ sở dữ liệu Lakehouse (các bảng Gold/Silver).",
        "schema-pos-postgresql-da.md": "Sơ đồ và mô tả thực thể liên kết (ERD) của hệ thống POS PostgreSQL.",
        "schema-pos-postgresql-columns.md": "Danh sách chi tiết tất cả các cột của 255 bảng trong hệ thống POS.",
        "design-brief-executive.md": "Tài liệu yêu cầu thiết kế giao diện (UI/UX) cho Executive Dashboard.",
        "executive-dashboard-functions.md": "Đặc tả các chức năng và API endpoints của Executive Dashboard.",
        "AGENTS.md": "Tài liệu hướng dẫn bắt đầu cho AI agent khi làm việc với dự án.",
        "rocky_unified_schema_and_business.md": "Tài liệu hợp nhất đặc tả cơ sở dữ liệu và quy tắc nghiệp vụ chuỗi Rocky, hướng dẫn AI viết SQL thô."
    }

    
    files = []
    try:
        for f in os.listdir(SPECS_DIR):
            if f.endswith(".md") or f.endswith(".txt"):
                path = os.path.join(SPECS_DIR, f)
                files.append({
                    "filename": f,
                    "size_bytes": os.path.getsize(path),
                    "description": descriptions.get(f, "Tài liệu nghiệp vụ bổ sung.")
                })
    except Exception as e:
        return {"error": f"Lỗi liệt kê danh sách tài liệu nghiệp vụ: {str(e)}"}
            
    return {
        "specs": files,
        "count": len(files),
        "directory": SPECS_DIR
    }


def get_spec_content(filename: str, line_start: int = 1, line_count: int = 200) -> dict:
    """Đọc nội dung của một file tài liệu nghiệp vụ cụ thể (phân trang theo dòng)."""
    import os
    SPECS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "specs")
    # Clean filename for security
    filename = os.path.basename(filename)
    path = os.path.join(SPECS_DIR, filename)
    
    if not os.path.exists(path):
        return {"error": f"Không tìm thấy tài liệu nghiệp vụ '{filename}' tại thư mục specs."}
        
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            
        total_lines = len(lines)
        # 1-indexed conversion
        start_idx = max(0, line_start - 1)
        end_idx = min(total_lines, start_idx + line_count)
        
        content = "".join(lines[start_idx:end_idx])
        
        return {
            "filename": filename,
            "line_start": line_start,
            "line_end": end_idx,
            "total_lines": total_lines,
            "content": content,
            "note": f"Hiển thị dòng {line_start} đến {end_idx} trên tổng số {total_lines} dòng."
        }
    except Exception as e:
        return {"error": f"Lỗi đọc file '{filename}': {str(e)}"}


def search_specs(query: str) -> dict:
    """Tìm kiếm từ khóa trong tất cả các file tài liệu nghiệp vụ."""
    import os
    SPECS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "specs")
    if not query or len(query.strip()) < 2:
        return {"error": "Từ khóa tìm kiếm phải có ít nhất 2 ký tự."}
        
    query_clean = query.lower().strip()
    results = []
    
    if not os.path.exists(SPECS_DIR):
        return {"results": [], "message": f"Thư mục specs không tồn tại hoặc trống tại {SPECS_DIR}."}
        
    try:
        for f in os.listdir(SPECS_DIR):
            if f.endswith(".md") or f.endswith(".txt"):
                path = os.path.join(SPECS_DIR, f)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                        lines = fh.readlines()
                        
                    file_matches = []
                    for idx, line in enumerate(lines):
                        if query_clean in line.lower():
                            file_matches.append({
                                "line_number": idx + 1,
                                "content": line.strip()
                            })
                            
                    if file_matches:
                        results.append({
                            "filename": f,
                            "matches_count": len(file_matches),
                            "matches": file_matches[:30] # Limit matches per file to 30
                        })
                except Exception:
                    pass
    except Exception as e:
        return {"error": f"Lỗi tìm kiếm tài liệu nghiệp vụ: {str(e)}"}
                
    return {
        "query": query,
        "results": results,
        "total_files_matched": len(results)
    }


# ---------------------------------------------------------------------------
# Tool 11: Tỷ lệ thu hồi nợ (Debt Recovery Rate)
# ---------------------------------------------------------------------------
def query_debt_recovery_rate(date_from: str | None = None, date_to: str | None = None) -> dict:
    """Tính toán tỷ lệ thu hồi nợ trung bình của các đại lý B2B.

    Tỷ lệ thu hồi nợ (%) = SUM(TotalReceiveAmount) / (SUM(CASE WHEN previous_balance < 0 THEN ABS(previous_balance) ELSE 0 END) + SUM(DebtAmount)) * 100
    - Nếu nợ cũ + nợ mới = 0: trả về 0%
    """
    conn = _get_conn()
    try:
        conditions = []
        params = []
        if date_from:
            conditions.append("start_at >= %s")
            params.append(date_from)
        if date_to:
            conditions.append("end_at <= %s")
            params.append(date_to)
            
        conditions.append("((CASE WHEN previous_balance < 0 THEN ABS(previous_balance) ELSE 0.0 END) + debt_amount) > 0")
        
        where = "WHERE " + " AND ".join(conditions)
        
        cur = conn.execute(
            f"""SELECT 
                    COALESCE(SUM(debt_amount), 0) AS total_debt_new,
                    COALESCE(SUM(CASE WHEN previous_balance < 0 THEN ABS(previous_balance) ELSE 0.0 END), 0) AS total_debt_old,
                    COALESCE(SUM(total_receive_amount), 0) AS total_received,
                    COUNT(DISTINCT customer_id) AS customer_count
                FROM debt_report {where}""",
            params
        )
        total_debt_new, total_debt_old, total_received, customer_count = cur.fetchone()
        
        total_debt_recoverable = total_debt_old + total_debt_new
        recovery_rate = (total_received / total_debt_recoverable * 100) if total_debt_recoverable > 0 else 0.0
        
        return {
            "metric": "ty_le_thu_hoi_no",
            "average_recovery_rate": round(recovery_rate, 2),
            "total_debt_old": round(total_debt_old, 0),
            "total_debt_new": round(total_debt_new, 0),
            "total_debt_recoverable": round(total_debt_recoverable, 0),
            "total_debt_received": round(total_received, 0),
            "customers_with_debt": customer_count,
            "period": f"{date_from or 'All'} to {date_to or 'All'}",
            "unit": "Percentage (%)",
            "note": "Tỷ lệ thu hồi nợ = Thực thu / (Nợ cũ đầu kỳ + Nợ phát sinh mới)."
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool 11.1: Biên Lợi nhuận Gộp (GPM)
# ---------------------------------------------------------------------------
def query_gpm(date_from: str, date_to: str, store_id: str | None = None) -> dict:
    """Tính toán Biên lợi nhuận gộp (Gross Profit Margin - GPM).

    GPM % = Gross Profit / Revenue * 100
    - Nếu cogs = 0 và revenue > 0: trả về null/None (chưa nhập giá vốn)
    """
    conn = _get_conn()
    try:
        conditions = ["d BETWEEN %s AND %s"]
        params = [date_from, date_to]
        if store_id:
            conditions.append("store_id = %s")
            params.append(store_id)

        where = "WHERE " + " AND ".join(conditions)
        sql = f"""
            SELECT 
                COALESCE(SUM(gross_profit), 0),
                COALESCE(SUM(revenue), 0),
                COALESCE(SUM(cogs), 0)
            FROM daily_sales
            {where}
        """
        cur = conn.execute(sql, params)
        gross_profit, revenue, cogs = cur.fetchone()

        if cogs == 0 and revenue > 0:
            gpm = None
        elif revenue > 0:
            gpm = (gross_profit / revenue) * 100
        else:
            gpm = 0.0

        return {
            "metric": "gpm",
            "gpm_pct": round(gpm, 2) if gpm is not None else None,
            "gross_profit": round(gross_profit, 0),
            "revenue": round(revenue, 0),
            "cogs": round(cogs, 0),
            "period": f"{date_from} to {date_to}",
            "store_id": store_id or "All",
            "unit": "Percentage (%)",
            "note": "GPM = Lợi nhuận gộp / Doanh thu. Nếu cogs = 0 nghĩa là chưa nhập giá vốn."
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool 11.2: Biên Lợi nhuận Ròng Proxy (NPM Proxy)
# ---------------------------------------------------------------------------
def query_npm(date_from: str, date_to: str, store_id: str | None = None) -> dict:
    """Tính toán Biên lợi nhuận ròng proxy (Net Profit Margin Proxy).

    NPM % = (Gross Profit - Opex Proxy) / Revenue * 100
    - Opex Proxy mặc định là 12% doanh thu
    """
    import os
    opex_pct = float(os.getenv("EDP_OPEX_PROXY_PCT", "0.12"))
    
    conn = _get_conn()
    try:
        conditions = ["d BETWEEN %s AND %s"]
        params = [date_from, date_to]
        if store_id:
            conditions.append("store_id = %s")
            params.append(store_id)

        where = "WHERE " + " AND ".join(conditions)
        sql = f"""
            SELECT 
                COALESCE(SUM(gross_profit), 0),
                COALESCE(SUM(revenue), 0),
                COALESCE(SUM(cogs), 0)
            FROM daily_sales
            {where}
        """
        cur = conn.execute(sql, params)
        gross_profit, revenue, cogs = cur.fetchone()

        if cogs == 0 and revenue > 0:
            npm = None
        elif revenue > 0:
            opex = revenue * opex_pct
            net_profit = gross_profit - opex
            npm = (net_profit / revenue) * 100
        else:
            npm = 0.0

        return {
            "metric": "npm",
            "npm_pct": round(npm, 2) if npm is not None else None,
            "revenue": round(revenue, 0),
            "gross_profit": round(gross_profit, 0),
            "opex_proxy": round(revenue * opex_pct, 0) if revenue > 0 else 0,
            "period": f"{date_from} to {date_to}",
            "store_id": store_id or "All",
            "unit": "Percentage (%)",
            "note": f"NPM Proxy = (Lợi nhuận gộp - Opex Proxy {opex_pct*100}%) / Doanh thu."
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool 11.3: Giá trị đơn hàng trung bình (ATV)
# ---------------------------------------------------------------------------
def query_atv(date_from: str, date_to: str, store_id: str | None = None) -> dict:
    """Tính toán Giá trị đơn hàng trung bình (Average Transaction Value).

    ATV = Revenue / Orders
    """
    conn = _get_conn()
    try:
        conditions = ["d BETWEEN %s AND %s"]
        params = [date_from, date_to]
        if store_id:
            conditions.append("store_id = %s")
            params.append(store_id)

        where = "WHERE " + " AND ".join(conditions)
        sql = f"""
            SELECT 
                COALESCE(SUM(revenue), 0),
                COALESCE(SUM(orders_n), 0)
            FROM daily_sales
            {where}
        """
        cur = conn.execute(sql, params)
        revenue, orders = cur.fetchone()

        atv = (revenue / orders) if orders > 0 else 0.0

        return {
            "metric": "atv",
            "atv_value": round(atv, 0),
            "revenue": round(revenue, 0),
            "orders_count": orders,
            "period": f"{date_from} to {date_to}",
            "store_id": store_id or "All",
            "unit": "VND",
            "note": "ATV = Doanh thu / Số đơn hàng duyệt."
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool 11.4: Số lượng sản phẩm trung bình/đơn (UPT)
# ---------------------------------------------------------------------------
def query_upt(date_from: str, date_to: str, store_id: str | None = None) -> dict:
    """Tính toán số sản phẩm trung bình mỗi đơn hàng (Units Per Transaction).

    UPT = Units Sold / Orders
    """
    conn = _get_conn()
    try:
        conditions = ["d BETWEEN %s AND %s"]
        params = [date_from, date_to]
        if store_id:
            conditions.append("store_id = %s")
            params.append(store_id)

        where = "WHERE " + " AND ".join(conditions)
        sql = f"""
            SELECT 
                COALESCE(SUM(units_sold), 0),
                COALESCE(SUM(orders_n), 0)
            FROM daily_sales
            {where}
        """
        cur = conn.execute(sql, params)
        units, orders = cur.fetchone()

        upt = (units / orders) if orders > 0 else 0.0

        return {
            "metric": "upt",
            "upt_value": round(upt, 2),
            "units_sold": units,
            "orders_count": orders,
            "period": f"{date_from} to {date_to}",
            "store_id": store_id or "All",
            "unit": "Quantity/Order",
            "note": "UPT = Tổng số sản phẩm bán ra / Tổng số đơn hàng."
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool 11.5: Doanh thu trung bình/Nhân viên (RPS)
# ---------------------------------------------------------------------------
def query_rps(date_from: str, date_to: str, store_id: str | None = None) -> dict:
    """Tính toán doanh thu trên đầu nhân sự (Revenue per Staff - RPS).

    RPS = Revenue / Staff Count (cửa hàng)
    """
    conn = _get_conn()
    try:
        conditions = ["ds.d BETWEEN %s AND %s"]
        params = [date_from, date_to]
        
        store_filter = ""
        if store_id:
            store_filter = "AND s.id = %s"
            params.append(store_id)

        sql = f"""
            SELECT 
                s.id,
                s.name,
                CASE WHEN s.staff_count IS NOT NULL AND s.staff_count > 0 THEN s.staff_count ELSE 12 END AS staff_count,
                COALESCE(SUM(ds.revenue), 0) AS revenue
            FROM stores s
            LEFT JOIN daily_sales ds ON ds.store_id = s.id AND {conditions[0]}
            WHERE 1=1 {store_filter}
            GROUP BY s.id, s.name, s.staff_count
        """
        cur = conn.execute(sql, params)
        rows = cur.fetchall()

        total_revenue = sum(r[3] for r in rows)
        total_staff = sum(r[2] for r in rows)
        rps = (total_revenue / total_staff) if total_staff > 0 else 0.0

        stores_breakdown = [{
            "store_id": r[0],
            "store_name": r[1],
            "staff_count": r[2],
            "revenue": round(r[3], 0),
            "rps": round(r[3] / r[2], 0) if r[2] > 0 else 0.0
        } for r in rows]

        return {
            "metric": "rps",
            "rps_value": round(rps, 0),
            "total_revenue": round(total_revenue, 0),
            "total_staff_count": total_staff,
            "stores": stores_breakdown,
            "period": f"{date_from} to {date_to}",
            "store_id": store_id or "All",
            "unit": "VND/Staff",
            "note": "RPS = Doanh thu / Số lượng nhân sự cửa hàng (mặc định fallback 12 nhân sự nếu trống)."
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool 11.6: Tỷ lệ làm lại kính (Remake Rate)
# ---------------------------------------------------------------------------
def query_remake_rate(date_from: str | None = None, date_to: str | None = None, store_id: str | None = None) -> dict:
    """Tính toán tỷ lệ làm lại kính (Remake Rate).

    Remake Rate (%) = SUM(remake_orders) / SUM(orders) * 100
    - Đơn làm lại là đơn có ExchangeParentOrderId IS NOT NULL
    - Query trực tiếp từ POS PostgreSQL (rocky_stg)
    """
    conn = _get_pos_conn()
    try:
        conditions = ['o."DeleteAt" IS NULL', 'o."CancelAt" IS NULL', 'o."Type" = 1', 'o."CompleteAt" IS NOT NULL']
        params = []
        if date_from:
            conditions.append("DATE(o.\"CompleteAt\" AT TIME ZONE 'Asia/Ho_Chi_Minh') >= %s")
            params.append(date_from)
        if date_to:
            conditions.append("DATE(o.\"CompleteAt\" AT TIME ZONE 'Asia/Ho_Chi_Minh') <= %s")
            params.append(date_to)
        if store_id:
            conditions.append('w."SiteId" = %s')
            params.append(store_id)

        join_clause = ""
        if store_id:
            join_clause = 'LEFT JOIN "Warehouse" w ON w."Id" = o."WarehouseId"'

        where = "WHERE " + " AND ".join(conditions)
        
        sql = f"""
            SELECT 
                COUNT(o."Id")::int AS total_orders,
                SUM(CASE WHEN o."ExchangeParentOrderId" IS NOT NULL THEN 1 ELSE 0 END)::int AS remake_orders
            FROM "Order" o
            {join_clause}
            {where}
        """
        cur = conn.execute(sql, params)
        total, remake = cur.fetchone()
        
        total = total or 0
        remake = remake or 0
        remake_rate = (remake / total * 100) if total > 0 else 0.0
        
        return {
            "metric": "remake_rate",
            "remake_rate_pct": round(remake_rate, 2),
            "total_orders": total,
            "remake_orders": remake,
            "period": f"{date_from or 'All'} to {date_to or 'All'}",
            "store_id": store_id or "All",
            "unit": "Percentage (%)",
            "note": "Đơn làm lại (remake) được xác định bằng ExchangeParentOrderId IS NOT NULL trên POS."
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool 11.7: Bảng xếp hạng Picker kho (Picker Leaderboard)
# ---------------------------------------------------------------------------
def query_picker_leaderboard(date_from: str | None = None, date_to: str | None = None, store_id: str | None = None, limit: int = 10) -> dict:
    """Bảng xếp hạng hiệu suất Picker kho (Chiến thần bốc tròng).

    Xếp hạng theo Items Picked (số sản phẩm soạn) và Orders Picked (số đơn soạn).
    """
    conn = _get_conn()
    try:
        conditions = []
        params = []
        if date_from:
            conditions.append("d >= %s")
            params.append(date_from)
        if date_to:
            conditions.append("d <= %s")
            params.append(date_to)
        if store_id:
            conditions.append("store_id = %s")
            params.append(store_id)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        sql = f"""
            SELECT 
                staff_id,
                staff_name,
                SUM(orders_picked)::int AS total_orders,
                SUM(items_picked)::float AS total_items
            FROM daily_picker_performance
            {where}
            GROUP BY staff_id, staff_name
            ORDER BY total_items DESC, total_orders DESC
            LIMIT %s
        """
        cur = conn.execute(sql, params + [limit])
        rows = cur.fetchall()

        leaderboard = [{
            "rank": idx + 1,
            "staff_id": r[0],
            "name": _anonymize_name(r[1]),
            "orders_picked": r[2],
            "items_picked": round(r[3], 0)
        } for idx, r in enumerate(rows)]

        return {
            "metric": "picker_leaderboard",
            "period": f"{date_from or 'All'} to {date_to or 'All'}",
            "store_id": store_id or "All",
            "leaderboard": leaderboard,
            "unit": "Units/Orders",
            "note": "Xếp hạng nhân viên kho soạn hàng theo tổng số tròng/sản phẩm soạn được (WMS OutboundDelivery)."
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool 11.8: Hiệu suất soạn hàng Picker (Picker Efficiency)
# ---------------------------------------------------------------------------
def query_picker_efficiency(date_from: str | None = None, date_to: str | None = None, store_id: str | None = None) -> dict:
    """Hiệu suất chi tiết của Picker kho (Average Pick Time & Items Per Hour)."""
    conn = _get_conn()
    try:
        conditions = []
        params = []
        if date_from:
            conditions.append("d >= %s")
            params.append(date_from)
        if date_to:
            conditions.append("d <= %s")
            params.append(date_to)
        if store_id:
            conditions.append("store_id = %s")
            params.append(store_id)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        sql = f"""
            SELECT 
                staff_id,
                staff_name,
                SUM(orders_picked)::int AS total_orders,
                SUM(items_picked)::float AS total_items,
                SUM(total_pick_time)::float AS total_time
            FROM daily_picker_performance
            {where}
            GROUP BY staff_id, staff_name
            ORDER BY total_orders DESC
        """
        cur = conn.execute(sql, params)
        rows = cur.fetchall()

        efficiency = []
        for r in rows:
            staff_id, staff_name, orders, items, total_time = r
            avg_pick_time = total_time / orders if orders > 0 else 0.0
            iph = items / (total_time / 3600.0) if total_time > 0 else 0.0
            efficiency.append({
                "staff_id": staff_id,
                "name": _anonymize_name(staff_name),
                "orders_picked": orders,
                "items_picked": round(items, 0),
                "avg_pick_time_seconds": round(avg_pick_time, 1),
                "items_per_hour": round(iph, 2)
            })

        return {
            "metric": "picker_efficiency",
            "period": f"{date_from or 'All'} to {date_to or 'All'}",
            "store_id": store_id or "All",
            "efficiency": efficiency,
            "note": "Items Per Hour (IPH) = Số sản phẩm soạn / (Thời gian soạn / 3600). Nếu IPH = 0 có thể do dữ liệu soạn hàng cùng giây phát hành/hoàn tất."
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool 12: Top nợ xấu (Top Bad Debts)
# ---------------------------------------------------------------------------
def query_top_bad_debts(limit: int = 10) -> dict:
    """Lấy danh sách các đại lý có số dư nợ xấu cao nhất (CurrentBalance âm sâu nhất)."""
    conn = _get_conn()
    try:
        cur = conn.execute(
            """SELECT customer_name, current_balance, debt_amount, total_receive_amount, end_at
               FROM debt_report
               WHERE current_balance < 0
               ORDER BY current_balance ASC LIMIT %s""",
            [limit]
        )
        rows = cur.fetchall()
        debtors = [{
            "customer": _anonymize_name(r[0]),
            "outstanding_debt": round(abs(r[1]), 0),
            "debt_amount": round(r[2], 0),
            "received": round(r[3], 0),
            "last_updated": r[4]
        } for r in rows]
        
        total_bad_debt = sum(d["outstanding_debt"] for d in debtors)
        
        return {
            "metric": "top_no_xau",
            "debtors": debtors,
            "total_bad_debt_summary": round(total_bad_debt, 0),
            "unit": "VND",
            "note": "Quy ước: Database lưu số âm thể hiện nợ. Dấu âm là Rocky nợ khách hàng, hiển thị trên đây sử dụng trị tuyệt đối để chỉ số tiền đại lý nợ Rocky."
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool 13: Cảnh báo sụt giảm doanh số VIP (VIP Drop Alerts)
# ---------------------------------------------------------------------------
def query_vip_revenue_drop_alerts(limit: int = 20) -> dict:
    """Phát hiện các khách hàng VIP (Champion, Loyal) có dấu hiệu sụt giảm mua hàng (không mua > 45 ngày)."""
    conn = _get_conn()
    try:
        cur = conn.execute(
            """SELECT name, segment, monetary, recency_days
               FROM customer_rfm
               WHERE segment IN ('Champion', 'Loyal') AND recency_days > 45
               ORDER BY recency_days DESC LIMIT %s""",
            [limit]
        )
        rows = cur.fetchall()
        alerts = [{
            "customer": _anonymize_name(r[0]),
            "segment": r[1],
            "historical_monetary": round(r[2], 0),
            "days_since_last_purchase": r[3],
            "risk_level": "HIGH (Chậm mua > 90 ngày)" if r[3] > 90 else "MEDIUM (Chậm mua > 45 ngày)"
        } for r in rows]
        
        return {
            "metric": "canh_bao_vip_sut_giam",
            "alerts": alerts,
            "alerts_count": len(alerts),
            "note": "Cảnh báo kích hoạt khi khách VIP (Champion/Loyal) quá 45 ngày chưa có đơn hàng mới."
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool 14: Doanh số (Subtotal) vs Doanh thu (Revenue)
# ---------------------------------------------------------------------------
def query_gross_net_sales(date_from: str, date_to: str) -> dict:
    """So sánh Doanh số (giá trị đơn hàng duyệt) và Doanh thu (tiền thực nhận).

    LƯU Ý NGHIỆP VỤ:
    - Doanh số (Subtotal) = SUM(OrderItem.SubTotalIncludeDiscount), group by ApproveAt
    - Doanh thu (Revenue) = SUM(PaymentOrderItem.PaidAmount), group by IssueAt
    - Revenue CÓ THỂ > Subtotal vì bao gồm thu nợ cũ từ kỳ trước
    - Subtotal CÓ THỂ > Revenue vì có đơn chưa thanh toán hết
    """
    conn = _get_conn()
    try:
        cur = conn.execute(
            """SELECT COALESCE(SUM(subtotal), 0), COALESCE(SUM(revenue), 0),
                      COALESCE(SUM(orders_n), 0)
               FROM daily_sales
               WHERE d BETWEEN %s AND %s""",
            [date_from, date_to]
        )
        subtotal, revenue, orders = cur.fetchone()
        difference = revenue - subtotal
        collection_rate_pct = (revenue / subtotal * 100) if subtotal > 0 else 0.0
        
        return {
            "metric": "gross_net_sales",
            "subtotal": round(subtotal, 0),
            "revenue": round(revenue, 0),
            "difference": round(difference, 0),
            "collection_rate_pct": round(collection_rate_pct, 2),
            "total_orders": orders,
            "period": f"{date_from} to {date_to}",
            "unit": "VND",
            "note": "Subtotal = Giá trị đơn hàng duyệt (không ship). Revenue = Tiền thực nhận (gồm thu nợ cũ). Revenue > Subtotal → thu nợ kỳ trước. Subtotal > Revenue → còn nợ chưa thanh toán."
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool 15: Phân loại Ngành hàng (DD vs DT)
# ---------------------------------------------------------------------------
def query_product_industry_sales(date_from: str, date_to: str) -> dict:
    """Phân loại doanh số bán hàng theo ngành hàng Gọng kính (DD) và Tròng kính (DT).

    Tròng kính (DT): HAI TRÒNG, DRIVESHIELD, CHỐNG TIA UV, ĐỔI MÀU,
                     CHỐNG VA ĐẬP, BLUECUT, BLUECONTROL, MYOPIA, ĐA TRÒNG
    Gọng kính (DD): Kính mát, Gọng nhựa, Gọng kim loại, phụ kiện...
    Uncategorized: Sản phẩm chưa phân loại (báo riêng)
    """
    conn = _get_conn()
    try:
        ym_from = date_from[:7]
        ym_to = date_to[:7]
        
        cur = conn.execute(
            """SELECT category, COALESCE(SUM(revenue), 0), COALESCE(SUM(units_sold), 0)
               FROM product_performance
               WHERE year_month BETWEEN %s AND %s
               GROUP BY category""",
            [ym_from, ym_to]
        )
        rows = cur.fetchall()
        
        lens_categories = {"HAI TRÒNG", "DRIVESHIELD", "CHỐNG TIA UV", "ĐỔI MÀU", "CHỐNG VA ĐẬP", "BLUECUT", "BLUECONTROL", "MYOPIA", "ĐA TRÒNG"}
        uncategorized_names = {"Uncategorized", "N/A", None, ""}
        
        lens_rev, lens_units = 0.0, 0
        frame_rev, frame_units = 0.0, 0
        uncat_rev, uncat_units = 0.0, 0
        category_breakdown = []
        
        for cat, rev, units in rows:
            category_breakdown.append({"category": cat or "N/A", "revenue": round(rev, 0), "units_sold": units})
            if cat in lens_categories:
                lens_rev += rev
                lens_units += units
            elif cat in uncategorized_names or cat is None:
                uncat_rev += rev
                uncat_units += units
            else:
                frame_rev += rev
                frame_units += units
                
        classified_rev = lens_rev + frame_rev
        total_rev = classified_rev + uncat_rev
        
        result = {
            "metric": "nganh_hang_sales",
            "period": f"{ym_from} to {ym_to}",
            "lenses_dt": {
                "revenue": round(lens_rev, 0),
                "units_sold": lens_units,
                "share_pct": round((lens_rev / total_rev * 100), 2) if total_rev > 0 else 0.0
            },
            "frames_dd": {
                "revenue": round(frame_rev, 0),
                "units_sold": frame_units,
                "share_pct": round((frame_rev / total_rev * 100), 2) if total_rev > 0 else 0.0
            },
            "total_revenue": round(total_rev, 0),
            "category_breakdown": sorted(category_breakdown, key=lambda x: x["revenue"], reverse=True),
            "note": "DT (Tròng kính) gồm 9 loại tròng công nghệ. DD (Gọng kính/Khác) là các sản phẩm còn lại. Uncategorized được tách riêng."
        }
        
        if uncat_rev > 0:
            result["uncategorized"] = {
                "revenue": round(uncat_rev, 0),
                "units_sold": uncat_units,
                "share_pct": round((uncat_rev / total_rev * 100), 2) if total_rev > 0 else 0.0
            }
        
        return result
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool 16: Tỷ lệ Chấp nhận B2B (B2B Adoption Rate)
# ---------------------------------------------------------------------------
def query_b2b_adoption_rate(date_from: str, date_to: str) -> dict:
    """Tính toán tỷ lệ doanh số đặt qua kênh B2B đại lý trên tổng đơn hàng."""
    conn = _get_conn()
    try:
        # B2B customers are those in debt_report.
        # Calculate revenue of B2B customers vs total revenue.
        cur = conn.execute(
            """SELECT 
                 SUM(CASE WHEN customer_name IN (SELECT DISTINCT customer_name FROM debt_report) THEN paid_amount ELSE 0 END),
                 SUM(paid_amount)
               FROM order_list
               WHERE LEFT(complete_at, 10) BETWEEN %s AND %s""",
            [date_from, date_to]
        )
        b2b_rev, total_rev = cur.fetchone()
        b2b_rev = b2b_rev or 0.0
        total_rev = total_rev or 0.0
        
        adoption_pct = (b2b_rev / total_rev * 100) if total_rev > 0 else 0.0
        
        return {
            "metric": "b2b_adoption_rate",
            "b2b_revenue": round(b2b_rev, 0),
            "total_revenue": round(total_rev, 0),
            "adoption_rate_pct": round(adoption_pct, 2),
            "period": f"{date_from} to {date_to}",
            "unit": "Percentage (%)",
            "note": "Tỷ lệ chấp nhận B2B = Doanh thu từ đại lý có nợ (B2B) / Tổng doanh thu thanh toán trong kỳ"
        }
    finally:
        conn.close()


def query_telegram_mappings() -> dict:
    """Truy vấn danh sách nhân viên và quản lý đã đăng ký nhận tin nhắn Telegram."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT staff_code, telegram_chat_id, registered_at::text FROM staff_telegram_mapping ORDER BY staff_code")
        staff_rows = cur.fetchall()
        
        cur.execute("SELECT manager_code, telegram_chat_id, region_id, registered_at::text FROM manager_telegram_mapping ORDER BY manager_code")
        manager_rows = cur.fetchall()
        
        return {
            "status": "success",
            "staff_mappings": [
                {"staff_code": r[0], "telegram_chat_id": r[1], "registered_at": r[2]}
                for r in staff_rows
            ],
            "manager_mappings": [
                {"manager_code": r[0], "telegram_chat_id": r[1], "region_id": r[2], "registered_at": r[3]}
                for r in manager_rows
            ]
        }
    except Exception as e:
        return {"status": "error", "message": f"Lỗi đọc dữ liệu Telegram: {str(e)}"}
    finally:
        conn.close()


def trigger_send_debt_reminders() -> dict:
    """Kích hoạt gửi tin nhắn nhắc nợ khẩn cấp/thủ công cho các nhân viên đã đăng ký Telegram."""
    import sys
    sys.path.append(r"c:\Users\dangt\Downloads\rocky-dashboard")
    
    try:
        from tools.send_overdue_reminders import (
            get_overdue_invoices_per_staff, 
            get_staff_telegram_mappings, 
            send_telegram_message, 
            TELEGRAM_BOT_TOKEN
        )
    except ImportError as e:
        return {
            "status": "error",
            "message": f"Không thể import module nhắc nợ: {str(e)}"
        }
    
    if not TELEGRAM_BOT_TOKEN:
        return {
            "status": "error",
            "message": "Chưa cấu hình TELEGRAM_BOT_TOKEN trên hệ thống."
        }
        
    try:
        overdue_data = get_overdue_invoices_per_staff()
        mappings = get_staff_telegram_mappings()
        
        sent_count = 0
        total_debt_sent = 0
        skipped_staff = []
        
        for staff_code, data in overdue_data.items():
            chat_id = mappings.get(staff_code)
            if not chat_id:
                skipped_staff.append(staff_code)
                continue
                
            if not data["normal_invoices"] and not data["urgent_invoices"]:
                continue
                
            msg = f"🔔 *Rocky Bot: BÁO CÁO CÔNG NỢ ĐẠI LÝ HÀNG NGÀY (AI TRIGGERED)*\n\n"
            msg += f"Chào *{data['name']}*,\nDưới đây là danh sách hóa đơn quá hạn của đại lý do bạn phụ trách:\n\n"
            
            total_debt = 0
            if data["normal_invoices"]:
                msg += "🟡 *CẤP ĐỘ 1: NHẮC NỢ THƯỜNG (>15 NGÀY)*\n"
                for idx, inv in enumerate(data["normal_invoices"]):
                    msg += f"{idx+1}. *Khách hàng:* {inv['customer']}\n"
                    msg += f"   • Mã đơn: `{inv['order_code']}` | Quá hạn: `{inv['days']} ngày`\n"
                    msg += f"   • Số tiền nợ: `{inv['debt']:,.0f} VND`\n"
                    msg += f"   • SĐT: `{inv['phone']}`\n\n"
                    total_debt += inv["debt"]
                    
            if data["urgent_invoices"]:
                msg += "🔴 *CẤP ĐỘ 2: CẢNH BÁO KHẨN CẤP (>60 NGÀY)*\n"
                for idx, inv in enumerate(data["urgent_invoices"]):
                    msg += f"{idx+1}. *Khách hàng:* {inv['customer']}\n"
                    msg += f"   • Mã đơn: `{inv['order_code']}` | Quá hạn: `{inv['days']} ngày`\n"
                    msg += f"   • Số tiền nợ: *{inv['debt']:,.0f} VND*\n"
                    msg += f"   • SĐT: `{inv['phone']}`\n\n"
                    total_debt += inv["debt"]
                    
            msg += f"➖ ➖ ➖ ➖ ➖ ➖ ➖ ➖ ➖\n"
            msg += f"💰 *Tổng công nợ quá hạn cần xử lý: {total_debt:,.0f} VND*\n\n"
            msg += "👉 _Vui lòng khẩn trương liên hệ đối soát và thu hồi nợ gối đầu._"
            
            success = send_telegram_message(TELEGRAM_BOT_TOKEN, chat_id, msg)
            if success:
                sent_count += 1
                total_debt_sent += total_debt
                
        return {
            "status": "success",
            "messages_sent": sent_count,
            "total_debt_notified_vnd": total_debt_sent,
            "skipped_staff_no_telegram": skipped_staff
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Gặp lỗi khi kích hoạt gửi tin: {str(e)}"
        }


