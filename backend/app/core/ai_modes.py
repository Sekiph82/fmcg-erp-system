"""
AI mode classification constants.

Three tiers in this ERP:
  LLM_POWERED  — calls external LLM (Anthropic / OpenAI / Gemini)
  RULE_BASED   — deterministic heuristic engine, no external API
  STATISTICAL  — statistical / moving-average engine, no external API
  HYBRID       — rule-based core + optional LLM explanation layer
"""
from __future__ import annotations


class AIMode:
    LLM_POWERED = "llm_powered"
    RULE_BASED = "rule_based"
    STATISTICAL = "statistical"
    HYBRID = "hybrid"


MODULE_AI_MODES: dict[str, str] = {
    # Central hub — real LLM
    "predictions": AIMode.LLM_POWERED,
    "recommendations": AIMode.LLM_POWERED,
    "scenarios": AIMode.LLM_POWERED,
    "formulations": AIMode.LLM_POWERED,
    "chat": AIMode.LLM_POWERED,
    # Statistical production engines
    "production": AIMode.STATISTICAL,
    "mps": AIMode.STATISTICAL,
    "planning": AIMode.STATISTICAL,
    "bom": AIMode.STATISTICAL,
    "shop_floor": AIMode.STATISTICAL,
    # Rule-based module AI (connected, deterministic)
    "procurement_suggestion": AIMode.RULE_BASED,
    "subcontracting": AIMode.RULE_BASED,
    "landed_cost": AIMode.RULE_BASED,
    "invoice_match": AIMode.RULE_BASED,
    "bank_reconciliation": AIMode.RULE_BASED,
    "fixed_assets": AIMode.RULE_BASED,
    "crm": AIMode.RULE_BASED,
    "van_sales": AIMode.RULE_BASED,
    "dunning": AIMode.RULE_BASED,
    "price_lists": AIMode.RULE_BASED,
    "recurring_orders": AIMode.RULE_BASED,
    "commissions": AIMode.RULE_BASED,
    "contracts": AIMode.RULE_BASED,
    "portal": AIMode.RULE_BASED,
    "supplier_portal": AIMode.RULE_BASED,
    "expenses": AIMode.RULE_BASED,
    "recruitment": AIMode.RULE_BASED,
    "ess": AIMode.RULE_BASED,
    "appraisals": AIMode.RULE_BASED,
    "training": AIMode.RULE_BASED,
    "timesheets": AIMode.RULE_BASED,
    "notifications": AIMode.RULE_BASED,
    "kanban": AIMode.RULE_BASED,
    "report_builder": AIMode.RULE_BASED,
    "calendar": AIMode.RULE_BASED,
    "chatter": AIMode.RULE_BASED,
    "custom_fields": AIMode.RULE_BASED,
    "allergen": AIMode.RULE_BASED,
    "qms": AIMode.RULE_BASED,
    "gs1": AIMode.RULE_BASED,
    "tpm": AIMode.RULE_BASED,
    "promotions": AIMode.RULE_BASED,
    "dimensions": AIMode.RULE_BASED,
    "fleet": AIMode.RULE_BASED,
    "cycle_count": AIMode.RULE_BASED,
    "fraud": AIMode.RULE_BASED,
    "rider_performance": AIMode.RULE_BASED,
    "esg": AIMode.RULE_BASED,
    "secondary_sales": AIMode.RULE_BASED,
    "payroll_ke": AIMode.RULE_BASED,
    "webhooks": AIMode.RULE_BASED,
}

MODE_LABELS: dict[str, str] = {
    AIMode.LLM_POWERED: "LLM-Powered",
    AIMode.RULE_BASED: "Rule-Based",
    AIMode.STATISTICAL: "Statistical",
    AIMode.HYBRID: "Hybrid",
}

MODE_DESCRIPTIONS: dict[str, str] = {
    AIMode.LLM_POWERED: "Uses external LLM (Anthropic/OpenAI/Gemini) for reasoning and generation.",
    AIMode.RULE_BASED: "Deterministic heuristic engine. Fast, predictable, no external API cost.",
    AIMode.STATISTICAL: "Statistical engine using historical ERP data patterns. No external API.",
    AIMode.HYBRID: "Rule-based core with optional LLM enhancement for explanation and summarization.",
}
