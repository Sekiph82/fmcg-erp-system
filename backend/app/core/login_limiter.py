"""
Login rate limiter + account lockout.

Per-identifier (username/IP) brute-force protection:
  - After MAX_ATTEMPTS failures within WINDOW_SECONDS → lockout for LOCKOUT_SECONDS
  - Uses Redis when available (REDIS_URL env var); falls back to in-memory.

Usage in auth endpoint:
    await check_login_allowed(identifier, db)
    # on success:
    clear_login_failures(identifier)
    # on failure:
    record_login_failure(identifier)
"""
from __future__ import annotations

import asyncio
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException

log = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 600
LOCKOUT_SECONDS = 1800

# ── In-memory fallback state ───────────────────────────────────────────────────
_failures: dict[str, list[float]] = defaultdict(list)
_lockouts: dict[str, float] = {}
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


def _now() -> float:
    return datetime.now(timezone.utc).timestamp()


async def check_login_allowed(identifier: str) -> None:
    """Raise HTTP 429 if the identifier is locked out."""
    r = _get_redis()
    if r is not None:
        try:
            ttl = await r.ttl(f"ll:lock:{identifier}")
            if ttl > 0:
                log.warning("Login blocked (lockout): %s — retry in %ds", identifier, ttl)
                raise HTTPException(
                    status_code=429,
                    detail={
                        "detail": "Account temporarily locked due to too many failed login attempts.",
                        "retry_after_seconds": ttl,
                    },
                    headers={"Retry-After": str(ttl)},
                )
            return
        except HTTPException:
            raise
        except Exception:
            log.debug("Redis unavailable in check_login_allowed, falling back to in-memory")

    async with _mem_lock:
        now = _now()
        lockout_exp = _lockouts.get(identifier)
        if lockout_exp and now < lockout_exp:
            retry_after = int(lockout_exp - now)
            log.warning("Login blocked (lockout): %s — retry in %ds", identifier, retry_after)
            raise HTTPException(
                status_code=429,
                detail={
                    "detail": "Account temporarily locked due to too many failed login attempts.",
                    "retry_after_seconds": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )
        if lockout_exp:
            del _lockouts[identifier]


async def record_login_failure(identifier: str) -> int:
    """Record a failed login. Returns total failure count in the window. Locks account if threshold reached."""
    r = _get_redis()
    if r is not None:
        try:
            now = _now()
            cutoff = now - WINDOW_SECONDS
            fail_key = f"ll:fail:{identifier}"
            async with r.pipeline() as pipe:
                pipe.zadd(fail_key, {str(now): now})
                pipe.zremrangebyscore(fail_key, "-inf", cutoff)
                pipe.expire(fail_key, WINDOW_SECONDS)
                pipe.zcard(fail_key)
                results = await pipe.execute()
            count = results[3]
            # Dual-write in-memory so sync is_locked() / get_failure_count() stay accurate
            # in single-worker deployments (and in unit tests).
            async with _mem_lock:
                _failures[identifier] = [t for t in _failures[identifier] if t > cutoff]
                _failures[identifier].append(now)
                if count >= MAX_ATTEMPTS:
                    _lockouts[identifier] = now + LOCKOUT_SECONDS
            if count >= MAX_ATTEMPTS:
                await r.setex(f"ll:lock:{identifier}", LOCKOUT_SECONDS, "1")
                log.warning("Account locked (Redis): %s — %d failures", identifier, count)
            return count
        except Exception:
            log.debug("Redis unavailable in record_login_failure, falling back to in-memory")

    async with _mem_lock:
        now = _now()
        cutoff = now - WINDOW_SECONDS
        _failures[identifier] = [t for t in _failures[identifier] if t > cutoff]
        _failures[identifier].append(now)
        count = len(_failures[identifier])
        if count >= MAX_ATTEMPTS:
            _lockouts[identifier] = now + LOCKOUT_SECONDS
            log.warning(
                "Account locked (mem): %s — %d failures in %ds window",
                identifier, count, WINDOW_SECONDS,
            )
        return count


def clear_login_failures(identifier: str) -> None:
    """Clear failure history on successful login."""
    _failures.pop(identifier, None)
    _lockouts.pop(identifier, None)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_redis_clear_failures(identifier))
    except RuntimeError:
        pass


async def _redis_clear_failures(identifier: str) -> None:
    r = _get_redis()
    if r:
        try:
            await r.delete(f"ll:fail:{identifier}", f"ll:lock:{identifier}")
        except Exception:
            pass


def get_failure_count(identifier: str) -> int:
    """Return current failure count within the window (in-memory; for diagnostics)."""
    now = _now()
    cutoff = now - WINDOW_SECONDS
    return sum(1 for t in _failures.get(identifier, []) if t > cutoff)


def is_locked(identifier: str) -> bool:
    exp = _lockouts.get(identifier)
    return bool(exp and _now() < exp)
