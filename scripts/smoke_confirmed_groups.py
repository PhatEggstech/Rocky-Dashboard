"""Live checks for confirmed employee grouping, HMK and delivery scopes."""
import asyncio
import json
import os
import sqlite3
import sys
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
load_dotenv(os.environ['MCP_ENV_FILE'],override=True,encoding='utf-8-sig')
from fastmcp import Client
from mcp_server.tools import _get_pos_conn


async def main():
    port=8086 if 'staging' in os.environ['MCP_ENV_FILE'] else 8085
    with sqlite3.connect(os.environ['MCP_LOCAL_AUTH_DB_PATH']) as conn:
        users=conn.execute("SELECT username,role,staff_id,api_key FROM users WHERE username LIKE 'rocky_%' AND is_active=1").fetchall()
    identities={str(row[2]):row for row in users}
    with _get_pos_conn() as conn:
        hmk=conn.execute('''SELECT "RevenueStaffId"::text,"Code" FROM "Customer" WHERE "DeleteAt" IS NULL AND "IsHmkCustomer"=TRUE AND "RevenueStaffId" IS NOT NULL LIMIT 1''').fetchone()
        transfers=conn.execute('''SELECT o."RevenueStaffId"::text,o."Code",(o."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date FROM "Order" o
          JOIN "Customer" c ON c."Id"=o."CustomerId" WHERE o."DeleteAt" IS NULL AND o."RevenueStaffId" IS NOT NULL
          AND c."RevenueStaffId" IS DISTINCT FROM o."RevenueStaffId" AND o."IssueAt" IS NOT NULL ORDER BY o."IssueAt" DESC LIMIT 1''').fetchone()
        shipping=conn.execute('''SELECT o."ShipperId"::text,o."Code",(o."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
          FROM "Order" o JOIN "Staff" s ON s."Id"=o."ShipperId" JOIN "Account" a ON a."Id"=s."AccountId"
          WHERE o."DeleteAt" IS NULL AND o."CancelAt" IS NULL AND a."RoleCode"='SHIPPER' AND o."IssueAt" IS NOT NULL
          ORDER BY o."IssueAt" DESC LIMIT 1''').fetchone()
    results=[]
    async def check(identity,title,tool,args,validate):
        async with Client(f'http://127.0.0.1:{port}/mcp',auth=identity[3],timeout=40) as client:
            response=await client.call_tool(tool,args)
            data=response.data
            passed=isinstance(data,dict) and validate(data)
            results.append({'username':identity[0],'case':title,'pass':passed,'error':data.get('error') if isinstance(data,dict) else 'non-object'})
    if not hmk or hmk[0] not in identities: raise RuntimeError('Need mapped HMK customer')
    await check(identities[hmk[0]],'Assigned HMK visible','get_customers',{'search':hmk[1],'top_n':10},lambda d:any(r['code']==hmk[1] and r['is_hmk_customer'] and r['assigned_staff_id']==hmk[0] for r in d.get('rows',[])))
    if not transfers or transfers[0] not in identities: raise RuntimeError('Need historical order with changed customer owner')
    await check(identities[transfers[0]],'Previous owner sees own order history','get_assigned_orders',{'date_from':transfers[2].isoformat(),'date_to':transfers[2].isoformat(),'code':transfers[1]},lambda d:len(d.get('rows',[]))==1 and d['rows'][0]['RevenueStaffId']==transfers[0])
    if not shipping or shipping[0] not in identities: raise RuntimeError('Need assigned shipping order')
    shipper=identities[shipping[0]]
    args={'date_from':shipping[2].isoformat(),'date_to':shipping[2].isoformat(),'code':shipping[1]}
    await check(shipper,'Assigned delivery with contacts','get_assigned_orders',args,lambda d:len(d.get('rows',[]))==1 and d['rows'][0]['ShipperId']==shipping[0] and 'Phone' in d['rows'][0]['shipping_contact'])
    await check(shipper,'Other order unavailable','get_assigned_orders',{**args,'code':transfers[1]},lambda d:not d.get('rows'))
    await check(shipper,'Own order inventory','get_assigned_order_inventory',{'order_code':shipping[1]},lambda d:not d.get('error') and all('cost_price' not in r for r in d.get('rows',[])))
    await check(shipper,'Other inventory denied','get_assigned_order_inventory',{'order_code':transfers[1]},lambda d:d.get('code')==403)
    await check(shipper,'Broad warehouse blocked','get_inventory_live',{'limit':1},lambda d:d.get('code')==403)
    managers=[row for row in users if row[1]=='sales_manager']
    for manager in managers:
        await check(manager,'Manager only assigned orders','get_assigned_orders',{},lambda d:all(r['RevenueStaffId']==manager[2] or r['AdminProcessorStaffId']==manager[2] for r in d.get('rows',[])))
        await check(manager,'Manager broad customer access blocked','get_customers',{'top_n':1},lambda d:d.get('code')==403)
    report={'endpoint_port':port,'pass':all(r['pass'] for r in results),'checks':results,'accounts':len(users)}
    target=Path('C:/ProgramData/RockyMCP/config/employee-onboarding')/f'confirmed-groups-check-{port}.json'
    target.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
    if not report['pass']: raise SystemExit(1)


if __name__=='__main__': asyncio.run(main())
