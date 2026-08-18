"""Run non-destructive MCP production smoke checks through OAuth.

Credentials are read only from process environment and never written to output.
The runner excludes tools with known notification side effects.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx


BASE_URL = os.environ.get("MCP_SMOKE_URL", "https://rockyhmkmcp.share.zrok.io").rstrip("/")
USERNAME = os.environ.get("MCP_SMOKE_USERNAME", "")
PASSWORD = os.environ.get("MCP_SMOKE_PASSWORD", "")
OUTPUT = Path(os.environ.get("MCP_SMOKE_OUTPUT", "outputs/production_smoke/latest.json"))
SIDE_EFFECT_TOOLS = {"trigger_debt_reminders"}


def _decode(response: httpx.Response) -> dict:
    body = response.text.strip()
    data_lines = [line[5:].strip() for line in body.splitlines() if line.startswith("data:")]
    return json.loads(data_lines[-1] if data_lines else body)


def _payload(result: dict) -> object:
    content = result.get("content") or []
    text = content[0].get("text", "") if content and isinstance(content[0], dict) else ""
    try:
        return json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return {"text": str(text)[:500]}


def _arguments(tool_name: str) -> dict:
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    dates = {"date_from": yesterday, "date_to": yesterday}
    mapping = {
        "query_raw_sql_tool": {"sql": "SELECT 1 AS smoke_test"},
        "query_raw_pos_sql_tool": {"sql": "SELECT 1 AS smoke_test"},
        "query_raw_wms_sql_tool": {"sql": "SELECT 1 AS smoke_test"},
        "get_inventory_live": {"limit": 1},
        "get_inventory_movements": {**dates, "limit": 1},
        "get_outbound_deliveries": {**dates, "limit": 1},
        "get_dashboard_metric": {"metric": "order_by_time", **dates, "page": 1, "size": 1},
        "get_dashboard_sales_by_customer": {**dates, "top_n": 1},
        "get_dashboard_debt_customers": {**dates, "page": 1, "size": 1},
        "get_customer_sales": {**dates, "top_n": 1, "page": 1, "page_size": 1},
        "get_top_bad_debts": {"limit": 1},
        "get_vip_revenue_drop_alerts": {"limit": 1},
        "get_orders": dates,
        "get_order_operations": {**dates, "limit": 1},
        "get_products": {**dates, "top_n": 1},
        "get_picker_leaderboard": {**dates, "limit": 1},
        "get_return_exchange_requests": {**dates, "limit": 1},
        "get_return_orders": {**dates, "limit": 1},
        "get_stores": dates,
        "get_revenue_legacy": dates,
        "get_revenue_by_source": dates,
        "get_dashboard_order_overview": dates,
        "get_tinh_hinh_kinh_doanh": dates,
        "get_dashboard_order_by_site": dates,
        "get_dashboard_revenue": dates,
        "get_dashboard_debt_overview": dates,
        "get_subtotal": dates,
        "get_staff_revenue": dates,
        "get_gross_net_sales": dates,
        "get_product_industry_sales": dates,
        "get_b2b_adoption_rate": dates,
        "get_gpm": dates,
        "get_npm": dates,
        "get_atv": dates,
        "get_upt": dates,
        "get_rps": dates,
        "get_remake_rate": dates,
        "get_sales_by_customer_type": dates,
        "get_customers": {"top_n": 1},
        "describe_table_tool": {"table_name": "orders"},
        "describe_pos_table_tool": {"table_name": "Order"},
        "get_business_spec_content": {"filename": "DASHBOARD_FORMULAS.md", "line_start": 1, "line_count": 5},
        "search_business_specs": {"query": "doanh thu"},
        "search_schema_tool": {"query": "Order", "max_results": 2},
        "explain": {"metric_name": "doanh_thu"},
    }
    return mapping.get(tool_name, {})


def _oauth_token(client: httpx.Client) -> str:
    if not USERNAME or not PASSWORD:
        raise RuntimeError("Set MCP_SMOKE_USERNAME and MCP_SMOKE_PASSWORD in the process environment")
    redirect_uri = "http://127.0.0.1:9876/callback"
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    login = client.post(
        f"{BASE_URL}/login",
        data={
            "username": USERNAME,
            "password": PASSWORD,
            "redirect_uri": redirect_uri,
            "state": "production-readonly-smoke",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        },
    )
    if login.status_code != 302:
        raise RuntimeError(f"OAuth login failed: HTTP {login.status_code}")
    code = parse_qs(urlparse(login.headers["location"]).query).get("code", [""])[0]
    token = client.post(
        f"{BASE_URL}/token",
        data={"grant_type": "authorization_code", "code": code, "code_verifier": verifier},
    )
    if token.status_code != 200:
        raise RuntimeError(f"OAuth token exchange failed: HTTP {token.status_code}")
    return str(token.json()["access_token"])


def main() -> int:
    started = time.monotonic()
    with httpx.Client(follow_redirects=False, timeout=60) as client:
        access_token = _oauth_token(client)
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json, text/event-stream", "Content-Type": "application/json"}

        def post(body: dict, session_id: str | None = None) -> httpx.Response:
            call_headers = dict(headers)
            if session_id:
                call_headers["Mcp-Session-Id"] = session_id
            return client.post(f"{BASE_URL}/mcp", headers=call_headers, json=body)

        init = post({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "production-readonly-smoke", "version": "1.0"}}})
        session_id = init.headers.get("mcp-session-id")
        if init.status_code != 200 or not session_id:
            raise RuntimeError(f"MCP initialize failed: HTTP {init.status_code}")
        post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}, session_id)
        listed = post({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}, session_id)
        tool_names = [str(item.get("name", "")) for item in _decode(listed).get("result", {}).get("tools", [])]

        output = {"run_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "endpoint": f"{BASE_URL}/mcp", "summary": {"PASS": 0, "FAIL": 0, "SKIPPED": 0}, "results": {}}
        for request_id, name in enumerate(tool_names, 10):
            if name in SIDE_EFFECT_TOOLS:
                record = {"status": "SKIPPED", "reason": "notification side effect", "arguments": {}}
            else:
                call_started = time.monotonic()
                try:
                    response = post({"jsonrpc": "2.0", "id": request_id, "method": "tools/call", "params": {"name": name, "arguments": _arguments(name)}}, session_id)
                    rpc = _decode(response)
                    result = rpc.get("result", {})
                    payload = _payload(result)
                    error = rpc.get("error") or (payload.get("text") if result.get("isError") and isinstance(payload, dict) else None) or (payload.get("error") if isinstance(payload, dict) else None)
                    record = {"status": "PASS" if response.status_code == 200 and not error else "FAIL", "http": response.status_code, "duration_ms": round((time.monotonic() - call_started) * 1000), "arguments": _arguments(name), "evidence": {key: payload.get(key) for key in ("metric", "source", "status", "count", "ok") if isinstance(payload, dict) and key in payload}, "error": str(error)[:500] if error else None}
                except Exception as exc:
                    record = {"status": "FAIL", "duration_ms": round((time.monotonic() - call_started) * 1000), "arguments": _arguments(name), "error": f"{type(exc).__name__}: {exc}"[:500]}
            output["results"][name] = record
            output["summary"][record["status"]] += 1
            time.sleep(0.1)

    output["duration_seconds"] = round(time.monotonic() - started, 2)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"summary": output["summary"], "duration_seconds": output["duration_seconds"], "output": str(OUTPUT)}, ensure_ascii=False))
    return 1 if output["summary"]["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
