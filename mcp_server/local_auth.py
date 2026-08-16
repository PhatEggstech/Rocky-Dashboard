"""Local SQLite backing store for the MCP OAuth fallback.

The database is intended to live on the customer host with Windows ACLs that
allow only LocalSystem and local administrators. It never logs passwords or
access tokens. Passwords use scrypt with a per-user random salt.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from pathlib import Path

VALID_ROLES = frozenset({"admin", "manager", "staff", "bod"})


class LocalAuthStore:
    def __init__(self, database_path: str):
        self.path = Path(database_path)

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_salt TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    api_key TEXT UNIQUE NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('admin', 'manager', 'staff', 'bod')),
                    store_id INTEGER,
                    staff_id INTEGER,
                    name TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS auth_codes (
                    code TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    api_key TEXT NOT NULL,
                    redirect_uri TEXT NOT NULL,
                    state TEXT NOT NULL,
                    code_challenge TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    used INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key);
                CREATE INDEX IF NOT EXISTS idx_auth_codes_expiry ON auth_codes(created_at);
                """
            )
            self._migrate_users_role_constraint(conn)

    @staticmethod
    def _migrate_users_role_constraint(conn: sqlite3.Connection) -> None:
        """Add the BOD role to databases created by an earlier release.

        SQLite cannot alter a CHECK constraint in place. The migration copies
        every existing user unchanged, including API keys and IDs referenced by
        OAuth authorization codes, then swaps in the updated table.
        """
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'users'"
        ).fetchone()
        table_sql = (row["sql"] if row else "").lower()
        if "'bod'" in table_sql:
            return

        conn.commit()
        conn.execute("PRAGMA foreign_keys = OFF")
        try:
            conn.executescript(
                """
                BEGIN;
                CREATE TABLE users_role_migration (
                    id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_salt TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    api_key TEXT UNIQUE NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('admin', 'manager', 'staff', 'bod')),
                    store_id INTEGER,
                    staff_id INTEGER,
                    name TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at INTEGER NOT NULL
                );
                INSERT INTO users_role_migration (
                    id, username, password_salt, password_hash, api_key, role,
                    store_id, staff_id, name, is_active, created_at
                )
                SELECT id, username, password_salt, password_hash, api_key, role,
                       store_id, staff_id, name, is_active, created_at
                FROM users;
                DROP TABLE users;
                ALTER TABLE users_role_migration RENAME TO users;
                CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key);
                COMMIT;
                """
            )
        finally:
            conn.execute("PRAGMA foreign_keys = ON")

    @staticmethod
    def _hash_password(password: str, salt: bytes) -> str:
        digest = hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32
        )
        return base64.b64encode(digest).decode("ascii")

    def create_or_replace_user(
        self,
        *,
        username: str,
        password: str,
        role: str,
        name: str,
        store_id: int | None = None,
        staff_id: int | None = None,
    ) -> None:
        if not username or not password:
            raise ValueError("username and password are required")
        if role not in VALID_ROLES:
            raise ValueError("invalid role")
        self.ensure_schema()
        salt = os.urandom(16)
        password_hash = self._hash_password(password, salt)
        api_key = f"rk_{secrets.token_urlsafe(32)}"
        with self._connect() as conn:
            conn.execute("DELETE FROM users WHERE username = ?", (username,))
            conn.execute(
                """
                INSERT INTO users (
                    username, password_salt, password_hash, api_key, role,
                    store_id, staff_id, name, is_active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    username,
                    base64.b64encode(salt).decode("ascii"),
                    password_hash,
                    api_key,
                    role,
                    store_id,
                    staff_id,
                    name,
                    int(time.time()),
                ),
            )

    def verify_login(self, username: str, password: str):
        self.ensure_schema()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, api_key, role, name, password_salt, password_hash
                FROM users WHERE username = ? AND is_active = 1
                """,
                (username,),
            ).fetchone()
        if not row:
            return None
        salt = base64.b64decode(row["password_salt"])
        candidate = self._hash_password(password, salt)
        if not hmac.compare_digest(candidate, row["password_hash"]):
            return None
        return row["api_key"], row["id"], row["role"], row["name"]

    def lookup_api_key(self, api_key: str):
        self.ensure_schema()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, role, store_id, staff_id, name
                FROM users WHERE api_key = ? AND is_active = 1
                """,
                (api_key,),
            ).fetchone()
        return row

    def store_auth_code(
        self, code: str, user_id: int, api_key: str, redirect_uri: str,
        state: str, code_challenge: str,
    ) -> None:
        self.ensure_schema()
        with self._connect() as conn:
            conn.execute("DELETE FROM auth_codes WHERE created_at < ?", (int(time.time()) - 600,))
            conn.execute(
                """
                INSERT INTO auth_codes (
                    code, user_id, api_key, redirect_uri, state,
                    code_challenge, created_at, used
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (code, user_id, api_key, redirect_uri, state, code_challenge or "", int(time.time())),
            )

    def exchange_auth_code(self, code: str):
        self.ensure_schema()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT api_key, user_id, code_challenge FROM auth_codes
                WHERE code = ? AND used = 0 AND created_at > ?
                """,
                (code, int(time.time()) - 600),
            ).fetchone()
            if row:
                conn.execute("UPDATE auth_codes SET used = 1 WHERE code = ?", (code,))
        if not row:
            return None
        return row["api_key"], row["user_id"], row["code_challenge"]
