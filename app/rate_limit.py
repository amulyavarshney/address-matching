"""Simple in-memory / Redis rate limiting middleware."""

from __future__ import annotations

from typing import Optional

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.auth import _is_public_path
from app.rate_limit_backend import RateLimitBackend, build_rate_limit_backend


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Limit requests per client key (API key or client IP).

    Public health/docs/metrics paths are excluded. Disabled when enabled=False.
    """

    def __init__(
        self,
        app,
        *,
        enabled: bool = True,
        max_requests_per_minute: int = 60,
        backend: Optional[RateLimitBackend] = None,
        backend_name: str = "memory",
        redis_url: Optional[str] = None,
    ):
        super().__init__(app)
        self.enabled = enabled
        self.max_requests = max(1, int(max_requests_per_minute))
        self.window_seconds = 60.0
        self.backend = backend or build_rate_limit_backend(
            backend_name, redis_url=redis_url
        )
        if self.enabled:
            logger.info(
                "Rate limiting enabled: %s req/min backend=%s",
                self.max_requests,
                type(self.backend).__name__,
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
        allowed, retry_after = self.backend.allow(
            key, self.max_requests, self.window_seconds
        )
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)
