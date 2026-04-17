"""
Machine Utility Consumption Mapping — API Endpoints
────────────────────────────────────────────────────
Prefix: /machine-utility

── Mapping master ──────────────────────────────────────────────────────────────
GET  /mappings                  list machine↔meter config entries
POST /mappings                  create mapping entry
GET  /mappings/{id}             get single mapping
PATCH/mappings/{id}             update mapping
DELETE/mappings/{id}            delete mapping

── Consumption records ──────────────────────────────────────────────────────────
GET  /records/export/csv        CSV export
GET  /records                   list consumption records (filters)
POST /records                   create consumption record
GET  /records/{id}              get single record
PATCH/records/{id}              update record
DELETE/records/{id}             delete record

── Analytics ────────────────────────────────────────────────────────────────────
GET  /kpis                      aggregated KPIs
GET  /trend/daily               daily trend per machine/utility
GET  /breakdown                 consumption breakdown by dimension

── Dropdowns ────────────────────────────────────────────────────────────────────
GET  /work-centers              WorkCenter dropdown (machines/lines)
GET  /devices                   UtilityDevice dropdown (meters)
GET  /production-orders         ProductionOrder dropdown (recent)
"""
from __future__ import annotations

import csv
import io
from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.crud.machine_utility import (
    create_mapping,
    create_consumption_record,
    delete_mapping,
    delete_consumption_record,
    get_mapping,
    get_consumption_record,
    list_mappings,
    list_consumption_records,
    update_mapping,
    update_consumption_record,
    _record_to_read,
    _mapping_to_read,
)
from app.models.user import User
from app.models.utility_management import (
    MachineConsumptionRecord,
    MachineUtilityMapping,
    UtilityDevice,
    UtilityType,
)
from app.models.production_advanced import WorkCenter
from app.models.production import ProductionOrder
from app.schemas.machine_utility import (
    MachineConsumptionRecordCreate,
    MachineConsumptionRecordRead,
    MachineConsumptionRecordUpdate,
    MachineUtilityBreakdown,
    MachineUtilityKPIs,
    MachineUtilityMappingCreate,
    MachineUtilityMappingRead,
    MachineUtilityMappingUpdate,
    MachineUtilityTrendPoint,
    MappingDropdown,
    WorkCenterDropdown,
)
from app.services.machine_utility_service import (
    get_machine_utility_breakdown,
    get_machine_utility_kpis,
    get_machine_utility_trend,
)

router = APIRouter()


# ── Dropdowns ─────────────────────────────────────────────────────────────────

@router.get("/work-centers", response_model=List[WorkCenterDropdown])
async def list_work_center_dropdown(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = list((await db.execute(
        select(WorkCenter).order_by(WorkCenter.work_center_id)
    )).scalars().all())
    return [
        WorkCenterDropdown(
            id=wc.id,
            work_center_id=wc.work_center_id,
            name=wc.name,
            department=wc.department,
            type=wc.type.value if hasattr(wc.type, "value") else str(wc.type),
        )
        for wc in rows
    ]


@router.get("/devices", response_model=List[dict])
async def list_device_dropdown(
    utility_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    clauses = [UtilityDevice.is_active == True]
    if utility_type:
        try:
            clauses.append(UtilityDevice.utility_type == UtilityType(utility_type))
        except ValueError:
            pass
    rows = list((await db.execute(
        select(UtilityDevice)
        .where(and_(*clauses))
        .order_by(UtilityDevice.device_code)
        .limit(500)
    )).scalars().all())
    return [{"id": str(d.id), "device_code": d.device_code, "name": d.name,
             "utility_type": d.utility_type.value if hasattr(d.utility_type, "value") else str(d.utility_type),
             "unit_of_measure": d.unit_of_measure} for d in rows]


@router.get("/production-orders", response_model=List[dict])
async def list_production_order_dropdown(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = list((await db.execute(
        select(ProductionOrder)
        .order_by(ProductionOrder.scheduled_start.desc())
        .limit(200)
    )).scalars().all())
    return [{"id": str(o.id), "order_no": o.order_no, "batch_no": o.batch_no,
             "status": o.status.value if hasattr(o.status, "value") else str(o.status)} for o in rows]


@router.get("/mappings/dropdown", response_model=List[MappingDropdown])
async def list_mapping_dropdown(
    work_center_id: Optional[UUID] = Query(None),
    utility_type:   Optional[str]  = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    clauses = [MachineUtilityMapping.is_active == True]
    if work_center_id:
        clauses.append(MachineUtilityMapping.work_center_id == work_center_id)
    if utility_type:
        try:
            clauses.append(MachineUtilityMapping.utility_type == UtilityType(utility_type))
        except ValueError:
            pass
    rows = list((await db.execute(
        select(MachineUtilityMapping).where(and_(*clauses))
        .order_by(MachineUtilityMapping.machine_ref)
    )).scalars().all())
    return [
        MappingDropdown(
            id=m.id,
            machine_ref=m.machine_ref,
            machine_name=m.machine_name,
            utility_type=m.utility_type.value if hasattr(m.utility_type, "value") else str(m.utility_type),
            rated_consumption=m.rated_consumption,
            rated_unit=m.rated_unit,
        )
        for m in rows
    ]


# ── Mapping master CRUD ────────────────────────────────────────────────────────

@router.get("/mappings", response_model=List[MachineUtilityMappingRead])
async def list_mappings_endpoint(
    machine_ref:     Optional[str]  = Query(None),
    work_center_id:  Optional[UUID] = Query(None),
    utility_type:    Optional[str]  = Query(None),
    department:      Optional[str]  = Query(None),
    production_line: Optional[str]  = Query(None),
    is_active:       Optional[bool] = Query(None),
    skip:  int = Query(0, ge=0),
    limit: int = Query(200, le=1000),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await list_mappings(
        db,
        machine_ref=machine_ref, work_center_id=work_center_id,
        utility_type=utility_type, department=department,
        production_line=production_line, is_active=is_active,
        skip=skip, limit=limit,
    )


@router.post("/mappings", response_model=MachineUtilityMappingRead, status_code=status.HTTP_201_CREATED)
async def create_mapping_endpoint(
    data: MachineUtilityMappingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    obj = await create_mapping(db, data, created_by_id=current_user.id)
    await db.commit()
    await db.refresh(obj)
    return _mapping_to_read(obj)


@router.get("/mappings/{mapping_id}", response_model=MachineUtilityMappingRead)
async def get_mapping_endpoint(
    mapping_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    obj = await get_mapping(db, mapping_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Machine utility mapping not found")
    return _mapping_to_read(obj)


@router.patch("/mappings/{mapping_id}", response_model=MachineUtilityMappingRead)
async def update_mapping_endpoint(
    mapping_id: UUID,
    data: MachineUtilityMappingUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    obj = await get_mapping(db, mapping_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Machine utility mapping not found")
    obj = await update_mapping(db, obj, data)
    await db.commit()
    await db.refresh(obj)
    return _mapping_to_read(obj)


@router.delete("/mappings/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mapping_endpoint(
    mapping_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    obj = await get_mapping(db, mapping_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Machine utility mapping not found")
    await delete_mapping(db, obj)
    await db.commit()


# ── Consumption records CRUD ───────────────────────────────────────────────────

@router.get("/records/export/csv")
async def export_records_csv(
    work_center_id:  Optional[UUID] = Query(None),
    machine_ref:     Optional[str]  = Query(None),
    utility_type:    Optional[str]  = Query(None),
    production_line: Optional[str]  = Query(None),
    department:      Optional[str]  = Query(None),
    shift_ref:       Optional[str]  = Query(None),
    date_from:       Optional[date] = Query(None),
    date_to:         Optional[date] = Query(None),
    batch_no:        Optional[str]  = Query(None),
    is_standby:      Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    records = await list_consumption_records(
        db,
        work_center_id=work_center_id, machine_ref=machine_ref,
        utility_type=utility_type, production_line=production_line,
        department=department, shift_ref=shift_ref,
        date_from=date_from, date_to=date_to,
        batch_no=batch_no, is_standby=is_standby,
        skip=0, limit=10000,
    )
    buf = io.StringIO()
    fields = [
        "record_no", "machine_ref", "machine_name", "utility_type",
        "record_date", "shift_ref", "department", "production_line",
        "source_method", "is_estimated", "is_standby",
        "runtime_hours", "nominal_rate", "nominal_unit",
        "actual_consumption", "actual_unit", "variance_pct",
        "production_order_no", "batch_no",
        "cost_rate", "total_cost", "currency_code",
        "is_anomaly", "notes",
    ]
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for rec in records:
        writer.writerow(rec.model_dump())
    buf.seek(0)
    return StreamingResponse(
        iter([buf.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=machine_consumption.csv"},
    )


@router.get("/records", response_model=List[MachineConsumptionRecordRead])
async def list_records_endpoint(
    work_center_id:  Optional[UUID] = Query(None),
    machine_ref:     Optional[str]  = Query(None),
    utility_type:    Optional[str]  = Query(None),
    production_line: Optional[str]  = Query(None),
    department:      Optional[str]  = Query(None),
    shift_ref:       Optional[str]  = Query(None),
    date_from:       Optional[date] = Query(None),
    date_to:         Optional[date] = Query(None),
    batch_no:        Optional[str]  = Query(None),
    production_order_id: Optional[UUID] = Query(None),
    is_standby:      Optional[bool] = Query(None),
    is_anomaly:      Optional[bool] = Query(None),
    is_estimated:    Optional[bool] = Query(None),
    skip:  int = Query(0, ge=0),
    limit: int = Query(300, le=1000),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await list_consumption_records(
        db,
        work_center_id=work_center_id, machine_ref=machine_ref,
        utility_type=utility_type, production_line=production_line,
        department=department, shift_ref=shift_ref,
        date_from=date_from, date_to=date_to,
        batch_no=batch_no, production_order_id=production_order_id,
        is_standby=is_standby, is_anomaly=is_anomaly, is_estimated=is_estimated,
        skip=skip, limit=limit,
    )


@router.post("/records", response_model=MachineConsumptionRecordRead, status_code=status.HTTP_201_CREATED)
async def create_record_endpoint(
    data: MachineConsumptionRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Resolve machine_ref and machine_name from WorkCenter
    wc = (await db.execute(
        select(WorkCenter).where(WorkCenter.id == data.work_center_id)
    )).scalar_one_or_none()
    if not wc:
        raise HTTPException(status_code=422, detail="work_center_id not found in work_centers table")

    obj = await create_consumption_record(
        db, data,
        created_by_id=current_user.id,
        machine_name=wc.name,
        machine_ref_code=wc.work_center_id,
    )
    await db.commit()
    await db.refresh(obj)
    return _record_to_read(obj)


@router.get("/records/{record_id}", response_model=MachineConsumptionRecordRead)
async def get_record_endpoint(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    obj = await get_consumption_record(db, record_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Machine consumption record not found")
    return _record_to_read(obj)


@router.patch("/records/{record_id}", response_model=MachineConsumptionRecordRead)
async def update_record_endpoint(
    record_id: UUID,
    data: MachineConsumptionRecordUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    obj = await get_consumption_record(db, record_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Machine consumption record not found")
    obj = await update_consumption_record(db, obj, data)
    await db.commit()
    await db.refresh(obj)
    return _record_to_read(obj)


@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_record_endpoint(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    obj = await get_consumption_record(db, record_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Machine consumption record not found")
    await delete_consumption_record(db, obj)
    await db.commit()


# ── Analytics ─────────────────────────────────────────────────────────────────

@router.get("/kpis", response_model=MachineUtilityKPIs)
async def read_kpis(
    work_center_id:  Optional[UUID] = Query(None),
    machine_ref:     Optional[str]  = Query(None),
    utility_type:    Optional[str]  = Query(None),
    production_line: Optional[str]  = Query(None),
    department:      Optional[str]  = Query(None),
    shift_ref:       Optional[str]  = Query(None),
    date_from:       Optional[date] = Query(None),
    date_to:         Optional[date] = Query(None),
    batch_no:        Optional[str]  = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await get_machine_utility_kpis(
        db,
        work_center_id=work_center_id, machine_ref=machine_ref,
        utility_type=utility_type, production_line=production_line,
        department=department, shift_ref=shift_ref,
        date_from=date_from, date_to=date_to, batch_no=batch_no,
    )


@router.get("/trend/daily", response_model=List[MachineUtilityTrendPoint])
async def read_daily_trend(
    work_center_id:  Optional[UUID] = Query(None),
    machine_ref:     Optional[str]  = Query(None),
    utility_type:    Optional[str]  = Query(None),
    production_line: Optional[str]  = Query(None),
    date_from:       Optional[date] = Query(None),
    date_to:         Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await get_machine_utility_trend(
        db,
        work_center_id=work_center_id, machine_ref=machine_ref,
        utility_type=utility_type, production_line=production_line,
        date_from=date_from, date_to=date_to,
    )


@router.get("/breakdown", response_model=MachineUtilityBreakdown)
async def read_breakdown(
    dimension:      str            = Query("machine"),
    work_center_id: Optional[UUID] = Query(None),
    utility_type:   Optional[str]  = Query(None),
    date_from:      Optional[date] = Query(None),
    date_to:        Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await get_machine_utility_breakdown(
        db,
        dimension=dimension, work_center_id=work_center_id,
        utility_type=utility_type, date_from=date_from, date_to=date_to,
    )
