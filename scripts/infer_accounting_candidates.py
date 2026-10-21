"""Payment activity evidence; no accounting role is granted by this script."""
import csv
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
load_dotenv(os.environ['MCP_ENV_FILE'],override=True,encoding='utf-8-sig')
from mcp_server.tools import _get_pos_conn
from mcp_server.config import PAYMENT_COLLECTION_DOCUMENT_TYPE, PAYMENT_RECEIVE_DOCUMENT_TYPE


def main():
    with _get_pos_conn() as conn:
        records=conn.execute('''SELECT s."Id"::text,s."Code",s."Name",a."RoleCode",
            COUNT(*),COUNT(*) FILTER (WHERE p."DocumentType"=%s),COUNT(*) FILTER (WHERE p."DocumentType"=%s),
            COUNT(DISTINCT p."CustomerId"),COUNT(DISTINCT p."SiteId"),MAX(p."IssueAt")::text
            FROM "PaymentOrder" p JOIN "Staff" s ON s."Id"=p."StaffId" AND s."DeleteAt" IS NULL
            LEFT JOIN "Account" a ON a."Id"=s."AccountId" AND a."DeleteAt" IS NULL
            WHERE p."DeleteAt" IS NULL AND p."CancelAt" IS NULL AND p."CompleteAt" IS NOT NULL
            AND p."IssueAt">='2026-09-01'::date AND p."DocumentType" IN (%s,%s)
            GROUP BY s."Id",s."Code",s."Name",a."RoleCode" ORDER BY COUNT(*) DESC LIMIT 20''',
            (PAYMENT_COLLECTION_DOCUMENT_TYPE,PAYMENT_RECEIVE_DOCUMENT_TYPE,PAYMENT_COLLECTION_DOCUMENT_TYPE,PAYMENT_RECEIVE_DOCUMENT_TYPE)).fetchall()
    keys=('staff_id','staff_code','staff_name','source_role','completed_documents','allocate_documents','receive_documents','customers','sites','latest_issue_at')
    rows=[dict(zip(keys,row),classification='payment_operator_candidate',permission_applied=False,
        reason='Payment handling can be performed by sales or delivery staff; accountant role not proven') for row in records]
    output=Path('C:/ProgramData/RockyMCP/config/employee-onboarding/accounting-candidates.csv')
    with output.open('w',encoding='utf-8-sig',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]) if rows else keys)
        writer.writeheader();writer.writerows(rows)
    print(json.dumps({'payment_operator_candidates':len(rows),'accountant_roles_granted':0}))


if __name__=='__main__': main()
