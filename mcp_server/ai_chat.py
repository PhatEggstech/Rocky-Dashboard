# -*- coding: utf-8 -*-
"""AI integration for Rocky Dashboard MCP — supports Ollama (prompt-based) and OpenRouter (native tools)."""
import json
import re
import inspect
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from openai import OpenAI

from .config import AI_API_KEY, AI_BASE_URL, AI_MODEL, AI_PROVIDER
from .prompts import SYSTEM_PROMPT
from .tools import (
    query_revenue,
    query_subtotal,
    query_debt,
    query_staff_revenue,
    query_orders,
    query_order_operations,
    query_inventory,
    query_customers,
    query_products,
    query_stores,
    query_return_exchange_requests,
    query_return_orders,
    explain_metric,
    query_raw_sql,
    list_tables,
    describe_table,
    get_schema_quick_context,
    search_specs,
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

VN_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")


def _dashboard_range(
    date_from: str | None = None,
    date_to: str | None = None,
    relative_period: str | None = None,
) -> tuple[str, str]:
    """Resolve dashboard dates locally for chat clients that bypass FastMCP."""
    if relative_period and (date_from or date_to):
        raise ValueError("Use either relative_period or date_from/date_to, not both")

    today = datetime.now(VN_TIMEZONE).date()
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
        start_text = date_from or date_to
        end_text = date_to or date_from
        if not start_text or not end_text:
            raise ValueError("Provide date_from/date_to or relative_period")
        start = date.fromisoformat(start_text)
        end = date.fromisoformat(end_text)
    if end < start:
        raise ValueError("date_to must be on or after date_from")
    return start.isoformat(), end.isoformat()


def query_dashboard_overview_for_chat(
    date_from: str | None = None,
    date_to: str | None = None,
    relative_period: str | None = None,
    site_ids: list[str] | None = None,
    staff_ids: list[str] | None = None,
    period_type: int = 1,
) -> dict:
    start, end = _dashboard_range(date_from, date_to, relative_period)
    return query_dashboard_order_overview(start, end, site_ids, staff_ids, period_type)


def query_dashboard_by_site_for_chat(
    date_from: str | None = None,
    date_to: str | None = None,
    relative_period: str | None = None,
    site_ids: list[str] | None = None,
    period_type: int = 1,
) -> dict:
    start, end = _dashboard_range(date_from, date_to, relative_period)
    return query_dashboard_order_by_site(start, end, site_ids, period_type)


def query_dashboard_revenue_for_chat(
    date_from: str | None = None,
    date_to: str | None = None,
    relative_period: str | None = None,
    site_ids: list[str] | None = None,
    period_type: int = 1,
) -> dict:
    start, end = _dashboard_range(date_from, date_to, relative_period)
    return query_dashboard_revenue(start, end, site_ids, period_type)


def query_revenue_dashboard_alias_for_chat(
    date_from: str | None = None,
    date_to: str | None = None,
    store_id: str | None = None,
    relative_period: str | None = None,
) -> dict:
    """Compatibility path: `get_revenue` must mirror the sales dashboard."""
    start, end = _dashboard_range(date_from, date_to, relative_period)
    site_ids = [str(store_id)] if store_id else None
    return query_dashboard_revenue(start, end, site_ids, 1)


def query_dashboard_sales_by_customer_for_chat(
    date_from: str | None = None,
    date_to: str | None = None,
    relative_period: str | None = None,
    top_n: int = 10,
) -> dict:
    start, end = _dashboard_range(date_from, date_to, relative_period)
    return query_dashboard_sales_by_customer(start, end, top_n)


def query_dashboard_metric_for_chat(
    metric: str,
    date_from: str | None = None,
    date_to: str | None = None,
    relative_period: str | None = None,
    **filters,
) -> dict:
    start, end = _dashboard_range(date_from, date_to, relative_period)
    return query_dashboard_metric(metric, start, end, **filters)


def query_dashboard_debt_overview_for_chat(
    date_from: str | None = None,
    date_to: str | None = None,
    relative_period: str | None = None,
    customer_ids: list[str] | None = None,
    payment_method_ids: list[str] | None = None,
) -> dict:
    start, end = _dashboard_range(date_from, date_to, relative_period)
    return query_dashboard_debt_overview(start, end, customer_ids, payment_method_ids)


def query_dashboard_debt_customers_for_chat(
    date_from: str | None = None,
    date_to: str | None = None,
    relative_period: str | None = None,
    customer_ids: list[str] | None = None,
    page: int = 1,
    size: int = 20,
) -> dict:
    start, end = _dashboard_range(date_from, date_to, relative_period)
    return query_dashboard_debt_customers(start, end, customer_ids, page, size)

def execute_tool_safely(fn, fn_args: dict) -> dict:
    """Execute tool function safely by filtering out unexpected keyword arguments."""
    sig = inspect.signature(fn)
    has_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
    if has_kwargs:
        return fn(**fn_args)
    
    # Filter keys in fn_args that are not parameters of the function
    filtered_args = {}
    for name, param in sig.parameters.items():
        if name in fn_args:
            val = fn_args[name]
            
            # Determine target type
            target_type = None
            if param.annotation is not inspect.Parameter.empty:
                # Handle Union types like str | None
                if hasattr(param.annotation, "__args__"): # Union / Optional
                    args = param.annotation.__args__
                    # Find first concrete type that is not NoneType
                    for arg in args:
                        if arg is not type(None):
                            target_type = arg
                            break
                elif isinstance(param.annotation, type):
                    target_type = param.annotation
            
            if target_type is None and param.default is not inspect.Parameter.empty and param.default is not None:
                target_type = type(param.default)
                
            # Type casting
            if target_type == bool:
                if isinstance(val, str):
                    val = val.lower() in ("true", "1", "yes", "on")
                else:
                    val = bool(val)
            elif target_type == int:
                try:
                    val = int(val)
                except (ValueError, TypeError):
                    pass
            elif target_type == float:
                try:
                    val = float(val)
                except (ValueError, TypeError):
                    pass
                    
            filtered_args[name] = val
    return fn(**filtered_args)


# Tool function mapping
TOOL_FUNCTIONS = {
    "get_revenue": query_revenue_dashboard_alias_for_chat,
    "get_revenue_legacy": query_revenue,
    "get_subtotal": query_subtotal,
    "get_debt": query_debt,
    "get_staff_revenue": query_staff_revenue,
    "get_orders": query_orders,
    "get_order_operations": query_order_operations,
    "get_inventory": query_inventory,
    "get_customers": query_customers,
    "get_products": query_products,
    "get_stores": query_stores,
    "get_return_exchange_requests": query_return_exchange_requests,
    "get_return_orders": query_return_orders,
    "explain": explain_metric,
    "query_raw_sql": query_raw_sql,
    "list_tables": list_tables,
    "describe_table": describe_table,
    "get_schema_quick_context": get_schema_quick_context,
    "search_schema": search_specs,
    "get_dashboard_order_overview": query_dashboard_overview_for_chat,
    "get_dashboard_order_by_site": query_dashboard_by_site_for_chat,
    "get_dashboard_revenue": query_dashboard_revenue_for_chat,
    "get_dashboard_sales_by_customer": query_dashboard_sales_by_customer_for_chat,
    "get_dashboard_metric": query_dashboard_metric_for_chat,
    "get_dashboard_debt_overview": query_dashboard_debt_overview_for_chat,
    "get_dashboard_debt_customers": query_dashboard_debt_customers_for_chat,
}

# Prompt-based tool description (for models without native function calling)
TOOLS_PROMPT = """
## CRITICAL: Tool Calling Rules

Khi cần tra cứu dữ liệu, BẮT BUỘC trả lời ĐÚNG format sau (KHÔNG thêm text nào khác):
```tool_call
{"name": "TOOL_NAME", "args": {"param1": "value1"}}
```

QUAN TRỌNG:
- store_id là OPTIONAL. Nếu không biết store_id, KHÔNG truyền field đó.
- Chỉ cần name + args, KHÔNG hỏi thêm thông tin.
- KHÔNG giải thích, KHÔNG hỏi lại. Gọi tool NGAY.
- Routing BOD: câu hỏi có KPI/màn Dashboard tương ứng phải dùng tool get_dashboard_*. Câu hỏi vận hành, kho/WMS, phân tích POS/B2B hoặc KPI không có trong Dashboard phải dùng tool cũ phù hợp. Không thay thế một Dashboard KPI bằng số tự tính từ tool cũ. Nếu Dashboard API lỗi, nêu lỗi nguồn; chỉ fallback tool cũ khi câu hỏi vốn nằm ngoài phạm vi Dashboard.
- Câu hỏi chưa có tool: gọi search_schema trước. Không tự viết SQL POS hay suy đoán bảng/cột khi chưa có schema retrieval.

## Tools:
1. get_revenue(date_from, date_to, store_id?) — Alias Dashboard bắt buộc cho câu hỏi doanh số; khớp trang Doanh số Rocky Lens
2. get_dashboard_order_overview(date_from?, date_to?, relative_period?, site_ids?, staff_ids?, period_type?) — KPI nguyên payload từ Rocky Lens dashboard; ưu tiên tool này để khớp UI. Với "hôm nay/hôm qua/tuần này", bắt buộc dùng relative_period, không tự suy diễn ngày.
3. get_dashboard_order_by_site(date_from?, date_to?, relative_period?, site_ids?, period_type?) — doanh thu theo chi nhánh nguyên payload từ dashboard
4. get_dashboard_revenue(date_from?, date_to?, relative_period?, site_ids?, period_type?) — trang Doanh số: Tổng, HMK, Khác, số đơn bán và đơn trả. Bắt buộc dùng tool này khi người dùng hỏi "doanh số" theo trang Doanh số.
5. get_dashboard_sales_by_customer(date_from?, date_to?, relative_period?, top_n?) — trang Doanh số KH. Tổng doanh số/số đơn/đơn trả theo Top N đang chọn, không phải tổng tất cả khách.
6. get_dashboard_metric(metric, date_from?, date_to?, relative_period?, ...) — metric Dashboard read-only mở rộng: đơn theo thời gian/nhân viên/trạng thái; chi tiết doanh thu; doanh thu theo nhân viên/hàng; khách hàng; sản phẩm; picker/app picker.
7. get_dashboard_debt_overview(date_from?, date_to?, relative_period?, customer_ids?, payment_method_ids?) — Công nợ đúng giao diện Dashboard: số dư đầu kỳ, phát sinh, đã thu, tỷ lệ thu hồi.
8. get_dashboard_debt_customers(date_from?, date_to?, relative_period?, customer_ids?, page?, size?) — Danh sách khách công nợ Dashboard có phân trang.
4. get_revenue_legacy(date_from, date_to, store_id?) — [LEGACY] cohort POS để đối soát công thức cũ, không dùng cho UI
5. get_subtotal(date_from, date_to, store_id?) — Doanh số NET đã trừ đơn trả, tách HMK/Khác
3. get_debt(customer_name?, date_from?, date_to?) — Công nợ B2B
4. get_staff_revenue(date_from, date_to, staff_name?) — DT nhân viên
5. get_orders(date_from, date_to, status?, payment_method?) — Đơn hàng
6. get_order_operations(date_from?, date_to?, date_field?, state?, payment_state?, code?, customer?, store_id?, limit?, offset?) — Vận hành đơn hàng thực tế; gồm đơn tạm/xác nhận/giao, không phải KPI doanh thu
6. get_inventory(category?, dead_stock_only?) — Tồn kho
7. get_customers(segment?, top_n?) — Khách hàng RFM
8. get_products(date_from?, date_to?, top_n?) — Hai bảng: doanh số theo hàng hóa và bán chạy theo số lượng
9. get_return_exchange_requests(date_from?, date_to?, date_field?, status?, code?, reason?, store_id?, limit?, offset?) — Danh sách yêu cầu trả/đổi hàng
10. get_return_orders(date_from?, date_to?, date_field?, state?, code?, customer?, store_id?, limit?, offset?) — Trả hàng thực tế từ ReturnOrder, không phải yêu cầu trả/đổi
9. get_stores(date_from, date_to) — Performance cửa hàng
10. explain(metric_name) — Giải thích metric
11. list_tables() — Liệt kê các bảng hiện có trong database
12. describe_table(table_name) — Xem cấu trúc cột của một bảng cụ thể
13. query_raw_sql(sql) — Thực hiện câu lệnh SQL SELECT tùy ý (Read-only)
14. get_schema_quick_context() — Bản đồ schema POS ngắn gọn và quy tắc fallback
15. search_schema(query, max_results?) — Tìm bảng/cột/join/quy tắc trong schema Markdown trước khi SQL fallback

## Examples:
User: "Doanh thu tháng 5 theo Dashboard?"
```tool_call
{"name": "get_dashboard_revenue", "args": {"date_from": "2026-05-01", "date_to": "2026-05-31"}}
```

User: "Nhân viên nào bán tốt nhất tháng này?"
```tool_call
{"name": "get_staff_revenue", "args": {"date_from": "2026-05-01", "date_to": "2026-05-31"}}
```

User: "Giải thích doanh thu là gì"
```tool_call
{"name": "explain", "args": {"metric_name": "doanh_thu"}}
```

User: "Có những bảng nào trong cơ sở dữ liệu?"
```tool_call
{"name": "list_tables", "args": {}}
```

User: "Cột của bảng product_performance là gì?"
```tool_call
{"name": "describe_table", "args": {"table_name": "product_performance"}}
```

User: "Lấy doanh thu trung bình mỗi ngày trong tháng 5 năm 2026"
```tool_call
{"name": "query_raw_sql", "args": {"sql": "SELECT AVG(revenue) FROM daily_sales WHERE d LIKE '2026-05-%'"}}
```
"""

# OpenAI-compatible tool definitions (for native function calling)
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_dashboard_order_overview",
            "description": "Lấy nguyên payload KPI Tổng quan từ Rocky Lens Admin Dashboard API để khớp chính xác giao diện; không tự tính lại",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "description": "Ngày bắt đầu YYYY-MM-DD; không dùng cùng relative_period"},
                    "date_to": {"type": "string", "description": "Ngày kết thúc YYYY-MM-DD; không dùng cùng relative_period"},
                    "relative_period": {"type": "string", "enum": ["today", "yesterday", "this_week", "last_week", "this_month"], "description": "Dùng cho các kỳ tương đối; được server tính theo Asia/Ho_Chi_Minh"},
                    "site_ids": {"type": "array", "items": {"type": "string"}, "description": "Danh sách ID chi nhánh (optional)"},
                    "staff_ids": {"type": "array", "items": {"type": "string"}, "description": "Danh sách ID nhân viên (optional)"},
                    "period_type": {"type": "integer", "description": "Dashboard periodType; mặc định 1"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dashboard_order_by_site",
            "description": "Lấy doanh thu theo chi nhánh nguyên payload từ Rocky Lens Admin Dashboard API",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "description": "Ngày bắt đầu YYYY-MM-DD; không dùng cùng relative_period"},
                    "date_to": {"type": "string", "description": "Ngày kết thúc YYYY-MM-DD; không dùng cùng relative_period"},
                    "relative_period": {"type": "string", "enum": ["today", "yesterday", "this_week", "last_week", "this_month"], "description": "Dùng cho các kỳ tương đối; được server tính theo Asia/Ho_Chi_Minh"},
                    "site_ids": {"type": "array", "items": {"type": "string"}, "description": "Danh sách ID chi nhánh (optional)"},
                    "period_type": {"type": "integer", "description": "Dashboard periodType; mặc định 1"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_revenue",
            "description": "Alias Dashboard cho trang Doanh số Rocky Lens: Tổng, HMK, Khác, số đơn bán và đơn trả. Không dùng cho KPI Thực thu/Còn phải thu.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "description": "Ngày bắt đầu YYYY-MM-DD"},
                    "date_to": {"type": "string", "description": "Ngày kết thúc YYYY-MM-DD"},
                    "store_id": {"type": "string", "description": "ID cửa hàng (optional)"},
                },
                "required": ["date_from", "date_to"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_subtotal",
            "description": "Lấy doanh số (giá trị hàng hóa, không ship) theo khoảng thời gian",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "description": "Ngày bắt đầu YYYY-MM-DD"},
                    "date_to": {"type": "string", "description": "Ngày kết thúc YYYY-MM-DD"},
                    "store_id": {"type": "string", "description": "ID cửa hàng (optional)"},
                },
                "required": ["date_from", "date_to"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_debt",
            "description": "Lấy công nợ khách hàng B2B",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Tên khách hàng (optional)"},
                    "date_from": {"type": "string", "description": "Từ ngày YYYY-MM-DD"},
                    "date_to": {"type": "string", "description": "Đến ngày YYYY-MM-DD"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_staff_revenue",
            "description": "Lấy doanh thu theo nhân viên bán hàng",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "description": "Ngày bắt đầu YYYY-MM-DD"},
                    "date_to": {"type": "string", "description": "Ngày kết thúc YYYY-MM-DD"},
                    "staff_name": {"type": "string", "description": "Tên nhân viên (optional)"},
                },
                "required": ["date_from", "date_to"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_orders",
            "description": "Lấy danh sách đơn hàng",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "description": "Ngày bắt đầu YYYY-MM-DD"},
                    "date_to": {"type": "string", "description": "Ngày kết thúc YYYY-MM-DD"},
                    "status": {"type": "string", "description": "completed/cancelled/processing"},
                    "payment_method": {"type": "string", "description": "Phương thức thanh toán"},
                },
                "required": ["date_from", "date_to"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_operations",
            "description": "Tra cứu Order vận hành thực tế (đơn tạm, xác nhận, giao, hoàn thành) và tổng tiền như màn Quản lý đơn hàng. Không dùng cho KPI doanh thu/thực thu.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "description": "Từ ngày YYYY-MM-DD"},
                    "date_to": {"type": "string", "description": "Đến ngày YYYY-MM-DD"},
                    "date_field": {"type": "string", "enum": ["issue", "create", "approve", "complete", "cancel"]},
                    "state": {"type": "string", "description": "Tên trạng thái workflow cần lọc"},
                    "payment_state": {"type": "integer", "description": "Mã tình trạng thanh toán POS"},
                    "code": {"type": "string", "description": "Mã đơn cần tìm"},
                    "customer": {"type": "string", "description": "Tên khách hàng cần tìm"},
                    "store_id": {"type": "string", "description": "ID chi nhánh"},
                    "limit": {"type": "integer", "description": "Số dòng, tối đa 100"},
                    "offset": {"type": "integer", "description": "Vị trí phân trang"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_inventory",
            "description": "Lấy tồn kho",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Nhóm sản phẩm"},
                    "dead_stock_only": {"type": "boolean", "description": "Chỉ hàng chết (>90 ngày)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_customers",
            "description": "Lấy khách hàng phân khúc RFM",
            "parameters": {
                "type": "object",
                "properties": {
                    "segment": {"type": "string", "description": "Champion/Loyal/At-Risk/Hibernating/Lost"},
                    "top_n": {"type": "integer", "description": "Số lượng top khách hàng"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_products",
            "description": "Lấy Top hàng hóa theo doanh số và Top biến thể/SKU theo số lượng trong đúng khoảng ngày",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "description": "Từ ngày YYYY-MM-DD"},
                    "date_to": {"type": "string", "description": "Đến ngày YYYY-MM-DD"},
                    "top_n": {"type": "integer", "description": "Số lượng top"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stores",
            "description": "Lấy performance cửa hàng",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "description": "Ngày bắt đầu YYYY-MM-DD"},
                    "date_to": {"type": "string", "description": "Ngày kết thúc YYYY-MM-DD"},
                },
                "required": ["date_from", "date_to"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_return_exchange_requests",
            "description": "Tra cứu yêu cầu trả/đổi hàng, trạng thái workflow, lý do và số tiền",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "description": "Từ ngày YYYY-MM-DD"},
                    "date_to": {"type": "string", "description": "Đến ngày YYYY-MM-DD"},
                    "date_field": {"type": "string", "enum": ["create", "issue", "update", "approve", "complete"]},
                    "status": {"type": "string", "description": "Tên trạng thái cần lọc"},
                    "code": {"type": "string", "description": "Mã EXC cần tìm"},
                    "reason": {"type": "string", "description": "Từ khóa lý do trả hàng"},
                    "store_id": {"type": "string", "description": "ID chi nhánh"},
                    "limit": {"type": "integer", "description": "Số dòng, tối đa 100"},
                    "offset": {"type": "integer", "description": "Vị trí phân trang"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dashboard_revenue",
            "description": "Lấy nguyên payload trang Doanh số Rocky Lens: Tổng doanh số, HMK, Khác, số đơn bán và đơn trả. Không dùng thay cho thực thu/còn phải thu của trang Tình hình kinh doanh.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "description": "Ngày bắt đầu YYYY-MM-DD; không dùng cùng relative_period"},
                    "date_to": {"type": "string", "description": "Ngày kết thúc YYYY-MM-DD; không dùng cùng relative_period"},
                    "relative_period": {"type": "string", "enum": ["today", "yesterday", "this_week", "last_week", "this_month"], "description": "Dùng cho kỳ tương đối; được server tính theo Asia/Ho_Chi_Minh"},
                    "site_ids": {"type": "array", "items": {"type": "string"}, "description": "Danh sách ID chi nhánh (optional)"},
                    "period_type": {"type": "integer", "description": "Dashboard periodType; mặc định 1"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dashboard_sales_by_customer",
            "description": "Lấy trang Doanh số khách hàng Rocky Lens. Tổng doanh số/số đơn/đơn trả theo Top N đang chọn; số khách là tổng danh sách API.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "description": "Ngày bắt đầu YYYY-MM-DD; không dùng cùng relative_period"},
                    "date_to": {"type": "string", "description": "Ngày kết thúc YYYY-MM-DD; không dùng cùng relative_period"},
                    "relative_period": {"type": "string", "enum": ["today", "yesterday", "this_week", "last_week", "this_month"], "description": "Dùng cho kỳ tương đối; được server tính theo Asia/Ho_Chi_Minh"},
                    "top_n": {"type": "integer", "minimum": 1, "maximum": 100, "description": "Số khách top để khớp bộ chọn Dashboard, mặc định 10"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dashboard_metric",
            "description": "Metric Dashboard read-only mở rộng. metric hợp lệ: order_by_time, order_by_staff, order_by_state, revenue_details, revenue_orders, revenue_return_orders, revenue_by_staff, revenue_by_staff_details, revenue_by_product, revenue_by_product_details, customer_overview, customer_by_province, customer_by_order, customer_birthday, customer_no_interaction, product_by_quantity, product_by_revenue, picker_overview, picker_average_time, picker_leaderboard, picker_heatmap, app_picker_average_time, app_picker_productivity, app_picker_completed_by_staff, app_picker_ranking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "description": "Tên metric trong danh sách mô tả"},
                    "date_from": {"type": "string", "description": "YYYY-MM-DD; không dùng cùng relative_period"},
                    "date_to": {"type": "string", "description": "YYYY-MM-DD; không dùng cùng relative_period"},
                    "relative_period": {"type": "string", "enum": ["today", "yesterday", "this_week", "last_week", "this_month"]},
                    "site_ids": {"type": "array", "items": {"type": "string"}},
                    "staff_ids": {"type": "array", "items": {"type": "string"}},
                    "customer_ids": {"type": "array", "items": {"type": "string"}},
                    "province_codes": {"type": "array", "items": {"type": "string"}},
                    "days": {"type": "integer"},
                    "staff_count": {"type": "integer"},
                    "customer_id": {"type": "string"},
                    "revenue_staff_id": {"type": "string"},
                    "revenue_staff_ids": {"type": "array", "items": {"type": "string"}},
                    "product_item_id": {"type": "string"},
                    "product_item_ids": {"type": "array", "items": {"type": "string"}},
                    "order_type": {"type": "integer"},
                    "status": {"type": "integer"},
                    "page": {"type": "integer"},
                    "size": {"type": "integer", "maximum": 100},
                },
                "required": ["metric"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dashboard_debt_overview",
            "description": "Lấy công nợ đúng payload Rocky Lens Dashboard: số dư đầu kỳ, phát sinh nợ, đã thu và tỷ lệ thu hồi. Không dùng tool POS cũ để thay số UI.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "description": "YYYY-MM-DD; không dùng cùng relative_period"},
                    "date_to": {"type": "string", "description": "YYYY-MM-DD; không dùng cùng relative_period"},
                    "relative_period": {"type": "string", "enum": ["today", "yesterday", "this_week", "last_week", "this_month"]},
                    "customer_ids": {"type": "array", "items": {"type": "string"}},
                    "payment_method_ids": {"type": "array", "items": {"type": "string"}}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_dashboard_debt_customers",
            "description": "Lấy danh sách khách công nợ phân trang đúng theo Rocky Lens Dashboard.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "description": "YYYY-MM-DD; không dùng cùng relative_period"},
                    "date_to": {"type": "string", "description": "YYYY-MM-DD; không dùng cùng relative_period"},
                    "relative_period": {"type": "string", "enum": ["today", "yesterday", "this_week", "last_week", "this_month"]},
                    "customer_ids": {"type": "array", "items": {"type": "string"}},
                    "page": {"type": "integer", "minimum": 1},
                    "size": {"type": "integer", "minimum": 1, "maximum": 100}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_return_orders",
            "description": "Tra cứu ReturnOrder thực tế như màn Quản lý trả hàng, khác với ReturnOrderRequest/yêu cầu trả đổi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "description": "Từ ngày YYYY-MM-DD"},
                    "date_to": {"type": "string", "description": "Đến ngày YYYY-MM-DD"},
                    "date_field": {"type": "string", "enum": ["issue", "create", "approve", "complete", "cancel"]},
                    "state": {"type": "string", "description": "Tên trạng thái trả hàng cần lọc"},
                    "code": {"type": "string", "description": "Mã RET cần tìm"},
                    "customer": {"type": "string", "description": "Tên khách hàng cần tìm"},
                    "store_id": {"type": "string", "description": "ID chi nhánh"},
                    "limit": {"type": "integer", "description": "Số dòng, tối đa 100"},
                    "offset": {"type": "integer", "description": "Vị trí phân trang"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "explain",
            "description": "Giải thích KPI/metric: doanh_thu, doanh_so, cong_no, order_type",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_name": {"type": "string", "description": "Tên metric cần giải thích"},
                },
                "required": ["metric_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_tables",
            "description": "Liệt kê danh sách các bảng hiện có trong database dashboard (ngoại trừ bảng users)",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "describe_table",
            "description": "Xem cấu trúc chi tiết (danh sách cột và kiểu dữ liệu) của một bảng cụ thể",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {"type": "string", "description": "Tên bảng cần xem cấu trúc"},
                },
                "required": ["table_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_raw_sql",
            "description": "Chạy câu lệnh SQL SELECT tùy ý (Read-only) trên database dashboard. Không được phép truy cập bảng users.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "Câu lệnh SQL SELECT đầy đủ để thực thi"},
                },
                "required": ["sql"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_schema_quick_context",
            "description": "Lấy bản đồ POS schema ngắn gọn và quy tắc bắt buộc trước khi SQL fallback",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_schema",
            "description": "Tìm bảng, cột, join và quy tắc nghiệp vụ trong schema Markdown trước khi viết SQL fallback",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Từ khóa nghiệp vụ, bảng hoặc cột"},
                    "max_results": {"type": "integer", "description": "Số kết quả tối đa, 1-30"},
                },
                "required": ["query"],
            },
        },
    },
]


def create_client() -> OpenAI:
    """Create AI client (Ollama or OpenRouter)."""
    if AI_PROVIDER == "ollama":
        return OpenAI(
            base_url=AI_BASE_URL,
            api_key=AI_API_KEY,
        )
    else:
        if not AI_API_KEY:
            raise ValueError("OPENROUTER_API_KEY not set. Get key from https://openrouter.ai/keys")
        return OpenAI(
            base_url=AI_BASE_URL,
            api_key=AI_API_KEY,
        )


def _parse_tool_call(text: str) -> dict | None:
    """Parse tool_call from AI response text (prompt-based mode)."""
    # Look for ```tool_call\n{...}\n``` or just {"name": ..., "args": ...}
    patterns = [
        r'```tool_call\s*\n(.*?)\n```',
        r'```json\s*\n(.*?)\n```',
        r'(\{"name"\s*:.*?"args"\s*:.*?\})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1).strip())
                if "name" in data and "args" in data:
                    return data
            except json.JSONDecodeError:
                continue
    return None


def _strip_thinking(text: str) -> str:
    """Strip <think>...</think> tags from DeepSeek R1 output."""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()


def chat_ollama(user_message: str, history: list | None = None) -> str:
    """Chat using Ollama (prompt-based tool calling)."""
    client = create_client()

    system = SYSTEM_PROMPT + "\n" + TOOLS_PROMPT
    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    # First call — AI decides if it needs a tool
    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=messages,
    )

    ai_text = response.choices[0].message.content or ""
    ai_text = _strip_thinking(ai_text)

    # Check if AI wants to call a tool
    tool_call = _parse_tool_call(ai_text)
    if not tool_call:
        return ai_text

    # Execute tool
    fn_name = tool_call["name"]
    fn_args = tool_call.get("args", {})
    fn = TOOL_FUNCTIONS.get(fn_name)

    if fn:
        try:
            result = execute_tool_safely(fn, fn_args)
            result_str = json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            result_str = json.dumps({"error": str(e)})
    else:
        result_str = json.dumps({"error": f"Unknown tool: {fn_name}"})

    # Second call — give tool result back to AI
    messages.append({"role": "assistant", "content": ai_text})
    messages.append({"role": "user", "content": f"Tool result for {fn_name}:\n{result_str}\n\nDựa trên kết quả trên, hãy trả lời câu hỏi ban đầu bằng tiếng Việt. Format số tiền với dấu phẩy."})

    response2 = client.chat.completions.create(
        model=AI_MODEL,
        messages=messages,
    )

    final = response2.choices[0].message.content or "(no response)"
    return _strip_thinking(final)


def chat_openrouter(user_message: str, history: list | None = None) -> str:
    """Chat using OpenRouter (native function calling)."""
    client = create_client()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=messages,
        tools=TOOLS_SCHEMA,
        tool_choice="auto",
    )

    msg = response.choices[0].message

    if not msg.tool_calls:
        return msg.content or "(no response)"

    messages.append(msg.model_dump())

    for tool_call in msg.tool_calls:
        fn_name = tool_call.function.name
        fn_args = json.loads(tool_call.function.arguments)

        fn = TOOL_FUNCTIONS.get(fn_name)
        if fn:
            try:
                result = execute_tool_safely(fn, fn_args)
                result_str = json.dumps(result, ensure_ascii=False, default=str)
            except Exception as e:
                result_str = json.dumps({"error": str(e)})
        else:
            result_str = json.dumps({"error": f"Unknown tool: {fn_name}"})

        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": result_str,
        })

    response2 = client.chat.completions.create(
        model=AI_MODEL,
        messages=messages,
    )

    return response2.choices[0].message.content or "(no response)"


def chat(user_message: str, history: list | None = None) -> str:
    """Chat with AI — auto-selects mode based on provider."""
    if AI_PROVIDER == "ollama":
        return chat_ollama(user_message, history)
    else:
        return chat_openrouter(user_message, history)
