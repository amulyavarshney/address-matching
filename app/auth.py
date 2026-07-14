"""API key authentication middleware."""

import secrets
from typing import Optional

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


# Paths that never require an API key
PUBLIC_PATH_PREFIXES = (
    "/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
)


def _is_public_path(path: str) -> bool:
    if path == "/":
        return True
    for prefix in PUBLIC_PATH_PREFIXES:
        if prefix != "/" and (path == prefix or path.startswith(prefix + "/")):
            return True
    return False


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Require X-API-Key when an API key is configured.

    If api_key is None/empty, authentication is disabled (local/dev default).
    """

    def __init__(self, app, api_key: Optional[str] = None):
        super().__init__(app)
        self.api_key = (api_key or "").strip() or None
        if self.api_key:
            logger.info("API key authentication enabled for protected routes")
        else:
            logger.warning(
                "API key authentication disabled — set API_KEY for production"
            )

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self.api_key or _is_public_path(request.url.path):
            return await call_next(request)

        provided = request.headers.get("X-API-Key", "")
        if not provided or not secrets.compare_digest(provided, self.api_key):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"},
            )
        return await call_next(request)
