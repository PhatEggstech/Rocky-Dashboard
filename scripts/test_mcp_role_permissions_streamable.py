# -*- coding: utf-8 -*-
"""Smoke test Rocky MCP OAuth/API-key role permissions over streamable HTTP."""
import asyncio
import json
from datetime import date

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


MCP_URL = "https://fortifiable-calculatingly-zaire.ngrok-free.dev/mcp"
TOKENS = {
    "admin": "rk_admin_master2026",
    "store1": "rk_mgr_store1_test",
    "staff1": "rk_staff_nv001_test",
}


async def call_tool(user: str, tool: str, args: dict) -> dict:
    headers = {"Authorization": f"Bearer {TOKENS[user]}"}
    async with streamablehttp_client(MCP_URL, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, args)
            text = result.content[0].text if result.content else ""
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"raw": text}


async def check(label: str, user: str, tool: str, args: dict, expect_block: bool = False) -> bool:
    data = await call_tool(user, tool, args)
    payload = json.dumps(data, ensure_ascii=False)
    blocked = "Permission denied" in payload or data.get("code") == 403
    tool_error = ("error" in data and not blocked) or ("raw" in data and "Error executing tool" in data["raw"])
    ok = blocked if expect_block else (not blocked and not tool_error)
    print(f"{label:<28} {'PASS' if ok else 'FAIL'} blocked={blocked} keys={list(data)[:6]}")
    if not ok:
        print(payload[:800])
    return ok


async def main() -> int:
    today = date.today().isoformat()
    results = [
        await check("admin raw allowed", "admin", "query_raw_sql_tool", {"sql": "SELECT 1 AS x"}),
        await check("manager revenue allowed", "store1", "get_revenue", {"date_from": today, "date_to": today}),
        await check("manager debt allowed", "store1", "get_debt", {}),
        await check("manager raw blocked", "store1", "query_raw_sql_tool", {"sql": "SELECT 1"}, True),
        await check("staff revenue allowed", "staff1", "get_revenue", {"date_from": today, "date_to": today}),
        await check("staff debt blocked", "staff1", "get_debt", {}, True),
        await check("staff explain allowed", "staff1", "explain", {"metric_name": "doanh_thu"}),
    ]
    passed = sum(results)
    print(f"\nSUMMARY {passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
