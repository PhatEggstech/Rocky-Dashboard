"""Run an isolated, read-only ASM scope smoke test against an MCP endpoint."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _decode(response: httpx.Response) -> dict:
    raw = response.text.strip()
    data = [line[5:].strip() for line in raw.splitlines() if line.startswith("data:")]
    return json.loads(data[-1] if data else raw)


def _tool_payload(response: httpx.Response) -> dict:
    rpc = _decode(response)
    result = rpc.get("result", {})
    content = result.get("content", [])
    text = content[0].get("text", "{}") if content else "{}"
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = {"text": text, "rpc_error": rpc.get("error")}
    return {"http": response.status_code, "is_error": bool(result.get("isError")), "payload": payload}


def main() -> int:
    env_file = os.environ.get("MCP_ENV_FILE")
    if env_file:
        load_dotenv(env_file, override=False, encoding="utf-8-sig")

    from mcp_server.local_auth import LocalAuthStore
    from mcp_server.regional_tools import query_sale_zones

    base_url = os.environ.get("MCP_SMOKE_URL", "http://127.0.0.1:8086").rstrip("/")
    auth_db = os.environ["MCP_LOCAL_AUTH_DB_PATH"]
    zones = [row["id"] for row in query_sale_zones()["zones"] if row["level"] == 2]
    if len(zones) != 3:
        raise RuntimeError(f"Expected exactly three root sales zones, got {len(zones)}")

    username = "asm_scope_smoke"
    password = secrets.token_urlsafe(24)
    store = LocalAuthStore(auth_db)
    store.create_or_replace_user(
        username=username,
        password=password,
        role="asm",
        name="ASM Scope Smoke",
        sale_zone_ids=zones,
    )

    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    output: dict[str, object] = {"summary": {}, "zones": len(zones)}

    with httpx.Client(follow_redirects=False, timeout=30) as client:
        login = client.post(
            f"{base_url}/login",
            data={
                "username": username,
                "password": password,
                "redirect_uri": "http://127.0.0.1/asm-scope-smoke",
                "state": "asm-scope-smoke",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            },
        )
        code = parse_qs(urlparse(login.headers.get("location", "")).query).get("code", [""])[0]
        token = client.post(
            f"{base_url}/token",
            data={"grant_type": "authorization_code", "code": code, "code_verifier": verifier},
        )
        if login.status_code != 302 or token.status_code != 200:
            raise RuntimeError("ASM OAuth smoke login failed")
        headers = {
            "Authorization": f"Bearer {token.json()['access_token']}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }

        def post(payload: dict, session: str | None = None) -> httpx.Response:
            call_headers = dict(headers)
            if session:
                call_headers["Mcp-Session-Id"] = session
            return client.post(f"{base_url}/mcp", headers=call_headers, json=payload)

        initialized = post({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "asm-scope-smoke", "version": "1"}},
        })
        session = initialized.headers.get("Mcp-Session-Id")
        if initialized.status_code != 200 or not session:
            raise RuntimeError("ASM MCP initialization failed")
        post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}, session)

        listed = _decode(post({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}, session))
        tool_names = {item["name"] for item in listed["result"]["tools"]}
        required = {
            "get_regional_sale_zones", "get_regional_field_sales",
            "get_regional_order_operations", "get_regional_receipts",
        }
        output["tools_visible"] = sorted(required & tool_names)
        output["raw_sql_visible"] = "query_raw_pos_sql_tool" in tool_names

        def call(request_id: int, name: str, arguments: dict) -> dict:
            return _tool_payload(post({
                "jsonrpc": "2.0", "id": request_id, "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }, session))

        zones_call = call(3, "get_regional_sale_zones", {})
        staff_call = call(4, "get_regional_field_sales", {})
        orders_call = call(5, "get_regional_order_operations", {
            "date_from": "2026-09-03", "date_to": "2026-09-03", "limit": 1,
        })
        receipts_call = call(6, "get_regional_receipts", {
            "date_from": "2026-09-03", "date_to": "2026-09-03", "limit": 1,
        })
        early_call = call(7, "get_regional_receipts", {
            "date_from": "2026-04-29", "date_to": "2026-04-29", "limit": 1,
        })
        outside_scope = call(8, "get_regional_sale_zones", {"sale_zone_ids": ["00000000-0000-0000-0000-000000000000"]})
        raw_call = call(9, "query_raw_pos_sql_tool", {"sql": "SELECT 1"})

        checks = {
            "tools_visible": required.issubset(tool_names),
            "raw_sql_blocked": raw_call["payload"].get("code") == 403,
            "three_zones_returned": len(zones_call["payload"].get("zones", [])) == 3,
            "field_sales_response": not staff_call["is_error"],
            "orders_hmk_filter": orders_call["payload"].get("hmk_excluded_by") == "Customer.IsHmkCustomer = TRUE",
            "receipts_hmk_filter": receipts_call["payload"].get("hmk_excluded_by") == "Customer.IsHmkCustomer = TRUE",
            "receipts_formula": "Allocate" in receipts_call["payload"].get("formula", ""),
            "early_range_blocked": early_call["payload"].get("code") == 400,
            "outside_scope_blocked": outside_scope["payload"].get("code") == 403,
        }
        output["summary"] = checks
        output["diagnostics"] = {
            "early_range": early_call["payload"],
            "outside_scope": outside_scope["payload"],
            "raw_sql": raw_call["payload"],
        }
        output["passed"] = all(checks.values())

    with store._connect() as conn:
        conn.execute("UPDATE users SET is_active = 0 WHERE username = ?", (username,))
    print(json.dumps(output, ensure_ascii=False))
    return 0 if output["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
