"""Standalone contacts, labelled associations and lifecycle stage (M43.S01.T015).

A contact is a person. It links many-to-many to customers (companies), CRM records (leads/deals), helpdesk tickets,
quotations and sales orders through labelled associations (e.g. billing contact, decision maker). Consent and
suppression stay per e-mail address in crm_contact_consents, so they follow the person everywhere.

Lifecycle: SUBSCRIBER < LEAD < MQL < SQL < OPPORTUNITY < CUSTOMER < EVANGELIST (+ OTHER). Automatic updates only move
forward (record created → LEAD, qualified → SQL, converted → OPPORTUNITY, won → CUSTOMER) and every change is
written to the history with its source; a person may move a contact backwards manually with a reason.
Duplicates: one contact per normalised e-mail (partial unique index); creating a second one returns the existing id.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm import CRMContact, CRMContactAssociation, CRMLifecycleHistory, CRMRecord, CRMRecordType, CRMStatus

STAGES = ("SUBSCRIBER", "LEAD", "MQL", "SQL", "OPPORTUNITY", "CUSTOMER", "EVANGELIST", "OTHER")
ORDER = {s: i for i, s in enumerate(STAGES[:-1])}
OBJECT_TYPES = ("customer", "crm_record", "ticket", "quotation", "sales_order")
LABELS = ("primary", "billing", "decision_maker", "buyer", "influencer", "champion", "user", "blocker", "finance",
          "technical", "other")


class ContactError(Exception):
    def __init__(self, message: str, status_code: int = 422, existing_id: Optional[UUID] = None):
        super().__init__(message)
        self.status_code, self.existing_id = status_code, existing_id


def norm_email(email: Optional[str]) -> Optional[str]:
    e = (email or "").strip().lower()
    return e or None


async def find_by_email(db: AsyncSession, email: Optional[str]) -> Optional[CRMContact]:
    e = norm_email(email)
    if not e:
        return None
    return (await db.execute(select(CRMContact).where(func.lower(CRMContact.email) == e))).scalar_one_or_none()


async def set_lifecycle(db: AsyncSession, c: CRMContact, stage: str, source: str, actor_id=None,
                        allow_backward: bool = False, reason: Optional[str] = None) -> bool:
    if stage not in STAGES:
        raise ContactError(f"Unknown lifecycle stage {stage}")
    cur = c.lifecycle_stage
    if cur == stage:
        return False
    if not allow_backward and cur in ORDER and stage in ORDER and ORDER[stage] < ORDER[cur]:
        return False                                    # automatic updates never move a contact back
    if allow_backward and cur in ORDER and stage in ORDER and ORDER[stage] < ORDER[cur] and not reason:
        raise ContactError("Moving a contact back needs a reason.")
    c.lifecycle_stage, c.lifecycle_changed_at = stage, datetime.now(timezone.utc)
    db.add(CRMLifecycleHistory(contact_id=c.id, from_stage=cur, to_stage=stage, source=source[:60],
                               reason=(reason or None) and reason[:300], changed_by_id=actor_id,
                               changed_at=c.lifecycle_changed_at))
    return True


async def associate(db: AsyncSession, contact_id: UUID, object_type: str, object_id: UUID, label: str = "primary") -> CRMContactAssociation:
    if object_type not in OBJECT_TYPES:
        raise ContactError(f"Cannot associate with {object_type}")
    if label not in LABELS:
        raise ContactError(f"Unknown association label {label}")
    a = (await db.execute(select(CRMContactAssociation).where(
        CRMContactAssociation.contact_id == contact_id, CRMContactAssociation.object_type == object_type,
        CRMContactAssociation.object_id == object_id, CRMContactAssociation.label == label))).scalar_one_or_none()
    if a is None:
        a = CRMContactAssociation(contact_id=contact_id, object_type=object_type, object_id=object_id, label=label,
                                  created_at=datetime.now(timezone.utc))
        db.add(a)
        await db.flush()
    return a


def _stage_for(rec: CRMRecord) -> str:
    status = getattr(rec.status, "value", rec.status)
    rtype = getattr(rec.record_type, "value", rec.record_type)
    if status == CRMStatus.WON.value:
        return "CUSTOMER"
    if rtype == CRMRecordType.OPPORTUNITY.value:
        return "OPPORTUNITY"
    return "SQL" if rec.qualified_flag else "LEAD"


async def sync_record(db: AsyncSession, rec: CRMRecord, source: str) -> Optional[CRMContact]:
    """Keep the record's primary contact in step with the CRM record (called on create / qualify / convert / win)."""
    if not (rec.contact_email or rec.contact_person_name):
        return None
    c = await find_by_email(db, rec.contact_email)
    if c is None:
        linked = (await db.execute(select(CRMContact).join(
            CRMContactAssociation, CRMContactAssociation.contact_id == CRMContact.id).where(
            CRMContactAssociation.object_type == "crm_record", CRMContactAssociation.object_id == rec.id,
            CRMContactAssociation.label == "primary"))).scalars().first()
        c = linked
    if c is None:
        c = CRMContact(full_name=(rec.contact_person_name or rec.contact_email or "Contact")[:200],
                       email=norm_email(rec.contact_email), phone=rec.contact_phone, company_id=rec.company_id,
                       lifecycle_stage=None, source=f"crm:{source}"[:60])
        db.add(c)
        await db.flush()
    await associate(db, c.id, "crm_record", rec.id, "primary")
    if rec.assigned_customer_id:
        await associate(db, c.id, "customer", rec.assigned_customer_id, "primary")
    await set_lifecycle(db, c, _stage_for(rec), f"crm:{source}")
    return c


async def contacts_for(db: AsyncSession, object_type: str, object_id: UUID) -> list[tuple[CRMContact, str]]:
    rows = (await db.execute(select(CRMContact, CRMContactAssociation.label).join(
        CRMContactAssociation, CRMContactAssociation.contact_id == CRMContact.id).where(
        CRMContactAssociation.object_type == object_type, CRMContactAssociation.object_id == object_id)
        .order_by(CRMContact.full_name))).all()
    return [(c, label) for c, label in rows]
