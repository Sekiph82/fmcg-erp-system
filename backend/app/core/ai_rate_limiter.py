"""
In-memory per-user AI rate limiter.

NOTE: Suitable for single-worker deployments.
For multi-worker production, replace _store with Redis-backed counter
(e.g., slowapi + redis, or custom Redis INCR with TTL).

TODO: upgrade to Redis before horizontal scaling.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException

# (user_id_str, endpoint) -> list of unix timestamps
_store: dict[tuple[str, str], list[float]] = defaultdict(list)
_lock = asyncio.Lock()


async def check_rate_limit(
    user_id: str,
    endpoint: str,
    limit: int,
    window_seconds: int = 3600,
) -> None:
    """
    Raise HTTP 429 if user has exceeded `limit` calls to `endpoint`
    within the rolling `window_seconds` window (default: 1 hour).
    """
    key = (str(user_id), endpoint)
    now = datetime.now(timezone.utc).timestamp()
    cutoff = now - window_seconds

    async with _lock:
        _store[key] = [t for t in _store[key] if t > cutoff]

        if len(_store[key]) >= limit:
            oldest = _store[key][0]
            reset_at = datetime.fromtimestamp(oldest + window_seconds, tz=timezone.utc)
            raise HTTPException(
                status_code=429,
                detail={
                    "detail": "AI rate limit exceeded. Please try again later.",
                    "limit": limit,
                    "window_hours": round(window_seconds / 3600, 1),
                    "reset_at": reset_at.isoformat(),
                },
            )

        _store[key].append(now)


def get_usage_count(user_id: str, endpoint: str, window_seconds: int = 3600) -> int:
    """Return current call count for user+endpoint within the rolling window."""
    key = (str(user_id), endpoint)
    now = datetime.now(timezone.utc).timestamp()
    cutoff = now - window_seconds
    return sum(1 for t in _store.get(key, []) if t > cutoff)
