"""Idempotent OAuth schema migration for the MCP authentication database.

Run only on the MCP host with MCP_ENV_FILE set, or pass --env-file explicitly.
The migration never creates or resets users, passwords, or API keys.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=os.environ.get("MCP_ENV_FILE", ""))
    args = parser.parse_args()

    if args.env_file:
        env_file = Path(args.env_file)
        if not env_file.exists():
            raise SystemExit(f"Environment file not found: {env_file}")
        load_dotenv(env_file, override=True)

    dsn = os.environ.get("DASHBOARD_PG_DSN", "")
    if not dsn:
        raise SystemExit("DASHBOARD_PG_DSN is not configured")

    with psycopg.connect(dsn, connect_timeout=8) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "ALTER TABLE auth_codes "
                "ADD COLUMN IF NOT EXISTS code_challenge TEXT NOT NULL DEFAULT ''"
            )
        conn.commit()

    print("OAuth schema migration completed: auth_codes.code_challenge is available.")


if __name__ == "__main__":
    main()
