"""
Per-user AI rate limiter.

Uses Redis when available (REDIS_URL env var); falls back to in-memory for single-worker setups.
"""
from __future__ import annotations

import asyncio
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException

log = logging.getLogger(__name__)

# ── In-memory fallback ─────────────────────────────────────────────────────────
_store: dict[tuple[str, str], list[float]] = defaultdict(list)
_mem_lock = asyncio.Lock()

# ── Redis client (lazy-init) ───────────────────────────────────────────────────
_redis = None


def _get_redis():
    global _redis
    if _redis is not None:
        return _redis
    try:
        import redis.asyncio as aioredis
        url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        _redis = aioredis.from_url(url, decode_responses=True)
    except Exception:
        pass
    return _redis


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
    r = _get_redis()
    if r is not None:
        try:
            now = datetime.now(timezone.utc).timestamp()
            cutoff = now - window_seconds
            key = f"ai:rl:{user_id}:{endpoint}"
            async with r.pipeline() as pipe:
                pipe.zremrangebyscore(key, "-inf", cutoff)
                pipe.zcard(key)
                results = await pipe.execute()
            current = results[1]
            if current >= limit:
                oldest_entries = await r.zrange(key, 0, 0, withscores=True)
                oldest = oldest_entries[0][1] if oldest_entries else now
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
            await r.zadd(key, {str(now): now})
            await r.expire(key, window_seconds)
            return
        except HTTPException:
            raise
        except Exception:
            log.debug("Redis unavailable in check_rate_limit, falling back to in-memory")

    key = (str(user_id), endpoint)
    now = datetime.now(timezone.utc).timestamp()
    cutoff = now - window_seconds

    async with _mem_lock:
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
    """Return current call count for user+endpoint within the rolling window (in-memory only)."""
    key = (str(user_id), endpoint)
    now = datetime.now(timezone.utc).timestamp()
    cutoff = now - window_seconds
    return sum(1 for t in _store.get(key, []) if t > cutoff)
