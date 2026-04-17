"""
CRUD operations for Chemical Water Treatment module.
"""
from __future__ import annotations

import random
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.utility_management import (
    ChemicalCategory,
    DosingMode,
    SourceMethod,
    TreatmentChemicalRecord,
    TreatmentType,
    UtilityAsset,
    WaterTreatmentChemical,
)
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


# ── Record number helpers ──────────────────────────────────────────────────────

def _gen_record_no(dt: datetime) -> str:
    d = dt.strftime("%Y%m%d") if dt else datetime.utcnow().strftime("%Y%m%d")
    return f"CTX-{d}-{random.randint(10000, 99999)}"


def _gen_chem_code(name: str) -> str:
    slug = "".join(c for c in name.upper() if c.isalnum())[:6]
    return f"CHM-{slug}-{random.randint(1000, 9999)}"


# ── Denormalize helpers ────────────────────────────────────────────────────────

def _record_to_read(rec: TreatmentChemicalRecord) -> TreatmentRecordRead:
    d = TreatmentRecordRead.model_validate(rec)
    if rec.asset:
        d.asset_name = rec.asset.name
        d.asset_no   = rec.asset.asset_no
    if rec.supplier:
        d.supplier_name = rec.supplier.name
    return d


def _chem_to_read(chem: WaterTreatmentChemical) -> WaterTreatmentChemicalRead:
    d = WaterTreatmentChemicalRead.model_validate(chem)
    if chem.supplier:
        d.supplier_name = chem.supplier.name
    return d


# ── Chemical Master CRUD ───────────────────────────────────────────────────────

async def list_chemicals(
    db: AsyncSession,
    *,
    chemical_category: Optional[str] = None,
    supplier_id:       Optional[UUID] = None,
    is_active:         Optional[bool] = None,
    search:            Optional[str]  = None,
    skip:  int = 0,
    limit: int = 500,
) -> List[WaterTreatmentChemicalRead]:
    clauses = []
    if chemical_category:
        try:
            clauses.append(WaterTreatmentChemical.chemical_category == ChemicalCategory(chemical_category))
        except ValueError:
            pass
    if supplier_id:
        clauses.append(WaterTreatmentChemical.supplier_id == supplier_id)
    if is_active is not None:
        clauses.append(WaterTreatmentChemical.is_active == is_active)
    if search:
        term = f"%{search}%"
        clauses.append(
            WaterTreatmentChemical.chemical_name.ilike(term)
            | WaterTreatmentChemical.chemical_code.ilike(term)
        )

    q = (
        select(WaterTreatmentChemical)
        .options(selectinload(WaterTreatmentChemical.supplier))
        .where(and_(*clauses) if clauses else True)
        .order_by(WaterTreatmentChemical.chemical_name)
        .offset(skip)
        .limit(limit)
    )
    rows = list((await db.execute(q)).scalars().all())
    return [_chem_to_read(r) for r in rows]


async def get_chemical(db: AsyncSession, chemical_id: UUID) -> Optional[WaterTreatmentChemical]:
    q = (
        select(WaterTreatmentChemical)
        .options(selectinload(WaterTreatmentChemical.supplier))
        .where(WaterTreatmentChemical.id == chemical_id)
    )
    return (await db.execute(q)).scalar_one_or_none()


async def create_chemical(
    db: AsyncSession,
    data: WaterTreatmentChemicalCreate,
    created_by_id: Optional[UUID] = None,
) -> WaterTreatmentChemical:
    obj = WaterTreatmentChemical(
        **data.model_dump(exclude_unset=True),
        created_by_id=created_by_id,
    )
    db.add(obj)
    await db.flush()
    return obj


async def update_chemical(
    db: AsyncSession,
    obj: WaterTreatmentChemical,
    data: WaterTreatmentChemicalUpdate,
) -> WaterTreatmentChemical:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    return obj


async def delete_chemical(db: AsyncSession, obj: WaterTreatmentChemical) -> None:
    await db.delete(obj)
    await db.flush()


# ── Treatment Record CRUD ──────────────────────────────────────────────────────

_RECORD_OPTIONS = [
    selectinload(TreatmentChemicalRecord.asset),
    selectinload(TreatmentChemicalRecord.supplier),
]


async def list_treatment_records(
    db: AsyncSession,
    *,
    asset_id:          Optional[UUID] = None,
    chemical_id:       Optional[UUID] = None,
    chemical_category: Optional[str]  = None,
    treatment_area:    Optional[str]  = None,
    supplier_id:       Optional[UUID] = None,
    date_from:         Optional[date] = None,
    date_to:           Optional[date] = None,
    is_anomaly:        Optional[bool] = None,
    overdose_flag:     Optional[bool] = None,
    underdose_flag:    Optional[bool] = None,
    shift_ref:         Optional[str]  = None,
    batch_lot_no:      Optional[str]  = None,
    skip:  int = 0,
    limit: int = 200,
) -> List[TreatmentRecordRead]:
    clauses = []
    if asset_id:
        clauses.append(TreatmentChemicalRecord.asset_id == asset_id)
    if chemical_id:
        clauses.append(TreatmentChemicalRecord.chemical_id == chemical_id)
    if chemical_category:
        try:
            clauses.append(TreatmentChemicalRecord.chemical_category == ChemicalCategory(chemical_category))
        except ValueError:
            pass
    if treatment_area:
        clauses.append(TreatmentChemicalRecord.treatment_area.ilike(f"%{treatment_area}%"))
    if supplier_id:
        clauses.append(TreatmentChemicalRecord.supplier_id == supplier_id)
    if date_from:
        clauses.append(TreatmentChemicalRecord.date >= date_from)
    if date_to:
        clauses.append(TreatmentChemicalRecord.date <= date_to)
    if is_anomaly is not None:
        clauses.append(TreatmentChemicalRecord.is_anomaly == is_anomaly)
    if overdose_flag is not None:
        clauses.append(TreatmentChemicalRecord.overdose_flag == overdose_flag)
    if underdose_flag is not None:
        clauses.append(TreatmentChemicalRecord.underdose_flag == underdose_flag)
    if shift_ref:
        clauses.append(TreatmentChemicalRecord.shift_ref == shift_ref)
    if batch_lot_no:
        clauses.append(TreatmentChemicalRecord.batch_lot_no == batch_lot_no)

    q = (
        select(TreatmentChemicalRecord)
        .options(*_RECORD_OPTIONS)
        .where(and_(*clauses) if clauses else True)
        .order_by(TreatmentChemicalRecord.record_datetime.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = list((await db.execute(q)).scalars().all())
    return [_record_to_read(r) for r in rows]


async def get_treatment_record(
    db: AsyncSession, record_id: UUID
) -> Optional[TreatmentChemicalRecord]:
    q = (
        select(TreatmentChemicalRecord)
        .options(*_RECORD_OPTIONS)
        .where(TreatmentChemicalRecord.id == record_id)
    )
    return (await db.execute(q)).scalar_one_or_none()


async def create_treatment_record(
    db: AsyncSession,
    data: TreatmentRecordCreate,
    entered_by_id: Optional[UUID] = None,
) -> TreatmentChemicalRecord:
    record_no = _gen_record_no(data.record_datetime)

    try:
        treatment_type = TreatmentType(data.treatment_type)
    except ValueError:
        treatment_type = TreatmentType.OTHER

    try:
        source_method = SourceMethod(data.source_method)
    except ValueError:
        source_method = SourceMethod.MANUAL

    dosing_mode: Optional[DosingMode] = None
    if data.manual_or_auto_dose:
        try:
            dosing_mode = DosingMode(data.manual_or_auto_dose)
        except ValueError:
            dosing_mode = DosingMode.MANUAL

    chem_category: Optional[ChemicalCategory] = None
    if data.chemical_category:
        try:
            chem_category = ChemicalCategory(data.chemical_category)
        except ValueError:
            pass

    rec_date = data.date or (data.record_datetime.date() if data.record_datetime else None)

    obj = TreatmentChemicalRecord(
        record_no=record_no,
        asset_id=data.asset_id,
        record_datetime=data.record_datetime,
        date=rec_date,
        treatment_type=treatment_type,
        chemical_id=data.chemical_id,
        chemical_code=data.chemical_code,
        chemical_name=data.chemical_name,
        chemical_category=chem_category,
        treatment_area=data.treatment_area,
        dosing_point=data.dosing_point,
        supplier_id=data.supplier_id,
        batch_lot_no=data.batch_lot_no,
        unit_cost=data.unit_cost,
        stock_uom=data.stock_uom,
        dosing_uom=data.dosing_uom,
        opening_stock=data.opening_stock,
        received_qty=data.received_qty,
        consumed_qty=data.consumed_qty,
        closing_stock=data.closing_stock,
        quantity_dosed=data.quantity_dosed,
        unit=data.unit,
        target_dose_ppm=data.target_dose_ppm,
        actual_dose_ppm=data.actual_dose_ppm,
        water_volume_m3=data.water_volume_m3,
        manual_or_auto_dose=dosing_mode,
        related_meter_id=data.related_meter_id,
        material_id=data.material_id,
        water_treated_m3=data.water_treated_m3,
        steam_produced_ton=data.steam_produced_ton,
        feed_ph=data.feed_ph,
        product_ph=data.product_ph,
        feed_turbidity_ntu=data.feed_turbidity_ntu,
        product_turbidity_ntu=data.product_turbidity_ntu,
        residual_chlorine_ppm=data.residual_chlorine_ppm,
        tds_feed_ppm=data.tds_feed_ppm,
        tds_product_ppm=data.tds_product_ppm,
        source_method=source_method,
        is_anomaly=data.is_anomaly,
        anomaly_note=data.anomaly_note,
        overdose_flag=data.overdose_flag,
        underdose_flag=data.underdose_flag,
        shift_ref=data.shift_ref,
        notes=data.notes,
        entered_by_id=entered_by_id,
    )
    db.add(obj)
    await db.flush()
    return obj


async def update_treatment_record(
    db: AsyncSession,
    obj: TreatmentChemicalRecord,
    data: TreatmentRecordUpdate,
) -> TreatmentChemicalRecord:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "treatment_type" and value is not None:
            try:
                value = TreatmentType(value)
            except ValueError:
                continue
        if field == "source_method" and value is not None:
            try:
                value = SourceMethod(value)
            except ValueError:
                continue
        if field == "manual_or_auto_dose" and value is not None:
            try:
                value = DosingMode(value)
            except ValueError:
                continue
        if field == "chemical_category" and value is not None:
            try:
                value = ChemicalCategory(value)
            except ValueError:
                continue
        setattr(obj, field, value)
    await db.flush()
    return obj


async def delete_treatment_record(
    db: AsyncSession, obj: TreatmentChemicalRecord
) -> None:
    await db.delete(obj)
    await db.flush()


# ── KPIs ──────────────────────────────────────────────────────────────────────

async def get_chemical_kpis(
    db: AsyncSession,
    *,
    asset_id:          Optional[UUID] = None,
    chemical_id:       Optional[UUID] = None,
    chemical_category: Optional[str]  = None,
    treatment_area:    Optional[str]  = None,
    date_from:         Optional[date] = None,
    date_to:           Optional[date] = None,
) -> ChemicalKPIs:
    clauses = []
    if asset_id:
        clauses.append(TreatmentChemicalRecord.asset_id == asset_id)
    if chemical_id:
        clauses.append(TreatmentChemicalRecord.chemical_id == chemical_id)
    if chemical_category:
        try:
            clauses.append(TreatmentChemicalRecord.chemical_category == ChemicalCategory(chemical_category))
        except ValueError:
            pass
    if treatment_area:
        clauses.append(TreatmentChemicalRecord.treatment_area.ilike(f"%{treatment_area}%"))
    if date_from:
        clauses.append(TreatmentChemicalRecord.date >= date_from)
    if date_to:
        clauses.append(TreatmentChemicalRecord.date <= date_to)

    where = and_(*clauses) if clauses else True

    row = (await db.execute(
        select(
            func.count(TreatmentChemicalRecord.id).label("total_records"),
            func.sum(TreatmentChemicalRecord.quantity_dosed).label("total_qty_dosed"),
            func.sum(TreatmentChemicalRecord.consumed_qty).label("total_consumed"),
            func.sum(TreatmentChemicalRecord.received_qty).label("total_received"),
            func.sum(
                TreatmentChemicalRecord.unit_cost * TreatmentChemicalRecord.consumed_qty
            ).label("total_cost"),
            func.sum(TreatmentChemicalRecord.water_treated_m3).label("total_water_m3"),
            func.sum(TreatmentChemicalRecord.steam_produced_ton).label("total_steam_ton"),
            func.sum(
                func.cast(TreatmentChemicalRecord.overdose_flag, func.Integer.__class__)
            ).label("overdose_count"),
            func.sum(
                func.cast(TreatmentChemicalRecord.underdose_flag, func.Integer.__class__)
            ).label("underdose_count"),
            func.sum(
                func.cast(TreatmentChemicalRecord.is_anomaly, func.Integer.__class__)
            ).label("anomaly_count"),
        ).where(where)
    )).one()

    total_qty  = Decimal(str(row.total_qty_dosed)) if row.total_qty_dosed else None
    total_water = Decimal(str(row.total_water_m3)) if row.total_water_m3 else None
    total_steam = Decimal(str(row.total_steam_ton)) if row.total_steam_ton else None

    per_m3:    Optional[Decimal] = None
    per_steam: Optional[Decimal] = None
    if total_qty and total_water and total_water > 0:
        per_m3 = total_qty / total_water
    if total_qty and total_steam and total_steam > 0:
        per_steam = total_qty / total_steam

    # Low-stock chemicals
    low_stock_rows = list((await db.execute(
        select(WaterTreatmentChemical.chemical_name)
        .where(
            WaterTreatmentChemical.is_active.is_(True),
            WaterTreatmentChemical.low_stock_threshold.is_not(None),
        )
    )).scalars().all())

    return ChemicalKPIs(
        date_from=date_from,
        date_to=date_to,
        total_records=row.total_records or 0,
        total_quantity_dosed=total_qty,
        total_consumed_qty=Decimal(str(row.total_consumed)) if row.total_consumed else None,
        total_received_qty=Decimal(str(row.total_received)) if row.total_received else None,
        total_cost=Decimal(str(row.total_cost)) if row.total_cost else None,
        chemical_per_m3_water=per_m3,
        chemical_per_ton_steam=per_steam,
        overdose_count=int(row.overdose_count or 0),
        underdose_count=int(row.underdose_count or 0),
        anomaly_count=int(row.anomaly_count or 0),
        low_stock_chemicals=list(low_stock_rows),
    )
