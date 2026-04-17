"""
CRUD operations for BoilerSteamRecord.
"""
from __future__ import annotations

import random
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.utility_management import (
    BoilerSteamRecord,
    BoilerStatus,
    SourceMethod,
)
from app.schemas.steam import BoilerRecordCreate, BoilerRecordRead, BoilerRecordUpdate


# ── Helpers ───────────────────────────────────────────────────────────────────

def _gen_record_no(dt: datetime) -> str:
    d = dt.strftime("%Y%m%d") if dt else datetime.utcnow().strftime("%Y%m%d")
    return f"BLR-{d}-{random.randint(10000, 99999)}"


def _to_read(rec: BoilerSteamRecord) -> BoilerRecordRead:
    d = BoilerRecordRead.model_validate(rec)
    if rec.asset:
        d.asset_name = rec.asset.name
        d.asset_no   = rec.asset.asset_no
    return d


# ── List ──────────────────────────────────────────────────────────────────────

async def list_boiler_records(
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
) -> List[BoilerRecordRead]:
    clauses = []
    if asset_id:
        clauses.append(BoilerSteamRecord.asset_id == asset_id)
    if department:
        clauses.append(BoilerSteamRecord.department == department)
    if date_from:
        clauses.append(
            BoilerSteamRecord.record_datetime >= datetime.combine(date_from, datetime.min.time())
        )
    if date_to:
        clauses.append(
            BoilerSteamRecord.record_datetime <= datetime.combine(date_to, datetime.max.time())
        )
    if shift_ref:
        clauses.append(BoilerSteamRecord.shift_ref == shift_ref)
    if is_anomaly is not None:
        clauses.append(BoilerSteamRecord.is_anomaly == is_anomaly)
    if maintenance_flag is not None:
        clauses.append(BoilerSteamRecord.maintenance_flag == maintenance_flag)
    if status:
        try:
            clauses.append(BoilerSteamRecord.status == BoilerStatus(status))
        except ValueError:
            pass

    q = (
        select(BoilerSteamRecord)
        .options(selectinload(BoilerSteamRecord.asset))
        .where(and_(*clauses) if clauses else True)
        .order_by(BoilerSteamRecord.record_datetime.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = list((await db.execute(q)).scalars().all())
    return [_to_read(r) for r in rows]


# ── Get one ───────────────────────────────────────────────────────────────────

async def get_boiler_record(
    db: AsyncSession, record_id: UUID
) -> Optional[BoilerSteamRecord]:
    q = (
        select(BoilerSteamRecord)
        .options(selectinload(BoilerSteamRecord.asset))
        .where(BoilerSteamRecord.id == record_id)
    )
    return (await db.execute(q)).scalar_one_or_none()


# ── Create ────────────────────────────────────────────────────────────────────

async def create_boiler_record(
    db: AsyncSession,
    data: BoilerRecordCreate,
    created_by_id: Optional[UUID] = None,
) -> BoilerSteamRecord:
    record_no = _gen_record_no(data.record_datetime)

    try:
        status = BoilerStatus(data.status)
    except ValueError:
        status = BoilerStatus.RUNNING

    try:
        source_method = SourceMethod(data.source_method)
    except ValueError:
        source_method = SourceMethod.MANUAL

    obj = BoilerSteamRecord(
        record_no=record_no,
        asset_id=data.asset_id,
        record_datetime=data.record_datetime,
        shift_ref=data.shift_ref,
        department=data.department,
        period_hours=data.period_hours,
        steam_pressure_bar=data.steam_pressure_bar,
        steam_temp_c=data.steam_temp_c,
        steam_flow_kgh=data.steam_flow_kgh,
        steam_quality_pct=data.steam_quality_pct,
        steam_generated_kg=data.steam_generated_kg,
        feedwater_consumed_m3=data.feedwater_consumed_m3,
        condensate_returned_m3=data.condensate_returned_m3,
        feed_water_temp_c=data.feed_water_temp_c,
        feed_water_flow_lpm=data.feed_water_flow_lpm,
        feed_water_ph=data.feed_water_ph,
        feed_water_tds_ppm=data.feed_water_tds_ppm,
        blowdown_pct=data.blowdown_pct,
        blowdown_volume_litres=data.blowdown_volume_litres,
        fuel_type=data.fuel_type,
        fuel_consumption=data.fuel_consumption,
        fuel_unit=data.fuel_unit,
        boiler_efficiency_pct=data.boiler_efficiency_pct,
        flue_gas_temp_c=data.flue_gas_temp_c,
        o2_pct=data.o2_pct,
        co2_pct=data.co2_pct,
        co_ppm=data.co_ppm,
        boiler_tds_ppm=data.boiler_tds_ppm,
        boiler_ph=data.boiler_ph,
        boiler_hardness_ppm=data.boiler_hardness_ppm,
        conductivity_uscm=data.conductivity_uscm,
        boiler_load_pct=data.boiler_load_pct,
        burner_runtime_hours=data.burner_runtime_hours,
        start_stop_count=data.start_stop_count,
        running_hours_cumulative=data.running_hours_cumulative,
        chemical_dosing_amount=data.chemical_dosing_amount,
        chemical_dosing_unit=data.chemical_dosing_unit,
        downtime_minutes=data.downtime_minutes,
        downtime_reason=data.downtime_reason,
        maintenance_flag=data.maintenance_flag,
        status=status,
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

async def update_boiler_record(
    db: AsyncSession,
    obj: BoilerSteamRecord,
    data: BoilerRecordUpdate,
) -> BoilerSteamRecord:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value is not None:
            try:
                value = BoilerStatus(value)
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

async def delete_boiler_record(db: AsyncSession, obj: BoilerSteamRecord) -> None:
    await db.delete(obj)
    await db.flush()
