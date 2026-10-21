"""Read-only live UAT: at most 20 identities and 20 orders per identity."""
import asyncio
import csv
import json
import os
import random
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(os.environ['MCP_ENV_FILE'], override=True, encoding='utf-8-sig')
from fastmcp import Client
from mcp_server.tools import _get_pos_conn


async def main():
    with sqlite3.connect(os.environ['MCP_LOCAL_AUTH_DB_PATH']) as conn:
        conn.row_factory = sqlite3.Row
        users = [dict(r) for r in conn.execute("""SELECT username,name,role,staff_id,api_key
            FROM users WHERE is_active=1 AND username LIKE 'rocky_%'
            AND role IN ('staff','shipper','sales_manager') ORDER BY username""")]
    rng = random.Random(20261014)
    specialized = [u for u in users if u['role'] != 'staff']
    selected = specialized[:20]
    selected += rng.sample([u for u in users if u['role'] == 'staff'], min(20-len(selected), sum(u['role']=='staff' for u in users)))
    rng.shuffle(selected)
    today = datetime.now(timezone(timedelta(hours=7))).date()
    start = today - timedelta(days=365)
    results, observed = [], []
    for user in selected:
        record = {'username':user['username'],'name':user['name'],'role':user['role'],
                  'status':'ERROR','total_orders':None,'checked_orders':0,'missing_fields':[],
                  'scope_violations':[],'error':None}
        try:
            async with Client('http://127.0.0.1:8085/mcp', auth=user['api_key'], timeout=40) as client:
                data = (await client.call_tool('get_assigned_orders',{
                    'date_from':start.isoformat(),'date_to':today.isoformat(),'limit':20})).data
            if not isinstance(data,dict) or data.get('error'):
                raise RuntimeError(str(data.get('error','Non-object response')) if isinstance(data,dict) else 'Non-object response')
            rows = data.get('rows',[])
            record['total_orders'] = data.get('total_count')
            record['checked_orders'] = len(rows)
            for row in rows:
                owners = [row.get('RevenueStaffId')]
                if user['role']=='shipper': owners=[row.get('ShipperId')]
                if user['role']=='sales_manager': owners.append(row.get('AdminProcessorStaffId'))
                if user['staff_id'] not in owners:
                    record['scope_violations'].append(row.get('Code'))
                customer = row.get('shipping_contact' if user['role']=='shipper' else 'Customer') or {}
                missing = [key for key in ('Id','Code','WarehouseId','IssueAt','wsCode','wsName','NeedPayAmount','PaidAmount','LeftAmount') if row.get(key) is None or row.get(key)=='']
                missing += ['Customer.'+key for key in ('Id','Code','Name') if customer.get(key) is None or customer.get(key)=='']
                if user['role']=='shipper':
                    missing += ['shipping_contact.'+key for key in ('Phone','FullAddress') if customer.get(key) is None or customer.get(key)=='']
                if missing: record['missing_fields'].append({'order_code':row.get('Code'),'fields':missing})
                observed.append((record,row,customer))
            record['status'] = 'SCOPE_FAIL' if record['scope_violations'] else ('EMPTY' if not rows else ('MISSING_DATA' if record['missing_fields'] else 'PASS'))
        except Exception as exc:
            # Never include auth headers, keys or passwords in the export.
            record['error'] = type(exc).__name__
        results.append(record)
        print(json.dumps({k:record[k] for k in ('username','role','status','total_orders','checked_orders','error')}), flush=True)
    ids = list(dict.fromkeys(row['Id'] for _,row,_ in observed))
    source_mismatches = []
    if ids:
        with _get_pos_conn() as conn:
            conn.execute('BEGIN TRANSACTION READ ONLY')
            conn.execute("SET LOCAL statement_timeout = '30s'")
            source_rows = conn.execute('''SELECT o."Id"::text,o."Code",o."WarehouseId"::text,
                o."RevenueStaffId"::text,o."AdminProcessorStaffId"::text,o."ShipperId"::text,
                o."NeedPayAmount",o."PaidAmount",o."LeftAmount",c."Id"::text,c."Code",c."Name",
                ws."Code",ws."Name",c."Phone",c."FullAddress"
                FROM "Order" o LEFT JOIN "Customer" c ON c."Id"=o."CustomerId"
                LEFT JOIN "WorkflowState" ws ON ws."Id"=o."StateId"
                WHERE o."Id"=ANY(%s::uuid[])''',[ids]).fetchall()
        source = {r[0]:r for r in source_rows}
        fields = ('Id','Code','WarehouseId','RevenueStaffId','AdminProcessorStaffId','ShipperId','NeedPayAmount','PaidAmount','LeftAmount')
        for record,row,customer in observed:
            raw = source.get(row['Id'])
            if raw is None:
                source_mismatches.append({'username':record['username'],'order_code':row['Code'],'field':'source_missing'})
                continue
            checks = [(field,row.get(field),raw[i]) for i,field in enumerate(fields)]
            checks += [('Customer.'+field,customer.get(field),raw[9+i]) for i,field in enumerate(('Id','Code','Name'))]
            checks += [('wsCode',row.get('wsCode'),raw[12]),('wsName',row.get('wsName'),raw[13])]
            if record['role']=='shipper': checks += [('Phone',customer.get('Phone'),raw[14]),('FullAddress',customer.get('FullAddress'),raw[15])]
            for field,actual,expected in checks:
                equal = actual == expected or (actual is not None and expected is not None and str(actual)==str(expected))
                if field in ('NeedPayAmount','PaidAmount','LeftAmount') and actual is not None and expected is not None:
                    from decimal import Decimal
                    equal = Decimal(str(actual))==Decimal(str(expected))
                if not equal: source_mismatches.append({'username':record['username'],'order_code':row['Code'],'field':field})
    summary = {'accounts_checked':len(results),'order_rows_checked':len(observed),
               'date_from':start.isoformat(),'date_to':today.isoformat(),
               'statuses':{s:sum(r['status']==s for r in results) for s in ('PASS','EMPTY','MISSING_DATA','SCOPE_FAIL','ERROR')},
               'source_mismatches':source_mismatches,'accounts':results,
               'note':'Read-only. EMPTY is no assigned orders in the tested date range, not a successful data-row validation. Canceled orders are included. Missing fields may originate in POS; no automatic data writes.'}
    root = Path('C:/ProgramData/RockyMCP/config/employee-onboarding')
    (root/'uat-random-orders-20261014.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    with (root/'uat-random-orders-20261014.csv').open('w',encoding='utf-8-sig',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(results[0]))
        writer.writeheader()
        for r in results: writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,list) else v for k,v in r.items()})
    print(json.dumps({k:v for k,v in summary.items() if k!='accounts'}),flush=True)


if __name__=='__main__': asyncio.run(main())
