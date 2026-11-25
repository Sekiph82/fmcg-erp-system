"""Contacts (M43.S01.T015). Prefix /api/v1/crm-contacts.

Company-wide CRM viewers see every contact; other CRM users see contacts they own or that are linked to CRM
records assigned to them. Writes need CRM edit rights; moving a lifecycle stage backwards needs a reason.
"""
from __future__ import annotations

import uuid
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission, require_any_permission
from app.core.deps import get_current_user, get_db
from app.models.crm import CRMContact, CRMContactAssociation, CRMLifecycleHistory, CRMRecord
from app.services import crm_contact_service as cs

VIEW = ("crm.view", "crm.view_all", "crm.view_own_scope", "crm.view_own_region")
EDIT = ("crm.edit", "crm.edit_all", "crm.edit_own_scope", "crm.edit_own_region")
router = APIRouter(dependencies=[Depends(require_any_permission(VIEW))])


def _all(u) -> bool:
    return u.is_superuser or has_any_permission(u, ("crm.view_all", "crm.edit_all"))


def _visible(q, u):
    if _all(u):
        return q
    mine = exists().where(CRMContactAssociation.contact_id == CRMContact.id,
                          CRMContactAssociation.object_type == "crm_record",
                          CRMContactAssociation.object_id == CRMRecord.id,
                          CRMRecord.assigned_rep_id == str(u.id))
    return q.where(or_(CRMContact.owner_user_id == u.id, mine))


async def _get(db, contact_id, u) -> CRMContact:
    c = (await db.execute(_visible(select(CRMContact).where(CRMContact.id == contact_id), u))).scalar_one_or_none()
    if c is None:
        raise HTTPException(404, "Contact not found")
    return c


def _out(c: CRMContact, user=None, pol=None) -> dict:
    out = {"id": str(c.id), "full_name": c.full_name, "email": c.email, "phone": c.phone, "job_title": c.job_title,
            "lifecycle_stage": c.lifecycle_stage, "language": c.language, "owner_user_id": str(c.owner_user_id) if c.owner_user_id else None,
            "company_id": str(c.company_id) if c.company_id else None, "source": c.source, "notes": c.notes}
    if user is not None and pol is not None:   # M45.S01.T017 sensitive fields
        from app.services import sensitive_service as sens
        sens.apply(out, "contact", pol, user)
    return out


class ContactIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    job_title: Optional[str] = Field(None, max_length=150)
    company_id: Optional[uuid.UUID] = None
    notes: Optional[str] = Field(None, max_length=5000)
    language: Optional[str] = Field(None, pattern=r"^[a-z]{2}(-[A-Z]{2})?$")


@router.get("")
async def list_contacts(q: Optional[str] = Query(None, max_length=100), lifecycle: Optional[str] = None,
                        limit: int = Query(100, ge=1, le=500), db: AsyncSession = Depends(get_db),
                        current_user=Depends(get_current_user)):
    stmt = _visible(select(CRMContact), current_user)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(or_(CRMContact.full_name.ilike(like), CRMContact.email.ilike(like), CRMContact.phone.ilike(like)))
    if lifecycle:
        stmt = stmt.where(CRMContact.lifecycle_stage == lifecycle)
    from app.services import sensitive_service as sens
    pol = await sens.policy(db)
    return [_out(c, current_user, pol) for c in (await db.execute(stmt.order_by(CRMContact.full_name).limit(limit))).scalars()]


@router.post("", status_code=201, dependencies=[Depends(require_any_permission(EDIT))])
async def create_contact(body: ContactIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    if body.email and (dup := await cs.find_by_email(db, str(body.email))) is not None:
        raise HTTPException(409, {"message": "A contact with this e-mail exists.", "existing_id": str(dup.id)})
    c = CRMContact(full_name=body.full_name.strip(), email=cs.norm_email(str(body.email) if body.email else None),
                   phone=body.phone, job_title=body.job_title, company_id=body.company_id, notes=body.notes, language=body.language,
                   owner_user_id=current_user.id, source="manual")
    db.add(c)
    await db.flush()
    await cs.set_lifecycle(db, c, "LEAD", "manual:create", current_user.id)
    await db.commit()
    return _out(c)


@router.get("/{contact_id}")
async def get_contact(contact_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    c = await _get(db, contact_id, current_user)
    assoc = (await db.execute(select(CRMContactAssociation).where(CRMContactAssociation.contact_id == c.id)
                              .order_by(CRMContactAssociation.object_type))).scalars().all()
    hist = (await db.execute(select(CRMLifecycleHistory).where(CRMLifecycleHistory.contact_id == c.id)
                             .order_by(CRMLifecycleHistory.changed_at.desc()))).scalars().all()
    from app.services import sensitive_service as sens
    return {**_out(c, current_user, await sens.policy(db)),
            "associations": [{"id": str(a.id), "object_type": a.object_type, "object_id": str(a.object_id), "label": a.label}
                             for a in assoc],
            "lifecycle_history": [{"from": h.from_stage, "to": h.to_stage, "source": h.source, "reason": h.reason,
                                   "changed_at": h.changed_at.isoformat()} for h in hist]}


@router.put("/{contact_id}", dependencies=[Depends(require_any_permission(EDIT))])
async def update_contact(contact_id: uuid.UUID, body: ContactIn, db: AsyncSession = Depends(get_db),
                         current_user=Depends(get_current_user)):
    c = await _get(db, contact_id, current_user)
    if body.phone and body.phone.startswith("•••"):   # M45.S01.T017 masked value: keep the stored one
        body.phone = c.phone
    email = cs.norm_email(str(body.email) if body.email else None)
    if email and email != c.email and (dup := await cs.find_by_email(db, email)) is not None:
        raise HTTPException(409, {"message": "Another contact has this e-mail; merge them instead.", "existing_id": str(dup.id)})
    c.full_name, c.email, c.phone, c.job_title, c.company_id, c.notes, c.language = (
        body.full_name.strip(), email, body.phone, body.job_title, body.company_id, body.notes, body.language)
    await db.commit()
    return _out(c)


class AssocIn(BaseModel):
    object_type: Literal["customer", "crm_record", "ticket", "quotation", "sales_order"]
    object_id: uuid.UUID
    label: str = Field("primary", max_length=20)


@router.post("/{contact_id}/associations", status_code=201, dependencies=[Depends(require_any_permission(EDIT))])
async def add_association(contact_id: uuid.UUID, body: AssocIn, db: AsyncSession = Depends(get_db),
                          current_user=Depends(get_current_user)):
    c = await _get(db, contact_id, current_user)
    if body.object_type == "crm_record":
        from app.api.v1.endpoints.crm_pipeline import _scoped_record
        await _scoped_record(db, body.object_id, current_user, "edit")
    else:   # review M43 #14: other objects need company-wide CRM rights and must exist
        if not _all(current_user):
            raise HTTPException(403, "Company-wide CRM rights are needed to link this record.")
        from sqlalchemy import text as _text
        table = {"customer": "customers", "ticket": "helpdesk_tickets", "quotation": "quotations",
                 "sales_order": "sales_orders"}[body.object_type]
        if (await db.execute(_text(f"SELECT 1 FROM {table} WHERE id = :i"), {"i": body.object_id})).first() is None:
            raise HTTPException(404, f"{body.object_type} not found")
    try:
        a = await cs.associate(db, c.id, body.object_type, body.object_id, body.label)
    except cs.ContactError as e:
        raise HTTPException(e.status_code, str(e)) from None
    await db.commit()
    return {"id": str(a.id), "object_type": a.object_type, "object_id": str(a.object_id), "label": a.label}


@router.delete("/{contact_id}/associations/{association_id}", status_code=204,
               dependencies=[Depends(require_any_permission(EDIT))])
async def remove_association(contact_id: uuid.UUID, association_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                             current_user=Depends(get_current_user)):
    c = await _get(db, contact_id, current_user)
    a = await db.get(CRMContactAssociation, association_id)
    if a is None or a.contact_id != c.id:
        raise HTTPException(404, "Association not found")
    await db.delete(a)
    await db.commit()


class LifecycleIn(BaseModel):
    stage: Literal["SUBSCRIBER", "LEAD", "MQL", "SQL", "OPPORTUNITY", "CUSTOMER", "EVANGELIST", "OTHER"]
    reason: Optional[str] = Field(None, max_length=300)


@router.put("/{contact_id}/lifecycle", dependencies=[Depends(require_any_permission(EDIT))])
async def set_lifecycle(contact_id: uuid.UUID, body: LifecycleIn, db: AsyncSession = Depends(get_db),
                        current_user=Depends(get_current_user)):
    c = await _get(db, contact_id, current_user)
    try:
        await cs.set_lifecycle(db, c, body.stage, "manual", current_user.id, allow_backward=True, reason=body.reason)
    except cs.ContactError as e:
        raise HTTPException(e.status_code, str(e)) from None
    await db.commit()
    return _out(c)


@router.get("/by-object/{object_type}/{object_id}")
async def contacts_of(object_type: str, object_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                      current_user=Depends(get_current_user)):
    if object_type == "crm_record":
        from app.api.v1.endpoints.crm_pipeline import _scoped_record
        await _scoped_record(db, object_id, current_user, "view")
    elif not _all(current_user):
        raise HTTPException(403, "Company-wide CRM view needed.")
    from app.services import sensitive_service as sens
    pol = await sens.policy(db)
    return [{**_out(c, current_user, pol), "label": label} for c, label in await cs.contacts_for(db, object_type, object_id)]
