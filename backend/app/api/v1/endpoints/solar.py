"""
Solar Energy Management API
────────────────────────────
Prefix: /solar (registered in router.py)

Analytics (read-only, SOLAR-scoped):
  GET  /solar/kpis                  – plant KPI block
  GET  /solar/trend/daily           – daily time-series
  GET  /solar/breakdown             – GROUP BY dept/line/machine/building/shift

Transactions (SOLAR generation records):
  GET  /solar/transactions          – filtered list
  GET  /solar/transactions/export/csv
  POST /solar/transactions          – create one solar generation record
  PATCH /solar/transactions/{id}    – update
  DELETE /solar/transactions/{id}   – delete

Operational Records (SolarRecord — irradiance, inverter, PR ratio):
  GET  /solar/records               – list operational records
  POST /solar/records               – create one
  PATCH /solar/records/{id}         – update
  DELETE /solar/records/{id}        – delete

Tariffs:
  GET  /solar/tariffs               – active tariffs for SOLAR type
"""
from __future__ import annotations

import csv
import io
import logging
import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_permission
from app.db.session import get_db
from app.crud import utility_management as crud
from app.crud import solar as solar_crud
from app.models.utility_management import UtilityTariff, UtilityType, SourceMethod, DataQuality
from app.schemas.solar import (
    SolarBreakdown,
    SolarKPIs,
    SolarRecordCreate,
    SolarRecordRead,
    SolarRecordUpdate,
    SolarTariffRead,
    SolarTrendPoint,
)
from app.schemas.utility_management import (
    UtilityTransactionCreate,
    UtilityTransactionRead,
    UtilityTransactionUpdate,
)
from app.services.solar_service import (
    get_breakdown,
    get_daily_trend,
    get_kpis,
)
from app.services.utility_transaction_service import (
    create_transaction as svc_create_transaction,
    enrich_transaction,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_PERM = "utility_management"


# ── Shared date-range params ──────────────────────────────────────────────────

def _date_range(
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    department:    Optional[str] = Query(None),
    building_area: Optional[str] = Query(None),
    line_id:       Optional[str] = Query(None),
    machine_id:    Optional[str] = Query(None),
    shift_id:      Optional[str] = Query(None),
    asset_id:      Optional[uuid.UUID] = Query(None),
):
    return dict(
        date_from=date_from, date_to=date_to,
        department=department, building_area=building_area,
        line_id=line_id, machine_id=machine_id, shift_id=shift_id,
        asset_id=asset_id,
    )


# ── Analytics ─────────────────────────────────────────────────────────────────

@router.get("/kpis", response_model=SolarKPIs)
async def solar_kpis(
    scope: dict = Depends(_date_range),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    """Plant-wide (or scoped) solar KPI block."""
    return await get_kpis(db, **scope)


@router.get("/trend/daily", response_model=List[SolarTrendPoint])
async def solar_daily_trend(
    scope: dict = Depends(_date_range),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    """Daily kWh generation + export/self-consumption time-series."""
    return await get_daily_trend(db, **scope)


@router.get("/breakdown", response_model=SolarBreakdown)
async def solar_breakdown(
    dimension: str = Query("department", description="department | line | machine | building_area | shift"),
    scope: dict = Depends(_date_range),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    """Generation breakdown grouped by a single dimension."""
    return await get_breakdown(db, dimension=dimension, **{k: v for k, v in scope.items() if k != "asset_id"})


# ── Tariffs ───────────────────────────────────────────────────────────────────

@router.get("/tariffs", response_model=List[SolarTariffRead])
async def list_solar_tariffs(
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    """List tariffs for SOLAR — used for the transaction form dropdown."""
    q = select(UtilityTariff).where(UtilityTariff.utility_type == UtilityType.SOLAR)
    if is_active is not None:
        q = q.where(UtilityTariff.is_active == is_active)
    q = q.order_by(UtilityTariff.tariff_code)
    rows = list((await db.execute(q)).scalars().all())
    return [SolarTariffRead.model_validate(r) for r in rows]


# ── Transactions ──────────────────────────────────────────────────────────────

@router.get("/transactions/export/csv")
async def export_solar_csv(
    date_from:    Optional[date] = Query(None),
    date_to:      Optional[date] = Query(None),
    department:    Optional[str] = Query(None),
    building_area: Optional[str] = Query(None),
    line_id:       Optional[str] = Query(None),
    machine_id:    Optional[str] = Query(None),
    shift_id:      Optional[str] = Query(None),
    source_meter_id: Optional[uuid.UUID] = Query(None),
    source_asset_id: Optional[uuid.UUID] = Query(None),
    is_anomaly:    Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    rows = await crud.list_transactions(
        db,
        utility_type=UtilityType.SOLAR,
        date_from=date_from, date_to=date_to,
        department=department, building_area=building_area,
        line_id=line_id, machine_id=machine_id, shift_id=shift_id,
        source_meter_id=source_meter_id, source_asset_id=source_asset_id,
        is_anomaly=is_anomaly,
        limit=50000,
    )

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([
        "transaction_no", "transaction_date", "quantity_kwh", "unit",
        "total_cost", "currency", "cost_rate",
        "department", "building_area", "production_line", "machine",
        "shift", "batch_no", "source_method", "quality",
        "estimated", "anomaly", "anomaly_note",
        "device_code", "asset_no", "tariff_code", "notes",
    ])
    for tx in rows:
        w.writerow([
            tx.transaction_no, tx.transaction_date,
            tx.quantity, tx.unit_of_measure,
            tx.total_cost, tx.currency_code, tx.cost_rate,
            tx.department, tx.building_area, tx.production_line, tx.machine_ref,
            tx.shift_ref, tx.batch_no, tx.source_method.value, tx.quality.value,
            tx.is_estimated, tx.is_anomaly, tx.anomaly_note,
            tx.device.device_code if tx.device else "",
            tx.asset.asset_no if tx.asset else "",
            tx.tariff.tariff_code if tx.tariff else "",
            tx.notes,
        ])

    filename = f"solar-transactions-{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/transactions", response_model=List[UtilityTransactionRead])
async def list_solar_transactions(
    date_from:    Optional[date] = Query(None),
    date_to:      Optional[date] = Query(None),
    department:    Optional[str] = Query(None),
    building_area: Optional[str] = Query(None),
    line_id:       Optional[str] = Query(None),
    machine_id:    Optional[str] = Query(None),
    shift_id:      Optional[str] = Query(None),
    source_meter_id: Optional[uuid.UUID] = Query(None),
    source_asset_id: Optional[uuid.UUID] = Query(None),
    batch_id:      Optional[str] = Query(None),
    source_method: Optional[SourceMethod] = Query(None),
    quality:       Optional[DataQuality] = Query(None),
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
        utility_type=UtilityType.SOLAR,
        date_from=date_from, date_to=date_to,
        department=department, building_area=building_area,
        line_id=line_id, machine_id=machine_id, shift_id=shift_id,
        source_meter_id=source_meter_id, source_asset_id=source_asset_id,
        batch_id=batch_id, source_method=source_method,
        is_anomaly=is_anomaly, is_estimated=is_estimated,
        search=search, skip=skip, limit=limit,
    )
    return [enrich_transaction(tx) for tx in txs]


@router.get("/transactions/{tx_id}", response_model=UtilityTransactionRead)
async def get_solar_transaction(
    tx_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    tx = await crud.get_transaction(db, tx_id)
    if not tx or tx.utility_type != UtilityType.SOLAR:
        raise HTTPException(404, "Solar transaction not found")
    return enrich_transaction(tx)


@router.post("/transactions", response_model=UtilityTransactionRead, status_code=201)
async def create_solar_transaction(
    data: UtilityTransactionCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "create")),
):
    """
    Create a new solar generation record.
    Forces utility_type = SOLAR regardless of payload value.
    """
    data = data.model_copy(update={"utility_type": UtilityType.SOLAR})
    tx = await svc_create_transaction(db, data)
    await db.commit()
    return tx


@router.patch("/transactions/{tx_id}", response_model=UtilityTransactionRead)
async def update_solar_transaction(
    tx_id: uuid.UUID,
    data: UtilityTransactionUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "edit")),
):
    tx = await crud.get_transaction(db, tx_id)
    if not tx or tx.utility_type != UtilityType.SOLAR:
        raise HTTPException(404, "Solar transaction not found")
    tx = await crud.update_transaction(db, tx, data)
    await db.commit()
    obj = await crud.get_transaction(db, tx_id)
    return enrich_transaction(obj)


@router.delete("/transactions/{tx_id}", status_code=204)
async def delete_solar_transaction(
    tx_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "delete")),
):
    tx = await crud.get_transaction(db, tx_id)
    if not tx or tx.utility_type != UtilityType.SOLAR:
        raise HTTPException(404, "Solar transaction not found")
    await crud.delete_transaction(db, tx)
    await db.commit()


# ── Operational Records (SolarRecord) ─────────────────────────────────────────

@router.get("/records", response_model=List[SolarRecordRead])
async def list_solar_records(
    asset_id:   Optional[uuid.UUID] = Query(None),
    date_from:  Optional[date] = Query(None),
    date_to:    Optional[date] = Query(None),
    is_anomaly: Optional[bool] = Query(None),
    skip:  int = Query(0, ge=0),
    limit: int = Query(200, le=2000),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    """List SolarRecord operational logs (irradiance, inverter, PR ratio)."""
    return await solar_crud.list_solar_records(
        db, asset_id=asset_id, date_from=date_from, date_to=date_to,
        is_anomaly=is_anomaly, skip=skip, limit=limit,
    )


@router.post("/records", response_model=SolarRecordRead, status_code=201)
async def create_solar_record(
    data: SolarRecordCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "create")),
):
    obj = await solar_crud.create_solar_record(db, data)
    await db.commit()
    refreshed = await solar_crud.get_solar_record(db, obj.id)
    return solar_crud._to_read(refreshed)


@router.patch("/records/{record_id}", response_model=SolarRecordRead)
async def update_solar_record(
    record_id: uuid.UUID,
    data: SolarRecordUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "edit")),
):
    obj = await solar_crud.get_solar_record(db, record_id)
    if not obj:
        raise HTTPException(404, "Solar record not found")
    obj = await solar_crud.update_solar_record(db, obj, data)
    await db.commit()
    refreshed = await solar_crud.get_solar_record(db, record_id)
    return solar_crud._to_read(refreshed)


@router.delete("/records/{record_id}", status_code=204)
async def delete_solar_record(
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "delete")),
):
    obj = await solar_crud.get_solar_record(db, record_id)
    if not obj:
        raise HTTPException(404, "Solar record not found")
    await solar_crud.delete_solar_record(db, obj)
    await db.commit()
