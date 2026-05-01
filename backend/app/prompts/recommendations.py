"""Recommendation prompt template."""
from __future__ import annotations
import json

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


def build_recommendation_prompt(erp_ctx: dict, focus_str: str) -> str:
    return f"""Based on this FMCG ERP data, generate specific, actionable recommendations.
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
