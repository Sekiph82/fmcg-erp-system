"""
CRUD helpers for UtilityTariff, UtilityBill, UtilityCostAllocation.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.utility_management import (
    AllocationMethod,
    BillStatus,
    SourceMethod,
    TargetType,
    TariffType,
    UtilityBill,
    UtilityCostAllocation,
    UtilityTariff,
    UtilityType,
)
from app.schemas.utility_billing import (
    AllocationCreate,
    AllocationRead,
    AllocationUpdate,
    BillCreate,
    BillRead,
    BillUpdate,
    TariffCreate,
    TariffRead,
    TariffUpdate,
)

logger = logging.getLogger(__name__)


# ── Record-number generators ───────────────────────────────────────────────────

async def _next_seq(db: AsyncSession, prefix: str, table, col) -> str:
    today = datetime.utcnow().strftime("%Y%m%d")
    like  = f"{prefix}-{today}-%"
    cnt   = (await db.execute(
        select(func.count()).where(col.like(like))
    )).scalar() or 0
    return f"{prefix}-{today}-{cnt + 1:05d}"


# ── Tariff helpers ─────────────────────────────────────────────────────────────

def _tariff_to_read(obj: UtilityTariff) -> TariffRead:
    return TariffRead(
        id=obj.id,
        tariff_code=obj.tariff_code,
        name=obj.name,
        description=obj.description,
        utility_type=obj.utility_type.value if hasattr(obj.utility_type, "value") else str(obj.utility_type),
        tariff_type=obj.tariff_type.value if hasattr(obj.tariff_type, "value") else str(obj.tariff_type),
        supplier_id=obj.supplier_id,
        effective_from=obj.effective_from,
        effective_to=obj.effective_to,
        unit=obj.unit,
        currency_code=obj.currency_code,
        base_rate=obj.base_rate,
        peak_rate=obj.peak_rate,
        offpeak_rate=obj.offpeak_rate,
        demand_rate=obj.demand_rate,
        fixed_charge=obj.fixed_charge,
        tax_rate_pct=obj.tax_rate_pct,
        tax_rule=obj.tax_rule,
        is_active=obj.is_active,
        notes=obj.notes,
        created_at=obj.created_at.isoformat() if obj.created_at else None,
        updated_at=obj.updated_at.isoformat() if obj.updated_at else None,
    )


async def list_tariffs(
    db: AsyncSession,
    *,
    utility_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    as_of_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 200,
) -> List[TariffRead]:
    clauses = []
    if utility_type:
        try:
            clauses.append(UtilityTariff.utility_type == UtilityType(utility_type))
        except ValueError:
            pass
    if is_active is not None:
        clauses.append(UtilityTariff.is_active == is_active)
    if as_of_date:
        clauses.append(UtilityTariff.effective_from <= as_of_date)
        clauses.append(
            (UtilityTariff.effective_to == None) | (UtilityTariff.effective_to >= as_of_date)  # noqa: E711
        )
    where = and_(*clauses) if clauses else True
    rows = list((await db.execute(
        select(UtilityTariff).where(where)
        .order_by(UtilityTariff.effective_from.desc())
        .offset(skip).limit(limit)
    )).scalars())
    return [_tariff_to_read(r) for r in rows]


async def get_tariff(db: AsyncSession, tariff_id: UUID) -> Optional[UtilityTariff]:
    return (await db.execute(
        select(UtilityTariff).where(UtilityTariff.id == tariff_id)
    )).scalar_one_or_none()


async def create_tariff(db: AsyncSession, data: TariffCreate, created_by_id: Optional[UUID] = None) -> TariffRead:
    try:
        utype = UtilityType(data.utility_type)
    except ValueError:
        utype = UtilityType.OTHER
    try:
        ttype = TariffType(data.tariff_type)
    except ValueError:
        ttype = TariffType.FLAT

    obj = UtilityTariff(
        tariff_code=data.tariff_code,
        name=data.name,
        description=data.description,
        utility_type=utype,
        tariff_type=ttype,
        supplier_id=data.supplier_id,
        effective_from=data.effective_from,
        effective_to=data.effective_to,
        unit=data.unit,
        currency_code=data.currency_code,
        base_rate=data.base_rate,
        peak_rate=data.peak_rate,
        offpeak_rate=data.offpeak_rate,
        demand_rate=data.demand_rate,
        fixed_charge=data.fixed_charge,
        tax_rate_pct=data.tax_rate_pct,
        tax_rule=data.tax_rule,
        is_active=data.is_active,
        notes=data.notes,
        created_by_id=created_by_id,
    )
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return _tariff_to_read(obj)


async def update_tariff(db: AsyncSession, obj: UtilityTariff, data: TariffUpdate) -> TariffRead:
    for field, val in data.model_dump(exclude_unset=True).items():
        if field == "tariff_type" and val:
            try:
                val = TariffType(val)
            except ValueError:
                pass
        setattr(obj, field, val)
    await db.flush()
    await db.refresh(obj)
    return _tariff_to_read(obj)


async def delete_tariff(db: AsyncSession, obj: UtilityTariff) -> None:
    await db.delete(obj)
    await db.flush()


# ── Bill helpers ───────────────────────────────────────────────────────────────

def _bill_to_read(obj: UtilityBill) -> BillRead:
    return BillRead(
        id=obj.id,
        bill_no=obj.bill_no,
        utility_type=obj.utility_type.value if hasattr(obj.utility_type, "value") else str(obj.utility_type),
        provider_name=obj.provider_name,
        supplier_id=obj.supplier_id,
        tariff_id=obj.tariff_id,
        tariff_code=obj.tariff_code,
        bill_reference=obj.bill_reference,
        billing_period_from=obj.billing_period_from,
        billing_period_to=obj.billing_period_to,
        invoice_date=obj.invoice_date,
        due_date=obj.due_date,
        consumption_quantity=obj.consumption_quantity,
        consumption_unit=obj.consumption_unit,
        unit_rate=obj.unit_rate,
        base_charge=obj.base_charge,
        energy_charge=obj.energy_charge,
        demand_charge=obj.demand_charge,
        fixed_charge=obj.fixed_charge,
        surcharge_amount=obj.surcharge_amount,
        tax_amount=obj.tax_amount,
        total_amount=obj.total_amount,
        currency_code=obj.currency_code,
        status=obj.status.value if hasattr(obj.status, "value") else str(obj.status),
        payment_date=obj.payment_date,
        document_ref=obj.document_ref,
        notes=obj.notes,
        created_at=obj.created_at.isoformat() if obj.created_at else None,
        updated_at=obj.updated_at.isoformat() if obj.updated_at else None,
    )


async def list_bills(
    db: AsyncSession,
    *,
    utility_type: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    supplier_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 200,
) -> List[BillRead]:
    clauses = []
    if utility_type:
        try:
            clauses.append(UtilityBill.utility_type == UtilityType(utility_type))
        except ValueError:
            pass
    if status:
        try:
            clauses.append(UtilityBill.status == BillStatus(status))
        except ValueError:
            pass
    if date_from:
        clauses.append(UtilityBill.billing_period_from >= date_from)
    if date_to:
        clauses.append(UtilityBill.billing_period_to <= date_to)
    if supplier_id:
        clauses.append(UtilityBill.supplier_id == supplier_id)
    where = and_(*clauses) if clauses else True
    rows = list((await db.execute(
        select(UtilityBill).where(where)
        .order_by(UtilityBill.billing_period_from.desc())
        .offset(skip).limit(limit)
    )).scalars())
    return [_bill_to_read(r) for r in rows]


async def get_bill(db: AsyncSession, bill_id: UUID) -> Optional[UtilityBill]:
    return (await db.execute(
        select(UtilityBill).where(UtilityBill.id == bill_id)
    )).scalar_one_or_none()


async def create_bill(db: AsyncSession, data: BillCreate, created_by_id: Optional[UUID] = None) -> BillRead:
    try:
        utype = UtilityType(data.utility_type)
    except ValueError:
        utype = UtilityType.OTHER
    try:
        bstatus = BillStatus(data.status)
    except ValueError:
        bstatus = BillStatus.RECEIVED

    bill_no = await _next_seq(db, "BILL", UtilityBill, UtilityBill.bill_no)

    obj = UtilityBill(
        bill_no=bill_no,
        utility_type=utype,
        provider_name=data.provider_name,
        supplier_id=data.supplier_id,
        tariff_id=data.tariff_id,
        tariff_code=data.tariff_code,
        bill_reference=data.bill_reference,
        billing_period_from=data.billing_period_from,
        billing_period_to=data.billing_period_to,
        invoice_date=data.invoice_date,
        due_date=data.due_date,
        consumption_quantity=data.consumption_quantity,
        consumption_unit=data.consumption_unit,
        unit_rate=data.unit_rate,
        base_charge=data.base_charge,
        energy_charge=data.energy_charge,
        demand_charge=data.demand_charge,
        fixed_charge=data.fixed_charge,
        surcharge_amount=data.surcharge_amount,
        tax_amount=data.tax_amount,
        total_amount=data.total_amount,
        currency_code=data.currency_code,
        status=bstatus,
        payment_date=data.payment_date,
        document_ref=data.document_ref,
        notes=data.notes,
        created_by_id=created_by_id,
    )
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return _bill_to_read(obj)


async def update_bill(db: AsyncSession, obj: UtilityBill, data: BillUpdate) -> BillRead:
    for field, val in data.model_dump(exclude_unset=True).items():
        if field == "status" and val:
            try:
                val = BillStatus(val)
            except ValueError:
                pass
        setattr(obj, field, val)
    await db.flush()
    await db.refresh(obj)
    return _bill_to_read(obj)


async def delete_bill(db: AsyncSession, obj: UtilityBill) -> None:
    await db.delete(obj)
    await db.flush()


# ── Allocation helpers ─────────────────────────────────────────────────────────

def _alloc_to_read(obj: UtilityCostAllocation) -> AllocationRead:
    def _ev(v):
        return v.value if hasattr(v, "value") else str(v) if v else None

    return AllocationRead(
        id=obj.id,
        allocation_no=obj.allocation_no,
        utility_type=_ev(obj.utility_type),
        allocation_date=obj.allocation_date,
        period_start=obj.period_start,
        period_end=obj.period_end,
        allocation_method=_ev(obj.allocation_method),
        target_type=_ev(obj.target_type),
        target_id=obj.target_id,
        target_name=obj.target_name,
        department=obj.department,
        production_line=obj.production_line,
        building_area=obj.building_area,
        machine_ref=obj.machine_ref,
        production_order_id=obj.production_order_id,
        batch_no=obj.batch_no,
        product_id=obj.product_id,
        source_cost=obj.source_cost,
        allocation_basis=obj.allocation_basis,
        allocation_basis_unit=obj.allocation_basis_unit,
        allocated_quantity=obj.allocated_quantity,
        quantity_unit=obj.quantity_unit,
        production_volume_kg=obj.production_volume_kg,
        total_cost=obj.total_cost,
        allocated_cost=obj.allocated_cost,
        currency_code=obj.currency_code,
        cost_per_unit=obj.cost_per_unit,
        cost_per_ton=obj.cost_per_ton,
        bill_id=obj.bill_id,
        source_method=_ev(obj.source_method),
        is_approved=obj.is_approved,
        notes=obj.notes,
        created_at=obj.created_at.isoformat() if obj.created_at else None,
        updated_at=obj.updated_at.isoformat() if obj.updated_at else None,
    )


async def list_allocations(
    db: AsyncSession,
    *,
    utility_type: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    department: Optional[str] = None,
    production_line: Optional[str] = None,
    machine_ref: Optional[str] = None,
    batch_no: Optional[str] = None,
    bill_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    is_approved: Optional[bool] = None,
    skip: int = 0,
    limit: int = 500,
) -> List[AllocationRead]:
    clauses = []
    if utility_type:
        try:
            clauses.append(UtilityCostAllocation.utility_type == UtilityType(utility_type))
        except ValueError:
            pass
    if target_type:
        try:
            clauses.append(UtilityCostAllocation.target_type == TargetType(target_type))
        except ValueError:
            pass
    if target_id:
        clauses.append(UtilityCostAllocation.target_id == target_id)
    if department:
        clauses.append(UtilityCostAllocation.department == department)
    if production_line:
        clauses.append(UtilityCostAllocation.production_line == production_line)
    if machine_ref:
        clauses.append(UtilityCostAllocation.machine_ref == machine_ref)
    if batch_no:
        clauses.append(UtilityCostAllocation.batch_no == batch_no)
    if bill_id:
        clauses.append(UtilityCostAllocation.bill_id == bill_id)
    if date_from:
        clauses.append(UtilityCostAllocation.allocation_date >= date_from)
    if date_to:
        clauses.append(UtilityCostAllocation.allocation_date <= date_to)
    if is_approved is not None:
        clauses.append(UtilityCostAllocation.is_approved == is_approved)
    where = and_(*clauses) if clauses else True
    rows = list((await db.execute(
        select(UtilityCostAllocation).where(where)
        .order_by(UtilityCostAllocation.allocation_date.desc())
        .offset(skip).limit(limit)
    )).scalars())
    return [_alloc_to_read(r) for r in rows]


async def get_allocation(db: AsyncSession, alloc_id: UUID) -> Optional[UtilityCostAllocation]:
    return (await db.execute(
        select(UtilityCostAllocation).where(UtilityCostAllocation.id == alloc_id)
    )).scalar_one_or_none()


async def create_allocation(
    db: AsyncSession,
    data: AllocationCreate,
    created_by_id: Optional[UUID] = None,
) -> AllocationRead:
    try:
        utype = UtilityType(data.utility_type)
    except ValueError:
        utype = UtilityType.OTHER
    try:
        method = AllocationMethod(data.allocation_method)
    except ValueError:
        method = AllocationMethod.METERED
    try:
        src_method = SourceMethod(data.source_method)
    except ValueError:
        src_method = SourceMethod.CALCULATED
    ttype = None
    if data.target_type:
        try:
            ttype = TargetType(data.target_type)
        except ValueError:
            pass

    alloc_no = await _next_seq(db, "ALLOC", UtilityCostAllocation, UtilityCostAllocation.allocation_no)

    obj = UtilityCostAllocation(
        allocation_no=alloc_no,
        utility_type=utype,
        allocation_date=data.allocation_date,
        period_start=data.period_start,
        period_end=data.period_end,
        allocation_method=method,
        target_type=ttype,
        target_id=data.target_id,
        target_name=data.target_name,
        department=data.department,
        production_line=data.production_line,
        building_area=data.building_area,
        machine_ref=data.machine_ref,
        production_order_id=data.production_order_id,
        batch_no=data.batch_no,
        product_id=data.product_id,
        source_cost=data.source_cost,
        allocation_basis=data.allocation_basis,
        allocation_basis_unit=data.allocation_basis_unit,
        allocated_quantity=data.allocated_quantity,
        quantity_unit=data.quantity_unit,
        production_volume_kg=data.production_volume_kg,
        total_cost=data.total_cost,
        allocated_cost=data.allocated_cost,
        currency_code=data.currency_code,
        cost_per_unit=data.cost_per_unit,
        cost_per_ton=data.cost_per_ton,
        bill_id=data.bill_id,
        source_method=src_method,
        notes=data.notes,
        created_by_id=created_by_id,
    )
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return _alloc_to_read(obj)


async def update_allocation(
    db: AsyncSession,
    obj: UtilityCostAllocation,
    data: AllocationUpdate,
) -> AllocationRead:
    for field, val in data.model_dump(exclude_unset=True).items():
        if field == "allocation_method" and val:
            try:
                val = AllocationMethod(val)
            except ValueError:
                pass
        elif field == "target_type" and val:
            try:
                val = TargetType(val)
            except ValueError:
                pass
        setattr(obj, field, val)
    await db.flush()
    await db.refresh(obj)
    return _alloc_to_read(obj)


async def delete_allocation(db: AsyncSession, obj: UtilityCostAllocation) -> None:
    await db.delete(obj)
    await db.flush()
