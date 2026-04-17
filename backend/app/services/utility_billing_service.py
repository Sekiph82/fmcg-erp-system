"""
Utility Billing Service — KPI aggregation, allocation engine, cost reports.

Allocation methods supported:
  METERED              — quantity already measured; just price at tariff rate
  RUNTIME              — pro-rata by machine runtime hours from machine_consumption_records
  STANDARD_CONSUMPTION — standard rate × actual output volume
  PROPORTIONAL         — fixed percentage split across targets
  COST_CENTER          — one-to-one mapping to a cost centre
  FIXED / CALCULATED   — legacy pass-through
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.utility_billing import (
    _alloc_to_read,
    _next_seq,
    create_allocation,
    get_bill,
)
from app.models.utility_management import (
    AllocationMethod,
    BillStatus,
    MachineConsumptionRecord,
    SourceMethod,
    TargetType,
    UtilityBill,
    UtilityCostAllocation,
    UtilityTariff,
    UtilityType,
)
from app.schemas.utility_billing import (
    AllocationEngineRequest,
    AllocationEngineResult,
    AllocationRead,
    AllocationReport,
    AllocationReportRow,
    BillingKPIs,
)

logger = logging.getLogger(__name__)

_D = lambda v: Decimal(str(v)) if v is not None else Decimal("0")
_DN = lambda v: Decimal(str(v)) if v is not None else None
_R = lambda v, dp=2: Decimal(str(round(float(v), dp))) if v is not None else None


# ── KPIs ───────────────────────────────────────────────────────────────────────

async def get_billing_kpis(
    db: AsyncSession,
    *,
    utility_type: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    currency_code: str = "USD",
) -> BillingKPIs:
    clauses = []
    if utility_type:
        try:
            clauses.append(UtilityBill.utility_type == UtilityType(utility_type))
        except ValueError:
            pass
    if date_from:
        clauses.append(UtilityBill.billing_period_from >= date_from)
    if date_to:
        clauses.append(UtilityBill.billing_period_to <= date_to)
    where = and_(*clauses) if clauses else True

    agg = (await db.execute(
        select(
            func.count().label("cnt"),
            func.sum(UtilityBill.total_amount).label("total_billed"),
            func.sum(UtilityBill.tax_amount).label("total_tax"),
            func.sum(UtilityBill.consumption_quantity).label("total_cons"),
            func.max(UtilityBill.consumption_unit).label("unit"),
            func.avg(UtilityBill.unit_rate).label("avg_rate"),
            # Unpaid = RECEIVED + OVERDUE
            func.sum(
                UtilityBill.total_amount
            ).filter(
                UtilityBill.status.in_([BillStatus.RECEIVED, BillStatus.OVERDUE])
            ).label("unpaid"),
            func.count().filter(
                UtilityBill.status == BillStatus.OVERDUE
            ).label("overdue_cnt"),
            func.count().filter(
                UtilityBill.status == BillStatus.DISPUTED
            ).label("disputed_cnt"),
        ).where(where)
    )).one()

    return BillingKPIs(
        date_from=date_from.isoformat() if date_from else None,
        date_to=date_to.isoformat() if date_to else None,
        utility_type=utility_type,
        total_bills=int(agg.cnt or 0),
        total_billed_amount=_D(agg.total_billed),
        total_tax_amount=_DN(agg.total_tax),
        total_consumption=_DN(agg.total_cons),
        consumption_unit=agg.unit,
        avg_unit_rate=_R(agg.avg_rate, 6),
        unpaid_amount=_DN(agg.unpaid),
        overdue_count=int(agg.overdue_cnt or 0),
        disputed_count=int(agg.disputed_cnt or 0),
        currency_code=currency_code,
    )


# ── Cost report ────────────────────────────────────────────────────────────────

async def get_allocation_report(
    db: AsyncSession,
    *,
    group_by: str = "target_type",  # "target_type" | "department" | "production_line" | "machine_ref" | "batch_no"
    utility_type: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> AllocationReport:
    clauses = []
    if utility_type:
        try:
            clauses.append(UtilityCostAllocation.utility_type == UtilityType(utility_type))
        except ValueError:
            pass
    if date_from:
        clauses.append(UtilityCostAllocation.allocation_date >= date_from)
    if date_to:
        clauses.append(UtilityCostAllocation.allocation_date <= date_to)
    where = and_(*clauses) if clauses else True

    _COL_MAP = {
        "target_type":     UtilityCostAllocation.target_type,
        "target_id":       UtilityCostAllocation.target_id,
        "department":      UtilityCostAllocation.department,
        "production_line": UtilityCostAllocation.production_line,
        "machine_ref":     UtilityCostAllocation.machine_ref,
        "batch_no":        UtilityCostAllocation.batch_no,
    }
    dim_col = _COL_MAP.get(group_by, UtilityCostAllocation.target_type)

    rows_raw = list((await db.execute(
        select(
            dim_col.label("gkey"),
            UtilityCostAllocation.target_name.label("tname"),
            UtilityCostAllocation.utility_type.label("utype"),
            func.sum(UtilityCostAllocation.allocated_cost).label("cost"),
            func.sum(UtilityCostAllocation.allocated_quantity).label("qty"),
            func.max(UtilityCostAllocation.quantity_unit).label("unit"),
            func.count().label("cnt"),
        )
        .where(where)
        .group_by(dim_col, UtilityCostAllocation.target_name, UtilityCostAllocation.utility_type)
        .order_by(func.sum(UtilityCostAllocation.allocated_cost).desc())
    )).all())

    grand = sum(_D(r.cost) for r in rows_raw) or Decimal("1")

    result_rows = []
    for r in rows_raw:
        cost = _D(r.cost)
        qty  = _DN(r.qty)
        cpu  = _R(cost / qty, 4) if qty and qty > 0 else None
        result_rows.append(AllocationReportRow(
            target_type=r.gkey.value if hasattr(r.gkey, "value") else str(r.gkey) if r.gkey else None,
            target_id=str(r.gkey) if r.gkey else None,
            target_name=r.tname,
            utility_type=r.utype.value if hasattr(r.utype, "value") else str(r.utype) if r.utype else None,
            allocated_cost=cost,
            allocated_quantity=qty,
            quantity_unit=r.unit,
            cost_per_unit=cpu,
            record_count=int(r.cnt or 0),
        ))

    return AllocationReport(
        period_start=date_from.isoformat() if date_from else None,
        period_end=date_to.isoformat() if date_to else None,
        utility_type=utility_type,
        group_by=group_by,
        rows=result_rows,
        grand_total=grand,
    )


# ── Allocation engine ──────────────────────────────────────────────────────────

async def run_allocation_engine(
    db: AsyncSession,
    req: AllocationEngineRequest,
    created_by_id: Optional[UUID] = None,
) -> AllocationEngineResult:
    """
    Distribute a bill's total cost across the provided targets using the
    requested allocation method.

    PROPORTIONAL / COST_CENTER / FIXED:
        basis_value is the weight (e.g., %) for each target.
        allocated_cost = total_cost × (basis_i / Σ basis_j)

    RUNTIME:
        basis_value is runtime hours supplied by the caller (pulled from
        MachineConsumptionRecord or provided directly).
        Same proportional split.

    STANDARD_CONSUMPTION:
        basis_value is the standard consumption quantity for the target.
        Same proportional split.

    METERED / CALCULATED:
        basis_value is the directly measured consumption; each target
        gets exactly its own quantity priced at the bill's implied unit rate.
    """
    bill = await get_bill(db, req.bill_id)
    if bill is None:
        raise ValueError(f"Bill {req.bill_id} not found")

    utype_str = bill.utility_type.value if hasattr(bill.utility_type, "value") else str(bill.utility_type)
    total_cost = _D(bill.total_amount)
    total_basis = sum(_D(t.basis_value) for t in req.targets) or Decimal("1")

    try:
        method = AllocationMethod(req.allocation_method)
    except ValueError:
        method = AllocationMethod.PROPORTIONAL

    created: List[AllocationRead] = []

    for target in req.targets:
        basis  = _D(target.basis_value)
        if method in (AllocationMethod.METERED, AllocationMethod.CALCULATED):
            # basis_value = measured quantity; price at bill's implied rate
            implied_rate = total_cost / (_D(bill.consumption_quantity) or Decimal("1")) if bill.consumption_quantity else Decimal("0")
            alloc_cost = _R(basis * implied_rate, 4) or Decimal("0")
        else:
            # Proportional split
            alloc_cost = _R(total_cost * basis / total_basis, 4) or Decimal("0")

        try:
            ttype = TargetType(target.target_type.upper())
        except (ValueError, AttributeError):
            ttype = None

        alloc_no = await _next_seq(db, "ALLOC", UtilityCostAllocation, UtilityCostAllocation.allocation_no)

        obj = UtilityCostAllocation(
            allocation_no=alloc_no,
            utility_type=bill.utility_type,
            allocation_date=req.allocation_date,
            period_start=bill.billing_period_from,
            period_end=bill.billing_period_to,
            allocation_method=method,
            target_type=ttype,
            target_id=target.target_id,
            target_name=target.target_name,
            source_cost=total_cost,
            allocation_basis=basis,
            allocation_basis_unit=target.basis_unit,
            total_cost=total_cost,
            allocated_cost=alloc_cost,
            currency_code=req.currency_code,
            bill_id=bill.id,
            source_method=SourceMethod.CALCULATED,
            created_by_id=created_by_id,
        )
        db.add(obj)
        await db.flush()
        await db.refresh(obj)
        created.append(_alloc_to_read(obj))

    return AllocationEngineResult(
        bill_id=bill.id,
        bill_no=bill.bill_no,
        total_cost=total_cost,
        allocation_method=req.allocation_method,
        allocations_created=len(created),
        rows=created,
    )


# ── Tariff lookup ──────────────────────────────────────────────────────────────

async def lookup_tariff(
    db: AsyncSession,
    *,
    utility_type: str,
    as_of: date,
) -> Optional[UtilityTariff]:
    """Return the active tariff for a utility type on a given date."""
    try:
        utype = UtilityType(utility_type.upper())
    except ValueError:
        return None

    return (await db.execute(
        select(UtilityTariff)
        .where(
            and_(
                UtilityTariff.utility_type == utype,
                UtilityTariff.is_active == True,      # noqa: E712
                UtilityTariff.effective_from <= as_of,
                (UtilityTariff.effective_to == None)  # noqa: E711
                | (UtilityTariff.effective_to >= as_of),
            )
        )
        .order_by(UtilityTariff.effective_from.desc())
        .limit(1)
    )).scalar_one_or_none()
