"""Dynamic / AI Pricing Engine endpoints.

Prefix: /api/v1/dynamic-pricing
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
from app.models.dynamic_pricing import (
    CompetitorPrice, PriceRecommendation,
    PriceChannel, RecommendationStatus,
)

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class CompetitorPriceIn(BaseModel):
    product_name: str
    our_sku: Optional[str] = None
    competitor_name: str
    competitor_sku: Optional[str] = None
    price: float
    currency: str = "KES"
    channel: PriceChannel = PriceChannel.MODERN_TRADE
    pack_size: Optional[str] = None
    observed_date: date
    source: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None


def _cp_out(c: CompetitorPrice) -> dict:
    return {
        "id": str(c.id),
        "product_name": c.product_name,
        "our_sku": c.our_sku,
        "competitor_name": c.competitor_name,
        "price": float(c.price),
        "currency": c.currency,
        "channel": c.channel,
        "pack_size": c.pack_size,
        "observed_date": str(c.observed_date),
        "source": c.source,
        "location": c.location,
        "notes": c.notes,
        "recorded_by": c.recorded_by,
        "created_at": c.created_at.isoformat() if c.created_at else "",
    }


def _rec_out(r: PriceRecommendation) -> dict:
    return {
        "id": str(r.id),
        "product_name": r.product_name,
        "our_sku": r.our_sku,
        "channel": r.channel,
        "current_price": float(r.current_price) if r.current_price else None,
        "recommended_price": float(r.recommended_price),
        "floor_price": float(r.floor_price) if r.floor_price else None,
        "avg_competitor_price": float(r.avg_competitor_price) if r.avg_competitor_price else None,
        "margin_pct": float(r.margin_pct) if r.margin_pct else None,
        "confidence_score": r.confidence_score,
        "rationale": r.rationale,
        "trigger": r.trigger,
        "status": r.status,
        "applied_by": r.applied_by,
        "applied_at": r.applied_at.isoformat() if r.applied_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else "",
    }


# ── Competitor Prices ─────────────────────────────────────────────────────────

@router.post("/competitor-prices", status_code=201)
async def add_competitor_price(
    payload: CompetitorPriceIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    cp = CompetitorPrice(
        **payload.model_dump(),
        recorded_by=getattr(current_user, "username", None) or str(current_user.id),
    )
    db.add(cp)
    await db.commit()
    await db.refresh(cp)
    return _cp_out(cp)


@router.get("/competitor-prices")
async def list_competitor_prices(
    product_name: Optional[str] = None,
    our_sku: Optional[str] = None,
    channel: Optional[str] = None,
    competitor_name: Optional[str] = None,
    days: int = Query(90, ge=1, le=365),
    limit: int = Query(200, le=1000),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    cutoff = date.today() - timedelta(days=days)
    q = select(CompetitorPrice).where(CompetitorPrice.observed_date >= cutoff)
    if product_name:
        q = q.where(CompetitorPrice.product_name.ilike(f"%{product_name}%"))
    if our_sku:
        q = q.where(CompetitorPrice.our_sku == our_sku)
    if channel:
        q = q.where(CompetitorPrice.channel == channel)
    if competitor_name:
        q = q.where(CompetitorPrice.competitor_name.ilike(f"%{competitor_name}%"))
    q = q.order_by(desc(CompetitorPrice.observed_date)).limit(limit)
    result = await db.execute(q)
    return [_cp_out(c) for c in result.scalars().all()]


@router.get("/competitor-prices/summary")
async def competitor_summary(
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Average competitor price per product × channel."""
    cutoff = date.today() - timedelta(days=days)
    r = await db.execute(
        select(
            CompetitorPrice.product_name,
            CompetitorPrice.our_sku,
            CompetitorPrice.channel,
            func.avg(CompetitorPrice.price).label("avg_price"),
            func.min(CompetitorPrice.price).label("min_price"),
            func.max(CompetitorPrice.price).label("max_price"),
            func.count().label("data_points"),
        )
        .where(CompetitorPrice.observed_date >= cutoff)
        .group_by(CompetitorPrice.product_name, CompetitorPrice.our_sku, CompetitorPrice.channel)
        .order_by(CompetitorPrice.product_name)
    )
    rows = r.all()
    return [
        {
            "product_name": row.product_name,
            "our_sku": row.our_sku,
            "channel": row.channel,
            "avg_competitor_price": round(float(row.avg_price), 2),
            "min_price": round(float(row.min_price), 2),
            "max_price": round(float(row.max_price), 2),
            "data_points": row.data_points,
        }
        for row in rows
    ]


# ── AI / Rule-Based Price Recommendations ─────────────────────────────────────

class GenerateRecIn(BaseModel):
    product_name: str
    our_sku: Optional[str] = None
    current_price: float
    cost_price: Optional[float] = None        # COGS per unit
    channel: PriceChannel = PriceChannel.MODERN_TRADE
    floor_margin_pct: float = 20.0            # min acceptable margin %
    target_margin_pct: float = 35.0


@router.post("/recommendations/generate", status_code=201)
async def generate_recommendation(
    payload: GenerateRecIn,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Rule-based price recommendation.
    Rules:
    1. If avg competitor price < current × 0.92 → recommend price cut to competitor avg × 0.98
    2. If margin < floor_margin_pct → recommend price increase to hit target margin
    3. Otherwise → HOLD (no change recommended)
    """
    cutoff = date.today() - timedelta(days=90)
    avg_r = await db.execute(
        select(func.avg(CompetitorPrice.price).label("avg"))
        .where(
            CompetitorPrice.observed_date >= cutoff,
            CompetitorPrice.product_name.ilike(f"%{payload.product_name}%"),
            CompetitorPrice.channel == payload.channel,
        )
    )
    avg_competitor = avg_r.scalar()

    # Compute current margin
    current_margin_pct = None
    if payload.cost_price and payload.cost_price > 0:
        current_margin_pct = (payload.current_price - payload.cost_price) / payload.current_price * 100

    # Rule engine
    recommended = payload.current_price
    trigger = "HOLD"
    rationale = "Price is competitive and margin is acceptable."
    confidence = 70

    if avg_competitor is not None:
        avg_comp = float(avg_competitor)
        if avg_comp < payload.current_price * 0.92:
            recommended = round(avg_comp * 0.98, 2)
            trigger = "COMPETITOR_UNDERCUT"
            rationale = (
                f"Competitor avg KES {avg_comp:.2f} is more than 8% below our price "
                f"KES {payload.current_price:.2f}. Recommend reducing to "
                f"KES {recommended:.2f} (2% below competitor avg)."
            )
            confidence = 80

    if payload.cost_price and payload.cost_price > 0:
        floor_price = payload.cost_price / (1 - payload.floor_margin_pct / 100)
        target_price = payload.cost_price / (1 - payload.target_margin_pct / 100)
        if current_margin_pct is not None and current_margin_pct < payload.floor_margin_pct:
            if recommended < floor_price:
                recommended = round(floor_price, 2)
                trigger = "LOW_MARGIN"
                rationale = (
                    f"Current margin {current_margin_pct:.1f}% is below floor "
                    f"{payload.floor_margin_pct}%. Price must be ≥ KES {floor_price:.2f} "
                    f"to maintain minimum margin."
                )
                confidence = 95
    else:
        floor_price = None
        target_price = None

    if trigger == "HOLD":
        rec_price = payload.current_price
    else:
        rec_price = recommended

    rec = PriceRecommendation(
        product_name=payload.product_name,
        our_sku=payload.our_sku,
        channel=payload.channel,
        current_price=payload.current_price,
        recommended_price=rec_price,
        floor_price=floor_price,
        avg_competitor_price=float(avg_competitor) if avg_competitor else None,
        margin_pct=current_margin_pct,
        confidence_score=confidence if trigger != "HOLD" else 50,
        rationale=rationale,
        trigger=trigger,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    return _rec_out(rec)


@router.get("/recommendations")
async def list_recommendations(
    status: Optional[str] = None,
    channel: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(PriceRecommendation)
    if status:
        q = q.where(PriceRecommendation.status == status)
    if channel:
        q = q.where(PriceRecommendation.channel == channel)
    q = q.order_by(desc(PriceRecommendation.created_at)).limit(limit)
    result = await db.execute(q)
    return [_rec_out(r) for r in result.scalars().all()]


@router.post("/recommendations/{rec_id}/apply")
async def apply_recommendation(
    rec_id: str,
    applied_by: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    r = await db.execute(
        select(PriceRecommendation).where(PriceRecommendation.id == uuid.UUID(rec_id))
    )
    rec = r.scalar_one_or_none()
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    rec.status = RecommendationStatus.APPLIED
    rec.applied_by = applied_by
    rec.applied_at = datetime.utcnow()
    await db.commit()
    return _rec_out(rec)


@router.post("/recommendations/{rec_id}/reject")
async def reject_recommendation(
    rec_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    r = await db.execute(
        select(PriceRecommendation).where(PriceRecommendation.id == uuid.UUID(rec_id))
    )
    rec = r.scalar_one_or_none()
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    rec.status = RecommendationStatus.REJECTED
    await db.commit()
    return _rec_out(rec)


@router.get("/dashboard")
async def pricing_dashboard(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    total_cp_r = await db.execute(select(func.count()).select_from(CompetitorPrice))
    pending_r = await db.execute(
        select(func.count()).select_from(PriceRecommendation)
        .where(PriceRecommendation.status == RecommendationStatus.PENDING)
    )
    applied_r = await db.execute(
        select(func.count()).select_from(PriceRecommendation)
        .where(PriceRecommendation.status == RecommendationStatus.APPLIED)
    )
    undercut_r = await db.execute(
        select(func.count()).select_from(PriceRecommendation)
        .where(
            PriceRecommendation.trigger == "COMPETITOR_UNDERCUT",
            PriceRecommendation.status == RecommendationStatus.PENDING,
        )
    )
    by_channel_r = await db.execute(
        select(CompetitorPrice.channel, func.count().label("cnt"))
        .group_by(CompetitorPrice.channel)
    )
    return {
        "total_competitor_observations": total_cp_r.scalar() or 0,
        "pending_recommendations": pending_r.scalar() or 0,
        "applied_recommendations": applied_r.scalar() or 0,
        "competitor_undercut_alerts": undercut_r.scalar() or 0,
        "competitor_data_by_channel": {r.channel: r.cnt for r in by_channel_r.all()},
    }
