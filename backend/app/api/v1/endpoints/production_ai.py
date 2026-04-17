"""
Production AI Intelligence — API endpoints
──────────────────────────────────────────
Routes:
  GET  /production-ai/dashboard              – top-level KPIs for AI panel
  POST /production-ai/run-all               – run all 6 agents (optional order_id param)

  Agent-specific:
  POST /production-ai/predict/{order_id}     – Agent 1: predict one order
  POST /production-ai/detect-anomalies       – Agent 2: global anomaly scan
  POST /production-ai/optimize              – Agent 3: optimization suggestions
  POST /production-ai/recipe-insights       – Agent 4: recipe improvement
  POST /production-ai/cost-intelligence     – Agent 5: cost optimization
  POST /production-ai/maintenance-predict   – Agent 6: predictive maintenance

  History:
  GET  /production-ai/predictions           – list predictions
  GET  /production-ai/anomalies             – list anomalies
  GET  /production-ai/suggestions           – list suggestions
  POST /production-ai/suggestions/{id}/action – accept/reject suggestion
  POST /production-ai/anomalies/{id}/resolve  – resolve anomaly
"""
from __future__ import annotations

import uuid
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.production import ProductionOrder
from app.models.production_ai import (
    ProductionPrediction, ProductionAnomaly, ProductionSuggestion,
    SuggestionStatus,
)
from app.schemas.production_ai import (
    PredictionOutput, AnomalyOutput, SuggestionOutput,
    AnomalyRead, SuggestionRead, PredictionRead,
    RunAllOutput, AIDashboard,
    UpdateSuggestionRequest, ResolveAnomalyRequest,
)
from app.services import production_ai_service as svc

router = APIRouter()


# ── Helper ────────────────────────────────────────────────────────────────────

async def _get_order(db, order_id: uuid.UUID) -> ProductionOrder:
    from fastapi import HTTPException
    q = await db.execute(select(ProductionOrder).where(ProductionOrder.id == order_id))
    order = q.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Production order not found")
    return order


def _fmt_pred(p: ProductionPrediction) -> PredictionRead:
    return PredictionRead(
        id                      = str(p.id),
        prediction_no           = p.prediction_no,
        production_order_id     = str(p.production_order_id),
        predicted_completion_at = p.predicted_completion_at.isoformat() if p.predicted_completion_at else None,
        predicted_output_qty    = float(p.predicted_output_qty) if p.predicted_output_qty else None,
        predicted_output_uom    = p.predicted_output_uom,
        delay_risk_pct          = float(p.delay_risk_pct)          if p.delay_risk_pct          else None,
        efficiency_forecast_pct = float(p.efficiency_forecast_pct) if p.efficiency_forecast_pct else None,
        historical_sample_size  = p.historical_sample_size,
        confidence_score        = float(p.confidence_score),
        explanation             = p.explanation,
        risk_level              = p.risk_level,
        actual_completion_at    = p.actual_completion_at.isoformat() if p.actual_completion_at else None,
        actual_output_qty       = float(p.actual_output_qty) if p.actual_output_qty else None,
        was_delayed             = p.was_delayed,
        prediction_error_pct    = float(p.prediction_error_pct) if p.prediction_error_pct else None,
        created_at              = p.created_at.isoformat() if p.created_at else None,
    )


def _fmt_anom(a: ProductionAnomaly) -> AnomalyRead:
    return AnomalyRead(
        id                  = str(a.id),
        anomaly_no          = a.anomaly_no,
        anomaly_type        = a.anomaly_type.value,
        severity            = a.severity.value,
        affected_area       = a.affected_area,
        affected_material   = a.affected_material,
        deviation_pct       = float(a.deviation_pct)  if a.deviation_pct  else None,
        actual_value        = float(a.actual_value)    if a.actual_value   else None,
        expected_value      = float(a.expected_value)  if a.expected_value else None,
        confidence_score    = float(a.confidence_score),
        explanation         = a.explanation,
        is_resolved         = a.is_resolved,
        resolved_at         = a.resolved_at.isoformat() if a.resolved_at else None,
        resolved_by         = a.resolved_by,
        production_order_id = str(a.production_order_id) if a.production_order_id else None,
        work_center_id      = str(a.work_center_id)      if a.work_center_id      else None,
        created_at          = a.created_at.isoformat() if a.created_at else None,
    )


def _fmt_sug(s: ProductionSuggestion) -> SuggestionRead:
    return SuggestionRead(
        id                           = str(s.id),
        suggestion_no                = s.suggestion_no,
        agent_type                   = s.agent_type.value,
        suggestion_type              = s.suggestion_type.value,
        issue_detected               = s.issue_detected,
        suggested_change             = s.suggested_change,
        current_value                = float(s.current_value)            if s.current_value            else None,
        recommended_value            = float(s.recommended_value)        if s.recommended_value        else None,
        value_unit                   = s.value_unit,
        expected_efficiency_gain_pct = float(s.expected_efficiency_gain_pct) if s.expected_efficiency_gain_pct else None,
        expected_cost_reduction_pct  = float(s.expected_cost_reduction_pct)  if s.expected_cost_reduction_pct  else None,
        expected_quality_improvement = s.expected_quality_improvement,
        estimated_kes_saving         = float(s.estimated_kes_saving)     if s.estimated_kes_saving     else None,
        confidence_score             = float(s.confidence_score),
        explanation                  = s.explanation,
        status                       = s.status.value,
        actioned_by                  = s.actioned_by,
        actioned_at                  = s.actioned_at.isoformat() if s.actioned_at else None,
        rejection_reason             = s.rejection_reason,
        product_id                   = str(s.product_id)     if s.product_id     else None,
        recipe_id                    = str(s.recipe_id)      if s.recipe_id      else None,
        work_center_id               = str(s.work_center_id) if s.work_center_id else None,
        created_at                   = s.created_at.isoformat() if s.created_at else None,
    )


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=AIDashboard)
async def ai_dashboard(
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_current_user),
):
    return await svc.get_ai_dashboard(db)


# ── Run all agents ─────────────────────────────────────────────────────────────

@router.post("/run-all")
async def run_all_agents(
    order_id: Optional[uuid.UUID] = Query(None, description="Optional production order to predict for"),
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_current_user),
):
    order = None
    if order_id:
        order = await _get_order(db, order_id)
    return await svc.run_all_agents(db, order=order)


# ── Agent 1: Prediction ────────────────────────────────────────────────────────

@router.post("/predict/{order_id}", response_model=PredictionOutput)
async def predict_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_current_user),
):
    order = await _get_order(db, order_id)
    result = await svc.run_prediction_agent(db, order, persist=True)
    await db.commit()
    return PredictionOutput(**result)


# ── Agent 2: Anomaly Detection ────────────────────────────────────────────────

@router.post("/detect-anomalies", response_model=List[AnomalyOutput])
async def detect_anomalies(
    order_id:        Optional[uuid.UUID] = Query(None),
    look_back_days:  int                 = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_current_user),
):
    order = None
    if order_id:
        order = await _get_order(db, order_id)
    result = await svc.run_anomaly_agent(db, order=order, look_back_days=look_back_days, persist=True)
    await db.commit()
    return [AnomalyOutput(**a) for a in result]


# ── Agent 3: Optimization ─────────────────────────────────────────────────────

@router.post("/optimize", response_model=List[SuggestionOutput])
async def optimize(
    product_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_current_user),
):
    result = await svc.run_optimization_agent(db, product_id=product_id, persist=True)
    await db.commit()
    return [SuggestionOutput(**s) for s in result]


# ── Agent 4: Recipe Insights ──────────────────────────────────────────────────

@router.post("/recipe-insights", response_model=List[SuggestionOutput])
async def recipe_insights(
    recipe_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_current_user),
):
    result = await svc.run_recipe_agent(db, recipe_id=recipe_id, persist=True)
    await db.commit()
    return [SuggestionOutput(**s) for s in result]


# ── Agent 5: Cost Intelligence ────────────────────────────────────────────────

@router.post("/cost-intelligence", response_model=List[SuggestionOutput])
async def cost_intelligence(
    look_back_days: int = Query(60, ge=7, le=180),
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_current_user),
):
    result = await svc.run_cost_agent(db, look_back_days=look_back_days, persist=True)
    await db.commit()
    return [SuggestionOutput(**s) for s in result]


# ── Agent 6: Predictive Maintenance ──────────────────────────────────────────

@router.post("/maintenance-predict", response_model=List[SuggestionOutput])
async def maintenance_predict(
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_current_user),
):
    result = await svc.run_maintenance_agent(db, persist=True)
    await db.commit()
    return [SuggestionOutput(**s) for s in result]


# ── History: Predictions ──────────────────────────────────────────────────────

@router.get("/predictions", response_model=List[PredictionRead])
async def list_predictions(
    order_id:  Optional[uuid.UUID] = Query(None),
    risk_level: Optional[str]      = Query(None),
    limit:     int                 = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_current_user),
):
    filters = []
    if order_id:
        filters.append(ProductionPrediction.production_order_id == order_id)
    if risk_level:
        filters.append(ProductionPrediction.risk_level == risk_level.upper())

    q = await db.execute(
        select(ProductionPrediction)
        .where(and_(*filters))
        .order_by(desc(ProductionPrediction.created_at))
        .limit(limit)
    )
    return [_fmt_pred(p) for p in q.scalars().all()]


# ── History: Anomalies ────────────────────────────────────────────────────────

@router.get("/anomalies", response_model=List[AnomalyRead])
async def list_anomalies(
    is_resolved: Optional[bool] = Query(None),
    severity:    Optional[str]  = Query(None),
    limit:       int            = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_current_user),
):
    filters = []
    if is_resolved is not None:
        filters.append(ProductionAnomaly.is_resolved == is_resolved)
    if severity:
        filters.append(ProductionAnomaly.severity == severity.lower())

    q = await db.execute(
        select(ProductionAnomaly)
        .where(and_(*filters))
        .order_by(desc(ProductionAnomaly.created_at))
        .limit(limit)
    )
    return [_fmt_anom(a) for a in q.scalars().all()]


@router.post("/anomalies/{anomaly_id}/resolve", response_model=AnomalyRead)
async def resolve_anomaly(
    anomaly_id: uuid.UUID,
    body: ResolveAnomalyRequest,
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_current_user),
):
    a = await svc.resolve_anomaly(db, anomaly_id, body.resolved_by, body.notes)
    await db.commit()
    return _fmt_anom(a)


# ── History: Suggestions ──────────────────────────────────────────────────────

@router.get("/suggestions", response_model=List[SuggestionRead])
async def list_suggestions(
    status:      Optional[str]      = Query(None),
    agent_type:  Optional[str]      = Query(None),
    product_id:  Optional[uuid.UUID] = Query(None),
    limit:       int                = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_current_user),
):
    filters = []
    if status:
        filters.append(ProductionSuggestion.status == status.lower())
    if agent_type:
        filters.append(ProductionSuggestion.agent_type == agent_type.upper())
    if product_id:
        filters.append(ProductionSuggestion.product_id == product_id)

    q = await db.execute(
        select(ProductionSuggestion)
        .where(and_(*filters))
        .order_by(desc(ProductionSuggestion.created_at))
        .limit(limit)
    )
    return [_fmt_sug(s) for s in q.scalars().all()]


@router.post("/suggestions/{suggestion_id}/action", response_model=SuggestionRead)
async def action_suggestion(
    suggestion_id: uuid.UUID,
    body: UpdateSuggestionRequest,
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_current_user),
):
    from app.models.production_ai import SuggestionStatus as SS
    status_map = {
        "accepted": SS.ACCEPTED,
        "rejected": SS.REJECTED,
        "applied":  SS.APPLIED,
    }
    new_status = status_map.get(body.status.lower())
    if not new_status:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="status must be accepted, rejected, or applied")

    s = await svc.update_suggestion_status(
        db, suggestion_id, new_status,
        actioned_by=body.actioned_by,
        rejection_reason=body.rejection_reason,
    )
    await db.commit()
    return _fmt_sug(s)
