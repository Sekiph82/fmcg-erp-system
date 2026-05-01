"""
Optional LLM enhancement layer for rule-based module AI recommendations.

Disabled by default (AI_ENABLE_MODULE_LLM_ENHANCEMENT=False in config).
When enabled, enriches rule-based recommendations with LLM-generated explanation,
priority justification, and next steps.

IMPORTANT — what this layer does NOT do:
  - Does NOT change numeric calculations from rule engines.
  - Does NOT override rule-based pass/fail decisions.
  - Does NOT execute ERP transactions.
  - Is purely additive: explanation, summarization, prioritization.

Usage:
    from app.services.module_ai_llm_enhancer import enhance_recommendation
    enriched = await enhance_recommendation("crm", rec_dict, masked_ctx, user_id, db)
"""
from __future__ import annotations

import logging
from typing import Any, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.ai_safety import mask_sensitive_context

log = logging.getLogger(__name__)


async def enhance_recommendation(
    module_name: str,
    recommendation: dict[str, Any],
    context: dict[str, Any],
    user_id: Optional[uuid.UUID],
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Optionally enrich a rule-based recommendation with LLM explanation.

    Returns the original recommendation dict with added keys:
      mode, llm_explanation, priority_reason, suggested_next_steps,
      business_risk_if_ignored, estimated_effort.

    If enhancement disabled or LLM call fails, returns original + mode="rule_based".
    """
    if not settings.AI_ENABLE_MODULE_LLM_ENHANCEMENT:
        return {**recommendation, "mode": "rule_based", "llm_explanation": None}

    try:
        from app.services.ai_provider import get_ai_provider
        from app.prompts.module_enhancement import build_enhancement_prompt
        from app.prompts.central_ai import SYSTEM_PROMPT_FMCG
        from app.core.ai_safety import build_safe_system_prompt

        safe_ctx = mask_sensitive_context(context)
        prompt = build_enhancement_prompt(module_name, recommendation, safe_ctx)
        safe_system = build_safe_system_prompt(SYSTEM_PROMPT_FMCG)

        provider = get_ai_provider()
        obj, _ = await provider.generate_structured_output(prompt, system=safe_system)

        return {
            **recommendation,
            "mode": "hybrid",
            "llm_explanation": obj.get("llm_explanation"),
            "priority_reason": obj.get("priority_reason"),
            "suggested_next_steps": obj.get("suggested_next_steps", []),
            "business_risk_if_ignored": obj.get("business_risk_if_ignored"),
            "estimated_effort": obj.get("estimated_effort"),
        }

    except Exception as exc:
        log.warning(
            "LLM enhancement failed for module=%s: %s — returning rule_based result.",
            module_name, exc,
        )
        return {**recommendation, "mode": "rule_based", "llm_explanation": None}
