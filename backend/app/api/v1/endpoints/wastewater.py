"""
Biological / Wastewater Treatment Endpoints
────────────────────────────────────────────────────────────────────────────
GET  /wastewater/kpis                    – aggregated KPIs + alarm flags
GET  /wastewater/trend/daily             – daily trend data
GET  /wastewater/trend/stage             – per-treatment-stage analysis
GET  /wastewater/compliance/summary      – compliance breakdown
GET  /wastewater/alarms/evaluate/{id}    – evaluate alarms for a record
GET  /wastewater/assets                  – WWTP asset dropdown
GET  /wastewater/records/export/csv      – CSV export
GET  /wastewater/records                 – list operational records (filters)
POST /wastewater/records                 – create record
GET  /wastewater/records/{id}            – get single record
PATCH/wastewater/records/{id}            – update record
DELETE/wastewater/records/{id}           – delete record
"""
from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.crud.wastewater import (
    create_wastewater_record,
    delete_wastewater_record,
    get_wastewater_record,
    list_wastewater_records,
    update_wastewater_record,
    _to_read,
)
from app.models.user import User
from app.models.utility_management import (
    UtilityAsset,
    UtilityType,
    WastewaterRecord,
)
from app.schemas.wastewater import (
    WastewaterAlarm,
    WastewaterAsset,
    WastewaterComplianceSummary,
    WastewaterKPIs,
    WastewaterRecordCreate,
    WastewaterRecordRead,
    WastewaterRecordUpdate,
    WastewaterStagePoint,
    WastewaterTrendPoint,
)
from app.services.wastewater_service import (
    evaluate_alarms,
    get_wastewater_compliance_summary,
    get_wastewater_daily_trend,
    get_wastewater_kpis,
    get_wastewater_stage_analysis,
)

router = APIRouter()


# ── KPIs & Analytics ──────────────────────────────────────────────────────────

@router.get("/kpis", response_model=WastewaterKPIs)
async def read_kpis(
    asset_id:      Optional[UUID] = Query(None),
    process_stage: Optional[str]  = Query(None),
    shift_ref:     Optional[str]  = Query(None),
    date_from:     Optional[date] = Query(None),
    date_to:       Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await get_wastewater_kpis(
        db,
        asset_id=asset_id,
        date_from=date_from,
        date_to=date_to,
        process_stage=process_stage,
        shift_ref=shift_ref,
    )


@router.get("/trend/daily", response_model=List[WastewaterTrendPoint])
async def read_daily_trend(
    asset_id:      Optional[UUID] = Query(None),
    process_stage: Optional[str]  = Query(None),
    date_from:     Optional[date] = Query(None),
    date_to:       Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await get_wastewater_daily_trend(
        db,
        asset_id=asset_id,
        date_from=date_from,
        date_to=date_to,
        process_stage=process_stage,
    )


@router.get("/trend/stage", response_model=List[WastewaterStagePoint])
async def read_stage_analysis(
    asset_id:  Optional[UUID] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await get_wastewater_stage_analysis(
        db, asset_id=asset_id, date_from=date_from, date_to=date_to,
    )


@router.get("/compliance/summary", response_model=WastewaterComplianceSummary)
async def read_compliance_summary(
    asset_id:  Optional[UUID] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await get_wastewater_compliance_summary(
        db, asset_id=asset_id, date_from=date_from, date_to=date_to,
    )


@router.get("/alarms/evaluate/{record_id}", response_model=List[WastewaterAlarm])
async def evaluate_record_alarms(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Evaluate alarm thresholds for a stored record and return triggered alarms."""
    obj = await get_wastewater_record(db, record_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Wastewater record not found")
    return evaluate_alarms(obj)


# ── Assets dropdown ────────────────────────────────────────────────────────────

@router.get("/assets", response_model=List[WastewaterAsset])
async def list_wastewater_assets(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = list((await db.execute(
        select(UtilityAsset)
        .where(UtilityAsset.utility_type == UtilityType.WASTEWATER)
        .where(UtilityAsset.is_active == True)
        .order_by(UtilityAsset.asset_no)
    )).scalars().all())
    return [WastewaterAsset(id=a.id, asset_no=a.asset_no, name=a.name) for a in rows]


# ── Records CRUD ──────────────────────────────────────────────────────────────

@router.get("/records/export/csv")
async def export_records_csv(
    asset_id:          Optional[UUID] = Query(None),
    date_from:         Optional[date] = Query(None),
    date_to:           Optional[date] = Query(None),
    process_stage:     Optional[str]  = Query(None),
    compliance_status: Optional[str]  = Query(None),
    shift_ref:         Optional[str]  = Query(None),
    is_anomaly:        Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    records = await list_wastewater_records(
        db,
        asset_id=asset_id, date_from=date_from, date_to=date_to,
        process_stage=process_stage, compliance_status=compliance_status,
        shift_ref=shift_ref, is_anomaly=is_anomaly, skip=0, limit=10000,
    )
    buf = io.StringIO()
    fields = [
        "record_no", "asset_no", "asset_name", "record_datetime",
        "process_stage", "shift_ref", "operator_id",
        "influent_flow_m3h", "effluent_flow_m3h",
        "influent_ph", "effluent_ph",
        "influent_cod_mgl", "effluent_cod_mgl",
        "influent_bod_mgl", "effluent_bod_mgl",
        "influent_tss_mgl", "effluent_tss_mgl",
        "conductivity_us_cm", "temperature_c",
        "do_mgl", "mlss_mgl", "mlvss_mgl", "svi", "srt_days",
        "aeration_runtime_hours", "blower_power_kw", "power_consumed_kwh",
        "nutrient_dose_kg", "antifoam_dose_kg",
        "sludge_produced_kg", "sludge_volume_m3", "sludge_disposal_qty_kg",
        "compliance_status", "permit_limit_ref", "deviation_reason", "corrective_action",
        "is_anomaly", "anomaly_note", "notes",
    ]
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for rec in records:
        writer.writerow(rec.model_dump())
    buf.seek(0)
    return StreamingResponse(
        iter([buf.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=wastewater_records.csv"},
    )


@router.get("/records", response_model=List[WastewaterRecordRead])
async def list_records(
    asset_id:          Optional[UUID] = Query(None),
    date_from:         Optional[date] = Query(None),
    date_to:           Optional[date] = Query(None),
    process_stage:     Optional[str]  = Query(None),
    compliance_status: Optional[str]  = Query(None),
    shift_ref:         Optional[str]  = Query(None),
    is_anomaly:        Optional[bool] = Query(None),
    skip:  int = Query(0, ge=0),
    limit: int = Query(200, le=1000),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await list_wastewater_records(
        db,
        asset_id=asset_id, date_from=date_from, date_to=date_to,
        process_stage=process_stage, compliance_status=compliance_status,
        shift_ref=shift_ref, is_anomaly=is_anomaly, skip=skip, limit=limit,
    )


@router.post("/records", response_model=WastewaterRecordRead, status_code=status.HTTP_201_CREATED)
async def create_record(
    data: WastewaterRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    obj = await create_wastewater_record(db, data, created_by_id=current_user.id)
    await db.commit()
    await db.refresh(obj)
    # Alarm evaluation (log; persistence hook can be added here)
    alarms = evaluate_alarms(obj)
    if alarms:
        logger_names = [a.alarm_key for a in alarms]
        import logging
        logging.getLogger(__name__).warning(
            "Wastewater alarms triggered on record %s: %s",
            obj.record_no, logger_names,
        )
    return _to_read(obj)


@router.get("/records/{record_id}", response_model=WastewaterRecordRead)
async def get_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    obj = await get_wastewater_record(db, record_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Wastewater record not found")
    return _to_read(obj)


@router.patch("/records/{record_id}", response_model=WastewaterRecordRead)
async def update_record(
    record_id: UUID,
    data: WastewaterRecordUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    obj = await get_wastewater_record(db, record_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Wastewater record not found")
    obj = await update_wastewater_record(db, obj, data)
    await db.commit()
    await db.refresh(obj)
    return _to_read(obj)


@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    obj = await get_wastewater_record(db, record_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Wastewater record not found")
    await delete_wastewater_record(db, obj)
    await db.commit()
