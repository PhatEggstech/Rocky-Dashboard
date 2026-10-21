"""Read-only order history; callers must supply their authorized Staff.Id."""
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from .tools import _get_pos_conn


_ASSIGNMENTS = {
    "revenue": ("RevenueStaffId",),
    "management": ("RevenueStaffId", "AdminProcessorStaffId"),
    "shipper": ("ShipperId",),
}
_LOCAL_TZ = timezone(timedelta(hours=7))


def _local_today():
    return datetime.now(_LOCAL_TZ).date()


def _date(value):
    if type(value) is date:
        return value
    if not isinstance(value, str):
        raise ValueError("Dates must be ISO local calendar dates")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Dates must be ISO local calendar dates") from exc
    if parsed.isoformat() != value:
        raise ValueError("Dates must use YYYY-MM-DD")
    return parsed


def query_assigned_orders(staff_id, assignment="revenue", date_from=None,
                          date_to=None, code=None, limit=50, offset=0):
    """List orders assigned to a trusted staff UUID, never current customer owners."""
    if not isinstance(assignment, str) or assignment not in _ASSIGNMENTS:
        raise ValueError("Unknown assignment")
    try:
        staff = str(UUID(str(staff_id).strip()))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("staff_id must be a nonempty Staff.Id UUID") from exc
    if UUID(staff).int == 0:
        raise ValueError("staff_id must not be the empty UUID")
    end = _local_today() if date_to is None else _date(date_to)
    start = end - timedelta(days=29) if date_from is None else _date(date_from)
    if not 1 <= (end - start).days + 1 <= 366 or end == date.max:
        raise ValueError("Date range must contain 1 to 366 inclusive local dates")
    limit, offset = max(1, min(int(limit), 100)), max(0, min(int(offset), 100000))
    if code is not None:
        if not isinstance(code, str) or not code.strip():
            raise ValueError("code must not be blank")
        code = code.strip()

    fields = _ASSIGNMENTS[assignment]
    scope = "(" + " OR ".join(f'o."{field}" = %s::uuid' for field in fields) + ")"
    conditions = [scope, 'o."DeleteAt" IS NULL',
                  '''o."IssueAt" >= (%s::date::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh')''',
                  '''o."IssueAt" < (%s::date::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh')''']
    params = [staff] * len(fields) + [start.isoformat(), (end + timedelta(days=1)).isoformat()]
    if code is not None:
        conditions.append('o."Code" = %s')
        params.append(code)
    base = 'FROM "Order" o WHERE ' + " AND ".join(conditions)
    keys = ("Id", "Code", "WarehouseId", "RevenueStaffId", "AdminProcessorStaffId",
            "ShipperId", "IssueAt", "CancelAt", "wsCode", "wsName", "NeedPayAmount",
            "PaidAmount", "LeftAmount", "customer_id", "customer_code", "customer_name")
    contact = ', c."Phone", c."FullAddress"' if assignment == "shipper" else ""
    conn = _get_pos_conn()
    try:
        conn.execute("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        conn.execute("SET LOCAL statement_timeout = '30s'")
        count = int(conn.execute("SELECT COUNT(*) " + base, params).fetchone()[0])
        rows = conn.execute('''SELECT o."Id"::text, o."Code", o."WarehouseId"::text,
            o."RevenueStaffId"::text, o."AdminProcessorStaffId"::text, o."ShipperId"::text,
            o."IssueAt"::text, o."CancelAt"::text, ws."Code", ws."Name",
            o."NeedPayAmount", o."PaidAmount", o."LeftAmount",
            c."Id"::text, c."Code", c."Name"''' + contact +
            ' FROM "Order" o LEFT JOIN "Customer" c ON c."Id" = o."CustomerId"'
            ' LEFT JOIN "WorkflowState" ws ON ws."Id" = o."StateId" WHERE ' +
            " AND ".join(conditions) + ' ORDER BY o."IssueAt" DESC, o."Id" DESC LIMIT %s OFFSET %s',
            [*params, limit, offset]).fetchall()
    finally:
        conn.close()
    result_rows = []
    for row in rows:
        item = dict(zip(keys + (("Phone", "FullAddress") if contact else ()), row))
        customer = {key: item.pop("customer_" + key.lower()) for key in ("Id", "Code", "Name")}
        if contact:
            customer.update({key: item.pop(key) for key in ("Phone", "FullAddress")})
            item["shipping_contact"] = customer
        else:
            item["Customer"] = customer
        item["status"] = "canceled" if item["CancelAt"] else item["wsCode"]
        result_rows.append(item)
    return {
        "source": "POS.Order, Customer, WorkflowState",
        "note": "History uses the order owner snapshot (assignment FKs to Staff.Id), not current customer ownership. No all-customer fallback. Order amounts are not collected cash.",
        "filters": {"staff_id": staff, "assignment": assignment,
                    "assignment_fields": ["Order." + field for field in fields],
                    "date_field": "Order.IssueAt", "date_from": start.isoformat(),
                    "date_to": end.isoformat(), "timezone": "Asia/Ho_Chi_Minh",
                    "code": code, "include_canceled": True, "limit": limit, "offset": offset},
        "summary": {"orders": count}, "total_count": count,
        "rows": result_rows, "returned": len(result_rows), "limit": limit, "offset": offset,
    }
