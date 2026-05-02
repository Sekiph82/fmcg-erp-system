"""
Login rate limiter + account lockout.

Per-identifier (username/IP) brute-force protection:
  - After MAX_ATTEMPTS failures within WINDOW_SECONDS → lockout for LOCKOUT_SECONDS
  - In-memory only; TODO: upgrade to Redis for multi-worker deployments.

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
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException

log = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────

MAX_ATTEMPTS = 5          # failures before lockout
WINDOW_SECONDS = 600      # 10-minute rolling window for counting failures
LOCKOUT_SECONDS = 1800    # 30-minute lockout after MAX_ATTEMPTS failures

# ── State ─────────────────────────────────────────────────────────────────────

# identifier → list of failure timestamps
_failures: dict[str, list[float]] = defaultdict(list)
# identifier → lockout expiry timestamp (None = not locked)
_lockouts: dict[str, float] = {}
_lock = asyncio.Lock()


def _now() -> float:
    return datetime.now(timezone.utc).timestamp()


async def check_login_allowed(identifier: str) -> None:
    """
    Raise HTTP 429 if the identifier (username or IP) is locked out.
    Raise HTTP 429 with retry info if too many recent failures.
    """
    async with _lock:
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
        # Clear expired lockout
        if lockout_exp:
            del _lockouts[identifier]


async def record_login_failure(identifier: str) -> int:
    """
    Record a failed login. Returns total failure count in the window.
    Locks account if threshold reached.
    """
    async with _lock:
        now = _now()
        cutoff = now - WINDOW_SECONDS
        # Prune old entries
        _failures[identifier] = [t for t in _failures[identifier] if t > cutoff]
        _failures[identifier].append(now)
        count = len(_failures[identifier])

        if count >= MAX_ATTEMPTS:
            _lockouts[identifier] = now + LOCKOUT_SECONDS
            log.warning(
                "Account locked: %s — %d failures in %ds window",
                identifier, count, WINDOW_SECONDS,
            )

        return count


def clear_login_failures(identifier: str) -> None:
    """Clear failure history on successful login."""
    _failures.pop(identifier, None)
    _lockouts.pop(identifier, None)


def get_failure_count(identifier: str) -> int:
    """Return current failure count within the window (for diagnostics)."""
    now = _now()
    cutoff = now - WINDOW_SECONDS
    return sum(1 for t in _failures.get(identifier, []) if t > cutoff)


def is_locked(identifier: str) -> bool:
    exp = _lockouts.get(identifier)
    return bool(exp and _now() < exp)
