import os
import time
from collections import deque
from threading import Lock

from fastapi import HTTPException, Request, status


class SlidingWindowLimiter:
    """In-memory per-key limiter: at most `limit` hits per `window` seconds. Single-process only."""

    def __init__(self, limit: int, window: float = 60.0) -> None:
        self.limit = limit
        self.window = window
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] >= self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            # Drop idle keys so memory stays bounded by active clients.
            if len(self._hits) > 10_000:
                for k in [k for k, v in self._hits.items() if not v or now - v[-1] >= self.window]:
                    del self._hits[k]
            return True


def search_limit_per_minute() -> int:
    return int(os.environ.get("SEARCH_RATE_LIMIT_PER_MIN", "30"))


def trust_proxy() -> bool:
    return os.environ.get("TRUST_PROXY") == "1"


def client_key(request: Request) -> str:
    # Fly-Client-IP is only trustworthy behind Fly's proxy; otherwise anyone can spoof it.
    if request.app.state.trust_proxy:
        forwarded = request.headers.get("fly-client-ip", "").strip()
        if forwarded:
            return forwarded
    return request.client.host if request.client else "unknown"


def limit_search(request: Request) -> None:
    limiter: SlidingWindowLimiter = request.app.state.search_limiter
    if not limiter.allow(client_key(request)):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "search rate limit exceeded",
            headers={"Retry-After": str(int(limiter.window))},
        )
