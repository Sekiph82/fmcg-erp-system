from __future__ import annotations
from datetime import date
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.tax_regulatory import (
    CountryTaxConfig, TaxCategory, TaxRule,
    ProductTaxMapping, RegulatoryFlag, TransactionTax,
    TaxAppliesTo, TxTaxStatus,
)
from app.schemas.tax_regulatory import (
    CountryTaxConfigCreate, CountryTaxConfigUpdate,
    TaxCategoryCreate, TaxCategoryUpdate,
    TaxRuleCreate, TaxRuleUpdate,
    ProductTaxMappingCreate, ProductTaxMappingUpdate,
    RegulatoryFlagCreate, RegulatoryFlagUpdate,
    TransactionTaxCreate, TransactionTaxUpdate,
)


# ── Country Tax Config ─────────────────────────────────────────────────────────

async def list_country_configs(db: AsyncSession, limit: int = 300) -> List[CountryTaxConfig]:
    result = await db.execute(select(CountryTaxConfig).order_by(CountryTaxConfig.country_code).limit(min(limit, 1000)))
    return list(result.scalars().all())


async def get_country_config(db: AsyncSession, country_code: str) -> Optional[CountryTaxConfig]:
    result = await db.execute(
        select(CountryTaxConfig).where(CountryTaxConfig.country_code == country_code)
    )
    return result.scalar_one_or_none()


async def create_country_config(db: AsyncSession, data: CountryTaxConfigCreate) -> CountryTaxConfig:
    obj = CountryTaxConfig(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def update_country_config(
    db: AsyncSession, country_code: str, data: CountryTaxConfigUpdate
) -> Optional[CountryTaxConfig]:
    obj = await get_country_config(db, country_code)
    if not obj:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


# ── Tax Category ───────────────────────────────────────────────────────────────

async def list_categories(db: AsyncSession, limit: int = 300) -> List[TaxCategory]:
    result = await db.execute(select(TaxCategory).order_by(TaxCategory.code).limit(min(limit, 1000)))
    return list(result.scalars().all())


async def get_category(db: AsyncSession, category_id: UUID) -> Optional[TaxCategory]:
    result = await db.execute(select(TaxCategory).where(TaxCategory.id == category_id))
    return result.scalar_one_or_none()


async def create_category(db: AsyncSession, data: TaxCategoryCreate) -> TaxCategory:
    obj = TaxCategory(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def update_category(
    db: AsyncSession, category_id: UUID, data: TaxCategoryUpdate
) -> Optional[TaxCategory]:
    obj = await get_category(db, category_id)
    if not obj:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


# ── Tax Rules ──────────────────────────────────────────────────────────────────

async def list_rules(
    db: AsyncSession, country_code: Optional[str] = None, limit: int = 200, offset: int = 0
) -> List[TaxRule]:
    q = select(TaxRule).options(selectinload(TaxRule.category)).order_by(TaxRule.country_code)
    if country_code:
        q = q.where(TaxRule.country_code == country_code)
    result = await db.execute(q.offset(offset).limit(min(limit, 1000)))
    return list(result.scalars().all())


async def get_rule(db: AsyncSession, rule_id: UUID) -> Optional[TaxRule]:
    result = await db.execute(
        select(TaxRule).options(selectinload(TaxRule.category)).where(TaxRule.id == rule_id)
    )
    return result.scalar_one_or_none()


async def create_rule(db: AsyncSession, data: TaxRuleCreate) -> TaxRule:
    obj = TaxRule(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return await get_rule(db, obj.id)


async def update_rule(
    db: AsyncSession, rule_id: UUID, data: TaxRuleUpdate
) -> Optional[TaxRule]:
    obj = await get_rule(db, rule_id)
    if not obj:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    await db.commit()
    return await get_rule(db, rule_id)


# ── Product Tax Mapping ────────────────────────────────────────────────────────

async def list_mappings(
    db: AsyncSession,
    country_code: Optional[str] = None,
    product_id: Optional[UUID] = None,
    material_id: Optional[UUID] = None,
    limit: int = 200,
    offset: int = 0,
) -> List[ProductTaxMapping]:
    q = select(ProductTaxMapping).options(selectinload(ProductTaxMapping.category))
    if country_code:
        q = q.where(ProductTaxMapping.country_code == country_code)
    if product_id:
        q = q.where(ProductTaxMapping.product_id == product_id)
    if material_id:
        q = q.where(ProductTaxMapping.material_id == material_id)
    result = await db.execute(q.offset(offset).limit(min(limit, 1000)))
    return list(result.scalars().all())


async def create_mapping(db: AsyncSession, data: ProductTaxMappingCreate) -> ProductTaxMapping:
    obj = ProductTaxMapping(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def update_mapping(
    db: AsyncSession, mapping_id: UUID, data: ProductTaxMappingUpdate
) -> Optional[ProductTaxMapping]:
    result = await db.execute(select(ProductTaxMapping).where(ProductTaxMapping.id == mapping_id))
    obj = result.scalar_one_or_none()
    if not obj:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


async def delete_mapping(db: AsyncSession, mapping_id: UUID) -> bool:
    result = await db.execute(select(ProductTaxMapping).where(ProductTaxMapping.id == mapping_id))
    obj = result.scalar_one_or_none()
    if not obj:
        return False
    await db.delete(obj)
    await db.commit()
    return True


# ── Regulatory Flags ───────────────────────────────────────────────────────────

async def list_flags(
    db: AsyncSession,
    country_code: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> List[RegulatoryFlag]:
    q = select(RegulatoryFlag).order_by(RegulatoryFlag.country_code, RegulatoryFlag.flag_type)
    if country_code:
        q = q.where(RegulatoryFlag.country_code == country_code)
    if status:
        q = q.where(RegulatoryFlag.status == status)
    result = await db.execute(q.offset(offset).limit(min(limit, 1000)))
    return list(result.scalars().all())


async def get_flag(db: AsyncSession, flag_id: UUID) -> Optional[RegulatoryFlag]:
    result = await db.execute(select(RegulatoryFlag).where(RegulatoryFlag.id == flag_id))
    return result.scalar_one_or_none()


async def create_flag(db: AsyncSession, data: RegulatoryFlagCreate) -> RegulatoryFlag:
    obj = RegulatoryFlag(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def update_flag(
    db: AsyncSession, flag_id: UUID, data: RegulatoryFlagUpdate
) -> Optional[RegulatoryFlag]:
    obj = await get_flag(db, flag_id)
    if not obj:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


async def delete_flag(db: AsyncSession, flag_id: UUID) -> bool:
    obj = await get_flag(db, flag_id)
    if not obj:
        return False
    await db.delete(obj)
    await db.commit()
    return True


# ── Transaction Tax ────────────────────────────────────────────────────────────

async def list_transaction_taxes(
    db: AsyncSession,
    entity_type: Optional[str] = None,
    entity_id: Optional[UUID] = None,
    country_code: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> List[TransactionTax]:
    q = select(TransactionTax).order_by(TransactionTax.created_at.desc())
    if entity_type:
        q = q.where(TransactionTax.entity_type == entity_type)
    if entity_id:
        q = q.where(TransactionTax.entity_id == entity_id)
    if country_code:
        q = q.where(TransactionTax.country_code == country_code)
    result = await db.execute(q.offset(offset).limit(min(limit, 1000)))
    return list(result.scalars().all())


async def get_transaction_tax(db: AsyncSession, tax_id: UUID) -> Optional[TransactionTax]:
    result = await db.execute(select(TransactionTax).where(TransactionTax.id == tax_id))
    return result.scalar_one_or_none()


async def create_transaction_tax(
    db: AsyncSession, data: TransactionTaxCreate, created_by_id: Optional[UUID] = None
) -> TransactionTax:
    obj = TransactionTax(**data.model_dump(), created_by_id=created_by_id)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def update_transaction_tax(
    db: AsyncSession, tax_id: UUID, data: TransactionTaxUpdate
) -> Optional[TransactionTax]:
    obj = await get_transaction_tax(db, tax_id)
    if not obj:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


async def bulk_post_transaction_taxes(
    db: AsyncSession, entity_type: str, entity_id: UUID
) -> int:
    """Mark all CONFIRMED taxes on an entity as POSTED."""
    result = await db.execute(
        select(TransactionTax).where(
            and_(
                TransactionTax.entity_type == entity_type,
                TransactionTax.entity_id == entity_id,
                TransactionTax.status == TxTaxStatus.CONFIRMED,
            )
        )
    )
    taxes = list(result.scalars().all())
    for t in taxes:
        t.status = TxTaxStatus.POSTED
    await db.commit()
    return len(taxes)
