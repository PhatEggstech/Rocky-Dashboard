# -*- coding: utf-8 -*-
"""End-to-end smoke test for the Rocky MCP WMS staging tools."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
import psycopg
from dotenv import load_dotenv

ROOT = Path(os.environ.get("MCP_ROOT", Path(__file__).resolve().parent.parent))
ENV_FILE = Path(os.environ.get("MCP_ENV_FILE", ROOT / ".env"))
BASE_URL = os.environ.get("MCP_TEST_URL", "http://127.0.0.1:8086/mcp")

load_dotenv(ENV_FILE)
sys.path.insert(0, str(ROOT))

from mcp_server.config import DASHBOARD_PG_DSN  # noqa: E402


def decode_response(response: httpx.Response) -> dict:
    text = response.text.strip()
    data_lines = [line[5:].strip() for line in text.splitlines() if line.startswith("data:")]
    return json.loads(data_lines[-1] if data_lines else text)


def get_admin_token() -> str:
    with psycopg.connect(DASHBOARD_PG_DSN, connect_timeout=8) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """SELECT api_key FROM api_keys
                   WHERE is_active = TRUE AND role = 'admin'
                   ORDER BY user_id LIMIT 1"""
            )
            row = cursor.fetchone()
    if not row:
        raise RuntimeError("No active admin API key is available for the smoke test")
    return row[0]


def main() -> int:
    token = get_admin_token()
    base_headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }

    def post(payload: dict, session_id: str | None = None) -> httpx.Response:
        headers = dict(base_headers)
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        return httpx.post(BASE_URL, headers=headers, json=payload, timeout=60)

    init_response = post({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "wms-staging-smoke", "version": "1.0"},
        },
    })
    session_id = init_response.headers.get("mcp-session-id")
    init_body = decode_response(init_response)
    post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}, session_id)

    list_response = post(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        session_id,
    )
    tools = decode_response(list_response)["result"]["tools"]
    tool_names = [tool["name"] for tool in tools]

    calls = [
        ("check_wms_health", {}),
        ("get_warehouses_live", {}),
        ("get_inventory_live", {"limit": 5}),
        ("get_inventory_movements", {
            "date_from": "2026-07-01", "date_to": "2026-07-20", "limit": 5,
        }),
        ("get_outbound_deliveries", {
            "date_from": "2026-07-01", "date_to": "2026-07-20", "limit": 5,
        }),
        ("query_raw_wms_sql_tool", {
            "sql": 'SELECT "Code", "Name" FROM "Warehouse" '
                   'WHERE "DeleteAt" IS NULL ORDER BY "Code"',
        }),
    ]

    output = {
        "initialize_status": init_response.status_code,
        "session": bool(session_id),
        "protocol": init_body.get("result", {}).get("protocolVersion"),
        "tool_count": len(tools),
        "wms_tools": [name for name in tool_names if name in {call[0] for call in calls}],
        "calls": {},
    }
    failed = init_response.status_code != 200 or not session_id

    for request_id, (name, arguments) in enumerate(calls, 10):
        response = post({
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }, session_id)
        result = decode_response(response).get("result", {})
        content = result.get("content", [])
        data = {}
        if content and content[0].get("text"):
            try:
                data = json.loads(content[0]["text"])
            except json.JSONDecodeError:
                data = {}
        call_result = {
            "http": response.status_code,
            "is_error": result.get("isError", False),
            "metric": data.get("metric"),
            "source": data.get("source"),
            "status": data.get("status"),
            "count": data.get("count"),
            "error": data.get("error"),
        }
        output["calls"][name] = call_result
        if response.status_code != 200 or call_result["is_error"] or call_result["error"]:
            failed = True

    print(json.dumps(output, ensure_ascii=True, separators=(",", ":")))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
