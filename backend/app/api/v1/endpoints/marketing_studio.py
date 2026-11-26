"""Integrated Marketing Studio (M49.S01.T012). Prefix /api/v1/marketing-studio.

One workspace per campaign: brief, linked creative / audiences / channel items, budget against the finance cap and
analytics with ERP attribution. It links to records owned by other modules; each channel is still approved and
submitted there. Every mutation is audited. A budget above MARKETING_STUDIO_BUDGET_CAP needs a finance approver who is
not the requester."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission, require_any_permission
from app.core.deps import get_current_user, get_db
from app.models.m49_studio import StudioBudgetRequest, StudioCampaign, StudioLink
from app.models.marketing import Campaign
from app.services import ads_service as svc
from app.services import marketing_studio_service as ms

router = APIRouter(dependencies=[Depends(require_any_permission(ms.READ + ms.FINANCE))])   # finance approvers decide from My Approvals


def _w(u) -> None:
    if not (u.is_superuser or has_any_permission(u, ms.WRITE)):
        raise HTTPException(403, "Marketing editors only.")


async def _campaign(db: AsyncSession, cid: uuid.UUID, lock: bool = False) -> Campaign:
    q = select(Campaign).where(Campaign.id == cid)
    c = (await db.execute(q.with_for_update() if lock else q)).scalar_one_or_none()
    if c is None:
        raise HTTPException(404, "Campaign not found")
    return c


@router.get("/campaigns")
async def campaigns(db: AsyncSession = Depends(get_db)):
    briefed = set((await db.execute(select(StudioCampaign.campaign_id))).scalars())
    rows = (await db.execute(select(Campaign).order_by(Campaign.created_at.desc()).limit(200))).scalars().all()
    return [{"id": str(c.id), "code": c.campaign_code, "name": c.campaign_name, "status": c.status.value,
             "approval_status": c.approval_status.value, "budget": str(c.budget) if c.budget is not None else None,
             "has_brief": c.id in briefed} for c in rows]


@router.get("/campaigns/{cid}")
async def get_studio(cid: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return await ms.studio(db, await _campaign(db, cid), user)


class BriefIn(BaseModel):
    summary: str = Field(min_length=1, max_length=2000)
    key_message: str = Field(min_length=1, max_length=500)
    audience_notes: str = Field("", max_length=1000)
    kpi: str = Field("", max_length=300)
    channels: list[Literal["email", "social", "ads"]] = Field(default_factory=list, max_length=3)
    product_skus: list[str] = Field(default_factory=list, max_length=20)


@router.put("/campaigns/{cid}/brief")
async def put_brief(cid: uuid.UUID, body: BriefIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _w(user)
    c = await _campaign(db, cid, lock=True)
    new = body.model_dump()
    new["channels"] = list(dict.fromkeys(new["channels"]))
    sc = await db.get(StudioCampaign, c.id)
    if sc is None:
        db.add(StudioCampaign(campaign_id=c.id, brief=new, brief_version=1, brief_history=[], updated_by=user.username))
    elif sc.brief != new:
        sc.brief_history = [*(sc.brief_history or []), {"version": sc.brief_version, "by": sc.updated_by, "brief": sc.brief}][-20:]
        sc.brief, sc.brief_version, sc.updated_by = new, sc.brief_version + 1, user.username
        sc.updated_at = datetime.now(timezone.utc)
    ms.audit(db, user, "BRIEF_SAVED", c.id, {"version": (sc.brief_version if sc else 1), "channels": new["channels"]})
    await db.commit()
    return await ms.studio(db, c, user)


class LinkIn(BaseModel):
    kind: Literal["DAM_ASSET", "BRAND_ASSET", "EMAIL_DESIGN", "SOCIAL_POST", "AD_TREE", "AUDIENCE_SYNC", "AUDIENCE"]
    ref_id: uuid.UUID


@router.get("/campaigns/{cid}/candidates")
async def candidates(cid: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return await ms.candidates(db, await _campaign(db, cid), user)


@router.post("/campaigns/{cid}/links", status_code=201)
async def add_link(cid: uuid.UUID, body: LinkIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _w(user)
    c = await _campaign(db, cid)
    try:
        label, version = await ms.resolve(db, body.kind, body.ref_id, user)
    except svc.Refused as e:
        raise HTTPException(e.status, str(e)) from None
    link = StudioLink(campaign_id=c.id, kind=body.kind, ref_id=body.ref_id, linked_version=version, label=label[:300],
                      created_by=user.username)
    db.add(link)
    ms.audit(db, user, "LINKED", c.id, {"kind": body.kind, "ref_id": str(body.ref_id), "version": version})
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Already linked to this campaign.") from None
    return await ms.link_view(db, link, user)


@router.delete("/campaigns/{cid}/links/{lid}", status_code=204)
async def remove_link(cid: uuid.UUID, lid: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _w(user)
    link = await db.get(StudioLink, lid)
    if link is None or link.campaign_id != cid:
        raise HTTPException(404, "Link not found")
    ms.audit(db, user, "UNLINKED", cid, {"kind": link.kind, "ref_id": str(link.ref_id)})
    await db.delete(link)
    await db.commit()


class BudgetIn(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=16, decimal_places=2)
    note: Optional[str] = Field(None, max_length=300)


@router.post("/campaigns/{cid}/budget", status_code=201)
async def request_budget(cid: uuid.UUID, body: BudgetIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Within the cap: applied at once. Above it: PENDING until a finance approver (not the requester) decides."""
    _w(user)
    c = await _campaign(db, cid, lock=True)
    if (await db.execute(select(StudioBudgetRequest.id).where(StudioBudgetRequest.campaign_id == c.id,
                                                              StudioBudgetRequest.status == "PENDING"))).first():
        raise HTTPException(409, "A budget request is already waiting for finance.")
    limit = ms.cap()
    within = body.amount <= limit
    r = StudioBudgetRequest(campaign_id=c.id, amount=body.amount, cap=limit, status="APPLIED" if within else "PENDING",
                            note=body.note, requested_by=user.username)
    db.add(r)
    if within:
        c.budget = body.amount
    await db.flush()
    ms.audit(db, user, "BUDGET_APPLIED" if within else "BUDGET_REQUESTED", c.id,
             {"request_id": str(r.id), "amount": str(body.amount), "cap": str(limit)})
    await db.commit()
    await db.refresh(r)
    return ms._req(r)


class DecideIn(BaseModel):
    ok: bool
    note: Optional[str] = Field(None, max_length=300)


@router.post("/budget-requests/{rid}/decide")
async def decide_budget(rid: uuid.UUID, body: DecideIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    if not (user.is_superuser or has_any_permission(user, ms.FINANCE)):
        raise HTTPException(403, "Finance approval is required for a budget above the cap.")
    r = (await db.execute(select(StudioBudgetRequest).where(StudioBudgetRequest.id == rid).with_for_update())).scalar_one_or_none()
    if r is None:
        raise HTTPException(404, "Budget request not found")
    if r.status != "PENDING":
        raise HTTPException(409, f"This request is already {r.status.lower()}.")
    if user.username == r.requested_by:
        raise HTTPException(403, "The requester cannot approve their own budget.")
    c = await _campaign(db, r.campaign_id, lock=True)
    r.status, r.decided_by, r.decided_at = ("APPROVED" if body.ok else "REJECTED"), user.username, datetime.now(timezone.utc)
    if body.note:
        r.note = body.note
    if body.ok:
        c.budget = r.amount
    ms.audit(db, user, "BUDGET_APPROVED" if body.ok else "BUDGET_REJECTED", c.id, {"request_id": str(r.id), "amount": str(r.amount)})
    await db.commit()
    await db.refresh(r)
    return ms._req(r)


@router.get("/campaigns/{cid}/analytics")
async def get_analytics(cid: uuid.UUID, company_id: Optional[uuid.UUID] = None, db: AsyncSession = Depends(get_db)):
    return await ms.analytics(db, await _campaign(db, cid), company_id)
