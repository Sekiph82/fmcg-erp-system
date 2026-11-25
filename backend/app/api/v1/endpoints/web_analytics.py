"""Website analytics reports for staff (M44.S01.T009). Prefix /api/v1/web-analytics."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import require_any_permission
from app.core.deps import get_current_user, get_db
from app.services import web_analytics_service as wa

READ = ("marketing.view", "marketing.edit", "crm.view_all", "crm.edit_all")
router = APIRouter(dependencies=[Depends(require_any_permission(READ))])


@router.get("/summary")
async def summary(days: int = Query(30, ge=1, le=400), db: AsyncSession = Depends(get_db)):
    return await wa.summary(db, days)


@router.get("/funnel")
async def funnel(steps: str = Query(..., max_length=1000), days: int = Query(30, ge=1, le=400),
                 db: AsyncSession = Depends(get_db)):
    parts = [s.strip() for s in steps.split(",") if s.strip()][:8]
    if len(parts) < 2:
        raise HTTPException(422, "Give at least two steps (page paths like /pricing or events like CTA:demo).")
    return await wa.funnel(db, parts, days)


@router.get("/journey")
async def journey(email: str = Query(..., min_length=3, max_length=254), db: AsyncSession = Depends(get_db)):
    return await wa.journey(db, email)


@router.get("/deal-journey/{record_id}")
async def deal_journey(record_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await wa.deal_journey(db, record_id)


@router.post("/purge-expired")
async def purge(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    if not current_user.is_superuser:
        raise HTTPException(403, "Administrators only.")
    n = await wa.purge_expired(db)
    await db.commit()
    return {"deleted_events": n}
