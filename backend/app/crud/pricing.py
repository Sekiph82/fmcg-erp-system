from __future__ import annotations
from typing import Optional, List
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.pricing import PricingRule, Promotion, PromotionProduct, PricingLevel
from app.schemas.pricing import PricingRuleCreate, PricingRuleUpdate, PromotionCreate, PromotionUpdate


async def list_pricing_rules(
    db: AsyncSession,
    *,
    product_id: Optional[uuid.UUID] = None,
    pricing_level: Optional[PricingLevel] = None,
    region: Optional[str] = None,
    active_only: bool = True,
) -> List[PricingRule]:
    q = select(PricingRule).options(
        selectinload(PricingRule.product),
    )
    if product_id:
        q = q.where(PricingRule.product_id == product_id)
    if pricing_level:
        q = q.where(PricingRule.pricing_level == pricing_level)
    if region:
        q = q.where(PricingRule.region == region)
    if active_only:
        q = q.where(PricingRule.is_active == True)  # noqa
    result = await db.execute(q.order_by(PricingRule.pricing_level))
    return list(result.scalars().all())


async def create_pricing_rule(db: AsyncSession, data: PricingRuleCreate) -> PricingRule:
    rule = PricingRule(**data.model_dump())
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return rule


async def update_pricing_rule(db: AsyncSession, rule: PricingRule, data: PricingRuleUpdate) -> PricingRule:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(rule, k, v)
    await db.flush()
    await db.refresh(rule)
    return rule


async def get_pricing_rule(db: AsyncSession, rule_id: uuid.UUID) -> Optional[PricingRule]:
    result = await db.execute(
        select(PricingRule).options(selectinload(PricingRule.product))
        .where(PricingRule.id == rule_id)
    )
    return result.scalar_one_or_none()


async def list_promotions(
    db: AsyncSession,
    *,
    active_only: bool = True,
    region: Optional[str] = None,
) -> List[Promotion]:
    q = select(Promotion).options(selectinload(Promotion.products))
    if active_only:
        q = q.where(Promotion.is_active == True)  # noqa
    if region:
        q = q.where(Promotion.region == region)
    result = await db.execute(q.order_by(Promotion.start_date.desc()))
    return list(result.scalars().all())


async def get_promotion(db: AsyncSession, promo_id: uuid.UUID) -> Optional[Promotion]:
    result = await db.execute(
        select(Promotion)
        .options(selectinload(Promotion.products).selectinload(PromotionProduct.product))
        .where(Promotion.id == promo_id)
    )
    return result.scalar_one_or_none()


async def create_promotion(db: AsyncSession, data: PromotionCreate) -> Promotion:
    prods_data = data.products
    promo = Promotion(**data.model_dump(exclude={"products"}))
    db.add(promo)
    await db.flush()
    for pd in prods_data:
        db.add(PromotionProduct(promotion_id=promo.id, **pd.model_dump()))
    await db.flush()
    await db.refresh(promo)
    return promo


async def update_promotion(db: AsyncSession, promo: Promotion, data: PromotionUpdate) -> Promotion:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(promo, k, v)
    await db.flush()
    await db.refresh(promo)
    return promo
