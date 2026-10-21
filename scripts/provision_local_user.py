"""Provision a local SQLite-backed MCP user without logging credentials.

This script is intended to run only on the customer host. Supply the password
through MCP_PROVISION_PASSWORD or let the terminal prompt for it.
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv


def _load_runtime_env() -> None:
    """Use the same env file convention as the Windows MCP service."""
    env_path = Path(os.environ.get("MCP_ENV_FILE", PROJECT_ROOT / ".env"))
    if env_path.exists():
        load_dotenv(env_path, override=False, encoding="utf-8-sig")


_load_runtime_env()

from mcp_server.auth import clear_key_cache
from mcp_server.config import MCP_AUTH_BACKEND
from mcp_server.local_auth import LocalAuthStore, VALID_ROLES


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--role", required=True, choices=sorted(VALID_ROLES))
    parser.add_argument("--name", required=True)
    parser.add_argument("--staff-id", help="POS employee UUID.")
    parser.add_argument("--store-id", help="POS store UUID.")
    parser.add_argument("--can-view-cost", action="store_true")
    parser.add_argument("--include-hmk", action="store_true")
    parser.add_argument("--warehouse-id", action="append", default=[], help="Permitted warehouse UUID. Repeat for each warehouse.")
    parser.add_argument(
        "--sale-zone-id",
        action="append",
        default=[],
        help="POS SaleZone UUID. Repeat for each permitted ASM zone.",
    )
    args = parser.parse_args()

    if MCP_AUTH_BACKEND != "sqlite":
        raise SystemExit(
            "MCP_AUTH_BACKEND is not sqlite. This script would create a user "
            "that the running service cannot authenticate; provision the "
            "configured dashboard_pg identity store instead."
        )

    password = os.environ.pop("MCP_PROVISION_PASSWORD", "") or getpass.getpass(
        "Password (stored only as a salted hash): "
    )
    if not password:
        raise SystemExit("Password is required")

    LocalAuthStore(args.database).create_or_replace_user(
        username=args.username,
        password=password,
        role=args.role,
        name=args.name,
        staff_id=args.staff_id,
        store_id=args.store_id,
        sale_zone_ids=args.sale_zone_id,
        can_view_cost=args.can_view_cost,
        include_hmk=args.include_hmk,
        warehouse_ids=args.warehouse_id,
    )
    clear_key_cache()
    print({"provisioned": True, "username": args.username, "role": args.role})


if __name__ == "__main__":
    main()
