"""
Soft Water Management API
─────────────────────────
Prefix: /soft-water (registered in router.py)

Analytics:
  GET  /soft-water/kpis            – softener KPI block
  GET  /soft-water/trend/daily     – daily trend

Records CRUD:
  GET  /soft-water/records         – filtered list
  GET  /soft-water/records/export/csv
  GET  /soft-water/records/{id}    – single record
  POST /soft-water/records         – create
  PATCH /soft-water/records/{id}   – update
  DELETE /soft-water/records/{id}  – delete

Assets (for UI dropdown):
  GET  /soft-water/assets          – utility assets with utility_type = SOFT_WATER
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_permission
from app.db.session import get_db
from app.crud.soft_water import (
    create_soft_water_record,
    delete_soft_water_record,
    get_soft_water_record,
    list_soft_water_records,
    update_soft_water_record,
)
from app.models.utility_management import (
    SoftWaterRecord,
    UtilityAsset,
    UtilityType,
)
from app.models.user import User
from app.schemas.water import (
    SoftWaterKPIs,
    SoftWaterRecordCreate,
    SoftWaterRecordRead,
    SoftWaterRecordUpdate,
    SoftWaterTrendPoint,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_PERM = "utility_management"


# ── Analytics ─────────────────────────────────────────────────────────────────


@router.get("/kpis", response_model=SoftWaterKPIs)
async def soft_water_kpis(
    date_from:    Optional[date] = Query(None),
    date_to:      Optional[date] = Query(None),
    asset_id:     Optional[UUID] = Query(None),
    department:   Optional[str]  = Query(None),
    shift_ref:    Optional[str]  = Query(None),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    """Aggregated KPIs from soft_water_records."""
    clauses = []
    if asset_id:
        clauses.append(SoftWaterRecord.asset_id == asset_id)
    if department:
        clauses.append(SoftWaterRecord.department == department)
    if shift_ref:
        clauses.append(SoftWaterRecord.shift_ref == shift_ref)
    if date_from:
        clauses.append(SoftWaterRecord.record_datetime >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        clauses.append(SoftWaterRecord.record_datetime <= datetime.combine(date_to, datetime.max.time()))

    where = and_(*clauses) if clauses else True

    from sqlalchemy import Integer, cast

    agg = (await db.execute(
        select(
            func.sum(SoftWaterRecord.volume_treated_m3).label("total_vol"),
            func.sum(SoftWaterRecord.raw_water_input_m3).label("total_raw"),
            func.sum(SoftWaterRecord.salt_consumed_kg).label("total_salt"),
            func.sum(SoftWaterRecord.regeneration_count).label("regen_count"),
            func.avg(SoftWaterRecord.efficiency_pct).label("avg_eff"),
            func.avg(SoftWaterRecord.downtime_minutes).label("avg_downtime"),
            func.avg(SoftWaterRecord.feed_water_hardness_ppm).label("avg_feed_hard"),
            func.avg(SoftWaterRecord.product_water_hardness_ppm).label("avg_prod_hard"),
            func.count().label("record_count"),
            func.sum(cast(SoftWaterRecord.is_anomaly, Integer)).label("anomaly_count"),
            func.sum(cast(SoftWaterRecord.maintenance_flag, Integer)).label("maintenance_count"),
        ).where(where)
    )).one()

    def _d(v) -> Decimal:
        return Decimal(str(v)) if v is not None else Decimal("0")

    total_vol  = _d(agg.total_vol)
    total_raw  = _d(agg.total_raw)
    total_salt = _d(agg.total_salt)
    regen_count = int(agg.regen_count or 0)
    record_count = int(agg.record_count or 0)
    anomaly_count = int(agg.anomaly_count or 0)
    maintenance_count = int(agg.maintenance_count or 0)

    avg_eff = Decimal(str(round(agg.avg_eff, 3))) if agg.avg_eff is not None else None
    avg_downtime = Decimal(str(round(agg.avg_downtime, 1))) if agg.avg_downtime is not None else None

    salt_per_m3 = (total_salt / total_vol) if total_vol > 0 else None
    loss_ratio  = (
        Decimal(str(round((total_raw - total_vol) / total_raw * 100, 2)))
        if total_raw > 0 else None
    )

    avg_feed_hard = _d(agg.avg_feed_hard)
    avg_prod_hard = _d(agg.avg_prod_hard)
    hardness_removal_pct = (
        Decimal(str(round((1 - avg_prod_hard / avg_feed_hard) * 100, 2)))
        if avg_feed_hard > 0 else None
    )

    # Compliance: product hardness ≤ 50 ppm (WHO drinking water guideline)
    compliance_pct = None
    if record_count > 0:
        compliant = (await db.execute(
            select(func.count()).where(
                and_(where, SoftWaterRecord.product_water_hardness_ppm <= 50)
            )
        )).scalar()
        compliance_pct = Decimal(str(round((compliant or 0) / record_count * 100, 2)))

    # Regeneration frequency (regens per day)
    regen_frequency = None
    if date_from and date_to:
        days = max(1, (date_to - date_from).days + 1)
        regen_frequency = Decimal(str(round(regen_count / days, 4))) if regen_count else None

    return SoftWaterKPIs(
        date_from=date_from,
        date_to=date_to,
        total_volume_m3=total_vol,
        total_raw_input_m3=total_raw,
        total_salt_kg=total_salt,
        conversion_eff_pct=avg_eff,
        salt_per_m3=salt_per_m3,
        regen_count=regen_count,
        regen_frequency=regen_frequency,
        hardness_removal_pct=hardness_removal_pct,
        loss_ratio=loss_ratio,
        compliance_pct=compliance_pct,
        record_count=record_count,
        anomaly_count=anomaly_count,
        maintenance_count=maintenance_count,
        avg_downtime_min=avg_downtime,
    )


@router.get("/trend/daily", response_model=List[SoftWaterTrendPoint])
async def soft_water_daily_trend(
    date_from:  Optional[date] = Query(None),
    date_to:    Optional[date] = Query(None),
    asset_id:   Optional[UUID] = Query(None),
    department: Optional[str]  = Query(None),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    """Daily aggregation of soft water volume, salt, and efficiency."""
    from sqlalchemy import Integer, cast, func
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID

    clauses = []
    if asset_id:
        clauses.append(SoftWaterRecord.asset_id == asset_id)
    if department:
        clauses.append(SoftWaterRecord.department == department)
    if date_from:
        clauses.append(SoftWaterRecord.record_datetime >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        clauses.append(SoftWaterRecord.record_datetime <= datetime.combine(date_to, datetime.max.time()))

    where = and_(*clauses) if clauses else True

    from sqlalchemy import func as F
    rows = list((await db.execute(
        select(
            func.date(SoftWaterRecord.record_datetime).label("day"),
            func.sum(SoftWaterRecord.volume_treated_m3).label("vol"),
            func.sum(SoftWaterRecord.salt_consumed_kg).label("salt"),
            func.avg(SoftWaterRecord.efficiency_pct).label("avg_eff"),
            func.sum(SoftWaterRecord.regeneration_count).label("regen"),
            func.sum(cast(SoftWaterRecord.is_anomaly, Integer)).label("anomaly"),
            func.sum(cast(SoftWaterRecord.maintenance_flag, Integer)).label("maint"),
            func.count().label("cnt"),
        )
        .where(where)
        .group_by(func.date(SoftWaterRecord.record_datetime))
        .order_by(func.date(SoftWaterRecord.record_datetime))
    )).all())

    def _d(v) -> Decimal:
        return Decimal(str(v)) if v is not None else Decimal("0")

    return [
        SoftWaterTrendPoint(
            date=r.day,
            volume_treated_m3=_d(r.vol),
            salt_consumed_kg=_d(r.salt),
            avg_efficiency_pct=Decimal(str(round(r.avg_eff, 3))) if r.avg_eff else None,
            regen_count=int(r.regen or 0),
            anomaly_count=int(r.anomaly or 0),
            maintenance_count=int(r.maint or 0),
            record_count=int(r.cnt or 0),
        )
        for r in rows
    ]


# ── Assets dropdown ───────────────────────────────────────────────────────────

@router.get("/assets")
async def list_softener_assets(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    """Return active SOFT_WATER utility assets for the UI dropdown."""
    rows = list((await db.execute(
        select(UtilityAsset)
        .where(
            UtilityAsset.utility_type == UtilityType.SOFT_WATER,
            UtilityAsset.is_active.is_(True),
        )
        .order_by(UtilityAsset.name)
    )).scalars().all())
    return [{"id": str(a.id), "asset_no": a.asset_no, "name": a.name} for a in rows]


# ── Records CRUD ──────────────────────────────────────────────────────────────

@router.get("/records/export/csv")
async def export_soft_water_csv(
    date_from:        Optional[date] = Query(None),
    date_to:          Optional[date] = Query(None),
    asset_id:         Optional[UUID] = Query(None),
    department:       Optional[str]  = Query(None),
    is_anomaly:       Optional[bool] = Query(None),
    maintenance_flag: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    records = await list_soft_water_records(
        db,
        asset_id=asset_id, department=department,
        date_from=date_from, date_to=date_to,
        is_anomaly=is_anomaly, maintenance_flag=maintenance_flag,
        limit=50000,
    )

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([
        "record_no", "record_datetime", "asset_no", "asset_name",
        "volume_treated_m3", "raw_water_input_m3", "flow_rate_lpm",
        "feed_hardness_ppm", "product_hardness_ppm",
        "feed_tds_ppm", "product_tds_ppm",
        "feed_ph", "product_ph",
        "conductivity_feed_uscm", "conductivity_product_uscm",
        "salt_consumed_kg", "regen_count",
        "regen_start", "regen_end",
        "efficiency_pct", "status",
        "downtime_minutes", "maintenance_flag",
        "destination_tag", "department", "shift_ref",
        "source_method", "is_anomaly", "anomaly_note", "notes",
    ])
    for r in records:
        w.writerow([
            r.record_no, r.record_datetime, r.asset_no, r.asset_name,
            r.volume_treated_m3, r.raw_water_input_m3, r.flow_rate_lpm,
            r.feed_water_hardness_ppm, r.product_water_hardness_ppm,
            r.feed_water_tds_ppm, r.product_water_tds_ppm,
            r.feed_ph, r.product_ph,
            r.conductivity_feed_uscm, r.conductivity_product_uscm,
            r.salt_consumed_kg, r.regeneration_count,
            r.regen_start, r.regen_end,
            r.efficiency_pct, r.status,
            r.downtime_minutes, r.maintenance_flag,
            r.destination_tag, r.department, r.shift_ref,
            r.source_method, r.is_anomaly, r.anomaly_note, r.notes,
        ])

    filename = f"soft-water-records-{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/records", response_model=List[SoftWaterRecordRead])
async def list_soft_water_records_endpoint(
    date_from:        Optional[date] = Query(None),
    date_to:          Optional[date] = Query(None),
    asset_id:         Optional[UUID] = Query(None),
    department:       Optional[str]  = Query(None),
    shift_ref:        Optional[str]  = Query(None),
    is_anomaly:       Optional[bool] = Query(None),
    maintenance_flag: Optional[bool] = Query(None),
    status:           Optional[str]  = Query(None),
    skip:  int = Query(0, ge=0),
    limit: int = Query(200, le=2000),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    return await list_soft_water_records(
        db,
        asset_id=asset_id, department=department,
        date_from=date_from, date_to=date_to,
        shift_ref=shift_ref, is_anomaly=is_anomaly,
        maintenance_flag=maintenance_flag, status=status,
        skip=skip, limit=limit,
    )


@router.get("/records/{record_id}", response_model=SoftWaterRecordRead)
async def get_soft_water_record_endpoint(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    rec = await get_soft_water_record(db, record_id)
    if not rec:
        raise HTTPException(404, "Soft water record not found")
    from app.crud.soft_water import _to_read
    return _to_read(rec)


@router.post("/records", response_model=SoftWaterRecordRead, status_code=201)
async def create_soft_water_record_endpoint(
    data: SoftWaterRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission(_PERM, "create")),
):
    rec = await create_soft_water_record(db, data, created_by_id=current_user.id)
    await db.commit()
    obj = await get_soft_water_record(db, rec.id)
    from app.crud.soft_water import _to_read
    return _to_read(obj)


@router.patch("/records/{record_id}", response_model=SoftWaterRecordRead)
async def update_soft_water_record_endpoint(
    record_id: UUID,
    data: SoftWaterRecordUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "edit")),
):
    rec = await get_soft_water_record(db, record_id)
    if not rec:
        raise HTTPException(404, "Soft water record not found")
    await update_soft_water_record(db, rec, data)
    await db.commit()
    obj = await get_soft_water_record(db, record_id)
    from app.crud.soft_water import _to_read
    return _to_read(obj)


@router.delete("/records/{record_id}", status_code=204)
async def delete_soft_water_record_endpoint(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "delete")),
):
    rec = await get_soft_water_record(db, record_id)
    if not rec:
        raise HTTPException(404, "Soft water record not found")
    await delete_soft_water_record(db, rec)
    await db.commit()
