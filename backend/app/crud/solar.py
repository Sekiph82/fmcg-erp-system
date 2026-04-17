"""
CRUD operations for SolarRecord.
"""
from __future__ import annotations

import random
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.utility_management import SolarRecord, SourceMethod
from app.schemas.solar import SolarRecordCreate, SolarRecordRead, SolarRecordUpdate


# ── Helpers ───────────────────────────────────────────────────────────────────

def _gen_record_no(dt: datetime) -> str:
    d = dt.strftime("%Y%m%d") if dt else datetime.utcnow().strftime("%Y%m%d")
    return f"SOL-{d}-{random.randint(10000, 99999)}"


def _to_read(rec: SolarRecord) -> SolarRecordRead:
    r = SolarRecordRead.model_validate(rec)
    if rec.asset:
        r.asset_name = rec.asset.name
        r.asset_no   = rec.asset.asset_no
    return r


# ── List ──────────────────────────────────────────────────────────────────────

async def list_solar_records(
    db: AsyncSession,
    *,
    asset_id:   Optional[UUID] = None,
    date_from:  Optional[date] = None,
    date_to:    Optional[date] = None,
    is_anomaly: Optional[bool] = None,
    skip:  int = 0,
    limit: int = 200,
) -> List[SolarRecordRead]:
    clauses = []
    if asset_id:
        clauses.append(SolarRecord.asset_id == asset_id)
    if date_from:
        clauses.append(
            SolarRecord.record_datetime >= datetime.combine(date_from, datetime.min.time())
        )
    if date_to:
        clauses.append(
            SolarRecord.record_datetime <= datetime.combine(date_to, datetime.max.time())
        )
    if is_anomaly is not None:
        clauses.append(SolarRecord.is_anomaly == is_anomaly)

    q = (
        select(SolarRecord)
        .options(selectinload(SolarRecord.asset))
        .where(and_(*clauses) if clauses else True)
        .order_by(SolarRecord.record_datetime.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = list((await db.execute(q)).scalars().all())
    return [_to_read(r) for r in rows]


# ── Get one ───────────────────────────────────────────────────────────────────

async def get_solar_record(
    db: AsyncSession, record_id: UUID
) -> Optional[SolarRecord]:
    q = (
        select(SolarRecord)
        .options(selectinload(SolarRecord.asset))
        .where(SolarRecord.id == record_id)
    )
    return (await db.execute(q)).scalar_one_or_none()


# ── Create ────────────────────────────────────────────────────────────────────

async def create_solar_record(
    db: AsyncSession,
    data: SolarRecordCreate,
    created_by_id: Optional[UUID] = None,
) -> SolarRecord:
    record_no = _gen_record_no(data.record_datetime)

    try:
        source_method = SourceMethod(data.source_method)
    except ValueError:
        source_method = SourceMethod.IOT

    obj = SolarRecord(
        record_no=record_no,
        asset_id=data.asset_id,
        record_datetime=data.record_datetime,
        irradiance_wm2=data.irradiance_wm2,
        panel_temp_c=data.panel_temp_c,
        ambient_temp_c=data.ambient_temp_c,
        dc_voltage_v=data.dc_voltage_v,
        dc_current_a=data.dc_current_a,
        dc_power_kw=data.dc_power_kw,
        ac_power_kw=data.ac_power_kw,
        energy_generated_kwh=data.energy_generated_kwh,
        grid_export_kwh=data.grid_export_kwh,
        self_consumption_kwh=data.self_consumption_kwh,
        inverter_efficiency_pct=data.inverter_efficiency_pct,
        pr_ratio=data.pr_ratio,
        availability_pct=data.availability_pct,
        capacity_factor_pct=data.capacity_factor_pct,
        source_method=source_method,
        is_anomaly=data.is_anomaly,
        anomaly_note=data.anomaly_note,
        notes=data.notes,
        entered_by_id=created_by_id,
    )
    db.add(obj)
    await db.flush()
    return obj


# ── Update ────────────────────────────────────────────────────────────────────

async def update_solar_record(
    db: AsyncSession,
    obj: SolarRecord,
    data: SolarRecordUpdate,
) -> SolarRecord:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "source_method" and value is not None:
            try:
                value = SourceMethod(value)
            except ValueError:
                continue
        setattr(obj, field, value)
    await db.flush()
    return obj


# ── Delete ────────────────────────────────────────────────────────────────────

async def delete_solar_record(db: AsyncSession, obj: SolarRecord) -> None:
    await db.delete(obj)
    await db.flush()
