"""Apply the explicitly approved accountant grant and verify live scope."""
import asyncio
import json
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(os.environ['MCP_ENV_FILE'], override=True, encoding='utf-8-sig')
from fastmcp import Client
from mcp_server.local_auth import LocalAuthStore
from mcp_server.tools import _get_pos_conn


async def main():
    store = LocalAuthStore(os.environ['MCP_LOCAL_AUTH_DB_PATH'])
    store.ensure_schema()
    with store._connect() as conn:
        before = conn.execute("SELECT id,api_key,password_hash FROM users WHERE username='rocky_nv888895'").fetchone()
        others = conn.execute("SELECT username,role,store_id,staff_id FROM users WHERE username!='rocky_nv888895' ORDER BY id").fetchall()
    if before is None:
        raise RuntimeError('Approved employee not provisioned')
    store.update_user_policy('rocky_nv888895', role='accountant', all_sites=True)
    with store._connect() as conn:
        after = conn.execute("SELECT id,api_key,password_hash FROM users WHERE username='rocky_nv888895'").fetchone()
        assert tuple(before) == tuple(after)
        assert [tuple(r) for r in others] == [tuple(r) for r in conn.execute("SELECT username,role,store_id,staff_id FROM users WHERE username!='rocky_nv888895' ORDER BY id")]
    with _get_pos_conn() as conn:
        expected = conn.execute('SELECT COUNT(*) FROM "Customer" WHERE "DeleteAt" IS NULL').fetchone()[0]
        customers = conn.execute('''SELECT DISTINCT ON (w."SiteId") c."Code",w."SiteId"::text
            FROM "Order" o JOIN "Warehouse" w ON w."Id"=o."WarehouseId"
            JOIN "Customer" c ON c."Id"=o."CustomerId"
            WHERE o."DeleteAt" IS NULL AND o."CancelAt" IS NULL AND o."ApproveAt" IS NOT NULL
            AND o."Type" IN (1,2) AND w."DeleteAt" IS NULL AND c."DeleteAt" IS NULL
            AND w."SiteId" IS NOT NULL ORDER BY w."SiteId",c."Code"''').fetchall()
    port = 8086 if 'staging' in os.environ['MCP_ENV_FILE'] else 8085
    checks = []
    async with Client(f'http://127.0.0.1:{port}/mcp', auth=before['api_key'], timeout=45) as client:
        async def check(name, tool, args, predicate):
            result = (await client.call_tool(tool,args)).data
            checks.append({'case':name,'pass':isinstance(result,dict) and predicate(result)})
        await check('All-branch customer count matches POS','get_customers',{'top_n':1},lambda d:d.get('total_count')==expected)
        for code, site in customers:
            await check('Customer debt accessible in site '+site,'get_scoped_customer_debt',{'customer_code':code},lambda d:not d.get('error'))
        await check('All-branch receipts','get_employee_receipts',{'date_from':'2026-09-01','date_to':date.today().isoformat(),'limit':1},lambda d:not d.get('error') and d.get('scope',{}).get('store_id') is None)
        for tool,args in [('query_raw_pos_sql_tool',{'sql':'SELECT 1'}),('get_inventory_live',{'limit':1})]:
            await check('Not admin: '+tool,tool,args,lambda d:d.get('code')==403)
    report={'pass':bool(customers) and all(c['pass'] for c in checks),'checks':checks,'port':port,'branches_checked':len(customers),'credentials_preserved':True}
    path=Path('C:/ProgramData/RockyMCP/config/employee-onboarding')/f'accountant-all-sites-{port}.json'
    path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
    if not report['pass']: raise SystemExit(1)


if __name__=='__main__': asyncio.run(main())
