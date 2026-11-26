"""M50.S01.T008 atomic AI budget ledger for agents.

A run RESERVES its worst-case cost before it calls a model and SETTLES the measured cost afterwards:

  reserve → (record_usage per model call, extend if the run needs more) → settle

* Atomic: each scope (company, user, agent, per day) is one row in ai_budget_counters; a reservation is a conditional
  UPDATE (`reserved + spent + :c <= cap`), so simultaneous workers queue on the row lock and the sum of what they hold
  can never pass the cap. Scopes are always locked in the order company → user → agent (no deadlocks); a denial rolls
  every scope back.
* Durable: reservations use their own short transactions (committed before the model is called), so a crashed worker
  leaves a visible RESERVED row. It carries a lease; record_usage is the heartbeat. recover_stuck() settles expired
  leases charging only the usage that was measured, never more than reserved, and never silently drops it.
* Idempotent: the reservation key is unique (job id + attempt); settle() and release are no-ops the second time.
"""
from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

LEASE_SECONDS = 900
HEARTBEAT_SECONDS = LEASE_SECONDS // 3


def worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"[:60]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _factory(factory=None):
    if factory is not None:
        return factory
    from app.db.session import AsyncSessionLocal
    return AsyncSessionLocal


@dataclass
class Reservation:
    id: Optional[str]
    ok: bool
    reserved_cost: Decimal = Decimal(0)
    reserved_tokens: int = 0
    day: Optional[date] = None
    denied_scope: Optional[str] = None
    contended: bool = False      # denied only because other runs hold reservations right now (may succeed shortly)
    reason: Optional[str] = None


def _scopes(agent_id, user_id, caps: dict) -> list[tuple[str, str, Decimal]]:
    out = [("COMPANY", "all", Decimal(str(caps["company"])))]
    if user_id:
        out.append(("USER", str(user_id), Decimal(str(caps["user"]))))
    out.append(("AGENT", str(agent_id), Decimal(str(caps["agent"]))))
    return out


_RESERVE = text("""UPDATE ai_budget_counters SET cap_cost = :cap, reserved_cost = reserved_cost + :c, reserved_tokens = reserved_tokens + :k
                   WHERE scope_type = :t AND scope_id = :i AND day = :d AND reserved_cost + spent_cost + :c <= :cap
                   RETURNING reserved_cost""")
_ENSURE = text("""INSERT INTO ai_budget_counters (scope_type, scope_id, day, cap_cost, reserved_cost, spent_cost, reserved_tokens, spent_tokens)
                  VALUES (:t, :i, :d, :cap, 0, 0, 0, 0) ON CONFLICT DO NOTHING""")


async def _take(s, scopes, day, cost: Decimal, tokens: int) -> Optional[tuple[str, bool]]:
    """Reserve in every scope inside the open transaction; None = all fit, else (denied scope, contended)."""
    for t, i, cap in scopes:
        p = {"t": t, "i": i, "d": day, "cap": cap, "c": cost, "k": tokens}
        await s.execute(_ENSURE, p)
        if (await s.execute(_RESERVE, p)).first() is None:
            row = (await s.execute(text("SELECT spent_cost FROM ai_budget_counters WHERE scope_type=:t AND scope_id=:i AND day=:d"), p)).first()
            return t, bool(row and Decimal(row[0]) + cost <= cap)
    return None


async def reserve(*, agent_id, user_id, est_cost: Decimal, est_tokens: int, caps: dict, key: str, job_id=None,
                  lease_s: int = LEASE_SECONDS, factory=None) -> Reservation:
    """caps = {"company": x, "user": y, "agent": z} (cost per day). Returns ok=False (nothing held) if any cap would be passed."""
    import uuid
    est_cost = Decimal(str(est_cost)).quantize(Decimal("0.000001"))
    day = _now().date()
    async with _factory(factory)() as s:
        old = (await s.execute(text("SELECT id, reserved_cost, reserved_tokens, day, status FROM ai_budget_reservations WHERE idempotency_key=:k"), {"k": key})).first()
        if old:
            return Reservation(str(old[0]), old[4] == "RESERVED", Decimal(old[1]), old[2], old[3])
        denied = await _take(s, _scopes(agent_id, user_id, caps), day, est_cost, est_tokens)
        if denied:
            await s.rollback()
            return Reservation(None, False, denied_scope=denied[0], contended=denied[1],
                               reason=f"{denied[0].title()} AI budget for today would be exceeded.")
        rid = uuid.uuid4()
        try:
            await s.execute(text("""INSERT INTO ai_budget_reservations (id, idempotency_key, job_id, agent_id, user_id, day, reserved_cost,
                reserved_tokens, actual_cost, actual_tokens, status, worker_id, expires_at, created_at)
                VALUES (:id, :k, :j, :a, :u, :d, :c, :t, 0, 0, 'RESERVED', :w, :e, now())"""),
                            {"id": rid, "k": key, "j": job_id, "a": str(agent_id), "u": str(user_id) if user_id else None, "d": day,
                             "c": est_cost, "t": est_tokens, "w": worker_id(), "e": _now() + timedelta(seconds=lease_s)})
            await s.commit()
        except IntegrityError:           # same key raced in: use that reservation, give ours back
            await s.rollback()
            return await reserve(agent_id=agent_id, user_id=user_id, est_cost=est_cost, est_tokens=est_tokens, caps=caps,
                                 key=key, job_id=job_id, factory=factory)
    return Reservation(str(rid), True, est_cost, est_tokens, day)


async def record_usage(rid: str, tokens: int, cost: Decimal, lease_s: int = LEASE_SECONDS, factory=None) -> None:
    """Add measured usage to the reservation (and extend its lease: this is the worker's heartbeat)."""
    async with _factory(factory)() as s:
        await s.execute(text("""UPDATE ai_budget_reservations SET actual_tokens = actual_tokens + :k, actual_cost = actual_cost + :c,
                                expires_at = :e WHERE id = :id AND status = 'RESERVED'"""),
                        {"k": tokens, "c": Decimal(str(cost)), "e": _now() + timedelta(seconds=lease_s), "id": rid})
        await s.commit()


async def heartbeat(rid: str, lease_s: int = LEASE_SECONDS, factory=None) -> bool:
    """Renew the lease independently of model calls (a slow live call must not look like a crash). Only the worker that
    owns the reservation may renew it; False = it no longer does (recovery settled it, or another worker holds it)."""
    async with _factory(factory)() as s:
        n = (await s.execute(text("""UPDATE ai_budget_reservations SET expires_at = :e
                                     WHERE id = :id AND status = 'RESERVED' AND worker_id = :w"""),
                            {"e": _now() + timedelta(seconds=lease_s), "id": rid, "w": worker_id()})).rowcount
        await s.commit()
    return bool(n)


async def extend(rid: str, agent_id, user_id, caps: dict, extra_cost: Decimal, extra_tokens: int, factory=None) -> bool:
    """Ask for more than was reserved (the run turned out to need it). False = a cap would be passed; nothing is held."""
    extra_cost = Decimal(str(extra_cost)).quantize(Decimal("0.000001"))
    async with _factory(factory)() as s:
        row = (await s.execute(text("SELECT day, status FROM ai_budget_reservations WHERE id=:id FOR UPDATE"), {"id": rid})).first()
        if not row or row[1] != "RESERVED":
            return False
        if await _take(s, _scopes(agent_id, user_id, caps), row[0], extra_cost, extra_tokens):
            await s.rollback()
            return False
        await s.execute(text("UPDATE ai_budget_reservations SET reserved_cost = reserved_cost + :c, reserved_tokens = reserved_tokens + :k WHERE id=:id"),
                        {"c": extra_cost, "k": extra_tokens, "id": rid})
        await s.commit()
    return True


async def settle(rid: str, status: str = "SETTLED", note: Optional[str] = None, factory=None) -> bool:
    """Turn the hold into measured spend (status SETTLED, or RELEASED when nothing was used, or EXPIRED by recovery).
    Returns False if it was already settled (idempotent: counters move exactly once)."""
    async with _factory(factory)() as s:
        r = (await s.execute(text("""SELECT agent_id, user_id, day, reserved_cost, reserved_tokens, actual_cost, actual_tokens, status
                                     FROM ai_budget_reservations WHERE id=:id FOR UPDATE"""), {"id": rid})).first()
        if not r or r[7] != "RESERVED":
            await s.rollback()
            return False
        agent_id, user_id, day, rc, rt, ac, at, _ = r
        over = max(Decimal(ac) - Decimal(rc), Decimal(0))      # measured spend beyond the hold (provider ignored max tokens)
        if over:                                              # the counter never passes the cap: charge the hold, log the rest
            ac = rc
            note = f"{note or ''} OVERAGE {over} not charged (exceeded the reserved worst case)".strip()
            import logging
            logging.getLogger(__name__).warning("AI budget overage %s on reservation %s", over, rid)
        for t, i in [("COMPANY", "all")] + ([("USER", user_id)] if user_id else []) + [("AGENT", agent_id)]:
            await s.execute(text("""UPDATE ai_budget_counters SET reserved_cost = reserved_cost - :rc, reserved_tokens = reserved_tokens - :rt,
                                    spent_cost = spent_cost + :ac, spent_tokens = spent_tokens + :at
                                    WHERE scope_type=:t AND scope_id=:i AND day=:d"""),
                            {"rc": rc, "rt": rt, "ac": ac, "at": at, "t": t, "i": i, "d": day})
        await s.execute(text("UPDATE ai_budget_reservations SET status=:st, settled_at=now(), note=:n WHERE id=:id"),
                        {"st": status if (ac or at or status != "SETTLED") else "RELEASED", "n": (note or "")[:300] or None, "id": rid})
        await s.commit()
    return True


async def recover_stuck(now: Optional[datetime] = None, factory=None) -> list[dict]:
    """Settle every RESERVED row whose lease has expired (worker crashed). Charges measured usage only; returns
    [{"reservation": id, "job_id": id|None, "actual_cost": Decimal}] so the caller can requeue/dead-letter the jobs."""
    now = now or _now()
    async with _factory(factory)() as s:
        rows = (await s.execute(text("SELECT id, job_id, actual_cost FROM ai_budget_reservations WHERE status='RESERVED' AND expires_at < :n"),
                                {"n": now})).all()
    out = []
    for rid, jid, ac in rows:
        if await settle(str(rid), "EXPIRED", "lease expired (worker presumed crashed); measured usage charged", factory):
            out.append({"reservation": str(rid), "job_id": str(jid) if jid else None, "actual_cost": Decimal(ac)})
    return out


async def usage_today(factory=None) -> list[dict]:
    async with _factory(factory)() as s:
        rows = (await s.execute(text("""SELECT scope_type, scope_id, cap_cost, reserved_cost, spent_cost, reserved_tokens, spent_tokens
                                        FROM ai_budget_counters WHERE day = :d ORDER BY scope_type, scope_id"""), {"d": _now().date()})).all()
    return [{"scope": r[0], "id": r[1], "cap_cost": str(r[2]), "reserved_cost": str(r[3]), "spent_cost": str(r[4]),
             "reserved_tokens": r[5], "spent_tokens": r[6]} for r in rows]
