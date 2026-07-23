"""Tests for API endpoints: health, auth, and dashboard routes."""

import os
import pytest
from fastapi.testclient import TestClient

# Set env vars before importing the app
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["POS_SYNC_ON_STARTUP"] = "0"
os.environ["WMS_SYNC_ON_STARTUP"] = "0"

from executive_dashboard.app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app (lifespan runs on enter)."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_token(client):
    """Get a valid auth token via login."""
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "changeme123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


class TestHealth:
    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_ready_endpoint(self, client):
        resp = client.get("/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ready"] is True


class TestAuthEndpoints:
    def test_login_success(self, client):
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "changeme123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "admin"
        assert data["user"]["role"] == "ceo"

    def test_login_wrong_password(self, client):
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/api/auth/login", json={"username": "ghost", "password": "pass"})
        assert resp.status_code == 401

    def test_me_with_valid_token(self, client, auth_token):
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {auth_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "admin"
        assert data["role"] == "ceo"

    def test_me_without_token(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_with_invalid_token(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401


class TestDashboardEndpoints:
    def test_executive_summary_requires_auth(self, client):
        resp = client.get("/api/react/executive-summary?start=2024-01-01&end=2024-12-31")
        assert resp.status_code == 401

    def test_executive_summary_with_auth(self, client, auth_token):
        resp = client.get(
            "/api/react/executive-summary?start=2024-01-01&end=2024-12-31",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200

    def test_sales_marketing_with_auth(self, client, auth_token):
        resp = client.get(
            "/api/react/sales-marketing?start=2024-01-01&end=2024-12-31",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
