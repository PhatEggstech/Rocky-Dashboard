"""Read-only OAuth and Dashboard-tool smoke test for a running MCP endpoint.

Uses the existing test account fixture but never prints credentials or tokens.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import secrets
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from scripts.test_oauth_pkce import PASSWORD, USERNAME


BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8086"
REPORT_DATE = sys.argv[2] if len(sys.argv) > 2 else "2026-07-31"
REPORT_RELATIVE_PERIOD = (
    "" if len(sys.argv) <= 3 or sys.argv[3] == "-" else sys.argv[3]
)
REPORT_METRIC = sys.argv[4] if len(sys.argv) > 4 else "order_overview"
REDIRECT_URI = "http://127.0.0.1:9999/callback"


def issue_token() -> tuple[int, str]:
    verifier = secrets.token_urlsafe(32)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")

    with httpx.Client(follow_redirects=False, timeout=25) as client:
        registration = client.post(
            f"{BASE_URL}/register",
            json={
                "client_name": "codex-staging-smoke",
                "redirect_uris": [REDIRECT_URI],
                "grant_types": ["authorization_code"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "none",
            },
        )
        registration.raise_for_status()
        client_id = registration.json()["client_id"]
        authorization = client.get(
            f"{BASE_URL}/authorize",
            params={
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": REDIRECT_URI,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "state": "staging-smoke",
                "scope": "mcp",
            },
        )
        login_url = authorization.headers["location"]
        if login_url.startswith("/"):
            login_url = f"{BASE_URL}{login_url}"
        params = parse_qs(urlparse(login_url).query)
        login = client.post(
            f"{BASE_URL}/login",
            data={
                "username": USERNAME,
                "password": PASSWORD,
                "redirect_uri": params.get("redirect_uri", [""])[0],
                "state": params.get("state", [""])[0],
                "code_challenge": params.get("code_challenge", [""])[0],
                "code_challenge_method": params.get("code_challenge_method", [""])[0],
            },
        )
        if login.status_code != 302:
            return login.status_code, ""
        code = parse_qs(urlparse(login.headers["location"]).query)["code"][0]
        token = client.post(
            f"{BASE_URL}/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "client_id": client_id,
                "code_verifier": verifier,
            },
        )
        return token.status_code, token.json().get("access_token", "") if token.status_code == 200 else ""


async def main() -> None:
    oauth_statuses = [issue_token()[0] for _ in range(3)]
    status, token = issue_token()
    result: dict[str, object] = {
        "oauth_statuses": oauth_statuses + [status],
        "oauth_all_success": all(item == 200 for item in oauth_statuses + [status]),
    }
    if not token:
        print(json.dumps(result, ensure_ascii=False))
        return

    async with streamablehttp_client(
        f"{BASE_URL}/mcp", headers={"Authorization": f"Bearer {token}"}
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            names = {tool.name for tool in (await session.list_tools()).tools}
            requested_tool = {
                "revenue": "get_dashboard_revenue",
                "customer_sales": "get_dashboard_sales_by_customer",
                "debt_overview": "get_dashboard_debt_overview",
                "debt_customers": "get_dashboard_debt_customers",
            }.get(
                REPORT_METRIC,
                "get_dashboard_metric" if REPORT_METRIC.startswith("metric:") else "get_dashboard_order_overview",
            )
            result["dashboard_overview_available"] = "get_dashboard_order_overview" in names
            result["dashboard_by_site_available"] = "get_dashboard_order_by_site" in names
            result["dashboard_revenue_available"] = "get_dashboard_revenue" in names
            result["dashboard_customer_sales_available"] = "get_dashboard_sales_by_customer" in names
            result["dashboard_debt_overview_available"] = "get_dashboard_debt_overview" in names
            result["dashboard_debt_customers_available"] = "get_dashboard_debt_customers" in names
            result["legacy_debt_available"] = "get_debt" in names
            if requested_tool in names:
                overview_args = (
                    {"relative_period": REPORT_RELATIVE_PERIOD}
                    if REPORT_RELATIVE_PERIOD
                    else {"date_from": REPORT_DATE, "date_to": REPORT_DATE}
                )
                if requested_tool in {
                    "get_dashboard_order_overview",
                    "get_dashboard_order_by_site",
                    "get_dashboard_revenue",
                }:
                    overview_args["period_type"] = 1
                if REPORT_METRIC.startswith("metric:"):
                    overview_args["metric"] = REPORT_METRIC.split(":", 1)[1]
                response = await session.call_tool(
                    requested_tool,
                    overview_args,
                )
                text = next(
                    (item.text for item in response.content if getattr(item, "type", "") == "text"),
                    "",
                )
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    payload = {"raw": text[:500]}
                result["dashboard_result"] = payload

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
