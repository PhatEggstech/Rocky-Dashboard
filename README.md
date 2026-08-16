# Rocky MCP Server

Sanitized source snapshot of the Rocky Lens MCP release running on the customer host.

## What this repository contains

- Streamable HTTP MCP server at `/mcp` with OAuth 2.1 PKCE login.
- Read-only integrations for Rocky POS, WMS, and Rocky Lens Dashboard API.
- Local SQLite authentication fallback with `admin`, `manager`, `staff`, and restricted `bod` roles.
- Windows service manifests and release/staging deployment scripts.
- Smoke tests for role boundaries, payment document type logic, Dashboard API mapping, product rankings, and schema retrieval.

No production credential, DSN, OAuth database, tunnel token, or log has been included.

## Main modules

| Module | Responsibility |
| --- | --- |
| `mcp_server/server.py` | FastMCP tool registry, reporting-range resolution, tool tracking, and BOD allow-list. |
| `mcp_server/auth.py` | Bearer authentication middleware and role decorators. |
| `mcp_server/local_auth.py` | Local SQLite user store, scrypt passwords, OAuth codes, and BOD-role migration. |
| `mcp_server/tools.py` | Read-only POS queries and business reporting calculations. |
| `mcp_server/dashboard_api.py` | Rocky Lens dashboard API adapter used to mirror dashboard numbers. |
| `mcp_server/wms_tools.py` | Read-only WMS inventory, movement, warehouse, and health queries. |
| `scripts/start_mcp_production_oauth.py` | Production ASGI app, OAuth/PKCE endpoints, and `/health`. |
| `deploy/rocky_mcp_windows/` | Windows service and staging/release automation. |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the deployed flow and role policy.

## Local setup

```powershell
Copy-Item .env.example .env
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\start_mcp_production_oauth.py
```

The local service listens on `http://127.0.0.1:8085/mcp` by default. Populate `.env` only on the target machine.

## Verification

```powershell
python -m pytest tests -q
```

To provision a local user without writing the password into a command history:

```powershell
python scripts\provision_local_user.py `
  --database C:\ProgramData\RockyMCP\auth\oauth.sqlite3 `
  --username bod_assistant --role bod --name "BOD Assistant"
```

## Deployment model

1. Build a new release directory.
2. Switch `staging` junction and run smoke tests.
3. Switch `current` junction only after staging passes.
4. Restart `RockyMCP`, health-check `127.0.0.1:8085/health`, keep ingress/tunnel process unchanged.
5. Roll back the `current` junction if the health gate fails.

