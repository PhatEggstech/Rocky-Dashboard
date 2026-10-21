"""Read-only smoke for the production Order-created footer summary."""
import asyncio
import json
import os
from pathlib import Path
import sys

from dotenv import load_dotenv
from fastmcp import Client

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def main() -> None:
    env_file = os.environ["MCP_ENV_FILE"]
    load_dotenv(env_file, override=True, encoding="utf-8-sig")
    from mcp_server.portal_runtime import store

    vault = store()
    with vault._connect() as conn:
        row = conn.execute(
            "SELECT payload FROM portal_uat_accounts ORDER BY tested_at DESC LIMIT 1"
        ).fetchone()
    if row is None:
        raise RuntimeError("A real Rocky SSO sign-in is required before smoke")
    session = json.loads(vault._cipher.decrypt(row[0]))["session"]

    async with Client("http://127.0.0.1:8085/mcp", auth=session, timeout=90) as client:
        result = (await client.call_tool(
            "get_orders_created_summary", {"relative_period": "today"}
        )).data

    totals = result.get("totals", {}) if isinstance(result, dict) else {}
    required = {
        "order_count", "product_amount", "shipping_fee", "order_discount",
        "return_value", "amount_due", "paid_amount", "remaining_amount",
    }
    report = {
        "pass": isinstance(result, dict) and result.get("complete") is True
        and result.get("source") == "rocky_portal_api"
        and result.get("date_basis", "").startswith("Order.IssueAt")
        and required <= set(totals),
        "order_count": totals.get("order_count"),
        "paid_amount": totals.get("paid_amount"),
        "sql_fallback": result.get("sql_fallback"),
    }
    print(json.dumps(report))
    if not report["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
