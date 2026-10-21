"""Read-only verification of the MCP OAuth authentication database."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--username", default="admin")
    args = parser.parse_args()

    env_file = Path(args.env_file)
    if not env_file.exists():
        raise SystemExit(f"Environment file not found: {env_file}")
    load_dotenv(env_file, override=True)
    dsn = os.environ.get("DASHBOARD_PG_DSN", "")
    if not dsn:
        raise SystemExit("DASHBOARD_PG_DSN is not configured")

    with psycopg.connect(dsn, connect_timeout=8) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user, inet_server_addr()")
            database_name, database_user, server_ip = cur.fetchone()
            cur.execute(
                "SELECT is_active, password_hash IS NOT NULL "
                "FROM api_keys WHERE username = %s",
                (args.username,),
            )
            user_row = cur.fetchone()
            cur.execute(
                "SELECT EXISTS ("
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'auth_codes' "
                "AND column_name = 'code_challenge'"
                ")"
            )
            has_code_challenge = cur.fetchone()[0]

    print(
        {
            "database_name": database_name,
            "database_user": database_user,
            "server_ip": str(server_ip) if server_ip else None,
            "user_exists": user_row is not None,
            "user_active": bool(user_row[0]) if user_row else None,
            "user_has_password_hash": bool(user_row[1]) if user_row else None,
            "auth_codes_has_code_challenge": has_code_challenge,
        }
    )


if __name__ == "__main__":
    main()
