"""Bounded, read-only POS queries with explicit employee/branch scope.

These helpers do not resolve caller permissions; callers must supply authorized
staff/site IDs. Supplying both scopes intersects them.
"""
from __future__ import annotations

from datetime import date, timedelta

from .config import PAYMENT_COLLECTION_DOCUMENT_TYPE, PAYMENT_RECEIVE_DOCUMENT_TYPE
from .tools import _get_pos_conn


def _scope(staff_id, store_id, all_sites=False):
    staff = str(staff_id).strip() if staff_id is not None else None
    store = str(store_id).strip() if store_id is not None else None
    if staff == "" or store == "":
        raise ValueError("Scope IDs must not be blank")
    if not staff and not store and not all_sites:
        raise ValueError("staff_id or store_id is required")
    return staff, store


def _metadata(staff, store, include_hmk):
    return {"staff_id": staff, "store_id": store,
            "assignment_basis": "Customer.RevenueStaffId",
            "site_basis": "Order.WarehouseId -> Warehouse.SiteId",
            "include_hmk": bool(include_hmk), "combined_scope": "intersection"}


def _page(limit, offset):
    return max(1, min(int(limit), 100)), max(0, min(int(offset), 100000))


def _connection():
    conn = _get_pos_conn()
    try:
        conn.execute("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        conn.execute("SET LOCAL statement_timeout = '30s'")
    except Exception:
        conn.close()
        raise
    return conn


def _customer_filter(staff, include_hmk):
    conditions = ['c."DeleteAt" IS NULL']
    params = []
    if staff:
        conditions.append('c."RevenueStaffId"::text = %s')
        params.append(staff)
    if not include_hmk:
        conditions.append('COALESCE(c."IsHmkCustomer", FALSE) = FALSE')
    return conditions, params


_VALID_ORDER = '''o."DeleteAt" IS NULL AND o."CancelAt" IS NULL
    AND o."ApproveAt" IS NOT NULL AND o."Type" IN (1, 2)'''
_ORDER_JOINS = '''JOIN "Warehouse" w ON w."Id" = o."WarehouseId"
    AND w."DeleteAt" IS NULL
    JOIN "Customer" c ON c."Id" = o."CustomerId"'''


def query_employee_customers(staff_id=None, include_hmk=False, limit=50,
                             offset=0, search=None, *, store_id=None, all_sites=False):
    """List current assignments, optionally intersected with valid branch orders."""
    staff, store = _scope(staff_id, store_id, all_sites)
    limit, offset = _page(limit, offset)
    conditions, params = _customer_filter(staff, include_hmk)
    if store:
        conditions.append(f'''EXISTS (
            SELECT 1 FROM "Order" o
            JOIN "Warehouse" w ON w."Id" = o."WarehouseId"
             AND w."DeleteAt" IS NULL
            WHERE o."CustomerId" = c."Id" AND {_VALID_ORDER}
              AND w."SiteId"::text = %s)''')
        params.append(store)
    if search is not None and str(search).strip():
        conditions.append('(c."Code" ILIKE %s OR c."Name" ILIKE %s)')
        term = "%" + str(search).strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        params.extend([term, term])
    base = 'FROM "Customer" c WHERE ' + " AND ".join(conditions)
    conn = _connection()
    try:
        count = int(conn.execute("SELECT COUNT(*) " + base, params).fetchone()[0])
        rows = conn.execute('''SELECT c."Id"::text, c."Code", c."Name",
            c."RevenueStaffId"::text, c."FollowStaffId"::text,
            COALESCE(c."IsHmkCustomer", FALSE), c."SaleZoneId"::text ''' + base +
            ' ORDER BY c."Code", c."Id" LIMIT %s OFFSET %s',
            [*params, limit, offset]).fetchall()
    finally:
        conn.close()
    customers = [dict(zip(("id", "code", "name", "assigned_staff_id",
                          "follow_staff_id", "is_hmk_customer", "sale_zone_id"), row))
                 for row in rows]
    return {"metric": "employee_customers", "source": "POS.Customer",
            "scope": _metadata(staff, store, include_hmk),
            "assignment_basis": "Customer.RevenueStaffId", "total_count": count,
            "totals": {"customers": count}, "rows": customers,
            "limit": limit, "offset": offset, "returned": len(customers)}


def query_scoped_receipts(date_from, date_to, staff_id=None, store_id=None,
                          include_hmk=False, limit=50, offset=0, *, all_sites=False):
    """Sum scoped collections over inclusive local calendar dates."""
    staff, store = _scope(staff_id, store_id, all_sites)
    start, end = date.fromisoformat(date_from), date.fromisoformat(date_to)
    if not 1 <= (end - start).days + 1 <= 366:
        raise ValueError("Inclusive date range must be at most 366 days and date_to >= date_from")
    try:
        end_exclusive = end + timedelta(days=1)
    except OverflowError as exc:
        raise ValueError("date_to must allow a next-day exclusive boundary") from exc
    limit, offset = _page(limit, offset)
    conditions, params = _customer_filter(staff, include_hmk)
    if store:
        conditions.append('w."SiteId"::text = %s')
        params.append(store)
    # Preference is per order across all dates, not just this reporting window.
    cte = f'''WITH allocate_lines AS (
        SELECT poi."Id" AS allocation_id, po."Id" AS receipt_id,
            po."Code" AS receipt_code, po."IssueAt" AS issued_at,
            poi."OrderId" AS order_id, poi."PaidAmount"::numeric AS amount,
            'Allocate'::text AS source_type
        FROM "PaymentOrderItem" poi
        JOIN "PaymentOrder" po ON po."Id" = poi."PaymentOrderId"
        WHERE poi."CancelAt" IS NULL AND poi."DeleteAt" IS NULL
          AND poi."PaidAmount" > 0
          AND po."CancelAt" IS NULL AND po."DeleteAt" IS NULL
          AND po."CompleteAt" IS NOT NULL AND po."DocumentType" = %s
          AND po."IssueAt" >= (%s::date::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh')
          AND po."IssueAt" < (%s::date::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh')
    ), legacy_receive_lines AS (
        SELECT NULL::uuid AS allocation_id, po."Id" AS receipt_id,
            po."Code" AS receipt_code, po."IssueAt" AS issued_at,
            po."ObjectId" AS order_id, po."PaidAmount"::numeric AS amount,
            'Receive_fallback'::text AS source_type
        FROM "PaymentOrder" po
        WHERE po."DocumentType" = %s AND po."ObjectType" = 1
          AND po."ObjectId" IS NOT NULL AND po."PaidAmount" > 0
          AND po."CancelAt" IS NULL AND po."DeleteAt" IS NULL
          AND po."CompleteAt" IS NOT NULL
          AND po."IssueAt" >= (%s::date::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh')
          AND po."IssueAt" < (%s::date::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh')
          AND NOT EXISTS (
                  SELECT 1 FROM "PaymentOrderItem" ai
                  JOIN "PaymentOrder" ap ON ap."Id" = ai."PaymentOrderId"
                  WHERE ai."OrderId" = po."ObjectId"
                    AND ai."CancelAt" IS NULL AND ai."DeleteAt" IS NULL
                    AND ai."PaidAmount" > 0
                    AND ap."DocumentType" = %s
                    AND ap."CancelAt" IS NULL AND ap."DeleteAt" IS NULL
                    AND ap."CompleteAt" IS NOT NULL)
    ), receipt_lines AS (
        SELECT * FROM allocate_lines
        UNION ALL
        SELECT * FROM legacy_receive_lines
    ), eligible_receipts AS (
        SELECT line.*, o."Code" AS order_code,
            c."Code" AS customer_code, c."Name" AS customer_name,
            w."SiteId"::text AS store_id
        FROM receipt_lines line
        JOIN "Order" o ON o."Id" = line.order_id
        {_ORDER_JOINS}
        WHERE {_VALID_ORDER} AND {' AND '.join(conditions)}
    )'''
    args = [PAYMENT_COLLECTION_DOCUMENT_TYPE, start, end_exclusive,
            PAYMENT_RECEIVE_DOCUMENT_TYPE, start, end_exclusive,
            PAYMENT_COLLECTION_DOCUMENT_TYPE, *params]
    conn = _connection()
    try:
        total = conn.execute(cte + '''SELECT COUNT(*), COUNT(DISTINCT receipt_id),
            COUNT(DISTINCT order_id), COALESCE(SUM(amount), 0)
            FROM eligible_receipts''', args).fetchone()
        rows = conn.execute(cte + '''SELECT allocation_id::text, receipt_id::text,
            receipt_code, order_code, customer_code, customer_name, store_id,
            (issued_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::text, source_type, amount
            FROM eligible_receipts ORDER BY issued_at DESC, receipt_id, allocation_id
            LIMIT %s OFFSET %s''', [*args, limit, offset]).fetchall()
    finally:
        conn.close()
    receipts = [dict(zip(("allocation_id", "receipt_id", "receipt_code", "order_code",
                         "customer_code", "customer_name", "store_id", "issued_at",
                         "source_type", "amount"), row)) for row in rows]
    for row in receipts:
        row["amount"] = float(row["amount"] or 0)
    return {"metric": "scoped_receipts",
            "source": "POS.PaymentOrderItem -> PaymentOrder, Order, Warehouse, Customer",
            "scope": _metadata(staff, store, include_hmk),
            "period": {"date_from": start.isoformat(), "date_to": end.isoformat(),
                       "end_exclusive": False, "date_to_inclusive": True,
                       "exclusive_end": end_exclusive.isoformat(),
                       "timezone": "Asia/Ho_Chi_Minh"},
            "document_types": {"allocate": PAYMENT_COLLECTION_DOCUMENT_TYPE,
                               "receive": PAYMENT_RECEIVE_DOCUMENT_TYPE},
            "formula": "Allocate uses PaymentOrderItem.PaidAmount; direct single-order Receive uses PaymentOrder.PaidAmount only without valid Allocate across all dates. Receive items are not queried.",
            "total_count": int(total[0]), "total_amount": float(total[3]),
            "totals": {"allocations": int(total[0]), "receipts": int(total[1]),
                       "orders": int(total[2]), "amount": float(total[3])},
            "rows": receipts, "limit": limit, "offset": offset, "returned": len(receipts)}


def query_scoped_customer_debt(customer_code, store_id=None, include_hmk=False,
                               *, staff_id=None, all_sites=False):
    """Return scoped order balances, never the customer's global debt ledger."""
    staff, store = _scope(staff_id, store_id, all_sites)
    code = str(customer_code).strip() if customer_code is not None else ""
    if not code:
        raise ValueError("customer_code is required")
    conditions, params = _customer_filter(staff, include_hmk)
    conditions.append('c."Code" = %s')
    params.append(code)
    order_scope = _VALID_ORDER
    if store:
        order_scope += ' AND w."SiteId"::text = %s'
        params.append(store)
    where = " AND ".join(conditions)
    conn = _connection()
    try:
        matches = conn.execute(f'''SELECT c."Id"::text, c."Code", c."Name"
            FROM "Customer" c WHERE {where}
            AND EXISTS (SELECT 1 FROM "Order" o
                JOIN "Warehouse" w ON w."Id" = o."WarehouseId"
                 AND w."DeleteAt" IS NULL
                WHERE o."CustomerId" = c."Id" AND {order_scope})
            ORDER BY c."Id" LIMIT 2''', params).fetchall()
        if len(matches) != 1:
            return {"error": "Customer unavailable in caller scope", "code": 403}
        balances = conn.execute(f'''SELECT ws."Code", COUNT(*),
            COALESCE(SUM(o."LeftAmount"::numeric), 0)
            FROM "Order" o {_ORDER_JOINS}
            JOIN "WorkflowState" ws ON ws."Id" = o."StateId"
            WHERE {where} AND {order_scope} AND c."Id"::text = %s
              AND ws."Code" IN ('ORDER_COMPLETED', 'ORDER_CONFIRMED')
            GROUP BY ws."Code"''', [*params, matches[0][0]]).fetchall()
    finally:
        conn.close()
    by_state = {row[0]: {"orders": int(row[1]), "left_amount": float(row[2])}
                for row in balances}
    return {"metric": "scoped_customer_order_balances",
            "source": "POS.Order.LeftAmount, WorkflowState, Warehouse, Customer",
            "scope": _metadata(staff, store, include_hmk),
            "customer": dict(zip(("id", "code", "name"), matches[0])),
            "completed": by_state.get("ORDER_COMPLETED", {"orders": 0, "left_amount": 0}),
            "confirmed": by_state.get("ORDER_CONFIRMED", {"orders": 0, "left_amount": 0}),
            "reconciliation_required": True,
            "caveat": "Scoped order LeftAmount only, not reconciled customer ledger debt. Confirmed orders are not delivered debt. Global CashDebt is not queried or disclosed."}
