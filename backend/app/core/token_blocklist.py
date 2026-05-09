"""
Token blocklist — invalidates JWTs on logout before their natural expiry.

Uses Redis when available (REDIS_URL env var); falls back to in-memory.
In multi-worker deployments, Redis is required for correctness.

Usage (async):
    await blocklist.add(jti_or_token, expire_at_unix_ts)
    await blocklist.is_blocked(jti_or_token) -> bool
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import time

log = logging.getLogger(__name__)

# ── In-memory fallback ─────────────────────────────────────────────────────────
_store: dict[str, float] = {}
_mem_lock = asyncio.Lock()
_CLEANUP_EVERY = 500
_op_counter = 0

# ── Redis client (lazy-init, async) ────────────────────────────────────────────
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


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()[:32]


def _cleanup() -> None:
    now = time.time()
    expired = [k for k, exp in _store.items() if exp <= now]
    for k in expired:
        del _store[k]


async def add(token: str, expire_at: float) -> None:
    """Block a token until its natural expiry time."""
    global _op_counter
    h = _hash_token(token)
    ttl = int(expire_at - time.time())
    if ttl <= 0:
        return

    r = _get_redis()
    if r is not None:
        try:
            await r.setex(f"bl:{h}", ttl, "1")
            return
        except Exception:
            log.debug("Redis unavailable in blocklist.add, falling back to in-memory")

    async with _mem_lock:
        _store[h] = expire_at
        _op_counter += 1
        if _op_counter % _CLEANUP_EVERY == 0:
            _cleanup()


async def is_blocked(token: str) -> bool:
    """Return True if the token has been explicitly invalidated."""
    h = _hash_token(token)

    r = _get_redis()
    if r is not None:
        try:
            return bool(await r.exists(f"bl:{h}"))
        except Exception:
            log.debug("Redis unavailable in is_blocked, falling back to in-memory")

    async with _mem_lock:
        exp = _store.get(h)
        if exp is None:
            return False
        if time.time() > exp:
            del _store[h]
            return False
        return True


async def revoke_all_for_user(user_id: str, expiry: float) -> None:
    """
    Adds a user-level revocation marker.
    Any token issued before this timestamp should be treated as revoked.
    Full per-token invalidation requires token JTIs stored in DB;
    this provides approximate user-level logout.
    """
    marker_key = f"user:{user_id}"
    ttl = int(expiry - time.time())

    r = _get_redis()
    if r is not None:
        try:
            if ttl > 0:
                await r.setex(f"bl:{marker_key}", ttl, "1")
            log.info("All tokens revoked for user=%s until ts=%s (Redis)", user_id, expiry)
            return
        except Exception:
            log.debug("Redis unavailable in revoke_all_for_user, falling back to in-memory")

    async with _mem_lock:
        _store[marker_key] = expiry
    log.info("All tokens revoked for user=%s until ts=%s (mem)", user_id, expiry)


async def store_size() -> int:
    r = _get_redis()
    if r is not None:
        try:
            return await r.dbsize()
        except Exception:
            pass
    async with _mem_lock:
        return len(_store)
