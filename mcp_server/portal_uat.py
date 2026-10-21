"""Staging-only browser entry point for two-user portal acceptance."""
import base64
import hashlib
from html import escape
import json
import os
import secrets
import time
from urllib.parse import urlencode
from starlette.responses import HTMLResponse,JSONResponse,RedirectResponse
from .portal_runtime import store


def enabled():
    from .portal_policy import enabled as portal_enabled
    return portal_enabled() and os.environ.get('MCP_PORTAL_UAT_ENABLED','false').lower()=='true'


def _table(vault):
    with vault._connect() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS portal_uat_flows(
            id TEXT PRIMARY KEY, expires_at REAL NOT NULL, payload BLOB NOT NULL)''')
        conn.execute('DELETE FROM portal_uat_flows WHERE expires_at<=?',(time.time(),))
        conn.execute('''CREATE TABLE IF NOT EXISTS portal_uat_accounts(
            rk_user_id TEXT PRIMARY KEY, tested_at REAL NOT NULL, payload BLOB NOT NULL)''')


async def begin(request):
    if not enabled():return JSONResponse({'error':'not_enabled'},status_code=404)
    vault=store();_table(vault)
    state=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(48)
    callback=str(request.base_url).rstrip('/')+'/portal/uat/callback'
    with vault._connect() as conn:
        conn.execute('INSERT INTO portal_uat_flows VALUES (?,?,?)',(hashlib.sha256(state.encode()).hexdigest(),time.time()+600,
            vault._cipher.encrypt(json.dumps({'verifier':verifier,'callback':callback}).encode())))
    challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    response=RedirectResponse('/portal/login?'+urlencode({'redirect_uri':callback,'state':state,'code_challenge':challenge,'code_challenge_method':'S256'}))
    response.set_cookie('rk_uat_state',state,httponly=True,samesite='lax',max_age=600,path='/portal/uat',secure=request.url.scheme=='https')
    return response


async def callback(request):
    if not enabled():return JSONResponse({'error':'not_enabled'},status_code=404)
    state=request.query_params.get('state','')
    if not state or not secrets.compare_digest(state,request.cookies.get('rk_uat_state','')):
        return JSONResponse({'error':'invalid_state'},status_code=400)
    vault=store();_table(vault)
    key=hashlib.sha256(state.encode()).hexdigest()
    with vault._connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        flow=conn.execute('SELECT payload FROM portal_uat_flows WHERE id=? AND expires_at>?',(key,time.time())).fetchone()
        conn.execute('DELETE FROM portal_uat_flows WHERE id=?',(key,))
    if not flow:return JSONResponse({'error':'flow_expired'},status_code=400)
    data=json.loads(vault._cipher.decrypt(flow[0]))
    from .portal_oauth import exchange_portal_code
    response=exchange_portal_code({'code':request.query_params.get('code',''),'code_verifier':data['verifier'],'redirect_uri':data['callback']})
    if response.status_code!=200:return response
    raw=json.loads(response.body)['access_token']
    session=vault.get_session(raw)
    with vault._connect() as conn:
        conn.execute('INSERT OR REPLACE INTO portal_uat_accounts VALUES (?,?,?)',
            (session['rk_user_id'],time.time(),vault._cipher.encrypt(json.dumps({'session':raw}).encode())))
        count=conn.execute('SELECT COUNT(*) FROM portal_uat_accounts').fetchone()[0]
    html=f'''<!doctype html><html lang="vi"><meta charset="utf-8"><title>Rocky Staging UAT</title>
        <h1>Rocky Staging UAT</h1><p>Sign-in successful.</p>
        <p>RK identity: {escape(session['rk_user_id'])}</p><p>Distinct accounts signed in: {count}</p>
        <p>RK tokens are encrypted on the server. Production admin was not changed.</p>
        <a href="/portal/uat">Sign in with the next Rocky account</a></html>'''
    return HTMLResponse(html,headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer',
        'Content-Security-Policy':"default-src 'none'; frame-ancestors 'none'"})
