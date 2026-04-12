from __future__ import annotations
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.deps import require_permission
from app.crud import pricing as crud
from app.models.pricing import PricingLevel
from app.schemas.pricing import (
    PricingRuleCreate, PricingRuleUpdate, PricingRuleRead,
    PromotionCreate, PromotionUpdate, PromotionRead,
)

router = APIRouter()


# ── Pricing Rules ─────────────────────────────────────────────────────────────

@router.get("/rules", response_model=List[PricingRuleRead],
            dependencies=[Depends(require_permission("sales", "view"))])
async def list_rules(
    product_id: Optional[uuid.UUID] = Query(None),
    pricing_level: Optional[PricingLevel] = Query(None),
    region: Optional[str] = Query(None),
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    rules = await crud.list_pricing_rules(
        db, product_id=product_id, pricing_level=pricing_level,
        region=region, active_only=active_only,
    )
    result = []
    for r in rules:
        rd = PricingRuleRead.model_validate(r)
        if r.product:
            rd.product_name = r.product.name
        result.append(rd)
    return result


@router.post("/rules", response_model=PricingRuleRead, status_code=201,
             dependencies=[Depends(require_permission("sales", "create"))])
async def create_rule(data: PricingRuleCreate, db: AsyncSession = Depends(get_db)):
    rule = await crud.create_pricing_rule(db, data)
    await db.commit()
    return rule


@router.patch("/rules/{rule_id}", response_model=PricingRuleRead,
              dependencies=[Depends(require_permission("sales", "edit"))])
async def update_rule(
    rule_id: uuid.UUID,
    data: PricingRuleUpdate,
    db: AsyncSession = Depends(get_db),
):
    rule = await crud.get_pricing_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Pricing rule not found")
    rule = await crud.update_pricing_rule(db, rule, data)
    await db.commit()
    return rule


# ── Promotions ────────────────────────────────────────────────────────────────

@router.get("/promotions", response_model=List[PromotionRead],
            dependencies=[Depends(require_permission("sales", "view"))])
async def list_promotions(
    active_only: bool = Query(True),
    region: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    promos = await crud.list_promotions(db, active_only=active_only, region=region)
    result = []
    for p in promos:
        pd = PromotionRead.model_validate(p)
        pd.product_ids = [pp.product_id for pp in p.products]
        result.append(pd)
    return result


@router.post("/promotions", response_model=PromotionRead, status_code=201,
             dependencies=[Depends(require_permission("sales", "create"))])
async def create_promotion(data: PromotionCreate, db: AsyncSession = Depends(get_db)):
    promo = await crud.create_promotion(db, data)
    await db.commit()
    pd = PromotionRead.model_validate(promo)
    pd.product_ids = [pp.product_id for pp in promo.products]
    return pd


@router.patch("/promotions/{promo_id}", response_model=PromotionRead,
              dependencies=[Depends(require_permission("sales", "edit"))])
async def update_promotion(
    promo_id: uuid.UUID,
    data: PromotionUpdate,
    db: AsyncSession = Depends(get_db),
):
    promo = await crud.get_promotion(db, promo_id)
    if not promo:
        raise HTTPException(status_code=404, detail="Promotion not found")
    promo = await crud.update_promotion(db, promo, data)
    await db.commit()
    pd = PromotionRead.model_validate(promo)
    pd.product_ids = [pp.product_id for pp in promo.products]
    return pd
