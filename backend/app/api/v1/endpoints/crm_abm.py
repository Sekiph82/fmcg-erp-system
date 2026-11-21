"""Account-based marketing API (M36.S05.T005). Reading needs CRM-wide or marketing view; changes need CRM-wide
or marketing edit rights (key accounts are worked across territories)."""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import require_any_permission
from app.core.deps import get_db
from app.models.crm import CRMAccountContact, CRMAccountGroup, CRMAccountGroupMember
from app.services import crm_abm_service as abm

router = APIRouter()
READ = require_any_permission(("crm.view_all", "crm.edit_all", "marketing.view", "marketing.edit"))
WRITE = require_any_permission(("crm.edit_all", "marketing.edit", "marketing.create"))


class GroupIn(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: Optional[str] = Field(None, max_length=2000)


class MemberIn(BaseModel):
    customer_id: uuid.UUID
    tier: int = Field(2, ge=1, le=3)


class ContactIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    title: Optional[str] = Field(None, max_length=150)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    committee_role: str = Field("INFLUENCER", pattern="^(DECISION_MAKER|BUYER|INFLUENCER|CHAMPION|USER|BLOCKER)$")
    notes: Optional[str] = Field(None, max_length=500)


class CampaignIn(BaseModel):
    subject: str = Field(min_length=3, max_length=300)
    body: str = Field(min_length=10, max_length=20000)
    roles: Optional[List[str]] = None


async def _group(db: AsyncSession, group_id: uuid.UUID) -> CRMAccountGroup:
    g = await db.get(CRMAccountGroup, group_id)
    if g is None:
        raise HTTPException(404, "Account group not found")
    return g


def _contact_out(c: CRMAccountContact) -> dict:
    return {"id": str(c.id), "customer_id": str(c.customer_id), "full_name": c.full_name, "title": c.title, "email": c.email,
            "phone": c.phone, "committee_role": c.committee_role, "notes": c.notes}


@router.get("/groups")
async def list_groups(db: AsyncSession = Depends(get_db), _=Depends(READ)):
    from sqlalchemy import func
    rows = (await db.execute(select(CRMAccountGroup, func.count(CRMAccountGroupMember.customer_id))
                             .outerjoin(CRMAccountGroupMember, CRMAccountGroupMember.group_id == CRMAccountGroup.id)
                             .group_by(CRMAccountGroup.id).order_by(CRMAccountGroup.name))).all()
    return [{"id": str(g.id), "name": g.name, "description": g.description, "accounts": n,
             "campaign_started_at": g.campaign_started_at.isoformat() if g.campaign_started_at else None} for g, n in rows]


@router.post("/groups", status_code=201)
async def create_group(body: GroupIn, db: AsyncSession = Depends(get_db), user=Depends(WRITE)):
    g = CRMAccountGroup(name=body.name.strip(), description=body.description, owner_user_id=user.id)
    db.add(g)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "A group with this name exists.")
    return {"id": str(g.id)}


@router.get("/groups/{group_id}")
async def get_group(group_id: uuid.UUID, days: int = Query(90, ge=7, le=365), db: AsyncSession = Depends(get_db), _=Depends(READ)):
    return await abm.group_overview(db, await _group(db, group_id), days)


@router.post("/groups/{group_id}/members", status_code=201)
async def add_member(group_id: uuid.UUID, body: MemberIn, db: AsyncSession = Depends(get_db), _=Depends(WRITE)):
    from sqlalchemy.dialects.postgresql import insert
    from app.models.sales import Customer
    await _group(db, group_id)
    if await db.get(Customer, body.customer_id) is None:
        raise HTTPException(422, "Unknown customer.")
    await db.execute(insert(CRMAccountGroupMember).values(group_id=group_id, customer_id=body.customer_id, tier=body.tier)
                     .on_conflict_do_update(index_elements=["group_id", "customer_id"], set_={"tier": body.tier}))
    await db.commit()
    return {"ok": True}


@router.delete("/groups/{group_id}/members/{customer_id}")
async def remove_member(group_id: uuid.UUID, customer_id: uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(WRITE)):
    await db.execute(delete(CRMAccountGroupMember).where(CRMAccountGroupMember.group_id == group_id,
                                                         CRMAccountGroupMember.customer_id == customer_id))
    await db.commit()
    return {"ok": True}


@router.get("/accounts/{customer_id}/committee")
async def get_committee(customer_id: uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(READ)):
    return {"contacts": [_contact_out(c) for c in await abm.committee(db, customer_id)],
            "engagement": await abm.engagement(db, customer_id)}


@router.post("/accounts/{customer_id}/committee", status_code=201)
async def add_contact(customer_id: uuid.UUID, body: ContactIn, db: AsyncSession = Depends(get_db), _=Depends(WRITE)):
    from app.models.sales import Customer
    if await db.get(Customer, customer_id) is None:
        raise HTTPException(422, "Unknown customer.")
    c = CRMAccountContact(customer_id=customer_id, **body.model_dump())
    db.add(c)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "This e-mail is already in the committee.")
    return _contact_out(c)


@router.delete("/contacts/{contact_id}")
async def remove_contact(contact_id: uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(WRITE)):
    await db.execute(delete(CRMAccountContact).where(CRMAccountContact.id == contact_id))
    await db.commit()
    return {"ok": True}


@router.post("/groups/{group_id}/campaign")
async def group_campaign(group_id: uuid.UUID, body: CampaignIn, db: AsyncSession = Depends(get_db), user=Depends(WRITE)):
    try:
        out = await abm.run_campaign(db, await _group(db, group_id), body.subject, body.body, body.roles, user.username)
    except abm.ABMError as e:
        raise HTTPException(e.status, e.detail)
    await db.commit()
    return out
