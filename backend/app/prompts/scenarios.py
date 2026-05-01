"""Scenario simulation prompt template."""
from __future__ import annotations
import json

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


def build_scenario_prompt(erp_ctx: dict, description: str, parameters: dict) -> str:
    return f"""Simulate this business scenario for an FMCG company:

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
