# GFIN Rate Limiter — Request Rate Limiting
#
# Per Constitution Article XXVII and Master Spec §45:
# Protect against API abuse, DoS, and resource exhaustion.
#
# Layer A: In-memory token bucket (development)
# Layer B: Redis-backed distributed rate limiter (REQUIRES EXTERNAL INFRASTRUCTURE)

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

import structlog

logger = structlog.get_logger("gfin.rate_limit")

DEFAULT_RATE_LIMITS = {
    "citizen": {"requests": 60, "window_seconds": 60},
    "analyst": {"requests": 200, "window_seconds": 60},
    "investigator": {"requests": 500, "window_seconds": 60},
    "administrator": {"requests": 1000, "window_seconds": 60},
}


@dataclass
class RateLimitBucket:
    """Token bucket for rate limiting."""
    user_id: str
    requests: list[float] = field(default_factory=list)
    max_requests: int = 60
    window_seconds: int = 60

    def is_allowed(self) -> bool:
        """Check if request is allowed under current rate limit."""
        now = time.time()
        cutoff = now - self.window_seconds
        self.requests = [t for t in self.requests if t > cutoff]
        if len(self.requests) >= self.max_requests:
            return False
        self.requests.append(now)
        return True

    def remaining(self) -> int:
        """Remaining requests in current window."""
        now = time.time()
        cutoff = now - self.window_seconds
        active = sum(1 for t in self.requests if t > cutoff)
        return max(0, self.max_requests - active)


class RateLimiter:
    """In-memory rate limiter (development).
    
    Production: Redis-backed distributed rate limiter
    (REQUIRES EXTERNAL INFRASTRUCTURE).
    """

    def __init__(
        self,
        limits: dict[str, dict[str, int]] | None = None,
    ) -> None:
        self._limits = limits or DEFAULT_RATE_LIMITS
        self._buckets: dict[str, RateLimitBucket] = {}

    def is_allowed(
        self,
        user_id: str,
        role: str = "citizen",
    ) -> bool:
        """Check if request is allowed. Returns True if allowed."""
        limit_config = self._limits.get(role)
        if limit_config is None:
            limit_config = next(iter(self._limits.values()), {"requests": 60, "window_seconds": 60})
        key = f"{user_id}:{role}"

        if key not in self._buckets:
            self._buckets[key] = RateLimitBucket(
                user_id=user_id,
                max_requests=limit_config["requests"],
                window_seconds=limit_config["window_seconds"],
            )

        bucket = self._buckets[key]
        allowed = bucket.is_allowed()

        if not allowed:
            logger.warning(
                "rate_limit_exceeded",
                user_id=user_id,
                role=role,
                remaining=0,
            )

        return allowed

    def remaining(self, user_id: str, role: str = "citizen") -> int:
        """Get remaining requests for user."""
        key = f"{user_id}:{role}"
        bucket = self._buckets.get(key)
        if not bucket:
            limit_config = self._limits.get(role)
            if limit_config is None:
                limit_config = next(iter(self._limits.values()), {"requests": 60, "window_seconds": 60})
            return limit_config["requests"]
        return bucket.remaining()

    def reset(self, user_id: str, role: str = "citizen") -> None:
        """Reset rate limit for a user (admin action)."""
        key = f"{user_id}:{role}"
        if key in self._buckets:
            del self._buckets[key]
