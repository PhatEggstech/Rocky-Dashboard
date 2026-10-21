"""Read-only reconciliation of the Dashboard API against Rocky MCP staging.

The script runs on the customer machine so the Dashboard API token remains
local. It compares the source Dashboard response with the corresponding MCP
tool output, writes a JSON report, and never prints secrets or access tokens.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import secrets
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# The caller supplies the customer-machine staging environment file. Load it
# before importing the API client, whose configuration is read at import time.
ENV_FILE = os.getenv("MCP_ENV_FILE", "")
if ENV_FILE:
    load_dotenv(ENV_FILE, override=True)

from mcp_server import dashboard_api
from scripts.test_oauth_pkce import PASSWORD, USERNAME


BASE_URL = os.getenv("MCP_TEST_BASE_URL", "http://127.0.0.1:8086")
REDIRECT_URI = "http://127.0.0.1:9999/callback"


def parse_day(value: str) -> date:
    return date.fromisoformat(value)


def reporting_ranges(anchor: date) -> list[tuple[str, str, str]]:
    monday = anchor - timedelta(days=anchor.weekday())
    return [
        ("today", anchor.isoformat(), anchor.isoformat()),
        ("yesterday", (anchor - timedelta(days=1)).isoformat(), (anchor - timedelta(days=1)).isoformat()),
        ("this_week", monday.isoformat(), (monday + timedelta(days=6)).isoformat()),
    ]


def issue_token() -> str:
    verifier = secrets.token_urlsafe(32)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")
    with httpx.Client(follow_redirects=False, timeout=30) as client:
        registration = client.post(
            f"{BASE_URL}/register",
            json={
                "client_name": "rocky-reconciliation",
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
                "redirect_uri": params["redirect_uri"][0],
                "state": params.get("state", [""])[0],
                "code_challenge": params["code_challenge"][0],
                "code_challenge_method": params["code_challenge_method"][0],
            },
        )
        if login.status_code != 302:
            raise RuntimeError(f"MCP OAuth login failed with HTTP {login.status_code}")
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
        token.raise_for_status()
        return token.json()["access_token"]


def dashboard_revenue_summary(result: dict[str, Any]) -> dict[str, Any]:
    data = result.get("data", {})
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        data = data["data"]
    summary = data.get("summary", {}) if isinstance(data, dict) else {}
    all_summary = summary.get("all", {}) if isinstance(summary, dict) else {}
    return {
        "total_revenue": all_summary.get("totalRevenue"),
        "hmk_revenue": all_summary.get("hmkRevenue"),
        "other_revenue": all_summary.get("otherRevenue"),
        "num_order": all_summary.get("numOrder"),
        "num_return_order": all_summary.get("numReturnOrder"),
    }


def dashboard_customer_summary(result: dict[str, Any]) -> dict[str, Any]:
    data = result.get("data", {})
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        data = data["data"]
    rows = data.get("data", []) if isinstance(data, dict) else []
    meta = data.get("meta", {}) if isinstance(data, dict) else {}
    return {
        "top_n": len(rows),
        "total_revenue": sum((row.get("totalRevenue") or 0) for row in rows),
        "customer_count": meta.get("total"),
        "num_order": sum((row.get("numOrder") or 0) for row in rows),
        "num_return_order": sum((row.get("numReturnOrder") or 0) for row in rows),
    }


def normalized(value: Any) -> Any:
    return value if value is not None else 0


def compare(source: dict[str, Any], mcp: dict[str, Any]) -> dict[str, Any]:
    keys = sorted(set(source) | set(mcp))
    fields = {
        key: {
            "dashboard": source.get(key),
            "mcp": mcp.get(key),
            "difference": normalized(mcp.get(key)) - normalized(source.get(key)),
            "match": mcp.get(key) == source.get(key),
        }
        for key in keys
    }
    return {"pass": all(field["match"] for field in fields.values()), "fields": fields}


async def mcp_call(session: ClientSession, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    response = await session.call_tool(name, arguments)
    text = next((item.text for item in response.content if getattr(item, "type", "") == "text"), "")
    return json.loads(text)


async def main() -> None:
    anchor = parse_day(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    token = issue_token()
    report: dict[str, Any] = {"anchor_date": anchor.isoformat(), "base_url": BASE_URL, "checks": []}

    async with streamablehttp_client(
        f"{BASE_URL}/mcp", headers={"Authorization": f"Bearer {token}"}
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for label, start, end in reporting_ranges(anchor):
                source_revenue = dashboard_api.query_dashboard_revenue(start, end)
                source_customer = dashboard_api.query_dashboard_sales_by_customer(start, end, top_n=10)
                mcp_revenue = await mcp_call(session, "get_dashboard_revenue", {"date_from": start, "date_to": end})
                mcp_customer = await mcp_call(
                    session, "get_dashboard_sales_by_customer", {"date_from": start, "date_to": end, "top_n": 10}
                )
                report["checks"].append(
                    {
                        "period": label,
                        "range": {"from": start, "to": end},
                        "revenue": compare(
                            dashboard_revenue_summary(source_revenue),
                            mcp_revenue.get("dashboard_summary") or dashboard_revenue_summary(mcp_revenue),
                        ),
                        "customer_sales_top_10": compare(
                            dashboard_customer_summary(source_customer),
                            mcp_customer.get("dashboard_summary") or dashboard_customer_summary(mcp_customer)
                        ),
                    }
                )

    report["pass"] = all(
        section["revenue"]["pass"] and section["customer_sales_top_10"]["pass"]
        for section in report["checks"]
    )
    output = ROOT / "outputs" / f"dashboard_mcp_reconciliation_{anchor.isoformat()}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"pass": report["pass"], "report": str(output), "checks": report["checks"]}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
