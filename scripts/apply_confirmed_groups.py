"""Apply confirmed POS roles and HMK policy without inferring broad BOD privileges."""
import argparse
import csv
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--target',choices=['staging','production'],required=True)
    args=parser.parse_args()
    load_dotenv(os.environ['MCP_ENV_FILE'],override=True,encoding='utf-8-sig')
    from mcp_server.local_auth import LocalAuthStore
    from mcp_server.tools import _get_pos_conn
    path=os.environ['MCP_LOCAL_AUTH_DB_PATH']
    if ('employee-staging' in path)!=(args.target=='staging'): raise RuntimeError('Wrong runtime target')
    with _get_pos_conn() as conn:
        employees=conn.execute('''SELECT s."Id"::text,s."Code",s."Name",a."RoleCode"
          FROM "Staff" s LEFT JOIN "Account" a ON a."Id"=s."AccountId" AND a."DeleteAt" IS NULL
          WHERE s."DeleteAt" IS NULL ORDER BY s."Code"''').fetchall()
    output=Path('C:/ProgramData/RockyMCP/config/employee-onboarding')
    backup=output/(args.target+'-before-groups-'+time.strftime('%Y%m%d%H%M%S')+'.sqlite3')
    with sqlite3.connect(path) as source,sqlite3.connect(backup) as destination: source.backup(destination)
    store=LocalAuthStore(path)
    store.ensure_schema()
    rows=[]
    for staff_id,code,name,role_code in employees:
        username='rocky_'+code.strip().lower()
        role={'SHIPPER':'shipper','SALEMANAGER':'sales_manager'}.get(role_code,'staff')
        store.update_user_policy(username,role=role,staff_id=staff_id,include_hmk=True,can_view_cost=False)
        rows.append({'username':username,'staff_code':code,'staff_name':name,'staff_id':staff_id,'role':role,
            'include_hmk':True,'can_view_cost':False,'source_role':role_code or '',
            'pending':'Warehouse scope/accounting/BOD require verified mapping' if role_code not in ('SHIPPER','SALEMANAGER') else ''})
    with (output/(args.target+'-confirmed-groups.csv')).open('w',encoding='utf-8-sig',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
    from collections import Counter
    print(json.dumps({'target':args.target,'accounts':len(rows),'groups':dict(Counter(row['role'] for row in rows)),
        'passwords_changed':False,'backup':str(backup)}))


if __name__=='__main__': main()
