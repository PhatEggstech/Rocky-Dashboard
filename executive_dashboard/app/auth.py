"""JWT Authentication + RBAC for Rocky Lens Dashboard."""
import os
import logging
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from .db import get_conn, put_conn

logger = logging.getLogger(__name__)

# Config
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "rocky-lens-dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "8"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


# --- Models ---

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


@dataclass
class UserContext:
    username: str
    role: str
    store_ids: list[str] | None = None
    region_ids: list[str] | None = None


# --- RBAC Page Permissions ---

PAGE_ROLES = {
    "executive-summary": {"ceo", "bod", "cfo", "om", "rsm", "sup", "store_manager"},
    "sales-marketing": {"ceo", "bod", "om", "rsm", "sup", "store_manager"},
    "inventory": {"ceo", "bod", "om"},
    "quality-clv": {"ceo", "bod", "cfo", "om", "store_manager"},
    "store-leaderboard": {"ceo", "bod", "cfo", "om", "rsm", "sup"},
    "csat-by-store": {"ceo", "bod", "cfo", "rsm"},
    "revenue-per-staff": {"ceo", "bod", "cfo", "rsm"},
    "b2b-analytics": {"ceo", "bod"},
    "conversation": {"ceo", "bod", "cfo", "om", "rsm", "sup", "store_manager"},
}


# --- DB Schema (users table is created via db.py init_schema) ---

def seed_admin_user(conn=None):
    """Seed default admin user if no users exist."""
    own_conn = conn is None
    if own_conn:
        conn = get_conn()
    try:
        cur = conn.execute("SELECT COUNT(*) FROM users")
        count = cur.fetchone()[0]
        if count == 0:
            hashed = pwd_context.hash("changeme123")
            conn.execute(
                "INSERT INTO users (username, hashed_password, role) VALUES (%s, %s, %s)",
                ("admin", hashed, "ceo"),
            )
            conn.commit()
            logger.info("Seeded default admin user (admin/changeme123)")
    finally:
        if own_conn:
            put_conn(conn)


# --- Token Operations ---

def create_access_token(username: str, role: str) -> tuple[str, int]:
    """Create JWT. Returns (token, expires_in_seconds)."""
    expires_delta = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": username,
        "role": role,
        "exp": expire,
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token, int(expires_delta.total_seconds())


def verify_token(token: str) -> dict | None:
    """Verify and decode JWT. Returns payload or None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# --- FastAPI Dependencies ---

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> UserContext:
    """Extract and validate JWT -> UserContext. Raises 401 if invalid."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserContext(
        username=payload["sub"],
        role=payload["role"],
    )


def require_page(page_key: str):
    """Dependency factory: verify user has access to the given page."""
    def checker(user: UserContext = Depends(get_current_user)) -> UserContext:
        allowed_roles = PAGE_ROLES.get(page_key, set())
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' cannot access '{page_key}'",
            )
        return user
    return checker
