from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, get_current_user, verify_password
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


def _issue(db: Session, user: User, how: str) -> dict:
    user.last_login = datetime.now(timezone.utc)
    audit(db, user, "login", "user", user.id, f"Signed in ({how})")
    return {"access_token": create_access_token(user), "token_type": "bearer", "user": user_out(user)}


@router.post("/login", response_model=TokenOut)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower().strip()))
    if not user or not verify_password(body.password, user.password_hash):
        audit(db, user, "login", "user", body.email[:64], "Invalid credentials", status="failure")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been disabled by an administrator.")
    return _issue(db, user, "password")


@router.post("/demo-login", response_model=TokenOut)
def demo_login(body: DemoLoginRequest, db: Session = Depends(get_db)):
    if not settings.DEMO_MODE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Demo accounts are disabled on this deployment.")
    user = db.scalar(select(User).where(User.email == DEMO_EMAILS[body.role]))
    if not user:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Demo data has not been seeded yet.")
    return _issue(db, user, "demo account")


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
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    audit(db, user, "logout", "user", user.id, "Signed out")
    return {"ok": True}
