"""Auth router: login, me endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import (
    LoginRequest,
    TokenResponse,
    UserContext,
    create_access_token,
    get_current_user,
    pwd_context,
)
from ..db import get_conn, put_conn

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    """Authenticate user and return JWT."""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT username, hashed_password, role, store_ids, region_ids, is_active FROM users WHERE username = %s",
            (req.username,),
        ).fetchone()

        if not row:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        username, hashed_pw, role, store_ids, region_ids, is_active = row

        if not is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account disabled")

        if not pwd_context.verify(req.password, hashed_pw):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        token, expires_in = create_access_token(username, role)

        return TokenResponse(
            access_token=token,
            expires_in=expires_in,
            user={"username": username, "role": role},
        )
    finally:
        put_conn(conn)


@router.get("/me")
def get_me(user: UserContext = Depends(get_current_user)):
    """Return current user info from JWT."""
    return {"username": user.username, "role": user.role}
