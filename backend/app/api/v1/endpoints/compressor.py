"""
Compressor & Compressed Air Management Endpoints
─────────────────────────────────────────────────────────────────────────────
GET  /compressor/kpis                     – aggregated KPIs
GET  /compressor/trend/daily              – daily trend data
GET  /compressor/trend/shift              – shift analysis
GET  /compressor/breakdown                – consumption breakdown by dimension
GET  /compressor/assets                   – compressor asset dropdown
GET  /compressor/records                  – list operational records (filters)
GET  /compressor/records/export/csv       – CSV export
POST /compressor/records                  – create record
GET  /compressor/records/{id}             – get single record
PATCH/compressor/records/{id}             – update record
DELETE/compressor/records/{id}            – delete record
GET  /compressor/transactions             – list COMPRESSED_AIR utility_transactions
POST /compressor/transactions             – create COMPRESSED_AIR transaction
PATCH/compressor/transactions/{id}        – update transaction
DELETE/compressor/transactions/{id}       – delete transaction
GET  /compressor/transactions/export/csv  – CSV export of transactions
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
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.crud.compressor import (
    create_compressor_record,
    delete_compressor_record,
    get_compressor_record,
    list_compressor_records,
    update_compressor_record,
)
from app.models.user import User
from app.models.utility_management import (
    CompressorRecord,
    CompressorStatus,
    UtilityAsset,
    UtilityTransaction,
    UtilityType,
)
from app.schemas.compressor import (
    AirBreakdown,
    AirKPIs,
    AirShiftPoint,
    AirTrendPoint,
    CompressorAsset,
    CompressorRecordCreate,
    CompressorRecordRead,
    CompressorRecordUpdate,
)
from app.services.compressor_service import (
    get_air_breakdown,
    get_air_daily_trend,
    get_air_kpis,
    get_air_shift_analysis,
)

# Reuse UtilityTransaction schemas from utility_management module
from app.schemas.utility_management import (
    UtilityTransactionCreate,
    UtilityTransactionRead,
    UtilityTransactionUpdate,
)

router = APIRouter()

# ── Helpers ───────────────────────────────────────────────────────────────────

async def _air_cost(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to:   Optional[date] = None,
) -> Optional[Decimal]:
    """Sum total_cost from COMPRESSED_AIR utility_transactions in the period."""
    clauses = [UtilityTransaction.utility_type == UtilityType.COMPRESSED_AIR]
    if date_from:
        clauses.append(UtilityTransaction.transaction_date >= date_from)
    if date_to:
        clauses.append(UtilityTransaction.transaction_date <= date_to)
    result = await db.execute(
        select(func.sum(UtilityTransaction.total_cost)).where(and_(*clauses))
    )
    val = result.scalar_one_or_none()
    return Decimal(str(val)) if val is not None else None


# ── KPIs & Analytics ──────────────────────────────────────────────────────────

@router.get("/kpis", response_model=AirKPIs)
async def read_air_kpis(
    asset_id:   Optional[UUID] = Query(None),
    department: Optional[str]  = Query(None),
    shift_ref:  Optional[str]  = Query(None),
    prod_line:  Optional[str]  = Query(None),
    date_from:  Optional[date] = Query(None),
    date_to:    Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    cost = await _air_cost(db, date_from, date_to)
    return await get_air_kpis(
        db,
        asset_id=asset_id, department=department, shift_ref=shift_ref,
        date_from=date_from, date_to=date_to, prod_line=prod_line,
        air_cost_total=cost,
    )


@router.get("/trend/daily", response_model=List[AirTrendPoint])
async def read_daily_trend(
    asset_id:   Optional[UUID] = Query(None),
    department: Optional[str]  = Query(None),
    shift_ref:  Optional[str]  = Query(None),
    prod_line:  Optional[str]  = Query(None),
    date_from:  Optional[date] = Query(None),
    date_to:    Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await get_air_daily_trend(
        db, asset_id=asset_id, department=department, shift_ref=shift_ref,
        date_from=date_from, date_to=date_to, prod_line=prod_line,
    )


@router.get("/trend/shift", response_model=List[AirShiftPoint])
async def read_shift_analysis(
    asset_id:   Optional[UUID] = Query(None),
    department: Optional[str]  = Query(None),
    date_from:  Optional[date] = Query(None),
    date_to:    Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await get_air_shift_analysis(
        db, asset_id=asset_id, department=department,
        date_from=date_from, date_to=date_to,
    )


@router.get("/breakdown", response_model=AirBreakdown)
async def read_breakdown(
    dimension:  str            = Query("department"),
    asset_id:   Optional[UUID] = Query(None),
    department: Optional[str]  = Query(None),
    date_from:  Optional[date] = Query(None),
    date_to:    Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await get_air_breakdown(
        db, dimension=dimension, asset_id=asset_id,
        date_from=date_from, date_to=date_to, department=department,
    )


# ── Assets dropdown ────────────────────────────────────────────────────────────

@router.get("/assets", response_model=List[CompressorAsset])
async def list_compressor_assets(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = list((await db.execute(
        select(UtilityAsset)
        .where(UtilityAsset.utility_type == UtilityType.COMPRESSED_AIR)
        .where(UtilityAsset.is_active == True)
        .order_by(UtilityAsset.asset_no)
    )).scalars().all())
    return [CompressorAsset(id=a.id, asset_no=a.asset_no, name=a.name) for a in rows]


# ── Compressor Records CRUD ────────────────────────────────────────────────────

@router.get("/records/export/csv")
async def export_records_csv(
    asset_id:         Optional[UUID] = Query(None),
    department:       Optional[str]  = Query(None),
    shift_ref:        Optional[str]  = Query(None),
    prod_line:        Optional[str]  = Query(None),
    date_from:        Optional[date] = Query(None),
    date_to:          Optional[date] = Query(None),
    is_anomaly:       Optional[bool] = Query(None),
    maintenance_flag: Optional[bool] = Query(None),
    leak_test_done:   Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    records = await list_compressor_records(
        db,
        asset_id=asset_id, department=department, shift_ref=shift_ref,
        prod_line=prod_line, date_from=date_from, date_to=date_to,
        is_anomaly=is_anomaly, maintenance_flag=maintenance_flag,
        leak_test_done=leak_test_done, skip=0, limit=10000,
    )
    buf = io.StringIO()
    fields = [
        "record_no", "asset_no", "asset_name", "record_datetime",
        "shift_ref", "department", "production_line", "period_hours",
        "air_generated_nm3", "electricity_used_kwh",
        "runtime_hours", "load_time_hours", "unload_time_hours", "idle_time_hours",
        "discharge_pressure_bar", "line_pressure_bar", "receiver_tank_pressure_bar",
        "specific_energy_kwh_m3", "dryer_status", "dryer_dew_point_c",
        "filter_dp_bar", "leak_test_done", "leak_estimation_pct",
        "night_idle_kwh", "downtime_minutes", "maintenance_flag",
        "status", "is_anomaly", "notes",
    ]
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for rec in records:
        writer.writerow(rec.model_dump())
    buf.seek(0)
    return StreamingResponse(
        iter([buf.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=compressor_records.csv"},
    )


@router.get("/records", response_model=List[CompressorRecordRead])
async def list_records(
    asset_id:         Optional[UUID] = Query(None),
    department:       Optional[str]  = Query(None),
    shift_ref:        Optional[str]  = Query(None),
    prod_line:        Optional[str]  = Query(None),
    date_from:        Optional[date] = Query(None),
    date_to:          Optional[date] = Query(None),
    is_anomaly:       Optional[bool] = Query(None),
    maintenance_flag: Optional[bool] = Query(None),
    leak_test_done:   Optional[bool] = Query(None),
    status:           Optional[str]  = Query(None),
    skip:  int = Query(0, ge=0),
    limit: int = Query(200, le=1000),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await list_compressor_records(
        db,
        asset_id=asset_id, department=department, shift_ref=shift_ref,
        prod_line=prod_line, date_from=date_from, date_to=date_to,
        is_anomaly=is_anomaly, maintenance_flag=maintenance_flag,
        leak_test_done=leak_test_done, status=status, skip=skip, limit=limit,
    )


@router.post("/records", response_model=CompressorRecordRead, status_code=status.HTTP_201_CREATED)
async def create_record(
    data: CompressorRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    obj = await create_compressor_record(db, data, created_by_id=current_user.id)
    await db.commit()
    await db.refresh(obj)
    from app.crud.compressor import _to_read
    return _to_read(obj)


@router.get("/records/{record_id}", response_model=CompressorRecordRead)
async def get_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    obj = await get_compressor_record(db, record_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Compressor record not found")
    from app.crud.compressor import _to_read
    return _to_read(obj)


@router.patch("/records/{record_id}", response_model=CompressorRecordRead)
async def update_record(
    record_id: UUID,
    data: CompressorRecordUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    obj = await get_compressor_record(db, record_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Compressor record not found")
    obj = await update_compressor_record(db, obj, data)
    await db.commit()
    await db.refresh(obj)
    from app.crud.compressor import _to_read
    return _to_read(obj)


@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    obj = await get_compressor_record(db, record_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Compressor record not found")
    await delete_compressor_record(db, obj)
    await db.commit()


# ── COMPRESSED_AIR Utility Transactions ───────────────────────────────────────

@router.get("/transactions/export/csv")
async def export_transactions_csv(
    date_from:  Optional[date] = Query(None),
    date_to:    Optional[date] = Query(None),
    department: Optional[str]  = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    clauses = [UtilityTransaction.utility_type == UtilityType.COMPRESSED_AIR]
    if date_from:
        clauses.append(UtilityTransaction.transaction_date >= date_from)
    if date_to:
        clauses.append(UtilityTransaction.transaction_date <= date_to)
    if department:
        clauses.append(UtilityTransaction.department == department)
    rows = list((await db.execute(
        select(UtilityTransaction).where(and_(*clauses))
        .order_by(UtilityTransaction.transaction_date.desc())
        .limit(10000)
    )).scalars().all())
    buf = io.StringIO()
    fields = [
        "transaction_no", "transaction_date", "quantity", "unit_of_measure",
        "total_cost", "currency_code", "department", "production_line",
        "machine_ref", "shift_ref", "batch_no", "is_anomaly", "notes",
    ]
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for tx in rows:
        writer.writerow({f: getattr(tx, f, None) for f in fields})
    buf.seek(0)
    return StreamingResponse(
        iter([buf.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=air_transactions.csv"},
    )


@router.get("/transactions", response_model=List[UtilityTransactionRead])
async def list_transactions(
    date_from:  Optional[date] = Query(None),
    date_to:    Optional[date] = Query(None),
    department: Optional[str]  = Query(None),
    prod_line:  Optional[str]  = Query(None),
    skip:  int = Query(0, ge=0),
    limit: int = Query(200, le=1000),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    clauses = [UtilityTransaction.utility_type == UtilityType.COMPRESSED_AIR]
    if date_from:
        clauses.append(UtilityTransaction.transaction_date >= date_from)
    if date_to:
        clauses.append(UtilityTransaction.transaction_date <= date_to)
    if department:
        clauses.append(UtilityTransaction.department == department)
    if prod_line:
        clauses.append(UtilityTransaction.production_line == prod_line)
    rows = list((await db.execute(
        select(UtilityTransaction).where(and_(*clauses))
        .order_by(UtilityTransaction.transaction_date.desc())
        .offset(skip).limit(limit)
    )).scalars().all())
    return rows


@router.post("/transactions", response_model=UtilityTransactionRead, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    data: UtilityTransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import random as _rand
    from datetime import datetime as _dt
    tx_no = f"ATX-{data.transaction_date.strftime('%Y%m%d')}-{_rand.randint(10000, 99999)}"
    obj = UtilityTransaction(
        transaction_no=tx_no,
        utility_type=UtilityType.COMPRESSED_AIR,
        transaction_date=data.transaction_date,
        quantity=data.quantity,
        unit_of_measure=data.uom,
        cost_rate=data.cost_rate,
        total_cost=data.total_cost,
        currency_code=data.currency_code or "USD",
        department=data.department,
        building_area=data.building_area,
        production_line=data.line_id,
        machine_ref=data.machine_id,
        shift_ref=data.shift_id,
        batch_no=data.batch_id,
        is_estimated=bool(data.estimated_or_actual),
        is_anomaly=bool(data.anomaly_flag),
        anomaly_note=data.anomaly_note,
        notes=data.notes,
        created_by_id=current_user.id,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.patch("/transactions/{tx_id}", response_model=UtilityTransactionRead)
async def update_transaction(
    tx_id: UUID,
    data: UtilityTransactionUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    tx = (await db.execute(
        select(UtilityTransaction).where(
            UtilityTransaction.id == tx_id,
            UtilityTransaction.utility_type == UtilityType.COMPRESSED_AIR,
        )
    )).scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    update_data = data.model_dump(exclude_unset=True)
    field_map = {
        "uom": "unit_of_measure",
        "line_id": "production_line",
        "machine_id": "machine_ref",
        "shift_id": "shift_ref",
        "batch_id": "batch_no",
        "estimated_or_actual": "is_estimated",
        "anomaly_flag": "is_anomaly",
    }
    for k, v in update_data.items():
        setattr(tx, field_map.get(k, k), v)
    await db.commit()
    await db.refresh(tx)
    return tx


@router.delete("/transactions/{tx_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    tx_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    tx = (await db.execute(
        select(UtilityTransaction).where(
            UtilityTransaction.id == tx_id,
            UtilityTransaction.utility_type == UtilityType.COMPRESSED_AIR,
        )
    )).scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    await db.delete(tx)
    await db.commit()
