"""
MRP + Demand Forecasting API
─────────────────────────────
Endpoints for forecast generation, MRP runs, results, and suggestions.
Permission: mrp.view / mrp.manage
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.master import Material, Product
from app.models.mrp import (
    DemandForecast, DemandForecastLine, ForecastStatus,
    MRPResult, MRPRun, MRPRunStatus, MRPSuggestion,
    SuggestionStatus, SuggestionType,
)
from app.models.user import User
from app.schemas.mrp import (
    ForecastAccuracyRow, ForecastGenerateRequest, ForecastLineOut,
    ForecastLineOverride, ForecastOut, ForecastSummary,
    MRPDashboard, MRPResultOut, MRPRunCreate, MRPRunOut,
    ShortageAlert, SuggestionApprove, SuggestionConvertResult,
    SuggestionOut, SuggestionReject,
)
from app.services.forecast_service import backfill_actuals, generate_forecast
from app.services.mrp_service import (
    convert_suggestion_to_pr,
    convert_suggestion_to_production_order,
    create_mrp_run,
    execute_mrp_run,
)

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_product_info(db: AsyncSession, product_id: Optional[UUID]):
    if not product_id:
        return None, None
    p = await db.get(Product, product_id)
    return (p.sku if p else None), (p.name if p else None)


async def _get_material_info(db: AsyncSession, material_id: Optional[UUID]):
    if not material_id:
        return None, None
    m = await db.get(Material, material_id)
    return (m.code if m else None), (m.name if m else None)


def _map_forecast_out(f: DemandForecast, product: Optional[Product]) -> ForecastOut:
    return ForecastOut(
        id=f.id,
        product_id=f.product_id,
        product_sku=product.sku if product else None,
        product_name=product.name if product else None,
        warehouse_id=f.warehouse_id,
        forecast_model=str(f.forecast_model),
        period_type=str(f.period_type),
        start_date=f.start_date,
        end_date=f.end_date,
        status=str(f.status),
        is_approved=f.is_approved,
        mape=f.mape,
        notes=f.notes,
        created_at=f.created_at,
        lines=[
            ForecastLineOut(
                id=ln.id,
                period_date=ln.period_date,
                forecast_qty=ln.forecast_qty,
                adjusted_qty=ln.adjusted_qty,
                actual_qty=ln.actual_qty,
                error_pct=ln.error_pct,
                is_spike=ln.is_spike,
                is_outlier=ln.is_outlier,
                notes=ln.notes,
            )
            for ln in f.lines
        ],
    )


# ══════════════════════════════════════════════════════════════════════════════
# DEMAND FORECASTING
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/forecast/generate", response_model=ForecastOut, status_code=201)
async def generate_demand_forecast(
    body: ForecastGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate statistical demand forecast for a product."""
    product = await db.get(Product, body.product_id)
    if not product:
        raise HTTPException(404, "Product not found")

    forecast = await generate_forecast(
        db,
        product_id=body.product_id,
        warehouse_id=body.warehouse_id,
        forecast_model=body.forecast_model,
        period_type=body.period_type,
        periods_ahead=body.periods_ahead,
        history_periods=body.history_periods,
        model_params=body.model_params,
        created_by=current_user.id,
    )
    await db.commit()
    await db.refresh(forecast)
    return _map_forecast_out(forecast, product)


@router.get("/forecasts", response_model=list[ForecastSummary])
async def list_forecasts(
    product_id: Optional[UUID]  = Query(None),
    status:     Optional[str]   = Query(None),
    skip:       int             = Query(0, ge=0),
    limit:      int             = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(DemandForecast, Product).join(Product, DemandForecast.product_id == Product.id)
    if product_id:
        q = q.where(DemandForecast.product_id == product_id)
    if status:
        q = q.where(DemandForecast.status == status)
    q = q.order_by(DemandForecast.created_at.desc()).offset(skip).limit(limit)
    rows = (await db.execute(q)).all()
    return [
        ForecastSummary(
            id=f.id,
            product_id=f.product_id,
            product_sku=p.sku,
            product_name=p.name,
            forecast_model=str(f.forecast_model),
            period_type=str(f.period_type),
            start_date=f.start_date,
            end_date=f.end_date,
            status=str(f.status),
            mape=f.mape,
            created_at=f.created_at,
        )
        for f, p in rows
    ]


@router.get("/forecasts/accuracy", response_model=list[ForecastAccuracyRow])
async def forecast_accuracy(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """MAPE summary by product across all forecasts."""
    q = (
        select(
            DemandForecast.product_id,
            Product.sku,
            Product.name,
            func.count(DemandForecast.id).label("periods"),
            func.avg(DemandForecast.mape).label("avg_mape"),
            func.min(DemandForecast.mape).label("min_mape"),
            func.max(DemandForecast.mape).label("max_mape"),
        )
        .join(Product, DemandForecast.product_id == Product.id)
        .where(DemandForecast.mape.isnot(None))
        .group_by(DemandForecast.product_id, Product.sku, Product.name)
        .order_by(func.avg(DemandForecast.mape).desc())
    )
    rows = (await db.execute(q)).all()
    return [
        ForecastAccuracyRow(
            product_id=r.product_id,
            product_sku=r.sku,
            product_name=r.name,
            periods=r.periods,
            avg_mape=r.avg_mape,
            min_mape=r.min_mape,
            max_mape=r.max_mape,
        )
        for r in rows
    ]


@router.get("/forecasts/{forecast_id}", response_model=ForecastOut)
async def get_forecast(
    forecast_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    f = await db.get(DemandForecast, forecast_id)
    if not f:
        raise HTTPException(404, "Forecast not found")
    product = await db.get(Product, f.product_id)
    return _map_forecast_out(f, product)


@router.patch("/forecasts/{forecast_id}/approve", response_model=ForecastOut)
async def approve_forecast(
    forecast_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    f = await db.get(DemandForecast, forecast_id)
    if not f:
        raise HTTPException(404, "Forecast not found")
    f.status = ForecastStatus.APPROVED
    f.is_approved = True
    f.approved_by = current_user.id
    f.approved_at = datetime.now(tz=timezone.utc)
    await db.commit()
    await db.refresh(f)
    product = await db.get(Product, f.product_id)
    return _map_forecast_out(f, product)


@router.patch("/forecasts/{forecast_id}/lines/{line_id}", response_model=ForecastLineOut)
async def override_forecast_line(
    forecast_id: UUID,
    line_id:     UUID,
    body:        ForecastLineOverride,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    line = await db.get(DemandForecastLine, line_id)
    if not line or line.forecast_id != forecast_id:
        raise HTTPException(404, "Forecast line not found")
    if body.adjusted_qty is not None:
        line.adjusted_qty = body.adjusted_qty
    if body.notes is not None:
        line.notes = body.notes
    await db.commit()
    await db.refresh(line)
    return ForecastLineOut(
        id=line.id, period_date=line.period_date,
        forecast_qty=line.forecast_qty, adjusted_qty=line.adjusted_qty,
        actual_qty=line.actual_qty, error_pct=line.error_pct,
        is_spike=line.is_spike, is_outlier=line.is_outlier, notes=line.notes,
    )


@router.post("/forecasts/{forecast_id}/backfill", response_model=dict)
async def backfill_forecast_actuals(
    forecast_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    updated = await backfill_actuals(db, forecast_id)
    await db.commit()
    return {"updated_lines": updated}


# ══════════════════════════════════════════════════════════════════════════════
# MRP RUNS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/runs", response_model=MRPRunOut, status_code=201)
async def trigger_mrp_run(
    body: MRPRunCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger a new MRP run and execute synchronously."""
    run = await create_mrp_run(
        db,
        planning_horizon_days=body.planning_horizon_days,
        include_forecast=body.include_forecast,
        include_safety_stock=body.include_safety_stock,
        warehouse_id=body.warehouse_id,
        triggered_by_id=current_user.id,
        notes=body.notes,
    )
    await db.flush()

    try:
        run = await execute_mrp_run(db, run.id)
    except Exception as exc:
        await db.commit()   # commit the FAILED status
        raise HTTPException(500, f"MRP run failed: {exc}") from exc

    await db.commit()
    await db.refresh(run)
    return MRPRunOut(
        id=run.id, run_no=run.run_no, run_date=run.run_date,
        planning_horizon_days=run.planning_horizon_days,
        status=str(run.status), trigger=str(run.trigger),
        include_forecast=run.include_forecast,
        include_safety_stock=run.include_safety_stock,
        warehouse_id=run.warehouse_id,
        error_message=run.error_message,
        product_count=run.product_count,
        shortage_count=run.shortage_count,
        suggestion_count=run.suggestion_count,
        started_at=run.started_at,
        completed_at=run.completed_at,
        notes=run.notes,
        created_at=run.created_at,
    )


@router.get("/runs", response_model=list[MRPRunOut])
async def list_mrp_runs(
    skip:  int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    runs = (await db.execute(
        select(MRPRun).order_by(MRPRun.created_at.desc()).offset(skip).limit(limit)
    )).scalars().all()
    return [
        MRPRunOut(
            id=r.id, run_no=r.run_no, run_date=r.run_date,
            planning_horizon_days=r.planning_horizon_days,
            status=str(r.status), trigger=str(r.trigger),
            include_forecast=r.include_forecast,
            include_safety_stock=r.include_safety_stock,
            warehouse_id=r.warehouse_id,
            error_message=r.error_message,
            product_count=r.product_count,
            shortage_count=r.shortage_count,
            suggestion_count=r.suggestion_count,
            started_at=r.started_at,
            completed_at=r.completed_at,
            notes=r.notes,
            created_at=r.created_at,
        )
        for r in runs
    ]


@router.get("/runs/{run_id}", response_model=MRPRunOut)
async def get_mrp_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    run = await db.get(MRPRun, run_id)
    if not run:
        raise HTTPException(404, "MRP run not found")
    return MRPRunOut(
        id=run.id, run_no=run.run_no, run_date=run.run_date,
        planning_horizon_days=run.planning_horizon_days,
        status=str(run.status), trigger=str(run.trigger),
        include_forecast=run.include_forecast,
        include_safety_stock=run.include_safety_stock,
        warehouse_id=run.warehouse_id,
        error_message=run.error_message,
        product_count=run.product_count,
        shortage_count=run.shortage_count,
        suggestion_count=run.suggestion_count,
        started_at=run.started_at,
        completed_at=run.completed_at,
        notes=run.notes,
        created_at=run.created_at,
    )


@router.get("/runs/{run_id}/results", response_model=list[MRPResultOut])
async def get_run_results(
    run_id: UUID,
    shortage_only: bool = Query(False),
    skip:  int = Query(0, ge=0),
    limit: int = Query(200, le=1000),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = (
        select(MRPResult, Product)
        .join(Product, MRPResult.product_id == Product.id)
        .where(MRPResult.run_id == run_id)
    )
    if shortage_only:
        q = q.where(MRPResult.shortage_flag == True)
    q = q.order_by(MRPResult.net_requirement_qty.desc()).offset(skip).limit(limit)
    rows = (await db.execute(q)).all()
    return [
        MRPResultOut(
            id=r.id, run_id=r.run_id, product_id=r.product_id,
            product_sku=p.sku, product_name=p.name,
            so_demand_qty=r.so_demand_qty,
            forecast_demand_qty=r.forecast_demand_qty,
            safety_stock_qty=r.safety_stock_qty,
            gross_demand_qty=r.gross_demand_qty,
            stock_on_hand_qty=r.stock_on_hand_qty,
            incoming_po_qty=r.incoming_po_qty,
            incoming_prod_qty=r.incoming_prod_qty,
            total_supply_qty=r.total_supply_qty,
            net_requirement_qty=r.net_requirement_qty,
            shortage_flag=r.shortage_flag,
            suggested_production_qty=r.suggested_production_qty,
            suggested_procurement_qty=r.suggested_procurement_qty,
        )
        for r, p in rows
    ]


# ══════════════════════════════════════════════════════════════════════════════
# SUGGESTIONS
# ══════════════════════════════════════════════════════════════════════════════

async def _sug_out(db: AsyncSession, s: MRPSuggestion) -> SuggestionOut:
    prod_sku, prod_name = await _get_product_info(db, s.product_id)
    mat_code, mat_name  = await _get_material_info(db, s.material_id)
    sup_name = None
    if s.preferred_supplier_id:
        from app.models.master import Supplier
        sup = await db.get(Supplier, s.preferred_supplier_id)
        sup_name = sup.name if sup else None
    return SuggestionOut(
        id=s.id, run_id=s.run_id,
        suggestion_type=str(s.suggestion_type),
        status=str(s.status),
        product_id=s.product_id, product_sku=prod_sku, product_name=prod_name,
        material_id=s.material_id, material_code=mat_code, material_name=mat_name,
        suggested_qty=s.suggested_qty, uom=s.uom,
        required_date=s.required_date,
        planned_start_date=s.planned_start_date,
        driver_product_id=s.driver_product_id,
        net_requirement_qty=s.net_requirement_qty,
        moq=s.moq,
        preferred_supplier_id=s.preferred_supplier_id,
        preferred_supplier_name=sup_name,
        estimated_cost=s.estimated_cost,
        rejection_reason=s.rejection_reason,
        notes=s.notes,
        created_at=s.created_at,
    )


@router.get("/suggestions", response_model=list[SuggestionOut])
async def list_suggestions(
    run_id:          Optional[UUID] = Query(None),
    suggestion_type: Optional[str]  = Query(None),
    status:          Optional[str]  = Query(None),
    skip:  int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(MRPSuggestion).order_by(MRPSuggestion.required_date, MRPSuggestion.created_at.desc())
    if run_id:
        q = q.where(MRPSuggestion.run_id == run_id)
    if suggestion_type:
        q = q.where(MRPSuggestion.suggestion_type == suggestion_type)
    if status:
        q = q.where(MRPSuggestion.status == status)
    sugs = (await db.execute(q.offset(skip).limit(limit))).scalars().all()
    return [await _sug_out(db, s) for s in sugs]


@router.patch("/suggestions/{sug_id}/approve", response_model=SuggestionOut)
async def approve_suggestion(
    sug_id: UUID,
    body: SuggestionApprove,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = await db.get(MRPSuggestion, sug_id)
    if not s:
        raise HTTPException(404, "Suggestion not found")
    if s.status != SuggestionStatus.DRAFT:
        raise HTTPException(409, f"Cannot approve: status is {s.status}")
    s.status = SuggestionStatus.APPROVED
    s.approved_by_id = current_user.id
    s.approved_at = datetime.now(tz=timezone.utc)
    if body.notes:
        s.notes = body.notes
    await db.commit()
    await db.refresh(s)
    return await _sug_out(db, s)


@router.patch("/suggestions/{sug_id}/reject", response_model=SuggestionOut)
async def reject_suggestion(
    sug_id: UUID,
    body: SuggestionReject,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = await db.get(MRPSuggestion, sug_id)
    if not s:
        raise HTTPException(404, "Suggestion not found")
    if s.status not in (SuggestionStatus.DRAFT, SuggestionStatus.APPROVED):
        raise HTTPException(409, f"Cannot reject: status is {s.status}")
    s.status = SuggestionStatus.REJECTED
    s.rejection_reason = body.rejection_reason
    await db.commit()
    await db.refresh(s)
    return await _sug_out(db, s)


@router.post("/suggestions/{sug_id}/convert", response_model=SuggestionConvertResult)
async def convert_suggestion(
    sug_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Convert an approved suggestion into a Purchase Requisition or Production Order."""
    s = await db.get(MRPSuggestion, sug_id)
    if not s:
        raise HTTPException(404, "Suggestion not found")
    if s.status == SuggestionStatus.CONVERTED:
        raise HTTPException(409, "Already converted")
    if s.status != SuggestionStatus.APPROVED:
        raise HTTPException(409, f"Suggestion must be APPROVED before converting (status: {s.status})")

    if s.suggestion_type == SuggestionType.PROCUREMENT:
        pr = await convert_suggestion_to_pr(db, s, current_user.id)
        await db.commit()
        return SuggestionConvertResult(
            suggestion_id=sug_id,
            converted_to="purchase_requisition",
            reference_no=pr.pr_no,
            reference_id=pr.id,
        )
    else:
        order = await convert_suggestion_to_production_order(db, s, current_user.id)
        await db.commit()
        return SuggestionConvertResult(
            suggestion_id=sug_id,
            converted_to="production_order",
            reference_no=order.order_no,
            reference_id=order.id,
        )


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/dashboard", response_model=MRPDashboard)
async def mrp_dashboard(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    # Last run
    last_run_row = (await db.execute(
        select(MRPRun).order_by(MRPRun.created_at.desc()).limit(1)
    )).scalar_one_or_none()

    recent_runs = (await db.execute(
        select(MRPRun).order_by(MRPRun.created_at.desc()).limit(5)
    )).scalars().all()

    total_runs = (await db.execute(select(func.count()).select_from(MRPRun))).scalar() or 0

    open_sug = (await db.execute(
        select(func.count()).select_from(MRPSuggestion)
        .where(MRPSuggestion.status == SuggestionStatus.DRAFT)
    )).scalar() or 0

    pending_approval = (await db.execute(
        select(func.count()).select_from(MRPSuggestion)
        .where(MRPSuggestion.status == SuggestionStatus.DRAFT)
    )).scalar() or 0

    shortage_prods = 0
    if last_run_row:
        shortage_prods = (await db.execute(
            select(func.count()).select_from(MRPResult)
            .where(MRPResult.run_id == last_run_row.id, MRPResult.shortage_flag == True)
        )).scalar() or 0

    active_forecasts = (await db.execute(
        select(func.count()).select_from(DemandForecast)
        .where(DemandForecast.status.in_(["DRAFT", "APPROVED"]))
    )).scalar() or 0

    def _run_out(r: MRPRun) -> MRPRunOut:
        return MRPRunOut(
            id=r.id, run_no=r.run_no, run_date=r.run_date,
            planning_horizon_days=r.planning_horizon_days,
            status=str(r.status), trigger=str(r.trigger),
            include_forecast=r.include_forecast,
            include_safety_stock=r.include_safety_stock,
            warehouse_id=r.warehouse_id,
            error_message=r.error_message,
            product_count=r.product_count,
            shortage_count=r.shortage_count,
            suggestion_count=r.suggestion_count,
            started_at=r.started_at,
            completed_at=r.completed_at,
            notes=r.notes,
            created_at=r.created_at,
        )

    return MRPDashboard(
        last_run=_run_out(last_run_row) if last_run_row else None,
        total_runs=total_runs,
        open_suggestions=open_sug,
        shortage_products=shortage_prods,
        pending_approval=pending_approval,
        active_forecasts=active_forecasts,
        recent_runs=[_run_out(r) for r in recent_runs],
    )


@router.get("/shortage-alerts", response_model=list[ShortageAlert])
async def shortage_alerts(
    run_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Return shortage alerts from the latest run (or a specific run)."""
    if not run_id:
        latest = (await db.execute(
            select(MRPRun).where(MRPRun.status == MRPRunStatus.COMPLETED)
            .order_by(MRPRun.created_at.desc()).limit(1)
        )).scalar_one_or_none()
        if not latest:
            return []
        run_id = latest.id

    run = await db.get(MRPRun, run_id)
    q = (
        select(MRPResult, Product, MRPSuggestion)
        .join(Product, MRPResult.product_id == Product.id)
        .outerjoin(
            MRPSuggestion,
            (MRPSuggestion.run_id == MRPResult.run_id) &
            (MRPSuggestion.product_id == MRPResult.product_id) &
            (MRPSuggestion.suggestion_type == SuggestionType.PRODUCTION),
        )
        .where(MRPResult.run_id == run_id, MRPResult.shortage_flag == True)
        .order_by(MRPResult.net_requirement_qty.desc())
    )
    rows = (await db.execute(q)).all()
    return [
        ShortageAlert(
            product_id=r.product_id,
            product_sku=p.sku,
            product_name=p.name,
            net_requirement=r.net_requirement_qty,
            suggested_qty=r.suggested_production_qty,
            required_date=s.required_date if s else None,
            run_no=run.run_no if run else "",
        )
        for r, p, s in rows
    ]
