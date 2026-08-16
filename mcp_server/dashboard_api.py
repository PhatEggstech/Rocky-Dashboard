# -*- coding: utf-8 -*-
"""Read-only client for the Rocky Lens dashboard API.

The dashboard UI is the source of truth for its overview widgets.  This
module deliberately returns the API payload without recomputing or rounding
the metrics in MCP, so Claude sees the same contract as the dashboard.
"""
from __future__ import annotations

from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from .config import (
    ROCKY_DASHBOARD_API_BASE_URL,
    ROCKY_DASHBOARD_API_TOKEN,
    ROCKY_DASHBOARD_IDENTITY_BASE_URL,
    ROCKY_DASHBOARD_PASSWORD,
    ROCKY_DASHBOARD_USERNAME,
)

VN_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")
DEFAULT_TIMEOUT_SECONDS = 20.0
_access_token = ""
_refresh_token = ""

# Read-only Dashboard endpoints. Sync, backfill, layout and other write
# endpoints are deliberately absent from this allow-list.
DASHBOARD_READ_METRICS: dict[str, tuple[str, str]] = {
    "order_by_time": ("/Admin/Dashboard/Order/ByTime", "common"),
    "order_by_staff": ("/Admin/Dashboard/Order/ByStaff", "common"),
    "order_by_state": ("/Admin/Dashboard/Order/ByStateOrder", "common"),
    "revenue_details": ("/Admin/Dashboard/Revenue/Details", "revenue_list"),
    "revenue_orders": ("/Admin/Dashboard/Revenue/Orders", "revenue_list"),
    "revenue_return_orders": ("/Admin/Dashboard/Revenue/ReturnOrders", "revenue_list"),
    "revenue_by_staff": ("/Admin/Dashboard/Revenue/SalesByRevenueStaff", "revenue_staff"),
    "revenue_by_staff_details": ("/Admin/Dashboard/Revenue/SalesByRevenueStaff/Details", "revenue_staff_details"),
    "revenue_by_product": ("/Admin/Dashboard/Revenue/SalesByProductItem", "revenue_product"),
    "revenue_by_product_details": ("/Admin/Dashboard/Revenue/SalesByProductItem/Details", "revenue_product_details"),
    "customer_overview": ("/Admin/Dashboard/Customer/Overview", "common"),
    "customer_by_province": ("/Admin/Dashboard/Customer/ByProvince", "common"),
    "customer_by_order": ("/Admin/Dashboard/Customer/ByOrder", "common"),
    "customer_birthday": ("/Admin/Dashboard/Customer/Birthday", "common"),
    "customer_no_interaction": ("/Admin/Dashboard/Customer/NoInteraction", "common"),
    "product_by_quantity": ("/Admin/Dashboard/Product/ByQuantity", "common"),
    "product_by_revenue": ("/Admin/Dashboard/Product/ByRevenue", "common"),
    "picker_overview": ("/Admin/Dashboard/Picker/Overview", "common"),
    "picker_average_time": ("/Admin/Dashboard/Picker/AverageTime", "common"),
    "picker_leaderboard": ("/Admin/Dashboard/Picker/LeaderBoard", "common"),
    "picker_heatmap": ("/Admin/Dashboard/Picker/Heatmap", "common"),
    "app_picker_average_time": ("/Admin/Dashboard/AppPicker/AverageTime", "common"),
    "app_picker_productivity": ("/Admin/Dashboard/AppPicker/Productivity", "common"),
    "app_picker_completed_by_staff": ("/Admin/Dashboard/AppPicker/CompletedByStaff", "common"),
    "app_picker_ranking": ("/Admin/Dashboard/AppPicker/Ranking", "common"),
}


def _epoch_millis(value: date, end_of_day: bool = False) -> int:
    """Convert a Vietnam-local date to the millisecond API contract."""
    local_time = time.max if end_of_day else time.min
    return int(datetime.combine(value, local_time, tzinfo=VN_TIMEZONE).timestamp() * 1000)


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Ngày phải có định dạng YYYY-MM-DD: {value!r}") from exc


def _base_result(
    metric: str,
    date_from: str,
    date_to: str,
    period_type: int,
    site_ids: list[str] | None,
    staff_ids: list[str] | None,
) -> dict[str, Any]:
    return {
        "metric": metric,
        "source": "rocky_dashboard_api",
        "timezone": "Asia/Ho_Chi_Minh",
        "period": {"date_from": date_from, "date_to": date_to},
        "request": {
            "periodType": period_type,
            "startAt": _epoch_millis(_parse_date(date_from)),
            "endAt": _epoch_millis(_parse_date(date_to), end_of_day=True),
            "siteIds": site_ids,
            "staffIds": staff_ids,
        },
        "formula_note": "Nguyên payload từ Rocky Lens Admin Dashboard API; MCP không tự tính lại.",
    }


def _login() -> tuple[str, str, dict[str, Any] | None]:
    """Sign in using credentials supplied only through the local environment."""
    if not ROCKY_DASHBOARD_USERNAME or not ROCKY_DASHBOARD_PASSWORD:
        return "", "", {
            "error": "Chưa cấu hình dashboard API token hoặc cặp đăng nhập local",
            "required_env": [
                "ROCKY_DASHBOARD_API_TOKEN",
                "ROCKY_DASHBOARD_USERNAME",
                "ROCKY_DASHBOARD_PASSWORD",
            ],
        }
    url = f"{ROCKY_DASHBOARD_IDENTITY_BASE_URL.rstrip('/')}/Identity/Login/Password"
    try:
        response = httpx.post(
            url,
            headers={"appCode": "ROCKY", "Accept": "application/json"},
            json={"username": ROCKY_DASHBOARD_USERNAME, "password": ROCKY_DASHBOARD_PASSWORD},
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        return "", "", {"error": "Không gọi được endpoint đăng nhập dashboard", "detail": str(exc)}
    if response.status_code >= 400:
        return "", "", {"error": "Đăng nhập dashboard thất bại", "http_status": response.status_code}
    try:
        body = response.json()
    except ValueError:
        return "", "", {"error": "Dashboard login trả về dữ liệu không hợp lệ"}
    data = body.get("data") if isinstance(body, dict) else None
    access = data.get("accessToken", "") if isinstance(data, dict) else ""
    refresh = data.get("refreshToken", "") if isinstance(data, dict) else ""
    if not access:
        return "", "", {"error": "Dashboard login không trả accessToken"}
    return access, refresh, None


def _get_access_token(force_login: bool = False) -> tuple[str, dict[str, Any] | None]:
    global _access_token, _refresh_token
    if ROCKY_DASHBOARD_API_TOKEN:
        return ROCKY_DASHBOARD_API_TOKEN, None
    if not force_login and _access_token:
        return _access_token, None
    access, refresh, error = _login()
    if error:
        return "", error
    _access_token, _refresh_token = access, refresh
    return _access_token, None


def _post(path: str, payload: dict[str, Any]) -> tuple[int, Any]:
    if not ROCKY_DASHBOARD_API_BASE_URL:
        return 0, {"error": "ROCKY_DASHBOARD_API_BASE_URL chưa được cấu hình"}
    token, auth_error = _get_access_token()
    if auth_error:
        return 0, auth_error

    url = f"{ROCKY_DASHBOARD_API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    try:
        response = httpx.post(
            url,
            json=payload,
            headers=headers,
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        return 0, {"error": "Không gọi được Rocky Lens dashboard API", "detail": str(exc)}

    if response.status_code == 401 and not ROCKY_DASHBOARD_API_TOKEN and ROCKY_DASHBOARD_USERNAME:
        token, auth_error = _get_access_token(force_login=True)
        if auth_error:
            return 0, auth_error
        headers["Authorization"] = f"Bearer {token}"
        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=DEFAULT_TIMEOUT_SECONDS)
        except httpx.HTTPError as exc:
            return 0, {"error": "Không gọi được Rocky Lens dashboard API", "detail": str(exc)}

    try:
        body = response.json()
    except ValueError:
        body = {"raw_text": response.text[:2000]}
    return response.status_code, body


def query_dashboard_order_overview(
    date_from: str,
    date_to: str,
    site_ids: list[str] | None = None,
    staff_ids: list[str] | None = None,
    period_type: int = 1,
) -> dict[str, Any]:
    """Return the exact dashboard Order/Overview response for a date range."""
    result = _base_result(
        "dashboard_order_overview", date_from, date_to, period_type, site_ids, staff_ids
    )
    payload = {
        "periodType": period_type,
        "startAt": result["request"]["startAt"],
        "endAt": result["request"]["endAt"],
        "siteIds": site_ids,
        "staffIds": staff_ids,
    }
    status, body = _post("/Admin/Dashboard/Order/Overview", payload)
    result["http_status"] = status
    if status == 0 or status >= 400:
        result["ok"] = False
        result["error"] = body
    else:
        result["ok"] = True
        result["data"] = body
    return result


def query_dashboard_order_by_site(
    date_from: str,
    date_to: str,
    site_ids: list[str] | None = None,
    period_type: int = 1,
) -> dict[str, Any]:
    """Return the exact dashboard Order/BySite response for a date range."""
    result = _base_result(
        "dashboard_order_by_site", date_from, date_to, period_type, site_ids, None
    )
    payload = {
        "periodType": period_type,
        "startAt": result["request"]["startAt"],
        "endAt": result["request"]["endAt"],
        "siteIds": site_ids,
    }
    status, body = _post("/Admin/Dashboard/Order/BySite", payload)
    result["http_status"] = status
    if status == 0 or status >= 400:
        result["ok"] = False
        result["error"] = body
    else:
        result["ok"] = True
        result["data"] = body
    return result


def query_dashboard_revenue(
    date_from: str,
    date_to: str,
    site_ids: list[str] | None = None,
    period_type: int = 1,
) -> dict[str, Any]:
    """Return the exact Revenue dashboard payload, including HMK/Other/returns."""
    result = _base_result(
        "dashboard_revenue", date_from, date_to, period_type, site_ids, None
    )
    payload = {
        "periodType": period_type,
        "startAt": result["request"]["startAt"],
        "endAt": result["request"]["endAt"],
        "siteIds": site_ids,
    }
    status, body = _post("/Admin/Dashboard/Revenue", payload)
    result["http_status"] = status
    if status == 0 or status >= 400:
        result["ok"] = False
        result["error"] = body
    else:
        result["ok"] = True
        result["data"] = body
        # Select, rather than recompute, the exact cards displayed by the
        # Dashboard's default "all" row. This gives clients one unambiguous
        # place to read UI metrics while preserving the full raw payload.
        all_summary = (
            body.get("data", {}).get("summary", {}).get("all", {})
            if isinstance(body, dict)
            else {}
        )
        if isinstance(all_summary, dict):
            result["dashboard_summary"] = {
                "scope": "summary.all",
                "total_revenue": all_summary.get("totalRevenue"),
                "hmk_revenue": all_summary.get("hmkRevenue"),
                "other_revenue": all_summary.get("otherRevenue"),
                "sales_orders": all_summary.get("numOrder"),
                "return_orders": all_summary.get("numReturnOrder"),
            }
        result["source_snapshot_at"] = datetime.now(VN_TIMEZONE).isoformat(
            timespec="seconds"
        )
    return result


def query_dashboard_sales_by_customer(
    date_from: str,
    date_to: str,
    top_n: int = 10,
) -> dict[str, Any]:
    """Mirror the Sales by Customer dashboard cards and its Top N table."""
    if not 1 <= top_n <= 100:
        raise ValueError("top_n must be between 1 and 100")
    result = _base_result(
        "dashboard_sales_by_customer", date_from, date_to, 1, None, None
    )
    payload = {
        "fromDate": result["request"]["startAt"],
        "toDate": result["request"]["endAt"],
        "page": 1,
        "size": top_n,
    }
    status, body = _post("/Admin/Dashboard/Revenue/SalesByCustomer", payload)
    result["http_status"] = status
    if status == 0 or status >= 400:
        result["ok"] = False
        result["error"] = body
        return result

    rows = body.get("data", []) if isinstance(body, dict) else []
    meta = body.get("meta", {}) if isinstance(body, dict) else {}
    result["ok"] = True
    result["data"] = body
    # These cards on Rocky Lens are derived from the currently selected Top N,
    # while the customer count comes from the response's total row count.
    result["dashboard_summary"] = {
        "top_n": top_n,
        "total_revenue": sum((row.get("totalRevenue") or 0) for row in rows),
        "customer_count": meta.get("total"),
        "num_order": sum((row.get("numOrder") or 0) for row in rows),
        "num_return_order": sum((row.get("numReturnOrder") or 0) for row in rows),
    }
    return result


def query_dashboard_debt_overview(
    date_from: str,
    date_to: str,
    customer_ids: list[str] | None = None,
    payment_method_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Return the Dashboard debt widgets without substituting POS calculations."""
    result = _base_result("dashboard_debt_overview", date_from, date_to, 1, None, None)
    request = result["request"]
    recovery_payload = {
        "startAt": request["startAt"],
        "endAt": request["endAt"],
        "customerIds": customer_ids,
    }
    revenue_payload = {
        "issueAt": {"from": request["startAt"], "to": request["endAt"]},
        "customerIds": customer_ids,
        "paymentMethodIds": payment_method_ids,
    }
    recovery_status, recovery_body = _post(
        "/Admin/DebtDashboard/RecoveryRate/Statistic", recovery_payload
    )
    revenue_status, revenue_body = _post(
        "/Admin/DebtDashboard/Revenue/Statistic", revenue_payload
    )
    result["http_status"] = {"recovery": recovery_status, "revenue": revenue_status}
    result["request_payload"] = {
        "recovery": recovery_payload,
        "revenue": revenue_payload,
    }
    if any(status == 0 or status >= 400 for status in (recovery_status, revenue_status)):
        result["ok"] = False
        result["error"] = {"recovery": recovery_body, "revenue": revenue_body}
        return result

    recovery = recovery_body.get("data", recovery_body) if isinstance(recovery_body, dict) else recovery_body
    revenue = revenue_body.get("data", revenue_body) if isinstance(revenue_body, dict) else revenue_body
    result["ok"] = True
    result["data"] = {"recovery": recovery_body, "revenue": revenue_body}
    result["dashboard_summary"] = {
        "total_previous_balance": recovery.get("totalPreviousBalance") if isinstance(recovery, dict) else None,
        "total_debt_amount": recovery.get("totalDebtAmount") if isinstance(recovery, dict) else None,
        "total_paid_amount": recovery.get("totalPaidAmount") if isinstance(recovery, dict) else None,
        "recovery_debt_rate": recovery.get("recoverDebtRate") if isinstance(recovery, dict) else None,
        "revenue_total_amount": revenue.get("totalAmount") if isinstance(revenue, dict) else None,
    }
    return result


def query_dashboard_debt_customers(
    date_from: str,
    date_to: str,
    customer_ids: list[str] | None = None,
    page: int = 1,
    size: int = 20,
) -> dict[str, Any]:
    """Return the paged customer-debt list from the Dashboard API."""
    if not 1 <= page <= 10_000 or not 1 <= size <= 100:
        raise ValueError("page must be positive and size must be between 1 and 100")
    result = _base_result("dashboard_debt_customers", date_from, date_to, 1, None, None)
    request = result["request"]
    payload = {
        "startAt": request["startAt"],
        "endAt": request["endAt"],
        "customerIds": customer_ids,
        "page": page,
        "size": size,
    }
    status, body = _post("/Admin/DebtDashboard/CustomerDebt/GetPage", payload)
    result["http_status"] = status
    result["request_payload"] = payload
    if status == 0 or status >= 400:
        result["ok"] = False
        result["error"] = body
    else:
        result["ok"] = True
        result["data"] = body
    return result


def query_dashboard_metric(
    metric: str,
    date_from: str,
    date_to: str,
    period_type: int = 1,
    site_ids: list[str] | None = None,
    staff_ids: list[str] | None = None,
    customer_ids: list[str] | None = None,
    province_codes: list[str] | None = None,
    days: int | None = None,
    staff_count: int | None = None,
    customer_id: str | None = None,
    revenue_staff_id: str | None = None,
    revenue_staff_ids: list[str] | None = None,
    product_item_id: str | None = None,
    product_item_ids: list[str] | None = None,
    order_type: int | None = None,
    status: int | None = None,
    page: int = 1,
    size: int = 20,
) -> dict[str, Any]:
    """Call a named allow-listed read-only Dashboard metric."""
    try:
        path, payload_kind = DASHBOARD_READ_METRICS[metric]
    except KeyError as exc:
        raise ValueError(f"Unsupported dashboard metric: {metric}") from exc
    if not 1 <= page <= 10_000 or not 1 <= size <= 100:
        raise ValueError("page must be positive and size must be between 1 and 100")

    result = _base_result(metric, date_from, date_to, period_type, site_ids, staff_ids)
    request = result["request"]
    if payload_kind == "revenue_list":
        payload = {
            "fromDate": request["startAt"],
            "toDate": request["endAt"],
            "page": page,
            "size": size,
            "status": 1 if status is None else status,
        }
        optional = {
            "customerId": customer_id,
            "revenueStaffId": revenue_staff_id,
            "type": order_type,
        }
        payload.update({key: value for key, value in optional.items() if value is not None})
    elif payload_kind == "revenue_staff":
        payload = {
            "fromDate": request["startAt"],
            "toDate": request["endAt"],
            "page": page,
            "size": size,
            "status": 0 if status is None else status,
        }
        if revenue_staff_ids is not None:
            payload["revenueStaffIds"] = revenue_staff_ids
        if order_type is not None:
            payload["type"] = order_type
    elif payload_kind == "revenue_staff_details":
        if not revenue_staff_id:
            raise ValueError("revenue_staff_id is required for revenue_by_staff_details")
        payload = {
            "fromDate": request["startAt"],
            "toDate": request["endAt"],
            "revenueStaffId": revenue_staff_id,
            "page": page,
            "size": size,
            "status": 0 if status is None else status,
        }
        if order_type is not None:
            payload["type"] = order_type
    elif payload_kind == "revenue_product":
        payload = {
            "fromDate": request["startAt"],
            "toDate": request["endAt"],
            "page": page,
            "size": size,
            "status": 0 if status is None else status,
        }
        if product_item_ids is not None:
            payload["productItemIds"] = product_item_ids
    elif payload_kind == "revenue_product_details":
        if not product_item_id:
            raise ValueError("product_item_id is required for revenue_by_product_details")
        payload = {
            "fromDate": request["startAt"],
            "toDate": request["endAt"],
            "productItemId": product_item_id,
            "page": page,
            "size": size,
            "status": 0 if status is None else status,
        }
    else:
        payload = {
            "periodType": period_type,
            "startAt": request["startAt"],
            "endAt": request["endAt"],
            "siteIds": site_ids,
            "staffIds": staff_ids,
            "customerIds": customer_ids,
            "provinceCodes": province_codes,
            "days": days,
            "staffCount": staff_count,
        }
    status_code, body = _post(path, payload)
    result["http_status"] = status_code
    result["request_payload"] = payload
    if status_code == 0 or status_code >= 400:
        result["ok"] = False
        result["error"] = body
    else:
        result["ok"] = True
        result["data"] = body
    return result
