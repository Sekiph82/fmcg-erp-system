"""
AI Service — business logic layer.

Gathers ERP context, applies data masking, engineers prompts (from app.prompts),
calls the AI provider via abstraction layer, persists results.
"""
from __future__ import annotations

import json
import time
import logging
from datetime import date, timedelta
from typing import Any, Optional
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_provider import get_ai_provider, AIResponse
from app.models.ai import (
    AIRequest, AIRequestType, AIProvider as AIProviderEnum,
    AIRequestStatus, AIPrediction, AIRecommendation, AIFormulation, AIScenario,
)
from app.core.config import settings
from app.core.ai_safety import mask_sensitive_context, build_safe_system_prompt

# Import prompt templates from dedicated module
from app.prompts.central_ai import SYSTEM_PROMPT_FMCG
from app.prompts.chat import CHAT_SYSTEM_PROMPT
from app.prompts.predictions import PREDICTION_SCHEMA, build_prediction_prompt
from app.prompts.recommendations import RECOMMENDATION_SCHEMA, build_recommendation_prompt
from app.prompts.scenarios import SCENARIO_SCHEMA, build_scenario_prompt
from app.prompts.formulations import FORMULATION_SCHEMA, build_formulation_prompt

log = logging.getLogger(__name__)


# ── ERP Data Gatherer ─────────────────────────────────────────────────────────

async def _gather_erp_context(db: AsyncSession) -> dict:
    """Pull live ERP aggregate data to feed into AI prompts."""
    from app.models.sales import Invoice, InvoiceStatus
    from app.models.inventory import Stock
    from app.models.master import Product, Material, Supplier
    from app.models.procurement import PurchaseOrder, POStatus

    today = date.today()
    d90 = today - timedelta(days=90)

    try:
        sales = (await db.execute(
            select(
                func.count(Invoice.id).label("invoice_count"),
                func.coalesce(func.sum(Invoice.total_amount), 0).label("total_revenue"),
                func.coalesce(func.sum(Invoice.paid_amount), 0).label("total_collected"),
            )
            .where(Invoice.invoice_date >= d90)
            .where(Invoice.status.notin_([InvoiceStatus.CANCELLED, InvoiceStatus.DRAFT]))
        )).one()
        sales_data = {
            "invoice_count": sales.invoice_count,
            "total_revenue_kes": float(sales.total_revenue),
            "total_collected_kes": float(sales.total_collected),
        }
    except Exception as e:
        log.warning("Could not gather sales context: %s", e)
        sales_data = {"invoice_count": 0, "total_revenue_kes": 0, "total_collected_kes": 0}

    try:
        recv = (await db.execute(
            select(func.coalesce(
                func.sum(Invoice.total_amount - Invoice.paid_amount), 0
            ).label("outstanding"))
            .where(Invoice.status.notin_([InvoiceStatus.PAID, InvoiceStatus.CANCELLED]))
        )).scalar() or 0
        sales_data["outstanding_receivables_kes"] = float(recv)
    except Exception as e:
        log.warning("Could not gather receivables: %s", e)
        sales_data["outstanding_receivables_kes"] = 0

    try:
        inventory = (await db.execute(
            select(
                func.count(Stock.id).label("sku_count"),
                func.coalesce(func.sum(Stock.quantity_on_hand), 0).label("total_qty"),
            )
        )).one()
        # reorder_point is on Product, NOT Stock
        low_stock_items = (await db.execute(
            select(Product.name, Stock.quantity_on_hand, Product.uom)
            .join(Stock, Stock.product_id == Product.id)
            .where(Stock.quantity_on_hand <= Product.reorder_point)
            .limit(settings.AI_CONTEXT_MAX_RECORDS)
        )).all()
        inventory_data = {
            "total_sku_count": inventory.sku_count,
            "total_qty": float(inventory.total_qty),
            "low_stock_items": [
                {"name": r.name, "qty": float(r.quantity_on_hand), "uom": r.uom}
                for r in low_stock_items
            ],
        }
    except Exception as e:
        log.warning("Could not gather inventory context: %s", e)
        inventory_data = {"total_sku_count": 0, "total_qty": 0, "low_stock_items": []}

    try:
        product_count = (await db.execute(
            select(func.count(Product.id)).where(Product.is_active == True)  # noqa: E712
        )).scalar() or 0
        supplier_count = (await db.execute(
            select(func.count(Supplier.id)).where(Supplier.is_active == True)  # noqa: E712
        )).scalar() or 0
    except Exception as e:
        log.warning("Could not gather master data counts: %s", e)
        product_count, supplier_count = 0, 0

    try:
        open_pos = (await db.execute(
            select(func.count(PurchaseOrder.id))
            .where(PurchaseOrder.status.in_([POStatus.APPROVED, POStatus.ORDERED, POStatus.PARTIALLY_RECEIVED]))
        )).scalar() or 0
    except Exception as e:
        log.warning("Could not gather PO context: %s", e)
        open_pos = 0

    return {
        "sales_90d": sales_data,
        "inventory": inventory_data,
        "master_data": {
            "active_products": product_count,
            "active_suppliers": supplier_count,
            "open_purchase_orders": open_pos,
        },
        "date": str(today),
    }


# ── AI Request logger ─────────────────────────────────────────────────────────

def _resolve_provider_enum() -> AIProviderEnum:
    active = get_ai_provider()
    name = active.__class__.__name__.lower().replace("provider", "")
    mapping = {
        "anthropic": AIProviderEnum.ANTHROPIC,
        "openai": AIProviderEnum.OPENAI,
        "gemini": AIProviderEnum.GEMINI,
        "mock": AIProviderEnum.MOCK,
    }
    return mapping.get(name, AIProviderEnum.AUTO)


def _resolve_model_name() -> str:
    active = get_ai_provider()
    return getattr(active, "_model", getattr(active, "_model_name", "mock-v1"))


async def _log_request(
    db: AsyncSession,
    request_type: AIRequestType,
    input_data: dict,
    user_id: Optional[uuid.UUID],
) -> AIRequest:
    req = AIRequest(
        request_type=request_type,
        provider=_resolve_provider_enum(),
        model=_resolve_model_name(),
        status=AIRequestStatus.RUNNING,
        input_data=input_data,
        created_by_id=user_id,
    )
    db.add(req)
    await db.flush()
    return req


async def _finish_request(
    db: AsyncSession,
    req: AIRequest,
    resp: AIResponse,
    output_data: Any,
    error: Optional[str] = None,
):
    req.status = AIRequestStatus.FAILED if error else AIRequestStatus.COMPLETED
    req.prompt_tokens = resp.prompt_tokens if resp else 0
    req.completion_tokens = resp.completion_tokens if resp else 0
    req.latency_ms = resp.latency_ms if resp else 0
    req.output_data = output_data
    req.error_message = error


# ── Prediction Engine ─────────────────────────────────────────────────────────

async def generate_predictions(
    db: AsyncSession,
    prediction_types: Optional[list[str]] = None,
    user_id: Optional[uuid.UUID] = None,
) -> list[AIPrediction]:
    erp_ctx = await _gather_erp_context(db)
    masked_ctx = mask_sensitive_context(erp_ctx)
    types_str = ", ".join(prediction_types) if prediction_types else "all types"

    safe_system = build_safe_system_prompt(SYSTEM_PROMPT_FMCG)
    prompt = build_prediction_prompt(masked_ctx, types_str)

    req = await _log_request(db, AIRequestType.PREDICTION,
                              {"types": prediction_types}, user_id)
    resp = None
    try:
        provider = get_ai_provider()
        obj, resp = await provider.generate_structured_output(prompt, system=safe_system)
        await _finish_request(db, req, resp, obj)

        results = []
        for p in obj.get("predictions", []):
            pred = AIPrediction(
                request_id=req.id,
                prediction_type=p.get("type", "unknown"),
                subject_name=p.get("subject"),
                period=p.get("period"),
                forecast_value=p.get("forecast_value"),
                confidence_score=p.get("confidence"),
                risk_level=p.get("risk_level"),
                trend=p.get("trend"),
                summary=p.get("summary"),
                details=p,
                created_by_id=user_id,
            )
            db.add(pred)
            results.append(pred)
        return results
    except Exception as e:
        await _finish_request(db, req, resp or AIResponse("", "mock", "mock"), None, str(e))
        raise


# ── Recommendation Engine ─────────────────────────────────────────────────────

async def generate_recommendations(
    db: AsyncSession,
    focus_area: Optional[str] = None,
    user_id: Optional[uuid.UUID] = None,
) -> list[AIRecommendation]:
    erp_ctx = await _gather_erp_context(db)
    masked_ctx = mask_sensitive_context(erp_ctx)
    focus_str = f"Focus particularly on: {focus_area}" if focus_area else "Cover all areas"

    safe_system = build_safe_system_prompt(SYSTEM_PROMPT_FMCG)
    prompt = build_recommendation_prompt(masked_ctx, focus_str)

    req = await _log_request(db, AIRequestType.RECOMMENDATION,
                              {"focus": focus_area}, user_id)
    resp = None
    try:
        provider = get_ai_provider()
        obj, resp = await provider.generate_structured_output(prompt, system=safe_system)
        await _finish_request(db, req, resp, obj)

        results = []
        for r in obj.get("recommendations", []):
            rec = AIRecommendation(
                request_id=req.id,
                category=r.get("category", "general"),
                title=r.get("title", ""),
                reason=r.get("reason"),
                expected_impact=r.get("expected_impact"),
                confidence_level=r.get("confidence_level"),
                priority=r.get("priority", "medium"),
                action_data=r,
                created_by_id=user_id,
            )
            db.add(rec)
            results.append(rec)
        return results
    except Exception as e:
        await _finish_request(db, req, resp or AIResponse("", "mock", "mock"), None, str(e))
        raise


# ── Scenario Simulator ────────────────────────────────────────────────────────

async def simulate_scenario(
    db: AsyncSession,
    scenario_type: str,
    parameters: dict,
    user_id: Optional[uuid.UUID] = None,
) -> AIScenario:
    erp_ctx = await _gather_erp_context(db)
    masked_ctx = mask_sensitive_context(erp_ctx)

    scenario_descriptions = {
        "price_change": f"Simulate changing product prices by {parameters.get('change_pct', 10)}% for {parameters.get('product', 'selected products')}",
        "cost_change": f"Simulate raw material cost change of {parameters.get('change_pct', 15)}% for {parameters.get('material', 'key inputs')}",
        "supplier_change": f"Simulate switching supplier for {parameters.get('material', 'key material')} to {parameters.get('new_supplier', 'alternative supplier')} at {parameters.get('price_change_pct', 0)}% price difference",
        "product_change": f"Simulate {parameters.get('action', 'launching')} product: {parameters.get('product', 'new SKU')}",
    }
    description = scenario_descriptions.get(scenario_type, f"Simulate scenario: {parameters}")

    safe_system = build_safe_system_prompt(SYSTEM_PROMPT_FMCG)
    prompt = build_scenario_prompt(masked_ctx, description, parameters)

    req = await _log_request(db, AIRequestType.SCENARIO,
                              {"type": scenario_type, "parameters": parameters}, user_id)
    resp = None
    try:
        provider = get_ai_provider()
        obj, resp = await provider.generate_structured_output(prompt, system=safe_system)
        await _finish_request(db, req, resp, obj)

        scenario_data = obj.get("scenario", obj)
        # Store expected_impact as JSON string in Text column (parsed on read in serializer)
        expected_impact_raw = scenario_data.get("expected_impact", {})
        scenario = AIScenario(
            request_id=req.id,
            title=scenario_data.get("title", description),
            scenario_type=scenario_type,
            input_parameters=parameters,
            expected_impact=json.dumps(expected_impact_raw) if isinstance(expected_impact_raw, dict) else expected_impact_raw,
            risks=scenario_data.get("risks", []),
            opportunities=scenario_data.get("opportunities", []),
            simulation_data=scenario_data,
            created_by_id=user_id,
        )
        db.add(scenario)
        return scenario
    except Exception as e:
        await _finish_request(db, req, resp or AIResponse("", "mock", "mock"), None, str(e))
        raise


# ── Formulation Engine ────────────────────────────────────────────────────────

async def generate_formulation(
    db: AsyncSession,
    product_category: str,
    target_properties: dict,
    cost_target: Optional[float],
    performance_priority: str,
    user_id: Optional[uuid.UUID] = None,
) -> AIFormulation:
    try:
        from app.models.master import Material
        materials = (await db.execute(
            select(Material.name, Material.uom).limit(20)
        )).all()
        erp_materials = [m.name for m in materials]
    except Exception:
        erp_materials = []

    cost_str = f"Target cost: ≤ ${cost_target:.2f}/kg" if cost_target else "No specific cost constraint"
    props_str = "\n".join(f"  - {k}: {v}" for k, v in target_properties.items())
    erp_mat_str = f"Available ERP materials (use if applicable): {', '.join(erp_materials)}" if erp_materials else ""

    safe_system = build_safe_system_prompt(SYSTEM_PROMPT_FMCG)
    prompt = build_formulation_prompt(product_category, props_str, performance_priority, cost_str, erp_mat_str)

    req = await _log_request(db, AIRequestType.FORMULATION, {
        "product_category": product_category,
        "performance_priority": performance_priority,
    }, user_id)
    resp = None
    try:
        provider = get_ai_provider()
        obj, resp = await provider.generate_structured_output(prompt, system=safe_system)
        await _finish_request(db, req, resp, obj)

        form_data = obj.get("formulation", obj)
        cost_breakdown = form_data.get("cost_breakdown", {})
        estimated_cost = cost_breakdown.get("total_cogs_per_kg_usd") or cost_breakdown.get("raw_materials_per_kg_usd")

        formulation = AIFormulation(
            request_id=req.id,
            name=form_data.get("name", f"{product_category} formulation"),
            product_category=product_category,
            version="standard",
            target_properties=target_properties,
            cost_target=cost_target,
            performance_priority=performance_priority,
            formulation_data=form_data,
            estimated_cost_per_kg=estimated_cost,
            created_by_id=user_id,
        )
        db.add(formulation)
        return formulation
    except Exception as e:
        await _finish_request(db, req, resp or AIResponse("", "mock", "mock"), None, str(e))
        raise


# ── AI Dashboard Summary ──────────────────────────────────────────────────────

async def get_ai_dashboard(db: AsyncSession) -> dict:
    from sqlalchemy import desc

    pred_count = (await db.execute(
        select(func.count(AIPrediction.id)).where(AIPrediction.is_archived == False)  # noqa: E712
    )).scalar() or 0

    rec_count = (await db.execute(
        select(func.count(AIRecommendation.id))
        .where(AIRecommendation.is_actioned == False, AIRecommendation.is_dismissed == False)  # noqa: E712
    )).scalar() or 0

    form_count = (await db.execute(
        select(func.count(AIFormulation.id))
    )).scalar() or 0

    scenario_count = (await db.execute(
        select(func.count(AIScenario.id))
    )).scalar() or 0

    recent_preds = (await db.execute(
        select(AIPrediction).order_by(desc(AIPrediction.created_at)).limit(5)
    )).scalars().all()

    critical_recs = (await db.execute(
        select(AIRecommendation)
        .where(AIRecommendation.priority == "critical", AIRecommendation.is_actioned == False)  # noqa: E712
        .order_by(desc(AIRecommendation.created_at))
        .limit(5)
    )).scalars().all()

    active_provider = get_ai_provider()
    provider_name = active_provider.__class__.__name__.replace("Provider", "").lower()
    provider_status = {
        "provider": provider_name,
        "configured": settings.AI_CONFIGURED,
        "model": getattr(active_provider, "_model", getattr(active_provider, "_model_name", "mock-v1")),
        "mode": "mock" if provider_name == "mock" else "llm",
        "fallback_active": provider_name == "mock" and not settings.AI_CONFIGURED,
    }

    return {
        "stats": {
            "active_predictions": pred_count,
            "pending_recommendations": rec_count,
            "saved_formulations": form_count,
            "scenario_simulations": scenario_count,
        },
        "provider": provider_status,
        "recent_predictions": [
            {
                "id": str(p.id),
                "type": p.prediction_type,
                "subject": p.subject_name,
                "risk_level": p.risk_level,
                "trend": p.trend,
                "summary": p.summary,
                "created_at": str(p.created_at),
            }
            for p in recent_preds
        ],
        "critical_recommendations": [
            {
                "id": str(r.id),
                "category": r.category,
                "title": r.title,
                "priority": r.priority,
                "expected_impact": r.expected_impact,
            }
            for r in critical_recs
        ],
    }


# ── ERP Copilot Chat ──────────────────────────────────────────────────────────

async def generate_chat_response(
    db: AsyncSession,
    message: str,
    conversation_history: Optional[list[dict]] = None,
    user_id: Optional[uuid.UUID] = None,
) -> dict:
    """
    ERP Copilot: answer a free-form question using masked live ERP context.
    Prompt injection sanitization is handled upstream in the endpoint layer.
    """
    erp_ctx = await _gather_erp_context(db)
    masked_ctx = mask_sensitive_context(erp_ctx)

    provider = get_ai_provider()
    is_mock = provider.__class__.__name__ == "MockProvider"

    history_str = ""
    if conversation_history:
        for turn in conversation_history[-6:]:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            history_str += f"\n{role.upper()}: {content}"

    prompt = f"""Current ERP Data Snapshot:
{json.dumps(masked_ctx, indent=2)}

{f'Conversation so far:{history_str}' if history_str else ''}

USER QUESTION: {message}

Provide a clear, data-grounded answer. If the ERP data doesn't contain enough information to answer precisely, say so and suggest what additional data would help.
{"[MOCK/DEV MODE: Use the demo data above to generate a plausible example answer. Clearly label the response as mock/demo data.]" if is_mock else ""}"""

    safe_system = build_safe_system_prompt(CHAT_SYSTEM_PROMPT)

    req = await _log_request(db, AIRequestType.DOCUMENT,
                              {"message": message}, user_id)
    resp = None
    try:
        resp = await provider.generate_text(prompt, system=safe_system)
        await _finish_request(db, req, resp, {"answer": resp.text})
        await db.commit()

        return {
            "answer": ("[MOCK/DEV MODE] " if is_mock else "") + resp.text,
            "provider": resp.provider,
            "model": resp.model,
            "mode": "mock" if is_mock else "live",
            "erp_context_used": list(masked_ctx.keys()),
            "tokens": {
                "prompt": resp.prompt_tokens,
                "completion": resp.completion_tokens,
            },
            "latency_ms": resp.latency_ms,
        }
    except Exception as e:
        err_msg = str(e)
        await _finish_request(db, req, resp or AIResponse("", "error", "error"), None, err_msg)
        await db.commit()
        raise


# ── Deterministic Forecast Baseline ──────────────────────────────────────────

async def compute_sales_baseline(db: AsyncSession) -> dict:
    """
    Deterministic weighted moving-average sales forecast — no LLM required.
    Uses last 90 days of invoice data to compute a 30-day baseline forecast.
    """
    from app.models.sales import Invoice, InvoiceStatus

    today = date.today()
    rows = []
    for months_ago in range(3, 0, -1):
        start = date(today.year, today.month, 1) - timedelta(days=30 * months_ago)
        end = start + timedelta(days=30)
        try:
            result = await db.execute(
                select(func.coalesce(func.sum(Invoice.total_amount), 0))
                .where(Invoice.invoice_date >= start)
                .where(Invoice.invoice_date < end)
                .where(Invoice.status.notin_([InvoiceStatus.CANCELLED, InvoiceStatus.DRAFT]))
            )
            rows.append(float(result.scalar() or 0))
        except Exception:
            rows.append(0.0)

    if not rows or all(v == 0 for v in rows):
        return {
            "baseline_forecast_kes": 0,
            "method": "moving_average_3m",
            "data_quality": "insufficient",
            "confidence": 0.0,
            "monthly_history": rows,
            "note": "No sales data available for baseline computation.",
        }

    avg = sum(rows) / len(rows)
    trend_pct = ((rows[-1] - rows[0]) / avg * 100) if avg > 0 else 0
    weights = [1, 2, 3]
    weighted = sum(r * w for r, w in zip(rows, weights)) / sum(weights)
    variance = sum((r - avg) ** 2 for r in rows) / len(rows)
    cv = (variance ** 0.5) / avg if avg > 0 else 1.0
    confidence = max(0.0, min(1.0, 1.0 - cv))

    return {
        "baseline_forecast_kes": round(weighted, 2),
        "moving_average_kes": round(avg, 2),
        "trend_pct": round(trend_pct, 2),
        "method": "weighted_moving_average_3m",
        "data_quality": "good" if all(r > 0 for r in rows) else "partial",
        "confidence": round(confidence, 3),
        "monthly_history_kes": rows,
        "note": "Baseline uses weighted 3-month moving average (weights: 1,2,3). LLM interprets this baseline.",
    }
