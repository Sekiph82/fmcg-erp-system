"""
CRUD operations for WastewaterRecord.
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
    ComplianceStatus,
    SourceMethod,
    WastewaterProcess,
    WastewaterRecord,
)
from app.schemas.wastewater import (
    WastewaterRecordCreate,
    WastewaterRecordRead,
    WastewaterRecordUpdate,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _gen_record_no(dt: datetime) -> str:
    d = dt.strftime("%Y%m%d") if dt else datetime.utcnow().strftime("%Y%m%d")
    return f"WWT-{d}-{random.randint(10000, 99999)}"


def _to_read(rec: WastewaterRecord) -> WastewaterRecordRead:
    r = WastewaterRecordRead.model_validate(rec)
    if rec.asset:
        r.asset_name = rec.asset.name
        r.asset_no   = rec.asset.asset_no
    r.operator_id = rec.entered_by_id
    if rec.entered_by:
        r.operator_name = getattr(rec.entered_by, "full_name", None) or getattr(rec.entered_by, "email", None)
    # map process_stage enum → str
    if hasattr(rec.process_stage, "value"):
        r.process_stage = rec.process_stage.value
    # map compliance_status enum → str
    if hasattr(rec.compliance_status, "value"):
        r.compliance_status = rec.compliance_status.value
    r.source_method = rec.source_method.value if hasattr(rec.source_method, "value") else str(rec.source_method)
    return r


# ── List ──────────────────────────────────────────────────────────────────────

async def list_wastewater_records(
    db: AsyncSession,
    *,
    asset_id:          Optional[UUID] = None,
    date_from:         Optional[date] = None,
    date_to:           Optional[date] = None,
    process_stage:     Optional[str]  = None,
    compliance_status: Optional[str]  = None,
    shift_ref:         Optional[str]  = None,
    is_anomaly:        Optional[bool] = None,
    skip:  int = 0,
    limit: int = 200,
) -> List[WastewaterRecordRead]:
    clauses = []
    if asset_id:
        clauses.append(WastewaterRecord.asset_id == asset_id)
    if shift_ref:
        clauses.append(WastewaterRecord.shift_ref == shift_ref)
    if date_from:
        clauses.append(
            WastewaterRecord.record_datetime >= datetime.combine(date_from, datetime.min.time())
        )
    if date_to:
        clauses.append(
            WastewaterRecord.record_datetime <= datetime.combine(date_to, datetime.max.time())
        )
    if process_stage:
        try:
            clauses.append(WastewaterRecord.process_stage == WastewaterProcess(process_stage))
        except ValueError:
            pass
    if compliance_status:
        try:
            clauses.append(WastewaterRecord.compliance_status == ComplianceStatus(compliance_status))
        except ValueError:
            pass
    if is_anomaly is not None:
        clauses.append(WastewaterRecord.is_anomaly == is_anomaly)

    q = (
        select(WastewaterRecord)
        .options(
            selectinload(WastewaterRecord.asset),
            selectinload(WastewaterRecord.entered_by),
        )
        .where(and_(*clauses) if clauses else True)
        .order_by(WastewaterRecord.record_datetime.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = list((await db.execute(q)).scalars().all())
    return [_to_read(r) for r in rows]


# ── Get one ───────────────────────────────────────────────────────────────────

async def get_wastewater_record(
    db: AsyncSession, record_id: UUID
) -> Optional[WastewaterRecord]:
    q = (
        select(WastewaterRecord)
        .options(
            selectinload(WastewaterRecord.asset),
            selectinload(WastewaterRecord.entered_by),
        )
        .where(WastewaterRecord.id == record_id)
    )
    return (await db.execute(q)).scalar_one_or_none()


# ── Create ────────────────────────────────────────────────────────────────────

async def create_wastewater_record(
    db: AsyncSession,
    data: WastewaterRecordCreate,
    created_by_id: Optional[UUID] = None,
) -> WastewaterRecord:
    record_no = _gen_record_no(data.record_datetime)

    try:
        stage = WastewaterProcess(data.process_stage)
    except ValueError:
        stage = WastewaterProcess.SECONDARY

    try:
        compliance = ComplianceStatus(data.compliance_status)
    except ValueError:
        compliance = ComplianceStatus.COMPLIANT

    try:
        source = SourceMethod(data.source_method)
    except ValueError:
        source = SourceMethod.MANUAL

    obj = WastewaterRecord(
        record_no=record_no,
        asset_id=data.asset_id,
        record_datetime=data.record_datetime,
        process_stage=stage,
        shift_ref=data.shift_ref,

        influent_flow_m3h=data.influent_flow_m3h,
        effluent_flow_m3h=data.effluent_flow_m3h,

        influent_cod_mgl=data.influent_cod_mgl,
        effluent_cod_mgl=data.effluent_cod_mgl,
        influent_bod_mgl=data.influent_bod_mgl,
        effluent_bod_mgl=data.effluent_bod_mgl,
        influent_tss_mgl=data.influent_tss_mgl,
        effluent_tss_mgl=data.effluent_tss_mgl,

        influent_ph=data.influent_ph,
        effluent_ph=data.effluent_ph,

        do_mgl=data.do_mgl,
        mlss_mgl=data.mlss_mgl,
        mlvss_mgl=data.mlvss_mgl,
        svi=data.svi,
        srt_days=data.srt_days,

        conductivity_us_cm=data.conductivity_us_cm,
        temperature_c=data.temperature_c,

        power_consumed_kwh=data.power_consumed_kwh,
        aeration_runtime_hours=data.aeration_runtime_hours,
        blower_power_kw=data.blower_power_kw,

        nutrient_dose_kg=data.nutrient_dose_kg,
        antifoam_dose_kg=data.antifoam_dose_kg,

        sludge_produced_kg=data.sludge_produced_kg,
        sludge_dewatered_pct=data.sludge_dewatered_pct,
        sludge_volume_m3=data.sludge_volume_m3,
        sludge_disposal_qty_kg=data.sludge_disposal_qty_kg,

        compliance_status=compliance,
        permit_limit_ref=data.permit_limit_ref,
        deviation_reason=data.deviation_reason,
        corrective_action=data.corrective_action,

        source_method=source,
        is_anomaly=data.is_anomaly,
        anomaly_note=data.anomaly_note,
        notes=data.notes,

        entered_by_id=data.operator_id or created_by_id,
    )
    db.add(obj)
    await db.flush()
    return obj


# ── Update ────────────────────────────────────────────────────────────────────

async def update_wastewater_record(
    db: AsyncSession,
    obj: WastewaterRecord,
    data: WastewaterRecordUpdate,
) -> WastewaterRecord:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "process_stage" and value is not None:
            try:
                value = WastewaterProcess(value)
            except ValueError:
                continue
        elif field == "compliance_status" and value is not None:
            try:
                value = ComplianceStatus(value)
            except ValueError:
                continue
        elif field == "source_method" and value is not None:
            try:
                value = SourceMethod(value)
            except ValueError:
                continue
        setattr(obj, field, value)
    await db.flush()
    return obj


# ── Delete ────────────────────────────────────────────────────────────────────

async def delete_wastewater_record(db: AsyncSession, obj: WastewaterRecord) -> None:
    await db.delete(obj)
    await db.flush()
