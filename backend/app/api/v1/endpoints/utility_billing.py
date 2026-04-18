"""
Utility Billing, Tariffs & Cost Allocation — FastAPI router.

Prefixed at /billing by the main router.

Routes:
  Tariffs
    GET  /tariffs                    list with filters
    POST /tariffs                    create
    GET  /tariffs/lookup             find active tariff for a date
    GET  /tariffs/{id}               get one
    PATCH /tariffs/{id}              update
    DELETE /tariffs/{id}             delete

  Bills
    GET  /bills/kpis                 KPI summary
    GET  /bills/export/csv           CSV download
    GET  /bills                      list with filters
    POST /bills                      create
    GET  /bills/{id}                 get one
    PATCH /bills/{id}                update
    DELETE /bills/{id}               delete

  Allocations
    GET  /allocations/report         cost report grouped by dimension
    GET  /allocations/export/csv     CSV download
    POST /allocations/run-engine     run allocation engine for a bill
    GET  /allocations                list with filters
    POST /allocations                create single allocation
    GET  /allocations/{id}           get one
    PATCH /allocations/{id}          update / approve
    DELETE /allocations/{id}         delete
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
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.crud.utility_billing import (
    create_allocation,
    create_bill,
    create_tariff,
    delete_allocation,
    delete_bill,
    delete_tariff,
    get_allocation,
    get_bill,
    get_tariff,
    list_allocations,
    list_bills,
    list_tariffs,
    update_allocation,
    update_bill,
    update_tariff,
)
from app.schemas.utility_billing import (
    AllocationCreate,
    AllocationEngineRequest,
    AllocationEngineResult,
    AllocationRead,
    AllocationReport,
    AllocationUpdate,
    BillingKPIs,
    BillCreate,
    BillRead,
    BillUpdate,
    TariffCreate,
    TariffRead,
    TariffUpdate,
)
from app.services.utility_billing_service import (
    get_allocation_report,
    get_billing_kpis,
    lookup_tariff,
    run_allocation_engine,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════════
# Tariffs
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/tariffs/lookup", response_model=Optional[TariffRead])
async def tariff_lookup(
    utility_type: str = Query(...),
    as_of: date   = Query(default_factory=date.today),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    tariff = await lookup_tariff(db, utility_type=utility_type, as_of=as_of)
    return None if tariff is None else TariffRead.model_validate(tariff)


@router.get("/tariffs", response_model=List[TariffRead])
async def list_tariffs_route(
    utility_type: Optional[str] = Query(None),
    is_active:    Optional[bool] = Query(None),
    as_of_date:   Optional[date] = Query(None),
    skip:         int = Query(0, ge=0),
    limit:        int = Query(200, le=1000),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return await list_tariffs(db, utility_type=utility_type, is_active=is_active,
                              as_of_date=as_of_date, skip=skip, limit=limit)


@router.post("/tariffs", response_model=TariffRead, status_code=201)
async def create_tariff_route(
    body: TariffCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    async with db.begin():
        return await create_tariff(db, body, created_by_id=user.get("id"))


@router.get("/tariffs/{tariff_id}", response_model=TariffRead)
async def get_tariff_route(
    tariff_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    obj = await get_tariff(db, tariff_id)
    if not obj:
        raise HTTPException(404, "Tariff not found")
    from app.crud.utility_billing import _tariff_to_read
    return _tariff_to_read(obj)


@router.patch("/tariffs/{tariff_id}", response_model=TariffRead)
async def update_tariff_route(
    tariff_id: UUID,
    body: TariffUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    async with db.begin():
        obj = await get_tariff(db, tariff_id)
        if not obj:
            raise HTTPException(404, "Tariff not found")
        return await update_tariff(db, obj, body)


@router.delete("/tariffs/{tariff_id}", status_code=204)
async def delete_tariff_route(
    tariff_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    async with db.begin():
        obj = await get_tariff(db, tariff_id)
        if not obj:
            raise HTTPException(404, "Tariff not found")
        await delete_tariff(db, obj)


# ═══════════════════════════════════════════════════════════════════════════════
# Bills
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/bills/kpis", response_model=BillingKPIs)
async def billing_kpis(
    utility_type: Optional[str] = Query(None),
    date_from:    Optional[date] = Query(None),
    date_to:      Optional[date] = Query(None),
    currency_code: str = Query("USD"),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return await get_billing_kpis(db, utility_type=utility_type,
                                  date_from=date_from, date_to=date_to,
                                  currency_code=currency_code)


@router.get("/bills/export/csv")
async def export_bills_csv(
    utility_type: Optional[str] = Query(None),
    status:       Optional[str] = Query(None),
    date_from:    Optional[date] = Query(None),
    date_to:      Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    rows = await list_bills(db, utility_type=utility_type, status=status,
                            date_from=date_from, date_to=date_to, limit=5000)
    buf = io.StringIO()
    fields = [
        "bill_no", "utility_type", "provider_name", "billing_period_from",
        "billing_period_to", "tariff_code", "consumption_quantity",
        "consumption_unit", "unit_rate", "base_charge", "energy_charge",
        "demand_charge", "fixed_charge", "surcharge_amount", "tax_amount",
        "total_amount", "currency_code", "status", "due_date", "payment_date",
        "document_ref", "notes",
    ]
    w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r.model_dump())
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": 'attachment; filename="utility_bills.csv"'})


@router.get("/bills", response_model=List[BillRead])
async def list_bills_route(
    utility_type: Optional[str] = Query(None),
    status:       Optional[str] = Query(None),
    date_from:    Optional[date] = Query(None),
    date_to:      Optional[date] = Query(None),
    supplier_id:  Optional[UUID] = Query(None),
    skip:         int = Query(0, ge=0),
    limit:        int = Query(200, le=1000),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return await list_bills(db, utility_type=utility_type, status=status,
                            date_from=date_from, date_to=date_to,
                            supplier_id=supplier_id, skip=skip, limit=limit)


@router.post("/bills", response_model=BillRead, status_code=201)
async def create_bill_route(
    body: BillCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    async with db.begin():
        return await create_bill(db, body, created_by_id=user.get("id"))


@router.get("/bills/{bill_id}", response_model=BillRead)
async def get_bill_route(
    bill_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    obj = await get_bill(db, bill_id)
    if not obj:
        raise HTTPException(404, "Bill not found")
    from app.crud.utility_billing import _bill_to_read
    return _bill_to_read(obj)


@router.patch("/bills/{bill_id}", response_model=BillRead)
async def update_bill_route(
    bill_id: UUID,
    body: BillUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    async with db.begin():
        obj = await get_bill(db, bill_id)
        if not obj:
            raise HTTPException(404, "Bill not found")
        return await update_bill(db, obj, body)


@router.delete("/bills/{bill_id}", status_code=204)
async def delete_bill_route(
    bill_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    async with db.begin():
        obj = await get_bill(db, bill_id)
        if not obj:
            raise HTTPException(404, "Bill not found")
        await delete_bill(db, obj)


# ═══════════════════════════════════════════════════════════════════════════════
# Allocations
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/allocations/report", response_model=AllocationReport)
async def allocation_report(
    group_by:     str           = Query("target_type"),
    utility_type: Optional[str] = Query(None),
    date_from:    Optional[date] = Query(None),
    date_to:      Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return await get_allocation_report(db, group_by=group_by,
                                       utility_type=utility_type,
                                       date_from=date_from, date_to=date_to)


@router.get("/allocations/export/csv")
async def export_allocations_csv(
    utility_type:    Optional[str]  = Query(None),
    target_type:     Optional[str]  = Query(None),
    date_from:       Optional[date] = Query(None),
    date_to:         Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    rows = await list_allocations(db, utility_type=utility_type,
                                  target_type=target_type,
                                  date_from=date_from, date_to=date_to, limit=10000)
    buf = io.StringIO()
    fields = [
        "allocation_no", "utility_type", "allocation_date", "period_start", "period_end",
        "allocation_method", "target_type", "target_id", "target_name",
        "department", "production_line", "machine_ref", "batch_no",
        "source_cost", "allocation_basis", "allocation_basis_unit",
        "allocated_quantity", "quantity_unit", "total_cost", "allocated_cost",
        "currency_code", "cost_per_unit", "cost_per_ton", "is_approved", "notes",
    ]
    w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r.model_dump())
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": 'attachment; filename="cost_allocations.csv"'})


@router.post("/allocations/run-engine", response_model=AllocationEngineResult)
async def run_engine(
    body: AllocationEngineRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    try:
        async with db.begin():
            return await run_allocation_engine(db, body, created_by_id=user.get("id"))
    except ValueError as exc:
        raise HTTPException(422, str(exc))


@router.get("/allocations", response_model=List[AllocationRead])
async def list_allocations_route(
    utility_type:    Optional[str]  = Query(None),
    target_type:     Optional[str]  = Query(None),
    target_id:       Optional[str]  = Query(None),
    department:      Optional[str]  = Query(None),
    production_line: Optional[str]  = Query(None),
    machine_ref:     Optional[str]  = Query(None),
    batch_no:        Optional[str]  = Query(None),
    bill_id:         Optional[UUID] = Query(None),
    date_from:       Optional[date] = Query(None),
    date_to:         Optional[date] = Query(None),
    is_approved:     Optional[bool] = Query(None),
    skip:            int = Query(0, ge=0),
    limit:           int = Query(500, le=2000),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return await list_allocations(db, utility_type=utility_type,
                                  target_type=target_type, target_id=target_id,
                                  department=department, production_line=production_line,
                                  machine_ref=machine_ref, batch_no=batch_no,
                                  bill_id=bill_id, date_from=date_from, date_to=date_to,
                                  is_approved=is_approved, skip=skip, limit=limit)


@router.post("/allocations", response_model=AllocationRead, status_code=201)
async def create_allocation_route(
    body: AllocationCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    async with db.begin():
        return await create_allocation(db, body, created_by_id=user.get("id"))


@router.get("/allocations/{alloc_id}", response_model=AllocationRead)
async def get_allocation_route(
    alloc_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    obj = await get_allocation(db, alloc_id)
    if not obj:
        raise HTTPException(404, "Allocation not found")
    from app.crud.utility_billing import _alloc_to_read
    return _alloc_to_read(obj)


@router.patch("/allocations/{alloc_id}", response_model=AllocationRead)
async def update_allocation_route(
    alloc_id: UUID,
    body: AllocationUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    async with db.begin():
        obj = await get_allocation(db, alloc_id)
        if not obj:
            raise HTTPException(404, "Allocation not found")
        if body.is_approved is True and not obj.is_approved:
            obj.approved_by_id = user.get("id")
        return await update_allocation(db, obj, body)


@router.delete("/allocations/{alloc_id}", status_code=204)
async def delete_allocation_route(
    alloc_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    async with db.begin():
        obj = await get_allocation(db, alloc_id)
        if not obj:
            raise HTTPException(404, "Allocation not found")
        await delete_allocation(db, obj)
