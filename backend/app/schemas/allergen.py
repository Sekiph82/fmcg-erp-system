"""Allergen + Nutrition Management — Pydantic v2 schemas."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── Allergen Master ───────────────────────────────────────────────────────────

class AllergenMasterCreate(_Base):
    allergen_code: str
    allergen_name: str
    regulatory_name: Optional[str] = None
    category: str = "MAJOR"
    sort_order: int = 0
    notes: Optional[str] = None


class AllergenMasterUpdate(_Base):
    allergen_name: Optional[str] = None
    regulatory_name: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    notes: Optional[str] = None


class AllergenMasterOut(_Base):
    id: uuid.UUID
    allergen_code: str
    allergen_name: str
    regulatory_name: Optional[str]
    category: str
    is_active: bool
    sort_order: int
    notes: Optional[str]
    created_at: datetime


# ── Material Allergen Profile ─────────────────────────────────────────────────

class MaterialAllergenLineCreate(_Base):
    allergen_id: uuid.UUID
    presence_type: str = "CONTAINS"
    concentration_note: Optional[str] = None
    declaration_required: bool = True
    critical_flag: bool = False
    notes: Optional[str] = None


class MaterialAllergenLineOut(_Base):
    id: uuid.UUID
    allergen_id: uuid.UUID
    presence_type: str
    concentration_note: Optional[str]
    declaration_required: bool
    critical_flag: bool
    notes: Optional[str]
    allergen_code: Optional[str] = None
    allergen_name: Optional[str] = None
    created_at: datetime


class MaterialAllergenProfileCreate(_Base):
    material_id: uuid.UUID
    cross_contact_risk_level: str = "NONE"
    supplier_allergen_statement_ref: Optional[str] = None
    allergen_review_date: Optional[date] = None
    approved_by: Optional[str] = None
    notes: Optional[str] = None
    lines: List[MaterialAllergenLineCreate] = []


class MaterialAllergenProfileUpdate(_Base):
    cross_contact_risk_level: Optional[str] = None
    supplier_allergen_statement_ref: Optional[str] = None
    allergen_review_date: Optional[date] = None
    approved_by: Optional[str] = None
    notes: Optional[str] = None


class MaterialAllergenProfileOut(_Base):
    id: uuid.UUID
    material_id: uuid.UUID
    allergen_present_flag: bool
    allergen_may_contain_flag: bool
    cross_contact_risk_level: str
    supplier_allergen_statement_ref: Optional[str]
    allergen_review_date: Optional[date]
    approved_by: Optional[str]
    is_active: bool
    notes: Optional[str]
    lines: List[MaterialAllergenLineOut] = []
    material_name: Optional[str] = None
    created_at: datetime


# ── Nutrition Profile ─────────────────────────────────────────────────────────

class NutritionLineCreate(_Base):
    nutrient_code: str
    nutrient_name: str
    unit: str = "g"
    value: Decimal = Decimal("0")
    source_type: str = "MANUAL"
    approved_flag: bool = False
    review_date: Optional[date] = None
    notes: Optional[str] = None


class NutritionLineUpdate(_Base):
    value: Optional[Decimal] = None
    source_type: Optional[str] = None
    approved_flag: Optional[bool] = None
    review_date: Optional[date] = None
    notes: Optional[str] = None


class NutritionLineOut(_Base):
    id: uuid.UUID
    nutrient_code: str
    nutrient_name: str
    unit: str
    value: Decimal
    source_type: str
    approved_flag: bool
    review_date: Optional[date]
    notes: Optional[str]
    created_at: datetime


class NutritionProfileCreate(_Base):
    material_id: Optional[uuid.UUID] = None
    product_id: Optional[uuid.UUID] = None
    basis_type: str = "PER_100G"
    density_factor: Optional[Decimal] = None
    moisture_factor: Optional[Decimal] = None
    notes: Optional[str] = None
    lines: List[NutritionLineCreate] = []


class NutritionProfileOut(_Base):
    id: uuid.UUID
    material_id: Optional[uuid.UUID]
    product_id: Optional[uuid.UUID]
    basis_type: str
    density_factor: Optional[Decimal]
    moisture_factor: Optional[Decimal]
    is_active: bool
    notes: Optional[str]
    lines: List[NutritionLineOut] = []
    entity_name: Optional[str] = None
    created_at: datetime


# ── Roll-Up Results ───────────────────────────────────────────────────────────

class AllergenRollupLine(_Base):
    allergen_code: str
    allergen_name: str
    presence_type: str
    declaration_required: bool
    critical_flag: bool
    source_materials: List[str] = []


class AllergenRollupResult(_Base):
    product_id: Optional[uuid.UUID]
    bom_id: Optional[uuid.UUID]
    bom_version: Optional[str]
    contains: List[AllergenRollupLine] = []
    may_contain: List[AllergenRollupLine] = []
    free_from: List[str] = []
    declaration_required: List[AllergenRollupLine] = []
    cross_contact_risk: str
    label_statement: str
    may_contain_statement: str
    ingredient_allergen_map: Dict[str, List[str]] = {}


class NutritionRollupLine(_Base):
    nutrient_code: str
    nutrient_name: str
    unit: str
    value_per_100g: Decimal
    value_per_100ml: Optional[Decimal] = None
    value_per_serving: Optional[Decimal] = None
    value_per_unit: Optional[Decimal] = None


class NutritionRollupResult(_Base):
    product_id: Optional[uuid.UUID]
    bom_id: Optional[uuid.UUID]
    bom_version: Optional[str]
    serving_size_g: Optional[Decimal]
    servings_per_pack: Optional[Decimal]
    nutrients: List[NutritionRollupLine] = []
    per_100g: Dict[str, Any] = {}
    per_serving: Dict[str, Any] = {}
    per_unit: Dict[str, Any] = {}
    completeness_pct: Decimal = Decimal("0")
    missing_profiles: List[str] = []


# ── Product Summary Outputs ───────────────────────────────────────────────────

class ProductAllergenSummaryOut(_Base):
    id: uuid.UUID
    product_id: uuid.UUID
    bom_id: Optional[uuid.UUID]
    bom_version: Optional[str]
    contains_allergens: Optional[List[str]]
    may_contain_allergens: Optional[List[str]]
    declaration_required: Optional[List[Dict]]
    cross_contact_risk: Optional[str]
    label_statement: Optional[str]
    may_contain_statement: Optional[str]
    last_calculated_at: Optional[datetime]
    calculation_source: Optional[str]
    is_stale: bool
    product_name: Optional[str] = None
    created_at: datetime


class ProductNutritionSummaryOut(_Base):
    id: uuid.UUID
    product_id: uuid.UUID
    bom_id: Optional[uuid.UUID]
    bom_version: Optional[str]
    serving_size_value: Optional[Decimal]
    serving_size_uom: Optional[str]
    servings_per_pack: Optional[Decimal]
    label_basis_type: str
    nutrition_per_100g: Optional[Dict[str, Any]]
    nutrition_per_100ml: Optional[Dict[str, Any]]
    nutrition_per_serving: Optional[Dict[str, Any]]
    nutrition_per_unit: Optional[Dict[str, Any]]
    last_calculated_at: Optional[datetime]
    calculation_source: Optional[str]
    is_stale: bool
    product_name: Optional[str] = None
    created_at: datetime


# ── Allergen Change Log ───────────────────────────────────────────────────────

class AllergenChangeLogOut(_Base):
    id: uuid.UUID
    product_id: Optional[uuid.UUID]
    bom_id: Optional[uuid.UUID]
    bom_version_from: Optional[str]
    bom_version_to: Optional[str]
    allergen_id: Optional[uuid.UUID]
    change_type: str
    old_value: Optional[str]
    new_value: Optional[str]
    detected_at: Optional[datetime]
    requires_label_review: bool
    requires_qc_review: bool
    requires_haccp_review: bool
    requires_cleaning_validation: bool
    label_review_done: bool
    qc_review_done: bool
    notes: Optional[str]
    allergen_name: Optional[str] = None
    product_name: Optional[str] = None
    created_at: datetime


# ── Serving Config ────────────────────────────────────────────────────────────

class ServingConfigCreate(_Base):
    product_id: uuid.UUID
    serving_size_value: Optional[Decimal] = None
    serving_size_uom: Optional[str] = "g"
    servings_per_pack: Optional[Decimal] = None
    label_basis_type: str = "PER_100G"
    market_profile: Optional[str] = None
    notes: Optional[str] = None


class ServingConfigOut(_Base):
    id: uuid.UUID
    product_id: uuid.UUID
    serving_size_value: Optional[Decimal]
    serving_size_uom: Optional[str]
    servings_per_pack: Optional[Decimal]
    label_basis_type: str
    market_profile: Optional[str]
    notes: Optional[str]
    created_at: datetime


# ── Label Readiness ───────────────────────────────────────────────────────────

class LabelReadinessOut(_Base):
    product_id: uuid.UUID
    product_name: str
    allergen_summary_complete: bool
    allergen_summary_stale: bool
    nutrition_summary_complete: bool
    nutrition_summary_stale: bool
    serving_config_present: bool
    open_change_logs: int
    pending_label_reviews: int
    pending_qc_reviews: int
    readiness_score: int
    warnings: List[str]
    last_checked: datetime


# ── BOM Version Comparison ────────────────────────────────────────────────────

class BOMAllergenComparisonOut(_Base):
    bom_id_a: uuid.UUID
    bom_id_b: uuid.UUID
    version_a: str
    version_b: str
    added_allergens: List[str]
    removed_allergens: List[str]
    changed_presence: List[Dict]
    declaration_changes: List[Dict]
    is_identical: bool


class BOMNutritionComparisonOut(_Base):
    bom_id_a: uuid.UUID
    bom_id_b: uuid.UUID
    version_a: str
    version_b: str
    changed_nutrients: List[Dict]
    is_significant_change: bool
    significance_threshold_pct: Decimal


# ── AI Recommendations ────────────────────────────────────────────────────────

class ANAIRecOut(_Base):
    id: uuid.UUID
    agent_type: str
    title: str
    description: str
    affected_entity_type: Optional[str]
    affected_entity_id: Optional[str]
    recommendation: str
    severity: str
    status: str
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    agent_metadata: Optional[Dict]
    created_at: datetime


class ANAIRecReview(_Base):
    status: str
    reviewed_by: Optional[str] = None


# ── Dashboard ─────────────────────────────────────────────────────────────────

class ANDashboardOut(_Base):
    total_allergens: int
    materials_with_allergen_profiles: int
    materials_missing_profiles: int
    products_with_allergen_summaries: int
    products_with_nutrition_summaries: int
    stale_allergen_summaries: int
    stale_nutrition_summaries: int
    open_change_logs: int
    pending_label_reviews: int
    ai_pending: int
    high_risk_cross_contact: int
