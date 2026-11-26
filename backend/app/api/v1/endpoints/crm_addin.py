"""Shared API for the Outlook and Gmail CRM add-ins (M45.S01.T012). Prefix /api/v1/public/crm-addin.

Auth: Authorization: Bearer <personal access token with the crm.addin scope> (created by the user in the ERP).
The add-in runs as that user: contact visibility and edit rights are the same as in the CRM screens.
- GET  /lookup?email=        contact, linked deals and recent activities for the open e-mail's sender
- POST /log-email            store the open e-mail (subject + first 2000 characters) as an EMAIL activity on a deal
- POST /note | /task         note or follow-up task on a deal
- GET  /templates            active e-mail templates to insert into a reply
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission
from app.core.deps import get_db
from app.models.crm import CRMActivity, CRMActivityType, CRMContact, CRMContactAssociation, CRMRecord
from app.services import crm_contact_service as cs
from app.services import pat_service as pats

router = APIRouter()
auth = pats.require_token("crm.addin")
EDIT = ("crm.edit", "crm.edit_all", "crm.edit_own_scope", "crm.edit_own_region")


async def _contact(db, user, email: str) -> Optional[CRMContact]:
    from app.api.v1.endpoints.crm_contacts import _visible
    e = cs.norm_email(email)
    return (await db.execute(_visible(select(CRMContact).where(CRMContact.email == e), user))).scalar_one_or_none()


async def _record(db, user, rid: uuid.UUID) -> CRMRecord:
    rec = await db.get(CRMRecord, rid)
    all_ = user.is_superuser or has_any_permission(user, ("crm.view_all", "crm.edit_all"))
    if rec is None or not (all_ or rec.assigned_rep_id == str(user.id)):
        raise HTTPException(404, "Deal not found")
    return rec


@router.get("/lookup")
async def lookup(email: str = Query(..., min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+$"), db: AsyncSession = Depends(get_db), ctx=Depends(auth)):
    user, _ = ctx
    c = await _contact(db, user, str(email))
    if c is None:
        return {"found": False, "email": str(email)}
    rec_ids = list((await db.execute(select(CRMContactAssociation.object_id).where(
        CRMContactAssociation.contact_id == c.id, CRMContactAssociation.object_type == "crm_record"))).scalars())
    all_ = user.is_superuser or has_any_permission(user, ("crm.view_all", "crm.edit_all"))
    recs = [r for r in (await db.execute(select(CRMRecord).where(CRMRecord.id.in_(rec_ids or [uuid.uuid4()])))).scalars()
            if all_ or r.assigned_rep_id == str(user.id)]
    rec_ids = [r.id for r in recs]
    acts = list((await db.execute(select(CRMActivity).where(CRMActivity.crm_record_id.in_(rec_ids or [uuid.uuid4()]))
                                  .order_by(CRMActivity.activity_datetime.desc().nullslast()).limit(5))).scalars())
    await db.commit()
    return {"found": True, "contact": {"id": str(c.id), "name": c.full_name, "job_title": c.job_title, "phone": c.phone,
                                       "lifecycle_stage": c.lifecycle_stage},
            "deals": [{"id": str(r.id), "company": r.company_name, "status": getattr(r.status, "value", r.status),
                       "link": f"/dashboard/crm/records/{r.id}"} for r in recs],
            "recent": [{"type": a.activity_type.value, "subject": a.subject,
                        "at": a.activity_datetime.isoformat() if a.activity_datetime else None} for a in acts]}


class LogIn(BaseModel):
    crm_record_id: uuid.UUID
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field("", max_length=20000)
    direction: Literal["IN", "OUT"] = "IN"
    message_id: Optional[str] = Field(None, max_length=300)   # without <> (the input sanitizer strips tags)


class NoteIn(BaseModel):
    crm_record_id: uuid.UUID
    text: str = Field(min_length=1, max_length=5000)
    due: Optional[datetime] = None


async def _add(db, user, rec: CRMRecord, kind: CRMActivityType, subject: str, notes: str, due=None,
               outcome: Optional[str] = None) -> dict:
    if not has_any_permission(user, EDIT):
        raise HTTPException(403, "You may not change CRM records.")
    a = CRMActivity(crm_record_id=rec.id, activity_type=kind, subject=subject[:300], notes=notes,
                    activity_datetime=datetime.utcnow(), due_datetime=due.replace(tzinfo=None) if due else None,
                    created_by=user.username[:50], assigned_to=str(user.id), outcome_code=outcome)
    db.add(a)
    pats.audit(db, user, "CRM_ADDIN_" + kind.value, "crm_record", str(rec.id), {"subject": subject[:100]})
    await db.commit()
    return {"activity_id": str(a.id)}


@router.post("/log-email", status_code=201)
async def log_email(body: LogIn, db: AsyncSession = Depends(get_db), ctx=Depends(auth)):
    user, _ = ctx
    rec = await _record(db, user, body.crm_record_id)
    if body.message_id and (await db.execute(select(CRMActivity.id).where(
            CRMActivity.crm_record_id == rec.id, CRMActivity.outcome_code == f"msg:{body.message_id}"[:100]))).first():
        return {"duplicate": True}
    return await _add(db, user, rec, CRMActivityType.EMAIL, ("Received: " if body.direction == "IN" else "Sent: ") + body.subject,
                      body.body[:2000], outcome=f"msg:{body.message_id}"[:100] if body.message_id else None)


@router.post("/note", status_code=201)
async def note(body: NoteIn, db: AsyncSession = Depends(get_db), ctx=Depends(auth)):
    user, _ = ctx
    return await _add(db, user, await _record(db, user, body.crm_record_id), CRMActivityType.NOTE, body.text[:80], body.text)


@router.post("/task", status_code=201)
async def task(body: NoteIn, db: AsyncSession = Depends(get_db), ctx=Depends(auth)):
    user, _ = ctx
    return await _add(db, user, await _record(db, user, body.crm_record_id), CRMActivityType.TASK, body.text[:80],
                      body.text, body.due)


@router.get("/templates")
async def templates(db: AsyncSession = Depends(get_db), ctx=Depends(auth)):
    from app.models.email_integration import EmailTemplate
    await db.commit()
    return [{"id": str(t.id), "name": t.name, "subject": t.subject_template, "body": t.body_template}
            for t in (await db.execute(select(EmailTemplate).where(EmailTemplate.is_active.is_(True))
                                       .order_by(EmailTemplate.name).limit(100))).scalars()]
