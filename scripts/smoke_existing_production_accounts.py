"""Read-only checks using existing production identities; no credentials printed."""
import asyncio
import json
import os
import sqlite3
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(os.environ['MCP_ENV_FILE'], override=True, encoding='utf-8-sig')
from fastmcp import Client


async def main():
    with sqlite3.connect(os.environ['MCP_LOCAL_AUTH_DB_PATH']) as conn:
        accounts=conn.execute('SELECT username,role,api_key FROM users WHERE is_active=1 ORDER BY username').fetchall()
    results=[]
    for username,role,key in accounts:
        async with Client('http://127.0.0.1:8085/mcp',auth=key,timeout=40) as client:
            cases = [('get_regional_sale_zones',{},False),('get_regional_receipts',{'date_from':'2026-10-14','date_to':'2026-10-14','limit':1},False)] if role=='asm' else [('get_inventory_live',{'limit':1},False)]
            if role=='admin': cases.append(('query_raw_pos_sql_tool',{'sql':'SELECT 1 AS probe'},False))
            if username=='bod_assistant':
                cases.extend([('query_raw_pos_sql_tool',{'sql':'SELECT 1 FROM bod_retail_orders LIMIT 1'},False),('query_raw_pos_sql_tool',{'sql':'SELECT 1 FROM "Customer" LIMIT 1'},True)])
            for tool,args,blocked in cases:
                try:
                    response=await client.call_tool(tool,args)
                    data=response.data
                    ok=isinstance(data,dict) and (data.get('code')==403 if blocked else not data.get('error') and data.get('code',0)<400)
                    results.append({'username':username,'tool':tool,'pass':ok})
                except Exception as exc:
                    results.append({'username':username,'tool':tool,'pass':False,'error':type(exc).__name__})
    report={'accounts':len(accounts),'checks':results,'pass':all(r['pass'] for r in results)}
    Path('C:/ProgramData/RockyMCP/logs/employee-production-smoke.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
    if not report['pass']: raise SystemExit(1)


if __name__=='__main__': asyncio.run(main())
