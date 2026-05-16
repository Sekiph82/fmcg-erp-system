from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, BackgroundTasks, Request
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
    AIRequestStatus, AIPrompt,
)
from app.schemas.ai import AIPromptCreate, AIPromptUpdate, AIPromptRead
from app.services import ai_service as svc

router = APIRouter()


def _ai_provider_name() -> str:
    from app.services.ai_provider import get_ai_provider

    provider = get_ai_provider()
    return provider.__class__.__name__.replace("Provider", "").lower()


def _ai_is_mock_mode() -> bool:
    return _ai_provider_name() == "mock"


def _require_live_ai_for_high_risk(action: str) -> None:
    if _ai_is_mock_mode():
        raise HTTPException(
            status_code=409,
            detail=(
                f"{action} is disabled in AI mock mode. Configure a live AI "
                "provider before approving or executing high-risk AI actions."
            ),
        )


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
        "nl_command_execution_enabled": settings.AI_NL_COMMAND_EXECUTION_ENABLED,
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
    _require_live_ai_for_high_risk("Formulation approval")
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
    _=Depends(require_permission("ai", "view")),
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


# ── Gap 66: Natural Language ERP Control ─────────────────────────────────────

from app.models.ai import NLCommandLog, NLCommandStatus


class NLCommandIn(BaseModel):
    command: str
    user_name: Optional[str] = None


class NLCommandExecuteBody(BaseModel):
    params: Optional[dict] = None
    idempotency_key: Optional[str] = None


# Intent parser — maps NL patterns to structured actions
_INTENT_PATTERNS = [
    {
        "keywords": ["approve", "po", "purchase"],
        "intent": "APPROVE_PO",
        "action": "Approve pending purchase orders under the specified amount threshold.",
        "endpoint": "POST /api/v1/approvals/{id}/approve",
        "risk": "MEDIUM",
        "params_hint": "threshold_amount, approver_name",
    },
    {
        "keywords": ["run", "mrp"],
        "intent": "RUN_MRP",
        "action": "Trigger an MRP run for demand planning.",
        "endpoint": "POST /api/v1/mrp/runs",
        "risk": "LOW",
        "params_hint": "planning_horizon_days",
    },
    {
        "keywords": ["dunning", "overdue", "reminder"],
        "intent": "SEND_DUNNING",
        "action": "Send payment reminder emails to overdue customers.",
        "endpoint": "POST /api/v1/dunning/send-batch",
        "risk": "MEDIUM",
        "params_hint": "days_overdue_threshold",
    },
    {
        "keywords": ["reorder", "low stock", "replenish"],
        "intent": "TRIGGER_REORDER",
        "action": "Create purchase requisitions for all below-reorder-point items.",
        "endpoint": "POST /api/v1/procurement/suggestions",
        "risk": "HIGH",
        "params_hint": "warehouse_id",
    },
    {
        "keywords": ["recall", "batch", "lot"],
        "intent": "INITIATE_RECALL",
        "action": "Initiate a product recall for a specific batch/lot.",
        "endpoint": "POST /api/v1/traceability/recalls",
        "risk": "HIGH",
        "params_hint": "lot_number, recall_reason",
    },
    {
        "keywords": ["payroll", "run payroll"],
        "intent": "RUN_PAYROLL",
        "action": "Trigger payroll calculation for a specified period.",
        "endpoint": "POST /api/v1/payroll-ke/runs",
        "risk": "HIGH",
        "params_hint": "period_month",
    },
    {
        "keywords": ["report", "generate", "export"],
        "intent": "GENERATE_REPORT",
        "action": "Generate and export a specified report.",
        "endpoint": "GET /api/v1/reports-builder/reports/{id}/export",
        "risk": "LOW",
        "params_hint": "report_name_or_id",
    },
]


def _parse_intent(command: str) -> dict:
    """Rule-based intent extraction. Production: use LLM function calling."""
    lower = command.lower()
    for pattern in _INTENT_PATTERNS:
        if any(kw in lower for kw in pattern["keywords"]):
            return pattern
    return {
        "intent": "UNKNOWN",
        "action": "Could not parse command into a known ERP action.",
        "endpoint": None,
        "risk": "LOW",
        "params_hint": None,
    }


@router.post("/nl-command", status_code=201)
async def submit_nl_command(
    payload: NLCommandIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("ai", "create")),
):
    """
    Parse a natural language command into an ERP action plan.
    Returns parsed intent + required confirmation before execution.
    Production: replace _parse_intent() with LLM function-calling (GPT-4 / Claude).
    """
    parsed = _parse_intent(payload.command)

    cmd = NLCommandLog(
        user_id=str(current_user.id),
        user_name=payload.user_name or getattr(current_user, "full_name", None) or getattr(current_user, "username", None),
        command_text=payload.command,
        parsed_intent=parsed["intent"],
        parsed_action=parsed["action"],
        target_endpoint=parsed.get("endpoint"),
        params_json={"params_needed": parsed.get("params_hint")},
        requires_confirmation=parsed["risk"] in ("MEDIUM", "HIGH"),
        risk_level=parsed["risk"],
    )
    db.add(cmd)
    await db.commit()
    await db.refresh(cmd)

    return {
        "id": str(cmd.id),
        "command": payload.command,
        "parsed_intent": cmd.parsed_intent,
        "parsed_action": cmd.parsed_action,
        "target_endpoint": cmd.target_endpoint,
        "risk_level": cmd.risk_level,
        "requires_confirmation": cmd.requires_confirmation,
        "status": cmd.status,
        "params_needed": parsed.get("params_hint"),
        "execution_enabled": settings.AI_NL_COMMAND_EXECUTION_ENABLED,
        "note": (
            "Confirm execution via POST /ai/nl-command/{id}/execute. "
            "HIGH risk commands require explicit confirmation."
            if cmd.requires_confirmation else
            "Low-risk command — auto-executable. Use POST /ai/nl-command/{id}/execute."
        ),
    }


@router.get("/nl-command/{cmd_id}/preview")
async def preview_nl_command(
    cmd_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("ai", "view")),
):
    """
    Return a dry-run execution preview for an NL command.
    This endpoint never mutates ERP state and is safe to use while execution is disabled.
    """
    r = await db.execute(select(NLCommandLog).where(NLCommandLog.id == uuid.UUID(cmd_id)))
    cmd = r.scalar_one_or_none()
    if not cmd:
        raise HTTPException(404, "Command not found")

    return {
        "id": cmd_id,
        "parsed_intent": cmd.parsed_intent,
        "parsed_action": cmd.parsed_action,
        "target_endpoint": cmd.target_endpoint,
        "risk_level": cmd.risk_level,
        "requires_confirmation": cmd.requires_confirmation,
        "params_needed": cmd.params_json,
        "execution_enabled": settings.AI_NL_COMMAND_EXECUTION_ENABLED,
        "approval_required": cmd.risk_level in ("MEDIUM", "HIGH"),
        "dry_run": True,
        "state_change": "none",
        "note": "Preview only. No ERP action has been executed.",
    }


@router.post("/nl-command/{cmd_id}/execute")
async def execute_nl_command(
    cmd_id: str,
    request: Request,
    confirmed_by: str = Query(...),
    body: Optional[NLCommandExecuteBody] = Body(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("ai", "approve")),
):
    """
    Confirm and execute a parsed NL command.
    Calls the target ERP endpoint when one is defined.
    Supply params in the request body to satisfy any path or body parameters.
    """
    import re
    import os
    import httpx
    from datetime import datetime

    _require_live_ai_for_high_risk("Natural-language command execution")

    r = await db.execute(select(NLCommandLog).where(NLCommandLog.id == uuid.UUID(cmd_id)))
    cmd = r.scalar_one_or_none()
    if not cmd:
        raise HTTPException(404, "Command not found")
    if cmd.status == NLCommandStatus.EXECUTED:
        raise HTTPException(400, "Already executed")
    if not settings.AI_NL_COMMAND_EXECUTION_ENABLED:
        cmd.status = NLCommandStatus.FAILED
        cmd.error_message = "NL command execution is disabled by AI_NL_COMMAND_EXECUTION_ENABLED=false."
        await db.commit()
        raise HTTPException(
            status_code=403,
            detail="NL command execution is disabled. Use the preview endpoint for dry-run review.",
        )
    if not body or not body.idempotency_key:
        raise HTTPException(
            status_code=422,
            detail="idempotency_key is required for NL command execution.",
        )

    params = dict(body.params) if body and body.params else {}
    result_summary = None
    call_error = None

    if cmd.target_endpoint:
        parts = cmd.target_endpoint.split(" ", 1)
        if len(parts) == 2:
            method, path = parts[0].upper(), parts[1]
            path_params_needed = re.findall(r'\{(\w+)\}', path)
            missing = [p for p in path_params_needed if p not in params]
            if missing:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "detail": f"Missing required path parameters: {missing}",
                        "params_hint": cmd.params_json,
                    },
                )
            for k in path_params_needed:
                path = path.replace(f"{{{k}}}", str(params.pop(k)))

            base_url = os.environ.get("INTERNAL_API_BASE_URL", "http://localhost:8000")
            url = base_url.rstrip("/") + path
            auth_header = request.headers.get("Authorization", "")
            headers = {"Authorization": auth_header} if auth_header else {}
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    if method == "GET":
                        resp = await client.get(url, params=params or None, headers=headers)
                    else:
                        resp = await client.request(method, url, json=params or None, headers=headers)
                result_summary = f"HTTP {resp.status_code}: {resp.text[:500]}"
                if resp.is_error:
                    call_error = result_summary
            except Exception as exc:
                call_error = f"Failed to reach {url}: {exc}"
                result_summary = call_error

    cmd.status = NLCommandStatus.EXECUTED
    cmd.confirmed_by = confirmed_by
    cmd.confirmed_at = datetime.utcnow()
    cmd.executed_at = datetime.utcnow()
    cmd.result_summary = result_summary or f"Command '{cmd.parsed_intent}' executed."
    await db.commit()

    response: dict = {
        "id": cmd_id,
        "status": "EXECUTED",
        "parsed_intent": cmd.parsed_intent,
        "parsed_action": cmd.parsed_action,
        "result_summary": cmd.result_summary,
        "confirmed_by": confirmed_by,
    }
    if call_error:
        response["call_error"] = call_error
    return response


@router.post("/nl-command/{cmd_id}/reject")
async def reject_nl_command(
    cmd_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("ai", "edit")),
):
    r = await db.execute(select(NLCommandLog).where(NLCommandLog.id == uuid.UUID(cmd_id)))
    cmd = r.scalar_one_or_none()
    if not cmd:
        raise HTTPException(404, "Command not found")
    cmd.status = NLCommandStatus.REJECTED
    await db.commit()
    return {"id": cmd_id, "status": "REJECTED"}


@router.get("/nl-command/history")
async def nl_command_history(
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("ai", "view")),
):
    q = select(NLCommandLog).order_by(desc(NLCommandLog.created_at)).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": str(r.id), "command_text": r.command_text,
            "parsed_intent": r.parsed_intent, "risk_level": r.risk_level,
            "status": r.status, "confirmed_by": r.confirmed_by,
            "result_summary": r.result_summary,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in rows
    ]


# ── Gap 67: AI Agent Governance ───────────────────────────────────────────────

from app.models.ai import AIAgentPolicy, AIAgentRun, AIAgentRunStatus
from datetime import datetime as _dt


class PolicyIn(BaseModel):
    agent_name: str
    description: Optional[str] = None
    allowed_actions: Optional[list] = None
    forbidden_actions: Optional[list] = None
    max_cost_per_run_tokens: Optional[int] = None
    requires_human_approval: bool = True
    max_runs_per_hour: Optional[int] = None
    allowed_modules: Optional[list] = None
    hallucination_guardrail: bool = True
    rag_enabled: bool = False
    notes: Optional[str] = None


class RunLogIn(BaseModel):
    agent_name: str
    trigger: Optional[str] = None
    triggered_by: Optional[str] = None
    actions_taken: Optional[list] = None
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
    status: str = "COMPLETED"
    result_summary: Optional[str] = None
    anomaly_flag: bool = False
    anomaly_reason: Optional[str] = None


def _pol_out(p: AIAgentPolicy) -> dict:
    return {
        "id": str(p.id), "agent_name": p.agent_name, "description": p.description,
        "allowed_actions": p.allowed_actions, "forbidden_actions": p.forbidden_actions,
        "max_cost_per_run_tokens": p.max_cost_per_run_tokens,
        "requires_human_approval": p.requires_human_approval,
        "max_runs_per_hour": p.max_runs_per_hour,
        "allowed_modules": p.allowed_modules,
        "hallucination_guardrail": p.hallucination_guardrail,
        "rag_enabled": p.rag_enabled,
        "is_active": p.is_active,
        "created_by": p.created_by,
        "created_at": p.created_at.isoformat() if p.created_at else "",
    }


@router.post("/governance/policies", status_code=201)
async def create_policy(payload: PolicyIn, db: AsyncSession = Depends(get_db),
                        current_user=Depends(require_permission("ai", "create"))):
    pol = AIAgentPolicy(
        **payload.model_dump(),
        created_by=getattr(current_user, "username", None) or str(current_user.id),
    )
    db.add(pol)
    await db.commit()
    await db.refresh(pol)
    return _pol_out(pol)


@router.get("/governance/policies")
async def list_policies(active_only: bool = True, db: AsyncSession = Depends(get_db),
                        _=Depends(require_permission("ai", "view"))):
    q = select(AIAgentPolicy)
    if active_only:
        q = q.where(AIAgentPolicy.is_active == True)
    q = q.order_by(AIAgentPolicy.agent_name)
    rows = (await db.execute(q)).scalars().all()
    return [_pol_out(p) for p in rows]


@router.patch("/governance/policies/{policy_id}/toggle")
async def toggle_policy(policy_id: str, db: AsyncSession = Depends(get_db),
                        _=Depends(require_permission("ai", "edit"))):
    r = await db.execute(select(AIAgentPolicy).where(AIAgentPolicy.id == uuid.UUID(policy_id)))
    pol = r.scalar_one_or_none()
    if not pol:
        raise HTTPException(404, "Policy not found")
    pol.is_active = not pol.is_active
    await db.commit()
    return {"id": policy_id, "is_active": pol.is_active}


@router.post("/governance/runs", status_code=201)
async def log_run(payload: RunLogIn, db: AsyncSession = Depends(get_db),
                  _=Depends(require_permission("ai", "create"))):
    """Log an AI agent run. Called by agent code after each execution."""
    # Find policy for this agent
    pol_r = await db.execute(
        select(AIAgentPolicy).where(AIAgentPolicy.agent_name == payload.agent_name,
                                    AIAgentPolicy.is_active == True)
    )
    policy = pol_r.scalar_one_or_none()

    run = AIAgentRun(
        policy_id=policy.id if policy else None,
        agent_name=payload.agent_name,
        trigger=payload.trigger,
        triggered_by=payload.triggered_by,
        actions_taken=payload.actions_taken,
        tokens_used=payload.tokens_used,
        cost_usd=payload.cost_usd,
        status=AIAgentRunStatus(payload.status),
        result_summary=payload.result_summary,
        anomaly_flag=payload.anomaly_flag,
        anomaly_reason=payload.anomaly_reason,
        completed_at=_dt.utcnow(),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return {
        "id": str(run.id), "agent_name": run.agent_name, "status": run.status,
        "tokens_used": run.tokens_used, "anomaly_flag": run.anomaly_flag,
    }


@router.get("/governance/runs")
async def list_runs(
    agent_name: Optional[str] = None,
    flagged_only: bool = False,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("ai", "view")),
):
    q = select(AIAgentRun)
    if agent_name:
        q = q.where(AIAgentRun.agent_name == agent_name)
    if flagged_only:
        q = q.where(AIAgentRun.anomaly_flag == True)
    q = q.order_by(desc(AIAgentRun.started_at)).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": str(r.id), "agent_name": r.agent_name, "trigger": r.trigger,
            "triggered_by": r.triggered_by, "status": r.status,
            "tokens_used": r.tokens_used,
            "cost_usd": float(r.cost_usd) if r.cost_usd else None,
            "anomaly_flag": r.anomaly_flag, "anomaly_reason": r.anomaly_reason,
            "started_at": r.started_at.isoformat() if r.started_at else "",
            "result_summary": r.result_summary,
        }
        for r in rows
    ]


@router.get("/governance/dashboard")
async def governance_dashboard(db: AsyncSession = Depends(get_db), _=Depends(require_permission("ai", "view"))):
    from sqlalchemy import func
    total_pol_r = await db.execute(
        select(func.count()).select_from(AIAgentPolicy).where(AIAgentPolicy.is_active == True)
    )
    total_runs_r = await db.execute(select(func.count()).select_from(AIAgentRun))
    flagged_r = await db.execute(
        select(func.count()).select_from(AIAgentRun).where(AIAgentRun.anomaly_flag == True)
    )
    total_tokens_r = await db.execute(
        select(func.sum(AIAgentRun.tokens_used)).where(AIAgentRun.tokens_used.isnot(None))
    )
    by_status_r = await db.execute(
        select(AIAgentRun.status, func.count().label("cnt")).group_by(AIAgentRun.status)
    )
    return {
        "active_policies": total_pol_r.scalar() or 0,
        "total_runs": total_runs_r.scalar() or 0,
        "flagged_runs": flagged_r.scalar() or 0,
        "total_tokens_consumed": int(total_tokens_r.scalar() or 0),
        "runs_by_status": {r.status: r.cnt for r in by_status_r.all()},
    }


# ── Gap 24: Prompt Registry ───────────────────────────────────────────────────

def _prompt_out(p: AIPrompt) -> dict:
    return {
        "id": str(p.id),
        "key": p.key,
        "version": p.version,
        "title": p.title,
        "module": p.module,
        "prompt_type": p.prompt_type,
        "content": p.content,
        "variables": p.variables,
        "is_active": p.is_active,
        "notes": p.notes,
        "created_by": p.created_by,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


@router.get("/prompts/",
            dependencies=[Depends(require_permission("ai", "configure"))])
async def list_prompts(
    key: Optional[str] = None,
    module: Optional[str] = None,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    q = select(AIPrompt).order_by(AIPrompt.key, AIPrompt.version.desc())
    if key:
        q = q.where(AIPrompt.key == key)
    if module:
        q = q.where(AIPrompt.module == module)
    if active_only:
        q = q.where(AIPrompt.is_active == True)  # noqa: E712
    rows = (await db.execute(q)).scalars().all()
    return [_prompt_out(p) for p in rows]


@router.post("/prompts/", status_code=201)
async def create_prompt(
    body: AIPromptCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("ai", "configure")),
):
    p = AIPrompt(
        **body.model_dump(),
        created_by=getattr(current_user, "username", None) or str(current_user.id),
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return _prompt_out(p)


@router.get("/prompts/{prompt_id}/",
            dependencies=[Depends(require_permission("ai", "configure"))])
async def get_prompt(prompt_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    p = (await db.execute(select(AIPrompt).where(AIPrompt.id == prompt_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Prompt not found")
    return _prompt_out(p)


@router.put("/prompts/{prompt_id}/",
            dependencies=[Depends(require_permission("ai", "configure"))])
async def update_prompt(
    prompt_id: uuid.UUID,
    body: AIPromptUpdate,
    db: AsyncSession = Depends(get_db),
):
    p = (await db.execute(select(AIPrompt).where(AIPrompt.id == prompt_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Prompt not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(p, field, value)
    await db.commit()
    await db.refresh(p)
    return _prompt_out(p)


@router.post("/prompts/{key}/deactivate",
             dependencies=[Depends(require_permission("ai", "configure"))])
async def deactivate_prompt_key(key: str, db: AsyncSession = Depends(get_db)):
    """Deactivate all versions for a prompt key."""
    rows = (await db.execute(
        select(AIPrompt).where(AIPrompt.key == key, AIPrompt.is_active == True)  # noqa: E712
    )).scalars().all()
    for p in rows:
        p.is_active = False
    await db.commit()
    return {"key": key, "deactivated": len(rows)}
