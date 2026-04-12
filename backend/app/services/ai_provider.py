"""
Provider-agnostic AI abstraction layer.

Supports:
  - Anthropic (Claude)
  - OpenAI (GPT-4o)
  - Mock (deterministic stubs for testing without API keys)

Usage:
    provider = get_ai_provider()
    text = await provider.generate_text(prompt)
    obj  = await provider.generate_structured_output(prompt, schema_hint)
"""
from __future__ import annotations

import json
import re
import time
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from app.core.config import settings

log = logging.getLogger(__name__)


# ── Response container ────────────────────────────────────────────────────────

class AIResponse:
    def __init__(
        self,
        text: str,
        provider: str,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_ms: int = 0,
    ):
        self.text = text
        self.provider = provider
        self.model = model
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.latency_ms = latency_ms

    def parse_json(self) -> Any:
        """Extract JSON from the response text (handles markdown code fences)."""
        text = self.text.strip()
        # Strip markdown code fences
        match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
        if match:
            text = match.group(1).strip()
        # Try to find first { or [
        for start_char in ["{", "["]:
            idx = text.find(start_char)
            if idx != -1:
                try:
                    return json.loads(text[idx:])
                except json.JSONDecodeError:
                    pass
        raise ValueError(f"Could not parse JSON from AI response: {text[:300]}")


# ── Base class ────────────────────────────────────────────────────────────────

class BaseAIProvider(ABC):
    @abstractmethod
    async def generate_text(self, prompt: str, system: Optional[str] = None) -> AIResponse:
        """Generate free-form text."""

    async def generate_structured_output(
        self,
        prompt: str,
        system: Optional[str] = None,
        schema_hint: Optional[str] = None,
    ) -> tuple[Any, AIResponse]:
        """Generate and parse structured JSON output.
        Returns (parsed_object, raw_response).
        """
        if schema_hint:
            full_prompt = f"{prompt}\n\nYou MUST respond with valid JSON only. No explanations. No markdown. Just raw JSON.\n\nSchema hint:\n{schema_hint}"
        else:
            full_prompt = f"{prompt}\n\nYou MUST respond with valid JSON only. No explanations. No markdown. Just raw JSON."
        resp = await self.generate_text(full_prompt, system=system)
        obj = resp.parse_json()
        return obj, resp


# ── Anthropic (Claude) ────────────────────────────────────────────────────────

class AnthropicProvider(BaseAIProvider):
    def __init__(self):
        try:
            import anthropic as _anthropic
            self._client = _anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            self._model = settings.ANTHROPIC_MODEL
        except ImportError:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

    async def generate_text(self, prompt: str, system: Optional[str] = None) -> AIResponse:
        import anthropic as _anthropic
        t0 = time.monotonic()
        messages = [{"role": "user", "content": prompt}]
        kwargs: dict = {
            "model": self._model,
            "max_tokens": settings.AI_MAX_TOKENS,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        try:
            msg = await self._client.messages.create(**kwargs)
            latency = int((time.monotonic() - t0) * 1000)
            text = msg.content[0].text if msg.content else ""
            return AIResponse(
                text=text,
                provider="anthropic",
                model=self._model,
                prompt_tokens=msg.usage.input_tokens,
                completion_tokens=msg.usage.output_tokens,
                latency_ms=latency,
            )
        except Exception as e:
            log.error("Anthropic API error: %s", e)
            raise


# ── OpenAI ────────────────────────────────────────────────────────────────────

class OpenAIProvider(BaseAIProvider):
    def __init__(self):
        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self._model = settings.OPENAI_MODEL
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")

    async def generate_text(self, prompt: str, system: Optional[str] = None) -> AIResponse:
        t0 = time.monotonic()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            resp = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=settings.AI_MAX_TOKENS,
                temperature=settings.AI_TEMPERATURE,
            )
            latency = int((time.monotonic() - t0) * 1000)
            text = resp.choices[0].message.content or ""
            usage = resp.usage
            return AIResponse(
                text=text,
                provider="openai",
                model=self._model,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                latency_ms=latency,
            )
        except Exception as e:
            log.error("OpenAI API error: %s", e)
            raise


# ── Mock provider (no API key needed) ────────────────────────────────────────

MOCK_FORMULATION = {
    "formulation": {
        "name": "Standard Liquid Detergent",
        "product_category": "liquid_detergent",
        "version": "standard",
        "description": "General-purpose liquid detergent for household use",
        "ingredients": [
            {"ingredient_name": "Sodium Lauryl Ether Sulfate (SLES 70%)", "inci_name": "Sodium Laureth Sulfate", "cas_number": "68585-34-2", "percentage": 12.0, "function": "Primary anionic surfactant – foaming and cleaning", "supplier_examples": ["BASF", "Stepan", "Evonik"], "approx_cost_per_kg_usd": 1.20},
            {"ingredient_name": "Cocamidopropyl Betaine (CAPB 30%)", "inci_name": "Cocamidopropyl Betaine", "cas_number": "61789-40-0", "percentage": 4.0, "function": "Amphoteric co-surfactant – mildness and foam stabilizer", "supplier_examples": ["Evonik", "Solvay"], "approx_cost_per_kg_usd": 1.80},
            {"ingredient_name": "Sodium Chloride", "inci_name": "Sodium Chloride", "cas_number": "7647-14-5", "percentage": 1.5, "function": "Viscosity builder", "supplier_examples": ["Local salt suppliers"], "approx_cost_per_kg_usd": 0.10},
            {"ingredient_name": "Citric Acid", "inci_name": "Citric Acid", "cas_number": "77-92-9", "percentage": 0.3, "function": "pH adjuster (target pH 6.5–7.5)", "supplier_examples": ["Jungbunzlauer", "Cargill"], "approx_cost_per_kg_usd": 0.90},
            {"ingredient_name": "Methylchloroisothiazolinone / Methylisothiazolinone (CMIT/MIT 1.5%)", "inci_name": "Methylchloroisothiazolinone, Methylisothiazolinone", "cas_number": "55965-84-9", "percentage": 0.05, "function": "Broad-spectrum preservative system", "supplier_examples": ["Dow Chemical", "Thor"], "approx_cost_per_kg_usd": 8.00},
            {"ingredient_name": "Fragrance (Lemon Fresh)", "inci_name": "Parfum", "cas_number": "N/A", "percentage": 0.5, "function": "Sensory – masking and consumer appeal", "supplier_examples": ["IFF", "Givaudan", "Firmenich"], "approx_cost_per_kg_usd": 4.00},
            {"ingredient_name": "FD&C Yellow #5 (Tartrazine) 1% solution", "inci_name": "CI 19140", "cas_number": "1934-21-0", "percentage": 0.1, "function": "Colorant – visual appeal", "supplier_examples": ["Sensient"], "approx_cost_per_kg_usd": 2.00},
            {"ingredient_name": "Purified Water (DI/RO)", "inci_name": "Aqua", "cas_number": "7732-18-5", "percentage": 81.55, "function": "Solvent / carrier", "supplier_examples": ["In-house production"], "approx_cost_per_kg_usd": 0.002},
        ],
        "process_instructions": [
            "1. Fill mixing vessel with 60% of required water at 25–30°C.",
            "2. Under moderate agitation (100–150 rpm), slowly add SLES 70%. Avoid aeration.",
            "3. Add CAPB and mix for 5 minutes until homogeneous.",
            "4. Dissolve sodium chloride in remaining water separately, then add to batch.",
            "5. Add fragrance and colorant. Mix for 3 minutes.",
            "6. Adjust pH to 6.5–7.5 using citric acid solution (pre-dissolved 10% w/v).",
            "7. When pH is stable, add preservative (CMIT/MIT). Mix 5 minutes.",
            "8. Check viscosity (target: 200–400 cP at 25°C). Adjust with NaCl if needed.",
            "9. Final QC: pH, viscosity, appearance, foam test.",
            "10. Fill and seal. Label with batch number and production date."
        ],
        "processing_temperature": "25–30°C (ambient)",
        "mixing_speed": "100–150 rpm (moderate)",
        "estimated_ph": "6.5–7.5",
        "estimated_viscosity_cP": "200–400",
        "cost_breakdown": {
            "raw_materials_per_kg_usd": 0.38,
            "packaging_estimate_per_unit_usd": 0.15,
            "labor_overhead_per_kg_usd": 0.08,
            "total_cogs_per_kg_usd": 0.61
        },
        "performance_profile": {
            "cleaning_efficiency": "Good (7.5/10)",
            "foam_level": "High",
            "rinse_ability": "Good",
            "stability": "12–18 months at 15–30°C",
            "biodegradability": "Moderate (SLES is readily biodegradable)",
            "skin_mildness": "Moderate",
            "antibacterial": "No – for antibacterial claim, add Benzalkonium Chloride 0.1%"
        },
        "alternatives": {
            "low_cost": {
                "name": "Economy Liquid Detergent",
                "key_changes": "Reduce CAPB to 2%, increase SLES to 14%, remove fragrance → estimated cost $0.28/kg",
                "trade_offs": "Lower foam stability, less skin-mild, no fragrance"
            },
            "premium": {
                "name": "Premium Concentrated Detergent",
                "key_changes": "Add 2% Sodium Lauroyl Sarcosinate, 1% glycerin, use ISO-certified fragrance → estimated cost $0.95/kg",
                "trade_offs": "Better skin feel, enhanced cleaning, higher margin potential"
            },
            "eco": {
                "name": "Bio-Based Eco Detergent",
                "key_changes": "Replace SLES with Coco Glucoside (6%), use COSMOS-approved preservative, add pH-balancing lactic acid → estimated cost $0.72/kg",
                "trade_offs": "Lower foam, shorter shelf life, premium price justified by eco-certification"
            }
        },
        "safety_notes": [
            "SLES may cause mild eye irritation – include eye-wash station in production area.",
            "CMIT/MIT is a sensitizer at high concentrations; keep below 0.0015% active.",
            "Store in HDPE containers; avoid aluminum contact.",
            "Follow local GHS/SDS regulations for labeling."
        ],
        "regulatory_notes": "Compliant with EU Detergents Regulation EC 648/2004. SLES biodegradability ≥90%.",
        "shelf_life": "18–24 months sealed; 6 months after opening"
    }
}

MOCK_PREDICTION = {
    "predictions": [
        {"type": "sales_forecast", "subject": "All Products", "period": "next_30_days", "forecast_value": 2850000, "unit": "KES", "confidence": 0.78, "trend": "up", "trend_pct": 8.5, "risk_level": "low", "summary": "Sales expected to increase 8.5% driven by seasonal demand. Top performer: Liquid Detergent 1L."},
        {"type": "stock_depletion", "subject": "Raw Materials", "period": "next_14_days", "risk_level": "high", "confidence": 0.85, "summary": "3 materials at critical reorder level. SLES 70% will deplete in 8 days at current production rate.", "items_at_risk": ["SLES 70%", "Cocamidopropyl Betaine", "Fragrance FG-0012"]},
        {"type": "demand_prediction", "subject": "Detergent SKUs", "period": "next_30_days", "forecast_value": 45000, "unit": "units", "confidence": 0.72, "trend": "up", "summary": "Demand uptick expected. Recommend increasing production order by 15%."},
        {"type": "cost_trend", "subject": "Raw Material Costs", "period": "next_90_days", "trend": "up", "trend_pct": 4.2, "risk_level": "medium", "confidence": 0.65, "summary": "Petrochemical-derived surfactant costs trending up 4.2% QoQ. Consider forward contracts for SLES."},
        {"type": "supplier_risk", "subject": "Supplier Portfolio", "risk_level": "medium", "confidence": 0.70, "summary": "2 suppliers have single-source risk for critical materials. Recommend qualifying backup suppliers."}
    ],
    "generated_at": "2026-04-10",
    "data_freshness": "Based on last 90 days of ERP data"
}

MOCK_RECOMMENDATION = {
    "recommendations": [
        {"category": "pricing", "title": "Increase Liquid Detergent 1L price by 5%", "reason": "Current gross margin of 32% is below industry benchmark of 38%. Raw material cost increase absorbed; price adjustment justified.", "expected_impact": "Estimated KES 85,000 additional monthly margin", "confidence_level": "high", "priority": "high"},
        {"category": "stock", "title": "Emergency reorder SLES 70% – 500kg", "reason": "Current stock 120kg; 8-day depletion at current rate. Lead time 5 days.", "expected_impact": "Prevent 3-day production stoppage worth KES 180,000", "confidence_level": "high", "priority": "critical"},
        {"category": "supplier", "title": "Qualify alternative supplier for Cocamidopropyl Betaine", "reason": "Single-source dependency on current supplier creates supply risk. 2 alternative suppliers identified.", "expected_impact": "Reduce supply disruption risk by 70%", "confidence_level": "medium", "priority": "medium"},
        {"category": "production", "title": "Schedule additional production run this week", "reason": "Sales forecast +8.5% next month. Current finished goods stock: 12 days. Target: 21 days.", "expected_impact": "Meet forecast demand without stockout", "confidence_level": "high", "priority": "high"},
        {"category": "margin", "title": "Reformulate Economy Line to reduce CAPB from 4% to 2%", "reason": "Economy SKU margin is 18%. Reducing CAPB saves KES 0.08/unit. Quality impact minimal for economy segment.", "expected_impact": "Improve economy line margin from 18% to 24%", "confidence_level": "medium", "priority": "medium"}
    ],
    "generated_at": "2026-04-10"
}

MOCK_SCENARIO = {
    "scenario": {
        "title": "Price increase simulation",
        "type": "price_change",
        "parameters": {"product": "Liquid Detergent 1L", "price_change_pct": 10},
        "expected_impact": {
            "revenue_change_pct": 6.5,
            "volume_change_pct": -3.5,
            "margin_change_pct": 12.8,
            "break_even_months": 1.2
        },
        "risks": [
            "Customer churn risk estimated at 8–12% if competitors don't follow",
            "Distributor resistance likely if margin not shared (recommend 2% distributor incentive)",
            "Potential for private-label switching in price-sensitive segment"
        ],
        "opportunities": [
            "Net revenue increase of KES 120,000/month if elasticity is -0.35 (historical avg)",
            "Signals premium repositioning opportunity",
            "Funds further R&D investment in eco formulation"
        ],
        "recommendation": "Proceed with 7–8% increase (not 10%) to minimize volume impact while capturing margin"
    }
}


class MockProvider(BaseAIProvider):
    """Returns deterministic mock responses. No API key required."""

    async def generate_text(self, prompt: str, system: Optional[str] = None) -> AIResponse:
        prompt_lower = prompt.lower()
        if "formulation" in prompt_lower or "formula" in prompt_lower or "ingredient" in prompt_lower:
            text = json.dumps(MOCK_FORMULATION)
        elif "predict" in prompt_lower or "forecast" in prompt_lower:
            text = json.dumps(MOCK_PREDICTION)
        elif "recommend" in prompt_lower or "suggestion" in prompt_lower:
            text = json.dumps(MOCK_RECOMMENDATION)
        elif "scenario" in prompt_lower or "simulate" in prompt_lower:
            text = json.dumps(MOCK_SCENARIO)
        else:
            text = json.dumps({"result": "Mock AI response", "status": "ok"})
        return AIResponse(text=text, provider="mock", model="mock-v1",
                          prompt_tokens=100, completion_tokens=500, latency_ms=50)


# ── Factory ───────────────────────────────────────────────────────────────────

_instance: Optional[BaseAIProvider] = None


def get_ai_provider() -> BaseAIProvider:
    global _instance
    if _instance is None:
        provider = settings.AI_PROVIDER.lower()
        if provider == "anthropic":
            if not settings.ANTHROPIC_API_KEY:
                log.warning("ANTHROPIC_API_KEY not set — falling back to mock provider")
                _instance = MockProvider()
            else:
                _instance = AnthropicProvider()
        elif provider == "openai":
            if not settings.OPENAI_API_KEY:
                log.warning("OPENAI_API_KEY not set — falling back to mock provider")
                _instance = MockProvider()
            else:
                _instance = OpenAIProvider()
        else:
            _instance = MockProvider()
    return _instance


def reset_provider():
    """Force re-instantiation (useful after config changes)."""
    global _instance
    _instance = None
