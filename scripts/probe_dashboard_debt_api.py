"""Read-only probe for the official Rocky Dashboard debt endpoints.

Run on the customer machine with MCP_ENV_FILE set to the staging environment.
It prints endpoint status and response bodies, never credentials or tokens.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

env_file = os.getenv("MCP_ENV_FILE", "")
if env_file:
    load_dotenv(env_file, override=True)

from mcp_server.dashboard_api import _epoch_millis, _post


def main() -> None:
    report_date = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    start_at = _epoch_millis(report_date)
    end_at = _epoch_millis(report_date, end_of_day=True)
    requests = {
        "debt_revenue_statistic": (
            "/Admin/DebtDashboard/Revenue/Statistic",
            {"issueAt": {"from": start_at, "to": end_at}, "paymentMethodIds": None, "customerIds": None},
        ),
        "debt_recovery_rate": (
            "/Admin/DebtDashboard/RecoveryRate/Statistic",
            {"startAt": start_at, "endAt": end_at, "customerIds": None},
        ),
        "debt_customer_page": (
            "/Admin/DebtDashboard/CustomerDebt/GetPage",
            {"startAt": start_at, "endAt": end_at, "customerIds": None, "page": 1, "size": 10},
        ),
    }
    output = {"date": report_date.isoformat(), "results": {}}
    for name, (path, payload) in requests.items():
        status, body = _post(path, payload)
        output["results"][name] = {"http_status": status, "ok": 200 <= status < 300, "data": body}
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
