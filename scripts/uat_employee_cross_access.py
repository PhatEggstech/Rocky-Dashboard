"""Read-only live cross-employee authorization checks, both directions."""
import asyncio
import json
import os
import sqlite3
import sys
from datetime import datetime,timedelta,timezone
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
load_dotenv(os.environ['MCP_ENV_FILE'],override=True,encoding='utf-8-sig')
from fastmcp import Client
from mcp_server.tools import _get_pos_conn


async def main():
    with sqlite3.connect(os.environ['MCP_LOCAL_AUTH_DB_PATH']) as conn:
        conn.row_factory=sqlite3.Row
        users=[dict(r) for r in conn.execute("SELECT username,role,staff_id,name,api_key FROM users WHERE username IN ('rocky_nv092','rocky_nv068') AND is_active=1 ORDER BY username")]
    assert len(users)==2 and all(u['role']=='staff' for u in users)
    today=datetime.now(timezone(timedelta(hours=7))).date()
    end=today.isoformat();start=(today-timedelta(days=29)).isoformat()
    samples={}
    with _get_pos_conn() as conn:
        conn.execute('BEGIN TRANSACTION READ ONLY')
        conn.execute("SET LOCAL statement_timeout = '20s'")
        for u in users:
            order=conn.execute('''SELECT "Code",("IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
                FROM "Order" WHERE "RevenueStaffId"=%s::uuid AND "DeleteAt" IS NULL
                AND "IssueAt" IS NOT NULL ORDER BY "IssueAt" DESC LIMIT 1''',[u['staff_id']]).fetchone()
            customer=conn.execute('''SELECT "Code" FROM "Customer"
                WHERE "RevenueStaffId"=%s::uuid AND "DeleteAt" IS NULL ORDER BY "Code" LIMIT 1''',[u['staff_id']]).fetchone()
            if not order or not customer: raise RuntimeError('Need positive controls for both identities')
            samples[u['username']]={'code':order[0],'date':order[1].isoformat(),'customer':customer[0]}
    checks=[]
    for own,other in ((users[0],users[1]),(users[1],users[0])):
        foreign=samples[other['username']];local=samples[own['username']]
        async with Client('http://127.0.0.1:8085/mcp',auth=own['api_key'],timeout=40) as client:
            async def check(label,tool,args,predicate):
                try:
                    data=(await client.call_tool(tool,args)).data
                    passed=isinstance(data,dict) and predicate(data)
                    checks.append({'actor':own['username'],'target':other['username'],'case':label,'pass':passed,'response_code':data.get('code') if isinstance(data,dict) else None})
                except Exception as exc:
                    checks.append({'actor':own['username'],'target':other['username'],'case':label,'pass':False,'error_type':type(exc).__name__})
            await check('Own order positive control','get_assigned_orders',{'code':local['code'],'date_from':local['date'],'date_to':local['date']},lambda d:len(d.get('rows',[]))==1 and d['rows'][0]['RevenueStaffId']==own['staff_id'])
            await check('Other order inaccessible','get_assigned_orders',{'code':foreign['code'],'date_from':foreign['date'],'date_to':foreign['date']},lambda d:d.get('total_count')==0 and d.get('rows')==[])
            await check('Other operational order inaccessible','get_order_operations',{'code':foreign['code'],'date_from':foreign['date'],'date_to':foreign['date'],'limit':1},lambda d:not d.get('error') and d.get('orders')==[] and d.get('summary',{}).get('orders')==0)
            await check('Own customer positive control','get_customers',{'search':local['customer'],'top_n':10},lambda d:any(r['code']==local['customer'] and r['assigned_staff_id']==own['staff_id'] for r in d.get('rows',[])))
            await check('Other customer inaccessible','get_customers',{'search':foreign['customer'],'top_n':10},lambda d:not d.get('error') and all(r['code']!=foreign['customer'] for r in d.get('rows',[])))
            await check('Other debt denied','get_scoped_customer_debt',{'customer_code':foreign['customer']},lambda d:d.get('code')==403 and 'customer' not in d)
            await check('Forged staff UUID/name overridden','get_staff_revenue',{'date_from':start,'date_to':end,'staff_id':other['staff_id'],'staff_name':other['name']},lambda d:d.get('effective_staff_id')==own['staff_id'] and all(r['staff_id']==own['staff_id'] for r in d.get('staff',[])))
            await check('Receipt scope remains own identity','get_employee_receipts',{'date_from':start,'date_to':end,'limit':1},lambda d:not d.get('error') and d.get('scope',{}).get('staff_id')==own['staff_id'])
            await check('Raw SQL cannot enumerate accounts','query_raw_pos_sql_tool',{'sql':'SELECT 1'},lambda d:d.get('code')==403)
    report={'pass':all(r['pass'] for r in checks),'checks':checks,'count':len(checks),'accounts':[u['username'] for u in users],
            'note':'Tests reuse each account own token; no password guessing or credential changes. Two staff identities, both directions; not every employee or auth endpoint.'}
    target=Path('C:/ProgramData/RockyMCP/config/employee-onboarding/uat-cross-employee-20261014.json')
    target.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
    if not report['pass']:raise SystemExit(1)


if __name__=='__main__':asyncio.run(main())
