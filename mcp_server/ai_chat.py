# -*- coding: utf-8 -*-
"""AI integration for Rocky Dashboard MCP — supports Ollama (prompt-based) and OpenRouter (native tools)."""
import json
import re
import inspect
from openai import OpenAI

from .config import AI_API_KEY, AI_BASE_URL, AI_MODEL, AI_PROVIDER
from .prompts import SYSTEM_PROMPT
from .tools import (
    query_revenue,
    query_subtotal,
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
)

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
    "get_revenue": query_revenue,
    "get_subtotal": query_subtotal,
    "get_debt": query_debt,
    "get_staff_revenue": query_staff_revenue,
    "get_orders": query_orders,
    "get_inventory": query_inventory,
    "get_customers": query_customers,
    "get_products": query_products,
    "get_stores": query_stores,
    "explain": explain_metric,
    "query_raw_sql": query_raw_sql,
    "list_tables": list_tables,
    "describe_table": describe_table,
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

## Tools:
1. get_revenue(date_from, date_to, store_id?) — Doanh thu tất cả cửa hàng (nếu không có store_id)
2. get_subtotal(date_from, date_to, store_id?) — Doanh số
3. get_debt(customer_name?, date_from?, date_to?) — Công nợ B2B
4. get_staff_revenue(date_from, date_to, staff_name?) — DT nhân viên
5. get_orders(date_from, date_to, status?, payment_method?) — Đơn hàng
6. get_inventory(category?, dead_stock_only?) — Tồn kho
7. get_customers(segment?, top_n?) — Khách hàng RFM
8. get_products(date_from?, date_to?, top_n?) — Sản phẩm bán chạy
9. get_stores(date_from, date_to) — Performance cửa hàng
10. explain(metric_name) — Giải thích metric
11. list_tables() — Liệt kê các bảng hiện có trong database
12. describe_table(table_name) — Xem cấu trúc cột của một bảng cụ thể
13. query_raw_sql(sql) — Thực hiện câu lệnh SQL SELECT tùy ý (Read-only)

## Examples:
User: "Doanh thu tháng 5?"
```tool_call
{"name": "get_revenue", "args": {"date_from": "2026-05-01", "date_to": "2026-05-31"}}
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
            "name": "get_revenue",
            "description": "Lấy doanh thu (tiền thực nhận) theo khoảng thời gian",
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
            "description": "Lấy sản phẩm bán chạy",
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
