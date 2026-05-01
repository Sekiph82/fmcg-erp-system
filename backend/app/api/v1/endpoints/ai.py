from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_permission
from app.core.config import settings
from app.core.ai_modes import MODULE_AI_MODES, MODE_LABELS, MODE_DESCRIPTIONS
from app.core.ai_rate_limiter import check_rate_limit
from app.core.ai_safety import detect_prompt_injection, sanitize_user_prompt, is_clearly_malicious
from app.models.ai import (
    AIRequest, AIPrediction, AIRecommendation, AIFormulation, AIScenario,
    AIRequestStatus,
)
from app.services import ai_service as svc

router = APIRouter()


# ── Request / Response schemas ────────────────────────────────────────────────

class PredictionRequest(BaseModel):
    prediction_types: Optional[List[str]] = None


class RecommendationRequest(BaseModel):
    focus_area: Optional[str] = None


class ScenarioRequest(BaseModel):
    scenario_type: str
    parameters: dict
    title: Optional[str] = None


class FormulationRequest(BaseModel):
    product_category: str
    target_properties: dict
    cost_target: Optional[float] = None
    performance_priority: str = "balanced"


class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[dict]] = None


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard/",
            dependencies=[Depends(require_permission("ai", "view"))])
async def ai_dashboard(db: AsyncSession = Depends(get_db)):
    return await svc.get_ai_dashboard(db)


@router.get("/status/",
            dependencies=[Depends(require_permission("ai", "view"))])
async def ai_status():
    """
    Return safe AI configuration status.
    Requires ai:view permission — never exposes API keys or raw env values.
    """
    from app.services.ai_provider import get_ai_provider
    active = get_ai_provider()
    provider_name = active.__class__.__name__.replace("Provider", "").lower()
    is_mock = provider_name == "mock"

    return {
        "provider": provider_name,
        "configured": settings.AI_CONFIGURED,
        "model": getattr(active, "_model", getattr(active, "_model_name", "mock-v1")),
        "mode": "llm" if not is_mock else "mock",
        "fallback_active": is_mock and settings.AI_CONFIGURED is False,
        "ai_mode_label": "Mock / Dev Mode" if is_mock else "LLM-Powered",
    }


@router.get("/modes/",
            dependencies=[Depends(require_permission("ai", "view"))])
async def ai_modes():
    """Return AI mode classification for all modules."""
    return {
        "modes": {
            module: {
                "mode": mode,
                "label": MODE_LABELS.get(mode, mode),
                "description": MODE_DESCRIPTIONS.get(mode, ""),
            }
            for module, mode in MODULE_AI_MODES.items()
        },
        "legend": {k: {"label": v, "description": MODE_DESCRIPTIONS[k]} for k, v in MODE_LABELS.items()},
    }


# ── Predictions ───────────────────────────────────────────────────────────────

@router.post("/predictions/generate/")
async def generate_predictions(
    body: PredictionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("ai", "create")),
):
    await check_rate_limit(str(current_user.id), "predictions", settings.AI_RATE_LIMIT_GENERATE)
    try:
        predictions = await svc.generate_predictions(
            db,
            prediction_types=body.prediction_types,
            user_id=current_user.id,
        )
        await db.commit()
        return {
            "count": len(predictions),
            "predictions": [_pred_to_dict(p) for p in predictions],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"AI prediction failed: {str(e)}")


@router.get("/predictions/")
async def list_predictions(
    prediction_type: Optional[str] = None,
    risk_level: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("ai", "view")),
):
    q = select(AIPrediction).where(AIPrediction.is_archived == False).order_by(  # noqa: E712
        desc(AIPrediction.created_at)
    ).limit(limit)
    if prediction_type:
        q = q.where(AIPrediction.prediction_type == prediction_type)
    if risk_level:
        q = q.where(AIPrediction.risk_level == risk_level)
    rows = (await db.execute(q)).scalars().all()
    return [_pred_to_dict(p) for p in rows]


@router.delete("/predictions/{pred_id}/archive/")
async def archive_prediction(
    pred_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("ai", "edit")),
):
    p = (await db.execute(
        select(AIPrediction).where(AIPrediction.id == pred_id)
    )).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Prediction not found")
    p.is_archived = True
    await db.commit()
    return {"status": "archived"}


# ── Recommendations ───────────────────────────────────────────────────────────

@router.post("/recommendations/generate/")
async def generate_recommendations(
    body: RecommendationRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("ai", "create")),
):
    await check_rate_limit(str(current_user.id), "recommendations", settings.AI_RATE_LIMIT_GENERATE)
    try:
        recs = await svc.generate_recommendations(
            db,
            focus_area=body.focus_area,
            user_id=current_user.id,
        )
        await db.commit()
        return {
            "count": len(recs),
            "recommendations": [_rec_to_dict(r) for r in recs],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"AI recommendation failed: {str(e)}")


@router.get("/recommendations/")
async def list_recommendations(
    category: Optional[str] = None,
    priority: Optional[str] = None,
    include_actioned: bool = False,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("ai", "view")),
):
    q = (
        select(AIRecommendation)
        .where(AIRecommendation.is_dismissed == False)  # noqa: E712
        .order_by(desc(AIRecommendation.created_at))
        .limit(limit)
    )
    if not include_actioned:
        q = q.where(AIRecommendation.is_actioned == False)  # noqa: E712
    if category:
        q = q.where(AIRecommendation.category == category)
    if priority:
        q = q.where(AIRecommendation.priority == priority)
    rows = (await db.execute(q)).scalars().all()
    return [_rec_to_dict(r) for r in rows]


@router.post("/recommendations/{rec_id}/action/")
async def action_recommendation(
    rec_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("ai", "edit")),
):
    r = (await db.execute(
        select(AIRecommendation).where(AIRecommendation.id == rec_id)
    )).scalar_one_or_none()
    if not r:
        raise HTTPException(404, "Recommendation not found")
    r.is_actioned = True
    await db.commit()
    return {"status": "actioned"}


@router.post("/recommendations/{rec_id}/dismiss/")
async def dismiss_recommendation(
    rec_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("ai", "edit")),
):
    r = (await db.execute(
        select(AIRecommendation).where(AIRecommendation.id == rec_id)
    )).scalar_one_or_none()
    if not r:
        raise HTTPException(404, "Recommendation not found")
    r.is_dismissed = True
    await db.commit()
    return {"status": "dismissed"}


# ── Scenario Simulator ────────────────────────────────────────────────────────

@router.post("/scenarios/simulate/")
async def simulate_scenario(
    body: ScenarioRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("ai", "create")),
):
    await check_rate_limit(str(current_user.id), "scenarios", settings.AI_RATE_LIMIT_GENERATE)
    try:
        scenario = await svc.simulate_scenario(
            db,
            scenario_type=body.scenario_type,
            parameters=body.parameters,
            user_id=current_user.id,
        )
        await db.commit()
        return _scenario_to_dict(scenario)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"AI scenario simulation failed: {str(e)}")


@router.get("/scenarios/")
async def list_scenarios(
    scenario_type: Optional[str] = None,
    limit: int = Query(30, le=100),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("ai", "view")),
):
    q = select(AIScenario).order_by(desc(AIScenario.created_at)).limit(limit)
    if scenario_type:
        q = q.where(AIScenario.scenario_type == scenario_type)
    rows = (await db.execute(q)).scalars().all()
    return [_scenario_to_dict(s) for s in rows]


@router.get("/scenarios/{scenario_id}/")
async def get_scenario(
    scenario_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("ai", "view")),
):
    s = (await db.execute(
        select(AIScenario).where(AIScenario.id == scenario_id)
    )).scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Scenario not found")
    return _scenario_to_dict(s)


# ── Formulation Engine ────────────────────────────────────────────────────────

@router.post("/formulations/generate/")
async def generate_formulation(
    body: FormulationRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("ai", "create")),
):
    await check_rate_limit(str(current_user.id), "formulations", settings.AI_RATE_LIMIT_GENERATE)
    try:
        formulation = await svc.generate_formulation(
            db,
            product_category=body.product_category,
            target_properties=body.target_properties,
            cost_target=body.cost_target,
            performance_priority=body.performance_priority,
            user_id=current_user.id,
        )
        await db.commit()
        await db.refresh(formulation)
        return _form_to_dict(formulation)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"AI formulation generation failed: {str(e)}")


@router.get("/formulations/")
async def list_formulations(
    product_category: Optional[str] = None,
    is_approved: Optional[bool] = None,
    limit: int = Query(30, le=100),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("ai", "view")),
):
    q = select(AIFormulation).order_by(desc(AIFormulation.created_at)).limit(limit)
    if product_category:
        q = q.where(AIFormulation.product_category == product_category)
    if is_approved is not None:
        q = q.where(AIFormulation.is_approved == is_approved)
    rows = (await db.execute(q)).scalars().all()
    return [_form_to_dict(f) for f in rows]


@router.get("/formulations/{form_id}/")
async def get_formulation(
    form_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("ai", "view")),
):
    f = (await db.execute(
        select(AIFormulation).where(AIFormulation.id == form_id)
    )).scalar_one_or_none()
    if not f:
        raise HTTPException(404, "Formulation not found")
    return _form_to_dict(f)


@router.post("/formulations/{form_id}/approve/")
async def approve_formulation(
    form_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("ai", "approve")),
):
    f = (await db.execute(
        select(AIFormulation).where(AIFormulation.id == form_id)
    )).scalar_one_or_none()
    if not f:
        raise HTTPException(404, "Formulation not found")
    f.is_approved = True
    await db.commit()
    return {"status": "approved"}


@router.post("/formulations/{form_id}/favorite/")
async def toggle_favorite(
    form_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("ai", "edit")),
):
    f = (await db.execute(
        select(AIFormulation).where(AIFormulation.id == form_id)
    )).scalar_one_or_none()
    if not f:
        raise HTTPException(404, "Formulation not found")
    f.is_favorite = not f.is_favorite
    await db.commit()
    return {"is_favorite": f.is_favorite}


# ── AI Request Log ────────────────────────────────────────────────────────────

@router.get("/logs/")
async def list_ai_logs(
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("ai", "view")),
):
    rows = (await db.execute(
        select(AIRequest).order_by(desc(AIRequest.created_at)).limit(limit)
    )).scalars().all()
    return [
        {
            "id": str(r.id),
            "request_type": r.request_type.value,
            "provider": r.provider.value,
            "model": r.model,
            "status": r.status.value,
            "prompt_tokens": r.prompt_tokens,
            "completion_tokens": r.completion_tokens,
            "latency_ms": r.latency_ms,
            "error_message": r.error_message,
            "created_at": str(r.created_at),
        }
        for r in rows
    ]


# ── Serializers ───────────────────────────────────────────────────────────────

def _pred_to_dict(p: AIPrediction) -> dict:
    return {
        "id": str(p.id),
        "prediction_type": p.prediction_type,
        "subject_name": p.subject_name,
        "period": p.period,
        "forecast_value": float(p.forecast_value) if p.forecast_value else None,
        "confidence_score": float(p.confidence_score) if p.confidence_score else None,
        "risk_level": p.risk_level,
        "trend": p.trend,
        "summary": p.summary,
        "details": p.details,
        "is_archived": p.is_archived,
        "created_at": str(p.created_at),
    }


def _rec_to_dict(r: AIRecommendation) -> dict:
    return {
        "id": str(r.id),
        "category": r.category,
        "title": r.title,
        "reason": r.reason,
        "expected_impact": r.expected_impact,
        "confidence_level": r.confidence_level,
        "priority": r.priority,
        "action_data": r.action_data,
        "is_actioned": r.is_actioned,
        "is_dismissed": r.is_dismissed,
        "created_at": str(r.created_at),
    }


def _safe_json_parse(v: Any) -> Any:
    """Parse a value that may be a JSON-encoded string stored in a Text column."""
    if isinstance(v, str):
        try:
            return json.loads(v)
        except (json.JSONDecodeError, ValueError):
            return v
    return v


def _scenario_to_dict(s: AIScenario) -> dict:
    return {
        "id": str(s.id),
        "title": s.title,
        "scenario_type": s.scenario_type,
        "input_parameters": s.input_parameters,
        "expected_impact": _safe_json_parse(s.expected_impact),
        "risks": s.risks,
        "opportunities": s.opportunities,
        "simulation_data": s.simulation_data,
        "created_at": str(s.created_at),
    }


def _form_to_dict(f: AIFormulation) -> dict:
    return {
        "id": str(f.id),
        "name": f.name,
        "product_category": f.product_category,
        "version": f.version,
        "target_properties": f.target_properties,
        "cost_target": float(f.cost_target) if f.cost_target else None,
        "performance_priority": f.performance_priority,
        "formulation_data": f.formulation_data,
        "estimated_cost_per_kg": float(f.estimated_cost_per_kg) if f.estimated_cost_per_kg else None,
        "is_approved": f.is_approved,
        "is_favorite": f.is_favorite,
        "notes": f.notes,
        "created_at": str(f.created_at),
    }


# ── ERP Copilot Chat ──────────────────────────────────────────────────────────

@router.post("/chat/")
async def chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("ai", "create")),
):
    """
    Free-form ERP copilot. Includes prompt injection guard and rate limiting.
    Returns structured response with answer, provider info, and context used.
    """
    if not body.message or not body.message.strip():
        raise HTTPException(400, "Message cannot be empty")
    if len(body.message) > 2000:
        raise HTTPException(400, "Message too long (max 2000 characters)")

    # Rate limit
    await check_rate_limit(str(current_user.id), "chat", settings.AI_RATE_LIMIT_CHAT)

    # Injection guard
    raw_message = body.message.strip()
    if is_clearly_malicious(raw_message):
        return {
            "answer": "I'm sorry, I can't process that request. Please ask an ERP-related question.",
            "provider": "safety_filter",
            "model": "none",
            "mode": "blocked",
            "erp_context_used": [],
            "tokens": {"prompt": 0, "completion": 0},
            "latency_ms": 0,
            "safety": {"injection_detected": True, "action": "blocked"},
        }

    detection = detect_prompt_injection(raw_message)
    sanitized_message = sanitize_user_prompt(raw_message)

    try:
        result = await svc.generate_chat_response(
            db,
            message=sanitized_message,
            conversation_history=body.conversation_history,
            user_id=current_user.id,
        )
        # Attach safety metadata (no secrets in response)
        result["safety"] = {
            "injection_detected": detection["detected"],
            "sanitized": sanitized_message != raw_message,
        }
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Chat failed: {str(e)}")


# ── Deterministic Forecast Baseline ──────────────────────────────────────────

@router.get("/forecast-baseline/")
async def get_forecast_baseline(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Deterministic moving-average sales baseline — no LLM required."""
    return await svc.compute_sales_baseline(db)


# ── AI Health ─────────────────────────────────────────────────────────────────

@router.get("/health/",
            dependencies=[Depends(get_current_user)])
async def ai_health():
    """Lightweight health check — tests provider instantiation. Requires auth."""
    from app.services.ai_provider import get_ai_provider
    try:
        provider = get_ai_provider()
        provider_name = provider.__class__.__name__.replace("Provider", "").lower()
        return {
            "status": "ok",
            "provider": provider_name,
            "mode": "mock" if provider_name == "mock" else "live",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
