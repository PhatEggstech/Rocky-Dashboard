"""Read-only retail reporting for ASM accounts, scoped by POS SaleZone."""
from __future__ import annotations

from datetime import date
from typing import Sequence
from zoneinfo import ZoneInfo

from .config import PAYMENT_COLLECTION_DOCUMENT_TYPE, PAYMENT_RECEIVE_DOCUMENT_TYPE
from .tools import _get_pos_conn

VN_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")
ASM_MIN_DATE = date(2026, 4, 30)


def validate_asm_date_range(date_from: str, date_to: str) -> None:
    """Reject report windows before the approved ASM reporting boundary."""
    start = date.fromisoformat(date_from)
    end = date.fromisoformat(date_to)
    if end < start:
        raise ValueError("date_to must be on or after date_from")
    if start < ASM_MIN_DATE:
        raise ValueError(
            f"ASM reporting starts on {ASM_MIN_DATE.isoformat()}; earlier data is restricted"
        )


def _normalize_zone_ids(sale_zone_ids: Sequence[str] | None) -> list[str]:
    return list(dict.fromkeys(
        str(value).strip() for value in sale_zone_ids or [] if str(value).strip()
    ))


def _zone_filter(alias: str, sale_zone_ids: Sequence[str] | None) -> tuple[str, list]:
    zone_ids = _normalize_zone_ids(sale_zone_ids)
    if not zone_ids:
        return "", []
    return f' AND {alias}."SaleZoneId"::text = ANY(%s)', [zone_ids]


def query_sale_zones(sale_zone_ids: Sequence[str] | None = None) -> dict:
    """List permitted POS sales zones without exposing any commercial data."""
    zone_ids = _normalize_zone_ids(sale_zone_ids)
    conditions = ['z."DeleteAt" IS NULL']
    params: list = []
    if zone_ids:
        conditions.append('z."Id"::text = ANY(%s)')
        params.append(zone_ids)

    conn = _get_pos_conn()
    try:
        rows = conn.execute(
            f'''
            SELECT z."Id"::text, z."Code", z."Name", z."Level",
                   parent."Id"::text, parent."Name"
            FROM "SaleZone" z
            LEFT JOIN "SaleZone" parent
              ON parent."Id" = z."ParentId" AND parent."DeleteAt" IS NULL
            WHERE {" AND ".join(conditions)}
            ORDER BY z."Level", z."Name"
            ''',
            params,
        ).fetchall()
    finally:
        conn.close()

    return {
        "metric": "sale_zones",
        "source": "POS.SaleZone",
        "zones": [
            {
                "id": row[0], "code": row[1], "name": row[2], "level": row[3],
                "parent_id": row[4], "parent_name": row[5],
            }
            for row in rows
        ],
    }


def query_field_sales_by_zone(sale_zone_ids: Sequence[str]) -> dict:
    """Return field-sales assignments from StaffAsignSaleZone, not a guessed region."""
    zone_ids = _normalize_zone_ids(sale_zone_ids)
    if not zone_ids:
        raise ValueError("At least one permitted sale zone is required")

    conn = _get_pos_conn()
    try:
        rows = conn.execute(
            '''
            SELECT z."Id"::text, z."Name", s."Id"::text, s."Code", s."Name", s."State"
            FROM "StaffAsignSaleZone" assignment
            JOIN "SaleZone" z ON z."Id" = assignment."SaleZoneId"
             AND z."DeleteAt" IS NULL
            JOIN "Staff" s ON s."Id" = assignment."StaffId"
             AND s."DeleteAt" IS NULL
            WHERE assignment."DeleteAt" IS NULL
              AND z."Id"::text = ANY(%s)
            ORDER BY z."Name", s."Name", s."Code"
            ''',
            [zone_ids],
        ).fetchall()
    finally:
        conn.close()

    sales = [
        {
            "sale_zone_id": row[0], "sale_zone": row[1], "staff_id": row[2],
            "staff_code": row[3], "staff_name": row[4], "staff_state": row[5],
        }
        for row in rows
    ]
    return {
        "metric": "field_sales_by_zone",
        "source": "POS.StaffAsignSaleZone -> POS.SaleZone -> POS.Staff",
        "sale_zone_ids": zone_ids,
        "staff_count": len(sales),
        "staff": sales,
    }


def query_regional_receipts(
    date_from: str,
    date_to: str,
    sale_zone_ids: Sequence[str],
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Return retail receipt detail using Allocate first and legacy Receive fallback.

    Allocation lines are the canonical receipt source. A legacy Receive header
    is included only when its Order has no valid Allocate anywhere, preventing
    duplicate collection when POS contains both document types for one order.
    """
    validate_asm_date_range(date_from, date_to)
    zone_ids = _normalize_zone_ids(sale_zone_ids)
    if not zone_ids:
        raise ValueError("At least one permitted sale zone is required")
    limit = max(1, min(int(limit), 100))
    offset = max(0, min(int(offset), 100000))

    zone_sql, zone_params = _zone_filter("o", zone_ids)
    cte = f'''
        WITH allocate_lines AS (
            SELECT poi."OrderId" AS order_id, po."Id" AS payment_order_id,
                   po."Code" AS receipt_code, po."IssueAt" AS receipt_issue_at,
                   poi."PaidAmount"::numeric AS amount, 'Allocate'::text AS source_type
            FROM "PaymentOrder" po
            JOIN "PaymentOrderItem" poi
              ON poi."PaymentOrderId" = po."Id"
             AND poi."DeleteAt" IS NULL AND poi."PaidAmount" > 0
            WHERE po."DocumentType" = %s
              AND po."DeleteAt" IS NULL AND po."CancelAt" IS NULL
              AND po."CompleteAt" IS NOT NULL
              AND (po."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date BETWEEN %s AND %s
        ),
        legacy_receive_lines AS (
            SELECT po."ObjectId" AS order_id, po."Id" AS payment_order_id,
                   po."Code" AS receipt_code, po."IssueAt" AS receipt_issue_at,
                   po."PaidAmount"::numeric AS amount, 'Receive_fallback'::text AS source_type
            FROM "PaymentOrder" po
            WHERE po."DocumentType" = %s
              AND po."ObjectType" = 1
              AND po."ObjectId" IS NOT NULL
              AND po."PaidAmount" > 0
              AND po."DeleteAt" IS NULL AND po."CancelAt" IS NULL
              AND po."CompleteAt" IS NOT NULL
              AND (po."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date BETWEEN %s AND %s
              AND NOT EXISTS (
                  SELECT 1
                  FROM "PaymentOrder" allocation
                  JOIN "PaymentOrderItem" allocation_item
                    ON allocation_item."PaymentOrderId" = allocation."Id"
                   AND allocation_item."DeleteAt" IS NULL
                   AND allocation_item."PaidAmount" > 0
                  WHERE allocation."DocumentType" = %s
                    AND allocation."DeleteAt" IS NULL AND allocation."CancelAt" IS NULL
                    AND allocation."CompleteAt" IS NOT NULL
                    AND allocation_item."OrderId" = po."ObjectId"
              )
        ),
        receipt_lines AS (
            SELECT * FROM allocate_lines
            UNION ALL
            SELECT * FROM legacy_receive_lines
        ),
        eligible_receipts AS (
            SELECT line.order_id, line.payment_order_id, line.receipt_code,
                   line.receipt_issue_at, line.amount, line.source_type,
                   o."Code" AS order_code, o."SaleZoneId"::text AS sale_zone_id,
                   COALESCE(z."Name", 'Unassigned') AS sale_zone,
                   c."Code" AS customer_code, c."Name" AS customer_name
            FROM receipt_lines line
            JOIN "Order" o ON o."Id" = line.order_id
            LEFT JOIN "SaleZone" z ON z."Id" = o."SaleZoneId" AND z."DeleteAt" IS NULL
            LEFT JOIN "Customer" c ON c."Id" = o."CustomerId"
            WHERE o."DeleteAt" IS NULL
              AND o."ApproveAt" IS NOT NULL
              AND o."CancelAt" IS NULL
              AND o."Type" IN (1, 2)
              AND COALESCE(c."IsHmkCustomer", FALSE) = FALSE
              {zone_sql}
        )
    '''
    base_params = [
        PAYMENT_COLLECTION_DOCUMENT_TYPE, date_from, date_to,
        PAYMENT_RECEIVE_DOCUMENT_TYPE, date_from, date_to,
        PAYMENT_COLLECTION_DOCUMENT_TYPE,
        *zone_params,
    ]

    conn = _get_pos_conn()
    try:
        totals = conn.execute(
            cte + '''
            SELECT sale_zone_id, sale_zone, source_type,
                   COUNT(DISTINCT order_id)::int, COUNT(DISTINCT payment_order_id)::int,
                   COALESCE(SUM(amount), 0)::numeric
            FROM eligible_receipts
            GROUP BY sale_zone_id, sale_zone, source_type
            ORDER BY sale_zone, source_type
            ''',
            base_params,
        ).fetchall()
        rows = conn.execute(
            cte + '''
            SELECT receipt_code, order_code, sale_zone_id, sale_zone, customer_code,
                   customer_name,
                   (receipt_issue_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::text,
                   source_type, amount
            FROM eligible_receipts
            ORDER BY receipt_issue_at DESC, receipt_code DESC
            LIMIT %s OFFSET %s
            ''',
            [*base_params, limit, offset],
        ).fetchall()
    finally:
        conn.close()

    by_zone = [
        {
            "sale_zone_id": row[0], "sale_zone": row[1], "source_type": row[2],
            "orders": int(row[3]), "receipts": int(row[4]), "amount": round(float(row[5] or 0), 0),
        }
        for row in totals
    ]
    receipts = [
        {
            "receipt_code": row[0], "order_code": row[1], "sale_zone_id": row[2],
            "sale_zone": row[3], "customer_code": row[4], "customer_name": row[5],
            "issued_at": row[6], "source_type": row[7], "amount": round(float(row[8] or 0), 0),
        }
        for row in rows
    ]
    return {
        "metric": "regional_retail_receipts",
        "source": "POS.PaymentOrder, PaymentOrderItem, Order, SaleZone, Customer",
        "period": {"date_from": date_from, "date_to": date_to, "timezone": "Asia/Ho_Chi_Minh"},
        "sale_zone_ids": zone_ids,
        "hmk_excluded_by": "Customer.IsHmkCustomer = TRUE",
        "formula": (
            "Allocate (DocumentType=3, PaymentOrderItem.PaidAmount) is primary. "
            "Receive (DocumentType=1, PaymentOrder.PaidAmount) is used only when no valid Allocate exists for the order."
        ),
        "by_zone": by_zone,
        "total_amount": round(sum(item["amount"] for item in by_zone), 0),
        "limit": limit,
        "offset": offset,
        "returned": len(receipts),
        "receipts": receipts,
    }
