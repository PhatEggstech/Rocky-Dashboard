# Rocky Dashboard

Rocky Dashboard combines an executive analytics API, a React frontend, and a
read-only MCP server for dashboard, POS, and WMS reporting.

## Components

- `executive_dashboard`: FastAPI analytics backend and synchronization jobs.
- `executive_dashboard_frontend`: React dashboard.
- `mcp_server`: MCP tools with API-key/OAuth authentication and role checks.
- `scripts`: read-only MCP/WMS smoke, resilience, and load tests.

## Local setup

1. Copy `.env.example` to `.env` and replace every placeholder.
2. Keep database accounts read-only wherever possible.
3. Start the Docker stack:

```powershell
docker compose up --build
```

The frontend is exposed on `http://localhost:3000` and the API on
`http://localhost:8000`.

## Security

Secrets, customer handoff files, generated reports, database exports, private
keys, and machine-specific deployment scripts are intentionally excluded from
this public repository.
