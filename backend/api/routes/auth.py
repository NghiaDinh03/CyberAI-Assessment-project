"""Authentication & User Management API Routes."""

import base64
import hashlib
import hmac
import json
import logging
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

try:
    from repositories.user_store import user_store
except ImportError:
    from backend.repositories.user_store import user_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

SECRET_KEY = "cyberai-secret-jwt-key-iso27001-platform-token"


def create_token(user_data: Dict[str, Any], expires_in_sec: int = 86400 * 7) -> str:
    """Create a signed HS256-like token."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
    payload_data = {
        "sub": user_data["id"],
        "username": user_data["username"],
        "role": user_data.get("role", "user"),
        "exp": time.time() + expires_in_sec
    }
    payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).decode().rstrip("=")
    signature = hmac.new(SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).hexdigest()
    return f"{header}.{payload}.{signature}"


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify signed token signature and expiry."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header, payload, signature = parts
        expected_sig = hmac.new(SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None

        # Add padding back for base64 decode
        padded_payload = payload + "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded_payload).decode())
        if data.get("exp") and data["exp"] < time.time():
            return None
        return data
    except Exception as e:
        logger.warning(f"Token verification error: {e}")
        return None


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    email: Optional[str] = Field(None)
    full_name: Optional[str] = Field(None)
    role: Optional[str] = Field("user")


@router.post("/login")
async def login(req: LoginRequest):
    """Authenticate user with username/email and password."""
    user = user_store.authenticate(req.username, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không chính xác."
        )
    token = create_token(user)
    return {
        "status": "success",
        "token": token,
        "user": user
    }


@router.post("/register")
async def register(req: RegisterRequest):
    """Register a new user account."""
    existing = user_store.get_user_by_username(req.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tên đăng nhập đã tồn tại trên hệ thống."
        )
    if req.email:
        existing_email = user_store.get_user_by_username(req.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email đã được đăng ký tài khoản khác."
            )

    new_user = user_store.create_user(
        username=req.username,
        password=req.password,
        email=req.email,
        full_name=req.full_name,
        role=req.role or "user"
    )
    if not new_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể khởi tạo tài khoản người dùng."
        )

    safe_user = {
        "id": new_user["id"],
        "username": new_user["username"],
        "email": new_user.get("email"),
        "full_name": new_user.get("full_name"),
        "role": new_user.get("role"),
        "created_at": new_user.get("created_at")
    }
    token = create_token(safe_user)
    return {
        "status": "success",
        "message": "Đăng ký tài khoản thành công.",
        "token": token,
        "user": safe_user
    }


@router.get("/me")
async def get_current_user(authorization: Optional[str] = Header(None)):
    """Retrieve profile of current authenticated user from Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yêu cầu xác thực Bearer token."
        )
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn."
        )
    user = user_store.get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Người dùng không tồn tại."
        )
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user["role"],
        "created_at": user["created_at"]
    }


@router.get("/users")
async def list_all_users(authorization: Optional[str] = Header(None)):
    """List all users (Admin only)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload or payload.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chỉ Admin mới có quyền xem danh sách người dùng.")
    return user_store.list_users()


@router.post("/logout")
async def logout():
    """Sign out user session."""
    return {"status": "success", "message": "Đăng xuất thành công."}
