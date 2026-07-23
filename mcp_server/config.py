"""MCP Server configuration."""
import os

# Dashboard PostgreSQL (local on server)
DASHBOARD_PG_DSN = os.environ.get("DASHBOARD_PG_DSN", "")

# POS PostgreSQL (production - internal network via VPN)
POS_PG_DSN = os.environ.get("POS_PG_DSN", "")

# WMS PostgreSQL (read-only; direct warehouse queries)
WMS_PG_DSN = os.environ.get("WMS_PG_DSN", "")
WMS_QUERY_TIMEOUT_MS = int(os.environ.get("WMS_QUERY_TIMEOUT_MS", "15000"))

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
