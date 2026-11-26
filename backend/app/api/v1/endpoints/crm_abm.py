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
WRITE = require_any_permission(("crm.edit_all", "marketing.edit"))


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
    company_id: Optional[uuid.UUID] = None      # required when the group's accounts belong to several companies
    approval_id: Optional[uuid.UUID] = None     # when MARKETING_EMAIL_APPROVAL_REQUIRED is on


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


def _may_send_for(user, company_id) -> None:
    """M48.S01.T023: the sender must have marketing (or company-wide CRM) edit rights in the campaign's company."""
    from app.core.access_control import can_access_scope, has_any_permission
    if user.is_superuser or has_any_permission(user, ("crm.edit_all",)):
        return
    if not can_access_scope(user, "marketing", "edit", "company", company_id or "ALL"):
        raise HTTPException(403, "You may not send marketing e-mail for this company.")


def _payload(group_id: uuid.UUID, company_id, body: CampaignIn) -> dict:
    return {"group_id": str(group_id), "company_id": str(company_id) if company_id else None, "subject": body.subject,
            "body": body.body, "roles": sorted(body.roles or [])}


@router.post("/groups/{group_id}/campaign")
async def group_campaign(group_id: uuid.UUID, body: CampaignIn, db: AsyncSession = Depends(get_db), user=Depends(WRITE)):
    """Coordinated send to one company's accounts of the group: company scope, the per-editor daily cap and, when
    MARKETING_EMAIL_APPROVAL_REQUIRED is on, a second editor's approval of this exact content (M48.S01.T023)."""
    from app.services import marketing_send_guard as guard
    try:
        g = await _group(db, group_id)
        company_id = await abm.campaign_company(db, g, body.company_id)
        _may_send_for(user, company_id)

        async def _checks(n: int) -> None:
            await guard.check_cap(db, user.username, n)
            await guard.consume(db, "ABM_GROUP", group_id, _payload(group_id, company_id, body), body.approval_id, user)

        out = await abm.run_campaign(db, g, body.subject, body.body, body.roles, user.username, company_id, _checks)
    except (abm.ABMError, guard.GuardError) as e:
        await db.rollback()
        raise HTTPException(e.status, e.detail)
    await db.commit()
    return out


@router.post("/groups/{group_id}/campaign/approval", status_code=201)
async def request_campaign_approval(group_id: uuid.UUID, body: CampaignIn, db: AsyncSession = Depends(get_db),
                                    user=Depends(WRITE)):
    from app.services import marketing_send_guard as guard
    try:
        company_id = await abm.campaign_company(db, await _group(db, group_id), body.company_id)
    except abm.ABMError as e:
        raise HTTPException(e.status, e.detail)
    _may_send_for(user, company_id)
    row = await guard.request(db, "ABM_GROUP", group_id, _payload(group_id, company_id, body), user, company_id)
    await db.commit()
    return guard.out(row)


@router.get("/campaign-approvals/policy")
async def campaign_send_policy(db: AsyncSession = Depends(get_db), user=Depends(WRITE)):
    from app.services import marketing_send_guard as guard
    return await guard.policy(db, user.username)


@router.get("/campaign-approvals")
async def list_campaign_approvals(status: str = Query("PENDING", pattern="^(PENDING|APPROVED|REJECTED|USED)$"),
                                  db: AsyncSession = Depends(get_db), _=Depends(WRITE)):
    from app.models.m48_crm_send_approval import CRMSendApproval
    from app.services import marketing_send_guard as guard
    rows = (await db.execute(select(CRMSendApproval).where(CRMSendApproval.kind == "ABM_GROUP", CRMSendApproval.status == status)
                             .order_by(CRMSendApproval.created_at.desc()).limit(200))).scalars()
    return [guard.out(r) for r in rows]


@router.post("/campaign-approvals/{approval_id}/{action}")
async def decide_campaign_approval(approval_id: uuid.UUID, action: str, db: AsyncSession = Depends(get_db),
                                   user=Depends(WRITE)):
    from app.services import marketing_send_guard as guard
    if action not in ("approve", "reject"):
        raise HTTPException(404, "Unknown action")
    try:
        row = await guard.decide(db, approval_id, "ABM_GROUP", user, action == "approve")
    except guard.GuardError as e:
        raise HTTPException(e.status, e.detail)
    if row.company_id:
        _may_send_for(user, row.company_id)
    await db.commit()
    return guard.out(row)
