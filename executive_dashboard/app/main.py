"""FastAPI application for Rocky Lens Executive Dashboard."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load env from .env.pg in executive_dashboard root
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env.pg"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)

from .db import get_conn, put_conn, init_schema, close_pool
from .middleware import setup_middleware
from .pos_sync import get_sync_status, resolve_pos_dsn, sync_from_postgres
from .routers.react_dashboard import router as react_router
from .routers.auth import router as auth_router
from .auth import seed_admin_user
from .wms_sync import sync_inventory as wms_sync_inventory

# Logging
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=log_level,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

_sync_running = False
_last_sync_result: dict | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init schema, optionally trigger POS sync."""
    global _last_sync_result

    conn = get_conn()
    try:
        init_schema(conn)
        seed_admin_user(conn)
        logger.info("PostgreSQL schema ready.")
    finally:
        put_conn(conn)

    # Sync on startup if configured
    if os.environ.get("POS_SYNC_ON_STARTUP", "0") == "1" and resolve_pos_dsn():
        logger.info("Running POS sync on startup...")
        conn = get_conn()
        try:
            _last_sync_result = sync_from_postgres(conn)
            logger.info("Startup sync complete: %s", _last_sync_result)
        finally:
            put_conn(conn)

    # WMS sync on startup if configured
    if os.environ.get("WMS_SYNC_ON_STARTUP", "0") == "1":
        logger.info("Running WMS inventory sync on startup...")
        conn = get_conn()
        try:
            wms_result = wms_sync_inventory(conn)
            logger.info("WMS sync complete: %s", wms_result)
        finally:
            put_conn(conn)

    yield  # app runs

    # Shutdown
    close_pool()
    logger.info("Shutting down.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Rocky Lens Dashboard API",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS
origins = os.environ.get("EDP_CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting & access logging
setup_middleware(app)

# Include routers
app.include_router(auth_router)
app.include_router(react_router)


# ---------------------------------------------------------------------------
# Health & Ready
# ---------------------------------------------------------------------------


@app.get("/health")
def health():
    """Health check."""
    return {
        "status": "ok",
        "pos_dsn_configured": resolve_pos_dsn() is not None,
        "database": "postgresql",
        "capabilities": ["executive-summary", "sales-marketing", "quality-clv", "b2b-analytics"],
    }


@app.get("/ready")
def ready():
    """Readiness probe: schema is initialised."""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM pg_catalog.pg_tables WHERE schemaname = 'public'"
        ).fetchone()
        tables = row[0] if row else 0
        return {"ready": tables >= 5, "tables": tables}
    except Exception as e:
        return {"ready": False, "error": str(e)}
    finally:
        put_conn(conn)


# ---------------------------------------------------------------------------
# Sync endpoints
# ---------------------------------------------------------------------------


def _do_sync(sections: list[str] | None = None):
    """Background sync task."""
    global _sync_running, _last_sync_result
    _sync_running = True
    try:
        conn = get_conn()
        try:
            _last_sync_result = sync_from_postgres(conn, sections=sections)
        finally:
            put_conn(conn)
    finally:
        _sync_running = False


@app.post("/api/pos/sync")
def trigger_sync(
    background_tasks: BackgroundTasks,
    wait: bool = False,
):
    """Trigger a full POS sync."""
    if _sync_running:
        return {"status": "already_running"}

    if wait:
        _do_sync()
        return {"status": "completed", "result": _last_sync_result}

    background_tasks.add_task(_do_sync)
    return {"status": "started"}


@app.get("/api/pos/sync/status")
def sync_status():
    """Return current sync state."""
    conn = get_conn()
    try:
        return {
            "running": _sync_running,
            "last_result": _last_sync_result,
            "sections": get_sync_status(conn),
        }
    finally:
        put_conn(conn)


# ---------------------------------------------------------------------------
# WMS sync endpoints
# ---------------------------------------------------------------------------

_wms_sync_running = False
_last_wms_result: dict | None = None


def _do_wms_sync():
    """Background WMS sync task."""
    global _wms_sync_running, _last_wms_result
    _wms_sync_running = True
    try:
        conn = get_conn()
        try:
            _last_wms_result = wms_sync_inventory(conn)
        finally:
            put_conn(conn)
    finally:
        _wms_sync_running = False


@app.post("/api/wms/sync")
def trigger_wms_sync(
    background_tasks: BackgroundTasks,
    wait: bool = False,
):
    """Trigger a WMS inventory sync."""
    if _wms_sync_running:
        return {"status": "already_running"}

    if wait:
        _do_wms_sync()
        return {"status": "completed", "result": _last_wms_result}

    background_tasks.add_task(_do_wms_sync)
    return {"status": "started"}


@app.get("/api/wms/sync/status")
def wms_sync_status():
    """Return WMS sync state."""
    return {
        "running": _wms_sync_running,
        "last_result": _last_wms_result,
    }
