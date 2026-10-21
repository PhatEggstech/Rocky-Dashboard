"""Separate portal sign-in and PKCE code exchange; local admin auth is untouched."""
import base64
import hashlib
import hmac
from html import escape
import json
import re
import secrets
import time
from urllib.parse import urlencode,urlparse,parse_qsl,urlunparse

from starlette.responses import HTMLResponse,JSONResponse,RedirectResponse
from starlette.concurrency import run_in_threadpool
from .portal_runtime import store


def _redirect_ok(uri):
    parsed=urlparse(uri)
    return bool(parsed.hostname and not parsed.username and not parsed.password and not parsed.fragment
        and (parsed.scheme=='https' or (parsed.scheme=='http' and parsed.hostname in {'127.0.0.1','localhost','::1'})))


def _tables(vault):
    with vault._connect() as conn:
        conn.executescript('''CREATE TABLE IF NOT EXISTS portal_oauth_flows(
            flow_hash TEXT PRIMARY KEY, expires_at REAL NOT NULL, payload BLOB NOT NULL);
            CREATE TABLE IF NOT EXISTS portal_oauth_codes(
            code_hash TEXT PRIMARY KEY, expires_at REAL NOT NULL, payload BLOB NOT NULL);''')
        conn.execute('DELETE FROM portal_oauth_flows WHERE expires_at <= ?',(time.time(),))
        conn.execute('DELETE FROM portal_oauth_codes WHERE expires_at <= ?',(time.time(),))


def _hash(value):return hashlib.sha256(value.encode()).hexdigest()


def _flow_cookie(flow):
    return 'rk_portal_flow_'+_hash(flow)[:20]


def _callback_origin(uri):
    parsed=urlparse(uri)
    host=parsed.hostname.encode('idna').decode('ascii')
    if not re.fullmatch(r'[A-Za-z0-9.:-]+',host):
        raise ValueError('Invalid callback host')
    if ':' in host:host='['+host+']'
    return parsed.scheme+'://'+host+(':'+str(parsed.port) if parsed.port else '')


def _flow_failure(request,error):
    if 'text/html' in request.headers.get('accept',''):
        return HTMLResponse('''<!doctype html><html lang="vi"><meta charset="utf-8">
            <title>Rocky Sign In</title><h1>Restart Rocky sign-in</h1>
            <p>The sign-in session expired or its browser cookie is missing.</p>
            <p>Close older sign-in tabs and reconnect Rocky from ChatGPT or Claude.
            Allow cookies for this site. No password change is needed.</p></html>''',status_code=400,
            headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer'})
    return JSONResponse({'error':error},status_code=400)


def _take(vault,table,field,token):
    with vault._connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=conn.execute(f'SELECT payload FROM {table} WHERE {field}=? AND expires_at>?',(_hash(token),time.time())).fetchone()
        if row is None:return None
        conn.execute(f'DELETE FROM {table} WHERE {field}=?',(_hash(token),))
        return json.loads(vault._cipher.decrypt(row[0]))


async def portal_login(request):
    from .portal_policy import enabled
    if not enabled():return JSONResponse({'error':'not_enabled'},status_code=404)
    try:
        vault=store();_tables(vault)
        if request.method=='GET':
            params=dict(request.query_params)
            redirect=params.get('redirect_uri','')
            challenge=params.get('code_challenge','')
            if not _redirect_ok(redirect) or params.get('code_challenge_method')!='S256' or not re.fullmatch(r'[A-Za-z0-9_-]{43}',challenge):
                return JSONResponse({'error':'invalid_request'},status_code=400)
            flow=secrets.token_urlsafe(32)
            with vault._connect() as conn:
                conn.execute('INSERT INTO portal_oauth_flows VALUES (?,?,?)',
                    (_hash(flow),time.time()+600,vault._cipher.encrypt(json.dumps(params).encode())))
            html=f'''<!doctype html><html lang="vi"><meta charset="utf-8"><title>Rocky Dashboard Sign In</title>
                <h1>Rocky Dashboard</h1><p>Connect your own Rocky account to MCP.</p>
                <p>Return to: {escape(urlparse(redirect).netloc)}</p>
                <form method="post" action="/portal/login"><input type="hidden" name="flow" value="{escape(flow,quote=True)}">
                <label>Rocky username <input name="username" autocomplete="username" required maxlength="200"></label>
                <label>Password <input type="password" name="password" autocomplete="current-password" required maxlength="1024"></label>
                <button type="submit">Sign In To Rocky</button></form></html>'''
            response=HTMLResponse(html,headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer',
                'Content-Security-Policy':"default-src 'none'; form-action 'self' "+_callback_origin(redirect)+"; frame-ancestors 'none'"})
            response.set_cookie(_flow_cookie(flow),flow,httponly=True,secure=request.url.scheme=='https' or request.headers.get('x-forwarded-proto')=='https',samesite='lax',max_age=600,path='/portal/login')
            return response
        form=await request.form()
        flow=str(form.get('flow',''))
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}',flow):
            return _flow_failure(request,'invalid_login_flow')
        cookie=request.cookies.get(_flow_cookie(flow),request.cookies.get('rk_portal_flow',''))
        if not hmac.compare_digest(flow,cookie):
            return _flow_failure(request,'invalid_login_flow')
        username=str(form.get('username','')).strip()
        password=str(form.get('password',''))
        if not username or not password:
            return JSONResponse({'error':'credentials_required'},status_code=422)
        if len(username)>200 or len(password)>1024:
            return JSONResponse({'error':'invalid_credentials_format'},status_code=400)
        params=_take(vault,'portal_oauth_flows','flow_hash',flow)
        if not params:return _flow_failure(request,'login_flow_expired')
        from .portal_identity import authenticate,PortalIdentityError
        try:
            identity=await run_in_threadpool(authenticate,username,password)
        except PortalIdentityError:
            return JSONResponse({'error':'Rocky sign-in failed; restart sign-in and try again'},status_code=401)
        raw=vault.create_session(identity['rk_user_id'],identity['rk_user_id'],identity['access_token'],identity['refresh_token'],
            token_expires_at=identity['token_expires_at'],session_expires_at=time.time()+7*86400)
        code='rkpc_'+secrets.token_urlsafe(32)
        grant={'session':raw,'redirect_uri':params['redirect_uri'],'challenge':params['code_challenge']}
        with vault._connect() as conn:
            conn.execute('INSERT INTO portal_oauth_codes VALUES (?,?,?)',(_hash(code),time.time()+120,vault._cipher.encrypt(json.dumps(grant).encode())))
        parsed=urlparse(params['redirect_uri']);query=dict(parse_qsl(parsed.query))
        query.update(code=code)
        if params.get('state'):query['state']=params['state']
        response=RedirectResponse(urlunparse(parsed._replace(query=urlencode(query))),status_code=302,headers={'Cache-Control':'no-store'})
        response.delete_cookie(_flow_cookie(flow),path='/portal/login')
        if request.cookies.get('rk_portal_flow')==flow:
            response.delete_cookie('rk_portal_flow',path='/portal/login')
        return response
    except Exception:
        return JSONResponse({'error':'Portal sign-in service unavailable'},status_code=503)


def exchange_portal_code(form):
    try:
        vault=store();_tables(vault)
        code=str(form.get('code',''));verifier=str(form.get('code_verifier',''))
        if not re.fullmatch(r'[A-Za-z0-9._~-]{43,128}',verifier):
            return JSONResponse({'error':'invalid_grant'},status_code=400)
        grant=_take(vault,'portal_oauth_codes','code_hash',code)
        if grant is None:return JSONResponse({'error':'invalid_grant'},status_code=400)
        challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        if not hmac.compare_digest(challenge,grant['challenge']) or form.get('redirect_uri')!=grant['redirect_uri']:
            vault.revoke_session(grant['session'])
            return JSONResponse({'error':'invalid_grant'},status_code=400)
        session=vault.get_session(grant['session'])
        if not session:return JSONResponse({'error':'invalid_grant'},status_code=400)
        return JSONResponse({'access_token':grant['session'],'token_type':'Bearer','expires_in':max(0,int(session['session_expires_at']-time.time())),'scope':'mcp'},
            headers={'Cache-Control':'no-store','Pragma':'no-cache'})
    except Exception:
        return JSONResponse({'error':'temporarily_unavailable'},status_code=503)


async def portal_logout(request):
    user=None
    from .auth import get_current_user
    user=get_current_user()
    if not user or not user.portal_session:return JSONResponse({'error':'Unauthorized'},status_code=401)
    store().revoke_session(user.portal_session)
    return JSONResponse({'revoked':True},headers={'Cache-Control':'no-store'})
