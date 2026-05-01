"""Prediction prompt template."""
from __future__ import annotations
import json

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


def build_prediction_prompt(erp_ctx: dict, types_str: str) -> str:
    return f"""Analyze this FMCG ERP data and generate predictions for: {types_str}

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
