"""Simple in-memory sliding-window rate limiting."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque, DefaultDict, Optional

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.auth import _is_public_path


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Limit requests per client key (API key or client IP).

    Public health/docs paths are excluded. Disabled when enabled=False.
    """

    def __init__(
        self,
        app,
        *,
        enabled: bool = True,
        max_requests_per_minute: int = 60,
    ):
        super().__init__(app)
        self.enabled = enabled
        self.max_requests = max(1, int(max_requests_per_minute))
        self.window_seconds = 60.0
        self._hits: DefaultDict[str, Deque[float]] = defaultdict(deque)
        if self.enabled:
            logger.info(
                "Rate limiting enabled: %s requests/minute",
                self.max_requests,
            )

    def _client_key(self, request: Request) -> str:
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"key:{api_key}"
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        client = request.client.host if request.client else "unknown"
        return f"ip:{client}"

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self.enabled or _is_public_path(request.url.path):
            return await call_next(request)

        key = self._client_key(request)
        now = time.monotonic()
        window_start = now - self.window_seconds
        bucket = self._hits[key]

        while bucket and bucket[0] < window_start:
            bucket.popleft()

        if len(bucket) >= self.max_requests:
            retry_after = max(1, int(self.window_seconds - (now - bucket[0])))
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(retry_after)},
            )

        bucket.append(now)
        return await call_next(request)
