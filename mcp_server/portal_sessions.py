"""Server-side encrypted portal credentials, independent of local admin auth.

Callers must verify the RK identity before creating a session. Keep the explicit
Fernet key outside the database and restrict filesystem access to both. This
module never generates a key, logs credentials, or falls back to other auth.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path
import secrets
import sqlite3
import time

from cryptography.fernet import Fernet, InvalidToken


class PortalSessionError(RuntimeError):
    """The vault key or encrypted session data could not be authenticated."""


class PortalSessionStore:
    def __init__(self, path: str | Path, key: str | bytes):
        if not isinstance(key, (str, bytes)) or not key:
            raise ValueError("An explicit Fernet key is required")
        try:
            self._cipher = Fernet(key)
        except (ValueError, TypeError):
            raise ValueError("Invalid Fernet key") from None
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS portal_vault_meta (
                    id INTEGER PRIMARY KEY CHECK (id = 1), marker BLOB NOT NULL
                );
                CREATE TABLE IF NOT EXISTS portal_identity_bindings (
                    user_id TEXT PRIMARY KEY, rk_user_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS portal_sessions (
                    session_hash TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    rk_user_id TEXT NOT NULL,
                    session_expires_at REAL NOT NULL,
                    revoked INTEGER NOT NULL DEFAULT 0,
                    payload BLOB NOT NULL
                );
                CREATE INDEX IF NOT EXISTS portal_sessions_expiry
                    ON portal_sessions(session_expires_at);
            """)
            conn.execute("INSERT OR IGNORE INTO portal_vault_meta VALUES (1, ?)",
                         (self._cipher.encrypt(b"portal-session-vault-v1"),))
            self._check_key(conn)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _check_key(self, conn):
        row = conn.execute("SELECT marker FROM portal_vault_meta WHERE id = 1").fetchone()
        try:
            if row is None or self._cipher.decrypt(row[0]) != b"portal-session-vault-v1":
                raise PortalSessionError("Vault authentication failed")
        except (InvalidToken, TypeError):
            raise PortalSessionError("Vault authentication failed") from None

    @staticmethod
    def _identity(value):
        if isinstance(value, bool) or not isinstance(value, (str, int)) or not str(value).strip():
            raise ValueError("A nonempty identity ID is required")
        return str(value)

    @staticmethod
    def _expiry(value):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("Expiry must be a finite Unix timestamp")
        return float(value)

    @staticmethod
    def _tokens(access_token, refresh_token):
        if not isinstance(access_token, str) or not access_token:
            raise ValueError("An access token is required")
        if not isinstance(refresh_token, str):
            raise ValueError("Refresh token must be a string")

    @staticmethod
    def _hash(rawtoken):
        if not isinstance(rawtoken, str) or not rawtoken.startswith("rkps_"):
            return None
        return hashlib.sha256(rawtoken.encode("utf-8")).hexdigest()

    def create_session(self, user_id, rk_user_id, access_token, refresh_token="",
                       *, token_expires_at, session_expires_at) -> str:
        user_id, rk_user_id = self._identity(user_id), self._identity(rk_user_id)
        self._tokens(access_token, refresh_token)
        token_expires_at = self._expiry(token_expires_at)
        session_expires_at = self._expiry(session_expires_at)
        if session_expires_at <= time.time():
            raise ValueError("Session expiry must be in the future")
        rawtoken = "rkps_" + secrets.token_urlsafe(32)
        session_hash = self._hash(rawtoken)
        data = dict(user_id=user_id, rk_user_id=rk_user_id,
                    access_token=access_token, refresh_token=refresh_token,
                    token_expires_at=token_expires_at,
                    session_expires_at=session_expires_at, session_hash=session_hash)
        payload = self._cipher.encrypt(json.dumps(data).encode("utf-8"))
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._check_key(conn)
            conn.execute("INSERT OR IGNORE INTO portal_identity_bindings VALUES (?, ?)",
                         (user_id, rk_user_id))
            bound = conn.execute("SELECT rk_user_id FROM portal_identity_bindings WHERE user_id = ?",
                                 (user_id,)).fetchone()
            if bound[0] != rk_user_id:
                raise ValueError("Local user is bound to a different RK identity")
            conn.execute("INSERT INTO portal_sessions VALUES (?, ?, ?, ?, 0, ?)",
                         (session_hash, user_id, rk_user_id, session_expires_at, payload))
        return rawtoken

    def _read(self, conn, rawtoken):
        self._check_key(conn)
        row = conn.execute("SELECT * FROM portal_sessions WHERE session_hash = ? AND revoked = 0 "
                           "AND session_expires_at > ?", (self._hash(rawtoken), time.time())).fetchone()
        if row is None:
            return None
        try:
            data = json.loads(self._cipher.decrypt(row["payload"]))
            expected = ("session_hash", "user_id", "rk_user_id", "session_expires_at")
            if any(data[name] != row[name] for name in expected):
                raise ValueError()
            binding = conn.execute("SELECT rk_user_id FROM portal_identity_bindings WHERE user_id = ?",
                                   (row["user_id"],)).fetchone()
            if binding is None or binding[0] != data["rk_user_id"]:
                raise ValueError()
            self._tokens(data["access_token"], data["refresh_token"])
            self._expiry(data["token_expires_at"])
        except (InvalidToken, ValueError, TypeError, KeyError):
            raise PortalSessionError("Session authentication failed") from None
        return data

    def get_session(self, rawtoken) -> dict | None:
        """Reusable session; token expiry is returned so the caller can refresh it."""
        with self._connect() as conn:
            data = self._read(conn, rawtoken)
        if data is not None:
            data.pop("session_hash")
        return data

    def update_tokens(self, rawtoken, access_token, refresh_token="", *, token_expires_at) -> bool:
        """Replace both tokens atomically; pass the old refresh token to retain it."""
        self._tokens(access_token, refresh_token)
        token_expires_at = self._expiry(token_expires_at)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            data = self._read(conn, rawtoken)
            if data is None:
                return False
            data.update(access_token=access_token, refresh_token=refresh_token,
                        token_expires_at=token_expires_at)
            conn.execute("UPDATE portal_sessions SET payload = ? WHERE session_hash = ?",
                         (self._cipher.encrypt(json.dumps(data).encode("utf-8")), data["session_hash"]))
        return True

    def revoke_session(self, rawtoken) -> bool:
        with self._connect() as conn:
            self._check_key(conn)
            return conn.execute("UPDATE portal_sessions SET revoked = 1 WHERE session_hash = ? "
                                "AND revoked = 0", (self._hash(rawtoken),)).rowcount == 1

    def delete_expired(self) -> int:
        """Delete expired or revoked credentials, retaining identity bindings."""
        with self._connect() as conn:
            self._check_key(conn)
            return conn.execute("DELETE FROM portal_sessions WHERE session_expires_at <= ? "
                                "OR revoked = 1", (time.time(),)).rowcount
