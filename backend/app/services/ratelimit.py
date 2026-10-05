"""In-process sliding-window rate limiting for public endpoints.

Deliberately dependency-free (stdlib + FastAPI primitives only): the supported
deployment is a single uvicorn worker behind docker-compose, so an in-memory
limiter is sufficient and keeps the offline/no-API-key path working. Limits are
configured per scope via settings (<scope>_rate_limit_per_minute); a value of 0
disables limiting entirely.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Callable

from fastapi import HTTPException, Request

from app.config import get_settings


class SlidingWindowLimiter:
    """max_events per window_seconds per key, using an injectable clock."""

    def __init__(
        self,
        max_events: int,
        window_seconds: float,
        *,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_events = max_events
        self.window_seconds = window_seconds
        self._now = now
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str) -> bool:
        """Record one event for key; return False when the cap is reached."""
        if self.max_events <= 0:  # disabled
            return True
        now = self._now()
        hits = self._hits[key]
        cutoff = now - self.window_seconds
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= self.max_events:
            return False
        hits.append(now)
        return True


_limiters: dict[str, tuple[tuple[int, float], SlidingWindowLimiter]] = {}


def _limiter_for(scope: str, per_minute: int) -> SlidingWindowLimiter:
    window = 60.0
    config = (per_minute, window)
    cached = _limiters.get(scope)
    if cached is None or cached[0] != config:
        limiter = SlidingWindowLimiter(per_minute, window)
        _limiters[scope] = (config, limiter)
        return limiter
    return cached[1]


def _client_key(request: Request, identity: str | None) -> str:
    if identity:
        return f"id:{identity}"
    host = request.client.host if request.client else "unknown"
    return f"ip:{host}"


async def enforce_rate_limit(
    request: Request,
    *,
    scope: str,
    identity: str | None = None,
) -> None:
    """Raise HTTP 429 when this caller exceeds the scope's per-minute budget."""
    settings = get_settings()
    per_minute = int(getattr(settings, f"{scope}_rate_limit_per_minute", 0) or 0)
    if per_minute <= 0:
        return
    limiter = _limiter_for(scope, per_minute)
    if not limiter.hit(_client_key(request, identity)):
        raise HTTPException(
            status_code=429,
            detail="Too many requests — vui lòng thử lại sau một phút.",
        )
