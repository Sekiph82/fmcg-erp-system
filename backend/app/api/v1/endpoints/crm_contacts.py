"""Contacts (M43.S01.T015). Prefix /api/v1/crm-contacts.

Company-wide CRM viewers see every contact; other CRM users see contacts they own or that are linked to CRM
records assigned to them. Writes need CRM edit rights; moving a lifecycle stage backwards needs a reason.
"""
from __future__ import annotations

import uuid
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import and_, exists, or_, select
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


def _edit_all(u) -> bool:
    """M48.S01.T023 (audit F5): only these rights write to every contact; a company-wide *view* right does not."""
    return u.is_superuser or has_any_permission(u, ("crm.edit_all", "crm.edit"))


async def _get_edit(db, contact_id, u) -> CRMContact:
    """A contact the caller may change: visible, and either edit-all rights, owned by the caller, or linked to a CRM
    record the caller may edit (the same edit scope as the pipeline)."""
    from app.core.access_control import can_modify_record
    c = await _get(db, contact_id, u)
    if _edit_all(u) or c.owner_user_id == u.id:
        return c
    recs = (await db.execute(select(CRMRecord).join(CRMContactAssociation, and_(
        CRMContactAssociation.object_id == CRMRecord.id, CRMContactAssociation.object_type == "crm_record"))
        .where(CRMContactAssociation.contact_id == c.id))).scalars().all()
    if not any(can_modify_record(u, "crm", "edit", r) for r in recs):
        raise HTTPException(403, "You may view this contact but not change it.")
    return c


def _out(c: CRMContact, user=None, pol=None, rules=None, props=None) -> dict:
    out = {"id": str(c.id), "full_name": c.full_name, "email": c.email, "phone": c.phone, "job_title": c.job_title,
            "lifecycle_stage": c.lifecycle_stage, "language": c.language, "owner_user_id": str(c.owner_user_id) if c.owner_user_id else None,
            "company_id": str(c.company_id) if c.company_id else None, "source": c.source, "notes": c.notes}
    if user is not None and pol is not None:   # M45.S01.T017 sensitive fields
        from app.services import sensitive_service as sens
        sens.apply(out, "contact", pol, user)
    if props is not None:
        out["properties"] = props
    if rules:                                  # M47.S01.T010 field-level permissions
        from app.services import sensitive_service as sens
        sens.strip_hidden(out, rules)
    return out


async def _props(db, ids) -> dict:
    from app.models.m47_platform import CRMContactProperty
    out: dict = {i: {} for i in ids}
    if ids:
        for p in (await db.execute(select(CRMContactProperty).where(CRMContactProperty.contact_id.in_(ids)))).scalars():
            out[p.contact_id][p.key] = p.value
    return out


async def _rules(db, u) -> dict:
    from app.services import sensitive_service as sens
    return await sens.field_rules(db, "contact", u)


def _guard(rules: dict, new: dict, old: dict) -> None:
    from app.services import sensitive_service as sens
    try:
        sens.check_write(rules, new, old)
    except PermissionError as e:
        raise HTTPException(403, str(e)) from None


def _std(c: CRMContact) -> dict:
    return {"full_name": c.full_name, "email": c.email, "phone": c.phone, "job_title": c.job_title,
            "company_id": c.company_id, "notes": c.notes, "language": c.language, "lifecycle_stage": c.lifecycle_stage}


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
    from app.services import sensitive_service as sens
    stmt = _visible(select(CRMContact), current_user)
    pol, rules = await sens.policy(db), await _rules(db, current_user)
    if q:
        like = f"%{q.lower()}%"
        # M47 review: never search on a field the caller cannot see (hidden or masked), or q becomes an oracle for it
        unseen = {k for k, a in rules.items() if a == "HIDDEN"} | (set() if sens.can_view(current_user) else pol.get("contact", set()))
        cols = [CRMContact.full_name] + [getattr(CRMContact, f) for f in ("email", "phone") if f not in unseen]
        stmt = stmt.where(or_(*(col.ilike(like) for col in cols)))
    if lifecycle:
        stmt = stmt.where(CRMContact.lifecycle_stage == lifecycle)
    rows = list((await db.execute(stmt.order_by(CRMContact.full_name).limit(limit))).scalars())
    props = await _props(db, [c.id for c in rows])
    return [_out(c, current_user, pol, rules, props[c.id]) for c in rows]


@router.post("", status_code=201, dependencies=[Depends(require_any_permission(EDIT))])
async def create_contact(body: ContactIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    if body.email and (dup := await cs.find_by_email(db, str(body.email))) is not None:
        raise HTTPException(409, {"message": "A contact with this e-mail exists.", "existing_id": str(dup.id)})
    rules = await _rules(db, current_user)
    _guard(rules, {k: v for k, v in body.model_dump().items() if v is not None and k != "full_name"}, {})
    c = CRMContact(full_name=body.full_name.strip(), email=cs.norm_email(str(body.email) if body.email else None),
                   phone=body.phone, job_title=body.job_title, company_id=body.company_id, notes=body.notes, language=body.language,
                   owner_user_id=current_user.id, source="manual")
    db.add(c)
    await db.flush()
    await cs.set_lifecycle(db, c, "LEAD", "manual:create", current_user.id)
    await db.commit()
    return _out(c, rules=rules)


@router.get("/{contact_id}")
async def get_contact(contact_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    c = await _get(db, contact_id, current_user)
    assoc = (await db.execute(select(CRMContactAssociation).where(CRMContactAssociation.contact_id == c.id)
                              .order_by(CRMContactAssociation.object_type))).scalars().all()
    hist = (await db.execute(select(CRMLifecycleHistory).where(CRMLifecycleHistory.contact_id == c.id)
                             .order_by(CRMLifecycleHistory.changed_at.desc()))).scalars().all()
    from app.services import sensitive_service as sens
    return {**_out(c, current_user, await sens.policy(db), await _rules(db, current_user), (await _props(db, [c.id]))[c.id]),
            "associations": [{"id": str(a.id), "object_type": a.object_type, "object_id": str(a.object_id), "label": a.label}
                             for a in assoc],
            "lifecycle_history": [{"from": h.from_stage, "to": h.to_stage, "source": h.source, "reason": h.reason,
                                   "changed_at": h.changed_at.isoformat()} for h in hist]}


@router.put("/{contact_id}", dependencies=[Depends(require_any_permission(EDIT))])
async def update_contact(contact_id: uuid.UUID, body: ContactIn, db: AsyncSession = Depends(get_db),
                         current_user=Depends(get_current_user)):
    c = await _get_edit(db, contact_id, current_user)
    if body.phone and body.phone.startswith("•••"):   # M45.S01.T017 masked value: keep the stored one
        body.phone = c.phone
    rules = await _rules(db, current_user)
    for k in rules:                            # a restricted field left out of the body keeps its stored value
        if k in ContactIn.model_fields and k not in body.model_fields_set:
            setattr(body, k, getattr(c, k))
    new = {k: getattr(body, k) for k in ContactIn.model_fields}
    new["email"] = cs.norm_email(str(body.email) if body.email else None)
    _guard(rules, new, _std(c))
    email = cs.norm_email(str(body.email) if body.email else None)
    if email and email != c.email and (dup := await cs.find_by_email(db, email)) is not None:
        raise HTTPException(409, {"message": "Another contact has this e-mail; merge them instead.", "existing_id": str(dup.id)})
    c.full_name, c.email, c.phone, c.job_title, c.company_id, c.notes, c.language = (
        body.full_name.strip(), email, body.phone, body.job_title, body.company_id, body.notes, body.language)
    await db.commit()
    return _out(c, rules=rules)


class AssocIn(BaseModel):
    object_type: Literal["customer", "crm_record", "ticket", "quotation", "sales_order"]
    object_id: uuid.UUID
    label: str = Field("primary", max_length=20)


@router.post("/{contact_id}/associations", status_code=201, dependencies=[Depends(require_any_permission(EDIT))])
async def add_association(contact_id: uuid.UUID, body: AssocIn, db: AsyncSession = Depends(get_db),
                          current_user=Depends(get_current_user)):
    c = await _get_edit(db, contact_id, current_user)
    if body.object_type == "crm_record":
        from app.api.v1.endpoints.crm_pipeline import _scoped_record
        await _scoped_record(db, body.object_id, current_user, "edit")
    else:   # review M43 #14: other objects need company-wide CRM rights and must exist
        if not _edit_all(current_user):   # M48.S01.T023: a write needs company-wide *edit* rights
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
    c = await _get_edit(db, contact_id, current_user)
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
    c = await _get_edit(db, contact_id, current_user)
    rules = await _rules(db, current_user)
    _guard(rules, {"lifecycle_stage": body.stage}, _std(c))
    try:
        await cs.set_lifecycle(db, c, body.stage, "manual", current_user.id, allow_backward=True, reason=body.reason)
    except cs.ContactError as e:
        raise HTTPException(e.status_code, str(e)) from None
    await db.commit()
    return _out(c, rules=rules)


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
    rules = await _rules(db, current_user)
    return [{**_out(c, current_user, pol, rules), "label": label} for c, label in await cs.contacts_for(db, object_type, object_id)]


# ── M47.S01.T010 contact properties (manual) ─────────────────────────────────

class PropertyIn(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,59}$")
    value: Optional[str] = Field(None, max_length=2000)


@router.put("/{contact_id}/properties", dependencies=[Depends(require_any_permission(EDIT))])
async def set_property(contact_id: uuid.UUID, body: PropertyIn, db: AsyncSession = Depends(get_db),
                       current_user=Depends(get_current_user)):
    """Typed properties only; smart (rule-filled) properties are recomputed from activity and cannot be typed over."""
    from app.models.m47_platform import CRMContactProperty
    c = await _get_edit(db, contact_id, current_user)
    if body.key in cs.SMART_KEYS or body.key in ContactIn.model_fields:
        raise HTTPException(422, "This property is filled automatically or is a standard field.")
    p = await db.get(CRMContactProperty, (c.id, body.key))
    _guard(await _rules(db, current_user), {body.key: body.value}, {body.key: p.value if p else None})
    if p is None:
        db.add(CRMContactProperty(contact_id=c.id, key=body.key, value=body.value, source="MANUAL"))
    else:
        from datetime import datetime, timezone
        p.value, p.updated_at = body.value, datetime.now(timezone.utc)
    await db.commit()
    return {"key": body.key, "value": body.value}
