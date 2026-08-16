"""MCP Server configuration."""
import os

from .payment_types import (
    resolve_collection_document_type,
    resolve_receive_document_type,
)

# Dashboard PostgreSQL (local on server)
DASHBOARD_PG_DSN = os.environ.get("DASHBOARD_PG_DSN", "")

# Authentication storage. The default keeps compatibility with the original
# Dashboard PostgreSQL-backed OAuth flow; "sqlite" is a self-contained
# customer-host fallback when that database is unavailable.
MCP_AUTH_BACKEND = os.environ.get("MCP_AUTH_BACKEND", "dashboard_pg").strip().lower()
MCP_LOCAL_AUTH_DB_PATH = os.environ.get(
    "MCP_LOCAL_AUTH_DB_PATH",
    r"C:\ProgramData\RockyMCP\auth\oauth.sqlite3",
)

# POS PostgreSQL (production - internal network via VPN)
POS_PG_DSN = os.environ.get("POS_PG_DSN", "")

# Legacy POS collection prefers the configured Allocate enum, and uses Receive
# only for orders that have no valid Allocate record.
PAYMENT_COLLECTION_DOCUMENT_TYPE = resolve_collection_document_type()
PAYMENT_RECEIVE_DOCUMENT_TYPE = resolve_receive_document_type()

# WMS PostgreSQL (read-only; direct warehouse queries)
WMS_PG_DSN = os.environ.get("WMS_PG_DSN", "")
WMS_QUERY_TIMEOUT_MS = int(os.environ.get("WMS_QUERY_TIMEOUT_MS", "15000"))

# Rocky Lens Admin dashboard API (read-only; used to mirror dashboard widgets)
ROCKY_DASHBOARD_API_BASE_URL = os.environ.get(
    "ROCKY_DASHBOARD_API_BASE_URL",
    "https://api.rocky.endpoint.eggstech.io",
).rstrip("/")
ROCKY_DASHBOARD_IDENTITY_BASE_URL = os.environ.get(
    "ROCKY_DASHBOARD_IDENTITY_BASE_URL",
    "https://identity.rocky.endpoint.eggstech.io",
).rstrip("/")
ROCKY_DASHBOARD_API_TOKEN = os.environ.get("ROCKY_DASHBOARD_API_TOKEN", "")
# Optional fallback when the dashboard owner cannot issue a service token.
# Set these only on the customer machine; never commit them or send them in chat.
ROCKY_DASHBOARD_USERNAME = os.environ.get("ROCKY_DASHBOARD_USERNAME", "")
ROCKY_DASHBOARD_PASSWORD = os.environ.get("ROCKY_DASHBOARD_PASSWORD", "")

# AI Provider: "ollama" (local/tailscale) or "openrouter" (cloud)
AI_PROVIDER = os.environ.get("AI_PROVIDER", "ollama")

# Ollama (AI server via Tailscale)
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "deepseek-r1:8b")

# OpenRouter AI (cloud fallback)
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")

# Active AI config (resolved)
if AI_PROVIDER == "ollama":
    AI_BASE_URL = OLLAMA_BASE_URL
    AI_API_KEY = "ollama"  # Ollama doesn't need real key but openai SDK requires one
    AI_MODEL = OLLAMA_MODEL
else:
    AI_BASE_URL = OPENROUTER_BASE_URL
    AI_API_KEY = OPENROUTER_API_KEY
    AI_MODEL = OPENROUTER_MODEL

# App
APP_NAME = "Rocky Dashboard MCP Server"
