"""Landing pages + A/B tests: staff API (M36.S05.T002). Marketing or CRM edit rights to change, view to read."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import require_any_permission
from app.core.deps import get_db
from app.models.crm import CRMLandingPage, CRMLandingVariant, CRMLeadForm
from app.services import crm_landing_service as lp

router = APIRouter()
READ = require_any_permission(("marketing.view", "marketing.edit", "crm.view_all", "crm.edit_all"))
WRITE = require_any_permission(("marketing.edit", "marketing.create", "crm.edit_all"))


class PageIn(BaseModel):
    slug: str = Field(min_length=3, max_length=80, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=2, max_length=150)
    lead_form_id: uuid.UUID
    min_sample: int = Field(100, ge=10, le=1000000)


class VariantIn(BaseModel):
    key: str = Field(pattern=r"^[A-E]$")
    headline: str = Field(min_length=3, max_length=200)
    body: Optional[str] = Field(None, max_length=5000)
    cta_label: str = Field("Send", min_length=1, max_length=60)
    weight: int = Field(50, ge=0, le=100)
    is_active: bool = True


class StatusIn(BaseModel):
    status: str = Field(pattern="^(DRAFT|LIVE|PAUSED)$")


async def _page(db: AsyncSession, page_id: uuid.UUID) -> CRMLandingPage:
    p = await db.get(CRMLandingPage, page_id)
    if p is None:
        raise HTTPException(404, "Landing page not found")
    return p


@router.get("/pages")
async def list_pages(db: AsyncSession = Depends(get_db), _=Depends(READ)):
    rows = (await db.execute(select(CRMLandingPage).order_by(CRMLandingPage.created_at.desc()))).scalars().all()
    return [{"id": str(p.id), "slug": p.slug, "name": p.name, "status": p.status, "lead_form_id": str(p.lead_form_id),
             "min_sample": p.min_sample} for p in rows]


@router.post("/pages", status_code=201)
async def create_page(body: PageIn, db: AsyncSession = Depends(get_db), _=Depends(WRITE)):
    form = await db.get(CRMLeadForm, body.lead_form_id)
    if form is None or not form.active_flag:
        raise HTTPException(422, "Choose an active lead form (it captures the lead and its consent).")
    page = CRMLandingPage(**body.model_dump())
    db.add(page)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "This address is already used.")
    return {"id": str(page.id)}


@router.put("/pages/{page_id}/variants")
async def save_variant(page_id: uuid.UUID, body: VariantIn, db: AsyncSession = Depends(get_db), _=Depends(WRITE)):
    from sqlalchemy.dialects.postgresql import insert
    page = await _page(db, page_id)
    if page.status == "LIVE" and body.weight is not None:
        pass  # weights may change while live; already-assigned visitors keep their variant only if weights stay
    await db.execute(insert(CRMLandingVariant).values(id=uuid.uuid4(), page_id=page.id, **body.model_dump())
                     .on_conflict_do_update(constraint="uq_crm_landing_variant_key", set_=body.model_dump(exclude={"key"})))
    await db.commit()
    return await lp.stats(db, page)


@router.post("/pages/{page_id}/status")
async def set_status(page_id: uuid.UUID, body: StatusIn, db: AsyncSession = Depends(get_db), _=Depends(WRITE)):
    page = await _page(db, page_id)
    if body.status == "LIVE":
        live = [v for v in await lp.variants(db, page.id) if v.is_active and v.weight > 0]
        if not live:
            raise HTTPException(422, "Add at least one active variant with a weight before going live.")
        if not any(v.key == "A" for v in live):
            raise HTTPException(422, "Variant A is the control and must be active.")
    page.status = body.status
    await db.commit()
    return {"status": page.status}


@router.get("/pages/{page_id}/stats")
async def page_stats(page_id: uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(READ)):
    return await lp.stats(db, await _page(db, page_id))
