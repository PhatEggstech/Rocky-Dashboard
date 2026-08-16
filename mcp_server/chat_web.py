# -*- coding: utf-8 -*-
"""
Rocky Dashboard AI Chat Web Server
Chạy trực tiếp trên AI server, cung cấp Web UI để hỏi đáp về dữ liệu.
Access: http://localhost:8080

Dependencies: fastapi, uvicorn, openai, psycopg, python-dotenv
"""
import os
import sys
import json
import re
import inspect
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ── Path setup ────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

try:
    from dotenv import load_dotenv
    env_path = os.path.join(BASE_DIR, "executive_dashboard", ".env.pg")
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    pass

# ── Config ───────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL    = os.environ.get("OLLAMA_MODEL", "deepseek-r1:8b")
AI_API_KEY      = "ollama"

DASHBOARD_PG_DSN = os.environ.get("DASHBOARD_PG_DSN", "")

# ── Import tools from mcp_server ─────────────────────────────────────────────
try:
    from mcp_server.tools import (
        query_revenue, query_subtotal, query_debt,
        query_staff_revenue, query_orders, query_inventory,
        query_order_operations,
        query_customers, query_products, query_stores,
        explain_metric, query_raw_sql, list_tables, describe_table,
        list_specs, get_spec_content, search_specs,
        query_debt_recovery_rate, query_top_bad_debts, query_vip_revenue_drop_alerts,
        query_gross_net_sales, query_product_industry_sales, query_b2b_adoption_rate,
        query_return_exchange_requests,
        query_return_orders,
    )
    from mcp_server.dashboard_api import query_dashboard_order_overview, query_dashboard_order_by_site, query_dashboard_revenue
    TOOLS_AVAILABLE = True
except Exception as e:
    TOOLS_AVAILABLE = False
    print(f"Warning: Could not load tools: {e}")

# ── Tool mapping ──────────────────────────────────────────────────────────────
def query_revenue_dashboard_alias(date_from=None, date_to=None, store_id=None):
    """Keep the web chat's legacy name aligned with Dashboard revenue."""
    if not date_from or not date_to:
        raise ValueError("get_revenue requires date_from and date_to")
    return query_dashboard_revenue(
        date_from, date_to, [str(store_id)] if store_id else None, 1
    )


TOOL_FUNCTIONS = {
    "get_revenue": query_revenue_dashboard_alias,
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
    "explain": explain_metric,
    "list_tables": list_tables,
    "describe_table": describe_table,
    "query_raw_sql": query_raw_sql,
    "list_business_specs": list_specs,
    "search_business_specs": search_specs,
    "get_business_spec_content": get_spec_content,
    "get_debt_recovery_rate": query_debt_recovery_rate,
    "get_top_bad_debts": query_top_bad_debts,
    "get_vip_revenue_drop_alerts": query_vip_revenue_drop_alerts,
    "get_gross_net_sales": query_gross_net_sales,
    "get_product_industry_sales": query_product_industry_sales,
    "get_b2b_adoption_rate": query_b2b_adoption_rate,
    "get_return_exchange_requests": query_return_exchange_requests,
    "get_return_orders": query_return_orders,
    "get_dashboard_order_overview": query_dashboard_order_overview,
    "get_dashboard_order_by_site": query_dashboard_order_by_site,
} if TOOLS_AVAILABLE else {}

# ── Prompts ───────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Bạn là AI assistant của Rocky Lens Dashboard — hệ thống BI cho chuỗi cửa hàng kính mắt HMK.

Bạn có thể:
- Truy vấn doanh thu, doanh số, đơn hàng, tồn kho, khách hàng, nhân viên
- Tra cứu công nợ B2B
- Đọc tài liệu nghiệp vụ (specs) để giải thích KPI, quy trình
- Chạy SQL tùy ý (SELECT only)

Trả lời bằng tiếng Việt. Format số tiền với dấu phẩy. Luôn gọi tool khi cần dữ liệu thực."""

TOOLS_PROMPT = """
## Tool Calling (BẮT BUỘC khi cần dữ liệu)

Format: ```tool_call\n{"name": "TOOL_NAME", "args": {...}}\n```

### Tools có sẵn:
0. get_dashboard_order_overview(date_from, date_to, site_ids?, staff_ids?, period_type?) — KPI Tổng quan nguyên payload từ Rocky Lens dashboard; ưu tiên để khớp UI
0.1 get_dashboard_order_by_site(date_from, date_to, site_ids?, period_type?) — doanh thu theo chi nhánh nguyên payload từ dashboard
1. get_revenue(date_from, date_to, store_id?) — Alias Dashboard: Tổng, HMK, Khác, số đơn bán và đơn trả
1.1 get_revenue_legacy(date_from, date_to, store_id?) — Đối soát POS cohort, không phải số UI
2. get_subtotal(date_from, date_to, store_id?) — Doanh số NET đơn duyệt đã trừ đơn trả, tách HMK/Khác
3. get_debt(customer_name?, date_from?, date_to?) — Công nợ B2B
4. get_staff_revenue(date_from, date_to, staff_name?) — Doanh thu nhân viên
5. get_orders(date_from, date_to, status?, payment_method?) — Đơn hàng
6. get_order_operations(date_from?, date_to?, date_field?, state?, payment_state?, code?, customer?, store_id?, limit?, offset?) — Vận hành Order thực tế, không phải KPI doanh thu
6. get_inventory(category?, dead_stock_only?) — Tồn kho
7. get_customers(segment?, top_n?) — Khách hàng RFM
8. get_products(date_from?, date_to?, top_n?) — Hai bảng: doanh số theo hàng hóa và bán chạy theo số lượng
9. get_return_exchange_requests(date_from?, date_to?, date_field?, status?, code?, reason?, store_id?, limit?, offset?) — Danh sách yêu cầu trả/đổi hàng
10. get_return_orders(date_from?, date_to?, date_field?, state?, code?, customer?, store_id?, limit?, offset?) — ReturnOrder thực tế của màn Quản lý trả hàng
9. get_stores(date_from, date_to) — Performance cửa hàng
10. explain(metric_name) — Giải thích KPI
11. list_tables() — Danh sách bảng DB
12. describe_table(table_name) — Cấu trúc bảng
13. query_raw_sql(sql) — SQL SELECT tùy ý
14. list_business_specs() — Danh sách tài liệu nghiệp vụ
15. search_business_specs(query) — Tìm trong tài liệu
16. get_business_spec_content(filename, line_start?, line_count?) — Đọc tài liệu
17. get_debt_recovery_rate(date_from?, date_to?) — Tỷ lệ thu hồi nợ B2B
18. get_top_bad_debts(limit?) — Top khách hàng nợ xấu
19. get_vip_revenue_drop_alerts(limit?) — Cảnh báo sụt giảm doanh số VIP (>45 ngày chưa mua)
20. get_gross_net_sales(date_from, date_to) — Doanh số Gross vs Net
21. get_product_industry_sales(date_from, date_to) — Phân loại Ngành hàng Gọng kính (DD) vs Tròng kính (DT)
22. get_b2b_adoption_rate(date_from, date_to) — Tỷ lệ chấp nhận B2B (Adoption Rate)
"""

# ── Helper functions ──────────────────────────────────────────────────────────
def execute_tool(fn, fn_args: dict) -> dict:
    sig = inspect.signature(fn)
    filtered = {}
    for name, param in sig.parameters.items():
        if name in fn_args:
            val = fn_args[name]
            target = None
            if param.annotation is not inspect.Parameter.empty:
                if hasattr(param.annotation, "__args__"):
                    for arg in param.annotation.__args__:
                        if arg is not type(None):
                            target = arg; break
                elif isinstance(param.annotation, type):
                    target = param.annotation
            if target == bool:
                val = str(val).lower() in ("true", "1", "yes")
            elif target == int:
                try: val = int(val)
                except: pass
            filtered[name] = val
    return fn(**filtered)


def parse_tool_call(text: str) -> Optional[dict]:
    for pattern in [
        r'```tool_call\s*\n(.*?)\n```',
        r'```json\s*\n(.*?)\n```',
        r'(\{"name"\s*:.*?"args"\s*:.*?\})',
    ]:
        m = re.search(pattern, text, re.DOTALL)
        if m:
            try:
                d = json.loads(m.group(1).strip())
                if "name" in d and "args" in d:
                    return d
            except:
                continue
    return None


def strip_thinking(text: str) -> str:
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()


def chat_with_ai(user_message: str, history: List[Dict] = None) -> str:
    """Send message to Ollama and handle tool calls."""
    try:
        from openai import OpenAI
        client = OpenAI(base_url=OLLAMA_BASE_URL, api_key=AI_API_KEY)

        messages = [{"role": "system", "content": SYSTEM_PROMPT + TOOLS_PROMPT}]
        if history:
            messages.extend(history[-10:])  # last 5 pairs
        messages.append({"role": "user", "content": user_message})

        # First call
        resp = client.chat.completions.create(model=OLLAMA_MODEL, messages=messages)
        ai_text = strip_thinking(resp.choices[0].message.content or "")

        # Check for tool call
        tc = parse_tool_call(ai_text)
        if not tc or not TOOLS_AVAILABLE:
            return ai_text

        fn_name = tc["name"]
        fn_args = tc.get("args", {})
        fn = TOOL_FUNCTIONS.get(fn_name)

        if fn:
            try:
                result = execute_tool(fn, fn_args)
                result_str = json.dumps(result, ensure_ascii=False, default=str)
            except Exception as e:
                result_str = json.dumps({"error": str(e)})
        else:
            result_str = json.dumps({"error": f"Tool '{fn_name}' không tồn tại"})

        # Second call with tool result
        messages.append({"role": "assistant", "content": ai_text})
        messages.append({
            "role": "user",
            "content": f"Kết quả tool {fn_name}:\n{result_str}\n\nHãy trả lời câu hỏi ban đầu bằng tiếng Việt, format số tiền với dấu phẩy (,)."
        })

        resp2 = client.chat.completions.create(model=OLLAMA_MODEL, messages=messages)
        return strip_thinking(resp2.choices[0].message.content or "(không có phản hồi)")

    except Exception as e:
        return f"❌ Lỗi kết nối AI: {e}"


# ── FastAPI App ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Rocky Dashboard AI Chat Server started!")
    yield

app = FastAPI(title="Rocky Dashboard AI Chat", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# In-memory sessions
sessions: Dict[str, List[Dict]] = {}
rate_limits: Dict[str, List[float]] = {}

# ── HTML UI ───────────────────────────────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Rocky Dashboard AI Chat</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0d0f14;
    --surface: #161922;
    --surface2: #1e2330;
    --border: #2a3045;
    --accent: #6366f1;
    --accent2: #8b5cf6;
    --text: #e2e8f0;
    --muted: #64748b;
    --user-bubble: #1e3a5f;
    --ai-bubble: #1a1f2e;
    --success: #22c55e;
    --warning: #f59e0b;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Inter', sans-serif;
    background: var(--bg);
    color: var(--text);
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  /* Header */
  .header {
    background: linear-gradient(135deg, var(--surface) 0%, #1a1f35 100%);
    border-bottom: 1px solid var(--border);
    padding: 14px 24px;
    display: flex;
    align-items: center;
    gap: 16px;
    flex-shrink: 0;
  }
  .header-logo {
    width: 36px; height: 36px;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
    flex-shrink: 0;
  }
  .header-title { font-size: 17px; font-weight: 700; letter-spacing: -0.3px; }
  .header-sub { font-size: 12px; color: var(--muted); margin-top: 1px; }
  .header-badge {
    margin-left: auto;
    background: linear-gradient(135deg, #064e3b, #065f46);
    border: 1px solid #059669;
    color: #34d399;
    font-size: 11px; font-weight: 600;
    padding: 4px 10px; border-radius: 20px;
    display: flex; align-items: center; gap: 5px;
  }
  .header-badge::before {
    content: '';
    width: 6px; height: 6px;
    background: #34d399;
    border-radius: 50%;
    animation: pulse 2s infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }

  /* Main layout */
  .main {
    flex: 1;
    display: flex;
    overflow: hidden;
  }

  /* Sidebar */
  .sidebar {
    width: 260px;
    background: var(--surface);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    overflow: hidden;
  }
  .sidebar-header {
    padding: 16px;
    border-bottom: 1px solid var(--border);
    font-size: 12px;
    font-weight: 600;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.8px;
  }
  .quick-btns {
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    overflow-y: auto;
    flex: 1;
  }
  .quick-btn {
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--text);
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 12px;
    cursor: pointer;
    text-align: left;
    transition: all 0.15s;
    line-height: 1.4;
  }
  .quick-btn:hover {
    border-color: var(--accent);
    background: #1e2340;
    color: #a5b4fc;
  }
  .quick-btn .icon { margin-right: 6px; }
  .sidebar-footer {
    padding: 12px;
    border-top: 1px solid var(--border);
    font-size: 11px;
    color: var(--muted);
  }
  .model-badge {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 11px;
    display: flex; align-items: center; gap: 6px;
  }

  /* Chat area */
  .chat-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .messages {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 20px;
    scroll-behavior: smooth;
  }
  .messages::-webkit-scrollbar { width: 4px; }
  .messages::-webkit-scrollbar-track { background: transparent; }
  .messages::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

  /* Welcome message */
  .welcome {
    text-align: center;
    padding: 40px 20px;
    max-width: 540px;
    margin: auto;
  }
  .welcome-icon {
    width: 70px; height: 70px;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    border-radius: 20px;
    margin: 0 auto 20px;
    display: flex; align-items: center; justify-content: center;
    font-size: 32px;
    box-shadow: 0 8px 32px rgba(99,102,241,0.3);
  }
  .welcome h2 { font-size: 22px; font-weight: 700; margin-bottom: 8px; }
  .welcome p { color: var(--muted); font-size: 14px; line-height: 1.6; }
  .welcome-chips {
    display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; margin-top: 20px;
  }
  .chip {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 6px 14px;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.15s;
    color: var(--text);
  }
  .chip:hover { border-color: var(--accent); color: #a5b4fc; }

  /* Message bubbles */
  .msg { display: flex; gap: 12px; align-items: flex-start; }
  .msg.user { flex-direction: row-reverse; }
  .msg-avatar {
    width: 32px; height: 32px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; flex-shrink: 0;
    margin-top: 2px;
  }
  .msg.user .msg-avatar {
    background: linear-gradient(135deg, #1e3a5f, #1e4080);
    border: 1px solid #2563eb;
  }
  .msg.ai .msg-avatar {
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    box-shadow: 0 4px 12px rgba(99,102,241,0.3);
  }
  .msg-bubble {
    max-width: 75%;
    padding: 12px 16px;
    border-radius: 14px;
    font-size: 14px;
    line-height: 1.65;
    white-space: pre-wrap;
    word-break: break-word;
  }
  .msg.user .msg-bubble {
    background: var(--user-bubble);
    border: 1px solid #1e40af;
    border-radius: 14px 4px 14px 14px;
    color: #bfdbfe;
  }
  .msg.ai .msg-bubble {
    background: var(--ai-bubble);
    border: 1px solid var(--border);
    border-radius: 4px 14px 14px 14px;
  }
  .msg-time {
    font-size: 10px;
    color: var(--muted);
    margin-top: 4px;
    padding: 0 4px;
  }
  .msg.user .msg-time { text-align: right; }

  /* Typing indicator */
  .typing-indicator {
    display: flex; align-items: center; gap: 4px; padding: 14px 16px;
    background: var(--ai-bubble);
    border: 1px solid var(--border);
    border-radius: 4px 14px 14px 14px;
    width: fit-content;
  }
  .typing-dot {
    width: 8px; height: 8px;
    background: var(--muted);
    border-radius: 50%;
    animation: typing 1.4s infinite;
  }
  .typing-dot:nth-child(2) { animation-delay: 0.2s; }
  .typing-dot:nth-child(3) { animation-delay: 0.4s; }
  @keyframes typing {
    0%, 60%, 100% { opacity: 0.3; transform: scale(1); }
    30% { opacity: 1; transform: scale(1.15); }
  }

  /* Input area */
  .input-area {
    padding: 16px 24px 20px;
    border-top: 1px solid var(--border);
    background: var(--surface);
    flex-shrink: 0;
  }
  .input-box {
    display: flex;
    gap: 10px;
    align-items: flex-end;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 10px 12px;
    transition: border-color 0.15s;
  }
  .input-box:focus-within { border-color: var(--accent); }
  textarea {
    flex: 1;
    background: none;
    border: none;
    outline: none;
    color: var(--text);
    font-family: inherit;
    font-size: 14px;
    resize: none;
    max-height: 120px;
    min-height: 22px;
    line-height: 1.5;
  }
  textarea::placeholder { color: var(--muted); }
  .send-btn {
    width: 36px; height: 36px;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    border: none;
    border-radius: 10px;
    color: white;
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
    flex-shrink: 0;
    transition: all 0.15s;
    box-shadow: 0 4px 12px rgba(99,102,241,0.3);
  }
  .send-btn:hover { transform: scale(1.05); box-shadow: 0 6px 16px rgba(99,102,241,0.4); }
  .send-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
  .input-hint { font-size: 11px; color: var(--muted); margin-top: 8px; text-align: center; }

  /* Markdown-like formatting in AI messages */
  .msg.ai .msg-bubble strong { color: #a5b4fc; }
  .msg.ai .msg-bubble code {
    background: #0d1117;
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 2px 6px;
    font-family: monospace;
    font-size: 12px;
    color: #f9a8d4;
  }

  /* Clear btn */
  .clear-btn {
    background: none;
    border: 1px solid var(--border);
    color: var(--muted);
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 11px;
    cursor: pointer;
    transition: all 0.15s;
  }
  .clear-btn:hover { border-color: #ef4444; color: #ef4444; }
</style>
</head>
<body>

<div class="header">
  <div class="header-logo">👁️</div>
  <div>
    <div class="header-title">Rocky Lens AI Chat</div>
    <div class="header-sub">HMK Dashboard Intelligence</div>
  </div>
  <div class="header-badge">AI Online</div>
  <button class="clear-btn" onclick="clearChat()" style="margin-left:12px">🗑️ Xóa chat</button>
</div>

<div class="main">
  <!-- Sidebar -->
  <div class="sidebar">
    <div class="sidebar-header">💡 Gợi ý câu hỏi</div>
    <div class="quick-btns">
      <button class="quick-btn" onclick="ask('Doanh thu tháng 6 năm 2026 là bao nhiêu?')">
        <span class="icon">💰</span>Doanh thu tháng 6/2026
      </button>
      <button class="quick-btn" onclick="ask('Top 5 nhân viên bán hàng tốt nhất tháng này?')">
        <span class="icon">🏆</span>Top nhân viên tháng này
      </button>
      <button class="quick-btn" onclick="ask('Có bao nhiêu cửa hàng? Performance từng cửa hàng tháng 6/2026?')">
        <span class="icon">🏪</span>Performance cửa hàng
      </button>
      <button class="quick-btn" onclick="ask('Tồn kho hiện tại như thế nào? Có hàng chết không?')">
        <span class="icon">📦</span>Kiểm tra tồn kho
      </button>
      <button class="quick-btn" onclick="ask('Danh sách khách hàng VIP (Champion) là ai?')">
        <span class="icon">👑</span>Khách hàng VIP
      </button>
      <button class="quick-btn" onclick="ask('Công nợ B2B hiện tại của các đại lý?')">
        <span class="icon">💳</span>Công nợ B2B
      </button>
      <button class="quick-btn" onclick="ask('Sản phẩm bán chạy nhất tháng 6/2026?')">
        <span class="icon">📊</span>Sản phẩm bán chạy
      </button>
      <button class="quick-btn" onclick="ask('Có bao nhiêu đơn hàng tháng 6? Tỷ lệ huỷ là bao nhiêu?')">
        <span class="icon">📋</span>Thống kê đơn hàng
      </button>
      <button class="quick-btn" onclick="ask('Doanh thu so sánh tháng 5 và tháng 6 năm 2026?')">
        <span class="icon">📈</span>So sánh tháng 5 vs tháng 6
      </button>
      <button class="quick-btn" onclick="ask('Giải thích KPI doanh_thu là gì? Tính như thế nào?')">
        <span class="icon">❓</span>Giải thích KPI doanh thu
      </button>
      <button class="quick-btn" onclick="ask('Liệt kê các tài liệu nghiệp vụ có sẵn')">
        <span class="icon">📁</span>Tài liệu nghiệp vụ
      </button>
      <button class="quick-btn" onclick="ask('Tìm kiếm thông tin về RFM trong tài liệu')">
        <span class="icon">🔍</span>Tìm trong tài liệu
      </button>
    </div>
    <div class="sidebar-footer">
      <div class="model-badge">
        🤖 <span id="model-name">DeepSeek R1 8B</span>
      </div>
      <div style="margin-top: 8px; font-size: 10px;">Ollama • Local AI • Rocky Server</div>
    </div>
  </div>

  <!-- Chat -->
  <div class="chat-area">
    <div class="messages" id="messages">
      <div class="welcome" id="welcome">
        <div class="welcome-icon">🔍</div>
        <h2>Xin chào! Tôi là Rocky AI</h2>
        <p>Hỏi tôi bất kỳ điều gì về doanh thu, đơn hàng, khách hàng, tồn kho, nhân viên, công nợ và tài liệu nghiệp vụ của chuỗi cửa hàng HMK.</p>
        <div class="welcome-chips">
          <span class="chip" onclick="ask('Doanh thu hôm nay?')">📅 Doanh thu hôm nay</span>
          <span class="chip" onclick="ask('Các bảng dữ liệu có sẵn?')">🗄️ Xem database</span>
          <span class="chip" onclick="ask('Giải thích doanh_so là gì?')">💡 Giải thích KPI</span>
          <span class="chip" onclick="ask('Đơn hàng tháng 6/2026?')">📋 Đơn hàng</span>
        </div>
      </div>
    </div>
    <div class="input-area">
      <div class="input-box">
        <textarea id="input" placeholder="Hỏi về doanh thu, đơn hàng, khách hàng, tồn kho... (Enter để gửi, Shift+Enter xuống dòng)" rows="1"
          onkeydown="handleKey(event)" oninput="autoResize(this)"></textarea>
        <button class="send-btn" id="send-btn" onclick="sendMessage()">➤</button>
      </div>
      <div class="input-hint">⚡ AI kết nối trực tiếp với database Rocky Dashboard</div>
    </div>
  </div>
</div>

<script>
let history = [];
let isLoading = false;
const sessionId = Math.random().toString(36).slice(2);

function getTime() {
  return new Date().toLocaleTimeString('vi-VN', {hour: '2-digit', minute: '2-digit'});
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function ask(text) {
  document.getElementById('input').value = text;
  sendMessage();
}

function clearChat() {
  history = [];
  const msgs = document.getElementById('messages');
  msgs.innerHTML = `<div class="welcome" id="welcome">
    <div class="welcome-icon">🔍</div>
    <h2>Xin chào! Tôi là Rocky AI</h2>
    <p>Hỏi tôi bất kỳ điều gì về doanh thu, đơn hàng, khách hàng, tồn kho, nhân viên, công nợ và tài liệu nghiệp vụ.</p>
  </div>`;
}

function addMessage(role, content) {
  // Remove welcome screen on first message
  const welcome = document.getElementById('welcome');
  if (welcome) welcome.remove();

  const msgs = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = `msg ${role}`;

  const avatar = role === 'user' ? '👤' : '🤖';
  const time = getTime();

  // Simple markdown: **bold** and `code`
  let formatted = content
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>');

  div.innerHTML = `
    <div class="msg-avatar">${avatar}</div>
    <div>
      <div class="msg-bubble">${formatted}</div>
      <div class="msg-time">${time}</div>
    </div>
  `;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
  return div;
}

function showTyping() {
  const welcome = document.getElementById('welcome');
  if (welcome) welcome.remove();

  const msgs = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = 'msg ai';
  div.id = 'typing';
  div.innerHTML = `
    <div class="msg-avatar">🤖</div>
    <div class="typing-indicator">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>
  `;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

function removeTyping() {
  const t = document.getElementById('typing');
  if (t) t.remove();
}

async function sendMessage() {
  if (isLoading) return;
  const input = document.getElementById('input');
  const text = input.value.trim();
  if (!text) return;

  input.value = '';
  input.style.height = 'auto';
  isLoading = true;
  document.getElementById('send-btn').disabled = true;

  addMessage('user', text);
  showTyping();

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        message: text,
        session_id: sessionId,
        history: history
      })
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const reply = data.reply || '(không có phản hồi)';

    removeTyping();
    addMessage('ai', reply);

    history.push({role: 'user', content: text});
    history.push({role: 'assistant', content: reply});
    if (history.length > 20) history = history.slice(-20);

  } catch (err) {
    removeTyping();
    addMessage('ai', `❌ Lỗi: ${err.message}`);
  }

  isLoading = false;
  document.getElementById('send-btn').disabled = false;
  input.focus();
}
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML


@app.post("/chat")
async def chat_endpoint(request: Request):
    try:
        body = await request.json()
        user_message = body.get("message", "").strip()
        history = body.get("history", [])

        if not user_message:
            raise HTTPException(status_code=400, detail="message is required")

        reply = chat_with_ai(user_message, history)
        return JSONResponse({"reply": reply, "status": "ok"})

    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"reply": f"❌ Server error: {e}", "status": "error"})


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "tools_available": TOOLS_AVAILABLE,
        "model": OLLAMA_MODEL,
        "ollama_url": OLLAMA_BASE_URL,
    }


if __name__ == "__main__":
    port = int(os.environ.get("CHAT_PORT", "8080"))
    host = os.environ.get("CHAT_HOST", "0.0.0.0")
    print(f"Starting Rocky AI Chat on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")
