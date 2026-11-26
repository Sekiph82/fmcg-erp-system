"""Shared guard for direct marketing sends (M48.S01.T023, M36 audit F4): ABM group campaigns and single sends of an
e-mail design.

- Approval: when MARKETING_EMAIL_APPROVAL_REQUIRED is on (as for segment campaigns in crm_pipeline), a send needs an
  APPROVED request for exactly this payload, decided by a second editor; the approval is used once.
- Cap: every editor may queue at most MARKETING_DIRECT_SEND_DAILY_CAP such messages per rolling 24 hours.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.m48_crm_send_approval import CRMSendApproval

KINDS = ("ABM_GROUP", "DESIGN_SEND")


class GuardError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status, self.detail = status, detail


def approval_required() -> bool:
    return bool(getattr(settings, "MARKETING_EMAIL_APPROVAL_REQUIRED", False))


def daily_cap() -> int:
    return int(getattr(settings, "MARKETING_DIRECT_SEND_DAILY_CAP", 200))


def content_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def _audit(db: AsyncSession, user, event: str, row: CRMSendApproval) -> None:
    from app.models.audit_log import AuditLog
    db.add(AuditLog(actor_id=getattr(user, "id", None), actor_email=getattr(user, "email", None),
                    actor_name=getattr(user, "full_name", None), event_type=event, module="crm",
                    target_type="crm_send_approval", target_id=str(row.id),
                    details={"kind": row.kind, "target_id": str(row.target_id), "status": row.status}))


def out(row: CRMSendApproval) -> dict:
    return {"id": str(row.id), "kind": row.kind, "target_id": str(row.target_id),
            "company_id": str(row.company_id) if row.company_id else None, "payload": row.payload,
            "content_hash": row.content_hash, "status": row.status, "requested_by": row.requested_by, "decided_by": row.decided_by,
            "created_at": row.created_at.isoformat(), "decided_at": row.decided_at.isoformat() if row.decided_at else None}


async def request(db: AsyncSession, kind: str, target_id: uuid.UUID, payload: dict, user,
                  company_id: Optional[uuid.UUID] = None) -> CRMSendApproval:
    row = CRMSendApproval(kind=kind, target_id=target_id, company_id=company_id, payload=payload,
                          content_hash=content_hash(payload), status="PENDING", requested_by=user.username,
                          created_at=datetime.now(timezone.utc))
    db.add(row)
    await db.flush()
    _audit(db, user, "CRM_SEND_APPROVAL_REQUESTED", row)
    return row


async def decide(db: AsyncSession, approval_id: uuid.UUID, kind: str, user, approve: bool) -> CRMSendApproval:
    row = (await db.execute(select(CRMSendApproval).where(CRMSendApproval.id == approval_id)
                            .with_for_update())).scalar_one_or_none()
    if row is None or row.kind != kind:
        raise GuardError(404, "Approval request not found")
    if row.status != "PENDING":
        raise GuardError(409, "Nothing waiting for approval.")
    if row.requested_by == user.username:
        raise GuardError(403, "A second editor must approve.")
    row.status = "APPROVED" if approve else "REJECTED"
    row.decided_by, row.decided_at = user.username, datetime.now(timezone.utc)
    _audit(db, user, "CRM_SEND_APPROVAL_" + row.status, row)
    await db.flush()
    return row


async def consume(db: AsyncSession, kind: str, target_id: uuid.UUID, payload: dict,
                  approval_id: Optional[uuid.UUID], user) -> None:
    """No-op when approval is not required; else the matching APPROVED request is marked USED (in the caller's
    transaction, so a failed send rolls the use back)."""
    if not approval_required():
        return
    if approval_id is None:
        raise GuardError(409, "This send needs approval by a second editor first (request an approval).")
    row = (await db.execute(select(CRMSendApproval).where(CRMSendApproval.id == approval_id)
                            .with_for_update())).scalar_one_or_none()
    if (row is None or row.kind != kind or row.target_id != target_id or row.status != "APPROVED"
            or row.content_hash != content_hash(payload)):
        raise GuardError(409, "No approved request matches this exact send (content changed, already used or not approved).")
    row.status, row.used_at = "USED", datetime.now(timezone.utc)
    _audit(db, user, "CRM_SEND_APPROVAL_USED", row)
    await db.flush()


async def used_today(db: AsyncSession, username: str) -> int:
    """The editor's ABM + design single-send messages of the last 24 hours."""
    from app.models.crm import CRMOutboundMessage
    return (await db.execute(select(func.count()).select_from(CRMOutboundMessage).where(
        CRMOutboundMessage.created_by.in_([username, f"abm:{username}"[:100]]),
        or_(CRMOutboundMessage.dedupe_key.like("abm:%"), CRMOutboundMessage.dedupe_key.like("single:%")),
        CRMOutboundMessage.created_at >= datetime.now(timezone.utc) - timedelta(days=1)))).scalar_one()


async def policy(db: AsyncSession, username: str) -> dict:
    """What the UI shows before a send: whether approval is needed and how much of the daily cap is left."""
    return {"approval_required": approval_required(), "daily_cap": daily_cap(), "used_today": await used_today(db, username)}


async def check_cap(db: AsyncSession, username: str, planned: int) -> None:
    """Refuse when the editor's ABM + design single sends of the last 24 hours plus `planned` exceed the cap."""
    used = await used_today(db, username)
    if used + planned > daily_cap():
        raise GuardError(429, f"Daily limit for direct marketing sends reached ({used} of {daily_cap()} used; "
                              f"this send needs {planned}).")
