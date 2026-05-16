from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import date
import uuid

from app.models.esg import (
    ActivityData, EmissionFactor, EmissionRecord, ResourceMetric, ESGTarget,
    SourceType, EmissionScope, ESGMetricType,
)
from app.schemas.esg import (
    ActivityCreate, EmissionFactorCreate, EmissionFactorUpdate,
    ResourceMetricCreate, ESGTargetCreate,
)


# ── Emission Factors ──────────────────────────────────────────────────────────

async def list_factors(
    db: AsyncSession,
    source_type: Optional[SourceType] = None,
    is_active: Optional[bool] = None,
    limit: int = 500,
    offset: int = 0,
) -> List[EmissionFactor]:
    q = select(EmissionFactor).order_by(EmissionFactor.source_type, EmissionFactor.valid_from.desc())
    if source_type:
        q = q.where(EmissionFactor.source_type == source_type)
    if is_active is not None:
        q = q.where(EmissionFactor.is_active == is_active)
    result = await db.execute(q.offset(offset).limit(min(limit, 1000)))
    return list(result.scalars().all())


async def get_factor(db: AsyncSession, factor_id: uuid.UUID) -> Optional[EmissionFactor]:
    result = await db.execute(select(EmissionFactor).where(EmissionFactor.id == factor_id))
    return result.scalar_one_or_none()


async def get_active_factor(
    db: AsyncSession,
    source_type: SourceType,
    region: str = "KE",
    as_of: Optional[date] = None,
) -> Optional[EmissionFactor]:
    ref_date = as_of or date.today()
    q = (
        select(EmissionFactor)
        .where(
            EmissionFactor.source_type == source_type,
            EmissionFactor.region == region,
            EmissionFactor.is_active == True,  # noqa: E712
            EmissionFactor.valid_from <= ref_date,
        )
        .where(
            (EmissionFactor.valid_to.is_(None)) | (EmissionFactor.valid_to >= ref_date)
        )
        .order_by(EmissionFactor.valid_from.desc())
    )
    result = await db.execute(q)
    return result.scalars().first()


async def create_factor(db: AsyncSession, data: EmissionFactorCreate) -> EmissionFactor:
    obj = EmissionFactor(**data.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_factor(
    db: AsyncSession, obj: EmissionFactor, data: EmissionFactorUpdate
) -> EmissionFactor:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj


# ── Activity Data ─────────────────────────────────────────────────────────────

async def list_activities(
    db: AsyncSession,
    source_type: Optional[SourceType] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    location_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 200,
) -> List[ActivityData]:
    q = (
        select(ActivityData)
        .options(
            selectinload(ActivityData.location),
            selectinload(ActivityData.supplier),
            selectinload(ActivityData.emission_records),
        )
        .order_by(ActivityData.activity_date.desc())
    )
    if source_type:
        q = q.where(ActivityData.source_type == source_type)
    if date_from:
        q = q.where(ActivityData.activity_date >= date_from)
    if date_to:
        q = q.where(ActivityData.activity_date <= date_to)
    if location_id:
        q = q.where(ActivityData.location_id == location_id)
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_activity(
    db: AsyncSession, data: ActivityCreate, user_id: Optional[uuid.UUID] = None,
    is_auto_imported: bool = False,
) -> ActivityData:
    obj = ActivityData(**data.model_dump(), created_by=user_id, is_auto_imported=is_auto_imported)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_activity(db: AsyncSession, activity_id: uuid.UUID) -> Optional[ActivityData]:
    result = await db.execute(
        select(ActivityData)
        .where(ActivityData.id == activity_id)
        .options(
            selectinload(ActivityData.location),
            selectinload(ActivityData.supplier),
            selectinload(ActivityData.emission_records).selectinload(EmissionRecord.factor),
        )
    )
    return result.scalar_one_or_none()


# ── Emission Records ──────────────────────────────────────────────────────────

async def list_emission_records(
    db: AsyncSession,
    scope: Optional[EmissionScope] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    skip: int = 0,
    limit: int = 500,
) -> List[EmissionRecord]:
    q = (
        select(EmissionRecord)
        .options(
            selectinload(EmissionRecord.activity).selectinload(ActivityData.location),
            selectinload(EmissionRecord.factor),
        )
        .order_by(EmissionRecord.calculated_at.desc())
    )
    if scope:
        q = q.where(EmissionRecord.scope == scope)
    if date_from:
        q = q.join(ActivityData, EmissionRecord.activity_id == ActivityData.id).where(ActivityData.activity_date >= date_from)
    if date_to:
        q = q.join(ActivityData, EmissionRecord.activity_id == ActivityData.id).where(ActivityData.activity_date <= date_to)
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_emission_record(db: AsyncSession, record: EmissionRecord) -> EmissionRecord:
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


# ── Resource Metrics ──────────────────────────────────────────────────────────

async def list_metrics(
    db: AsyncSession,
    metric_type: Optional[ESGMetricType] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    skip: int = 0,
    limit: int = 200,
) -> List[ResourceMetric]:
    q = (
        select(ResourceMetric)
        .options(selectinload(ResourceMetric.location))
        .order_by(ResourceMetric.period_from.desc())
    )
    if metric_type:
        q = q.where(ResourceMetric.metric_type == metric_type)
    if date_from:
        q = q.where(ResourceMetric.period_from >= date_from)
    if date_to:
        q = q.where(ResourceMetric.period_to <= date_to)
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_metric(
    db: AsyncSession, data: ResourceMetricCreate, user_id: Optional[uuid.UUID] = None
) -> ResourceMetric:
    obj = ResourceMetric(**data.model_dump(), created_by=user_id)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


# ── ESG Targets ───────────────────────────────────────────────────────────────

async def list_targets(
    db: AsyncSession,
    is_active: Optional[bool] = None,
    limit: int = 200,
    offset: int = 0,
) -> List[ESGTarget]:
    q = select(ESGTarget).order_by(ESGTarget.target_date)
    if is_active is not None:
        q = q.where(ESGTarget.is_active == is_active)
    result = await db.execute(q.offset(offset).limit(min(limit, 1000)))
    return list(result.scalars().all())


async def create_target(db: AsyncSession, data: ESGTargetCreate) -> ESGTarget:
    obj = ESGTarget(**data.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_target(db: AsyncSession, target_id: uuid.UUID) -> Optional[ESGTarget]:
    result = await db.execute(select(ESGTarget).where(ESGTarget.id == target_id))
    return result.scalar_one_or_none()
