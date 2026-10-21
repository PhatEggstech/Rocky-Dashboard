"""Server-only release snapshot and canary checks; never export credentials."""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
from dotenv import load_dotenv,dotenv_values
from fastmcp import Client
import httpx

ROOT=Path('C:/ProgramData/RockyMCP')
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))


def fingerprint(conn):
    state={table:conn.execute('SELECT * FROM '+table+' ORDER BY 1,2').fetchall()
        for table in ('users','user_policies','user_warehouses','user_sale_zones')}
    return hashlib.sha256(json.dumps(state,sort_keys=True,default=str).encode()).hexdigest()


async def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['snapshot','check']);parser.add_argument('--backup',required=True);parser.add_argument('--port',type=int,default=8087)
    args=parser.parse_args();backup=Path(args.backup)
    load_dotenv(ROOT/'config/.env',override=True,encoding='utf-8-sig')
    db=os.environ['MCP_LOCAL_AUTH_DB_PATH']
    with sqlite3.connect(db) as conn:
        digest=fingerprint(conn)
        admin=conn.execute("SELECT api_key FROM users WHERE username='admin' AND is_active=1").fetchone()[0]
        staff=conn.execute("SELECT api_key FROM users WHERE role='staff' AND is_active=1 LIMIT 1").fetchone()[0]
        if args.mode=='snapshot':
            with sqlite3.connect(backup/'auth.sqlite3') as destination:
                conn.backup(destination)
                if destination.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise RuntimeError('Backup integrity failed')
            data={'identity_policy_sha256':digest,'env_sha256':hashlib.sha256((ROOT/'config/.env').read_bytes()).hexdigest(),
                'auth_db':db,'users':conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]}
            (backup/'baseline.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
            print('AUTH_SNAPSHOT=verified');return
    baseline=json.loads((backup/'baseline.json').read_text(encoding='utf-8'))
    checks=[{'case':'All identities and policy rows preserved','pass':digest==baseline['identity_policy_sha256']},
        {'case':'Original production env byte-for-byte preserved','pass':hashlib.sha256((ROOT/'config/.env').read_bytes()).hexdigest()==baseline['env_sha256']}]
    url=f'http://127.0.0.1:{args.port}/mcp'
    async with Client(url,auth=admin,timeout=30) as client:
        result=(await client.call_tool('query_raw_pos_sql_tool',{'sql':'SELECT 1 AS preserved_admin'})).data
        checks.append({'case':'Original admin key and SQL read path','pass':isinstance(result,dict) and not result.get('error')})
    async with httpx.AsyncClient(timeout=20) as client:
        response=await client.post(url,headers={'Authorization':'Bearer '+staff},json={})
        checks.append({'case':'Old nonadmin key cannot bypass RK sign-in','pass':response.status_code==401})
        response=await client.get(f'http://127.0.0.1:{args.port}/portal/uat')
        checks.append({'case':'UAT helper is disabled on production candidate','pass':response.status_code==404})
    from mcp_server.portal_sessions import PortalSessionStore
    stage=dotenv_values(ROOT/'config/.env.staging',encoding='utf-8-sig')
    stage_vault=PortalSessionStore(stage['MCP_PORTAL_SESSION_DB_PATH'],Path(stage['MCP_PORTAL_KEY_FILE']).read_bytes().strip())
    with stage_vault._connect() as conn:
        row=conn.execute('SELECT payload FROM portal_uat_accounts ORDER BY tested_at DESC LIMIT 1').fetchone()
    if row is None:raise RuntimeError('Real staging login required')
    stage_raw=json.loads(stage_vault._cipher.decrypt(row[0]))['session']
    session=stage_vault.get_session(stage_raw)
    vault=PortalSessionStore(ROOT/'config/portal-production.sqlite3',(ROOT/'config/portal-production.key').read_bytes().strip())
    raw=vault.create_session(session['user_id'],session['rk_user_id'],session['access_token'],session['refresh_token'],
        token_expires_at=session['token_expires_at'],session_expires_at=time.time()+600)
    try:
        async with Client(url,auth=raw,timeout=30) as client:
            for name,arguments in [('query_raw_sql_tool',{'sql':'SELECT 1'}),('query_raw_pos_sql_tool',{'sql':'SELECT 1'}),
                ('query_raw_wms_sql_tool',{'sql':'SELECT 1'}),('trigger_debt_reminders',{})]:
                result=(await client.call_tool(name,arguments)).data
                checks.append({'case':'Portal denied '+name,'pass':result.get('code')==403})
            result=(await client.call_tool('get_dashboard_order_overview',{'relative_period':'today'})).data
            checks.append({'case':'Strict GET-only data policy','pass':result.get('http_status')==403})
            fixture=json.loads((ROOT/'config/employee-onboarding/portal-groups-uat-20261015.json').read_text(encoding='utf-8'))['results'][0]
            result=(await client.call_tool('get_portal_record',{'resource':'order','object_id':fixture['fixture_id']})).data
            checks.append({'case':'Real user GET order returns API data','pass':isinstance(result.get('data'),dict) and bool(result['data']) and not result.get('error')})
    finally:
        vault.revoke_session(raw)
        vault.delete_expired()
    report={'pass':all(c['pass'] for c in checks),'checks':checks,'port':args.port,
        'known_limitations':['Read-only POST reports remain disabled','Legacy list/receipt SQL tools unavailable to portal users','One broad-rights RK account tested; sale cross-user ACL not validated']}
    (backup/f'check-{args.port}.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
    if not report['pass']:raise SystemExit(1)


if __name__=='__main__':asyncio.run(main())
