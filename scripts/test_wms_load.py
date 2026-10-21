# -*- coding: utf-8 -*-
"""Concurrent MCP health-call load test for the WMS staging service."""
from __future__ import annotations

import json
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx
import psycopg
from dotenv import load_dotenv

ROOT = Path(os.environ.get("MCP_ROOT", Path(__file__).resolve().parent.parent))
ENV_FILE = Path(os.environ.get("MCP_ENV_FILE", ROOT / ".env"))
BASE_URL = os.environ.get("MCP_TEST_URL", "http://127.0.0.1:8086/mcp")
REQUESTS = max(1, min(int(os.environ.get("MCP_LOAD_REQUESTS", "20")), 100))
WORKERS = max(1, min(int(os.environ.get("MCP_LOAD_WORKERS", "5")), 20))

load_dotenv(ENV_FILE)
sys.path.insert(0, str(ROOT))
from mcp_server.config import DASHBOARD_PG_DSN  # noqa: E402


def _decode(response: httpx.Response) -> dict:
    lines = [line[5:].strip() for line in response.text.splitlines() if line.startswith("data:")]
    return json.loads(lines[-1] if lines else response.text)


def _admin_token() -> str:
    with psycopg.connect(DASHBOARD_PG_DSN, connect_timeout=8) as conn:
        row = conn.execute(
            "SELECT api_key FROM api_keys WHERE is_active=TRUE AND role='admin' ORDER BY user_id LIMIT 1"
        ).fetchone()
    if not row:
        raise RuntimeError("No active admin API key")
    return row[0]


def _one(token: str, index: int) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    started = time.perf_counter()
    try:
        with httpx.Client(timeout=30) as client:
            init = client.post(BASE_URL, headers=headers, json={
                "jsonrpc": "2.0", "id": index * 10 + 1, "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                           "clientInfo": {"name": "wms-load", "version": "1.0"}},
            })
            session = init.headers.get("mcp-session-id")
            if init.status_code != 200 or not session:
                raise RuntimeError(f"initialize={init.status_code}")
            session_headers = {**headers, "Mcp-Session-Id": session}
            client.post(BASE_URL, headers=session_headers, json={
                "jsonrpc": "2.0", "method": "notifications/initialized", "params": {},
            })
            response = client.post(BASE_URL, headers=session_headers, json={
                "jsonrpc": "2.0", "id": index * 10 + 2, "method": "tools/call",
                "params": {"name": "check_wms_health", "arguments": {}},
            })
            body = _decode(response).get("result", {})
            content = body.get("content", [])
            data = json.loads(content[0]["text"]) if content else {}
            if response.status_code != 200 or body.get("isError") or data.get("status") != "ok":
                raise RuntimeError(f"health={response.status_code}:{data.get('status')}")
        return {"ok": True, "seconds": time.perf_counter() - started}
    except Exception as exc:
        return {"ok": False, "seconds": time.perf_counter() - started, "error": type(exc).__name__}


def main() -> int:
    token = _admin_token()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(as_completed(pool.submit(_one, token, i) for i in range(REQUESTS)))
        rows = [future.result() for future in results]
    durations = [row["seconds"] for row in rows]
    failures = [row for row in rows if not row["ok"]]
    output = {
        "requests": REQUESTS,
        "workers": WORKERS,
        "passed": REQUESTS - len(failures),
        "failed": len(failures),
        "latency_seconds": {
            "min": round(min(durations), 3),
            "median": round(statistics.median(durations), 3),
            "max": round(max(durations), 3),
        },
        "error_types": sorted({row["error"] for row in failures}),
    }
    print(json.dumps(output, separators=(",", ":")))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
