"""Rate-limit backends: in-memory (default) and optional Redis."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from typing import Deque, DefaultDict, Optional, Tuple

from loguru import logger


class RateLimitBackend(ABC):
    """Allow/deny decisions for a client key within a sliding/fixed window."""

    @abstractmethod
    def allow(
        self, key: str, limit: int, window_seconds: float
    ) -> Tuple[bool, int]:
        """
        Returns (allowed, retry_after_seconds).
        retry_after_seconds is 0 when allowed.
        """


class MemoryRateLimitBackend(RateLimitBackend):
    """Process-local sliding window (not shared across instances)."""

    def __init__(self) -> None:
        self._hits: DefaultDict[str, Deque[float]] = defaultdict(deque)

    def allow(
        self, key: str, limit: int, window_seconds: float
    ) -> Tuple[bool, int]:
        now = time.monotonic()
        window_start = now - window_seconds
        bucket = self._hits[key]
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        if len(bucket) >= limit:
            retry_after = max(1, int(window_seconds - (now - bucket[0])))
            return False, retry_after
        bucket.append(now)
        return True, 0


class RedisRateLimitBackend(RateLimitBackend):
    """
    Fixed-window counter in Redis for multi-instance deployments.

    Uses INCR + EXPIRE. Requires the optional `redis` package.
    """

    def __init__(self, redis_url: str, key_prefix: str = "addr_match:rl:"):
        try:
            import redis
        except ImportError as exc:
            raise RuntimeError(
                "redis package required for Redis rate limiting. "
                "Install with: pip install redis"
            ) from exc

        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._prefix = key_prefix
        # Verify connectivity early
        self._client.ping()
        logger.info("Redis rate-limit backend connected (%s)", redis_url.split("@")[-1])

    def allow(
        self, key: str, limit: int, window_seconds: float
    ) -> Tuple[bool, int]:
        window = max(1, int(window_seconds))
        bucket = int(time.time()) // window
        redis_key = f"{self._prefix}{key}:{bucket}"
        pipe = self._client.pipeline()
        pipe.incr(redis_key)
        pipe.expire(redis_key, window + 1)
        count, _ = pipe.execute()
        if int(count) > limit:
            # Seconds remaining in this fixed window
            retry_after = window - (int(time.time()) % window)
            return False, max(1, retry_after)
        return True, 0


def build_rate_limit_backend(
    backend: str = "memory",
    redis_url: Optional[str] = None,
) -> RateLimitBackend:
    name = (backend or "memory").strip().lower()
    if name in {"redis", "remote"}:
        if not redis_url:
            logger.warning(
                "RATE_LIMIT_BACKEND=redis but REDIS_URL missing; "
                "falling back to memory"
            )
            return MemoryRateLimitBackend()
        try:
            return RedisRateLimitBackend(redis_url)
        except Exception as exc:
            logger.warning(
                "Redis rate-limit backend unavailable (%s); using memory",
                exc,
            )
            return MemoryRateLimitBackend()
    return MemoryRateLimitBackend()
