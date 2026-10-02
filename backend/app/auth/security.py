"""JWT authentication, password hashing and role-based access control."""
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models import User

ALGORITHM = "HS256"

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "public": ["search", "read", "ask_ai"],
    "researcher": ["search", "read", "ask_ai", "upload", "manage_own", "generate_content", "save"],
    "editor": [
        "search", "read", "ask_ai", "generate_content", "save",
        "review", "approve", "publish", "edit_content",
    ],
    "admin": [
        "search", "read", "ask_ai", "upload", "manage_own", "generate_content", "save",
        "review", "approve", "publish", "edit_content",
        "manage_repository", "manage_users", "view_audit", "view_analytics", "view_internal",
    ],
}

ROLE_INFO = {
    "public": ("Public User", "Search, explore, read and ask the AI assistant."),
    "researcher": ("Researcher", "Upload resources, manage own uploads, use AI and create outreach drafts."),
    "editor": ("Editor", "Review AI-generated content, edit, approve, reject and publish."),
    "admin": ("Administrator", "Manage the repository, users, roles, analytics and audit logs."),
}

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=10)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": str(user.id), "role": user.role_name, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def permissions_for(role: str) -> list[str]:
    return ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["public"])


SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_HEADER = "x-polarnexus-client"


def get_current_user_optional(
    request: Request, creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> User | None:
    token = creds.credentials if creds else None
    if not token and settings.AUTH_COOKIE_ENABLED:
        # HttpOnly session cookie (v3). Browsers attach it automatically, so state-changing requests that rely on
        # the cookie alone must also carry a custom header — a cross-site form cannot set it (CSRF protection).
        token = request.cookies.get(settings.AUTH_COOKIE_NAME)
        if token and request.method not in SAFE_METHODS and not request.headers.get(CSRF_HEADER):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Missing client header for a cookie-authenticated request.")
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub", 0))
    except (JWTError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired or invalid. Please sign in again.")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account not found or disabled.")
    return user


def get_current_user(user: User | None = Depends(get_current_user_optional)) -> User:
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in required.")
    return user


def require_permission(permission: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if permission not in permissions_for(user.role_name):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Your role ({user.role_name}) does not have the '{permission}' permission.",
            )
        return user

    return checker


def can(user: User | None, permission: str) -> bool:
    return permission in permissions_for(user.role_name if user else "public")


def set_session_cookie(response: Response, token: str) -> None:
    if not settings.AUTH_COOKIE_ENABLED:
        return
    response.set_cookie(settings.AUTH_COOKIE_NAME, token, max_age=settings.JWT_EXPIRE_MINUTES * 60, httponly=True,
                        secure=settings.is_production, samesite="lax", path="/")


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(settings.AUTH_COOKIE_NAME, path="/", httponly=True, secure=settings.is_production, samesite="lax")
