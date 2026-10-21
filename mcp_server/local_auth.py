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
import re
import secrets
import sqlite3
import time
from pathlib import Path

VALID_ROLES = frozenset({"admin", "manager", "staff", "bod", "asm", "accountant", "warehouse", "sales_manager", "shipper"})

_USERS_ROLE_CHECK = "'admin', 'manager', 'staff', 'bod', 'asm', 'accountant', 'warehouse', 'sales_manager', 'shipper'"


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
                    role TEXT NOT NULL CHECK (role IN ('admin', 'manager', 'staff', 'bod', 'asm', 'accountant', 'warehouse', 'sales_manager', 'shipper')),
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
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS user_sale_zones (
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    sale_zone_id TEXT NOT NULL,
                    PRIMARY KEY (user_id, sale_zone_id)
                );
                CREATE INDEX IF NOT EXISTS idx_user_sale_zones_user
                    ON user_sale_zones(user_id);
                CREATE TABLE IF NOT EXISTS user_policies (
                    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    can_view_cost INTEGER NOT NULL DEFAULT 0 CHECK (can_view_cost IN (0, 1)),
                    include_hmk INTEGER NOT NULL DEFAULT 0 CHECK (include_hmk IN (0, 1))
                );
                CREATE TABLE IF NOT EXISTS user_warehouses (
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    warehouse_id TEXT NOT NULL,
                    PRIMARY KEY (user_id, warehouse_id)
                );
                """
            )

            columns = {row[1] for row in conn.execute("PRAGMA table_info(user_policies)")}
            if "all_sites" not in columns:
                conn.execute("ALTER TABLE user_policies ADD COLUMN all_sites INTEGER NOT NULL DEFAULT 0 CHECK (all_sites IN (0, 1))")

    @staticmethod
    def _migrate_users_role_constraint(conn: sqlite3.Connection) -> None:
        """Expand the role CHECK without changing user identities or child rows.

        SQLite cannot alter a CHECK constraint in place. The migration copies
        every existing user unchanged, including API keys and IDs referenced by
        OAuth authorization codes, then swaps in the updated table.
        """
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'users'"
        ).fetchone()
        table_sql = row["sql"] if row else ""
        role_check = re.search(
            r"\bCHECK\s*\(\s*[\"`\[]?role[\"`\]]?\s+IN\s*\(([^)]*)\)\s*\)",
            table_sql, re.IGNORECASE,
        )
        if role_check is None:
            raise RuntimeError("users table has no recognizable role CHECK constraint")
        existing_roles = set(re.findall(r"['\"]([^'\"]+)['\"]", role_check.group(1)))
        if VALID_ROLES <= existing_roles:
            return

        replacement_sql = (
            table_sql[:role_check.start()] + f"CHECK (role IN ({_USERS_ROLE_CHECK}))"
            + table_sql[role_check.end():]
        )
        replacement_sql = re.sub(
            r'^(CREATE\s+TABLE\s+)(?:IF\s+NOT\s+EXISTS\s+)?(?:"users"|`users`|\[users\]|users)',
            r'\1users_role_migration', replacement_sql, count=1, flags=re.IGNORECASE,
        )
        columns = [item["name"] for item in conn.execute("PRAGMA table_info(users)")]
        column_sql = ", ".join('"' + column.replace('"', '""') + '"' for column in columns)
        dependent_sql = [item[0] for item in conn.execute(
            "SELECT sql FROM sqlite_master WHERE tbl_name = 'users' "
            "AND type IN ('index', 'trigger') AND sql IS NOT NULL"
        )]

        conn.commit()
        conn.execute("PRAGMA foreign_keys = OFF")
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(replacement_sql)
            conn.execute(f"INSERT INTO users_role_migration ({column_sql}) SELECT {column_sql} FROM users")
            conn.execute("DROP TABLE users")
            conn.execute("ALTER TABLE users_role_migration RENAME TO users")
            for sql in dependent_sql:
                conn.execute(sql)
            if conn.execute("PRAGMA foreign_key_check").fetchone():
                raise sqlite3.IntegrityError("foreign key violation during users migration")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
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
        store_id: str | int | None = None,
        staff_id: str | int | None = None,
        sale_zone_ids: tuple[str, ...] | list[str] = (),
        can_view_cost: bool = False,
        include_hmk: bool = False,
        warehouse_ids: tuple[str, ...] | list[str] = (),
    ) -> None:
        if not username or not password:
            raise ValueError("username and password are required")
        if role not in VALID_ROLES:
            raise ValueError("invalid role")
        if role in {"sales_manager", "shipper"} and (staff_id is None or not str(staff_id).strip()):
            raise ValueError(f"{role} users require staff_id")
        sale_zone_ids = tuple(dict.fromkeys(
            str(zone_id).strip() for zone_id in sale_zone_ids if str(zone_id).strip()
        ))
        if role == "asm" and not sale_zone_ids:
            raise ValueError("asm users require at least one sale_zone_id")
        warehouse_ids = tuple(dict.fromkeys(
            str(warehouse_id).strip() for warehouse_id in warehouse_ids
            if str(warehouse_id).strip()
        ))
        if role == "warehouse" and not warehouse_ids:
            raise ValueError("warehouse users require at least one warehouse_id")
        if role == "accountant" and (store_id is None or not str(store_id).strip()):
            raise ValueError("accountant users require store_id")
        self.ensure_schema()
        salt = os.urandom(16)
        password_hash = self._hash_password(password, salt)
        api_key = f"rk_{secrets.token_urlsafe(32)}"
        with self._connect() as conn:
            # Reprovisioning credentials invalidates outstanding OAuth codes.
            conn.execute(
                "DELETE FROM auth_codes WHERE user_id IN (SELECT id FROM users WHERE username = ?)",
                (username,),
            )
            conn.execute(
                """
                INSERT INTO users (
                    username, password_salt, password_hash, api_key, role,
                    store_id, staff_id, name, is_active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(username) DO UPDATE SET
                    password_salt = excluded.password_salt,
                    password_hash = excluded.password_hash,
                    role = excluded.role,
                    store_id = excluded.store_id,
                    staff_id = excluded.staff_id,
                    name = excluded.name,
                    is_active = 1
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
            user_id = conn.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()["id"]
            conn.execute(
                "INSERT INTO user_policies (user_id, can_view_cost, include_hmk) VALUES (?, ?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET can_view_cost = excluded.can_view_cost, "
                "include_hmk = excluded.include_hmk",
                (user_id, int(bool(can_view_cost)), int(bool(include_hmk))),
            )
            conn.execute("DELETE FROM user_warehouses WHERE user_id = ?", (user_id,))
            conn.executemany(
                "INSERT INTO user_warehouses (user_id, warehouse_id) VALUES (?, ?)",
                [(user_id, warehouse_id) for warehouse_id in warehouse_ids],
            )
            conn.execute("DELETE FROM user_sale_zones WHERE user_id = ?", (user_id,))
            if sale_zone_ids:
                conn.executemany(
                    "INSERT INTO user_sale_zones (user_id, sale_zone_id) VALUES (?, ?)",
                    [(user_id, zone_id) for zone_id in sale_zone_ids],
                )

    def update_user_policy(
        self, username: str, role: str | None = None,
        include_hmk: bool | None = None, can_view_cost: bool | None = None,
        staff_id: str | int | None = None,
        warehouse_ids: tuple[str, ...] | list[str] | None = None,
        all_sites: bool | None = None,
    ) -> None:
        """Apply policy without resetting credentials or unspecified scope."""
        if role is not None and role not in VALID_ROLES:
            raise ValueError("invalid role")
        if warehouse_ids is not None:
            warehouse_ids = tuple(dict.fromkeys(
                str(value).strip() for value in warehouse_ids if str(value).strip()
            ))
        self.ensure_schema()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            if user is None:
                raise ValueError("user not found")
            user_id = user["id"]
            effective_role = user["role"] if role is None else role
            policy = conn.execute("SELECT all_sites FROM user_policies WHERE user_id = ?", (user_id,)).fetchone()
            effective_all_sites = bool(policy[0]) if policy else False
            if all_sites is not None:
                effective_all_sites = bool(all_sites)
            if effective_all_sites and effective_role != "accountant":
                raise ValueError("all_sites is reserved for explicitly approved accountants")
            effective_staff = user["staff_id"] if staff_id is None else staff_id
            effective_warehouses = warehouse_ids if warehouse_ids is not None else tuple(
                row[0] for row in conn.execute(
                    "SELECT warehouse_id FROM user_warehouses WHERE user_id = ?", (user_id,)
                )
            )
            if effective_role in {"sales_manager", "shipper"} and (
                effective_staff is None or not str(effective_staff).strip()
            ):
                raise ValueError(f"{effective_role} users require staff_id")
            if effective_role == "warehouse" and not effective_warehouses:
                raise ValueError("warehouse users require at least one warehouse_id")
            if effective_role == "accountant" and not effective_all_sites and (
                user["store_id"] is None or not str(user["store_id"]).strip()
            ):
                raise ValueError("accountant users require store_id")
            if effective_role == "asm" and not conn.execute(
                "SELECT 1 FROM user_sale_zones WHERE user_id = ?", (user_id,)
            ).fetchone():
                raise ValueError("asm users require at least one sale_zone_id")
            conn.execute(
                "UPDATE users SET role = ?, staff_id = ? WHERE id = ?",
                (effective_role, effective_staff, user_id),
            )
            conn.execute("INSERT OR IGNORE INTO user_policies (user_id) VALUES (?)", (user_id,))
            conn.execute("UPDATE user_policies SET all_sites = ? WHERE user_id = ?", (int(effective_all_sites), user_id))
            conn.execute(
                "UPDATE user_policies SET include_hmk = COALESCE(?, include_hmk), "
                "can_view_cost = COALESCE(?, can_view_cost) WHERE user_id = ?",
                (None if include_hmk is None else int(bool(include_hmk)),
                 None if can_view_cost is None else int(bool(can_view_cost)), user_id),
            )
            if warehouse_ids is not None:
                conn.execute("DELETE FROM user_warehouses WHERE user_id = ?", (user_id,))
                conn.executemany(
                    "INSERT INTO user_warehouses (user_id, warehouse_id) VALUES (?, ?)",
                    [(user_id, value) for value in warehouse_ids],
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
                     , username
                FROM users WHERE api_key = ? AND is_active = 1
                """,
                (api_key,),
            ).fetchone()
            if not row:
                return None
            result = dict(row)
            policy = conn.execute(
                "SELECT can_view_cost, include_hmk, all_sites FROM user_policies WHERE user_id = ?",
                (row["id"],),
            ).fetchone()
            result["can_view_cost"] = bool(policy["can_view_cost"]) if policy else False
            result["include_hmk"] = bool(policy["include_hmk"]) if policy else False
            result["all_sites"] = bool(policy["all_sites"]) and result["role"] == "accountant" if policy else False
            result["warehouse_ids"] = tuple(item[0] for item in conn.execute(
                "SELECT warehouse_id FROM user_warehouses WHERE user_id = ? ORDER BY warehouse_id",
                (row["id"],),
            ))
            result["sale_zone_ids"] = tuple(
                item[0] for item in conn.execute(
                    "SELECT sale_zone_id FROM user_sale_zones WHERE user_id = ? ORDER BY sale_zone_id",
                    (row["id"],),
                ).fetchall()
            )
        return result

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
