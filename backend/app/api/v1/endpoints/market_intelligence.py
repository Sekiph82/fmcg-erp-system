"""Market Intelligence / Competitor Tracking endpoints.

Prefix: /api/v1/market-intel
"""
from __future__ import annotations

import uuid
from datetime import datetime, date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.market_intelligence import (
    MarketObservation, MarketShareEstimate, OutletType,
)

router = APIRouter()
_SEQ = 0


def _ref() -> str:
    global _SEQ
    _SEQ += 1
    return f"OBS-{datetime.utcnow().strftime('%Y%m%d')}-{_SEQ:04d}"


def _obs_out(o: MarketObservation) -> dict:
    return {
        "id": str(o.id),
        "obs_ref": o.obs_ref,
        "observer_name": o.observer_name,
        "outlet_name": o.outlet_name,
        "outlet_type": o.outlet_type,
        "location": o.location,
        "category": o.category,
        "observation_date": str(o.observation_date),
        "our_brand": o.our_brand,
        "our_facings": o.our_facings,
        "total_facings": o.total_facings,
        "our_shelf_share_pct": float(o.our_shelf_share_pct) if o.our_shelf_share_pct else None,
        "our_promo_active": o.our_promo_active,
        "competitor_promo_active": o.competitor_promo_active,
        "competitor_promo_notes": o.competitor_promo_notes,
        "our_oos_flag": o.our_oos_flag,
        "notes": o.notes,
        "created_at": o.created_at.isoformat() if o.created_at else "",
    }


def _share_out(s: MarketShareEstimate) -> dict:
    return {
        "id": str(s.id),
        "category": s.category,
        "period_month": s.period_month,
        "our_brand": s.our_brand,
        "our_share_pct": float(s.our_share_pct) if s.our_share_pct else None,
        "total_market_value_kes": float(s.total_market_value_kes) if s.total_market_value_kes else None,
        "our_value_kes": float(s.our_value_kes) if s.our_value_kes else None,
        "competitor_shares": s.competitor_shares,
        "source": s.source,
        "notes": s.notes,
        "created_at": s.created_at.isoformat() if s.created_at else "",
    }


# ── Schemas ───────────────────────────────────────────────────────────────────

class ObsIn(BaseModel):
    outlet_name: str
    outlet_type: OutletType = OutletType.SUPERMARKET
    location: Optional[str] = None
    category: str
    observation_date: date
    observer_name: Optional[str] = None
    our_brand: Optional[str] = None
    our_facings: Optional[int] = None
    total_facings: Optional[int] = None
    our_promo_active: bool = False
    competitor_promo_active: bool = False
    competitor_promo_notes: Optional[str] = None
    our_oos_flag: bool = False
    notes: Optional[str] = None


class ShareIn(BaseModel):
    category: str
    period_month: str        # YYYY-MM
    our_brand: Optional[str] = None
    our_share_pct: Optional[float] = None
    total_market_value_kes: Optional[float] = None
    our_value_kes: Optional[float] = None
    competitor_shares: Optional[dict] = None
    source: Optional[str] = None
    notes: Optional[str] = None


# ── Observations ──────────────────────────────────────────────────────────────

@router.post("/observations", status_code=201)
async def add_observation(payload: ObsIn, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    shelf_share = None
    if payload.our_facings is not None and payload.total_facings and payload.total_facings > 0:
        shelf_share = round(payload.our_facings / payload.total_facings * 100, 2)

    obs = MarketObservation(
        obs_ref=_ref(),
        **{k: v for k, v in payload.model_dump().items()},
        our_shelf_share_pct=shelf_share,
    )
    db.add(obs)
    await db.commit()
    await db.refresh(obs)
    return _obs_out(obs)


@router.get("/observations")
async def list_observations(
    category: Optional[str] = None,
    outlet_name: Optional[str] = None,
    location: Optional[str] = None,
    oos_only: bool = False,
    days: int = Query(90, ge=1, le=365),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    cutoff = date.today() - timedelta(days=days)
    q = select(MarketObservation).where(MarketObservation.observation_date >= cutoff)
    if category:
        q = q.where(MarketObservation.category.ilike(f"%{category}%"))
    if outlet_name:
        q = q.where(MarketObservation.outlet_name.ilike(f"%{outlet_name}%"))
    if location:
        q = q.where(MarketObservation.location.ilike(f"%{location}%"))
    if oos_only:
        q = q.where(MarketObservation.our_oos_flag == True)
    q = q.order_by(desc(MarketObservation.observation_date)).limit(limit)
    result = await db.execute(q)
    return [_obs_out(o) for o in result.scalars().all()]


@router.get("/shelf-share/summary")
async def shelf_share_summary(
    category: Optional[str] = None,
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Average shelf share % per category + OOS rate."""
    cutoff = date.today() - timedelta(days=days)
    q = (
        select(
            MarketObservation.category,
            func.avg(MarketObservation.our_shelf_share_pct).label("avg_shelf_share"),
            func.count().label("observations"),
            func.sum(MarketObservation.our_oos_flag.cast(int)).label("oos_count"),
            func.sum(MarketObservation.competitor_promo_active.cast(int)).label("comp_promo_count"),
        )
        .where(
            MarketObservation.observation_date >= cutoff,
            MarketObservation.our_shelf_share_pct.isnot(None),
        )
    )
    if category:
        q = q.where(MarketObservation.category.ilike(f"%{category}%"))
    q = q.group_by(MarketObservation.category).order_by(MarketObservation.category)
    result = await db.execute(q)
    rows = result.all()
    return [
        {
            "category": r.category,
            "avg_shelf_share_pct": round(float(r.avg_shelf_share), 2) if r.avg_shelf_share else None,
            "observations": r.observations,
            "oos_rate_pct": round(int(r.oos_count or 0) / r.observations * 100, 1),
            "competitor_promo_rate_pct": round(int(r.comp_promo_count or 0) / r.observations * 100, 1),
        }
        for r in rows
    ]


@router.get("/dashboard")
async def market_intel_dashboard(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    today = date.today()
    cutoff_30 = today - timedelta(days=30)

    total_r = await db.execute(select(func.count()).select_from(MarketObservation))
    recent_r = await db.execute(
        select(func.count()).select_from(MarketObservation)
        .where(MarketObservation.observation_date >= cutoff_30)
    )
    oos_r = await db.execute(
        select(func.count()).select_from(MarketObservation)
        .where(MarketObservation.our_oos_flag == True, MarketObservation.observation_date >= cutoff_30)
    )
    avg_share_r = await db.execute(
        select(func.avg(MarketObservation.our_shelf_share_pct))
        .where(
            MarketObservation.observation_date >= cutoff_30,
            MarketObservation.our_shelf_share_pct.isnot(None),
        )
    )
    share_estimates_r = await db.execute(select(func.count()).select_from(MarketShareEstimate))

    return {
        "total_observations": total_r.scalar() or 0,
        "observations_last_30d": recent_r.scalar() or 0,
        "oos_incidents_30d": oos_r.scalar() or 0,
        "avg_shelf_share_30d": round(float(avg_share_r.scalar()), 2) if avg_share_r.scalar() else None,
        "market_share_estimates": share_estimates_r.scalar() or 0,
    }


# ── Market Share Estimates ────────────────────────────────────────────────────

@router.post("/market-share", status_code=201)
async def add_market_share(payload: ShareIn, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    est = MarketShareEstimate(**payload.model_dump())
    db.add(est)
    await db.commit()
    await db.refresh(est)
    return _share_out(est)


@router.get("/market-share")
async def list_market_share(
    category: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(MarketShareEstimate)
    if category:
        q = q.where(MarketShareEstimate.category.ilike(f"%{category}%"))
    q = q.order_by(desc(MarketShareEstimate.period_month), MarketShareEstimate.category).limit(limit)
    result = await db.execute(q)
    return [_share_out(s) for s in result.scalars().all()]
