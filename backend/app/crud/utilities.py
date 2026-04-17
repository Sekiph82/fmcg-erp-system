from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
import uuid

from app.models.utilities import SystemConfig, UomConversion, NumberSeries, Currency
from app.schemas.utilities import (
    SystemConfigCreate, SystemConfigUpdate,
    UomConversionCreate, UomConversionUpdate,
    NumberSeriesCreate, NumberSeriesUpdate,
    CurrencyCreate, CurrencyUpdate,
)


# ── SystemConfig ───────────────────────────────────────────────────────────────

async def list_configs(db: AsyncSession, category: Optional[str] = None, skip=0, limit=100) -> List[SystemConfig]:
    q = select(SystemConfig)
    if category:
        q = q.where(SystemConfig.category == category)
    result = await db.execute(q.order_by(SystemConfig.category, SystemConfig.key).offset(skip).limit(limit))
    return list(result.scalars().all())


async def get_config(db: AsyncSession, config_id: uuid.UUID) -> Optional[SystemConfig]:
    result = await db.execute(select(SystemConfig).where(SystemConfig.id == config_id))
    return result.scalar_one_or_none()


async def get_config_by_key(db: AsyncSession, key: str) -> Optional[SystemConfig]:
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    return result.scalar_one_or_none()


async def create_config(db: AsyncSession, data: SystemConfigCreate, user_id: Optional[uuid.UUID] = None) -> SystemConfig:
    obj = SystemConfig(**data.model_dump(), updated_by_id=user_id)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_config(db: AsyncSession, obj: SystemConfig, data: SystemConfigUpdate, user_id: Optional[uuid.UUID] = None) -> SystemConfig:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    obj.updated_by_id = user_id
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_config(db: AsyncSession, obj: SystemConfig) -> None:
    await db.delete(obj)
    await db.flush()


# ── UomConversion ──────────────────────────────────────────────────────────────

async def list_conversions(db: AsyncSession, skip=0, limit=100) -> List[UomConversion]:
    result = await db.execute(select(UomConversion).order_by(UomConversion.from_uom, UomConversion.to_uom).offset(skip).limit(limit))
    return list(result.scalars().all())


async def get_conversion(db: AsyncSession, conversion_id: uuid.UUID) -> Optional[UomConversion]:
    result = await db.execute(select(UomConversion).where(UomConversion.id == conversion_id))
    return result.scalar_one_or_none()


async def get_conversion_pair(db: AsyncSession, from_uom: str, to_uom: str) -> Optional[UomConversion]:
    result = await db.execute(
        select(UomConversion).where(UomConversion.from_uom == from_uom, UomConversion.to_uom == to_uom)
    )
    return result.scalar_one_or_none()


async def create_conversion(db: AsyncSession, data: UomConversionCreate, user_id: Optional[uuid.UUID] = None) -> UomConversion:
    obj = UomConversion(**data.model_dump(), created_by_id=user_id)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_conversion(db: AsyncSession, obj: UomConversion, data: UomConversionUpdate) -> UomConversion:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_conversion(db: AsyncSession, obj: UomConversion) -> None:
    await db.delete(obj)
    await db.flush()


# ── NumberSeries ───────────────────────────────────────────────────────────────

async def list_series(db: AsyncSession, skip=0, limit=100) -> List[NumberSeries]:
    result = await db.execute(select(NumberSeries).order_by(NumberSeries.module).offset(skip).limit(limit))
    return list(result.scalars().all())


async def get_series(db: AsyncSession, series_id: uuid.UUID) -> Optional[NumberSeries]:
    result = await db.execute(select(NumberSeries).where(NumberSeries.id == series_id))
    return result.scalar_one_or_none()


async def get_series_by_module(db: AsyncSession, module: str) -> Optional[NumberSeries]:
    result = await db.execute(select(NumberSeries).where(NumberSeries.module == module))
    return result.scalar_one_or_none()


async def create_series(db: AsyncSession, data: NumberSeriesCreate) -> NumberSeries:
    obj = NumberSeries(**data.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_series(db: AsyncSession, obj: NumberSeries, data: NumberSeriesUpdate) -> NumberSeries:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_series(db: AsyncSession, obj: NumberSeries) -> None:
    await db.delete(obj)
    await db.flush()


# ── Currency ───────────────────────────────────────────────────────────────────

async def list_currencies(db: AsyncSession, skip=0, limit=100) -> List[Currency]:
    result = await db.execute(select(Currency).order_by(Currency.code).offset(skip).limit(limit))
    return list(result.scalars().all())


async def get_currency(db: AsyncSession, currency_id: uuid.UUID) -> Optional[Currency]:
    result = await db.execute(select(Currency).where(Currency.id == currency_id))
    return result.scalar_one_or_none()


async def get_currency_by_code(db: AsyncSession, code: str) -> Optional[Currency]:
    result = await db.execute(select(Currency).where(Currency.code == code.upper()))
    return result.scalar_one_or_none()


async def get_base_currency(db: AsyncSession) -> Optional[Currency]:
    result = await db.execute(select(Currency).where(Currency.is_base == True))  # noqa: E712
    return result.scalar_one_or_none()


async def create_currency(db: AsyncSession, data: CurrencyCreate) -> Currency:
    obj = Currency(**data.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_currency(db: AsyncSession, obj: Currency, data: CurrencyUpdate) -> Currency:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_currency(db: AsyncSession, obj: Currency) -> None:
    await db.delete(obj)
    await db.flush()
