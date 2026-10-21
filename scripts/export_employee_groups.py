"""Export evidence-based business grouping without changing access privileges."""
import collections
import csv
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
load_dotenv(os.environ['MCP_ENV_FILE'],override=True,encoding='utf-8-sig')
from mcp_server.tools import _get_pos_conn


def main():
    with _get_pos_conn() as conn:
        records=conn.execute('''SELECT s."Id"::text,s."Code",s."Name",a."RoleCode",
          COALESCE(s."AmisDepartmentName",''),
          (SELECT COUNT(*) FROM "StaffAsignSaleZone" z WHERE z."StaffId"=s."Id" AND z."DeleteAt" IS NULL),
          (SELECT COUNT(*) FROM "Customer" c WHERE c."RevenueStaffId"=s."Id" AND c."DeleteAt" IS NULL)
          FROM "Staff" s LEFT JOIN "Account" a ON a."Id"=s."AccountId" AND a."DeleteAt" IS NULL
          WHERE s."DeleteAt" IS NULL ORDER BY s."Code"''').fetchall()
    rows=[]
    for staff_id,code,name,source_role,department,zones,customers in records:
        if source_role=='WAREHOUSESTAFF':
            group,review='Kho','Can xac nhan warehouse_ids'
        elif source_role=='SALEMANAGER':
            group,review='Quan ly sale','Can xac nhan chi nhanh/vung'
        elif source_role=='SHIPPER':
            group,review='Giao nhan','Chua co policy giao nhan rieng'
        elif source_role=='AGENAI':
            group,review='Tai khoan dich vu AI','Can xac nhan chu tai khoan va scope'
        elif zones or customers:
            group,review='Sale / phu trach khach','Giu quyen staff theo RevenueStaffId'
        else:
            group,review='Chua xac dinh','Can xac nhan chuc danh; khong tu map BOD'
        rows.append(dict(username='rocky_'+code.strip().lower(),staff_code=code,staff_name=name,staff_id=staff_id,
            business_group=group,current_mcp_role='staff',source_role=source_role or '',department=department,
            assigned_zones=zones,assigned_customers=customers,review=review))
    output=Path('C:/ProgramData/RockyMCP/config/employee-onboarding')
    with (output/'employee-grouping-review.csv').open('w',encoding='utf-8-sig',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary={'total':len(rows),'groups':dict(collections.Counter(r['business_group'] for r in rows)),
        'permission_changes':0,'reason':'Business grouping requires verified role and scope; ambiguous BOD source not promoted'}
    (output/'employee-grouping-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=True))


if __name__=='__main__': main()
