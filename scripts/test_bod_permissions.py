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
import hashlib

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

env_path = Path(os.environ.get("MCP_ENV_FILE", PROJECT_ROOT / ".env"))
if env_path.exists():
    load_dotenv(env_path, override=False, encoding="utf-8-sig")

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from mcp_server.config import DASHBOARD_PG_DSN, MCP_AUTH_BACKEND
from mcp_server.local_auth import LocalAuthStore
import psycopg


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
                ("get_inventory_live", {"limit": 1}, "allowed"),
                ("get_customer_sales", {"relative_period": "today", "top_n": 3}, "allowed"),
                ("get_dashboard_debt_overview", {"relative_period": "today"}, "allowed"),
                ("query_raw_pos_sql_tool", {"sql": "SELECT 1"}, "blocked"),
                ("get_dashboard_sales_by_customer", {"top_n": 3}, "blocked"),
                ("get_orders", {"date_from": "2026-08-24", "date_to": "2026-08-24"}, "blocked"),
                ("get_dashboard_metric", {"metric": "revenue_details"}, "blocked"),
                ("get_dashboard_metric", {"metric": "customer_by_order"}, "blocked"),
                ("get_dashboard_metric", {"metric": "order_by_time"}, "allowed"),
                ("get_debt", {}, "blocked"),
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


def resolve_api_key(database: str, username: str, password: str) -> str | None:
    """Use the same auth backend as the running server, without printing a key."""
    if MCP_AUTH_BACKEND == "sqlite":
        login = LocalAuthStore(database).verify_login(username, password)
        return login[0] if login else None

    if MCP_AUTH_BACKEND == "dashboard_pg":
        if not DASHBOARD_PG_DSN:
            raise SystemExit("DASHBOARD_PG_DSN is not configured")
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        with psycopg.connect(DASHBOARD_PG_DSN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT api_key FROM api_keys
                    WHERE username = %s AND password_hash = %s AND is_active = TRUE
                    """,
                    (username, password_hash),
                )
                row = cur.fetchone()
        return row[0] if row else None

    raise SystemExit(f"Unsupported MCP_AUTH_BACKEND: {MCP_AUTH_BACKEND}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--username", required=True)
    args = parser.parse_args()
    password = os.environ.pop("MCP_PROVISION_PASSWORD", "")
    if not password:
        raise SystemExit("MCP_PROVISION_PASSWORD is required")

    api_key = resolve_api_key(args.database, args.username, password)
    if not api_key:
        raise SystemExit("BOD login verification failed")
    results = asyncio.run(call_tools(args.url, api_key))
    print(json.dumps(results, ensure_ascii=True, sort_keys=True))
    if any(value != "PASS" for value in results.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
