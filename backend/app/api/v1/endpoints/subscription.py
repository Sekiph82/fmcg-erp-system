"""Subscription / Recurring Orders API endpoints."""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.subscription import (
    SubscriptionTemplateCreate, SubscriptionTemplateOut, SubscriptionTemplateUpdate,
    SubscriptionLineOut,
    GenerationLogOut, PauseSkipCreate, PauseSkipOut,
    SubAIRecOut, SubAIRecAck, GenerateNowRequest,
)
from app.services import subscription_service as svc

router = APIRouter()


def _404(label: str = "Record"):
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")


# ── Templates CRUD ────────────────────────────────────────────────────────────

@router.get("", response_model=List[SubscriptionTemplateOut])
async def list_templates(
    customer_id: Optional[UUID] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_templates(db, customer_id=customer_id, status=status, skip=skip, limit=limit)


@router.post("", response_model=SubscriptionTemplateOut, status_code=201)
async def create_template(
    payload: SubscriptionTemplateCreate,
    db: AsyncSession = Depends(get_db),
):
    return await svc.create_template(db, payload, user_id=None)


@router.get("/{template_id}", response_model=SubscriptionTemplateOut)
async def get_template(template_id: UUID, db: AsyncSession = Depends(get_db)):
    t = await svc.get_template(db, template_id)
    if not t:
        raise _404("Template")
    return t


@router.patch("/{template_id}", response_model=SubscriptionTemplateOut)
async def update_template(
    template_id: UUID,
    payload: SubscriptionTemplateUpdate,
    db: AsyncSession = Depends(get_db),
):
    t = await svc.get_template(db, template_id)
    if not t:
        raise _404("Template")
    return await svc.update_template(db, t, payload)


# ── Status transitions ────────────────────────────────────────────────────────

@router.post("/{template_id}/activate", response_model=SubscriptionTemplateOut)
async def activate(template_id: UUID, db: AsyncSession = Depends(get_db)):
    t = await svc.get_template(db, template_id)
    if not t:
        raise _404("Template")
    return await svc.activate_template(db, t, user_id=None)


@router.post("/{template_id}/cancel", response_model=SubscriptionTemplateOut)
async def cancel(template_id: UUID, db: AsyncSession = Depends(get_db)):
    t = await svc.get_template(db, template_id)
    if not t:
        raise _404("Template")
    return await svc.cancel_template(db, t)


@router.post("/{template_id}/archive", response_model=SubscriptionTemplateOut)
async def archive(template_id: UUID, db: AsyncSession = Depends(get_db)):
    t = await svc.get_template(db, template_id)
    if not t:
        raise _404("Template")
    return await svc.archive_template(db, t)


# ── Pause / Skip / Resume ─────────────────────────────────────────────────────

@router.post("/{template_id}/pause", response_model=PauseSkipOut, status_code=201)
async def pause(
    template_id: UUID,
    payload: PauseSkipCreate,
    db: AsyncSession = Depends(get_db),
):
    t = await svc.get_template(db, template_id)
    if not t:
        raise _404("Template")
    return await svc.add_pause_skip(db, t, payload, user_id=None)


@router.post("/{template_id}/skip-cycle", response_model=PauseSkipOut, status_code=201)
async def skip_cycle(
    template_id: UUID,
    payload: PauseSkipCreate,
    db: AsyncSession = Depends(get_db),
):
    t = await svc.get_template(db, template_id)
    if not t:
        raise _404("Template")
    from app.schemas.subscription import PauseSkipCreate as PSC
    payload.action_type = "SKIP_ONE_CYCLE"
    return await svc.add_pause_skip(db, t, payload, user_id=None)


@router.post("/{template_id}/resume", response_model=PauseSkipOut, status_code=201)
async def resume(
    template_id: UUID,
    payload: PauseSkipCreate,
    db: AsyncSession = Depends(get_db),
):
    t = await svc.get_template(db, template_id)
    if not t:
        raise _404("Template")
    payload.action_type = "RESUME"
    return await svc.add_pause_skip(db, t, payload, user_id=None)


@router.get("/{template_id}/pause-history", response_model=List[PauseSkipOut])
async def pause_history(template_id: UUID, db: AsyncSession = Depends(get_db)):
    return await svc.list_pause_skips(db, template_id)


# ── Order Generation ──────────────────────────────────────────────────────────

@router.post("/{template_id}/generate-now", response_model=GenerationLogOut, status_code=201)
async def generate_now(
    template_id: UUID,
    req: Optional[GenerateNowRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    t = await svc.get_template(db, template_id)
    if not t:
        raise _404("Template")
    target = t.next_generation_date or date.today()
    return await svc.generate_order(db, t, target, req, user_id=None, system_initiated=False)


@router.get("/{template_id}/generation-log", response_model=List[GenerationLogOut])
async def generation_log(
    template_id: UUID,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_generation_log(db, template_id, skip=skip, limit=limit)


# ── Scheduler trigger ─────────────────────────────────────────────────────────

@router.post("/scheduler/run", response_model=Dict[str, Any])
async def run_scheduler(db: AsyncSession = Depends(get_db)):
    return await svc.run_scheduled_generation(db)


# ── Upcoming Demand ───────────────────────────────────────────────────────────

@router.get("/upcoming-demand", response_model=List[Dict])
async def upcoming_demand(
    from_date: date = Query(default_factory=date.today),
    to_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
):
    if not to_date:
        from datetime import timedelta
        to_date = from_date + timedelta(days=30)
    return await svc.get_upcoming_demand(db, from_date, to_date)


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/templates", response_model=Dict[str, Any])
async def report_templates(db: AsyncSession = Depends(get_db)):
    return await svc.report_templates(db)


@router.get("/reports/generation", response_model=List[Dict])
async def report_generation(days: int = 30, db: AsyncSession = Depends(get_db)):
    return await svc.report_generation(db, days=days)


@router.get("/reports/failed", response_model=List[GenerationLogOut])
async def report_failed(days: int = 30, db: AsyncSession = Depends(get_db)):
    return await svc.report_failed(db, days=days)


# ── AI ────────────────────────────────────────────────────────────────────────

@router.post("/ai/run", response_model=List[SubAIRecOut], status_code=201)
async def run_ai(db: AsyncSession = Depends(get_db)):
    return await svc.run_ai_agents(db)


@router.get("/ai/recommendations", response_model=List[SubAIRecOut])
async def ai_recs(
    agent_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_ai_recs(db, agent_type=agent_type, status=status)


@router.patch("/ai/recommendations/{rec_id}", response_model=SubAIRecOut)
async def ack_rec(rec_id: UUID, payload: SubAIRecAck, db: AsyncSession = Depends(get_db)):
    rec = await svc.ack_ai_rec(db, rec_id, payload)
    if not rec:
        raise _404("Recommendation")
    return rec
