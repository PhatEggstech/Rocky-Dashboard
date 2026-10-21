"""Read-only comparison of POS BOD labels and deployed employee scope."""
import csv
import json
import os
import sqlite3
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
load_dotenv(os.environ['MCP_ENV_FILE'],override=True,encoding='utf-8-sig')
from mcp_server.tools import _get_pos_conn


def main():
    with sqlite3.connect(os.environ['MCP_LOCAL_AUTH_DB_PATH']) as auth:
        auth.row_factory=sqlite3.Row
        deployed={str(r['staff_id']):dict(r) for r in auth.execute("""SELECT username,role,is_active,staff_id
            FROM users WHERE username LIKE 'rocky_%'""")}
        bod_accounts=[dict(r) for r in auth.execute("SELECT username,name,role,is_active FROM users WHERE role='bod'")]
    with _get_pos_conn() as conn:
        conn.execute('BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        conn.execute("SET LOCAL statement_timeout = '30s'")
        people=conn.execute('''SELECT s."Id"::text,s."Code",s."Name",s."State"
            FROM "Staff" s JOIN "Account" a ON a."Id"=s."AccountId"
            WHERE s."DeleteAt" IS NULL AND a."DeleteAt" IS NULL AND a."RoleCode"='BOD'
            ORDER BY s."Code"''').fetchall()
        ids=[r[0] for r in people]
        counts={}
        for field in ('RevenueStaffId','AdminProcessorStaffId'):
            counts[field]={r[0]:r[1] for r in conn.execute(f'''SELECT "{field}"::text,COUNT(*)
                FROM "Order" WHERE "DeleteAt" IS NULL AND "{field}"=ANY(%s::uuid[])
                GROUP BY "{field}"''',[ids]).fetchall()}
    rows=[]
    for staff_id,code,name,state in people:
        current=deployed.get(staff_id,{})
        revenue=counts['RevenueStaffId'].get(staff_id,0)
        processing=counts['AdminProcessorStaffId'].get(staff_id,0)
        if current.get('username')=='rocky_nv888895' and current.get('role')=='accountant':
            finding='APPROVED_ACCOUNTANT_EXCEPTION'
            note='User explicitly approved accountant access to all branches'
        elif current.get('is_active') and current.get('role')=='staff':
            if not revenue and not processing:
                finding='ACTIVE_WITH_NO_ASSIGNED_ORDERS'
                note='No non-deleted orders under either assignment FK; activation contradicts requested rule'
            elif not revenue:
                finding='PROCESSOR_ONLY_SCOPE_GAP'
                note='Only AdminProcessorStaffId assignments; current staff history filters RevenueStaffId'
            else:
                finding='STAFF_EXTRA_TOOLS_PENDING_RESTRICTION'
                note='Has revenue-owned orders but customer/revenue/receipt/debt tools exceed requested orders-only policy'
        else:
            finding='REVIEW_OTHER_ROLE'
            note='Not classified as active staff; review explicitly approved policy'
        rows.append({'staff_code':code,'staff_name':name,'username':current.get('username',''),
            'pos_role':'BOD','mcp_role':current.get('role',''),'active':current.get('is_active',0),
            'staff_state':state,'revenue_assigned_orders':revenue,'processor_assigned_orders':processing,
            'finding':finding,'note':note})
    root=Path('C:/ProgramData/RockyMCP/config/employee-onboarding')
    with (root/'pos-bod-access-audit-20261014.csv').open('w',encoding='utf-8-sig',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    summary={'pos_bod_employees':len(rows),'findings':{f:sum(r['finding']==f for r in rows) for f in sorted({r['finding'] for r in rows})},
             'actual_mcp_bod_accounts':bod_accounts,'date_scope':'All non-deleted orders, including canceled history; no date limit',
             'permission_changes':0,'rows':rows}
    (root/'pos-bod-access-audit-20261014.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='rows'},ensure_ascii=True))


if __name__=='__main__':main()
