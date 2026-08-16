# -*- coding: utf-8 -*-
"""API Key authentication & role-based authorization for MCP Server.

Roles:
- admin: full access to all tools and all stores
- manager: data tools filtered to their store_id only, no raw SQL
- staff: personal data only (own sales, own picker stats), no raw SQL
- bod: approved executive reports across all stores, no raw SQL or operations

Usage:
  1. Middleware extracts Bearer token from Authorization header
  2. Looks up api_key in dashboard PG → resolves UserContext
  3. Sets contextvars so tool functions can read current user
  4. Permission decorators check role before executing tool logic
"""
from __future__ import annotations

import contextvars
import functools
import logging
import time
from dataclasses import dataclass, asdict
from typing import Callable

import psycopg
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .config import DASHBOARD_PG_DSN, MCP_AUTH_BACKEND, MCP_LOCAL_AUTH_DB_PATH
from .local_auth import LocalAuthStore

logger = logging.getLogger("mcp_auth")

# ---------------------------------------------------------------------------
# User Context (thread-safe via contextvars)
# ---------------------------------------------------------------------------

@dataclass
class UserContext:
    user_id: int
    role: str           # "admin", "manager", "staff", "bod"
    store_id: int | None  # None = all stores (admin / bod)
    staff_id: int | None  # POS Staff.Id for staff role
    name: str

    def to_dict(self) -> dict:
        return asdict(self)


# ContextVar holding current authenticated user (set per-request by middleware)
_current_user: contextvars.ContextVar[UserContext | None] = contextvars.ContextVar(
    'current_user', default=None
)


def get_current_user() -> UserContext | None:
    """Get the current authenticated user from request context."""
    return _current_user.get()


# ---------------------------------------------------------------------------
# API Key Cache (simple TTL cache to avoid DB hit every request)
# ---------------------------------------------------------------------------

_key_cache: dict[str, tuple[UserContext, float]] = {}
_CACHE_TTL = 300  # 5 minutes
_local_auth_store: LocalAuthStore | None = None


def _get_local_auth_store() -> LocalAuthStore:
    global _local_auth_store
    if _local_auth_store is None:
        _local_auth_store = LocalAuthStore(MCP_LOCAL_AUTH_DB_PATH)
    return _local_auth_store


def _lookup_api_key(api_key: str) -> UserContext | None:
    """Lookup API key in database, with simple cache."""
    now = time.time()
    
    # Check cache first
    if api_key in _key_cache:
        user, cached_at = _key_cache[api_key]
        if now - cached_at < _CACHE_TTL:
            return user
        else:
            del _key_cache[api_key]
    
    # Query the configured authorization store.
    try:
        if MCP_AUTH_BACKEND == "sqlite":
            row = _get_local_auth_store().lookup_api_key(api_key)
            if row:
                user = UserContext(
                    user_id=row["id"], role=row["role"], store_id=row["store_id"],
                    staff_id=row["staff_id"], name=row["name"],
                )
                _key_cache[api_key] = (user, now)
                return user
            return None
        if not DASHBOARD_PG_DSN:
            raise RuntimeError("DASHBOARD_PG_DSN is not configured")
        with psycopg.connect(DASHBOARD_PG_DSN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT user_id, role, store_id, staff_id, name
                    FROM api_keys
                    WHERE api_key = %s AND is_active = TRUE
                """, (api_key,))
                row = cur.fetchone()
                if row:
                    user = UserContext(
                        user_id=row[0],
                        role=row[1],
                        store_id=row[2],
                        staff_id=row[3],
                        name=row[4]
                    )
                    _key_cache[api_key] = (user, now)
                    return user
    except Exception as e:
        logger.error(f"API key lookup failed: {e}")
        # On DB error, check cache even if expired (graceful degradation)
        if api_key in _key_cache:
            return _key_cache[api_key][0]
    
    return None


def clear_key_cache():
    """Clear the API key cache (call after updating keys)."""
    _key_cache.clear()


# ---------------------------------------------------------------------------
# Starlette Auth Middleware
# ---------------------------------------------------------------------------

# Paths that don't require authentication (health + OAuth flow)
_PUBLIC_PATHS = {"/health", "/healthz", "/ping",
                 "/", "/mcp/", "/sse",
                 "/.well-known/oauth-authorization-server",
                 "/.well-known/openid-configuration",
                 "/.well-known/oauth-protected-resource",
                 "/.well-known/oauth-protected-resource/mcp",
                 "/register", "/authorize", "/token", "/login"}

# Environment variable to disable auth (transition period)
import os
REQUIRE_AUTH = os.environ.get("MCP_REQUIRE_AUTH", "true").lower() in ("true", "1", "yes")


class AuthMiddleware:
    """Pure ASGI middleware: validates API key from Authorization header."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # Build path from scope
        path = scope.get("path", "")

        # Skip auth for health checks
        if path in _PUBLIC_PATHS:
            await self.app(scope, receive, send)
            return

        # Extract Authorization header
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode("utf-8", errors="ignore")

        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:].strip()
            user = _lookup_api_key(api_key)

            if user:
                # Set user context for this request
                token = _current_user.set(user)
                try:
                    await self.app(scope, receive, send)
                finally:
                    _current_user.reset(token)
                return
            else:
                # Invalid key
                logger.warning(f"Invalid API key attempt: {api_key[:8]}...")
                response = JSONResponse(
                    {"error": "Invalid API key", "code": 401},
                    status_code=401
                )
                await response(scope, receive, send)
                return
        else:
            # No auth header
            if REQUIRE_AUTH:
                headers = dict(scope.get("headers", []))
                host = headers.get(b"x-forwarded-host", headers.get(b"host", b"localhost")).decode("utf-8")
                proto = headers.get(b"x-forwarded-proto", b"https").decode("utf-8")
                metadata_url = f"{proto}://{host}/.well-known/oauth-protected-resource/mcp"
                response = JSONResponse(
                    {"error": "Authorization required. Use header: Authorization: Bearer <your_api_key>", "code": 401},
                    status_code=401,
                    headers={"WWW-Authenticate": f'Bearer resource_metadata="{metadata_url}", scope="mcp"'},
                )
                await response(scope, receive, send)
                return
            else:
                # Auth not required (transition mode) - allow anonymous with admin access
                anon_user = UserContext(user_id=0, role="admin", store_id=None, staff_id=None, name="Anonymous")
                token = _current_user.set(anon_user)
                try:
                    await self.app(scope, receive, send)
                finally:
                    _current_user.reset(token)
                return


# ---------------------------------------------------------------------------
# Permission Decorators (apply to tool functions in server.py)
# ---------------------------------------------------------------------------

def require_role(*allowed_roles: str):
    """Block tool execution if current user's role is not in allowed_roles.
    
    Usage:
        @mcp.tool()
        @track_tool
        @require_role('admin')
        def query_raw_sql_tool(sql: str) -> dict: ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if user is None:
                return {"error": "Authentication required", "code": 401}
            if user.role not in allowed_roles:
                return {
                    "error": f"Permission denied. Your role '{user.role}' cannot access this tool. Required: {list(allowed_roles)}",
                    "code": 403,
                    "user": user.name
                }
            return func(*args, **kwargs)
        return wrapper
    return decorator


def enforce_store_filter(func: Callable):
    """Force store_id parameter for non-admin users.
    
    If the user is a manager/staff, their store_id is injected automatically,
    overriding any store_id they might pass.
    
    Usage:
        @mcp.tool()
        @track_tool
        @enforce_store_filter
        def get_revenue(date_from: str, date_to: str, store_id: str | None = None) -> dict: ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if user and user.role != 'admin' and user.store_id is not None:
            # Force store_id filter for non-admin
            kwargs['store_id'] = str(user.store_id)
        return func(*args, **kwargs)
    return wrapper


def enforce_staff_filter(func: Callable):
    """For staff role: force staff_name filter to their own name only.
    
    Usage:
        @mcp.tool()
        @track_tool
        @enforce_staff_filter
        def get_staff_revenue(date_from, date_to, staff_name=None) -> dict: ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if user and user.role == 'staff':
            kwargs['staff_name'] = user.name
        return func(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# SQL: Create api_keys table
# ---------------------------------------------------------------------------

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    api_key VARCHAR(64) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'manager', 'staff', 'bod')),
    store_id INTEGER,
    staff_id INTEGER,
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_api_keys_key ON api_keys(api_key);
"""

# Deliberately empty. Production users and API keys are provisioned on the
# customer host and must never be committed as source-controlled seed data.
SEED_TEST_KEYS_SQL = ""
