"""
CRUD operations for SoftWaterRecord.
"""
from __future__ import annotations

import random
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.utility_management import SoftWaterRecord, SoftenerStatus, SourceMethod
from app.schemas.water import SoftWaterRecordCreate, SoftWaterRecordRead, SoftWaterRecordUpdate


# ── Helpers ───────────────────────────────────────────────────────────────────


def _gen_record_no(record_datetime: datetime) -> str:
    d = record_datetime.strftime("%Y%m%d") if record_datetime else datetime.utcnow().strftime("%Y%m%d")
    return f"SW-{d}-{random.randint(10000, 99999)}"


def _to_read(rec: SoftWaterRecord) -> SoftWaterRecordRead:
    asset_name = rec.asset.name if rec.asset else None
    asset_no   = rec.asset.asset_no if rec.asset else None
    d = SoftWaterRecordRead.model_validate(rec)
    d.asset_name = asset_name
    d.asset_no   = asset_no
    return d


# ── List ──────────────────────────────────────────────────────────────────────


async def list_soft_water_records(
    db: AsyncSession,
    *,
    asset_id:         Optional[UUID] = None,
    department:       Optional[str]  = None,
    date_from:        Optional[date] = None,
    date_to:          Optional[date] = None,
    shift_ref:        Optional[str]  = None,
    is_anomaly:       Optional[bool] = None,
    maintenance_flag: Optional[bool] = None,
    status:           Optional[str]  = None,
    skip:  int = 0,
    limit: int = 200,
) -> List[SoftWaterRecordRead]:
    clauses = []
    if asset_id:
        clauses.append(SoftWaterRecord.asset_id == asset_id)
    if department:
        clauses.append(SoftWaterRecord.department == department)
    if date_from:
        clauses.append(SoftWaterRecord.record_datetime >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        clauses.append(SoftWaterRecord.record_datetime <= datetime.combine(date_to, datetime.max.time()))
    if shift_ref:
        clauses.append(SoftWaterRecord.shift_ref == shift_ref)
    if is_anomaly is not None:
        clauses.append(SoftWaterRecord.is_anomaly == is_anomaly)
    if maintenance_flag is not None:
        clauses.append(SoftWaterRecord.maintenance_flag == maintenance_flag)
    if status:
        try:
            clauses.append(SoftWaterRecord.status == SoftenerStatus(status))
        except ValueError:
            pass

    q = (
        select(SoftWaterRecord)
        .options(selectinload(SoftWaterRecord.asset))
        .where(and_(*clauses) if clauses else True)
        .order_by(SoftWaterRecord.record_datetime.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = list((await db.execute(q)).scalars().all())
    return [_to_read(r) for r in rows]


# ── Get one ───────────────────────────────────────────────────────────────────


async def get_soft_water_record(db: AsyncSession, record_id: UUID) -> Optional[SoftWaterRecord]:
    q = (
        select(SoftWaterRecord)
        .options(selectinload(SoftWaterRecord.asset))
        .where(SoftWaterRecord.id == record_id)
    )
    return (await db.execute(q)).scalar_one_or_none()


# ── Create ────────────────────────────────────────────────────────────────────


async def create_soft_water_record(
    db: AsyncSession,
    data: SoftWaterRecordCreate,
    created_by_id: Optional[UUID] = None,
) -> SoftWaterRecord:
    record_no = _gen_record_no(data.record_datetime)

    try:
        status = SoftenerStatus(data.status)
    except ValueError:
        status = SoftenerStatus.ONLINE

    try:
        source_method = SourceMethod(data.source_method)
    except ValueError:
        source_method = SourceMethod.MANUAL

    obj = SoftWaterRecord(
        record_no=record_no,
        asset_id=data.asset_id,
        record_datetime=data.record_datetime,
        feed_water_hardness_ppm=data.feed_water_hardness_ppm,
        product_water_hardness_ppm=data.product_water_hardness_ppm,
        feed_water_tds_ppm=data.feed_water_tds_ppm,
        product_water_tds_ppm=data.product_water_tds_ppm,
        feed_ph=data.feed_ph,
        product_ph=data.product_ph,
        conductivity_feed_uscm=data.conductivity_feed_uscm,
        conductivity_product_uscm=data.conductivity_product_uscm,
        flow_rate_lpm=data.flow_rate_lpm,
        volume_treated_m3=data.volume_treated_m3,
        raw_water_input_m3=data.raw_water_input_m3,
        salt_consumed_kg=data.salt_consumed_kg,
        resin_volume_litres=data.resin_volume_litres,
        regen_start=data.regen_start,
        regen_end=data.regen_end,
        regeneration_count=data.regeneration_count,
        service_run_hours=data.service_run_hours,
        efficiency_pct=data.efficiency_pct,
        status=status,
        downtime_minutes=data.downtime_minutes,
        maintenance_flag=data.maintenance_flag,
        destination_tag=data.destination_tag,
        department=data.department,
        source_method=source_method,
        is_anomaly=data.is_anomaly,
        anomaly_note=data.anomaly_note,
        shift_ref=data.shift_ref,
        notes=data.notes,
        entered_by_id=created_by_id,
    )
    db.add(obj)
    await db.flush()
    return obj


# ── Update ────────────────────────────────────────────────────────────────────


async def update_soft_water_record(
    db: AsyncSession,
    obj: SoftWaterRecord,
    data: SoftWaterRecordUpdate,
) -> SoftWaterRecord:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value is not None:
            try:
                value = SoftenerStatus(value)
            except ValueError:
                continue
        if field == "source_method" and value is not None:
            try:
                value = SourceMethod(value)
            except ValueError:
                continue
        setattr(obj, field, value)
    await db.flush()
    return obj


# ── Delete ────────────────────────────────────────────────────────────────────


async def delete_soft_water_record(db: AsyncSession, obj: SoftWaterRecord) -> None:
    await db.delete(obj)
    await db.flush()
