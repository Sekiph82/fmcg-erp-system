"""Personal access tokens (M45.S01.T012 add-ins, T022 MCP) and the shared approval queue for AI-proposed writes.

A token acts as its user (same roles and data scope) and is narrowed by its scopes. Rate limit per token per minute
(in-process window). Every token use for a write and every decision is written to the audit log.
"""
from __future__ import annotations

import hashlib
import secrets
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_db
from app.models.ai_hub import AIActionRequest, PersonalAccessToken

SCOPES = {"crm.addin": "Outlook/Gmail add-in: look up contacts, log e-mails, notes and tasks",
          "mcp.read": "AI client: read customers, orders, stock and invoices you may see",
          "mcp.write": "AI client: propose changes; a person approves each one"}
_hits: dict = defaultdict(deque)   # ponytail: per-process rate window; use Redis when running several workers


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def now() -> datetime:
    return datetime.now(timezone.utc)


async def create(db: AsyncSession, user_id, name: str, scopes: list[str], days: int) -> tuple[PersonalAccessToken, str]:
    if not scopes or set(scopes) - set(SCOPES):
        raise ValueError("Unknown scope.")
    token = "pat_" + secrets.token_urlsafe(32)
    t = PersonalAccessToken(user_id=user_id, name=name, token_hash=digest(token), prefix=token[:10], scopes=sorted(set(scopes)),
                            expires_at=now() + timedelta(days=days))
    db.add(t)
    await db.flush()
    return t, token


def out(t: PersonalAccessToken) -> dict:
    return {"id": str(t.id), "name": t.name, "prefix": t.prefix, "scopes": t.scopes, "expires_at": t.expires_at.isoformat(),
            "revoked": t.revoked_at is not None, "last_used_at": t.last_used_at.isoformat() if t.last_used_at else None}


def _rate(t: PersonalAccessToken) -> None:
    q, cut = _hits[t.id], time.monotonic() - 60
    while q and q[0] < cut:
        q.popleft()
    if len(q) >= t.rate_limit_per_min:
        raise HTTPException(429, "Rate limit reached for this token; try again in a minute.", headers={"Retry-After": "60"})
    q.append(time.monotonic())


async def authenticate(db: AsyncSession, authorization: str, scope: str):
    """→ (user with roles loaded, token). 401 for a bad/revoked/expired token, 403 when the scope is missing."""
    from app.models.role import Role
    from app.models.user import User
    raw = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
    t = (await db.execute(select(PersonalAccessToken).where(PersonalAccessToken.token_hash == digest(raw)))).scalar_one_or_none() if raw else None
    if t is None or t.revoked_at is not None or t.expires_at <= now():
        raise HTTPException(401, "Invalid, revoked or expired token.", headers={"WWW-Authenticate": "Bearer"})
    if scope not in t.scopes:
        raise HTTPException(403, f"This token does not have the {scope} scope.")
    user = (await db.execute(select(User).options(selectinload(User.roles).selectinload(Role.permissions))
                             .options(selectinload(User.roles).selectinload(Role.access_scopes))
                             .options(selectinload(User.access_scopes)).where(User.id == t.user_id))).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(401, "The token's user is disabled.", headers={"WWW-Authenticate": "Bearer"})
    _rate(t)
    t.last_used_at = now()
    return user, t


def require_token(scope: str):
    async def dep(authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
        return await authenticate(db, authorization, scope)
    return dep


def audit(db: AsyncSession, user, event: str, target_type: str, target_id: Optional[str], details: dict) -> None:
    from app.models.audit_log import AuditLog
    db.add(AuditLog(actor_id=getattr(user, "id", None), actor_email=getattr(user, "email", None),
                    actor_name=getattr(user, "full_name", None), event_type=event, module="ai",
                    target_type=target_type, target_id=target_id, details=details))


# ── approval queue ───────────────────────────────────────────────────────────

ACTIONS = {"create_task": "Create a follow-up task on a CRM record (or the customer's newest deal)",
           "send_email": "Queue an e-mail through the CRM outbox (suppression and consent rules apply)"}


async def propose(db: AsyncSession, *, source: str, source_ref: Optional[str], user, action: str, arguments: dict,
                  summary: str) -> AIActionRequest:
    if action not in ACTIONS:
        raise ValueError(f"Unknown action {action}.")
    r = AIActionRequest(source=source, source_ref=source_ref, requested_by=getattr(user, "id", None), action=action,
                        arguments=arguments, summary=summary[:500])
    db.add(r)
    await db.flush()
    audit(db, user, "AI_ACTION_PROPOSED", "ai_action_request", str(r.id), {"source": source, "action": action})
    return r


async def decide(db: AsyncSession, req: AIActionRequest, approver, approve: bool) -> AIActionRequest:
    if req.status != "PENDING":
        raise ValueError("Already decided.")
    if req.requested_by and approver.id == req.requested_by:
        raise PermissionError("Someone other than the requester must approve.")
    req.decided_by, req.decided_at = approver.username, now()
    if not approve:
        req.status = "REJECTED"
    else:
        try:
            req.result = await _execute(db, req, approver)
            req.status = "DONE"
        except ValueError as e:
            req.status, req.result = "FAILED", {"error": str(e)}
    audit(db, approver, "AI_ACTION_" + req.status, "ai_action_request", str(req.id), {"action": req.action})
    return req


async def _execute(db: AsyncSession, req: AIActionRequest, approver) -> dict:
    if req.action == "create_task":
        from app.models.crm import CRMActivity, CRMRecord
        if req.arguments.get("crm_record_id"):
            rec = await db.get(CRMRecord, uuid.UUID(str(req.arguments["crm_record_id"])))
        else:   # agents work per customer: use the customer's newest deal
            rec = (await db.execute(select(CRMRecord).where(CRMRecord.assigned_customer_id == uuid.UUID(str(req.arguments.get("customer_id"))))
                                    .order_by(CRMRecord.created_at.desc()))).scalars().first()
        if rec is None:
            raise ValueError("CRM record not found.")
        a = CRMActivity(crm_record_id=rec.id, **_activity_fields(req.arguments, approver))
        db.add(a)
        await db.flush()
        return {"activity_id": str(a.id)}
    if req.action == "send_email":
        from app.services import crm_outbound_service as outbound
        a = req.arguments
        if not a.get("to_email"):
            raise ValueError("No e-mail address.")
        m = await outbound.queue(db, to_email=str(a["to_email"]), subject=str(a.get("subject") or "")[:300],
                                 body=str(a.get("body") or ""), purpose="MANUAL", dedupe_key=f"ai:{req.id}",
                                 customer_id=uuid.UUID(str(a["customer_id"])) if a.get("customer_id") else None,
                                 created_by=f"ai:{approver.username}"[:100])
        return {"outbound_id": str(m.id), "status": m.status}
    raise ValueError("Unsupported action.")


def _activity_fields(args: dict, approver) -> dict:
    from app.models.crm import CRMActivityType
    due = args.get("due_date")
    return {"activity_type": CRMActivityType.TASK, "subject": str(args.get("subject") or "Follow up")[:300],
            "notes": str(args.get("note") or "")[:2000], "created_by": approver.username[:50],
            "due_datetime": datetime.fromisoformat(due) if due else None,
            "assigned_to": str(args["assigned_to"])[:50] if args.get("assigned_to") else None}
