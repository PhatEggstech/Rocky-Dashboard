# -*- coding: utf-8 -*-
"""MCP Server definition using FastMCP - with role-based authorization."""
from fastmcp import FastMCP

from .tools import (
    query_revenue,
    query_subtotal,
    query_sales_by_customer_type,
    query_debt,
    query_staff_revenue,
    query_orders,
    query_inventory,
    query_customers,
    query_products,
    query_stores,
    explain_metric,
    query_raw_sql,
    list_tables,
    describe_table,
    list_specs,
    get_spec_content,
    search_specs,
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
from .auth import require_role, enforce_store_filter, enforce_staff_filter, get_current_user
from .wms_tools import (
    query_inventory_live,
    query_inventory_movements,
    query_outbound_deliveries,
    query_raw_wms_sql,
    query_warehouses_live,
    query_wms_health,
)

mcp = FastMCP("Rocky Dashboard")

import functools
import time
import logging
import os
from pathlib import Path

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

def track_tool(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        tool_name = func.__name__
        start_time = time.time()
        # Include user info in tracking
        user = get_current_user()
        user_info = f"User: {user.name} ({user.role})" if user else "User: Anonymous"
        tracker_logger.info(f"[CALL] Tool '{tool_name}' | {user_info} | Args: {args} | Kwargs: {kwargs}")
        try:
            res = func(*args, **kwargs)
            duration = (time.time() - start_time) * 1000
            if isinstance(res, dict):
                # Check for permission errors
                if res.get("code") in (401, 403):
                    tracker_logger.warning(f"[BLOCKED] Tool '{tool_name}' | {user_info} | {res.get('error')}")
                    return res
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
def get_revenue(date_from: str, date_to: str, store_id: str | None = None) -> dict:
    """Lấy 4 KPI Tổng quan theo grain ngày: số đơn, giá trị đơn, thực thu cùng ngày và còn phải thu. Format: YYYY-MM-DD"""
    return query_revenue(date_from, date_to, store_id)


@mcp.tool()
@track_tool
@enforce_store_filter
def get_subtotal(date_from: str, date_to: str, store_id: str | None = None) -> dict:
    """Lấy doanh số (giá trị đơn hàng, không ship) theo khoảng thời gian."""
    return query_subtotal(date_from, date_to, store_id)


@mcp.tool()
@track_tool
@enforce_store_filter
def get_orders(date_from: str, date_to: str, status: str | None = None, payment_method: str | None = None) -> dict:
    """Lấy danh sách đơn hàng. Status: completed/cancelled/processing."""
    return query_orders(date_from, date_to, status, payment_method)


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
def get_sales_by_customer_type(date_from: str, date_to: str) -> dict:
    """Phân loại doanh số NET theo loại khách: HMK (B2B) vs Khách lẻ."""
    return query_sales_by_customer_type(date_from, date_to)


# ===========================================================================
# PUBLIC TOOLS (all roles can access - read-only reference)
# ===========================================================================

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
