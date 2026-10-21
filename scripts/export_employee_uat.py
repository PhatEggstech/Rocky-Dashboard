"""Export deployed employee permissions without tokens or password changes."""
import csv
import json
import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv


def main():
    load_dotenv(os.environ['MCP_ENV_FILE'], override=True, encoding='utf-8-sig')
    root = Path('C:/ProgramData/RockyMCP/config/employee-onboarding')
    source = root / 'production-credentials-20261014-121743.csv'
    with source.open(encoding='utf-8-sig', newline='') as handle:
        directory = {row['username']: row for row in csv.DictReader(handle)}
    with sqlite3.connect(os.environ['MCP_LOCAL_AUTH_DB_PATH']) as conn:
        conn.row_factory = sqlite3.Row
        records = conn.execute("""SELECT u.username,u.name,u.role,u.is_active,u.staff_id,u.store_id,
            COALESCE(p.include_hmk,0) AS include_hmk,COALESCE(p.can_view_cost,0) AS can_view_cost,
            COALESCE(p.all_sites,0) AS all_sites
            FROM users u LEFT JOIN user_policies p ON p.user_id=u.id
            WHERE u.username LIKE 'rocky_%' ORDER BY u.role,u.username""").fetchall()
    rows = []
    for record in records:
        row = dict(record)
        row['staff_code'] = directory.get(row['username'], {}).get('staff_code', '')
        row['status'] = 'Active' if row.pop('is_active') else 'Inactive'
        row['endpoint'] = 'https://mcp-rocky.eggstech.io/mcp'
        row['policy_note'] = 'Current production policy; pending assigned-orders-only restriction for staff'
        rows.append(row)
    target = root / 'employee-uat-current-20261014.csv'
    with target.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({'accounts':len(rows),'active':sum(r['status']=='Active' for r in rows),'export':str(target),'passwords_changed':False}))


if __name__ == '__main__':
    main()
