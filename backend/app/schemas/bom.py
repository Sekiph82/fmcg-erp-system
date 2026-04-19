"""Pydantic schemas for Advanced Multi-Level BOM / Formula / Packaging BOM."""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.bom import (
    BOMType, BOMLifecycle, ComponentType, BasisType,
    SubstitutionPolicy, ItemLinkType, LossCategory,
    BOMAgentType, BOMRecStatus,
)


# ── AdvancedBOM ────────────────────────────────────────────────────────────────

class BOMCreate(BaseModel):
    bom_name: str
    bom_type: BOMType = BOMType.FORMULA
    product_id: Optional[UUID] = None
    base_qty: Decimal = Decimal("1000")
    base_uom: str = "KG"
    version_no: str = "1.0"
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    notes: Optional[str] = None

class BOMUpdate(BaseModel):
    bom_name: Optional[str] = None
    bom_type: Optional[BOMType] = None
    base_qty: Optional[Decimal] = None
    base_uom: Optional[str] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    linked_routing_id: Optional[UUID] = None
    linked_quality_spec_id: Optional[UUID] = None
    notes: Optional[str] = None

class BOMSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    bom_code: str
    bom_name: str
    bom_type: BOMType
    product_id: Optional[UUID]
    product_name: Optional[str]
    base_qty: Decimal
    base_uom: str
    version_no: str
    lifecycle: BOMLifecycle
    is_default: bool
    effective_from: Optional[date]
    effective_to: Optional[date]
    standard_batch_cost: Optional[Decimal]
    created_at: datetime

class BOMOut(BOMSummary):
    revision_no: str
    created_by_id: Optional[UUID]
    reviewed_by_id: Optional[UUID]
    approved_by_id: Optional[UUID]
    released_by_id: Optional[UUID]
    linked_routing_id: Optional[UUID]
    linked_quality_spec_id: Optional[UUID]
    linked_label_profile_id: Optional[UUID]
    linked_compliance_profile_id: Optional[UUID]
    standard_cost_per_uom: Optional[Decimal]
    total_raw_cost: Optional[Decimal]
    total_packaging_cost: Optional[Decimal]
    by_product_credit: Optional[Decimal]
    costing_updated_at: Optional[datetime]
    allergen_flags: Optional[Dict[str, bool]]
    nutrition_per_100g: Optional[Dict[str, float]]
    notes: Optional[str]
    lines: List[BOMLineOut] = []
    yield_configs: List[YieldConfigOut] = []


# ── AdvancedBOMLine ────────────────────────────────────────────────────────────

class BOMLineCreate(BaseModel):
    line_no: int
    component_type: ComponentType = ComponentType.RAW
    item_type: ItemLinkType = ItemLinkType.MATERIAL
    item_id: Optional[UUID] = None
    item_name: Optional[str] = None
    item_code: Optional[str] = None
    child_bom_id: Optional[UUID] = None
    required_qty: Decimal
    required_uom: str = "KG"
    basis_type: BasisType = BasisType.PER_BATCH
    concentration_pct: Optional[Decimal] = None
    wastage_pct: Decimal = Decimal("0")
    process_loss_pct: Decimal = Decimal("0")
    yield_contribution_pct: Optional[Decimal] = None
    fixed_consumption: bool = False
    is_optional: bool = False
    qc_required: bool = False
    allergen_flag: bool = False
    nutrition_relevant: bool = False
    critical_component: bool = False
    substitute_group_id: Optional[UUID] = None
    substitution_policy: SubstitutionPolicy = SubstitutionPolicy.NO_SUB
    consumption_stage: Optional[str] = None
    issue_stage: Optional[str] = None
    allergen_types: Optional[List[str]] = None
    traceability_level: Optional[str] = None
    nutrition_data: Optional[Dict[str, float]] = None
    notes: Optional[str] = None

class BOMLineUpdate(BaseModel):
    component_type: Optional[ComponentType] = None
    required_qty: Optional[Decimal] = None
    required_uom: Optional[str] = None
    basis_type: Optional[BasisType] = None
    wastage_pct: Optional[Decimal] = None
    process_loss_pct: Optional[Decimal] = None
    fixed_consumption: Optional[bool] = None
    is_optional: Optional[bool] = None
    allergen_flag: Optional[bool] = None
    allergen_types: Optional[List[str]] = None
    substitution_policy: Optional[SubstitutionPolicy] = None
    substitute_group_id: Optional[UUID] = None
    consumption_stage: Optional[str] = None
    notes: Optional[str] = None

class BOMLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    bom_id: UUID
    line_no: int
    component_type: ComponentType
    item_type: ItemLinkType
    item_id: Optional[UUID]
    item_name: Optional[str]
    item_code: Optional[str]
    child_bom_id: Optional[UUID]
    required_qty: Decimal
    required_uom: str
    basis_type: BasisType
    concentration_pct: Optional[Decimal]
    wastage_pct: Decimal
    process_loss_pct: Decimal
    yield_contribution_pct: Optional[Decimal]
    fixed_consumption: bool
    is_optional: bool
    qc_required: bool
    allergen_flag: bool
    nutrition_relevant: bool
    critical_component: bool
    substitute_group_id: Optional[UUID]
    substitution_policy: SubstitutionPolicy
    consumption_stage: Optional[str]
    issue_stage: Optional[str]
    allergen_types: Optional[List[str]]
    traceability_level: Optional[str]
    nutrition_data: Optional[Dict[str, float]]
    unit_cost: Optional[Decimal]
    extended_cost: Optional[Decimal]
    notes: Optional[str]


# ── Substitute Group ───────────────────────────────────────────────────────────

class SubstGroupCreate(BaseModel):
    group_name: str
    policy: SubstitutionPolicy = SubstitutionPolicy.PLANNER_APPROVAL
    notes: Optional[str] = None

class SubstGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    group_code: str
    group_name: str
    policy: SubstitutionPolicy
    notes: Optional[str]
    is_active: bool
    substitutes: List[SubstituteOut] = []

class SubstituteCreate(BaseModel):
    group_id: UUID
    item_type: ItemLinkType = ItemLinkType.MATERIAL
    item_id: Optional[UUID] = None
    item_name: Optional[str] = None
    item_code: Optional[str] = None
    priority: int = 1
    qty_ratio: Decimal = Decimal("1.0")
    cost_impact_pct: Optional[Decimal] = None
    quality_impact: Optional[str] = None
    allergen_impact: Optional[str] = None
    notes: Optional[str] = None

class SubstituteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    group_id: UUID
    item_type: ItemLinkType
    item_id: Optional[UUID]
    item_name: Optional[str]
    item_code: Optional[str]
    priority: int
    qty_ratio: Decimal
    cost_impact_pct: Optional[Decimal]
    quality_impact: Optional[str]
    allergen_impact: Optional[str]
    notes: Optional[str]
    is_active: bool


# ── Conversion Profile ─────────────────────────────────────────────────────────

class ConversionProfileCreate(BaseModel):
    profile_name: str
    source_product_id: Optional[UUID] = None
    source_product_name: Optional[str] = None
    target_product_id: Optional[UUID] = None
    target_product_name: Optional[str] = None
    theoretical_conversion_ratio: Decimal = Decimal("1.0")
    standard_fill_volume: Optional[Decimal] = None
    fill_volume_uom: Optional[str] = None
    fill_tolerance_pct: Decimal = Decimal("1.0")
    density_g_per_ml: Optional[Decimal] = None
    startup_loss_pct: Decimal = Decimal("0.5")
    shutdown_loss_pct: Decimal = Decimal("0.3")
    packaging_reject_pct: Decimal = Decimal("0.5")
    residual_bulk_pct: Decimal = Decimal("0.2")
    line_purge_loss_pct: Decimal = Decimal("0.1")
    standard_expected_units: Optional[Decimal] = None
    realistic_expected_units: Optional[Decimal] = None
    linked_packaging_bom_id: Optional[UUID] = None
    notes: Optional[str] = None

class ConversionProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    profile_code: str
    profile_name: str
    source_product_id: Optional[UUID]
    source_product_name: Optional[str]
    target_product_id: Optional[UUID]
    target_product_name: Optional[str]
    theoretical_conversion_ratio: Decimal
    standard_fill_volume: Optional[Decimal]
    fill_volume_uom: Optional[str]
    fill_tolerance_pct: Decimal
    density_g_per_ml: Optional[Decimal]
    startup_loss_pct: Decimal
    shutdown_loss_pct: Decimal
    packaging_reject_pct: Decimal
    residual_bulk_pct: Decimal
    line_purge_loss_pct: Decimal
    standard_expected_units: Optional[Decimal]
    realistic_expected_units: Optional[Decimal]
    linked_packaging_bom_id: Optional[UUID]
    is_active: bool
    notes: Optional[str]

class ConversionCalcResult(BaseModel):
    source_qty: Decimal
    source_uom: str
    theoretical_units: Decimal
    startup_loss_units: Decimal
    shutdown_loss_units: Decimal
    reject_units: Decimal
    residual_units: Decimal
    expected_good_units: Decimal
    total_loss_pct: Decimal
    fill_volume_per_unit: Optional[Decimal]
    notes: str


# ── Yield Config ───────────────────────────────────────────────────────────────

class YieldConfigCreate(BaseModel):
    loss_category: LossCategory
    description: Optional[str] = None
    basis: str = "PCT_OF_INPUT"
    standard_pct: Decimal = Decimal("0")
    max_allowable_pct: Optional[Decimal] = None
    cost_impact_flag: bool = True
    notes: Optional[str] = None

class YieldConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    bom_id: UUID
    loss_category: LossCategory
    description: Optional[str]
    basis: str
    standard_pct: Decimal
    max_allowable_pct: Optional[Decimal]
    cost_impact_flag: bool
    notes: Optional[str]


# ── Explosion ──────────────────────────────────────────────────────────────────

class ExplosionNode(BaseModel):
    level: int
    line_id: str
    bom_id: str
    bom_code: str
    parent_item_name: str
    item_name: str
    item_code: Optional[str]
    component_type: str
    required_qty: Decimal
    adjusted_qty: Decimal       # after waste/loss
    required_uom: str
    wastage_pct: Decimal
    process_loss_pct: Decimal
    basis_type: str
    consumption_stage: Optional[str]
    allergen_flag: bool
    critical_component: bool
    substitutes: List[str]      # item names of available substitutes
    children: List["ExplosionNode"] = []

ExplosionNode.model_rebuild()

class ExplosionResult(BaseModel):
    bom_id: str
    bom_code: str
    bom_name: str
    target_qty: Decimal
    target_uom: str
    total_levels: int
    nodes: List[ExplosionNode]
    flat_requirements: List[dict]  # aggregated leaf-level requirements


# ── Scaling Preview ────────────────────────────────────────────────────────────

class ScalingRequest(BaseModel):
    target_qty: Decimal
    target_uom: Optional[str] = None

class ScaledLine(BaseModel):
    line_no: int
    item_name: Optional[str]
    item_code: Optional[str]
    component_type: str
    basis_type: str
    original_qty: Decimal
    scaled_qty: Decimal
    adjusted_qty: Decimal   # after waste
    required_uom: str
    fixed_consumption: bool
    warning: Optional[str]

class ScalingResult(BaseModel):
    bom_id: str
    bom_code: str
    original_base_qty: Decimal
    target_qty: Decimal
    scale_factor: Decimal
    lines: List[ScaledLine]


# ── Costing ───────────────────────────────────────────────────────────────────

class CostingLine(BaseModel):
    line_no: int
    item_name: Optional[str]
    component_type: str
    qty: Decimal
    uom: str
    unit_cost: Optional[Decimal]
    extended_cost: Decimal
    is_by_product_credit: bool

class CostingResult(BaseModel):
    bom_id: str
    bom_code: str
    bom_name: str
    base_qty: Decimal
    base_uom: str
    raw_material_cost: Decimal
    intermediate_cost: Decimal
    packaging_cost: Decimal
    utility_cost: Decimal
    by_product_credit: Decimal
    total_batch_cost: Decimal
    cost_per_uom: Decimal
    lines: List[CostingLine]


# ── Compliance Summary ────────────────────────────────────────────────────────

class ComplianceSummary(BaseModel):
    bom_id: str
    bom_code: str
    allergen_flags: Dict[str, bool]
    cross_contact_risks: List[str]
    critical_components: List[str]
    nutrition_per_100g: Optional[Dict[str, float]]
    warnings: List[str]


# ── Version Comparison ────────────────────────────────────────────────────────

class VersionDiff(BaseModel):
    added_lines: List[BOMLineOut]
    removed_lines: List[BOMLineOut]
    changed_lines: List[dict]
    allergen_changes: List[str]
    cost_delta: Optional[Decimal]


# ── AI Recs ───────────────────────────────────────────────────────────────────

class BOMAIRecOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    bom_id: UUID
    agent_type: BOMAgentType
    status: BOMRecStatus
    title: str
    explanation: Optional[str]
    impact_summary: Optional[str]
    confidence_score: Optional[Decimal]
    payload: Optional[Any]
    actioned_at: Optional[datetime]

class BOMAIRecAction(BaseModel):
    status: BOMRecStatus


# ── Dashboard ─────────────────────────────────────────────────────────────────

class BOMDashboard(BaseModel):
    total_boms: int
    released_boms: int
    draft_boms: int
    pending_review: int
    boms_with_allergens: int
    pending_ai_recs: int
    recent_boms: List[BOMSummary]
    by_type: Dict[str, int]
    by_lifecycle: Dict[str, int]


# Forward reference resolution
BOMOut.model_rebuild()
SubstGroupOut.model_rebuild()
