"""
CRUD operations for CompressorRecord.
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
    CompressorRecord,
    CompressorStatus,
    SourceMethod,
)
from app.schemas.compressor import (
    CompressorRecordCreate,
    CompressorRecordRead,
    CompressorRecordUpdate,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _gen_record_no(dt: datetime) -> str:
    d = dt.strftime("%Y%m%d") if dt else datetime.utcnow().strftime("%Y%m%d")
    return f"CPR-{d}-{random.randint(10000, 99999)}"


def _to_read(rec: CompressorRecord) -> CompressorRecordRead:
    r = CompressorRecordRead.model_validate(rec)
    if rec.asset:
        r.asset_name = rec.asset.name
        r.asset_no   = rec.asset.asset_no
    return r


# ── List ──────────────────────────────────────────────────────────────────────

async def list_compressor_records(
    db: AsyncSession,
    *,
    asset_id:         Optional[UUID] = None,
    department:       Optional[str]  = None,
    date_from:        Optional[date] = None,
    date_to:          Optional[date] = None,
    shift_ref:        Optional[str]  = None,
    prod_line:        Optional[str]  = None,
    is_anomaly:       Optional[bool] = None,
    maintenance_flag: Optional[bool] = None,
    leak_test_done:   Optional[bool] = None,
    status:           Optional[str]  = None,
    skip:  int = 0,
    limit: int = 200,
) -> List[CompressorRecordRead]:
    clauses = []
    if asset_id:
        clauses.append(CompressorRecord.asset_id == asset_id)
    if department:
        clauses.append(CompressorRecord.department == department)
    if shift_ref:
        clauses.append(CompressorRecord.shift_ref == shift_ref)
    if prod_line:
        clauses.append(CompressorRecord.production_line == prod_line)
    if date_from:
        clauses.append(
            CompressorRecord.record_datetime >= datetime.combine(date_from, datetime.min.time())
        )
    if date_to:
        clauses.append(
            CompressorRecord.record_datetime <= datetime.combine(date_to, datetime.max.time())
        )
    if is_anomaly is not None:
        clauses.append(CompressorRecord.is_anomaly == is_anomaly)
    if maintenance_flag is not None:
        clauses.append(CompressorRecord.maintenance_flag == maintenance_flag)
    if leak_test_done is not None:
        clauses.append(CompressorRecord.leak_test_done == leak_test_done)
    if status:
        try:
            clauses.append(CompressorRecord.status == CompressorStatus(status))
        except ValueError:
            pass

    q = (
        select(CompressorRecord)
        .options(selectinload(CompressorRecord.asset))
        .where(and_(*clauses) if clauses else True)
        .order_by(CompressorRecord.record_datetime.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = list((await db.execute(q)).scalars().all())
    return [_to_read(r) for r in rows]


# ── Get one ───────────────────────────────────────────────────────────────────

async def get_compressor_record(
    db: AsyncSession, record_id: UUID
) -> Optional[CompressorRecord]:
    q = (
        select(CompressorRecord)
        .options(selectinload(CompressorRecord.asset))
        .where(CompressorRecord.id == record_id)
    )
    return (await db.execute(q)).scalar_one_or_none()


# ── Create ────────────────────────────────────────────────────────────────────

async def create_compressor_record(
    db: AsyncSession,
    data: CompressorRecordCreate,
    created_by_id: Optional[UUID] = None,
) -> CompressorRecord:
    record_no = _gen_record_no(data.record_datetime)

    try:
        status = CompressorStatus(data.status)
    except ValueError:
        status = CompressorStatus.RUNNING

    try:
        source_method = SourceMethod(data.source_method)
    except ValueError:
        source_method = SourceMethod.MANUAL

    obj = CompressorRecord(
        record_no=record_no,
        asset_id=data.asset_id,
        record_datetime=data.record_datetime,
        shift_ref=data.shift_ref,
        department=data.department,
        production_line=data.production_line,
        period_hours=data.period_hours,
        air_generated_nm3=data.air_generated_nm3,
        air_unit=data.air_unit,
        electricity_used_kwh=data.electricity_used_kwh,
        runtime_hours=data.runtime_hours,
        load_time_hours=data.load_time_hours,
        unload_time_hours=data.unload_time_hours,
        idle_time_hours=data.idle_time_hours,
        inlet_pressure_bar=data.inlet_pressure_bar,
        discharge_pressure_bar=data.discharge_pressure_bar,
        system_pressure_bar=data.system_pressure_bar,
        receiver_tank_pressure_bar=data.receiver_tank_pressure_bar,
        line_pressure_bar=data.line_pressure_bar,
        flow_rate_m3h=data.flow_rate_m3h,
        power_kw=data.power_kw,
        specific_energy_kwh_m3=data.specific_energy_kwh_m3,
        load_pct=data.load_pct,
        running_hours_cumulative=data.running_hours_cumulative,
        loaded_hours_cumulative=data.loaded_hours_cumulative,
        air_temperature_c=data.air_temperature_c,
        dew_point_c=data.dew_point_c,
        pressure_dew_point_c=data.pressure_dew_point_c,
        dryer_status=data.dryer_status,
        dryer_dew_point_c=data.dryer_dew_point_c,
        oil_pressure_bar=data.oil_pressure_bar,
        oil_temp_c=data.oil_temp_c,
        filter_dp_bar=data.filter_dp_bar,
        oil_level=data.oil_level,
        leak_test_done=data.leak_test_done,
        leak_estimation_pct=data.leak_estimation_pct,
        leak_volume_nm3=data.leak_volume_nm3,
        night_idle_kwh=data.night_idle_kwh,
        night_idle_nm3=data.night_idle_nm3,
        start_stop_count=data.start_stop_count,
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

async def update_compressor_record(
    db: AsyncSession,
    obj: CompressorRecord,
    data: CompressorRecordUpdate,
) -> CompressorRecord:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value is not None:
            try:
                value = CompressorStatus(value)
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

async def delete_compressor_record(db: AsyncSession, obj: CompressorRecord) -> None:
    await db.delete(obj)
    await db.flush()
