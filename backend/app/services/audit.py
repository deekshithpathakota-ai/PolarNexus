"""Audit logging, analytics events and notifications."""
import logging

from sqlalchemy.orm import Session

from app.models import AnalyticsEvent, AuditLog, Notification, User

log = logging.getLogger("polarnexus.audit")


def audit(
    db: Session,
    user: User | None,
    action: str,
    resource_type: str = "",
    resource_id: str | int = "",
    detail: str = "",
    status: str = "success",
    commit: bool = True,
) -> None:
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            user_email=user.email if user else "anonymous",
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            detail=detail[:2000],
            status=status,
        )
    )
    if commit:
        db.commit()
    log.info("audit action=%s user=%s resource=%s:%s status=%s", action, user.email if user else "-", resource_type, resource_id, status)


def track(db: Session, event_type: str, resource_type: str = "", resource_id: int | None = None,
          user: User | None = None, meta: dict | None = None, commit: bool = True) -> None:
    db.add(AnalyticsEvent(event_type=event_type, resource_type=resource_type, resource_id=resource_id,
                          user_id=user.id if user else None, meta=meta or {}))
    if commit:
        db.commit()


def notify(db: Session, title: str, body: str = "", link: str = "", kind: str = "info",
           user_id: int | None = None, role: str = "", commit: bool = True) -> None:
    db.add(Notification(title=title, body=body, link=link, kind=kind, user_id=user_id, role=role))
    if commit:
        db.commit()
