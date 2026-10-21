# -*- coding: utf-8 -*-
"""PRODUCTION MCP Server with OAuth Login + PKCE - port 8085.

Supports Claude Desktop via mcp-remote (OAuth 2.1 with PKCE S256).
Also supports direct API key auth via Authorization: Bearer header.

Transport: streamable-http (endpoint /mcp)
"""
import sys
import os
import logging
import secrets
import hashlib
import base64
import time
import uvicorn
import psycopg
from urllib.parse import urlencode
from starlette.responses import JSONResponse, RedirectResponse, HTMLResponse
from starlette.routing import Route
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    env_path = Path(os.environ.get("MCP_ENV_FILE", PROJECT_ROOT / ".env"))
    if env_path.exists():
        # The service config is authoritative. Do not keep stale machine-level DSNs.
        # Windows editors may prepend a UTF-8 BOM. Read it explicitly so the
        # first key is not interpreted as "\ufeffDASHBOARD_PG_DSN".
        load_dotenv(env_path, override=True, encoding="utf-8-sig")
except Exception as e:
    print(f"Error loading env: {e}", file=sys.stderr)

log_dir = Path(os.environ.get("MCP_LOG_DIR", PROJECT_ROOT / "logs"))
log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=log_dir / "mcp_production.log",
    level=getattr(logging, os.environ.get("MCP_LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(message)s",
    filemode="a",
)
logging.info("Starting PRODUCTION MCP with OAuth+PKCE...")

os.environ.setdefault("MCP_REQUIRE_AUTH", "true")

from mcp_server.server import mcp
from mcp_server.auth import AuthMiddleware
from mcp_server.config import DASHBOARD_PG_DSN, MCP_AUTH_BACKEND, MCP_LOCAL_AUTH_DB_PATH
from mcp_server.local_auth import LocalAuthStore

_local_auth_store = LocalAuthStore(MCP_LOCAL_AUTH_DB_PATH) if MCP_AUTH_BACKEND == "sqlite" else None

# --- Transport: streamable-http serves at /mcp ---
app = mcp.http_app(transport="streamable-http")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_pkce(code_verifier: str, code_challenge: str) -> bool:
    """Verify PKCE S256: SHA256(code_verifier) base64url == code_challenge."""
    if not code_verifier or not code_challenge:
        return False
    computed = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('ascii')).digest()
    ).rstrip(b'=').decode('ascii')
    return computed == code_challenge


class AuthDatabaseUnavailable(RuntimeError):
    """The authentication database could not be reached reliably."""


def _with_auth_database(operation, operation_name: str):
    if not DASHBOARD_PG_DSN:
        raise AuthDatabaseUnavailable("DASHBOARD_PG_DSN is not configured")

    last_error = None
    for attempt in range(3):
        try:
            with psycopg.connect(DASHBOARD_PG_DSN, connect_timeout=5) as conn:
                return operation(conn)
        except Exception as exc:
            last_error = exc
            if attempt == 2:
                break
            logging.warning(
                "%s database attempt %s/3 failed: %s",
                operation_name,
                attempt + 1,
                type(exc).__name__,
            )
            time.sleep(0.25 * (attempt + 1))

    logging.error("%s database unavailable: %s", operation_name, type(last_error).__name__)
    raise AuthDatabaseUnavailable(f"{operation_name} database unavailable") from last_error


def verify_login(username: str, password: str):
    if _local_auth_store is not None:
        try:
            return _local_auth_store.verify_login(username, password)
        except Exception as exc:
            raise AuthDatabaseUnavailable("Local authentication unavailable") from exc

    def operation(conn):
        with conn.cursor() as cur:
            cur.execute("""
                SELECT api_key, user_id, role, name FROM api_keys
                WHERE username = %s AND password_hash = %s AND is_active = TRUE
            """, (username, hash_password(password)))
            return cur.fetchone()

    return _with_auth_database(operation, "Login verify")


def store_auth_code(code, user_id, api_key, redirect_uri, state, code_challenge=""):
    if _local_auth_store is not None:
        try:
            return _local_auth_store.store_auth_code(
                code, user_id, api_key, redirect_uri, state, code_challenge
            )
        except Exception as exc:
            raise AuthDatabaseUnavailable("Local authentication unavailable") from exc

    def operation(conn):
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO auth_codes (code, user_id, api_key, redirect_uri, state, code_challenge)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (code, user_id, api_key, redirect_uri, state, code_challenge or ""))
        conn.commit()
        return True

    return _with_auth_database(operation, "Store auth code")


def exchange_auth_code(code: str):
    """Exchange auth code for (api_key, user_id, code_challenge)."""
    if _local_auth_store is not None:
        try:
            return _local_auth_store.exchange_auth_code(code)
        except Exception as exc:
            raise AuthDatabaseUnavailable("Local authentication unavailable") from exc

    def operation(conn):
        with conn.cursor() as cur:
            cur.execute("""
                SELECT api_key, user_id, code_challenge FROM auth_codes
                WHERE code = %s AND used = FALSE
                AND created_at > NOW() - INTERVAL '10 minutes'
            """, (code,))
            row = cur.fetchone()
            if row:
                cur.execute("UPDATE auth_codes SET used = TRUE WHERE code = %s", (code,))
                conn.commit()
            return row

    return _with_auth_database(operation, "Exchange auth code")


# ---------------------------------------------------------------------------
# Login HTML (CSS braces escaped for .format())
# ---------------------------------------------------------------------------

LOGIN_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rocky Dashboard - Login</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            display: flex; align-items: center; justify-content: center;
        }}
        .card {{
            background: rgba(255,255,255,0.95);
            border-radius: 16px; padding: 40px;
            width: 100%; max-width: 400px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        .logo {{ text-align: center; margin-bottom: 24px; }}
        .logo h1 {{ font-size: 24px; color: #1a1a2e; }}
        .logo p {{ color: #666; font-size: 14px; margin-top: 4px; }}
        .field {{ margin-bottom: 20px; }}
        .field label {{ display: block; font-size: 13px; font-weight: 600; color: #333; margin-bottom: 6px; }}
        .field input {{
            width: 100%; padding: 12px 16px;
            border: 2px solid #e0e0e0; border-radius: 8px;
            font-size: 15px; outline: none;
        }}
        .field input:focus {{ border-color: #0f3460; }}
        .btn {{
            width: 100%; padding: 14px;
            background: #0f3460; color: white; border: none;
            border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer;
        }}
        .btn:hover {{ background: #1a4a7a; }}
        .error {{
            background: #fee; border: 1px solid #fcc; color: #c33;
            padding: 10px 14px; border-radius: 8px; font-size: 13px;
            margin-bottom: 16px; display: {error_display};
        }}
        .info {{ text-align: center; margin-top: 16px; font-size: 12px; color: #999; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="logo">
            <h1>Rocky Lens Dashboard</h1>
            <p>MCP Server Authentication</p>
        </div>
        <div class="error">{error_message}</div>
        <form method="POST" action="/login">
            <input type="hidden" name="redirect_uri" value="{redirect_uri}">
            <input type="hidden" name="state" value="{state}">
            <input type="hidden" name="code_challenge" value="{code_challenge}">
            <input type="hidden" name="code_challenge_method" value="{code_challenge_method}">
            <div class="field">
                <label>Username</label>
                <input type="text" name="username" placeholder="Enter username" required autofocus>
            </div>
            <div class="field">
                <label>Password</label>
                <input type="password" name="password" placeholder="Enter password" required>
            </div>
            <button type="submit" class="btn">Login</button>
        </form>
        <div class="info">Authorized access only.</div>
    </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# OAuth Endpoints
# ---------------------------------------------------------------------------

def get_base_url(request):
    forwarded_host = request.headers.get("x-forwarded-host")
    forwarded_proto = request.headers.get("x-forwarded-proto", "https")
    if forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}"
    return str(request.base_url).rstrip("/")


async def oauth_metadata(request):
    """RFC 8414: OAuth Authorization Server Metadata."""
    base = get_base_url(request)
    return JSONResponse({
        "issuer": base,
        "authorization_endpoint": f"{base}/authorize",
        "token_endpoint": f"{base}/token",
        "registration_endpoint": f"{base}/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "token_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": ["mcp"],
        "code_challenge_methods_supported": ["S256"]
    })


async def oauth_protected_resource(request):
    """RFC 9728: OAuth Protected Resource Metadata."""
    base = get_base_url(request)
    return JSONResponse({
        "resource": f"{base}/mcp",
        "authorization_servers": [base],
        "bearer_methods_supported": ["header"],
        "scopes_supported": ["mcp"]
    })


async def oauth_register(request):
    """RFC 7591: Dynamic Client Registration."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    redirect_uris = body.get("redirect_uris", [])
    response_data = {
        "client_id": "rocky-mcp-client",
        "client_secret": "",
        "client_id_issued_at": 1600000000,
        "client_secret_expires_at": 0,
        "token_endpoint_auth_method": "none",
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
        "redirect_uris": redirect_uris,
    }
    for k, v in body.items():
        response_data[k] = v
    logging.info(f"Client registered: redirect_uris={redirect_uris}")
    return JSONResponse(response_data)


async def oauth_authorize(request):
    """Authorization endpoint - preserves ALL OAuth params including PKCE."""
    params = dict(request.query_params)
    redirect_uri = params.get("redirect_uri", "")
    state = params.get("state", "")
    code_challenge = params.get("code_challenge", "")
    code_challenge_method = params.get("code_challenge_method", "")

    if not code_challenge or code_challenge_method != "S256":
        return JSONResponse({
            "error": "invalid_request",
            "error_description": "PKCE with code_challenge_method=S256 is required",
        }, status_code=400)

    logging.info(f"OAuth authorize: redirect_uri={redirect_uri}, has_pkce={bool(code_challenge)}")

    base = get_base_url(request)
    login_params = urlencode({
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
    })
    return RedirectResponse(url=f"{base}/login?{login_params}")


async def login_page(request):
    """Login page - GET shows form, POST validates and redirects with auth code."""
    if request.method == "GET":
        params = dict(request.query_params)
        redirect_uri = params.get("redirect_uri", "")
        state = params.get("state", "")
        code_challenge = params.get("code_challenge", "")
        code_challenge_method = params.get("code_challenge_method", "")
        html = LOGIN_HTML_TEMPLATE.format(
            redirect_uri=redirect_uri,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            error_display="none",
            error_message=""
        )
        from mcp_server.portal_policy import enabled as portal_enabled
        if portal_enabled():
            from html import escape
            portal_url='/portal/login?'+urlencode(params)
            html=html.replace('<form method="POST" action="/login">',
                '<p><a href="'+escape(portal_url,quote=True)+'">Sign in with your Rocky Dashboard account</a></p><form method="POST" action="/login">',1)
        return HTMLResponse(html)

    # POST - validate credentials
    form = await request.form()
    username = form.get("username", "").strip()
    password = form.get("password", "")
    redirect_uri = form.get("redirect_uri", "")
    state = form.get("state", "")
    code_challenge = form.get("code_challenge", "")
    code_challenge_method = form.get("code_challenge_method", "")

    try:
        result = verify_login(username, password)
    except AuthDatabaseUnavailable:
        logging.error("Login unavailable for user %s", username)
        html = LOGIN_HTML_TEMPLATE.format(
            redirect_uri=redirect_uri,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            error_display="block",
            error_message="Authentication service is temporarily unavailable. Please retry."
        )
        return HTMLResponse(html, status_code=503)

    if result:
        api_key, user_id, role, name = result
        from mcp_server.portal_policy import enabled as portal_enabled
        if portal_enabled() and role != 'admin':
            return RedirectResponse('/portal/login?'+urlencode({'redirect_uri':redirect_uri,'state':state,
                'code_challenge':code_challenge,'code_challenge_method':code_challenge_method}),status_code=303)
        code = secrets.token_urlsafe(32)
        try:
            store_auth_code(code, user_id, api_key, redirect_uri, state, code_challenge)
        except AuthDatabaseUnavailable:
            logging.error("Auth code storage unavailable for user %s", username)
            html = LOGIN_HTML_TEMPLATE.format(
                redirect_uri=redirect_uri,
                state=state,
                code_challenge=code_challenge,
                code_challenge_method=code_challenge_method,
                error_display="block",
                error_message="Authentication service is temporarily unavailable. Please retry."
            )
            return HTMLResponse(html, status_code=503)
        logging.info(f"Login OK: {username} ({role}) -> redirect to {redirect_uri[:60]}")

        # Build redirect target
        redirect_target = f"{redirect_uri}?code={code}"
        if state:
            redirect_target += f"&state={state}"

        return RedirectResponse(url=redirect_target, status_code=302)
    else:
        logging.warning(f"Login FAILED: {username}")
        html = LOGIN_HTML_TEMPLATE.format(
            redirect_uri=redirect_uri,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            error_display="block",
            error_message="Invalid username or password."
        )
        return HTMLResponse(html, status_code=401)


async def oauth_token(request):
    """Token exchange with PKCE verification."""
    try:
        form_data = await request.form()
        code = form_data.get("code") or ""
        code_verifier = form_data.get("code_verifier") or ""
        grant_type = form_data.get("grant_type") or ""
    except Exception:
        return JSONResponse({"error": "invalid_request"}, status_code=400)

    logging.info(f"Token exchange: grant_type={grant_type}, has_verifier={bool(code_verifier)}")

    if not code:
        return JSONResponse({"error": "invalid_request", "error_description": "Missing code"}, status_code=400)
    if grant_type != "authorization_code":
        return JSONResponse({"error": "unsupported_grant_type"}, status_code=400)

    from mcp_server.portal_policy import enabled as portal_enabled
    if portal_enabled() and code.startswith('rkpc_'):
        from mcp_server.portal_oauth import exchange_portal_code
        return exchange_portal_code(form_data)

    try:
        result = exchange_auth_code(code)
    except AuthDatabaseUnavailable:
        return JSONResponse(
            {
                "error": "temporarily_unavailable",
                "error_description": "Authentication service is temporarily unavailable. Please retry.",
            },
            status_code=503,
        )
    if not result:
        logging.warning("Token exchange: invalid or expired code")
        return JSONResponse({"error": "invalid_grant", "error_description": "Code expired or already used"}, status_code=400)

    api_key, user_id, stored_challenge = result

    # Verify PKCE if code_challenge was stored
    if stored_challenge:
        if not code_verifier:
            logging.warning("Token exchange: PKCE required but no code_verifier")
            return JSONResponse({"error": "invalid_grant", "error_description": "code_verifier required"}, status_code=400)
        if not verify_pkce(code_verifier, stored_challenge):
            logging.warning("Token exchange: PKCE verification FAILED")
            return JSONResponse({"error": "invalid_grant", "error_description": "PKCE verification failed"}, status_code=400)
        logging.info("PKCE verification OK")

    return JSONResponse({
        "access_token": api_key,
        "token_type": "Bearer",
        "expires_in": 86400,
        "scope": "mcp"
    })


# ---------------------------------------------------------------------------
# Register routes (BEFORE AuthMiddleware wraps the app)
# ---------------------------------------------------------------------------

app.routes.insert(0, Route("/.well-known/oauth-authorization-server", oauth_metadata, methods=["GET"]))
app.routes.insert(0, Route("/.well-known/openid-configuration", oauth_metadata, methods=["GET"]))
app.routes.insert(0, Route("/.well-known/oauth-protected-resource", oauth_protected_resource, methods=["GET"]))
app.routes.insert(0, Route("/.well-known/oauth-protected-resource/mcp", oauth_protected_resource, methods=["GET"]))
app.routes.insert(0, Route("/register", oauth_register, methods=["POST"]))
app.routes.insert(0, Route("/authorize", oauth_authorize, methods=["GET"]))
app.routes.insert(0, Route("/login", login_page, methods=["GET", "POST"]))
app.routes.insert(0, Route("/token", oauth_token, methods=["POST"]))
from mcp_server.portal_oauth import portal_login, portal_logout
app.routes.insert(0, Route('/portal/login',portal_login,methods=['GET','POST']))
app.routes.insert(0, Route('/portal/logout',portal_logout,methods=['POST']))
from mcp_server.portal_uat import begin as portal_uat_begin, callback as portal_uat_callback
app.routes.insert(0, Route('/portal/uat',portal_uat_begin,methods=['GET']))
app.routes.insert(0, Route('/portal/uat/callback',portal_uat_callback,methods=['GET']))

# Health check
async def health_check(request):
    return JSONResponse({"status": "ok", "server": "Rocky Dashboard MCP", "transport": "streamable-http"})

app.routes.insert(0, Route("/health", health_check, methods=["GET"]))


async def root_compat(request):
    """Compatibility endpoint for clients that probe / before /mcp."""
    base = get_base_url(request)
    if request.method == "POST":
        return RedirectResponse(url=f"{base}/mcp", status_code=307)
    return JSONResponse({
        "status": "ok",
        "server": "Rocky Dashboard MCP",
        "transport": "streamable-http",
        "mcp_endpoint": f"{base}/mcp",
        "oauth_metadata": f"{base}/.well-known/oauth-authorization-server",
        "note": "Use the /mcp endpoint for Claude custom connector."
    })


async def legacy_sse_compat(request):
    """Compatibility endpoint for old /sse docs or clients."""
    base = get_base_url(request)
    if request.method == "POST":
        return RedirectResponse(url=f"{base}/mcp", status_code=307)
    return JSONResponse({
        "status": "moved",
        "server": "Rocky Dashboard MCP",
        "old_endpoint": f"{base}/sse",
        "mcp_endpoint": f"{base}/mcp",
        "transport": "streamable-http",
        "note": "Legacy SSE is disabled; use /mcp."
    }, status_code=200)


app.routes.insert(0, Route("/", root_compat, methods=["GET", "POST"]))
app.routes.insert(0, Route("/mcp/", root_compat, methods=["GET", "POST"]))
app.routes.insert(0, Route("/sse", legacy_sse_compat, methods=["GET", "POST"]))

# Wrap with auth middleware
app = AuthMiddleware(app)

logging.info("PRODUCTION server ready: streamable-http + OAuth PKCE")

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.environ.get("MCP_HOST", "127.0.0.1"),
        port=int(os.environ.get("MCP_PORT", "8085")),
        timeout_keep_alive=int(os.environ.get("MCP_KEEPALIVE_SEC", "120")),
    )
