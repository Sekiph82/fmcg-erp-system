"""Formulation generation prompt template."""
from __future__ import annotations

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


def build_formulation_prompt(
    product_category: str,
    props_str: str,
    performance_priority: str,
    cost_str: str,
    erp_mat_str: str,
) -> str:
    return f"""You are a senior formulation chemist specializing in FMCG products.
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
