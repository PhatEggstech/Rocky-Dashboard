"""Verify production OAuth and row filters without printing credentials."""
import asyncio
import base64
import csv
import hashlib
import json
import os
import secrets
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import httpx
from dotenv import load_dotenv

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
load_dotenv(os.environ['MCP_ENV_FILE'],override=True,encoding='utf-8-sig')
from fastmcp import Client
from mcp_server.local_auth import LocalAuthStore
from mcp_server.tools import _get_pos_conn


async def main():
    store=LocalAuthStore(os.environ['MCP_LOCAL_AUTH_DB_PATH'])
    folder=Path('C:/ProgramData/RockyMCP/config/employee-onboarding')
    path=max(folder.glob('production-credentials-*.csv'),key=lambda p:p.stat().st_mtime)
    credentials=list(csv.DictReader(path.open(encoding='utf-8-sig')))
    with _get_pos_conn() as conn:
        ids=[r[0] for r in conn.execute('''SELECT "RevenueStaffId"::text,COUNT(*) FROM "Customer"
          WHERE "DeleteAt" IS NULL AND "RevenueStaffId" IS NOT NULL AND COALESCE("IsHmkCustomer",FALSE)=FALSE
          GROUP BY "RevenueStaffId" ORDER BY COUNT(*) DESC LIMIT 3''').fetchall()]
    samples=[]
    for row in credentials:
        login=store.verify_login(row['username'],row['password'])
        assert login
        identity=store.lookup_api_key(login[0])
        if str(identity['staff_id']) in ids: samples.append((row,identity))
    results=[]
    for row,user in samples:
        verifier=secrets.token_urlsafe(48)
        challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        with httpx.Client(timeout=15,follow_redirects=False) as client:
            response=client.post('http://127.0.0.1:8085/login',data={
                'username':row['username'],'password':row['password'],'redirect_uri':'http://127.0.0.1/employee-test',
                'state':'employee-test','code_challenge':challenge,'code_challenge_method':'S256'})
            code=parse_qs(urlparse(response.headers.get('location','')).query).get('code',[''])[0]
            token=client.post('http://127.0.0.1:8085/token',data={'grant_type':'authorization_code','code':code,'code_verifier':verifier})
            assert response.status_code==302 and token.status_code==200
            bearer=token.json()['access_token']
        async with Client('http://127.0.0.1:8085/mcp',auth=bearer) as client:
            own=(await client.call_tool('get_customers',{'top_n':2})).data
            assert own.get('rows') and all(r['assigned_staff_id']==str(user['staff_id']) and not r['is_hmk_customer'] for r in own['rows'])
            denied=(await client.call_tool('query_raw_pos_sql_tool',{'sql':'SELECT 1'})).data
            assert denied.get('code')==403
            cost=(await client.call_tool('get_gpm',{'date_from':'2026-10-01','date_to':'2026-10-14'})).data
            assert cost.get('code')==403
        results.append({'username':row['username'],'oauth_login':'PASS','assigned_customers':'PASS','raw_sql_blocked':'PASS','cost_blocked':'PASS'})
    report={'verified_new_logins':len(credentials),'sampled_live_accounts':len(samples),'results':results,'pass':len(samples)==3}
    (folder/'production-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
    assert report['pass']


if __name__=='__main__': asyncio.run(main())
