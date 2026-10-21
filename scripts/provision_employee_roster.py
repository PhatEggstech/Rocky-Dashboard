"""Idempotent bulk staff provisioning; preserves existing identities and passwords."""
import argparse
import base64
import csv
import hashlib
import json
import os
import re
import secrets
import sqlite3
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def username_for(code):
    code = str(code or '').strip().lower()
    if not code or not re.fullmatch(r'[a-z0-9_-]+', code):
        raise ValueError('Employee code is empty or unsuitable for an unambiguous username')
    return 'rocky_' + code


def provision(store, rows, *, credentials_path, inventory_path):
    store.ensure_schema()
    names = [username_for(row['staff_code']) for row in rows]
    if len(set(names)) != len(names):
        raise ValueError('Duplicate normalized employee codes; bulk provisioning aborted')
    if len({row['staff_id'] for row in rows}) != len(rows):
        raise ValueError('Duplicate employee UUIDs')
    created, preserved, credentials, inventory = 0, 0, [], []
    with store._connect() as conn:
        before = conn.execute('SELECT id,username,api_key,role,is_active FROM users ORDER BY id').fetchall()
        baseline = [tuple(r) for r in before]
        for row, username in zip(rows, names):
            previous = conn.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
            if previous:
                if str(previous['staff_id']) != row['staff_id'] or previous['role'] != 'staff':
                    raise ValueError('Existing username belongs to a different employee or role')
                preserved += 1
                active = previous['is_active']
            else:
                password = secrets.token_urlsafe(24)
                salt = os.urandom(16)
                api_key = 'rk_' + secrets.token_urlsafe(32)
                # Only State=1 accounts are activated. Other records are created
                # disabled until their employment status is reviewed.
                active = int(str(row['staff_state']) == '1')
                cursor = conn.execute('''INSERT INTO users
                    (username,password_salt,password_hash,api_key,role,store_id,staff_id,name,is_active,created_at)
                    VALUES (?,?,?,?, 'staff',NULL,?,?,?,?)''',
                    (username,base64.b64encode(salt).decode(),store._hash_password(password,salt),api_key,
                     row['staff_id'],row['staff_name'],active,int(time.time())))
                conn.execute('INSERT INTO user_policies(user_id,can_view_cost,include_hmk) VALUES (?,0,0)',(cursor.lastrowid,))
                credentials.append({'username':username,'password':password,'staff_code':row['staff_code'],'staff_name':row['staff_name'],'active':active})
                created += 1
            inventory.append({**row,'username':username,'role':'staff','active':active,
                'include_hmk':False,'can_view_cost':False,'scope':'personal / Customer.RevenueStaffId',
                'credential_status':'new' if not previous else 'preserved'})
        after_existing = [tuple(conn.execute('SELECT id,username,api_key,role,is_active FROM users WHERE id=?',(r[0],)).fetchone()) for r in baseline]
        if after_existing != baseline:
            raise AssertionError('Existing account changed')
        # Persist the delivery files before transaction commit. A disk failure
        # rolls back newly inserted accounts rather than losing their passwords.
        if credentials:
            with credentials_path.open('x',encoding='utf-8-sig',newline='') as handle:
                writer=csv.DictWriter(handle,fieldnames=list(credentials[0]))
                writer.writeheader()
                writer.writerows(credentials)
        with inventory_path.open('x',encoding='utf-8-sig',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=list(inventory[0]))
            writer.writeheader()
            writer.writerows(inventory)
    verified=0
    for record in credentials:
        if record['active']:
            login=store.verify_login(record['username'],record['password'])
            if not login or login[2]!='staff': raise AssertionError('New employee login verification failed')
            identity=store.lookup_api_key(login[0])
            expected=next(r for r in inventory if r['username']==record['username'])
            if str(identity['staff_id']) != expected['staff_id']: raise AssertionError('Wrong employee mapping')
            verified+=1
    return {'created':created,'preserved':preserved,'total_employee_accounts':len(inventory),
        'activated':sum(r['active'] for r in inventory),'login_verified':verified,'existing_accounts_unchanged':True}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--target',choices=['staging','production'],required=True)
    args=parser.parse_args()
    load_dotenv(os.environ['MCP_ENV_FILE'],override=True,encoding='utf-8-sig')
    from mcp_server.config import MCP_LOCAL_AUTH_DB_PATH, MCP_AUTH_BACKEND
    from mcp_server.local_auth import LocalAuthStore
    from mcp_server.tools import _get_pos_conn
    if MCP_AUTH_BACKEND!='sqlite': raise RuntimeError('Requires deployed SQLite auth')
    is_stage='employee-staging' in MCP_LOCAL_AUTH_DB_PATH
    if is_stage != (args.target=='staging'): raise RuntimeError('Target does not match runtime auth DB')
    with _get_pos_conn() as conn:
        records=conn.execute('SELECT "Id"::text,"Code","Name","State"::text FROM "Staff" WHERE "DeleteAt" IS NULL ORDER BY "Code","Id"').fetchall()
    rows=[dict(zip(('staff_id','staff_code','staff_name','staff_state'),r)) for r in records]
    if not rows: raise RuntimeError('Staff directory is empty')
    output=Path('C:/ProgramData/RockyMCP/config/employee-onboarding')
    output.mkdir(parents=True,exist_ok=True)
    stamp=time.strftime('%Y%m%d-%H%M%S')
    credentials=output/f'{args.target}-credentials-{stamp}.csv'
    inventory=output/f'{args.target}-inventory-{stamp}.csv'
    backup=output/f'{args.target}-auth-before-{stamp}.sqlite3'
    with sqlite3.connect(MCP_LOCAL_AUTH_DB_PATH) as source, sqlite3.connect(backup) as destination:
        source.backup(destination)
    report=provision(LocalAuthStore(MCP_LOCAL_AUTH_DB_PATH),rows,credentials_path=credentials,inventory_path=inventory)
    report.update(target=args.target,inventory_file=str(inventory),credentials_file=str(credentials) if credentials.exists() else None,backup=str(backup))
    (output/f'{args.target}-report-{stamp}.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__': main()
