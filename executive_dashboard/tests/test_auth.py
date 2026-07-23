"""Tests for auth module: JWT creation, verification, RBAC."""

import sqlite3
import pytest

from executive_dashboard.app.auth import (
    UserContext,
    create_access_token,
    init_auth_schema,
    pwd_context,
    require_page,
    seed_admin_user,
    verify_token,
    PAGE_ROLES,
)


@pytest.fixture
def db():
    """In-memory SQLite for tests."""
    conn = sqlite3.connect(":memory:")
    init_auth_schema(conn)
    yield conn
    conn.close()


class TestTokenOps:
    def test_create_and_verify_token(self):
        token, expires = create_access_token("testuser", "ceo")
        assert isinstance(token, str)
        assert expires > 0

        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "testuser"
        assert payload["role"] == "ceo"

    def test_verify_invalid_token_returns_none(self):
        result = verify_token("invalid.token.here")
        assert result is None

    def test_verify_tampered_token_returns_none(self):
        token, _ = create_access_token("user", "ceo")
        # tamper with token
        tampered = token[:-5] + "XXXXX"
        result = verify_token(tampered)
        assert result is None


class TestSchema:
    def test_init_creates_users_table(self, db):
        tables = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()
        assert tables is not None

    def test_seed_admin_creates_user(self, db):
        seed_admin_user(db)
        row = db.execute("SELECT username, role FROM users WHERE username='admin'").fetchone()
        assert row == ("admin", "ceo")

    def test_seed_admin_idempotent(self, db):
        seed_admin_user(db)
        seed_admin_user(db)
        count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        assert count == 1

    def test_password_verification(self, db):
        seed_admin_user(db)
        hashed = db.execute("SELECT hashed_password FROM users WHERE username='admin'").fetchone()[0]
        assert pwd_context.verify("changeme123", hashed)
        assert not pwd_context.verify("wrongpassword", hashed)


class TestRBAC:
    def test_page_roles_all_have_sets(self):
        for page, roles in PAGE_ROLES.items():
            assert isinstance(roles, set)
            assert len(roles) > 0

    def test_ceo_has_access_to_all_pages(self):
        for page, roles in PAGE_ROLES.items():
            assert "ceo" in roles, f"CEO should have access to {page}"

    def test_store_manager_limited_access(self):
        # store_manager should NOT have access to b2b
        assert "store_manager" not in PAGE_ROLES["b2b-analytics"]
        # but should have access to executive summary
        assert "store_manager" in PAGE_ROLES["executive-summary"]
