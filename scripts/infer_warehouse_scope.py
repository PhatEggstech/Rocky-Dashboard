"""Evidence-only warehouse proposals; never grants access from activity history."""
import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
load_dotenv(os.environ['MCP_ENV_FILE'],override=True,encoding='utf-8-sig')
from mcp_server.tools import _get_pos_conn
from mcp_server.wms_tools import _get_wms_conn


def main():
    with _get_pos_conn() as conn:
        employees=conn.execute('''SELECT s."Id"::text,s."Code",s."Name",a."RoleCode"
          FROM "Staff" s LEFT JOIN "Account" a ON a."Id"=s."AccountId" AND a."DeleteAt" IS NULL
          WHERE s."DeleteAt" IS NULL ORDER BY s."Code"''').fetchall()
    with _get_wms_conn() as conn:
        roles=dict(conn.execute('''SELECT s."Id"::text,a."RoleCode" FROM "Staff" s
          LEFT JOIN "Account" a ON a."Id"=s."AccountId" AND a."DeleteAt" IS NULL WHERE s."DeleteAt" IS NULL''').fetchall())
        evidence=conn.execute('''WITH events AS (
          SELECT "StaffId","WarehouseId","IssueAt" FROM "OutboundDelivery" WHERE "DeleteAt" IS NULL AND "CancelAt" IS NULL AND "IssueAt">='2026-04-30'::date
          UNION ALL SELECT "StaffId","WarehouseId","IssueAt" FROM "InboundDelivery" WHERE "DeleteAt" IS NULL AND "CancelAt" IS NULL AND "IssueAt">='2026-04-30'::date
          ) SELECT e."StaffId"::text,w."Code",COUNT(*),MAX(e."IssueAt")::text
          FROM events e JOIN "Warehouse" w ON w."Id"=e."WarehouseId" AND w."DeleteAt" IS NULL
          WHERE e."StaffId" IS NOT NULL GROUP BY e."StaffId",w."Code"''').fetchall()
    grouped=defaultdict(list)
    for staff,warehouse,count,latest in evidence: grouped[staff].append((warehouse,count,latest))
    rows=[]
    for staff,code,name,pos_role in employees:
        wms_role=roles.get(staff)
        if pos_role not in ('WAREHOUSESTAFF','WAREHOUSEMANAGER') and wms_role not in ('WAREHOUSESTAFF','WAREHOUSEMANAGER'): continue
        events=sorted(grouped[staff],key=lambda r:r[1],reverse=True)
        total=sum(r[1] for r in events)
        primary=events[0] if events else ('',0,'')
        share=primary[1]/total if total else 0
        confidence='strong_activity_evidence' if total>=20 and share>=.95 else 'weak_or_missing'
        rows.append({'staff_code':code,'staff_name':name,'staff_id':staff,'username':'rocky_'+code.lower(),
            'pos_role':pos_role or '', 'wms_role':wms_role or '', 'suggested_primary_warehouse':primary[0],
            'documents':total,'primary_share_percent':round(100*share,2),'latest_primary_event':primary[2],
            'observed_warehouses':'; '.join(f'{r[0]}:{r[1]}' for r in events),
            'confidence':confidence,'permission_applied':False,
            'reason':'Activity supports a proposal, not an authoritative warehouse assignment'})
    output=Path('C:/ProgramData/RockyMCP/config/employee-onboarding')
    with (output/'warehouse-scope-proposals.csv').open('w',encoding='utf-8-sig',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps({'candidates':len(rows),'strong_activity_evidence':sum(r['confidence']=='strong_activity_evidence' for r in rows),
        'permissions_changed':0,'proposals':[{'staff_code':r['staff_code'],'warehouse':r['suggested_primary_warehouse'],'share':r['primary_share_percent'],'confidence':r['confidence']} for r in rows]}))


if __name__=='__main__': main()
