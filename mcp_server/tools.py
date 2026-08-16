# -*- coding: utf-8 -*-
"""Business logic tools for MCP Server — queries Dashboard PostgreSQL."""
from __future__ import annotations

from datetime import date, timedelta
import os
from pathlib import Path
import re
from zoneinfo import ZoneInfo

import psycopg
from .config import (
    DASHBOARD_PG_DSN,
    PAYMENT_COLLECTION_DOCUMENT_TYPE,
    PAYMENT_RECEIVE_DOCUMENT_TYPE,
    POS_PG_DSN,
)


def _get_conn():
    """Get dashboard PG connection."""
    if not DASHBOARD_PG_DSN:
        raise RuntimeError("DASHBOARD_PG_DSN is not configured")
    return psycopg.connect(DASHBOARD_PG_DSN, connect_timeout=10)


def _get_pos_conn():
    """Get POS PG connection (remote) with statement timeout."""
    if not POS_PG_DSN:
        raise RuntimeError("POS_PG_DSN is not configured")
    return psycopg.connect(POS_PG_DSN, connect_timeout=15,
                           options="-c statement_timeout=30000")


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


SPECS_DIR = Path(__file__).resolve().parent / "specs"
POS_TABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")
SCHEMA_QUICK_CONTEXT = {
    "purpose": "Tra cứu schema trước khi viết SQL POS thô; không thay thế tool KPI Dashboard.",
    "source_priority": [
        "KPI giống UI: dùng Dashboard API tool trước.",
        "Câu hỏi nghiệp vụ có tool: dùng tool chuyên biệt.",
        "Không có tool: search schema, xác minh bảng live, rồi mới SELECT POS read-only.",
    ],
    "pos_core_tables": {
        "Order": "Đơn bán; lọc DeleteAt IS NULL, ApproveAt IS NOT NULL, CancelAt IS NULL.",
        "OrderItemGroup": "Cầu nối từ OrderItem sang Order qua OrderId.",
        "OrderItem": "Dòng hàng; nối OrderItemGroupId.",
        "PaymentOrder": "Chứng từ thanh toán; DocumentType là enum nguồn, IssueAt theo giờ Việt Nam.",
        "PaymentOrderItem": "Dòng thanh toán; nối PaymentOrderId và OrderId; PaidAmount là số tiền dòng.",
        "ReturnOrder": "Đơn trả; không tự trừ hai lần nếu tool đã trả NET.",
        "Warehouse": "Nối Order.WarehouseId sang SiteId/chi nhánh.",
        "Customer": "Nối Order.CustomerId; Type=1 là HMK theo contract hiện hữu.",
    },
    "mandatory_rules": [
        "Chuyển timestamp sang Asia/Ho_Chi_Minh trước khi lọc/group theo ngày.",
        "Luôn xem xét DeleteAt IS NULL và trạng thái nghiệp vụ phù hợp.",
        "Không cộng Receive và Allocate cho cùng OrderId khi công thức yêu cầu ưu tiên Allocate.",
        "SQL fallback chỉ SELECT, có LIMIT, và phải nêu nguồn/công thức trong câu trả lời.",
    ],
}


# ---------------------------------------------------------------------------
# Tool 1: Doanh thu (Revenue)
# ---------------------------------------------------------------------------

def query_revenue(date_from: str, date_to: str, store_id: str | None = None) -> dict:
    """Return the four order-overview KPIs used by the Rocky POS dashboard.

    - Order count: valid orders issued in the requested period.
    - Order value: SUM(Order.TotalAmount) for those orders.
    - Order collection: Allocate is used when an order has a valid Allocate;
      Receive is used only when the order has no valid Allocate at all.
    - Outstanding: order value - order collection.

    This preserves the daily dashboard grain for multi-day ranges. A weekly
    result is the sum of its daily results, without later-day debt collections
    leaking into earlier order cohorts.
    """
    conn = _get_pos_conn()
    try:
        snapshot_at = conn.execute("SELECT CURRENT_TIMESTAMP").fetchone()[0]
        snapshot_at = snapshot_at.astimezone(
            ZoneInfo("Asia/Ho_Chi_Minh")
        ).isoformat()
        order_params = [date_from, date_to]
        store_filter = ""
        if store_id:
            store_filter = 'AND w."SiteId"::text = %s'
            order_params.append(store_id)
        payment_params = [
            PAYMENT_COLLECTION_DOCUMENT_TYPE,
            PAYMENT_COLLECTION_DOCUMENT_TYPE,
            date_from,
            date_to,
            PAYMENT_RECEIVE_DOCUMENT_TYPE,
            date_from,
            date_to,
        ]
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
                    ob.order_id,
                    COALESCE(BOOL_OR(po."DocumentType" = %s), FALSE) AS has_allocate,
                    COALESCE(SUM(poi."PaidAmount"::numeric) FILTER (
                        WHERE po."DocumentType" = %s
                          AND (po."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
                              BETWEEN %s AND %s
                    ), 0) AS allocate_collected,
                    COALESCE(SUM(poi."PaidAmount"::numeric) FILTER (
                        WHERE po."DocumentType" = %s
                          AND (po."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
                              BETWEEN %s AND %s
                    ), 0) AS receive_collected
                FROM order_base ob
                LEFT JOIN "PaymentOrderItem" poi
                  ON poi."OrderId" = ob.order_id
                 AND poi."DeleteAt" IS NULL
                 AND poi."PaidAmount" > 0
                LEFT JOIN "PaymentOrder" po
                  ON po."Id" = poi."PaymentOrderId"
                 AND po."DeleteAt" IS NULL
                 AND po."CompleteAt" IS NOT NULL
                 AND po."CancelAt" IS NULL
                GROUP BY ob.order_id
            )
            SELECT
                ob.d,
                ob.site_id,
                ob.store_name,
                ob.is_hmk,
                COUNT(*)::int AS order_count,
                COALESCE(SUM(ob.order_value), 0) AS order_value,
                COALESCE(SUM(CASE
                    WHEN pbo.has_allocate THEN pbo.allocate_collected
                    ELSE pbo.receive_collected
                END), 0) AS collected
            FROM order_base ob
            LEFT JOIN payment_by_order pbo
              ON pbo.order_id = ob.order_id
            GROUP BY ob.d, ob.site_id, ob.store_name, ob.is_hmk
            ORDER BY ob.d, order_value DESC
            """,
            [*order_params, *payment_params],
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
        "formula_version": "overview-v5-allocate-first-receive-fallback",
        "data_as_of": snapshot_at,
        "timezone": "Asia/Ho_Chi_Minh",
        "GIAI_THICH": (
            "Giá trị đơn hàng = SUM(Order.TotalAmount) của đơn phát hành trong kỳ. "
            "Thực thu đơn hàng: nếu OrderId có chứng từ Allocate hợp lệ thì chỉ lấy Allocate phát hành "
            "cùng ngày Việt Nam với đơn; nếu không có Allocate thì fallback Receive cùng ngày. "
            "Không cộng đồng thời Allocate và Receive cho cùng một OrderId. "
            "Báo cáo nhiều ngày bằng tổng từng ngày. "
            "Còn phải thu = Giá trị đơn hàng - Thực thu đơn hàng."
        ),
        "so_don": totals["orders"],
        "gia_tri_don_hang": round(totals["value"], 0),
        "thuc_thu": round(totals["collected"], 0),
        "con_phai_thu": round(total_outstanding, 0),
        "canonical_metrics": {
            "so_don": totals["orders"],
            "gia_tri_don_hang": round(totals["value"], 0),
            "thuc_thu": round(totals["collected"], 0),
            "con_phai_thu": round(total_outstanding, 0),
        },
        "allocate_document_type": PAYMENT_COLLECTION_DOCUMENT_TYPE,
        "receive_fallback_document_type": PAYMENT_RECEIVE_DOCUMENT_TYPE,
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
            "Không cộng chéo ngày tiền thu nợ của đơn phát hành trước đó. "
            "Dữ liệu live có thể thay đổi sau data_as_of khi đơn hoặc phiếu thu "
            "cũ được duyệt/cập nhật muộn."
        ),
    }


# ---------------------------------------------------------------------------
# Tool 2: Doanh số (Subtotal)
# ---------------------------------------------------------------------------

def query_subtotal(date_from: str, date_to: str, store_id: str | None = None) -> dict:
    """Query net sales shown on the Rocky Lens sales dashboard."""
    start_date = date.fromisoformat(date_from)
    end_date = date.fromisoformat(date_to)
    if end_date < start_date:
        raise ValueError("date_to must be on or after date_from")

    conn = _get_pos_conn()
    try:
        params = [date_from, date_to]
        store_filter = ""
        if store_id:
            store_filter = 'AND w."SiteId" = %s'
            params.append(store_id)

        # Gross sales are approved orders by approval date. ProductAmount excludes
        # shipping and matches the sales dashboard before approved returns.
        cur = conn.execute(
            f"""
            SELECT
                (o."ApproveAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date::text AS d,
                COALESCE(c."IsHmkCustomer", FALSE) AS is_hmk,
                o."Type"::int AS order_type,
                COUNT(DISTINCT o."Id")::int AS orders_n,
                COALESCE(SUM(o."ProductAmount"::numeric), 0) AS gross_sales
            FROM "Order" o
            LEFT JOIN "Customer" c ON c."Id" = o."CustomerId"
            LEFT JOIN "Warehouse" w ON w."Id" = o."WarehouseId"
            WHERE o."DeleteAt" IS NULL
              AND o."CancelAt" IS NULL
              AND o."ApproveAt" IS NOT NULL
              AND o."Type" IN (1, 2)
              AND o."ApproveAt" >= (
                  %s::date::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh'
              )
              AND o."ApproveAt" < (
                  (%s::date + 1)::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh'
              )
              {store_filter}
            GROUP BY
                (o."ApproveAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date,
                COALESCE(c."IsHmkCustomer", FALSE),
                o."Type"
            ORDER BY d
            """,
            params
        )
        gross_rows = cur.fetchall()

        # Returns reduce the same customer bucket as the original order and are
        # recognized on ReturnOrder.CompleteAt, matching the dashboard.
        return_params = [date_from, date_to]
        if store_id:
            return_params.append(store_id)
        cur = conn.execute(
            f"""
            SELECT
                (ro."CompleteAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date::text AS d,
                COALESCE(c."IsHmkCustomer", FALSE) AS is_hmk,
                COALESCE(o."Type", 1)::int AS order_type,
                COUNT(DISTINCT ro."Id")::int AS return_orders_n,
                COALESCE(SUM(ro."TotalAmount"::numeric), 0) AS return_amount
            FROM "ReturnOrder" ro
            LEFT JOIN "Order" o ON o."Id" = ro."OriginalOrderId"
            LEFT JOIN "Customer" c ON c."Id" = o."CustomerId"
            LEFT JOIN "Warehouse" w ON w."Id" = o."WarehouseId"
            WHERE ro."DeleteAt" IS NULL
              AND ro."CompleteAt" IS NOT NULL
              AND ro."CompleteAt" >= (
                  %s::date::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh'
              )
              AND ro."CompleteAt" < (
                  (%s::date + 1)::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh'
              )
              {store_filter}
            GROUP BY
                (ro."CompleteAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date,
                COALESCE(c."IsHmkCustomer", FALSE),
                COALESCE(o."Type", 1)
            ORDER BY d
            """,
            return_params,
        )
        return_rows = cur.fetchall()

        daily_map = {}
        current = start_date
        while current <= end_date:
            daily_map[current.isoformat()] = {
                "date": current.isoformat(),
                "gross_sales": 0.0,
                "return_amount": 0.0,
                "subtotal": 0.0,
                "hmk_total": 0.0,
                "other_total": 0.0,
                "sales_orders": 0,
                "return_orders": 0,
            }
            current += timedelta(days=1)

        order_type_map = {}

        def get_order_type_row(order_type):
            order_type = int(order_type or 1)
            if order_type not in order_type_map:
                order_type_map[order_type] = {
                    "order_type": order_type,
                    "label": {
                        1: "Đơn thường",
                        2: "Đơn đẩy",
                    }.get(order_type, f"Loại {order_type}"),
                    "gross_sales": 0.0,
                    "return_amount": 0.0,
                    "net_sales": 0.0,
                    "hmk_total": 0.0,
                    "other_total": 0.0,
                    "sales_orders": 0,
                    "return_orders": 0,
                }
            return order_type_map[order_type]

        for d, is_hmk, order_type, orders_n, gross_sales in gross_rows:
            row = daily_map[d]
            amount = float(gross_sales or 0)
            row["gross_sales"] += amount
            row["sales_orders"] += int(orders_n or 0)
            row["hmk_total" if is_hmk else "other_total"] += amount
            type_row = get_order_type_row(order_type)
            type_row["gross_sales"] += amount
            type_row["sales_orders"] += int(orders_n or 0)
            type_row["hmk_total" if is_hmk else "other_total"] += amount

        for d, is_hmk, order_type, return_orders_n, return_amount in return_rows:
            row = daily_map[d]
            amount = float(return_amount or 0)
            row["return_amount"] += amount
            row["return_orders"] += int(return_orders_n or 0)
            row["hmk_total" if is_hmk else "other_total"] -= amount
            type_row = get_order_type_row(order_type)
            type_row["return_amount"] += amount
            type_row["return_orders"] += int(return_orders_n or 0)
            type_row["hmk_total" if is_hmk else "other_total"] -= amount

        daily = list(daily_map.values())
        for row in daily:
            row["subtotal"] = row["hmk_total"] + row["other_total"]
            for key in (
                "gross_sales", "return_amount", "subtotal",
                "hmk_total", "other_total",
            ):
                row[key] = round(row[key], 0)

        total_sub = sum(row["subtotal"] for row in daily)
        hmk_sub = sum(row["hmk_total"] for row in daily)
        other_sub = sum(row["other_total"] for row in daily)
        gross_total = sum(row["gross_sales"] for row in daily)
        return_amount = sum(row["return_amount"] for row in daily)
        total_orders = sum(row["sales_orders"] for row in daily)
        return_orders = sum(row["return_orders"] for row in daily)
        order_type_breakdown = []
        for type_row in order_type_map.values():
            type_row["net_sales"] = (
                type_row["hmk_total"] + type_row["other_total"]
            )
            for key in (
                "gross_sales", "return_amount", "net_sales",
                "hmk_total", "other_total",
            ):
                type_row[key] = round(type_row[key], 0)
            order_type_breakdown.append(type_row)
        order_type_breakdown.sort(key=lambda row: row["order_type"])

        return {
            "metric": "doanh_so",
            "total": round(total_sub, 0),
            "hmk_total": round(hmk_sub, 0),
            "other_total": round(other_sub, 0),
            "gross_total": round(gross_total, 0),
            "return_amount": round(return_amount, 0),
            "return_orders": int(return_orders),
            "total_orders": int(total_orders),
            "period": f"{date_from} to {date_to}",
            "days": len(daily),
            "daily": daily,
            "order_type_breakdown": order_type_breakdown,
            "unit": "VND",
            "formula": (
                "Net sales = SUM(Order.ProductAmount by ApproveAt) "
                "- SUM(ReturnOrder.TotalAmount by CompleteAt)"
            ),
            "note": (
                "HMK is Customer.IsHmkCustomer=true. Returns are assigned to "
                "the original order's customer bucket. ProductAmount excludes shipping."
            ),
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool 2b: Doanh số theo loại khách hàng (HMK vs Khách lẻ)
# ---------------------------------------------------------------------------

def query_sales_by_customer_type(
    date_from: str,
    date_to: str,
    store_id: str | None = None,
) -> dict:
    """Phân loại doanh số NET theo loại khách hàng: HMK (B2B) vs Khách lẻ.

    ⚠️ QUAN TRỌNG: Tất cả giá trị doanh số trong kết quả ĐÃ LÀ NET (đã trừ đơn trả rồi).
    - hmk_net_sales   = Doanh số NET của HMK  (đã trừ đơn trả, KHÔNG trừ thêm)
    - other_net_sales = Doanh số NET của Khách lẻ (đã trừ đơn trả, KHÔNG trừ thêm)
    - total_net_sales = Tổng doanh số NET (đã trừ đơn trả, KHÔNG trừ thêm)

    Đây là dữ liệu CUỐI CÙNG để báo cáo doanh số net — không cần thêm bước nào.
    Chỉ report thẳng hmk_net_sales và other_net_sales.
    """
    sales = query_subtotal(date_from, date_to, store_id)
    summary = {
        "DA_LA_NET": True,
        "total_net_sales": sales["total"],
        "hmk_net_sales": sales["hmk_total"],
        "other_net_sales": sales["other_total"],
        "total_orders": sales["total_orders"],
        "return_orders": sales["return_orders"],
    }
    daily = [{
        "date": row["date"],
        "total_net": row["subtotal"],
        "hmk_net": row["hmk_total"],
        "other_net": row["other_total"],
        "orders": row["sales_orders"],
        "return_orders": row["return_orders"],
    } for row in sales["daily"]]
    return {
        "metric": "doanh_so_net_theo_loai_khach",
        "canh_bao": "DA_LA_NET=True: doanh so da tru don tra; khong tru them.",
        "period": sales["period"],
        "summary": summary,
        "don_tra_tham_khao": {
            "luu_y": "Da duoc tru vao net_sales roi, KHONG tru them",
            "tong_so_don_tra": sales["return_orders"],
            "tong_gia_tri_don_tra": sales["return_amount"],
        },
        "avg_net_per_day": round(
            sales["total"] / sales["days"], 0
        ) if sales["days"] else 0,
        "theo_loai_don": sales["order_type_breakdown"],
        "daily": daily,
        "unit": "VND",
        "huong_dan_bao_cao": (
            "Report hmk_net_sales va other_net_sales. Day la so cuoi cung."
        ),
    }


def query_return_exchange_requests(
    date_from: str | None = None,
    date_to: str | None = None,
    date_field: str = "create",
    status: str | None = None,
    code: str | None = None,
    reason: str | None = None,
    store_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """List return/exchange requests directly from the POS workflow."""
    date_columns = {
        "create": 'r."CreateAt"',
        "issue": 'r."IssueAt"',
        "update": 'r."UpdateAt"',
        "approve": 'r."ApproveAt"',
        "complete": 'r."CompleteAt"',
    }
    if date_field not in date_columns:
        raise ValueError(
            "date_field must be create, issue, update, approve, or complete"
        )

    limit = max(1, min(int(limit), 100))
    offset = max(0, min(int(offset), 100000))
    date_column = date_columns[date_field]
    conditions = ['r."DeleteAt" IS NULL']
    params = []

    if date_from:
        conditions.append(
            f"{date_column} >= "
            "(%s::date::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh')"
        )
        params.append(date_from)
    if date_to:
        conditions.append(
            f"{date_column} < "
            "((%s::date + 1)::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh')"
        )
        params.append(date_to)
    if status:
        conditions.append('ws."Name" ILIKE %s')
        params.append(f"%{status}%")
    if code:
        conditions.append('r."Code" ILIKE %s')
        params.append(f"%{code}%")
    if reason:
        conditions.append(
            """COALESCE(
                NULLIF(BTRIM(ro."ReturnReason"), ''),
                NULLIF(BTRIM(r."Description"), ''),
                NULLIF(BTRIM(r."CustomerDescription"), ''),
                NULLIF(BTRIM(r."Note"), '')
            ) ILIKE %s"""
        )
        params.append(f"%{reason}%")
    if store_id:
        conditions.append('w."SiteId" = %s')
        params.append(store_id)

    where = " AND ".join(conditions)
    joins = """
        LEFT JOIN "WorkflowState" ws ON ws."Id" = r."StateId"
        LEFT JOIN "ReturnOrder" ro ON ro."Id" = r."ReturnOrderId"
        LEFT JOIN "Customer" c ON c."Id" = r."CustomerId"
        LEFT JOIN "Staff" st ON st."Id" = r."StaffId"
        LEFT JOIN "Order" original_order ON original_order."Id" = r."OriginalOrderId"
        LEFT JOIN "Warehouse" w ON w."Id" = original_order."WarehouseId"
        LEFT JOIN "Site" si ON si."Id" = w."SiteId"
    """

    conn = _get_pos_conn()
    try:
        cur = conn.execute(
            f"""
            SELECT
                COALESCE(ws."Name", 'Không xác định') AS status,
                COUNT(*)::int AS requests_n
            FROM "ReturnOrderRequest" r
            {joins}
            WHERE {where}
            GROUP BY COALESCE(ws."Name", 'Không xác định')
            ORDER BY requests_n DESC, status
            """,
            params,
        )
        status_breakdown = [{
            "status": row[0],
            "requests": int(row[1]),
        } for row in cur.fetchall()]
        total_requests = sum(row["requests"] for row in status_breakdown)

        cur = conn.execute(
            f"""
            SELECT
                r."Code",
                (r."CreateAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::text AS created_at,
                (r."UpdateAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::text AS updated_at,
                (r."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::text AS issued_at,
                (r."ApproveAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::text AS approved_at,
                (r."CompleteAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::text AS completed_at,
                COALESCE(ws."Name", 'Không xác định') AS status,
                COALESCE(
                    NULLIF(BTRIM(ro."ReturnReason"), ''),
                    NULLIF(BTRIM(r."Description"), ''),
                    NULLIF(BTRIM(r."CustomerDescription"), ''),
                    NULLIF(BTRIM(r."Note"), ''),
                    '-'
                ) AS reason,
                c."Name" AS customer_name,
                st."Name" AS staff_name,
                si."Name" AS store_name,
                CASE
                    WHEN r."ReturnOrderId" IS NOT NULL
                     AND r."ExchangeOrderId" IS NOT NULL THEN 'return_exchange'
                    WHEN r."ExchangeOrderId" IS NOT NULL THEN 'exchange'
                    WHEN r."ReturnOrderId" IS NOT NULL THEN 'return'
                    ELSE 'request'
                END AS request_type,
                r."ReturnOrderTotalAmount"::numeric,
                r."ExchangeOrderTotalAmount"::numeric,
                r."DeviationAmount"::numeric
            FROM "ReturnOrderRequest" r
            {joins}
            WHERE {where}
            ORDER BY r."CreateAt" DESC, r."Code" DESC
            LIMIT %s OFFSET %s
            """,
            params + [limit, offset],
        )
        requests = [{
            "code": row[0],
            "created_at": row[1],
            "updated_at": row[2],
            "issued_at": row[3],
            "approved_at": row[4],
            "completed_at": row[5],
            "status": row[6],
            "reason": row[7],
            "customer": _anonymize_name(row[8]),
            "staff": row[9] or "-",
            "store": row[10] or "Không xác định",
            "request_type": row[11],
            "return_amount": round(float(row[12] or 0), 0),
            "exchange_amount": round(float(row[13] or 0), 0),
            "deviation_amount": round(float(row[14] or 0), 0),
        } for row in cur.fetchall()]

        return {
            "metric": "yeu_cau_tra_doi_hang",
            "date_filter": {
                "field": date_field,
                "date_from": date_from,
                "date_to": date_to,
                "timezone": "Asia/Ho_Chi_Minh",
            },
            "filters": {
                "status": status,
                "code": code,
                "reason": reason,
                "store_id": store_id,
            },
            "total_requests": total_requests,
            "status_breakdown": status_breakdown,
            "limit": limit,
            "offset": offset,
            "returned": len(requests),
            "requests": requests,
            "note": (
                "Nguồn ReturnOrderRequest. Trạng thái từ WorkflowState.Name; "
                "lý do ưu tiên ReturnOrder.ReturnReason."
            ),
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool: Vận hành đơn hàng và trả hàng
# ---------------------------------------------------------------------------

def _pos_date_filter(
    conditions: list[str],
    params: list,
    column: str,
    date_from: str | None,
    date_to: str | None,
) -> None:
    """Append Vietnam-local whole-day bounds for a POS timestamp column."""
    if date_from:
        conditions.append(
            f"{column} >= (%s::date::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh')"
        )
        params.append(date_from)
    if date_to:
        conditions.append(
            f"{column} < ((%s::date + 1)::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh')"
        )
        params.append(date_to)


def query_order_operations(
    date_from: str | None = None,
    date_to: str | None = None,
    date_field: str = "issue",
    state: str | None = None,
    payment_state: int | None = None,
    code: str | None = None,
    customer: str | None = None,
    store_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """List active POS orders and the same monetary totals as the order UI.

    This is an operations view, deliberately separate from revenue KPIs. It
    includes active draft, confirmed, shipping, completed, and cancelled
    workflow states exactly as the order-management screen can show them.
    """
    date_columns = {
        "issue": 'o."IssueAt"',
        "create": 'o."CreateAt"',
        "approve": 'o."ApproveAt"',
        "complete": 'o."CompleteAt"',
        "cancel": 'o."CancelAt"',
    }
    if date_field not in date_columns:
        raise ValueError("date_field must be issue, create, approve, complete, or cancel")

    limit = max(1, min(int(limit), 100))
    offset = max(0, min(int(offset), 100000))
    conditions = ['o."DeleteAt" IS NULL']
    params: list = []
    _pos_date_filter(conditions, params, date_columns[date_field], date_from, date_to)

    if state:
        conditions.append('ws."Name" ILIKE %s')
        params.append(f"%{state}%")
    if payment_state is not None:
        conditions.append('o."PaymentState" = %s')
        params.append(int(payment_state))
    if code:
        conditions.append('o."Code" ILIKE %s')
        params.append(f"%{code}%")
    if customer:
        conditions.append('c."Name" ILIKE %s')
        params.append(f"%{customer}%")
    if store_id:
        conditions.append('w."SiteId"::text = %s')
        params.append(str(store_id))

    where = " AND ".join(conditions)
    joins = """
        LEFT JOIN "WorkflowState" ws ON ws."Id" = o."StateId"
        LEFT JOIN "Customer" c ON c."Id" = o."CustomerId"
        LEFT JOIN "Staff" st ON st."Id" = o."StaffId"
        LEFT JOIN "Warehouse" w ON w."Id" = o."WarehouseId"
        LEFT JOIN "Site" si ON si."Id" = w."SiteId"
    """

    conn = _get_pos_conn()
    try:
        cur = conn.execute(
            f"""
            SELECT
                COUNT(*)::int,
                COALESCE(SUM(o."ProductAmount"::numeric), 0),
                COALESCE(SUM(o."ShippingFee"::numeric), 0),
                COALESCE(SUM(o."ShippingFeeTotalAmount"::numeric), 0),
                COALESCE(SUM(o."TotalDiscountAmount"::numeric), 0),
                COALESCE(SUM(o."TotalAmount"::numeric), 0),
                COALESCE(SUM(o."NeedPayAmount"::numeric), 0),
                COALESCE(SUM(o."PaidAmount"::numeric), 0),
                COALESCE(SUM(o."LeftAmount"::numeric), 0)
            FROM "Order" o
            {joins}
            WHERE {where}
            """,
            params,
        )
        totals = cur.fetchone()

        cur = conn.execute(
            f"""
            SELECT
                COALESCE(ws."Name", 'Không xác định') AS state_name,
                COUNT(*)::int AS orders_n,
                COALESCE(SUM(o."TotalAmount"::numeric), 0) AS total_amount
            FROM "Order" o
            {joins}
            WHERE {where}
            GROUP BY COALESCE(ws."Name", 'Không xác định')
            ORDER BY orders_n DESC, state_name
            """,
            params,
        )
        state_breakdown = [
            {
                "state": row[0],
                "orders": int(row[1]),
                "total_amount": round(float(row[2] or 0), 0),
            }
            for row in cur.fetchall()
        ]

        cur = conn.execute(
            f"""
            SELECT
                o."Code",
                (o."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::text,
                (o."ApproveAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::text,
                (o."CompleteAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::text,
                COALESCE(ws."Name", 'Không xác định'),
                o."PaymentState",
                o."Type",
                c."Name",
                st."Name",
                si."Name",
                o."ProductAmount"::numeric,
                o."ShippingFee"::numeric,
                o."TotalDiscountAmount"::numeric,
                o."TotalAmount"::numeric,
                o."NeedPayAmount"::numeric,
                o."PaidAmount"::numeric,
                o."LeftAmount"::numeric
            FROM "Order" o
            {joins}
            WHERE {where}
            ORDER BY o."IssueAt" DESC NULLS LAST, o."Code" DESC
            LIMIT %s OFFSET %s
            """,
            params + [limit, offset],
        )
        orders = [
            {
                "code": row[0],
                "issued_at": row[1],
                "approved_at": row[2],
                "completed_at": row[3],
                "state": row[4],
                "payment_state": row[5],
                "order_type": row[6],
                "customer": _anonymize_name(row[7]),
                "staff": row[8] or "-",
                "store": row[9] or "Không xác định",
                "product_amount": round(float(row[10] or 0), 0),
                "shipping_fee": round(float(row[11] or 0), 0),
                "total_discount_amount": round(float(row[12] or 0), 0),
                "total_amount": round(float(row[13] or 0), 0),
                "need_pay_amount": round(float(row[14] or 0), 0),
                "paid_amount": round(float(row[15] or 0), 0),
                "left_amount": round(float(row[16] or 0), 0),
            }
            for row in cur.fetchall()
        ]
    finally:
        conn.close()

    return {
        "metric": "van_hanh_don_hang",
        "date_filter": {
            "field": date_field,
            "date_from": date_from,
            "date_to": date_to,
            "timezone": "Asia/Ho_Chi_Minh",
        },
        "filters": {
            "state": state,
            "payment_state": payment_state,
            "code": code,
            "customer": customer,
            "store_id": store_id,
            "active_only": True,
        },
        "summary": {
            "orders": int(totals[0] or 0),
            "total_product_amount": round(float(totals[1] or 0), 0),
            "total_shipping_fee": round(float(totals[2] or 0), 0),
            "total_shipping_after_discount": round(float(totals[3] or 0), 0),
            "total_discount_amount": round(float(totals[4] or 0), 0),
            "total_amount": round(float(totals[5] or 0), 0),
            "total_need_pay_amount": round(float(totals[6] or 0), 0),
            "total_paid_amount": round(float(totals[7] or 0), 0),
            "total_left_amount": round(float(totals[8] or 0), 0),
        },
        "state_breakdown": state_breakdown,
        "limit": limit,
        "offset": offset,
        "returned": len(orders),
        "orders": orders,
        "note": (
            "Nguồn POS Order, điều kiện Order.DeleteAt IS NULL như màn Quản lý đơn hàng. "
            "Đây là dữ liệu vận hành, bao gồm cả đơn chưa hoàn thành; không dùng thay cho KPI doanh thu/thực thu. "
            "total_shipping_fee tương ứng cột Tổng tiền vận chuyển của UI."
        ),
    }


def query_return_orders(
    date_from: str | None = None,
    date_to: str | None = None,
    date_field: str = "issue",
    state: str | None = None,
    code: str | None = None,
    customer: str | None = None,
    store_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """List actual return orders from POS ReturnOrder, not workflow requests."""
    date_columns = {
        "issue": 'r."IssueAt"',
        "create": 'r."CreateAt"',
        "approve": 'r."ApproveAt"',
        "complete": 'r."CompleteAt"',
        "cancel": 'r."CancelAt"',
    }
    if date_field not in date_columns:
        raise ValueError("date_field must be issue, create, approve, complete, or cancel")

    limit = max(1, min(int(limit), 100))
    offset = max(0, min(int(offset), 100000))
    conditions = ['r."DeleteAt" IS NULL']
    params: list = []
    _pos_date_filter(conditions, params, date_columns[date_field], date_from, date_to)

    if state:
        conditions.append('ws."Name" ILIKE %s')
        params.append(f"%{state}%")
    if code:
        conditions.append('r."Code" ILIKE %s')
        params.append(f"%{code}%")
    if customer:
        conditions.append('c."Name" ILIKE %s')
        params.append(f"%{customer}%")
    if store_id:
        conditions.append('w."SiteId"::text = %s')
        params.append(str(store_id))

    where = " AND ".join(conditions)
    joins = """
        LEFT JOIN "WorkflowState" ws ON ws."Id" = r."StateId"
        LEFT JOIN "Customer" c ON c."Id" = r."CustomerId"
        LEFT JOIN "Staff" st ON st."Id" = r."StaffId"
        LEFT JOIN "Order" o ON o."Id" = r."OriginalOrderId"
        LEFT JOIN "Warehouse" w ON w."Id" = o."WarehouseId"
        LEFT JOIN "Site" si ON si."Id" = w."SiteId"
    """

    conn = _get_pos_conn()
    try:
        cur = conn.execute(
            f"""
            SELECT
                COUNT(*)::int,
                COALESCE(SUM(r."ProductAmount"::numeric), 0),
                COALESCE(SUM(r."TotalDiscountAmount"::numeric), 0),
                COALESCE(SUM(r."ShippingFeeTotalAmount"::numeric), 0),
                COALESCE(SUM(r."TotalAmount"::numeric), 0),
                COALESCE(SUM(r."NeedPayAmount"::numeric), 0),
                COALESCE(SUM(r."PaidAmount"::numeric), 0),
                COALESCE(SUM(r."CustomerReturnAmount"::numeric), 0)
            FROM "ReturnOrder" r
            {joins}
            WHERE {where}
            """,
            params,
        )
        totals = cur.fetchone()

        cur = conn.execute(
            f"""
            SELECT
                COALESCE(ws."Name", 'Không xác định') AS state_name,
                COUNT(*)::int AS returns_n,
                COALESCE(SUM(r."TotalAmount"::numeric), 0) AS total_amount
            FROM "ReturnOrder" r
            {joins}
            WHERE {where}
            GROUP BY COALESCE(ws."Name", 'Không xác định')
            ORDER BY returns_n DESC, state_name
            """,
            params,
        )
        state_breakdown = [
            {
                "state": row[0],
                "returns": int(row[1]),
                "total_amount": round(float(row[2] or 0), 0),
            }
            for row in cur.fetchall()
        ]

        cur = conn.execute(
            f"""
            SELECT
                r."Code",
                (r."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::text,
                (r."ApproveAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::text,
                (r."CompleteAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::text,
                COALESCE(ws."Name", 'Không xác định'),
                o."Code",
                c."Name",
                st."Name",
                si."Name",
                r."ProductAmount"::numeric,
                r."TotalDiscountAmount"::numeric,
                r."ShippingFeeTotalAmount"::numeric,
                r."TotalAmount"::numeric,
                r."NeedPayAmount"::numeric,
                r."PaidAmount"::numeric,
                r."CustomerReturnAmount"::numeric
            FROM "ReturnOrder" r
            {joins}
            WHERE {where}
            ORDER BY r."IssueAt" DESC NULLS LAST, r."Code" DESC
            LIMIT %s OFFSET %s
            """,
            params + [limit, offset],
        )
        returns = [
            {
                "code": row[0],
                "issued_at": row[1],
                "approved_at": row[2],
                "completed_at": row[3],
                "state": row[4],
                "original_order_code": row[5],
                "customer": _anonymize_name(row[6]),
                "staff": row[7] or "-",
                "store": row[8] or "Không xác định",
                "product_amount": round(float(row[9] or 0), 0),
                "total_discount_amount": round(float(row[10] or 0), 0),
                "shipping_fee_total_amount": round(float(row[11] or 0), 0),
                "total_amount": round(float(row[12] or 0), 0),
                "need_pay_amount": round(float(row[13] or 0), 0),
                "paid_amount": round(float(row[14] or 0), 0),
                "customer_return_amount": round(float(row[15] or 0), 0),
            }
            for row in cur.fetchall()
        ]
    finally:
        conn.close()

    return {
        "metric": "tra_hang",
        "date_filter": {
            "field": date_field,
            "date_from": date_from,
            "date_to": date_to,
            "timezone": "Asia/Ho_Chi_Minh",
        },
        "filters": {
            "state": state,
            "code": code,
            "customer": customer,
            "store_id": store_id,
            "active_only": True,
        },
        "summary": {
            "return_orders": int(totals[0] or 0),
            "total_product_amount": round(float(totals[1] or 0), 0),
            "total_discount_amount": round(float(totals[2] or 0), 0),
            "total_shipping_fee_after_discount": round(float(totals[3] or 0), 0),
            "total_amount": round(float(totals[4] or 0), 0),
            "total_need_pay_amount": round(float(totals[5] or 0), 0),
            "total_paid_amount": round(float(totals[6] or 0), 0),
            "total_customer_return_amount": round(float(totals[7] or 0), 0),
        },
        "state_breakdown": state_breakdown,
        "limit": limit,
        "offset": offset,
        "returned": len(returns),
        "return_orders": returns,
        "note": (
            "Nguồn POS ReturnOrder, điều kiện ReturnOrder.DeleteAt IS NULL như màn Quản lý trả hàng. "
            "Không phải ReturnOrderRequest; dùng tool yêu cầu trả/đổi khi cần theo dõi workflow request."
        ),
    }


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
              AND o."IssueAt" >= (%s::date::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh')
              AND o."IssueAt" < (
                  (%s::date + 1)::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh'
              )
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
        except Exception:
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
# Tool 7b: Doanh số theo khách hàng
# ---------------------------------------------------------------------------

def query_customer_sales(
    date_from: str,
    date_to: str,
    top_n: int = 10,
    page: int = 1,
    page_size: int = 20,
    order_type: int | None = None,
    store_id: str | None = None,
) -> dict:
    """Query the Rocky Lens customer-sales list and Top-N overview."""
    start_date = date.fromisoformat(date_from)
    end_date = date.fromisoformat(date_to)
    if end_date < start_date:
        raise ValueError("date_to must be on or after date_from")

    top_n = max(1, min(int(top_n), 50))
    page = max(1, int(page))
    page_size = max(1, min(int(page_size), 100))
    if order_type not in (None, 0, 1, 2, 3):
        raise ValueError("order_type must be 0, 1, 2, or 3")

    order_filters = ['o."Type" IN (1, 2)']
    return_filters = ['original_order."Type" IN (1, 2)']
    order_params = [date_from, date_to]
    return_params = [date_from, date_to]

    if order_type not in (None, 0):
        order_filters = ['o."Type" = %s']
        return_filters = ['original_order."Type" = %s']
        order_params.append(order_type)
        return_params.append(order_type)
    if store_id:
        order_filters.append('w."SiteId" = %s')
        return_filters.append('return_w."SiteId" = %s')
        order_params.append(store_id)
        return_params.append(store_id)

    conn = _get_pos_conn()
    try:
        cur = conn.execute(
            f"""
            WITH order_sales AS (
                SELECT
                    o."CustomerId" AS customer_id,
                    COUNT(DISTINCT o."Id")::int AS num_order,
                    COALESCE(SUM(o."ProductAmount"::numeric), 0) AS order_revenue
                FROM "Order" o
                LEFT JOIN "Warehouse" w ON w."Id" = o."WarehouseId"
                WHERE o."DeleteAt" IS NULL
                  AND o."CancelAt" IS NULL
                  AND o."ApproveAt" IS NOT NULL
                  AND o."CustomerId" IS NOT NULL
                  AND o."ApproveAt" >= (
                      %s::date::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh'
                  )
                  AND o."ApproveAt" < (
                      (%s::date + 1)::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh'
                  )
                  AND {' AND '.join(order_filters)}
                GROUP BY o."CustomerId"
            ),
            return_sales AS (
                SELECT
                    original_order."CustomerId" AS customer_id,
                    COUNT(DISTINCT ro."Id")::int AS num_return_order,
                    COALESCE(SUM(ro."TotalAmount"::numeric), 0) AS return_revenue
                FROM "ReturnOrder" ro
                JOIN "Order" original_order
                  ON original_order."Id" = ro."OriginalOrderId"
                LEFT JOIN "Warehouse" return_w
                  ON return_w."Id" = original_order."WarehouseId"
                WHERE ro."DeleteAt" IS NULL
                  AND ro."CompleteAt" IS NOT NULL
                  AND original_order."CustomerId" IS NOT NULL
                  AND ro."CompleteAt" >= (
                      %s::date::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh'
                  )
                  AND ro."CompleteAt" < (
                      (%s::date + 1)::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh'
                  )
                  AND {' AND '.join(return_filters)}
                GROUP BY original_order."CustomerId"
            )
            SELECT
                c."Id"::text AS customer_id,
                c."Code" AS customer_code,
                c."Name" AS customer_name,
                COALESCE(os.order_revenue, 0) AS order_revenue,
                COALESCE(rs.return_revenue, 0) AS return_revenue,
                COALESCE(os.order_revenue, 0)
                    - COALESCE(rs.return_revenue, 0) AS total_revenue,
                COALESCE(os.num_order, 0)::int AS num_order,
                COALESCE(rs.num_return_order, 0)::int AS num_return_order
            FROM order_sales os
            FULL OUTER JOIN return_sales rs
              ON rs.customer_id = os.customer_id
            JOIN "Customer" c
              ON c."Id" = COALESCE(os.customer_id, rs.customer_id)
            ORDER BY total_revenue DESC, c."Code", c."Id"
            """,
            order_params + return_params,
        )
        rows = [{
            "customer_id": row[0],
            "customer_code": row[1],
            "customer_name": row[2] or "Không xác định",
            "order_revenue": round(float(row[3] or 0), 0),
            "return_revenue": round(float(row[4] or 0), 0),
            "total_revenue": round(float(row[5] or 0), 0),
            "num_order": int(row[6] or 0),
            "num_return_order": int(row[7] or 0),
        } for row in cur.fetchall()]

        top_rows = rows[:top_n]
        offset = (page - 1) * page_size
        page_rows = rows[offset:offset + page_size]

        def summarize(summary_rows):
            return {
                "customers": len(summary_rows),
                "total_revenue": round(
                    sum(row["total_revenue"] for row in summary_rows), 0
                ),
                "order_revenue": round(
                    sum(row["order_revenue"] for row in summary_rows), 0
                ),
                "return_revenue": round(
                    sum(row["return_revenue"] for row in summary_rows), 0
                ),
                "orders": sum(row["num_order"] for row in summary_rows),
                "return_orders": sum(
                    row["num_return_order"] for row in summary_rows
                ),
            }

        total_customers = len(rows)
        top_summary = summarize(top_rows)
        return {
            "metric": "doanh_so_theo_khach_hang",
            "period": f"{date_from} to {date_to}",
            "dashboard_ui_summary": {
                "total_revenue": top_summary["total_revenue"],
                "customers": total_customers,
                "orders": top_summary["orders"],
                "return_orders": top_summary["return_orders"],
                "top_n": top_n,
                "scope_note": (
                    "Matches the Rocky Lens customer-sales dashboard: customers is the "
                    "full filtered customer count; revenue, orders, and return_orders "
                    "are sums of the Top N customers."
                ),
            },
            "dashboard_top_summary": {
                **top_summary,
                "top_n": top_n,
                "all_customer_count": total_customers,
                "scope_note": (
                    "Rocky Lens shows all_customer_count from the full result, "
                    "but revenue/orders/returns are summed from Top N only."
                ),
            },
            "all_customers_summary": summarize(rows),
            "top_customers": top_rows,
            "customer_list": {
                "page": page,
                "page_size": page_size,
                "page_count": (
                    (total_customers + page_size - 1) // page_size
                    if total_customers else 0
                ),
                "total": total_customers,
                "data": page_rows,
            },
            "filters": {
                "order_type": order_type or 0,
                "store_id": store_id,
            },
            "unit": "VND",
            "formula": (
                "Per customer net sales = SUM(Order.ProductAmount by ApproveAt) "
                "- SUM(ReturnOrder.TotalAmount by CompleteAt)."
            ),
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
            WITH filtered_orders AS MATERIALIZED (
                SELECT o."Id"
                FROM "Order" o
                WHERE o."DeleteAt" IS NULL
                  AND o."ApproveAt" IS NOT NULL
                  AND o."CancelAt" IS NULL
                  AND o."IssueAt" IS NOT NULL
                  AND o."Type" IN (1, 2)
                  AND o."IssueAt" >= (%s::date::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh')
                  AND o."IssueAt" < (
                      (%s::date + 1)::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh'
                  )
            ),
            filtered_items AS MATERIALIZED (
                SELECT
                    oi."ProductId" AS product_id,
                    COALESCE(oi."ProductItemId", oi."ProductId") AS product_item_id,
                    NULLIF(oi."ProductName", '') AS item_name,
                    oi."SubTotalIncludeDiscount"::numeric AS revenue,
                    oi."Quantity"::numeric AS units_sold
                FROM filtered_orders o
                JOIN "OrderItemGroup" oig
                  ON oig."OrderId" = o."Id"
                 AND oig."DeleteAt" IS NULL
                JOIN "OrderItem" oi
                  ON oi."OrderItemGroupId" = oig."Id"
                 AND oi."DeleteAt" IS NULL
            ),
            aggregates AS (
                SELECT
                    product_id,
                    product_item_id,
                    CASE WHEN GROUPING(product_item_id) = 1
                        THEN 'revenue' ELSE 'quantity' END AS ranking,
                    MAX(item_name) AS item_name,
                    COALESCE(SUM(revenue), 0) AS revenue,
                    COALESCE(SUM(units_sold), 0) AS units_sold
                FROM filtered_items
                GROUP BY GROUPING SETS (
                    (product_id),
                    (product_id, product_item_id)
                )
            ),
            ranked AS (
                SELECT
                    aggregates.*,
                    SUM(revenue) FILTER (WHERE ranking = 'revenue') OVER () AS grand_total_revenue,
                    ROW_NUMBER() OVER (
                        PARTITION BY ranking
                        ORDER BY
                            CASE WHEN ranking = 'revenue' THEN revenue END DESC NULLS LAST,
                            CASE WHEN ranking = 'quantity' THEN units_sold END DESC NULLS LAST,
                            revenue DESC,
                            product_id,
                            product_item_id NULLS FIRST
                    ) AS rank
                FROM aggregates
            )
            SELECT
                ranked.ranking,
                ranked.rank,
                ranked.product_id::text AS product_id,
                ranked.product_item_id::text AS product_item_id,
                p."Name" AS product_name,
                COALESCE(pc."Name", 'Uncategorized') AS category,
                COALESCE(ranked.item_name, p."Name") AS display_name,
                ranked.revenue,
                ranked.units_sold,
                ranked.grand_total_revenue
            FROM ranked
            JOIN "Product" p
              ON p."Id" = ranked.product_id
             AND p."DeleteAt" IS NULL
            LEFT JOIN "ProductCategory" pc ON pc."Id" = p."ProductCategoryId"
            WHERE ranked.rank <= %s
            ORDER BY ranked.ranking, ranked.rank
            """,
            [date_from, date_to, top_n],
        )
        rows = cur.fetchall()
        top_by_revenue = []
        top_by_quantity = []
        for row in rows:
            ranking, _, product_id, product_item_id, product_name, category, display_name, revenue, units_sold, grand_total = row
            if ranking == "revenue":
                rounded_revenue = round(float(revenue or 0), 0)
                total_revenue = float(grand_total or 0)
                top_by_revenue.append({
                    "product_id": product_id,
                    "name": product_name,
                    "category": category,
                    "revenue": rounded_revenue,
                    "units_sold": float(units_sold or 0),
                    "share_pct": round(rounded_revenue / total_revenue * 100, 2)
                    if total_revenue else 0,
                })
            else:
                top_by_quantity.append({
                    "product_item_id": product_item_id,
                    "name": display_name,
                    "category": category,
                    "units_sold": float(units_sold or 0),
                    "revenue": round(float(revenue or 0), 0),
                })

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
    if not SPECS_DIR.exists():
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
        for path in SPECS_DIR.iterdir():
            if path.suffix in {".md", ".txt"}:
                f = path.name
                files.append({
                    "filename": f,
                    "size_bytes": path.stat().st_size,
                    "description": descriptions.get(f, "Tài liệu nghiệp vụ bổ sung.")
                })
    except Exception as e:
        return {"error": f"Lỗi liệt kê danh sách tài liệu nghiệp vụ: {str(e)}"}
            
    return {
        "specs": files,
        "count": len(files),
        "directory": str(SPECS_DIR)
    }


def get_spec_content(filename: str, line_start: int = 1, line_count: int = 200) -> dict:
    """Đọc nội dung của một file tài liệu nghiệp vụ cụ thể (phân trang theo dòng)."""
    # Clean filename for security
    filename = Path(filename).name
    path = SPECS_DIR / filename
    
    if not os.path.exists(path):
        return {"error": f"Không tìm thấy tài liệu nghiệp vụ '{filename}' tại thư mục specs."}
        
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
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


def get_schema_quick_context() -> dict:
    """Lấy bản đồ schema POS ngắn gọn và quy tắc bắt buộc trước SQL fallback."""
    return {"metric": "schema_quick_context", **SCHEMA_QUICK_CONTEXT}


def search_specs(query: str, max_results: int = 12) -> dict:
    """Tìm schema/nghiệp vụ theo từ khóa và trả đoạn ngữ cảnh có giới hạn."""
    if not query or len(query.strip()) < 2:
        return {"error": "Từ khóa tìm kiếm phải có ít nhất 2 ký tự."}
    if not 1 <= max_results <= 30:
        return {"error": "max_results phải trong khoảng 1 đến 30."}

    tokens = re.findall(r"[\wÀ-ỹ]+", query.lower())
    if not tokens:
        return {"error": "Không tách được từ khóa tìm kiếm hợp lệ."}
    results = []

    if not SPECS_DIR.exists():
        return {"results": [], "message": f"Thư mục specs không tồn tại hoặc trống tại {SPECS_DIR}."}

    try:
        for path in SPECS_DIR.iterdir():
            if path.suffix in {".md", ".txt"}:
                try:
                    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
                    file_matches: list[dict] = []
                    for idx, line in enumerate(lines):
                        normalized = line.lower()
                        score = sum(token in normalized for token in tokens)
                        if score:
                            context_start = max(0, idx - 1)
                            context_end = min(len(lines), idx + 2)
                            file_matches.append({
                                "line_number": idx + 1,
                                "score": score,
                                "content": "\n".join(lines[context_start:context_end]).strip(),
                            })
                    if file_matches:
                        file_matches.sort(key=lambda item: (-item["score"], item["line_number"]))
                        results.append({
                            "filename": path.name,
                            "matches_count": len(file_matches),
                            "matches": file_matches[:max_results],
                        })
                except Exception:
                    pass
    except Exception as e:
        return {"error": f"Lỗi tìm kiếm tài liệu nghiệp vụ: {str(e)}"}
                
    results.sort(key=lambda item: (-max(match["score"] for match in item["matches"]), item["filename"]))
    return {
        "query": query,
        "tokens": tokens,
        "results": results[:max_results],
        "total_files_matched": len(results),
        "note": "Đây là retrieval tài liệu. Dùng describe_pos_table để xác minh cột DB live trước SQL fallback.",
    }


def describe_pos_table(table_name: str) -> dict:
    """Mô tả cột và foreign key của một bảng public trong POS gốc, không đọc dữ liệu."""
    table_name = table_name.strip()
    if not POS_TABLE_NAME_RE.fullmatch(table_name):
        return {"error": "Tên bảng POS không hợp lệ."}

    conn = _get_pos_conn()
    try:
        columns = conn.execute(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            [table_name],
        ).fetchall()
        if not columns:
            return {"error": f"Không tìm thấy bảng POS '{table_name}'."}
        foreign_keys = conn.execute(
            """
            SELECT kcu.column_name, ccu.table_name AS referenced_table,
                   ccu.column_name AS referenced_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name = tc.constraint_name
             AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'public'
              AND tc.table_name = %s
            ORDER BY kcu.ordinal_position
            """,
            [table_name],
        ).fetchall()
        return {
            "metric": "pos_table_schema",
            "database": "pos_source",
            "table": table_name,
            "columns": [
                {
                    "column": row[0],
                    "type": row[1],
                    "nullable": row[2] == "YES",
                    "default": row[3],
                }
                for row in columns
            ],
            "foreign_keys": [
                {
                    "column": row[0],
                    "referenced_table": row[1],
                    "referenced_column": row[2],
                }
                for row in foreign_keys
            ],
            "count": len(columns),
        }
    except Exception as e:
        return {"error": f"Lỗi mô tả bảng POS: {str(e)}"}
    finally:
        conn.close()


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
                
            msg = "🔔 *Rocky Bot: BÁO CÁO CÔNG NỢ ĐẠI LÝ HÀNG NGÀY (AI TRIGGERED)*\n\n"
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
                    
            msg += "➖ ➖ ➖ ➖ ➖ ➖ ➖ ➖ ➖\n"
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
