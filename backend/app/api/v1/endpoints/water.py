"""
Water Management API
────────────────────
Prefix: /water (registered in router.py)

Analytics (multi-type: WATER + PROCESS_WATER + WASTEWATER):
  GET  /water/kpis                 – plant water KPI block
  GET  /water/trend/daily          – daily time-series
  GET  /water/breakdown            – GROUP BY dept/line/machine/building/shift

Transactions (water utility records):
  GET  /water/transactions         – filtered list
  GET  /water/transactions/export/csv
  POST /water/transactions         – create a water record
  PATCH /water/transactions/{id}   – update
  DELETE /water/transactions/{id}  – delete
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
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_permission
from app.db.session import get_db
from app.crud import utility_management as crud
from app.models.utility_management import UtilityType, SourceMethod, DataQuality
from app.schemas.water import WaterBreakdown, WaterKPIs, WaterTrendPoint
from app.schemas.utility_management import (
    UtilityTransactionCreate,
    UtilityTransactionRead,
    UtilityTransactionUpdate,
)
from app.services.water_service import (
    get_water_breakdown,
    get_water_daily_trend,
    get_water_kpis,
)
from app.services.utility_transaction_service import (
    create_transaction as svc_create_transaction,
    enrich_transaction,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_PERM = "utility_management"

# Water utility types available for transaction filter
_WATER_TYPES = {UtilityType.WATER, UtilityType.PROCESS_WATER, UtilityType.WASTEWATER}


# ── Shared scope params ───────────────────────────────────────────────────────

def _scope(
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    department:    Optional[str] = Query(None),
    building_area: Optional[str] = Query(None),
    line_id:       Optional[str] = Query(None),
    machine_id:    Optional[str] = Query(None),
    shift_id:      Optional[str] = Query(None),
):
    return dict(
        date_from=date_from, date_to=date_to,
        department=department, building_area=building_area,
        line_id=line_id, machine_id=machine_id, shift_id=shift_id,
    )


# ── Analytics ─────────────────────────────────────────────────────────────────

@router.get("/kpis", response_model=WaterKPIs)
async def water_kpis(
    scope: dict = Depends(_scope),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    """Plant-wide (or scoped) water KPI block."""
    return await get_water_kpis(db, **scope)


@router.get("/trend/daily", response_model=List[WaterTrendPoint])
async def water_daily_trend(
    scope: dict = Depends(_scope),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    """Daily m³ time-series across all water types."""
    return await get_water_daily_trend(db, **scope)


@router.get("/breakdown", response_model=WaterBreakdown)
async def water_breakdown(
    dimension:  str = Query("department", description="department | line | machine | building_area | shift"),
    water_type: str = Query("WATER", description="WATER | PROCESS_WATER | WASTEWATER"),
    scope: dict = Depends(_scope),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    """Consumption breakdown by dimension for a specific water type."""
    return await get_water_breakdown(db, dimension=dimension, water_type=water_type, **scope)


# ── Transactions ──────────────────────────────────────────────────────────────

@router.get("/transactions/export/csv")
async def export_water_csv(
    utility_type:  Optional[str] = Query(None, description="WATER | PROCESS_WATER | WASTEWATER"),
    date_from:    Optional[date] = Query(None),
    date_to:      Optional[date] = Query(None),
    department:    Optional[str] = Query(None),
    building_area: Optional[str] = Query(None),
    line_id:       Optional[str] = Query(None),
    machine_id:    Optional[str] = Query(None),
    shift_id:      Optional[str] = Query(None),
    is_anomaly:    Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    # Resolve utility type filter
    ut: Optional[UtilityType] = None
    if utility_type:
        try:
            ut = UtilityType(utility_type)
            if ut not in _WATER_TYPES:
                ut = UtilityType.WATER
        except ValueError:
            ut = UtilityType.WATER

    # If no specific type, default to raw WATER for the export
    if ut is None:
        ut = UtilityType.WATER

    rows = await crud.list_transactions(
        db,
        utility_type=ut,
        date_from=date_from, date_to=date_to,
        department=department, building_area=building_area,
        line_id=line_id, machine_id=machine_id, shift_id=shift_id,
        is_anomaly=is_anomaly,
        limit=50000,
    )

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([
        "transaction_no", "utility_type", "transaction_date", "quantity_m3", "unit",
        "total_cost", "currency", "cost_rate",
        "department", "building_area", "production_line", "machine",
        "shift", "batch_no", "source_method", "quality",
        "estimated", "anomaly", "anomaly_note",
        "device_code", "asset_no", "notes",
    ])
    for tx in rows:
        w.writerow([
            tx.transaction_no, tx.utility_type.value, tx.transaction_date,
            tx.quantity, tx.unit_of_measure,
            tx.total_cost, tx.currency_code, tx.cost_rate,
            tx.department, tx.building_area, tx.production_line, tx.machine_ref,
            tx.shift_ref, tx.batch_no, tx.source_method.value, tx.quality.value,
            tx.is_estimated, tx.is_anomaly, tx.anomaly_note,
            tx.device.device_code if tx.device else "",
            tx.asset.asset_no if tx.asset else "",
            tx.notes,
        ])

    filename = f"water-transactions-{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/transactions", response_model=List[UtilityTransactionRead])
async def list_water_transactions(
    utility_type:  Optional[str] = Query(None, description="WATER | PROCESS_WATER | WASTEWATER"),
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
    """List water transactions (any water sub-type)."""
    ut: UtilityType = UtilityType.WATER
    if utility_type:
        try:
            ut = UtilityType(utility_type)
            if ut not in _WATER_TYPES:
                ut = UtilityType.WATER
        except ValueError:
            ut = UtilityType.WATER

    txs = await crud.list_transactions(
        db,
        utility_type=ut,
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
async def get_water_transaction(
    tx_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    tx = await crud.get_transaction(db, tx_id)
    if not tx or tx.utility_type not in _WATER_TYPES:
        raise HTTPException(404, "Water transaction not found")
    return enrich_transaction(tx)


@router.post("/transactions", response_model=UtilityTransactionRead, status_code=201)
async def create_water_transaction(
    data: UtilityTransactionCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "create")),
):
    """
    Create a water consumption record.
    Validates that utility_type is a water sub-type; defaults to WATER.
    """
    ut = data.utility_type
    if ut not in _WATER_TYPES:
        data = data.model_copy(update={"utility_type": UtilityType.WATER})
    tx = await svc_create_transaction(db, data)
    await db.commit()
    return tx


@router.patch("/transactions/{tx_id}", response_model=UtilityTransactionRead)
async def update_water_transaction(
    tx_id: uuid.UUID,
    data: UtilityTransactionUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "edit")),
):
    tx = await crud.get_transaction(db, tx_id)
    if not tx or tx.utility_type not in _WATER_TYPES:
        raise HTTPException(404, "Water transaction not found")
    tx = await crud.update_transaction(db, tx, data)
    await db.commit()
    obj = await crud.get_transaction(db, tx_id)
    return enrich_transaction(obj)


@router.delete("/transactions/{tx_id}", status_code=204)
async def delete_water_transaction(
    tx_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "delete")),
):
    tx = await crud.get_transaction(db, tx_id)
    if not tx or tx.utility_type not in _WATER_TYPES:
        raise HTTPException(404, "Water transaction not found")
    await crud.delete_transaction(db, tx)
    await db.commit()
