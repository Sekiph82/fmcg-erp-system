"""
AI Service — business logic layer.

Gathers ERP data, engineers prompts, calls the AI provider,
persists results, and returns structured outputs.
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

log = logging.getLogger(__name__)

SYSTEM_PROMPT_FMCG = """You are an expert AI assistant embedded in an FMCG (Fast-Moving Consumer Goods) ERP system
for a manufacturing company in Kenya/East Africa producing personal care and home care products (detergents, shampoos, creams, wipes, etc.).

You have deep expertise in:
- FMCG product formulation chemistry (surfactants, emulsifiers, preservatives, rheology)
- East African/Kenyan market dynamics
- Supply chain management and procurement
- Financial analysis and margin optimization
- Demand forecasting and inventory management

Always provide actionable, specific, commercially realistic advice grounded in actual industry practice.
All monetary values in KES unless specified otherwise.
Always output valid JSON as specified in each prompt."""


# ── ERP Data Gatherer ─────────────────────────────────────────────────────────

async def _gather_erp_context(db: AsyncSession) -> dict:
    """Pull live ERP data to feed into AI prompts."""
    from app.models.sales import Invoice, SalesOrder, Customer, InvoiceStatus
    from app.models.inventory import Stock
    from app.models.master import Product, Material, Supplier
    from app.models.procurement import PurchaseOrder, POStatus

    today = date.today()
    d90 = today - timedelta(days=90)

    # Sales last 90 days
    sales = (await db.execute(
        select(
            func.count(Invoice.id).label("invoice_count"),
            func.coalesce(func.sum(Invoice.total_amount), 0).label("total_revenue"),
            func.coalesce(func.sum(Invoice.paid_amount), 0).label("total_collected"),
        )
        .where(Invoice.invoice_date >= d90)
        .where(Invoice.status.notin_([InvoiceStatus.CANCELLED, InvoiceStatus.DRAFT]))
    )).one()

    # Outstanding receivables
    recv = (await db.execute(
        select(func.coalesce(
            func.sum(Invoice.total_amount - Invoice.paid_amount), 0
        ).label("outstanding"))
        .where(Invoice.status.notin_([InvoiceStatus.PAID, InvoiceStatus.CANCELLED]))
    )).scalar() or 0

    # Inventory summary
    inventory = (await db.execute(
        select(
            func.count(Stock.id).label("sku_count"),
            func.coalesce(func.sum(Stock.quantity_on_hand), 0).label("total_qty"),
        )
    )).one()

    # Low-stock items (quantity_on_hand <= reorder_point)
    low_stock_items = (await db.execute(
        select(Product.name, Stock.quantity_on_hand, Product.uom)
        .join(Stock, Stock.product_id == Product.id)
        .where(Stock.quantity_on_hand <= Stock.reorder_point)
        .limit(10)
    )).all()

    # Active products
    product_count = (await db.execute(
        select(func.count(Product.id)).where(Product.is_active == True)
    )).scalar() or 0

    # Active suppliers
    supplier_count = (await db.execute(
        select(func.count(Supplier.id)).where(Supplier.is_active == True)
    )).scalar() or 0

    # Open POs
    open_pos = (await db.execute(
        select(func.count(PurchaseOrder.id))
        .where(PurchaseOrder.status.in_([POStatus.APPROVED, POStatus.ORDERED, POStatus.PARTIALLY_RECEIVED]))
    )).scalar() or 0

    return {
        "sales_90d": {
            "invoice_count": sales.invoice_count,
            "total_revenue_kes": float(sales.total_revenue),
            "total_collected_kes": float(sales.total_collected),
            "outstanding_receivables_kes": float(recv),
        },
        "inventory": {
            "total_sku_count": inventory.sku_count,
            "total_qty": float(inventory.total_qty),
            "low_stock_items": [
                {"name": r.name, "qty": float(r.quantity_on_hand), "uom": r.uom}
                for r in low_stock_items
            ],
        },
        "master_data": {
            "active_products": product_count,
            "active_suppliers": supplier_count,
            "open_purchase_orders": open_pos,
        },
        "date": str(today),
    }


# ── AI Request logger ─────────────────────────────────────────────────────────

async def _log_request(
    db: AsyncSession,
    request_type: AIRequestType,
    input_data: dict,
    user_id: Optional[uuid.UUID],
) -> AIRequest:
    req = AIRequest(
        request_type=request_type,
        provider=AIProviderEnum(settings.AI_PROVIDER),
        model=settings.ANTHROPIC_MODEL if settings.AI_PROVIDER == "anthropic" else settings.OPENAI_MODEL,
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

PREDICTION_SCHEMA = """{
  "predictions": [
    {
      "type": "sales_forecast | demand_prediction | stock_depletion | cost_trend | supplier_risk | production_planning",
      "subject": "string",
      "period": "string",
      "forecast_value": number_or_null,
      "unit": "string",
      "confidence": 0.0_to_1.0,
      "trend": "up | down | stable",
      "trend_pct": number_or_null,
      "risk_level": "low | medium | high | critical",
      "summary": "2-3 sentence actionable summary",
      "items_at_risk": ["array of specific items if applicable"]
    }
  ],
  "generated_at": "YYYY-MM-DD",
  "data_freshness": "string"
}"""


async def generate_predictions(
    db: AsyncSession,
    prediction_types: Optional[list[str]] = None,
    user_id: Optional[uuid.UUID] = None,
) -> list[AIPrediction]:
    erp_ctx = await _gather_erp_context(db)
    types_str = ", ".join(prediction_types) if prediction_types else "all types"

    prompt = f"""Analyze this FMCG ERP data and generate predictions for: {types_str}

ERP Context (last 90 days):
{json.dumps(erp_ctx, indent=2)}

Generate comprehensive predictions covering:
1. Sales forecast (next 30 days)
2. Demand prediction by category
3. Stock depletion risk (focus on low-stock items)
4. Raw material cost trends (next 90 days)
5. Supplier risk assessment
6. Production planning recommendations

For each prediction provide specific KES values, timelines, and actionable insights.
Today is {erp_ctx['date']}.

Output schema:
{PREDICTION_SCHEMA}"""

    req = await _log_request(db, AIRequestType.PREDICTION,
                              {"erp_context": erp_ctx, "types": prediction_types}, user_id)
    resp = None
    try:
        provider = get_ai_provider()
        obj, resp = await provider.generate_structured_output(prompt, system=SYSTEM_PROMPT_FMCG)
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

RECOMMENDATION_SCHEMA = """{
  "recommendations": [
    {
      "category": "pricing | stock | supplier | production | margin | cash_flow",
      "title": "short actionable title",
      "reason": "why this is recommended (data-backed)",
      "expected_impact": "specific quantified impact",
      "confidence_level": "low | medium | high",
      "priority": "low | medium | high | critical",
      "action_steps": ["step 1", "step 2"]
    }
  ],
  "generated_at": "YYYY-MM-DD"
}"""


async def generate_recommendations(
    db: AsyncSession,
    focus_area: Optional[str] = None,
    user_id: Optional[uuid.UUID] = None,
) -> list[AIRecommendation]:
    erp_ctx = await _gather_erp_context(db)
    focus_str = f"Focus particularly on: {focus_area}" if focus_area else "Cover all areas"

    prompt = f"""Based on this FMCG ERP data, generate specific, actionable recommendations.
{focus_str}

ERP Context:
{json.dumps(erp_ctx, indent=2)}

Generate 5–8 recommendations covering:
- Pricing optimization (where margins can be improved)
- Stock optimization (what to reorder, what's overstocked)
- Supplier selection (risks, alternates)
- Production planning (capacity, scheduling)
- Margin improvement (cost reduction, mix shift)
- Cash flow optimization

Each recommendation must have specific numbers, timelines, and clear ROI.

Output schema:
{RECOMMENDATION_SCHEMA}"""

    req = await _log_request(db, AIRequestType.RECOMMENDATION,
                              {"erp_context": erp_ctx, "focus": focus_area}, user_id)
    resp = None
    try:
        provider = get_ai_provider()
        obj, resp = await provider.generate_structured_output(prompt, system=SYSTEM_PROMPT_FMCG)
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

SCENARIO_SCHEMA = """{
  "scenario": {
    "title": "string",
    "type": "string",
    "parameters": {},
    "expected_impact": {
      "revenue_change_pct": number,
      "volume_change_pct": number,
      "margin_change_pct": number,
      "break_even_months": number_or_null
    },
    "risks": ["risk 1", "risk 2"],
    "opportunities": ["opportunity 1", "opportunity 2"],
    "recommendation": "final actionable recommendation"
  }
}"""


async def simulate_scenario(
    db: AsyncSession,
    scenario_type: str,
    parameters: dict,
    user_id: Optional[uuid.UUID] = None,
) -> AIScenario:
    erp_ctx = await _gather_erp_context(db)

    scenario_descriptions = {
        "price_change": f"Simulate changing product prices by {parameters.get('change_pct', 10)}% for {parameters.get('product', 'selected products')}",
        "cost_change": f"Simulate raw material cost change of {parameters.get('change_pct', 15)}% for {parameters.get('material', 'key inputs')}",
        "supplier_change": f"Simulate switching supplier for {parameters.get('material', 'key material')} to {parameters.get('new_supplier', 'alternative supplier')} at {parameters.get('price_change_pct', 0)}% price difference",
        "product_change": f"Simulate {parameters.get('action', 'launching')} product: {parameters.get('product', 'new SKU')}",
    }
    description = scenario_descriptions.get(scenario_type, f"Simulate scenario: {parameters}")

    prompt = f"""Simulate this business scenario for an FMCG company:

Scenario: {description}
Full Parameters: {json.dumps(parameters)}

Current ERP Context:
{json.dumps(erp_ctx, indent=2)}

Provide a detailed impact analysis including:
- Revenue, volume, and margin impacts (as percentages and KES amounts)
- Break-even timeline if applicable
- Top 3–5 risks with mitigation ideas
- Top 3–5 opportunities to capitalize on
- Final recommendation (proceed / modify / avoid)

Be specific with numbers based on the ERP data provided.

Output schema:
{SCENARIO_SCHEMA}"""

    req = await _log_request(db, AIRequestType.SCENARIO,
                              {"type": scenario_type, "parameters": parameters, "erp_context": erp_ctx}, user_id)
    resp = None
    try:
        provider = get_ai_provider()
        obj, resp = await provider.generate_structured_output(prompt, system=SYSTEM_PROMPT_FMCG)
        await _finish_request(db, req, resp, obj)

        scenario_data = obj.get("scenario", obj)
        scenario = AIScenario(
            request_id=req.id,
            title=scenario_data.get("title", description),
            scenario_type=scenario_type,
            input_parameters=parameters,
            expected_impact=json.dumps(scenario_data.get("expected_impact", {})),
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

FORMULATION_SCHEMA = """{
  "formulation": {
    "name": "string",
    "product_category": "string",
    "version": "standard",
    "description": "string",
    "ingredients": [
      {
        "ingredient_name": "Full chemical name with grade/concentration",
        "inci_name": "INCI / IUPAC name",
        "cas_number": "string or N/A",
        "percentage": number,
        "function": "function in formulation",
        "supplier_examples": ["supplier1", "supplier2"],
        "approx_cost_per_kg_usd": number
      }
    ],
    "process_instructions": ["step 1", "step 2", "..."],
    "processing_temperature": "string",
    "mixing_speed": "string",
    "estimated_ph": "string",
    "estimated_viscosity_cP": "string or null",
    "cost_breakdown": {
      "raw_materials_per_kg_usd": number,
      "packaging_estimate_per_unit_usd": number,
      "labor_overhead_per_kg_usd": number,
      "total_cogs_per_kg_usd": number
    },
    "performance_profile": {
      "cleaning_efficiency": "rating/10 and description",
      "foam_level": "Low|Medium|High",
      "rinse_ability": "string",
      "stability": "string",
      "biodegradability": "string",
      "skin_mildness": "string",
      "antibacterial": "string"
    },
    "alternatives": {
      "low_cost": {"name": "string", "key_changes": "string", "trade_offs": "string"},
      "premium": {"name": "string", "key_changes": "string", "trade_offs": "string"},
      "eco": {"name": "string", "key_changes": "string", "trade_offs": "string"}
    },
    "safety_notes": ["note 1", "note 2"],
    "regulatory_notes": "string",
    "shelf_life": "string"
  }
}"""


async def generate_formulation(
    db: AsyncSession,
    product_category: str,
    target_properties: dict,
    cost_target: Optional[float],
    performance_priority: str,
    user_id: Optional[uuid.UUID] = None,
) -> AIFormulation:

    # Try to load ERP material context
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

    prompt = f"""You are a senior formulation chemist specializing in FMCG products.
Generate a complete, commercially viable formulation for the following:

Product Category: {product_category}
Target Properties:
{props_str}
Performance Priority: {performance_priority} (cost = minimize cost, quality = maximize performance, balanced = both)
{cost_str}
{erp_mat_str}

REQUIREMENTS:
1. Use REAL chemical ingredient names (not generic like "surfactant" — use "Sodium Lauryl Ether Sulfate 70%")
2. Include CAS numbers for all synthetic ingredients
3. All percentages must add up to EXACTLY 100%
4. Cost estimates must be realistic USD/kg for East African market (2024–2025)
5. Process instructions must be step-by-step, practically executable
6. Include all three alternative formulations (low-cost, premium, eco-friendly)
7. Safety notes must be specific to the actual chemicals used

This formulation will be reviewed by the company's quality team before production.

Output schema (follow EXACTLY):
{FORMULATION_SCHEMA}"""

    req = await _log_request(db, AIRequestType.FORMULATION, {
        "product_category": product_category,
        "target_properties": target_properties,
        "cost_target": cost_target,
        "performance_priority": performance_priority,
    }, user_id)
    resp = None
    try:
        provider = get_ai_provider()
        obj, resp = await provider.generate_structured_output(prompt, system=SYSTEM_PROMPT_FMCG)
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

    # Count stored items
    pred_count = (await db.execute(
        select(func.count(AIPrediction.id)).where(AIPrediction.is_archived == False)
    )).scalar() or 0

    rec_count = (await db.execute(
        select(func.count(AIRecommendation.id))
        .where(AIRecommendation.is_actioned == False, AIRecommendation.is_dismissed == False)
    )).scalar() or 0

    form_count = (await db.execute(
        select(func.count(AIFormulation.id))
    )).scalar() or 0

    scenario_count = (await db.execute(
        select(func.count(AIScenario.id))
    )).scalar() or 0

    # Recent predictions
    recent_preds = (await db.execute(
        select(AIPrediction).order_by(desc(AIPrediction.created_at)).limit(5)
    )).scalars().all()

    # Critical recommendations
    critical_recs = (await db.execute(
        select(AIRecommendation)
        .where(AIRecommendation.priority == "critical", AIRecommendation.is_actioned == False)
        .order_by(desc(AIRecommendation.created_at))
        .limit(5)
    )).scalars().all()

    # Provider status
    provider_status = {
        "provider": settings.AI_PROVIDER,
        "configured": settings.AI_CONFIGURED,
        "model": settings.ANTHROPIC_MODEL if settings.AI_PROVIDER == "anthropic" else settings.OPENAI_MODEL,
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
