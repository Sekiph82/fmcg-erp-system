"""
Prompt template for optional LLM enhancement of rule-based module AI recommendations.
Used when AI_ENABLE_MODULE_LLM_ENHANCEMENT=True.
"""
from __future__ import annotations
import json

MODULE_ENHANCEMENT_SCHEMA = """{
  "llm_explanation": "Plain English explanation of why this recommendation matters",
  "priority_reason": "Why this should be acted on before other items",
  "suggested_next_steps": ["concrete step 1", "step 2", "step 3"],
  "business_risk_if_ignored": "What happens if ignored for 1 week",
  "estimated_effort": "low | medium | high",
  "mode": "HYBRID"
}"""


def build_enhancement_prompt(
    module_name: str,
    recommendation: dict,
    safe_context: dict,
) -> str:
    return f"""You are an ERP business advisor reviewing a rule-based system recommendation.

Module: {module_name}
Recommendation from rule engine:
{json.dumps(recommendation, indent=2)}

Current ERP context summary:
{json.dumps(safe_context, indent=2)}

TASK:
1. Explain this recommendation in plain English a non-technical manager can understand.
2. Justify the priority level in concrete business terms.
3. Provide 2-3 actionable next steps.
4. Describe the business risk if ignored for one week.
5. Estimate implementation effort.

RULES (non-negotiable):
- Do NOT change the numeric values or calculations from the rule engine.
- Do NOT override the rule engine's pass/fail decision.
- Do NOT recommend executing ERP transactions directly.
- Focus purely on explanation, prioritization, and communication.

Output schema:
{MODULE_ENHANCEMENT_SCHEMA}"""
