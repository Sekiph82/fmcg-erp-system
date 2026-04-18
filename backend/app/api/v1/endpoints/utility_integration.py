"""
Utility Integration — FastAPI router.

Exposes cross-module integration endpoints that wire the Utility Management
module to Production, Inventory, Maintenance, Quality, and Finance.

Prefixed at /utility-management by the main router.

Routes:
  GET  /integration/production/{order_id}/utility-summary        → ProductionUtilitySummary
  POST /integration/billing/{bill_id}/post-to-gl                 → PostBillToGLResult
  POST /integration/billing/{bill_id}/post-to-production-costs   → PostAllocationsResult
  POST /integration/chemicals/{record_id}/sync-to-inventory      → ChemicalSyncResult
  GET  /integration/assets/{asset_id}/maintenance-status         → MaintenanceStatusResult
  POST /integration/alarms/{event_id}/maintenance-action         → MaintenanceActionResult
  GET  /integration/assets/{asset_id}/quality-inspections        → List[QualityInspectionSummary]
  GET  /integration/health                                        → {"status": "ok", ...}
"""
from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.schemas.utility_integration import (
    ChemicalSyncRequest,
    ChemicalSyncResult,
    MaintenanceActionRequest,
    MaintenanceActionResult,
    MaintenanceStatusResult,
    PostAllocationsResult,
    PostBillToGLRequest,
    PostBillToGLResult,
    ProductionUtilitySummary,
    QualityInspectionSummary,
    UtilityTypeBreakdown,
)
from app.services.utility_integration_service import (
    create_maintenance_action_from_alarm,
    get_maintenance_status_for_utility_asset,
    get_production_utility_summary,
    get_quality_inspections_for_utility,
    post_allocations_to_production_costs,
    post_bill_to_finance,
    sync_chemical_to_inventory,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Health check ──────────────────────────────────────────────────────────────

@router.get("/integration/health")
async def integration_health() -> dict:
    """Liveness probe for the utility integration sub-module."""
    return {"status": "ok", "module": "utility_integration"}


# ── Production ────────────────────────────────────────────────────────────────

@router.get(
    "/integration/production/{order_id}/utility-summary",
    response_model=ProductionUtilitySummary,
    summary="Get utility consumption summary for a production order",
)
async def get_production_utility_summary_route(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProductionUtilitySummary:
    try:
        result = await get_production_utility_summary(
            db, production_order_id=order_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ProductionUtilitySummary(
        production_order_id=result["production_order_id"],
        order_no=result["order_no"],
        total_utility_cost=result["total_utility_cost"],
        by_type=[
            UtilityTypeBreakdown(
                utility_type=item["utility_type"],
                quantity=item["quantity"],
                unit=item["unit"],
                cost=item["cost"],
            )
            for item in result["by_type"]
        ],
    )


# ── Finance / Billing ─────────────────────────────────────────────────────────

@router.post(
    "/integration/billing/{bill_id}/post-to-gl",
    response_model=PostBillToGLResult,
    summary="Post a utility bill to the general ledger",
)
async def post_bill_to_gl_route(
    bill_id: UUID,
    body: PostBillToGLRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PostBillToGLResult:
    try:
        async with db.begin():
            result = await post_bill_to_finance(
                db,
                bill_id=bill_id,
                debit_account_id=body.debit_account_id,
                credit_account_id=body.credit_account_id,
                posted_by_id=current_user.id,
            )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return PostBillToGLResult(
        bill_id=result["bill_id"],
        journal_entry_id=result["journal_entry_id"],
        entry_no=result["entry_no"],
        amount=result["amount"],
    )


@router.post(
    "/integration/billing/{bill_id}/post-to-production-costs",
    response_model=PostAllocationsResult,
    summary="Post approved utility cost allocations as production cost entries",
)
async def post_allocations_route(
    bill_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PostAllocationsResult:
    try:
        async with db.begin():
            result = await post_allocations_to_production_costs(
                db,
                bill_id=bill_id,
                posted_by_id=current_user.id,
            )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return PostAllocationsResult(
        bill_id=result["bill_id"],
        entries_created=result["entries_created"],
        total_cost_posted=result["total_cost_posted"],
    )


# ── Inventory ─────────────────────────────────────────────────────────────────

@router.post(
    "/integration/chemicals/{record_id}/sync-to-inventory",
    response_model=ChemicalSyncResult,
    summary="Create an inventory stock movement for a chemical dosing record",
)
async def sync_chemical_route(
    record_id: UUID,
    body: ChemicalSyncRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ChemicalSyncResult:
    try:
        async with db.begin():
            result = await sync_chemical_to_inventory(
                db,
                record_id=record_id,
                warehouse_id=body.warehouse_id,
                posted_by_id=current_user.id,
            )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ChemicalSyncResult(
        record_id=result["record_id"],
        movement_id=result["movement_id"],
        movement_reference=result["movement_reference"],
        quantity_issued=result["quantity_issued"],
    )


# ── Maintenance ───────────────────────────────────────────────────────────────

@router.get(
    "/integration/assets/{asset_id}/maintenance-status",
    response_model=MaintenanceStatusResult,
    summary="Get maintenance module status for a utility asset",
)
async def get_maintenance_status_route(
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> MaintenanceStatusResult:
    try:
        result = await get_maintenance_status_for_utility_asset(
            db, utility_asset_id=asset_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return MaintenanceStatusResult(**result)


@router.post(
    "/integration/alarms/{event_id}/maintenance-action",
    response_model=MaintenanceActionResult,
    summary="Create a PM work order or breakdown record from a utility alarm event",
)
async def create_maintenance_action_route(
    event_id: UUID,
    body: MaintenanceActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> MaintenanceActionResult:
    try:
        async with db.begin():
            result = await create_maintenance_action_from_alarm(
                db,
                event_id=event_id,
                action_type=body.action_type,
                description=body.description,
                scheduled_date=body.scheduled_date,
                plan_id=body.plan_id,
                assigned_to_id=body.assigned_to_id,
                posted_by_id=current_user.id,
            )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return MaintenanceActionResult(**result)


# ── Quality ───────────────────────────────────────────────────────────────────

@router.get(
    "/integration/assets/{asset_id}/quality-inspections",
    response_model=List[QualityInspectionSummary],
    summary="List QC inspections linked to utility asset records",
)
async def get_quality_inspections_route(
    asset_id: UUID,
    date_from: Optional[date] = Query(None, description="Filter from this date (inclusive)"),
    date_to: Optional[date] = Query(None, description="Filter to this date (inclusive)"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> List[QualityInspectionSummary]:
    try:
        results = await get_quality_inspections_for_utility(
            db,
            utility_asset_id=asset_id,
            date_from=date_from,
            date_to=date_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return [QualityInspectionSummary(**item) for item in results]
