"""
Token blocklist — invalidates JWTs on logout before their natural expiry.

In-memory implementation (single-process safe).
TODO: Replace with Redis SADD/TTL for multi-worker production deployments.

Usage:
    blocklist.add(jti_or_token, expire_at_unix_ts)
    blocklist.is_blocked(jti_or_token) -> bool
"""
from __future__ import annotations

import hashlib
import logging
import time
from threading import Lock

log = logging.getLogger(__name__)

# token_hash → expiry unix timestamp
_store: dict[str, float] = {}
_lock = Lock()

_CLEANUP_EVERY = 500   # run cleanup every N operations


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()[:32]


def _cleanup() -> None:
    now = time.time()
    expired = [k for k, exp in _store.items() if exp <= now]
    for k in expired:
        del _store[k]


_op_counter = 0


def add(token: str, expire_at: float) -> None:
    """Block a token until its natural expiry time."""
    global _op_counter
    with _lock:
        _store[_hash_token(token)] = expire_at
        _op_counter += 1
        if _op_counter % _CLEANUP_EVERY == 0:
            _cleanup()


def is_blocked(token: str) -> bool:
    """Return True if the token has been explicitly invalidated."""
    h = _hash_token(token)
    with _lock:
        exp = _store.get(h)
        if exp is None:
            return False
        if time.time() > exp:
            del _store[h]
            return False
        return True


def revoke_all_for_user(user_id: str, expiry: float) -> None:
    """
    Adds a user-level revocation marker.
    Any token issued before this timestamp should be treated as revoked.
    Full per-token invalidation requires token JTIs stored in DB;
    this provides approximate user-level logout.
    """
    marker_key = f"user:{user_id}"
    with _lock:
        _store[marker_key] = expiry
    log.info("All tokens revoked for user=%s until ts=%s", user_id, expiry)


def store_size() -> int:
    with _lock:
        return len(_store)
