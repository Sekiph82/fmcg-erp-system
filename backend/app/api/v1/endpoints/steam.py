"""
Steam & Boiler Management API
──────────────────────────────
Prefix: /steam (registered in router.py)

Analytics:
  GET  /steam/kpis               – boiler KPI block
  GET  /steam/trend/daily        – daily time-series
  GET  /steam/trend/shift        – per-shift aggregation
  GET  /steam/breakdown          – GROUP BY dept/line/machine (from utility_transactions)

Boiler operational records:
  GET  /steam/records            – filtered list
  GET  /steam/records/export/csv
  GET  /steam/records/{id}       – single record
  POST /steam/records            – create
  PATCH /steam/records/{id}      – update
  DELETE /steam/records/{id}     – delete

Utility transactions (STEAM type):
  GET  /steam/transactions       – STEAM utility_transactions
  POST /steam/transactions       – create STEAM transaction (cost/allocation)
  PATCH /steam/transactions/{id}
  DELETE /steam/transactions/{id}

Assets:
  GET  /steam/assets             – active STEAM/boiler utility assets
"""
from __future__ import annotations

import csv
import io
import logging
import uuid as _uuid
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
from app.crud import utility_management as crud
from app.crud.boiler import (
    create_boiler_record,
    delete_boiler_record,
    get_boiler_record,
    list_boiler_records,
    update_boiler_record,
    _to_read,
)
from app.models.utility_management import (
    BoilerSteamRecord,
    SourceMethod,
    DataQuality,
    UtilityAsset,
    UtilityType,
    UtilityTransaction,
)
from app.models.user import User
from app.schemas.steam import (
    BoilerAsset,
    BoilerRecordCreate,
    BoilerRecordRead,
    BoilerRecordUpdate,
    SteamBreakdown,
    SteamKPIs,
    SteamShiftPoint,
    SteamTrendPoint,
)
from app.schemas.utility_management import (
    UtilityTransactionCreate,
    UtilityTransactionRead,
    UtilityTransactionUpdate,
)
from app.services.steam_service import (
    get_steam_breakdown,
    get_steam_daily_trend,
    get_steam_kpis,
    get_steam_shift_analysis,
)
from app.services.utility_transaction_service import (
    create_transaction as svc_create_transaction,
    enrich_transaction,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_PERM = "utility_management"


# ── Scope params ──────────────────────────────────────────────────────────────

def _scope(
    date_from:  Optional[date] = Query(None),
    date_to:    Optional[date] = Query(None),
    asset_id:   Optional[UUID] = Query(None),
    department: Optional[str]  = Query(None),
    shift_ref:  Optional[str]  = Query(None),
):
    return dict(
        date_from=date_from, date_to=date_to,
        asset_id=asset_id, department=department, shift_ref=shift_ref,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _steam_cost(
    db: AsyncSession,
    date_from: Optional[date],
    date_to:   Optional[date],
    department: Optional[str],
) -> Optional[Decimal]:
    """Fetch total STEAM cost from utility_transactions for the KPI block."""
    clauses = [UtilityTransaction.utility_type == UtilityType.STEAM]
    if date_from:
        clauses.append(UtilityTransaction.transaction_date >= date_from)
    if date_to:
        clauses.append(UtilityTransaction.transaction_date <= date_to)
    if department:
        clauses.append(UtilityTransaction.department == department)
    val = (await db.execute(
        select(func.sum(UtilityTransaction.total_cost)).where(and_(*clauses))
    )).scalar()
    return Decimal(str(val)) if val else None


# ── Analytics ─────────────────────────────────────────────────────────────────

@router.get("/kpis", response_model=SteamKPIs)
async def steam_kpis(
    scope: dict = Depends(_scope),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    """Aggregated boiler/steam KPI block (operational + cost)."""
    cost = await _steam_cost(
        db,
        date_from=scope.get("date_from"),
        date_to=scope.get("date_to"),
        department=scope.get("department"),
    )
    return await get_steam_kpis(db, **scope, steam_cost_total=cost)


@router.get("/trend/daily", response_model=List[SteamTrendPoint])
async def steam_daily_trend(
    scope: dict = Depends(_scope),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    """Daily boiler record aggregation for trend charts."""
    return await get_steam_daily_trend(db, **scope)


@router.get("/trend/shift", response_model=List[SteamShiftPoint])
async def steam_shift_trend(
    date_from:  Optional[date] = Query(None),
    date_to:    Optional[date] = Query(None),
    asset_id:   Optional[UUID] = Query(None),
    department: Optional[str]  = Query(None),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    """Per-shift steam production and efficiency aggregation."""
    return await get_steam_shift_analysis(
        db, date_from=date_from, date_to=date_to,
        asset_id=asset_id, department=department,
    )


@router.get("/breakdown", response_model=SteamBreakdown)
async def steam_breakdown(
    dimension:  str = Query("department", description="department | line | machine | building_area | shift"),
    date_from:  Optional[date] = Query(None),
    date_to:    Optional[date] = Query(None),
    asset_id:   Optional[UUID] = Query(None),
    department: Optional[str]  = Query(None),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    """Steam consumption breakdown by dimension (from utility_transactions)."""
    return await get_steam_breakdown(
        db, dimension=dimension,
        asset_id=asset_id, date_from=date_from, date_to=date_to, department=department,
    )


# ── Assets dropdown ───────────────────────────────────────────────────────────

@router.get("/assets", response_model=List[BoilerAsset])
async def list_boiler_assets(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    """Active STEAM utility assets for the UI dropdown."""
    rows = list((await db.execute(
        select(UtilityAsset)
        .where(
            UtilityAsset.utility_type == UtilityType.STEAM,
            UtilityAsset.is_active.is_(True),
        )
        .order_by(UtilityAsset.name)
    )).scalars().all())
    return [BoilerAsset(id=a.id, asset_no=a.asset_no, name=a.name) for a in rows]


# ── Boiler Records CRUD ───────────────────────────────────────────────────────

@router.get("/records/export/csv")
async def export_boiler_records_csv(
    date_from:        Optional[date] = Query(None),
    date_to:          Optional[date] = Query(None),
    asset_id:         Optional[UUID] = Query(None),
    department:       Optional[str]  = Query(None),
    shift_ref:        Optional[str]  = Query(None),
    is_anomaly:       Optional[bool] = Query(None),
    maintenance_flag: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    records = await list_boiler_records(
        db,
        asset_id=asset_id, department=department,
        date_from=date_from, date_to=date_to,
        shift_ref=shift_ref, is_anomaly=is_anomaly,
        maintenance_flag=maintenance_flag,
        limit=50000,
    )

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([
        "record_no", "record_datetime", "asset_no", "asset_name",
        "shift_ref", "department", "period_hours",
        "steam_generated_kg", "feedwater_consumed_m3", "condensate_returned_m3",
        "blowdown_volume_litres", "blowdown_pct",
        "fuel_type", "fuel_consumption", "fuel_unit",
        "boiler_efficiency_pct", "boiler_load_pct",
        "steam_pressure_bar", "steam_temp_c", "steam_flow_kgh",
        "flue_gas_temp_c", "o2_pct", "co2_pct",
        "feed_water_ph", "feed_water_tds_ppm",
        "boiler_tds_ppm", "boiler_ph", "conductivity_uscm",
        "burner_runtime_hours", "start_stop_count",
        "chemical_dosing_amount", "chemical_dosing_unit",
        "downtime_minutes", "downtime_reason",
        "maintenance_flag", "status", "is_anomaly", "anomaly_note", "notes",
    ])
    for r in records:
        w.writerow([
            r.record_no, r.record_datetime, r.asset_no, r.asset_name,
            r.shift_ref, r.department, r.period_hours,
            r.steam_generated_kg, r.feedwater_consumed_m3, r.condensate_returned_m3,
            r.blowdown_volume_litres, r.blowdown_pct,
            r.fuel_type, r.fuel_consumption, r.fuel_unit,
            r.boiler_efficiency_pct, r.boiler_load_pct,
            r.steam_pressure_bar, r.steam_temp_c, r.steam_flow_kgh,
            r.flue_gas_temp_c, r.o2_pct, r.co2_pct,
            r.feed_water_ph, r.feed_water_tds_ppm,
            r.boiler_tds_ppm, r.boiler_ph, r.conductivity_uscm,
            r.burner_runtime_hours, r.start_stop_count,
            r.chemical_dosing_amount, r.chemical_dosing_unit,
            r.downtime_minutes, r.downtime_reason,
            r.maintenance_flag, r.status, r.is_anomaly, r.anomaly_note, r.notes,
        ])

    filename = f"boiler-records-{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/records", response_model=List[BoilerRecordRead])
async def list_boiler_records_endpoint(
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
    return await list_boiler_records(
        db,
        asset_id=asset_id, department=department,
        date_from=date_from, date_to=date_to,
        shift_ref=shift_ref, is_anomaly=is_anomaly,
        maintenance_flag=maintenance_flag, status=status,
        skip=skip, limit=limit,
    )


@router.get("/records/{record_id}", response_model=BoilerRecordRead)
async def get_boiler_record_endpoint(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    rec = await get_boiler_record(db, record_id)
    if not rec:
        raise HTTPException(404, "Boiler record not found")
    return _to_read(rec)


@router.post("/records", response_model=BoilerRecordRead, status_code=201)
async def create_boiler_record_endpoint(
    data: BoilerRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission(_PERM, "create")),
):
    rec = await create_boiler_record(db, data, created_by_id=current_user.id)
    await db.commit()
    obj = await get_boiler_record(db, rec.id)
    return _to_read(obj)


@router.patch("/records/{record_id}", response_model=BoilerRecordRead)
async def update_boiler_record_endpoint(
    record_id: UUID,
    data: BoilerRecordUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "edit")),
):
    rec = await get_boiler_record(db, record_id)
    if not rec:
        raise HTTPException(404, "Boiler record not found")
    await update_boiler_record(db, rec, data)
    await db.commit()
    obj = await get_boiler_record(db, record_id)
    return _to_read(obj)


@router.delete("/records/{record_id}", status_code=204)
async def delete_boiler_record_endpoint(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "delete")),
):
    rec = await get_boiler_record(db, record_id)
    if not rec:
        raise HTTPException(404, "Boiler record not found")
    await delete_boiler_record(db, rec)
    await db.commit()


# ── Utility Transactions (STEAM cost allocation) ──────────────────────────────

@router.get("/transactions", response_model=List[UtilityTransactionRead])
async def list_steam_transactions(
    date_from:    Optional[date] = Query(None),
    date_to:      Optional[date] = Query(None),
    department:    Optional[str] = Query(None),
    building_area: Optional[str] = Query(None),
    line_id:       Optional[str] = Query(None),
    machine_id:    Optional[str] = Query(None),
    shift_id:      Optional[str] = Query(None),
    is_anomaly:    Optional[bool] = Query(None),
    is_estimated:  Optional[bool] = Query(None),
    search:        Optional[str] = Query(None),
    skip:  int = Query(0, ge=0),
    limit: int = Query(200, le=2000),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    txs = await crud.list_transactions(
        db,
        utility_type=UtilityType.STEAM,
        date_from=date_from, date_to=date_to,
        department=department, building_area=building_area,
        line_id=line_id, machine_id=machine_id, shift_id=shift_id,
        is_anomaly=is_anomaly, is_estimated=is_estimated,
        search=search, skip=skip, limit=limit,
    )
    return [enrich_transaction(tx) for tx in txs]


@router.post("/transactions", response_model=UtilityTransactionRead, status_code=201)
async def create_steam_transaction(
    data: UtilityTransactionCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "create")),
):
    """Create a STEAM utility transaction (cost/allocation entry)."""
    data = data.model_copy(update={"utility_type": UtilityType.STEAM})
    tx = await svc_create_transaction(db, data)
    await db.commit()
    return tx


@router.patch("/transactions/{tx_id}", response_model=UtilityTransactionRead)
async def update_steam_transaction(
    tx_id: _uuid.UUID,
    data: UtilityTransactionUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "edit")),
):
    tx = await crud.get_transaction(db, tx_id)
    if not tx or tx.utility_type != UtilityType.STEAM:
        raise HTTPException(404, "Steam transaction not found")
    tx = await crud.update_transaction(db, tx, data)
    await db.commit()
    obj = await crud.get_transaction(db, tx_id)
    return enrich_transaction(obj)


@router.delete("/transactions/{tx_id}", status_code=204)
async def delete_steam_transaction(
    tx_id: _uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "delete")),
):
    tx = await crud.get_transaction(db, tx_id)
    if not tx or tx.utility_type != UtilityType.STEAM:
        raise HTTPException(404, "Steam transaction not found")
    await crud.delete_transaction(db, tx)
    await db.commit()
