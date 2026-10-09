"""
Simple in-memory rate limiting for the expensive /risk/score route.

Each client (identified by its IP address) may make `limit` requests in any
rolling window. Requests over the limit get `429` with a `Retry-After`
header. State lives in the process, so with several workers each one
counts separately; put a shared limiter (for example at the reverse proxy)
in front if you need an exact global limit. Behind a proxy, every request
looks like it comes from the proxy's IP unless the proxy is configured to
pass the real client address through.
"""
import math
import time
from collections import deque
from typing import Callable

from fastapi import HTTPException, Request, status

from app.config import get_settings

WINDOW_SECONDS = 60.0
_PRUNE_EVERY_KEYS = 10_000


class SlidingWindowLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}

    def reset(self) -> None:
        self._hits.clear()

    def check(self, key: str, limit: int, window: float = WINDOW_SECONDS) -> float | None:
        """
        Record a request for `key`. Returns None if it is allowed, or the
        number of seconds to wait before the next request would be allowed.
        Rejected requests are not recorded, so waiting is enough to recover.
        """
        now = self._clock()
        cutoff = now - window
        hits = self._hits.setdefault(key, deque())
        while hits and hits[0] <= cutoff:
            hits.popleft()

        if len(hits) >= limit:
            return max(hits[0] + window - now, 0.0)

        hits.append(now)
        if len(self._hits) > _PRUNE_EVERY_KEYS:
            self._prune(cutoff)
        return None

    def _prune(self, cutoff: float) -> None:
        for key in [k for k, h in self._hits.items() if not h or h[-1] <= cutoff]:
            del self._hits[key]


limiter = SlidingWindowLimiter()


async def rate_limit(request: Request) -> None:
    """FastAPI dependency. A limit of 0 or less turns rate limiting off."""
    limit = get_settings().risk_rate_limit_per_minute
    if limit <= 0:
        return

    client = request.client.host if request.client else "unknown"
    retry_after = limiter.check(client, limit)
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests; slow down and retry shortly.",
            headers={"Retry-After": str(max(1, math.ceil(retry_after)))},
        )
