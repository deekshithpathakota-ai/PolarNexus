"""Small in-memory, per-client-IP sliding-window rate limiter for expensive endpoints (AI, uploads).

It protects a single API instance from accidental floods; a multi-instance production deployment should add a
shared limiter (reverse proxy or Redis). Limits are configurable and 0 disables a bucket.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.core.config import settings

_hits: dict[tuple[str, str], deque] = defaultdict(deque)


def _limit(bucket: str) -> int:
    return {"ai": settings.RATE_LIMIT_AI_PER_MINUTE, "upload": settings.RATE_LIMIT_UPLOADS_PER_MINUTE}.get(bucket, 0)


def rate_limit(bucket: str):
    def dep(request: Request) -> None:
        limit = _limit(bucket)
        if limit <= 0:
            return
        ip = request.client.host if request.client else "-"
        q = _hits[(bucket, ip)]
        now = time.monotonic()
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                                "Too many requests in a short time. Please wait a minute and try again.")
        q.append(now)

    return dep


def reset() -> None:
    _hits.clear()
