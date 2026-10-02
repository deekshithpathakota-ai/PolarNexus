import time
from collections import defaultdict, deque
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import clear_session_cookie, create_access_token, get_current_user, set_session_cookie, verify_password
from app.core.config import settings
from app.core.database import get_db
from app.models import Role, User
from app.schemas.common import DemoLoginRequest, LoginRequest, TokenOut, UserOut
from app.services.audit import audit
from app.services.serializers import user_out

router = APIRouter(prefix="/api/auth", tags=["auth"])

DEMO_EMAILS = {
    "public": "public@polarnexus.demo",
    "researcher": "researcher@polarnexus.demo",
    "editor": "editor@polarnexus.demo",
    "admin": "admin@polarnexus.demo",
}


def _issue(db: Session, user: User, how: str, response: Response | None = None) -> dict:
    user.last_login = datetime.now(timezone.utc)
    audit(db, user, "login", "user", user.id, f"Signed in ({how})")
    token = create_access_token(user)
    if response is not None:
        set_session_cookie(response, token)  # HttpOnly cookie in addition to the (unchanged) bearer token
    return {"access_token": token, "token_type": "bearer", "user": user_out(user)}


_failures: dict[tuple[str, str], deque] = defaultdict(deque)


def _throttled(key: tuple[str, str]) -> bool:
    window = settings.LOGIN_WINDOW_SECONDS
    q = _failures[key]
    now = time.monotonic()
    while q and now - q[0] > window:
        q.popleft()
    return len(q) >= settings.LOGIN_MAX_FAILURES


@router.post("/login", response_model=TokenOut)
def login(body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    email = body.email.lower().strip()
    key = (request.client.host if request.client else "-", email)
    if _throttled(key):
        audit(db, None, "login", "user", email[:64], "Throttled after repeated failures", status="failure")
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Too many failed sign-in attempts. Please wait a few minutes and try again.")
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(body.password, user.password_hash):
        _failures[key].append(time.monotonic())
        audit(db, user, "login", "user", email[:64], "Invalid credentials", status="failure")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    _failures.pop(key, None)
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been disabled by an administrator.")
    return _issue(db, user, "password", response)


@router.post("/demo-login", response_model=TokenOut)
def demo_login(body: DemoLoginRequest, response: Response, db: Session = Depends(get_db)):
    if not settings.DEMO_MODE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Demo accounts are disabled on this deployment.")
    user = db.scalar(select(User).where(User.email == DEMO_EMAILS[body.role]))
    if not user:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Demo data has not been seeded yet.")
    return _issue(db, user, "demo account", response)


@router.get("/demo-accounts")
def demo_accounts(db: Session = Depends(get_db)):
    if not settings.DEMO_MODE:
        return {"enabled": False, "accounts": []}
    roles = {r.name: r for r in db.scalars(select(Role))}
    out = []
    for role, email in DEMO_EMAILS.items():
        u = db.scalar(select(User).where(User.email == email))
        if u:
            out.append({"role": role, "label": roles[role].label if role in roles else role, "email": email,
                        "name": u.name, "description": roles[role].description if role in roles else ""})
    return {"enabled": True, "accounts": out}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user_out(user)


@router.post("/logout")
def logout(response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    audit(db, user, "logout", "user", user.id, "Signed out")
    clear_session_cookie(response)
    return {"ok": True}
