#!/usr/bin/env python3
"""Exercise the local OAuth PKCE flow without logging credentials or tokens."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import secrets
import urllib.error
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--inspect-revenue", action="store_true")
    parser.add_argument("--inspect-overview", action="store_true")
    parser.add_argument("--inspect-payment-document-types", action="store_true")
    parser.add_argument("--inspect-legacy-revenue", action="store_true")
    parser.add_argument("--raw-pos-sql", help="Read-only POS SQL for controlled validation")
    parser.add_argument("--date-from", default="2026-08-03")
    parser.add_argument("--date-to", default="2026-08-03")
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")
    opener = urllib.request.build_opener(NoRedirect)

    def request(url: str, data: bytes | None = None, headers: dict | None = None):
        req = urllib.request.Request(url, data=data, headers=headers or {})
        try:
            return opener.open(req, timeout=12)
        except urllib.error.HTTPError as exc:
            return exc

    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    redirect_uri = "http://127.0.0.1/callback"
    authorize_params = urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": "rocky-mcp-client",
            "redirect_uri": redirect_uri,
            "state": "smoke",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    authorize = request(f"{base_url}/authorize?{authorize_params}")
    authorize_ok = authorize.code in (302, 303, 307) and "/login?" in authorize.headers.get("Location", "")

    login_form = urllib.parse.urlencode(
        {
            "username": args.username,
            "password": args.password,
            "redirect_uri": redirect_uri,
            "state": "smoke",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    ).encode()
    login = request(
        f"{base_url}/login",
        login_form,
        {"Content-Type": "application/x-www-form-urlencoded"},
    )
    location = login.headers.get("Location", "")
    code = urllib.parse.parse_qs(urllib.parse.urlsplit(location).query).get("code", [""])[0]
    login_ok = login.code in (302, 303) and bool(code)

    token_form = urllib.parse.urlencode(
        {"grant_type": "authorization_code", "code": code, "code_verifier": verifier}
    ).encode()
    token_response = request(
        f"{base_url}/token",
        token_form,
        {"Content-Type": "application/x-www-form-urlencoded"},
    )
    token_body = json.loads(token_response.read().decode()) if token_response.code == 200 else {}
    access_token = token_body.get("access_token", "")

    initialize_payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "local-auth-smoke", "version": "1"},
            },
        }
    ).encode()
    mcp = request(
        f"{base_url}/mcp",
        initialize_payload,
        {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {access_token}",
        },
    )
    session_id = mcp.headers.get("Mcp-Session-Id", "")
    tools_payload = json.dumps(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    ).encode()
    tools_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {access_token}",
    }
    if session_id:
        tools_headers["Mcp-Session-Id"] = session_id
    tools_response = request(f"{base_url}/mcp", tools_payload, tools_headers)
    tools_raw = tools_response.read().decode(errors="replace")
    json_payload = tools_raw
    if tools_raw.startswith("event:"):
        json_payload = next(
            (line[6:] for line in tools_raw.splitlines() if line.startswith("data: ")),
            "{}",
        )
    try:
        tools_body = json.loads(json_payload) if tools_response.code == 200 else {}
    except json.JSONDecodeError:
        tools_body = {}
    tools = tools_body.get("result", {}).get("tools", [])

    def call_tool(name: str, arguments: dict, request_id: int) -> tuple[bool, int, dict]:
        payload = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        ).encode()
        response = request(f"{base_url}/mcp", payload, tools_headers)
        raw = response.read().decode(errors="replace")
        data = next((line[6:] for line in raw.splitlines() if line.startswith("data: ")), raw)
        try:
            body = json.loads(data)
        except json.JSONDecodeError:
            return False, response.code, {}
        result = body.get("result", {})
        content = result.get("content", [])
        failed = bool(result.get("isError")) or "error" in body
        tool_data: dict = {}
        if content and isinstance(content[0], dict):
            try:
                parsed = json.loads(content[0].get("text", "{}"))
                if isinstance(parsed, dict):
                    tool_data = parsed
            except json.JSONDecodeError:
                pass
        return response.code == 200 and bool(content) and not failed, response.code, tool_data

    wms_ok, wms_status, _ = call_tool("check_wms_health", {}, 3)
    pos_ok, pos_status, _ = call_tool(
        "get_subtotal", {"date_from": args.date_from, "date_to": args.date_to}, 4
    )
    dashboard_arguments = {"date_from": args.date_from, "date_to": args.date_to}
    revenue_ok, revenue_status, revenue_payload = call_tool(
        "get_revenue_by_source", dashboard_arguments, 5
    )
    dashboard_ok, dashboard_status, dashboard_payload = call_tool(
        "get_dashboard_revenue", dashboard_arguments, 6
    )
    overview_ok, overview_status, overview_payload = call_tool(
        "get_dashboard_order_overview", dashboard_arguments, 7
    )
    legacy_ok = True
    legacy_status = 0
    legacy_payload: dict = {}
    if args.inspect_legacy_revenue:
        legacy_ok, legacy_status, legacy_payload = call_tool(
            "get_revenue_legacy", dashboard_arguments, 8
        )
    payment_types_ok = True
    payment_types_status = 0
    payment_types_payload: dict = {}
    if args.inspect_payment_document_types:
        payment_types_ok, payment_types_status, payment_types_payload = call_tool(
            "query_raw_pos_sql_tool",
            {
                "sql": """
                    SELECT po.\"DocumentType\" AS document_type,
                           COUNT(DISTINCT po.\"Id\") AS payment_orders,
                           COUNT(poi.\"Id\") AS payment_items,
                           COALESCE(SUM(poi.\"PaidAmount\"::numeric), 0) AS paid_amount,
                           COALESCE(SUM(po.\"AllocateAmount\"::numeric), 0) AS allocate_amount
                    FROM \"PaymentOrder\" po
                    LEFT JOIN \"PaymentOrderItem\" poi
                      ON poi.\"PaymentOrderId\" = po.\"Id\"
                     AND poi.\"DeleteAt\" IS NULL
                    WHERE po.\"DeleteAt\" IS NULL
                      AND po.\"CompleteAt\" IS NOT NULL
                      AND po.\"CancelAt\" IS NULL
                      AND (po.\"IssueAt\" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
                          BETWEEN DATE '2026-07-01' AND DATE '2026-08-05'
                    GROUP BY po.\"DocumentType\"
                    ORDER BY po.\"DocumentType\"
                """
            },
            8,
        )
    raw_pos_ok = True
    raw_pos_status = 0
    raw_pos_payload: dict = {}
    if args.raw_pos_sql:
        raw_pos_ok, raw_pos_status, raw_pos_payload = call_tool(
            "query_raw_pos_sql_tool", {"sql": args.raw_pos_sql}, 9
        )
    def stable_dashboard_data(value):
        if isinstance(value, dict):
            return {
                key: stable_dashboard_data(item)
                for key, item in value.items()
                if key != "traceId"
            }
        if isinstance(value, list):
            return [stable_dashboard_data(item) for item in value]
        return value

    revenue_matches_dashboard = (
        revenue_ok
        and dashboard_ok
        and stable_dashboard_data(revenue_payload.get("data"))
        == stable_dashboard_data(dashboard_payload.get("data"))
    )
    def fingerprint(payload: dict) -> str:
        data = json.dumps(payload.get("data"), ensure_ascii=True, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()[:12]

    def differing_paths(left, right, path: str = "data", limit: int = 12) -> list[str]:
        if len(path) >= 1024:
            return [path]
        if type(left) is not type(right):
            return [path]
        if isinstance(left, dict):
            differences: list[str] = []
            for key in sorted(set(left) | set(right)):
                if key not in left or key not in right:
                    differences.append(f"{path}.{key}")
                else:
                    differences.extend(differing_paths(left[key], right[key], f"{path}.{key}", limit))
                if len(differences) >= limit:
                    return differences[:limit]
            return differences
        if isinstance(left, list):
            if len(left) != len(right):
                return [f"{path}.length"]
            differences = []
            for index, (left_item, right_item) in enumerate(zip(left, right)):
                differences.extend(differing_paths(left_item, right_item, f"{path}[{index}]", limit))
                if len(differences) >= limit:
                    return differences[:limit]
            return differences
        return [] if left == right else [path]
    result = {
        "authorize_redirect": authorize_ok,
        "login_redirect": login_ok,
        "token_issued": bool(access_token),
        "mcp_authenticated": mcp.code not in (401, 403, 500, 503),
        "mcp_status": mcp.code,
        "tools_list_ok": tools_response.code == 200 and bool(tools),
        "tools_status": tools_response.code,
        "tools_preview": tools_raw[:160].replace(access_token, "***"),
        "tool_count": len(tools),
        "wms_tool_ok": wms_ok,
        "wms_status": wms_status,
        "pos_tool_ok": pos_ok,
        "pos_status": pos_status,
        "revenue_by_source_tool_ok": revenue_ok,
        "revenue_by_source_status": revenue_status,
        "dashboard_revenue_tool_ok": dashboard_ok,
        "dashboard_revenue_status": dashboard_status,
        "dashboard_overview_tool_ok": overview_ok,
        "dashboard_overview_status": overview_status,
        "legacy_revenue_tool_ok": legacy_ok,
        "legacy_revenue_status": legacy_status,
        "payment_document_types_tool_ok": payment_types_ok,
        "payment_document_types_status": payment_types_status,
        "raw_pos_tool_ok": raw_pos_ok,
        "raw_pos_status": raw_pos_status,
        "revenue_matches_dashboard": revenue_matches_dashboard,
        "revenue_data_fingerprint": fingerprint(revenue_payload),
        "dashboard_revenue_data_fingerprint": fingerprint(dashboard_payload),
        "revenue_difference_paths": differing_paths(
            revenue_payload.get("data"), dashboard_payload.get("data")
        ),
    }
    if args.inspect_revenue:
        result["dashboard_revenue_data"] = dashboard_payload.get("data")
    if args.inspect_overview:
        result["dashboard_overview_data"] = overview_payload.get("data")
    if args.inspect_legacy_revenue:
        result["legacy_revenue_data"] = legacy_payload
    if args.inspect_payment_document_types:
        result["payment_document_types"] = payment_types_payload
    if args.raw_pos_sql:
        result["raw_pos_result"] = raw_pos_payload
    print(json.dumps(result, separators=(",", ":")))
    required = (
        "authorize_redirect", "login_redirect", "token_issued",
        "mcp_authenticated", "tools_list_ok", "wms_tool_ok", "pos_tool_ok",
        "revenue_by_source_tool_ok", "dashboard_revenue_tool_ok", "revenue_matches_dashboard",
        "dashboard_overview_tool_ok",
    )
    return 0 if all(result[key] for key in required) else 1


if __name__ == "__main__":
    raise SystemExit(main())
