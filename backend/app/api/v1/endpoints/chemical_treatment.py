"""
Chemical Water Treatment API
────────────────────────────────────────────────────────────────
Prefix: /chemical-treatment (registered in router.py)

Chemical master:
  GET  /chemical-treatment/chemicals
  POST /chemical-treatment/chemicals
  GET  /chemical-treatment/chemicals/{id}
  PATCH /chemical-treatment/chemicals/{id}
  DELETE /chemical-treatment/chemicals/{id}

Treatment records:
  GET  /chemical-treatment/kpis
  GET  /chemical-treatment/records
  GET  /chemical-treatment/records/export/csv
  GET  /chemical-treatment/records/{id}
  POST /chemical-treatment/records
  PATCH /chemical-treatment/records/{id}
  DELETE /chemical-treatment/records/{id}

Assets dropdown:
  GET  /chemical-treatment/assets
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_permission
from app.db.session import get_db
from app.crud.chemical_treatment import (
    create_chemical,
    create_treatment_record,
    delete_chemical,
    delete_treatment_record,
    get_chemical,
    get_chemical_kpis,
    get_treatment_record,
    list_chemicals,
    list_treatment_records,
    update_chemical,
    update_treatment_record,
    _chem_to_read,
    _record_to_read,
)
from app.models.utility_management import UtilityAsset, UtilityType
from app.models.user import User
from app.schemas.chemical_treatment import (
    ChemicalKPIs,
    ChemicalOption,
    TreatmentRecordCreate,
    TreatmentRecordRead,
    TreatmentRecordUpdate,
    WaterTreatmentChemicalCreate,
    WaterTreatmentChemicalRead,
    WaterTreatmentChemicalUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_PERM = "utility_management"


# ── Scope filter dependency ───────────────────────────────────────────────────

def _scope(
    date_from:         Optional[date] = Query(None),
    date_to:           Optional[date] = Query(None),
    asset_id:          Optional[UUID] = Query(None),
    chemical_id:       Optional[UUID] = Query(None),
    chemical_category: Optional[str]  = Query(None),
    treatment_area:    Optional[str]  = Query(None),
    supplier_id:       Optional[UUID] = Query(None),
):
    return dict(
        date_from=date_from, date_to=date_to,
        asset_id=asset_id, chemical_id=chemical_id,
        chemical_category=chemical_category,
        treatment_area=treatment_area,
        supplier_id=supplier_id,
    )


# ── KPIs ──────────────────────────────────────────────────────────────────────

@router.get("/kpis", response_model=ChemicalKPIs)
async def chemical_kpis(
    scope: dict = Depends(_scope),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    """Aggregated KPI block: dosing totals, cost, chemical/m3, anomaly counts."""
    return await get_chemical_kpis(db, **scope)


# ── Chemical Master ───────────────────────────────────────────────────────────

@router.get("/chemicals", response_model=List[WaterTreatmentChemicalRead])
async def list_chemicals_endpoint(
    chemical_category: Optional[str]  = Query(None),
    supplier_id:       Optional[UUID] = Query(None),
    is_active:         Optional[bool] = Query(None),
    search:            Optional[str]  = Query(None),
    skip:  int = Query(0, ge=0),
    limit: int = Query(500, le=2000),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    return await list_chemicals(
        db,
        chemical_category=chemical_category, supplier_id=supplier_id,
        is_active=is_active, search=search, skip=skip, limit=limit,
    )


@router.get("/chemicals/options", response_model=List[ChemicalOption])
async def chemical_options(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    """Compact list for UI dropdowns — active chemicals only."""
    from app.models.utility_management import WaterTreatmentChemical
    rows = list((await db.execute(
        select(WaterTreatmentChemical)
        .where(WaterTreatmentChemical.is_active.is_(True))
        .order_by(WaterTreatmentChemical.chemical_name)
    )).scalars().all())
    return [
        ChemicalOption(
            id=r.id,
            chemical_code=r.chemical_code,
            chemical_name=r.chemical_name,
            chemical_category=r.chemical_category.value if r.chemical_category else "OTHER",
            stock_uom=r.stock_uom,
            dosing_uom=r.dosing_uom,
            unit_cost=r.unit_cost,
        )
        for r in rows
    ]


@router.get("/chemicals/{chemical_id}", response_model=WaterTreatmentChemicalRead)
async def get_chemical_endpoint(
    chemical_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    obj = await get_chemical(db, chemical_id)
    if not obj:
        raise HTTPException(404, "Chemical not found")
    return _chem_to_read(obj)


@router.post("/chemicals", response_model=WaterTreatmentChemicalRead, status_code=201)
async def create_chemical_endpoint(
    data: WaterTreatmentChemicalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission(_PERM, "create")),
):
    obj = await create_chemical(db, data, created_by_id=current_user.id)
    await db.commit()
    fresh = await get_chemical(db, obj.id)
    return _chem_to_read(fresh)


@router.patch("/chemicals/{chemical_id}", response_model=WaterTreatmentChemicalRead)
async def update_chemical_endpoint(
    chemical_id: UUID,
    data: WaterTreatmentChemicalUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "edit")),
):
    obj = await get_chemical(db, chemical_id)
    if not obj:
        raise HTTPException(404, "Chemical not found")
    await update_chemical(db, obj, data)
    await db.commit()
    fresh = await get_chemical(db, chemical_id)
    return _chem_to_read(fresh)


@router.delete("/chemicals/{chemical_id}", status_code=204)
async def delete_chemical_endpoint(
    chemical_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "delete")),
):
    obj = await get_chemical(db, chemical_id)
    if not obj:
        raise HTTPException(404, "Chemical not found")
    await delete_chemical(db, obj)
    await db.commit()


# ── Assets dropdown ───────────────────────────────────────────────────────────

@router.get("/assets", response_model=List[dict])
async def list_treatment_assets(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    """Active utility assets for the treatment area dropdown."""
    rows = list((await db.execute(
        select(UtilityAsset)
        .where(UtilityAsset.is_active.is_(True))
        .order_by(UtilityAsset.name)
    )).scalars().all())
    return [{"id": str(r.id), "asset_no": r.asset_no, "name": r.name, "utility_type": r.utility_type.value} for r in rows]


# ── Treatment Records ─────────────────────────────────────────────────────────

@router.get("/records/export/csv")
async def export_treatment_records_csv(
    date_from:         Optional[date] = Query(None),
    date_to:           Optional[date] = Query(None),
    asset_id:          Optional[UUID] = Query(None),
    chemical_id:       Optional[UUID] = Query(None),
    chemical_category: Optional[str]  = Query(None),
    treatment_area:    Optional[str]  = Query(None),
    supplier_id:       Optional[UUID] = Query(None),
    is_anomaly:        Optional[bool] = Query(None),
    overdose_flag:     Optional[bool] = Query(None),
    underdose_flag:    Optional[bool] = Query(None),
    shift_ref:         Optional[str]  = Query(None),
    batch_lot_no:      Optional[str]  = Query(None),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    records = await list_treatment_records(
        db,
        asset_id=asset_id, chemical_id=chemical_id,
        chemical_category=chemical_category, treatment_area=treatment_area,
        supplier_id=supplier_id, date_from=date_from, date_to=date_to,
        is_anomaly=is_anomaly, overdose_flag=overdose_flag,
        underdose_flag=underdose_flag, shift_ref=shift_ref,
        batch_lot_no=batch_lot_no, limit=50000,
    )

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([
        "record_no", "date", "record_datetime", "asset_name", "asset_no",
        "treatment_type", "chemical_code", "chemical_name", "chemical_category",
        "treatment_area", "dosing_point",
        "supplier_name", "batch_lot_no", "unit_cost",
        "stock_uom", "dosing_uom",
        "opening_stock", "received_qty", "consumed_qty", "closing_stock",
        "quantity_dosed", "unit",
        "target_dose_ppm", "actual_dose_ppm", "water_volume_m3",
        "manual_or_auto_dose",
        "water_treated_m3", "steam_produced_ton",
        "feed_ph", "product_ph",
        "feed_turbidity_ntu", "product_turbidity_ntu",
        "residual_chlorine_ppm", "tds_feed_ppm", "tds_product_ppm",
        "source_method", "is_anomaly", "overdose_flag", "underdose_flag",
        "anomaly_note", "shift_ref", "inventory_synced", "notes",
    ])
    for r in records:
        w.writerow([
            r.record_no, r.date, r.record_datetime, r.asset_name, r.asset_no,
            r.treatment_type, r.chemical_code, r.chemical_name, r.chemical_category,
            r.treatment_area, r.dosing_point,
            r.supplier_name, r.batch_lot_no, r.unit_cost,
            r.stock_uom, r.dosing_uom,
            r.opening_stock, r.received_qty, r.consumed_qty, r.closing_stock,
            r.quantity_dosed, r.unit,
            r.target_dose_ppm, r.actual_dose_ppm, r.water_volume_m3,
            r.manual_or_auto_dose,
            r.water_treated_m3, r.steam_produced_ton,
            r.feed_ph, r.product_ph,
            r.feed_turbidity_ntu, r.product_turbidity_ntu,
            r.residual_chlorine_ppm, r.tds_feed_ppm, r.tds_product_ppm,
            r.source_method, r.is_anomaly, r.overdose_flag, r.underdose_flag,
            r.anomaly_note, r.shift_ref, r.inventory_synced, r.notes,
        ])

    filename = f"chemical-treatment-{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/records", response_model=List[TreatmentRecordRead])
async def list_treatment_records_endpoint(
    date_from:         Optional[date] = Query(None),
    date_to:           Optional[date] = Query(None),
    asset_id:          Optional[UUID] = Query(None),
    chemical_id:       Optional[UUID] = Query(None),
    chemical_category: Optional[str]  = Query(None),
    treatment_area:    Optional[str]  = Query(None),
    supplier_id:       Optional[UUID] = Query(None),
    is_anomaly:        Optional[bool] = Query(None),
    overdose_flag:     Optional[bool] = Query(None),
    underdose_flag:    Optional[bool] = Query(None),
    shift_ref:         Optional[str]  = Query(None),
    batch_lot_no:      Optional[str]  = Query(None),
    skip:  int = Query(0, ge=0),
    limit: int = Query(200, le=2000),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    return await list_treatment_records(
        db,
        asset_id=asset_id, chemical_id=chemical_id,
        chemical_category=chemical_category, treatment_area=treatment_area,
        supplier_id=supplier_id, date_from=date_from, date_to=date_to,
        is_anomaly=is_anomaly, overdose_flag=overdose_flag,
        underdose_flag=underdose_flag, shift_ref=shift_ref,
        batch_lot_no=batch_lot_no, skip=skip, limit=limit,
    )


@router.get("/records/{record_id}", response_model=TreatmentRecordRead)
async def get_treatment_record_endpoint(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "view")),
):
    rec = await get_treatment_record(db, record_id)
    if not rec:
        raise HTTPException(404, "Treatment record not found")
    return _record_to_read(rec)


@router.post("/records", response_model=TreatmentRecordRead, status_code=201)
async def create_treatment_record_endpoint(
    data: TreatmentRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission(_PERM, "create")),
):
    rec = await create_treatment_record(db, data, entered_by_id=current_user.id)
    await db.commit()
    fresh = await get_treatment_record(db, rec.id)
    return _record_to_read(fresh)


@router.patch("/records/{record_id}", response_model=TreatmentRecordRead)
async def update_treatment_record_endpoint(
    record_id: UUID,
    data: TreatmentRecordUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "edit")),
):
    rec = await get_treatment_record(db, record_id)
    if not rec:
        raise HTTPException(404, "Treatment record not found")
    await update_treatment_record(db, rec, data)
    await db.commit()
    fresh = await get_treatment_record(db, record_id)
    return _record_to_read(fresh)


@router.delete("/records/{record_id}", status_code=204)
async def delete_treatment_record_endpoint(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(_PERM, "delete")),
):
    rec = await get_treatment_record(db, record_id)
    if not rec:
        raise HTTPException(404, "Treatment record not found")
    await delete_treatment_record(db, rec)
    await db.commit()
