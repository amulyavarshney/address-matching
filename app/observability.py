"""In-process metrics and request-id helpers for production observability."""

from __future__ import annotations

import threading
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Dict, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


@dataclass
class MetricsRegistry:
    """Simple thread-safe counters for Prometheus-style exposition."""

    _lock: threading.Lock = field(default_factory=threading.Lock)
    http_requests_total: int = 0
    http_requests_by_status: Dict[str, int] = field(default_factory=dict)
    http_request_duration_seconds_sum: float = 0.0
    match_requests_total: int = 0
    match_positive_total: int = 0
    match_errors_total: int = 0

    def observe_http(self, status_code: int, duration_seconds: float) -> None:
        with self._lock:
            self.http_requests_total += 1
            key = str(status_code)
            self.http_requests_by_status[key] = (
                self.http_requests_by_status.get(key, 0) + 1
            )
            self.http_request_duration_seconds_sum += duration_seconds

    def observe_match(self, matched: bool) -> None:
        with self._lock:
            self.match_requests_total += 1
            if matched:
                self.match_positive_total += 1

    def observe_match_error(self) -> None:
        with self._lock:
            self.match_errors_total += 1

    def render_prometheus(self) -> str:
        with self._lock:
            lines = [
                "# HELP address_matching_http_requests_total Total HTTP requests",
                "# TYPE address_matching_http_requests_total counter",
                f"address_matching_http_requests_total {self.http_requests_total}",
                "# HELP address_matching_http_request_duration_seconds_sum "
                "Sum of HTTP request durations",
                "# TYPE address_matching_http_request_duration_seconds_sum counter",
                "address_matching_http_request_duration_seconds_sum "
                f"{self.http_request_duration_seconds_sum:.6f}",
                "# HELP address_matching_match_requests_total Match API calls",
                "# TYPE address_matching_match_requests_total counter",
                f"address_matching_match_requests_total {self.match_requests_total}",
                "# HELP address_matching_match_positive_total Positive match decisions",
                "# TYPE address_matching_match_positive_total counter",
                f"address_matching_match_positive_total {self.match_positive_total}",
                "# HELP address_matching_match_errors_total Match API errors",
                "# TYPE address_matching_match_errors_total counter",
                f"address_matching_match_errors_total {self.match_errors_total}",
            ]
            for status, count in sorted(self.http_requests_by_status.items()):
                lines.append(
                    'address_matching_http_responses_total{'
                    f'status="{status}"'
                    f'}} {count}'
                )
            lines.append("")
            return "\n".join(lines)


metrics = MetricsRegistry()


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Propagate or generate X-Request-ID for each request."""

    header_name = "X-Request-ID"

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(self.header_name) or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        duration = time.perf_counter() - started
        metrics.observe_http(response.status_code, duration)
        response.headers[self.header_name] = request_id
        return response


def get_request_id() -> str:
    return request_id_ctx.get()
