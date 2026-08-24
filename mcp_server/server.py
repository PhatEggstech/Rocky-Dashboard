# -*- coding: utf-8 -*-
"""MCP Server definition using FastMCP - with role-based authorization."""
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from fastmcp import FastMCP

from .prompts import SYSTEM_PROMPT
from .tools import (
    query_revenue,
    query_subtotal,
    query_sales_by_customer_type,
    query_return_exchange_requests,
    query_return_orders,
    query_debt,
    query_staff_revenue,
    query_orders,
    query_order_operations,
    query_inventory,
    query_customers,
    query_customer_sales,
    query_products,
    query_stores,
    explain_metric,
    query_raw_sql,
    list_tables,
    describe_table,
    list_specs,
    get_spec_content,
    get_schema_quick_context,
    search_specs,
    describe_pos_table,
    query_debt_recovery_rate,
    query_top_bad_debts,
    query_vip_revenue_drop_alerts,
    query_gross_net_sales,
    query_product_industry_sales,
    query_b2b_adoption_rate,
    query_gpm,
    query_npm,
    query_atv,
    query_upt,
    query_rps,
    query_remake_rate,
    query_picker_leaderboard,
    query_picker_efficiency,
    query_raw_pos_sql,
    query_telegram_mappings,
    trigger_send_debt_reminders,
)
from .dashboard_api import (
    query_dashboard_order_overview,
    query_dashboard_order_by_site,
    query_dashboard_revenue,
    query_dashboard_sales_by_customer,
    query_dashboard_metric,
    query_dashboard_debt_overview,
    query_dashboard_debt_customers,
)
from .auth import require_role, enforce_store_filter, enforce_staff_filter, get_current_user
from .wms_tools import (
    query_inventory_live,
    query_inventory_movements,
    query_outbound_deliveries,
    query_raw_wms_sql,
    query_warehouses_live,
    query_wms_health,
)

MCP_VERSION = "2026.08.17-disclaimer1"
VN_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")
RelativePeriod = Literal[
    "today", "yesterday", "this_week", "last_week", "this_month"
]

import functools
import time
import logging
import os

mcp = FastMCP(
    "Rocky Dashboard",
    instructions=SYSTEM_PROMPT,
    version=MCP_VERSION,
)


def _resolve_reporting_range(
    date_from: str | None,
    date_to: str | None,
    relative_period: RelativePeriod | None,
) -> tuple[str, str, str]:
    """Resolve relative periods on the server in Vietnam time."""
    today = datetime.now(VN_TIMEZONE).date()

    if relative_period and (date_from or date_to):
        raise ValueError(
            "Use either relative_period or date_from/date_to, not both"
        )

    if relative_period == "today":
        start = end = today
    elif relative_period == "yesterday":
        start = end = today - timedelta(days=1)
    elif relative_period == "this_week":
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
    elif relative_period == "last_week":
        end = today - timedelta(days=today.weekday() + 1)
        start = end - timedelta(days=6)
    elif relative_period == "this_month":
        start = today.replace(day=1)
        next_month = (
            start.replace(year=start.year + 1, month=1)
            if start.month == 12
            else start.replace(month=start.month + 1)
        )
        end = next_month - timedelta(days=1)
    elif relative_period:
        raise ValueError(f"Unsupported relative_period: {relative_period}")
    else:
        if not date_from and not date_to:
            start = end = today
        else:
            date_from = date_from or date_to
            date_to = date_to or date_from
            start = date.fromisoformat(date_from)
            end = date.fromisoformat(date_to)

    if end < start:
        raise ValueError("date_to must be on or after date_from")

    label = relative_period or "custom"
    return start.isoformat(), end.isoformat(), label


def _query_context(
    date_from: str,
    date_to: str,
    period_label: str,
    effective_store_id: str | None,
) -> dict:
    user = get_current_user()
    role = user.role if user else "anonymous"
    scoped_store = (
        str(user.store_id)
        if user and user.role != "admin" and user.store_id is not None
        else effective_store_id
    )
    return {
        "server_version": MCP_VERSION,
        "timezone": "Asia/Ho_Chi_Minh",
        "date_from": date_from,
        "date_to": date_to,
        "relative_period": period_label,
        "role": role,
        "scope": "single_store" if scoped_store else "all_stores",
        "effective_store_id": scoped_store,
    }

# Set up dedicated logger for tracking tool calls
tracker_logger = logging.getLogger("mcp_tracker")
# Avoid adding handlers multiple times
if not tracker_logger.handlers:
    log_dir = Path(os.environ.get("MCP_LOG_DIR", Path.cwd() / "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_dir / "mcp_tracking.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    tracker_logger.addHandler(handler)
    tracker_logger.setLevel(logging.INFO)

# Executive accounts get a deliberately small, read-only surface. Keep this
# check in the tracking wrapper so an unprotected tool cannot be exposed by a
# missing decorator elsewhere in this module.
BOD_ALLOWED_TOOLS = frozenset({
    "get_mcp_context",
    "explain",
    "get_revenue_by_source",
    "get_products",
    "get_dashboard_order_overview",
    "get_tinh_hinh_kinh_doanh",
    "get_dashboard_order_by_site",
    "get_dashboard_revenue",
    "get_dashboard_sales_by_customer",
    "get_dashboard_debt_overview",
})

# BOD can use aggregate Dashboard reports, but not raw SQL, warehouse data,
# purchase-cost data, payment receipt detail, or customer-level debt records.
# Return a useful alternative when Claude chooses a disallowed legacy tool.
_BOD_TOOL_ALTERNATIVES = {
    "get_customer_sales": ["get_dashboard_sales_by_customer"],
    "get_customers": ["get_dashboard_sales_by_customer"],
    "get_debt": ["get_dashboard_debt_overview"],
    "get_dashboard_debt_customers": ["get_dashboard_debt_overview"],
}

_DASHBOARD_TOOLS = frozenset({
    "get_revenue_by_source",
    "get_dashboard_order_overview",
    "get_tinh_hinh_kinh_doanh",
    "get_dashboard_order_by_site",
    "get_dashboard_revenue",
    "get_dashboard_sales_by_customer",
    "get_dashboard_debt_overview",
    "get_dashboard_debt_customers",
    "get_dashboard_metric",
})
_WMS_TOOLS = frozenset({
    "check_wms_health",
    "get_warehouses_live",
    "get_inventory_live",
    "get_inventory_movements",
    "get_outbound_deliveries",
    "query_raw_wms_sql_tool",
})
_RAW_OR_SCHEMA_TOOLS = frozenset({
    "query_raw_sql_tool",
    "query_raw_pos_sql_tool",
    "query_raw_wms_sql_tool",
    "list_tables_tool",
    "describe_table_tool",
    "get_schema_quick_context_tool",
    "search_schema_tool",
    "describe_pos_table_tool",
})


def _result_disclaimer(tool_name: str) -> dict:
    """Return a concise, source-specific caveat for every successful tool call."""
    if tool_name in _DASHBOARD_TOOLS:
        return {
            "type": "dashboard_snapshot",
            "message": (
                "Số liệu là snapshot read-only từ Rocky Lens Dashboard tại thời điểm truy vấn. "
                "Chỉ tiêu Tổng doanh thu dùng phạm vi Dashboard đang chọn; khi có cả "
                "HMK và Khác thì Tổng bao gồm cả hai nguồn."
            ),
            "reconciliation": "Dùng Dashboard Rocky Lens làm nguồn đối soát KPI UI; không dùng số này làm chứng từ kế toán cuối kỳ.",
        }
    if tool_name in _WMS_TOOLS:
        return {
            "type": "wms_live_snapshot",
            "message": (
                "Tồn kho và chuyển động kho là snapshot WMS live tại thời điểm truy vấn; "
                "có thể thay đổi sau nhập/xuất, kiểm kê hoặc đồng bộ."
            ),
            "reconciliation": "Xác nhận lại chứng từ kho và thời điểm chốt trước khi ra quyết định điều chuyển hoặc kiểm kê.",
        }
    if tool_name == "get_revenue_legacy":
        return {
            "type": "legacy_pos_reconciliation",
            "message": "Đây là đối soát cohort từ POS legacy, không phải chỉ tiêu hiển thị chính thức trên Dashboard Rocky Lens.",
            "reconciliation": "Không thay thế KPI Dashboard hoặc số liệu kế toán bằng kết quả này nếu chưa được Finance xác nhận.",
        }
    if tool_name in _RAW_OR_SCHEMA_TOOLS:
        return {
            "type": "technical_read_only_result",
            "message": "Kết quả là dữ liệu read-only phục vụ phân tích kỹ thuật; việc diễn giải nghiệp vụ cần đối chiếu quy tắc Dashboard/POS hiện hành.",
            "reconciliation": "Không sử dụng trực tiếp làm kết luận tài chính, tồn kho hoặc quyết định vận hành nếu chưa đối soát nguồn chuẩn.",
        }
    return {
        "type": "read_only_snapshot",
        "message": "Kết quả là snapshot read-only tại thời điểm truy vấn và có thể thay đổi khi dữ liệu nguồn được duyệt hoặc đồng bộ.",
        "reconciliation": "Đối chiếu nguồn nghiệp vụ phù hợp trước khi dùng cho chứng từ hoặc quyết định chính thức.",
    }


def _tool_failure(res: object) -> str | None:
    """Recognize structured tool failures before logging a false success."""
    if not isinstance(res, dict):
        return None
    if res.get("error"):
        return str(res["error"])
    if res.get("ok") is False:
        return "Tool returned ok=false"
    code = res.get("code")
    if isinstance(code, int) and code >= 400:
        return f"Tool returned code={code}"
    return None


def track_tool(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        tool_name = func.__name__
        start_time = time.time()
        # Include user info in tracking
        user = get_current_user()
        user_info = f"User: {user.name} ({user.role})" if user else "User: Anonymous"
        if user and user.role == "bod" and tool_name not in BOD_ALLOWED_TOOLS:
            alternatives = _BOD_TOOL_ALTERNATIVES.get(tool_name, [])
            result = {
                "error": "Permission denied. The BOD role may only use approved aggregate executive reports.",
                "code": 403,
                "user": user.name,
                "alternatives": alternatives,
                "allowed_aggregate_tools": sorted(BOD_ALLOWED_TOOLS),
            }
            tracker_logger.warning(
                f"[BLOCKED] Tool '{tool_name}' | {user_info} | BOD allow-list"
            )
            return result
        tracker_logger.info(f"[CALL] Tool '{tool_name}' | {user_info} | Args: {args} | Kwargs: {kwargs}")
        try:
            res = func(*args, **kwargs)
            duration = (time.time() - start_time) * 1000
            if isinstance(res, dict):
                failure = _tool_failure(res)
                if failure:
                    tracker_logger.error(
                        f"[FAILURE] Tool '{tool_name}' | Duration: {duration:.2f}ms | "
                        f"{user_info} | Err: {failure}"
                    )
                    return res
                # Check for permission errors
                if res.get("code") in (401, 403):
                    tracker_logger.warning(f"[BLOCKED] Tool '{tool_name}' | {user_info} | {res.get('error')}")
                    return res
                res.setdefault("disclaimer", _result_disclaimer(tool_name))
                res_info = f"Result keys: {list(res.keys())}"
            else:
                res_info = "non-dict result"
            tracker_logger.info(f"[SUCCESS] Tool '{tool_name}' | Duration: {duration:.2f}ms | {user_info} | {res_info}")
            return res
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            tracker_logger.error(f"[ERROR] Tool '{tool_name}' | Duration: {duration:.2f}ms | {user_info} | Err: {e}", exc_info=True)
            raise e
    return wrapper


# ===========================================================================
# ADMIN ONLY TOOLS (sensitive operations)
# ===========================================================================

@mcp.tool()
@track_tool
@require_role('admin')
def query_raw_sql_tool(sql: str) -> dict:
    """[ADMIN] Chạy câu lệnh SQL SELECT tùy ý (Read-only) trên database dashboard."""
    return query_raw_sql(sql)


@mcp.tool()
@track_tool
@require_role('admin')
def query_raw_pos_sql_tool(sql: str) -> dict:
    """[ADMIN] Chạy câu lệnh SQL SELECT tùy ý (Read-only) trên database POS gốc."""
    return query_raw_pos_sql(sql)


@mcp.tool()
@track_tool
@require_role('admin')
def query_raw_wms_sql_tool(sql: str) -> dict:
    """[ADMIN] Chạy một câu SELECT read-only trên database kho Rocky WMS."""
    return query_raw_wms_sql(sql)


@mcp.tool()
@track_tool
@require_role('admin')
def check_wms_health() -> dict:
    """[ADMIN] Kiểm tra kết nối trực tiếp tới database kho Rocky WMS."""
    return query_wms_health()


@mcp.tool()
@track_tool
@require_role('admin')
def get_warehouses_live() -> dict:
    """[ADMIN] Danh sách kho/site và tổng tồn hiện tại từ WMS."""
    return query_warehouses_live()


@mcp.tool()
@track_tool
@require_role('admin')
def get_inventory_live(
    warehouse_code: str | None = None,
    product_search: str | None = None,
    low_stock_only: bool = False,
    limit: int = 50,
) -> dict:
    """[ADMIN] Tồn kho trực tiếp theo kho hoặc sản phẩm; tự fallback cache khi WMS lỗi."""
    return query_inventory_live(warehouse_code, product_search, low_stock_only, limit)


@mcp.tool()
@track_tool
@require_role('admin')
def get_inventory_movements(
    date_from: str,
    date_to: str,
    warehouse_code: str | None = None,
    product_search: str | None = None,
    include_cancelled: bool = False,
    limit: int = 100,
) -> dict:
    """[ADMIN] Lịch sử nhập/xuất/điều chỉnh tồn kho trực tiếp từ WMS. Format ngày: YYYY-MM-DD."""
    return query_inventory_movements(date_from, date_to, warehouse_code, product_search, include_cancelled, limit)


@mcp.tool()
@track_tool
@require_role('admin')
def get_outbound_deliveries(
    date_from: str,
    date_to: str,
    warehouse_code: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> dict:
    """[ADMIN] Phiếu xuất kho theo ngày/kho/trạng thái từ WMS. Status: completed/cancelled/processing."""
    return query_outbound_deliveries(date_from, date_to, warehouse_code, status, limit)


@mcp.tool()
@track_tool
@require_role('admin')
def trigger_debt_reminders() -> dict:
    """[ADMIN] Kích hoạt khẩn cấp tiến trình quét nợ quá hạn và gửi nhắc nợ Telegram."""
    return trigger_send_debt_reminders()


# ===========================================================================
# ADMIN + MANAGER TOOLS (store-level data)
# ===========================================================================

@mcp.tool()
@track_tool
@require_role('admin', 'manager')
def get_debt(customer_name: str | None = None, date_from: str | None = None, date_to: str | None = None) -> dict:
    """Lấy công nợ khách hàng B2B. CurrentBalance âm = khách nợ."""
    return query_debt(customer_name, date_from, date_to)


@mcp.tool()
@track_tool
@require_role('admin', 'manager')
@enforce_store_filter
def get_inventory(category: str | None = None, dead_stock_only: bool = False) -> dict:
    """Lấy tồn kho. dead_stock_only=True để xem hàng chết (>90 ngày không bán)."""
    return query_inventory(category, dead_stock_only)


@mcp.tool()
@track_tool
@require_role('admin', 'manager')
@enforce_store_filter
def get_customers(segment: str | None = None, top_n: int = 10) -> dict:
    """Lấy khách hàng RFM. Segments: Champion, Loyal, At-Risk, Hibernating, Lost"""
    return query_customers(segment, top_n)


@mcp.tool()
@track_tool
@require_role('admin', 'manager', 'bod')
@enforce_store_filter
def get_customer_sales(
    date_from: str | None = None,
    date_to: str | None = None,
    top_n: int = 10,
    page: int = 1,
    page_size: int = 20,
    order_type: int | None = None,
    store_id: str | None = None,
    relative_period: RelativePeriod | None = None,
) -> dict:
    """Doanh số theo khách hàng giống màn Doanh số KH của Rocky Lens.

    dashboard_top_summary cộng Top N, còn all_customers_summary cộng toàn bộ.
    Dùng relative_period hoặc date_from/date_to.
    """
    resolved_from, resolved_to, period_label = _resolve_reporting_range(
        date_from, date_to, relative_period
    )
    result = query_customer_sales(
        resolved_from,
        resolved_to,
        top_n,
        page,
        page_size,
        order_type,
        store_id,
    )
    result["query_context"] = _query_context(
        resolved_from, resolved_to, period_label, store_id
    )
    return result


@mcp.tool()
@track_tool
@require_role('admin', 'manager')
@enforce_store_filter
def get_stores(date_from: str, date_to: str) -> dict:
    """Lấy performance từng cửa hàng."""
    return query_stores(date_from, date_to)


@mcp.tool()
@track_tool
@require_role('admin', 'manager')
def get_debt_recovery_rate(date_from: str | None = None, date_to: str | None = None) -> dict:
    """Tính toán tỷ lệ thu hồi nợ trung bình của các đại lý B2B."""
    return query_debt_recovery_rate(date_from, date_to)


@mcp.tool()
@track_tool
@require_role('admin', 'manager')
def get_top_bad_debts(limit: int = 10) -> dict:
    """Lấy danh sách các đại lý có số dư nợ xấu cao nhất."""
    return query_top_bad_debts(limit)


@mcp.tool()
@track_tool
@require_role('admin', 'manager')
def get_vip_revenue_drop_alerts(limit: int = 20) -> dict:
    """Cảnh báo sớm khách hàng VIP có doanh số sụt giảm."""
    return query_vip_revenue_drop_alerts(limit)


@mcp.tool()
@track_tool
@require_role('admin', 'manager')
def get_telegram_mappings() -> dict:
    """Xem danh sách nhân viên đã đăng ký nhận cảnh báo nợ qua Telegram Bot."""
    return query_telegram_mappings()


# ===========================================================================
# ALL ROLES - STORE-FILTERED TOOLS (data scoped by store_id)
# ===========================================================================

@mcp.tool()
@track_tool
@enforce_store_filter
def get_revenue_by_source(
    date_from: str | None = None,
    date_to: str | None = None,
    store_id: str | None = None,
    relative_period: RelativePeriod | None = None,
) -> dict:
    """[CHI TIET DOANH SO] Phan tach doanh so theo nguon: HMK vs Khac, App/Portal/System.

    CHI goi khi user yeu cau CU THE: 'phan tach doanh so theo nguon',
    'HMK bao nhieu', 'so sanh App vs Portal', 'revenue breakdown'.
    KHONG DUNG cho: 'tinh hinh kinh doanh', 'tong quan', 'hom nay the nao'.
    Neu user hoi tong quan → goi get_tinh_hinh_kinh_doanh thay vi tool nay.
    """
    resolved_from, resolved_to, period_label = _resolve_reporting_range(
        date_from, date_to, relative_period
    )
    site_ids = [str(store_id)] if store_id else None
    result = query_dashboard_revenue(resolved_from, resolved_to, site_ids, 1)
    result["compatibility_alias"] = "get_dashboard_revenue"
    result["query_context"] = _query_context(
        resolved_from, resolved_to, period_label, store_id
    )
    return result


@mcp.tool()
@track_tool
@enforce_store_filter
def get_revenue_legacy(
    date_from: str | None = None,
    date_to: str | None = None,
    store_id: str | None = None,
    relative_period: RelativePeriod | None = None,
) -> dict:
    """[LEGACY POS] Đối soát cohort đơn phát hành, không dùng cho KPI UI."""
    resolved_from, resolved_to, period_label = _resolve_reporting_range(
        date_from, date_to, relative_period
    )
    result = query_revenue(resolved_from, resolved_to, store_id)
    result["query_context"] = _query_context(
        resolved_from, resolved_to, period_label, store_id
    )
    return result


@mcp.tool()
@track_tool
@require_role('admin', 'manager', 'bod')
def get_dashboard_order_overview(
    date_from: str | None = None,
    date_to: str | None = None,
    site_ids: list[str] | None = None,
    staff_ids: list[str] | None = None,
    period_type: int = 1,
    relative_period: RelativePeriod | None = None,
) -> dict:
    """[TRANG TONG QUAN] 4 KPI chinh: So don, Gia tri don, Thuc thu, Con phai thu.

    Nen dung get_tinh_hinh_kinh_doanh thay vi tool nay (no gom nhieu data hon).
    Chi dung tool nay khi can RIENG 4 KPI ma khong can staff/site breakdown.
    Dung relative_period (today/yesterday/this_week/last_week/this_month) de
    server tu chot ngay theo gio Viet Nam.
    """
    resolved_from, resolved_to, period_label = _resolve_reporting_range(
        date_from, date_to, relative_period
    )
    user = get_current_user()
    if user and user.role != "admin" and user.store_id is not None:
        site_ids = [str(user.store_id)]
    result = query_dashboard_order_overview(
        resolved_from, resolved_to, site_ids, staff_ids, period_type
    )
    result["query_context"] = _query_context(
        resolved_from, resolved_to, period_label, site_ids[0] if site_ids and len(site_ids) == 1 else None
    )
    return result


@mcp.tool()
@track_tool
@require_role('admin', 'manager', 'bod')
def get_tinh_hinh_kinh_doanh(
    date_from: str | None = None,
    date_to: str | None = None,
    relative_period: RelativePeriod | None = None,
) -> dict:
    """Tinh hinh kinh doanh hom nay / tong quan kinh doanh Rocky.

    DEFAULT TOOL — goi tool nay khi user hoi bat ky cau nao lien quan:
    'tinh hinh kinh doanh', 'hom nay the nao', 'tong quan', 'overview',
    'bao cao', 'so lieu hom nay', 'cho toi biet tinh hinh'.
    Tra ve: 4 KPI (so don, gia tri, thuc thu, con phai thu) + doanh so theo site +
    top nhan vien. Day la trang TONG QUAN cua Rocky Lens Dashboard.
    """
    resolved_from, resolved_to, period_label = _resolve_reporting_range(
        date_from, date_to, relative_period
    )
    user = get_current_user()
    site_ids = (
        [str(user.store_id)]
        if user and user.role != "admin" and user.store_id is not None
        else None
    )

    overview = query_dashboard_order_overview(resolved_from, resolved_to, site_ids)
    by_site = query_dashboard_order_by_site(resolved_from, resolved_to, site_ids)
    # This tool represents the Dashboard overview. Use the dashboard staff
    # endpoint too, rather than silently mixing a POS-only staff calculation.
    staff = query_dashboard_metric(
        "order_by_staff", resolved_from, resolved_to, site_ids=site_ids
    )

    return {
        "metric": "business_summary",
        "source": "rocky_dashboard_api",
        "period": {"date_from": resolved_from, "date_to": resolved_to, "label": period_label},
        "overview": overview.get("data", {}) if overview.get("ok") else {"error": overview.get("error")},
        "by_site": by_site.get("data", {}) if by_site.get("ok") else {"error": by_site.get("error")},
        "staff": staff.get("data", {}) if staff.get("ok") else {"error": staff.get("error")},
        "query_context": _query_context(resolved_from, resolved_to, period_label, None),
    }


@mcp.tool()
@track_tool
@require_role('admin', 'manager', 'bod')
def get_dashboard_order_by_site(
    date_from: str | None = None,
    date_to: str | None = None,
    site_ids: list[str] | None = None,
    period_type: int = 1,
    relative_period: RelativePeriod | None = None,
) -> dict:
    """Doanh thu theo chi nhánh theo API Dashboard và lịch Việt Nam."""
    resolved_from, resolved_to, period_label = _resolve_reporting_range(
        date_from, date_to, relative_period
    )
    user = get_current_user()
    if user and user.role != "admin" and user.store_id is not None:
        site_ids = [str(user.store_id)]
    result = query_dashboard_order_by_site(resolved_from, resolved_to, site_ids, period_type)
    result["query_context"] = _query_context(
        resolved_from, resolved_to, period_label, site_ids[0] if site_ids and len(site_ids) == 1 else None
    )
    return result


@mcp.tool()
@track_tool
@require_role('admin', 'manager', 'bod')
def get_dashboard_revenue(
    date_from: str | None = None,
    date_to: str | None = None,
    site_ids: list[str] | None = None,
    period_type: int = 1,
    relative_period: RelativePeriod | None = None,
) -> dict:
    """Doanh số đúng theo trang Doanh số Rocky Lens.

    Trả nguyên payload gồm Tổng doanh số, HMK, Khác, số đơn bán và đơn trả.
    Không dùng cho các KPI Thực thu/Còn phải thu ở trang Tình hình kinh doanh.
    """
    resolved_from, resolved_to, period_label = _resolve_reporting_range(
        date_from, date_to, relative_period
    )
    user = get_current_user()
    if user and user.role != "admin" and user.store_id is not None:
        site_ids = [str(user.store_id)]
    result = query_dashboard_revenue(resolved_from, resolved_to, site_ids, period_type)
    result["query_context"] = _query_context(
        resolved_from, resolved_to, period_label, site_ids[0] if site_ids and len(site_ids) == 1 else None
    )
    return result


@mcp.tool()
@track_tool
@require_role('admin', 'manager', 'bod')
def get_dashboard_sales_by_customer(
    date_from: str | None = None,
    date_to: str | None = None,
    top_n: int = 10,
    relative_period: RelativePeriod | None = None,
) -> dict:
    """Doanh số khách hàng đúng theo trang Doanh số KH Rocky Lens.

    Tổng doanh số/số đơn/đơn trả được tính theo Top N đang chọn trên giao diện;
    số khách lấy từ tổng danh sách trả về bởi Dashboard API.
    """
    resolved_from, resolved_to, period_label = _resolve_reporting_range(
        date_from, date_to, relative_period
    )
    result = query_dashboard_sales_by_customer(resolved_from, resolved_to, top_n)
    result["query_context"] = _query_context(
        resolved_from, resolved_to, period_label, None
    )
    return result


@mcp.tool()
@track_tool
@require_role('admin', 'manager', 'bod')
def get_dashboard_debt_overview(
    date_from: str | None = None,
    date_to: str | None = None,
    customer_ids: list[str] | None = None,
    payment_method_ids: list[str] | None = None,
    relative_period: RelativePeriod | None = None,
) -> dict:
    """Công nợ đúng theo Rocky Lens Dashboard: số dư đầu kỳ, phát sinh, đã thu và tỷ lệ thu hồi.

    Dùng cho câu hỏi cần khớp giao diện Công nợ. Công nợ B2B/tra cứu POS
    ngoài phạm vi Dashboard vẫn dùng tool cũ get_debt.
    """
    resolved_from, resolved_to, period_label = _resolve_reporting_range(
        date_from, date_to, relative_period
    )
    result = query_dashboard_debt_overview(
        resolved_from, resolved_to, customer_ids, payment_method_ids
    )
    result["query_context"] = _query_context(resolved_from, resolved_to, period_label, None)
    return result


@mcp.tool()
@track_tool
@require_role('admin', 'manager', 'bod')
def get_dashboard_debt_customers(
    date_from: str | None = None,
    date_to: str | None = None,
    customer_ids: list[str] | None = None,
    page: int = 1,
    size: int = 20,
    relative_period: RelativePeriod | None = None,
) -> dict:
    """Danh sách khách công nợ phân trang đúng theo Rocky Lens Dashboard."""
    resolved_from, resolved_to, period_label = _resolve_reporting_range(
        date_from, date_to, relative_period
    )
    result = query_dashboard_debt_customers(
        resolved_from, resolved_to, customer_ids, page, size
    )
    result["query_context"] = _query_context(resolved_from, resolved_to, period_label, None)
    return result


@mcp.tool()
@track_tool
@require_role('admin', 'manager', 'bod')
def get_dashboard_metric(
    metric: str,
    date_from: str | None = None,
    date_to: str | None = None,
    relative_period: RelativePeriod | None = None,
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
) -> dict:
    """Đọc metric Dashboard đã allow-list, không có thao tác ghi dữ liệu.

    metric: order_by_time, order_by_staff, order_by_state, revenue_details,
    revenue_orders, revenue_return_orders, revenue_by_staff,
    revenue_by_staff_details, revenue_by_product, revenue_by_product_details,
    customer_overview, customer_by_province, customer_by_order,
    customer_birthday, customer_no_interaction, product_by_quantity,
    product_by_revenue, picker_overview, picker_average_time,
    picker_leaderboard, picker_heatmap, app_picker_average_time,
    app_picker_productivity, app_picker_completed_by_staff, app_picker_ranking.
    """
    resolved_from, resolved_to, period_label = _resolve_reporting_range(
        date_from, date_to, relative_period
    )
    user = get_current_user()
    if user and user.role != "admin" and user.store_id is not None:
        site_ids = [str(user.store_id)]
    result = query_dashboard_metric(
        metric=metric,
        date_from=resolved_from,
        date_to=resolved_to,
        site_ids=site_ids,
        staff_ids=staff_ids,
        customer_ids=customer_ids,
        province_codes=province_codes,
        days=days,
        staff_count=staff_count,
        customer_id=customer_id,
        revenue_staff_id=revenue_staff_id,
        revenue_staff_ids=revenue_staff_ids,
        product_item_id=product_item_id,
        product_item_ids=product_item_ids,
        order_type=order_type,
        status=status,
        page=page,
        size=size,
    )
    result["query_context"] = _query_context(
        resolved_from, resolved_to, period_label, site_ids[0] if site_ids and len(site_ids) == 1 else None
    )
    return result


@mcp.tool()
@track_tool
@enforce_store_filter
def get_subtotal(
    date_from: str | None = None,
    date_to: str | None = None,
    store_id: str | None = None,
    relative_period: RelativePeriod | None = None,
) -> dict:
    """Doanh số NET không ship: đơn duyệt trừ đơn trả.

    Đây không phải field thực thu của widget Tổng quan. Dùng relative_period
    hoặc date_from/date_to.
    """
    resolved_from, resolved_to, period_label = _resolve_reporting_range(
        date_from, date_to, relative_period
    )
    result = query_subtotal(resolved_from, resolved_to, store_id)
    result["query_context"] = _query_context(
        resolved_from, resolved_to, period_label, store_id
    )
    return result


@mcp.tool()
@track_tool
@enforce_store_filter
def get_orders(date_from: str, date_to: str, status: str | None = None, payment_method: str | None = None) -> dict:
    """Lấy danh sách đơn hàng. Status: completed/cancelled/processing."""
    return query_orders(date_from, date_to, status, payment_method)


@mcp.tool()
@track_tool
@enforce_store_filter
def get_order_operations(
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
    """Tra cứu vận hành Order: đơn tạm/xác nhận/giao/hoàn thành và các tổng tiền của màn Quản lý đơn hàng.

    Không dùng tool này để trả lời KPI doanh thu hoặc thực thu.
    """
    return query_order_operations(
        date_from, date_to, date_field, state, payment_state, code, customer,
        store_id, limit, offset,
    )


@mcp.tool()
@track_tool
@enforce_store_filter
@enforce_staff_filter
def get_staff_revenue(date_from: str, date_to: str, staff_name: str | None = None) -> dict:
    """Xếp hạng nhân viên theo tổng giá trị đơn và số đơn phát hành trong kỳ."""
    return query_staff_revenue(date_from, date_to, staff_name)


@mcp.tool()
@track_tool
@enforce_store_filter
def get_products(date_from: str | None = None, date_to: str | None = None, top_n: int = 10) -> dict:
    """Lấy hai xếp hạng hàng hóa theo đúng ngày: doanh số theo ProductId và số lượng theo ProductItemId."""
    return query_products(date_from, date_to, top_n)


@mcp.tool()
@track_tool
@enforce_store_filter
def get_gross_net_sales(date_from: str, date_to: str) -> dict:
    """Thống kê bóc tách doanh số gộp (Gross) và doanh số thực thu (Net)."""
    return query_gross_net_sales(date_from, date_to)


@mcp.tool()
@track_tool
@enforce_store_filter
def get_product_industry_sales(date_from: str, date_to: str) -> dict:
    """Phân loại doanh số hàng hóa theo nhóm ngành hàng Gọng kính (DD) và Tròng kính (DT)."""
    return query_product_industry_sales(date_from, date_to)


@mcp.tool()
@track_tool
@enforce_store_filter
def get_b2b_adoption_rate(date_from: str, date_to: str) -> dict:
    """Tính toán Adoption Rate - tỷ lệ B2B trên tổng doanh thu."""
    return query_b2b_adoption_rate(date_from, date_to)


@mcp.tool()
@track_tool
@enforce_store_filter
def get_gpm(date_from: str, date_to: str, store_id: str | None = None) -> dict:
    """Tính toán Biên lợi nhuận gộp (Gross Profit Margin - GPM). Format: YYYY-MM-DD"""
    return query_gpm(date_from, date_to, store_id)


@mcp.tool()
@track_tool
@enforce_store_filter
def get_npm(date_from: str, date_to: str, store_id: str | None = None) -> dict:
    """Tính toán Biên lợi nhuận ròng proxy (Net Profit Margin Proxy). Format: YYYY-MM-DD"""
    return query_npm(date_from, date_to, store_id)


@mcp.tool()
@track_tool
@enforce_store_filter
def get_atv(date_from: str, date_to: str, store_id: str | None = None) -> dict:
    """Tính toán Giá trị đơn hàng trung bình (Average Transaction Value). Format: YYYY-MM-DD"""
    return query_atv(date_from, date_to, store_id)


@mcp.tool()
@track_tool
@enforce_store_filter
def get_upt(date_from: str, date_to: str, store_id: str | None = None) -> dict:
    """Tính toán số sản phẩm trung bình mỗi đơn hàng (Units Per Transaction). Format: YYYY-MM-DD"""
    return query_upt(date_from, date_to, store_id)


@mcp.tool()
@track_tool
@enforce_store_filter
def get_rps(date_from: str, date_to: str, store_id: str | None = None) -> dict:
    """Tính toán doanh thu trên đầu nhân sự (Revenue per Staff - RPS). Format: YYYY-MM-DD"""
    return query_rps(date_from, date_to, store_id)


@mcp.tool()
@track_tool
@enforce_store_filter
def get_remake_rate(date_from: str | None = None, date_to: str | None = None, store_id: str | None = None) -> dict:
    """Tính toán tỷ lệ làm lại kính (Remake Rate). Format: YYYY-MM-DD"""
    return query_remake_rate(date_from, date_to, store_id)


@mcp.tool()
@track_tool
@enforce_store_filter
def get_picker_leaderboard(date_from: str | None = None, date_to: str | None = None, store_id: str | None = None, limit: int = 10) -> dict:
    """Bảng xếp hạng hiệu suất Picker kho (Chiến thần bốc tròng). Format: YYYY-MM-DD"""
    return query_picker_leaderboard(date_from, date_to, store_id, limit)


@mcp.tool()
@track_tool
@enforce_store_filter
def get_picker_efficiency(date_from: str | None = None, date_to: str | None = None, store_id: str | None = None) -> dict:
    """Hiệu suất chi tiết của Picker kho (Average Pick Time & Items Per Hour). Format: YYYY-MM-DD"""
    return query_picker_efficiency(date_from, date_to, store_id)


@mcp.tool()
@track_tool
@enforce_store_filter
def get_sales_by_customer_type(
    date_from: str | None = None,
    date_to: str | None = None,
    store_id: str | None = None,
    relative_period: RelativePeriod | None = None,
) -> dict:
    """Doanh số NET theo HMK/khách lẻ, không phải thực thu Tổng quan."""
    resolved_from, resolved_to, period_label = _resolve_reporting_range(
        date_from, date_to, relative_period
    )
    result = query_sales_by_customer_type(
        resolved_from, resolved_to, store_id
    )
    result["query_context"] = _query_context(
        resolved_from, resolved_to, period_label, store_id
    )
    return result


@mcp.tool()
@track_tool
@enforce_store_filter
def get_return_exchange_requests(
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
    """Tra cứu yêu cầu trả/đổi hàng, trạng thái, lý do và số tiền. Ngày theo giờ Việt Nam."""
    return query_return_exchange_requests(
        date_from, date_to, date_field, status, code, reason,
        store_id, limit, offset,
    )


@mcp.tool()
@track_tool
@enforce_store_filter
def get_return_orders(
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
    """Tra cứu ReturnOrder thực tế của màn Quản lý trả hàng, không phải ReturnOrderRequest."""
    return query_return_orders(
        date_from, date_to, date_field, state, code, customer,
        store_id, limit, offset,
    )


# ===========================================================================
# PUBLIC TOOLS (all roles can access - read-only reference)
# ===========================================================================

@mcp.tool()
@track_tool
def get_mcp_context() -> dict:
    """Xem version, giờ Việt Nam, role và phạm vi dữ liệu của kết nối hiện tại."""
    user = get_current_user()
    effective_store_id = (
        str(user.store_id)
        if user and user.role != "admin" and user.store_id is not None
        else None
    )
    return {
        "server": "Rocky Dashboard",
        "server_version": MCP_VERSION,
        "current_time": datetime.now(VN_TIMEZONE).isoformat(),
        "timezone": "Asia/Ho_Chi_Minh",
        "role": user.role if user else "anonymous",
        "scope": "single_store" if effective_store_id else "all_stores",
        "effective_store_id": effective_store_id,
        "reporting_contract": {
            "tong_quan": "get_tinh_hinh_kinh_doanh",
            "tong_quan_by_site": "get_dashboard_order_by_site",
            "doanh_so": "get_revenue_by_source",
            "doanh_so_net": "get_subtotal",
            "hmk_vs_other": "get_sales_by_customer_type",
            "staff": "get_staff_revenue",
            "products": "get_products",
            "cong_no": "get_dashboard_debt_overview",
            "inventory": "get_inventory_live",
        },
    }


@mcp.tool()
@track_tool
def explain(metric_name: str) -> dict:
    """Giải thích KPI. VD: doanh_thu, doanh_so, cong_no, order_type"""
    return explain_metric(metric_name)


@mcp.tool()
@track_tool
def list_tables_tool() -> dict:
    """Liệt kê các bảng hiện có trong database dashboard."""
    return list_tables()


@mcp.tool()
@track_tool
def describe_table_tool(table_name: str) -> dict:
    """Xem cấu trúc cột và kiểu dữ liệu của một bảng cụ thể."""
    return describe_table(table_name)


@mcp.tool()
@track_tool
def list_business_specs() -> dict:
    """Liệt kê tất cả các file tài liệu đặc tả nghiệp vụ."""
    return list_specs()


@mcp.tool()
@track_tool
def get_business_spec_content(filename: str, line_start: int = 1, line_count: int = 200) -> dict:
    """Đọc nội dung tài liệu nghiệp vụ (phân trang, mặc định 200 dòng từ line_start)."""
    return get_spec_content(filename, line_start, line_count)


@mcp.tool()
@track_tool
def search_business_specs(query: str) -> dict:
    """Tìm kiếm từ khóa trong tất cả tài liệu đặc tả nghiệp vụ."""
    return search_specs(query)


@mcp.tool()
@track_tool
def get_schema_quick_context_tool() -> dict:
    """Bản đồ POS schema ngắn gọn và quy tắc cần tuân thủ trước khi viết SQL fallback."""
    return get_schema_quick_context()


@mcp.tool()
@track_tool
def search_schema_tool(query: str, max_results: int = 12) -> dict:
    """Tìm bảng, cột, join và quy tắc nghiệp vụ trong schema Markdown; trả đoạn ngữ cảnh giới hạn."""
    return search_specs(query, max_results)


@mcp.tool()
@track_tool
@require_role('admin')
def describe_pos_table_tool(table_name: str) -> dict:
    """[ADMIN] Xác minh cột và foreign key của bảng POS gốc qua information_schema, không đọc dữ liệu."""
    return describe_pos_table(table_name)
