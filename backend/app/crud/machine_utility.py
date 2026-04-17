"""
CRUD operations for MachineUtilityMapping and MachineConsumptionRecord.
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
    MachineConsumptionRecord,
    MachineUtilityMapping,
    SourceMethod,
    UtilityType,
)
from app.schemas.machine_utility import (
    MachineConsumptionRecordCreate,
    MachineConsumptionRecordRead,
    MachineConsumptionRecordUpdate,
    MachineUtilityMappingCreate,
    MachineUtilityMappingRead,
    MachineUtilityMappingUpdate,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _gen_record_no(dt: date) -> str:
    d = dt.strftime("%Y%m%d") if dt else datetime.utcnow().strftime("%Y%m%d")
    return f"MCR-{d}-{random.randint(10000, 99999)}"


def _mapping_to_read(obj: MachineUtilityMapping) -> MachineUtilityMappingRead:
    r = MachineUtilityMappingRead.model_validate(obj)
    r.utility_type = obj.utility_type.value if hasattr(obj.utility_type, "value") else str(obj.utility_type)
    if obj.device:
        r.device_name = obj.device.name
    return r


def _record_to_read(obj: MachineConsumptionRecord) -> MachineConsumptionRecordRead:
    r = MachineConsumptionRecordRead.model_validate(obj)
    r.utility_type  = obj.utility_type.value  if hasattr(obj.utility_type,  "value") else str(obj.utility_type)
    r.source_method = obj.source_method.value if hasattr(obj.source_method, "value") else str(obj.source_method)
    if obj.device:
        r.device_name = obj.device.name
    if obj.production_order:
        r.production_order_no = obj.production_order.order_no
    if obj.entered_by:
        r.entered_by_name = (
            getattr(obj.entered_by, "full_name", None)
            or getattr(obj.entered_by, "email", None)
        )
    return r


# ══════════════════════════════════════════════════════════════════════════════
# MachineUtilityMapping CRUD
# ══════════════════════════════════════════════════════════════════════════════

async def list_mappings(
    db: AsyncSession,
    *,
    machine_ref:     Optional[str]  = None,
    work_center_id:  Optional[UUID] = None,
    utility_type:    Optional[str]  = None,
    department:      Optional[str]  = None,
    production_line: Optional[str]  = None,
    is_active:       Optional[bool] = None,
    skip:  int = 0,
    limit: int = 200,
) -> List[MachineUtilityMappingRead]:
    clauses = []
    if machine_ref:
        clauses.append(MachineUtilityMapping.machine_ref == machine_ref)
    if work_center_id:
        clauses.append(MachineUtilityMapping.work_center_id == work_center_id)
    if department:
        clauses.append(MachineUtilityMapping.department == department)
    if production_line:
        clauses.append(MachineUtilityMapping.production_line == production_line)
    if utility_type:
        try:
            clauses.append(MachineUtilityMapping.utility_type == UtilityType(utility_type))
        except ValueError:
            pass
    if is_active is not None:
        clauses.append(MachineUtilityMapping.is_active == is_active)

    q = (
        select(MachineUtilityMapping)
        .options(selectinload(MachineUtilityMapping.device))
        .where(and_(*clauses) if clauses else True)
        .order_by(MachineUtilityMapping.machine_ref, MachineUtilityMapping.utility_type)
        .offset(skip).limit(limit)
    )
    rows = list((await db.execute(q)).scalars().all())
    return [_mapping_to_read(r) for r in rows]


async def get_mapping(db: AsyncSession, mapping_id: UUID) -> Optional[MachineUtilityMapping]:
    q = (
        select(MachineUtilityMapping)
        .options(selectinload(MachineUtilityMapping.device))
        .where(MachineUtilityMapping.id == mapping_id)
    )
    return (await db.execute(q)).scalar_one_or_none()


async def create_mapping(
    db: AsyncSession,
    data: MachineUtilityMappingCreate,
    created_by_id: Optional[UUID] = None,
) -> MachineUtilityMapping:
    try:
        utype = UtilityType(data.utility_type)
    except ValueError:
        utype = UtilityType.ELECTRICITY

    obj = MachineUtilityMapping(
        machine_ref=data.machine_ref,
        machine_name=data.machine_name,
        work_center_id=data.work_center_id,
        department=data.department,
        production_line=data.production_line,
        building_area=data.building_area,
        utility_type=utype,
        device_id=data.device_id,
        asset_id=data.asset_id,
        allocation_pct=data.allocation_pct,
        rated_consumption=data.rated_consumption,
        rated_unit=data.rated_unit,
        is_active=data.is_active,
        notes=data.notes,
        created_by_id=created_by_id,
    )
    db.add(obj)
    await db.flush()
    return obj


async def update_mapping(
    db: AsyncSession,
    obj: MachineUtilityMapping,
    data: MachineUtilityMappingUpdate,
) -> MachineUtilityMapping:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.flush()
    return obj


async def delete_mapping(db: AsyncSession, obj: MachineUtilityMapping) -> None:
    await db.delete(obj)
    await db.flush()


# ══════════════════════════════════════════════════════════════════════════════
# MachineConsumptionRecord CRUD
# ══════════════════════════════════════════════════════════════════════════════

async def list_consumption_records(
    db: AsyncSession,
    *,
    work_center_id:  Optional[UUID] = None,
    machine_ref:     Optional[str]  = None,
    utility_type:    Optional[str]  = None,
    production_line: Optional[str]  = None,
    department:      Optional[str]  = None,
    shift_ref:       Optional[str]  = None,
    date_from:       Optional[date] = None,
    date_to:         Optional[date] = None,
    batch_no:        Optional[str]  = None,
    production_order_id: Optional[UUID] = None,
    is_standby:      Optional[bool] = None,
    is_anomaly:      Optional[bool] = None,
    is_estimated:    Optional[bool] = None,
    skip:  int = 0,
    limit: int = 300,
) -> List[MachineConsumptionRecordRead]:
    clauses = []
    if work_center_id:
        clauses.append(MachineConsumptionRecord.work_center_id == work_center_id)
    if machine_ref:
        clauses.append(MachineConsumptionRecord.machine_ref == machine_ref)
    if utility_type:
        try:
            clauses.append(MachineConsumptionRecord.utility_type == UtilityType(utility_type))
        except ValueError:
            pass
    if production_line:
        clauses.append(MachineConsumptionRecord.production_line == production_line)
    if department:
        clauses.append(MachineConsumptionRecord.department == department)
    if shift_ref:
        clauses.append(MachineConsumptionRecord.shift_ref == shift_ref)
    if date_from:
        clauses.append(MachineConsumptionRecord.record_date >= date_from)
    if date_to:
        clauses.append(MachineConsumptionRecord.record_date <= date_to)
    if batch_no:
        clauses.append(MachineConsumptionRecord.batch_no == batch_no)
    if production_order_id:
        clauses.append(MachineConsumptionRecord.production_order_id == production_order_id)
    if is_standby is not None:
        clauses.append(MachineConsumptionRecord.is_standby == is_standby)
    if is_anomaly is not None:
        clauses.append(MachineConsumptionRecord.is_anomaly == is_anomaly)
    if is_estimated is not None:
        clauses.append(MachineConsumptionRecord.is_estimated == is_estimated)

    q = (
        select(MachineConsumptionRecord)
        .options(
            selectinload(MachineConsumptionRecord.device),
            selectinload(MachineConsumptionRecord.production_order),
            selectinload(MachineConsumptionRecord.entered_by),
        )
        .where(and_(*clauses) if clauses else True)
        .order_by(MachineConsumptionRecord.record_date.desc(), MachineConsumptionRecord.machine_ref)
        .offset(skip).limit(limit)
    )
    rows = list((await db.execute(q)).scalars().all())
    return [_record_to_read(r) for r in rows]


async def get_consumption_record(
    db: AsyncSession, record_id: UUID
) -> Optional[MachineConsumptionRecord]:
    q = (
        select(MachineConsumptionRecord)
        .options(
            selectinload(MachineConsumptionRecord.device),
            selectinload(MachineConsumptionRecord.production_order),
            selectinload(MachineConsumptionRecord.entered_by),
        )
        .where(MachineConsumptionRecord.id == record_id)
    )
    return (await db.execute(q)).scalar_one_or_none()


async def create_consumption_record(
    db: AsyncSession,
    data: MachineConsumptionRecordCreate,
    created_by_id: Optional[UUID] = None,
    machine_name: Optional[str] = None,
    machine_ref_code: Optional[str] = None,
) -> MachineConsumptionRecord:
    try:
        utype = UtilityType(data.utility_type)
    except ValueError:
        utype = UtilityType.ELECTRICITY

    try:
        source = SourceMethod(data.source_method)
    except ValueError:
        source = SourceMethod.MANUAL

    # Auto-compute variance_pct if possible
    variance_pct = None
    if (
        data.actual_consumption is not None
        and data.nominal_rate is not None
        and data.runtime_hours is not None
        and data.nominal_rate > 0
        and data.runtime_hours > 0
    ):
        expected = data.nominal_rate * data.runtime_hours
        if expected > 0:
            variance_pct = (data.actual_consumption - expected) / expected * 100

    # Auto-compute total_cost
    total_cost = data.total_cost
    if total_cost is None and data.actual_consumption is not None and data.cost_rate is not None:
        total_cost = data.actual_consumption * data.cost_rate

    obj = MachineConsumptionRecord(
        record_no=_gen_record_no(data.record_date),
        mapping_id=data.mapping_id,
        work_center_id=data.work_center_id,
        machine_ref=machine_ref_code or str(data.work_center_id),
        machine_name=machine_name,
        utility_type=utype,
        device_id=data.device_id,
        record_date=data.record_date,
        shift_ref=data.shift_ref,
        department=data.department,
        production_line=data.production_line,
        source_method=source,
        is_estimated=data.is_estimated,
        is_standby=data.is_standby,
        runtime_hours=data.runtime_hours,
        nominal_rate=data.nominal_rate,
        nominal_unit=data.nominal_unit,
        actual_consumption=data.actual_consumption,
        actual_unit=data.actual_unit,
        variance_pct=variance_pct,
        production_order_id=data.production_order_id,
        batch_no=data.batch_no,
        batch_lot_id=data.batch_lot_id,
        cost_rate=data.cost_rate,
        total_cost=total_cost,
        currency_code=data.currency_code or "USD",
        is_anomaly=data.is_anomaly,
        anomaly_note=data.anomaly_note,
        notes=data.notes,
        entered_by_id=created_by_id,
    )
    db.add(obj)
    await db.flush()
    return obj


async def update_consumption_record(
    db: AsyncSession,
    obj: MachineConsumptionRecord,
    data: MachineConsumptionRecordUpdate,
) -> MachineConsumptionRecord:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "source_method" and value is not None:
            try:
                value = SourceMethod(value)
            except ValueError:
                continue
        setattr(obj, field, value)
    # Recompute total_cost if cost_rate or consumption changed
    if obj.actual_consumption is not None and obj.cost_rate is not None:
        if "total_cost" not in update_data:
            obj.total_cost = obj.actual_consumption * obj.cost_rate
    await db.flush()
    return obj


async def delete_consumption_record(db: AsyncSession, obj: MachineConsumptionRecord) -> None:
    await db.delete(obj)
    await db.flush()
