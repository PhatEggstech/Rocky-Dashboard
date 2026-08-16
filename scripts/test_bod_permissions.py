"""Smoke-test BOD authentication and its read-only tool boundary.

The password is supplied through MCP_PROVISION_PASSWORD and is never printed.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from mcp_server.local_auth import LocalAuthStore


async def call_tools(url: str, api_key: str) -> dict[str, int | str]:
    results: dict[str, int | str] = {}
    async with streamablehttp_client(
        url, headers={"Authorization": f"Bearer {api_key}"}
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for tool, arguments, expected in (
                ("get_tinh_hinh_kinh_doanh", {"relative_period": "today"}, "allowed"),
                ("get_products", {"top_n": 3}, "allowed"),
                ("query_raw_pos_sql_tool", {"sql": "SELECT 1"}, "blocked"),
                ("get_inventory_live", {"limit": 1}, "blocked"),
                ("get_dashboard_metric", {"metric": "revenue_details"}, "blocked"),
                ("get_dashboard_sales_by_customer", {}, "blocked"),
                ("trigger_debt_reminders", {}, "blocked"),
            ):
                response = await session.call_tool(tool, arguments)
                text = response.content[0].text if response.content else "{}"
                data = json.loads(text)
                code = data.get("code")
                if expected == "allowed":
                    results[tool] = "PASS" if code not in (401, 403) else f"FAIL:{code}"
                else:
                    results[tool] = "PASS" if code == 403 else f"FAIL:{code}"
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--username", required=True)
    args = parser.parse_args()
    password = os.environ.pop("MCP_PROVISION_PASSWORD", "")
    if not password:
        raise SystemExit("MCP_PROVISION_PASSWORD is required")

    login = LocalAuthStore(args.database).verify_login(args.username, password)
    if not login:
        raise SystemExit("BOD login verification failed")
    api_key = login[0]
    results = asyncio.run(call_tools(args.url, api_key))
    print(json.dumps(results, ensure_ascii=True, sort_keys=True))
    if any(value != "PASS" for value in results.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
