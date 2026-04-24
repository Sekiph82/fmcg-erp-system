from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.shelf_life import (
    ShelfLifeStatus, PickingStrategy, ExpiryBlockPolicy, NearExpiryPolicy,
    ShelfLifeCategory, RetestStatus, DispositionAction, DispositionStatus,
    AlertType, AlertSeverity, SLAIAgentType, SLAIRecStatus, StrategyScope,
    CustomerRuleType, FEFOContext,
)


# ── Shared ────────────────────────────────────────────────────────────────────

class _Base(BaseModel):
    model_config = {"from_attributes": True}


# ── ItemShelfLifeConfig ───────────────────────────────────────────────────────

class ItemShelfLifeConfigCreate(BaseModel):
    product_id:  Optional[UUID] = None
    material_id: Optional[UUID] = None
    shelf_life_control_enabled: bool = True
    shelf_life_category:        ShelfLifeCategory = ShelfLifeCategory.raw
    shelf_life_days:            Optional[int] = None
    min_remaining_days_issue:   Optional[int] = None
    min_remaining_days_ship:    Optional[int] = None
    near_expiry_threshold_days: int = 30
    picking_strategy_default:   PickingStrategy = PickingStrategy.fefo
    expiry_block_policy:        ExpiryBlockPolicy = ExpiryBlockPolicy.block
    near_expiry_issue_policy:   NearExpiryPolicy = NearExpiryPolicy.warn
    near_expiry_ship_policy:    NearExpiryPolicy = NearExpiryPolicy.warn
    manufacturing_date_required: bool = True
    expiry_date_required:        bool = True
    retest_date_required:        bool = False
    best_before_date_required:   bool = False
    allowed_retest:              bool = False
    auto_expiry_calculation:     bool = True
    max_hold_hours:              Optional[Decimal] = None
    notes:                       Optional[str] = None

class ItemShelfLifeConfigUpdate(ItemShelfLifeConfigCreate):
    pass

class ItemShelfLifeConfigOut(_Base):
    id:          UUID
    product_id:  Optional[UUID]
    material_id: Optional[UUID]
    shelf_life_control_enabled: bool
    shelf_life_category:        ShelfLifeCategory
    shelf_life_days:            Optional[int]
    min_remaining_days_issue:   Optional[int]
    min_remaining_days_ship:    Optional[int]
    near_expiry_threshold_days: int
    picking_strategy_default:   PickingStrategy
    expiry_block_policy:        ExpiryBlockPolicy
    near_expiry_issue_policy:   NearExpiryPolicy
    near_expiry_ship_policy:    NearExpiryPolicy
    manufacturing_date_required: bool
    expiry_date_required:        bool
    retest_date_required:        bool
    best_before_date_required:   bool
    allowed_retest:              bool
    auto_expiry_calculation:     bool
    max_hold_hours:              Optional[Decimal]
    notes:                       Optional[str]
    created_at:  datetime
    updated_at:  datetime


# ── PickingStrategyConfig ─────────────────────────────────────────────────────

class PickingStrategyConfigCreate(BaseModel):
    scope:        StrategyScope
    strategy:     PickingStrategy
    product_id:   Optional[UUID] = None
    material_id:  Optional[UUID] = None
    warehouse_id: Optional[UUID] = None
    location_id:  Optional[UUID] = None
    effective_from: Optional[date] = None
    notes:        Optional[str] = None

class PickingStrategyConfigOut(_Base):
    id:           UUID
    scope:        StrategyScope
    strategy:     PickingStrategy
    is_active:    bool
    product_id:   Optional[UUID]
    material_id:  Optional[UUID]
    warehouse_id: Optional[UUID]
    location_id:  Optional[UUID]
    effective_from: Optional[date]
    notes:        Optional[str]
    created_at:   datetime


# ── CustomerShelfLifeRule ─────────────────────────────────────────────────────

class CustomerShelfLifeRuleCreate(BaseModel):
    customer_id:        Optional[UUID] = None
    customer_group:     Optional[str]  = None
    country_code:       Optional[str]  = None
    channel:            Optional[str]  = None
    product_id:         Optional[UUID] = None
    material_id:        Optional[UUID] = None
    rule_type:          CustomerRuleType = CustomerRuleType.fixed_days
    min_remaining_days: Optional[int]   = None
    min_pct_remaining:  Optional[Decimal] = None
    block_policy:       ExpiryBlockPolicy = ExpiryBlockPolicy.block
    notes:              Optional[str]   = None

class CustomerShelfLifeRuleOut(_Base):
    id:                 UUID
    customer_id:        Optional[UUID]
    customer_group:     Optional[str]
    country_code:       Optional[str]
    channel:            Optional[str]
    product_id:         Optional[UUID]
    material_id:        Optional[UUID]
    rule_type:          CustomerRuleType
    min_remaining_days: Optional[int]
    min_pct_remaining:  Optional[Decimal]
    block_policy:       ExpiryBlockPolicy
    is_active:          bool
    notes:              Optional[str]
    created_at:         datetime


# ── LotShelfLifeProfile ───────────────────────────────────────────────────────

class LotShelfLifeProfileOut(_Base):
    id:                    UUID
    lot_id:                UUID
    manufacturing_date:    Optional[date]
    expiry_date:           Optional[date]
    best_before_date:      Optional[date]
    retest_date:           Optional[date]
    qc_release_date:       Optional[date]
    remaining_shelf_life_days:  Optional[int]
    age_since_production_days:  Optional[int]
    age_since_release_days:     Optional[int]
    original_shelf_life_days:   Optional[int]
    pct_remaining:              Optional[Decimal]
    shelf_life_status:          ShelfLifeStatus
    near_expiry_flag:           bool
    expired_flag:               bool
    blocked_for_issue_flag:     bool
    blocked_for_shipment_flag:  bool
    blocked_for_consumption_flag: bool
    hold_reason:                Optional[str]
    last_recalc_at:             Optional[datetime]
    status_changed_at:          Optional[datetime]
    created_at:                 datetime

class LotShelfLifeProfileUpdate(BaseModel):
    manufacturing_date: Optional[date] = None
    expiry_date:        Optional[date] = None
    best_before_date:   Optional[date] = None
    retest_date:        Optional[date] = None
    qc_release_date:    Optional[date] = None
    hold_reason:        Optional[str]  = None
    blocked_for_issue_flag:       Optional[bool] = None
    blocked_for_shipment_flag:    Optional[bool] = None
    blocked_for_consumption_flag: Optional[bool] = None


# ── FEFO Ranking ──────────────────────────────────────────────────────────────

class FEFORankRequest(BaseModel):
    product_id:   Optional[UUID] = None
    material_id:  Optional[UUID] = None
    warehouse_id: Optional[UUID] = None
    quantity_needed: Optional[Decimal] = None
    context:      FEFOContext = FEFOContext.warehouse_pick
    customer_id:  Optional[UUID] = None
    exclude_lot_ids: List[UUID] = Field(default_factory=list)

class FEFOLotCandidate(BaseModel):
    lot_id:         UUID
    lot_number:     str
    expiry_date:    Optional[date]
    remaining_days: Optional[int]
    pct_remaining:  Optional[Decimal]
    quantity_available: Decimal
    shelf_life_status:  ShelfLifeStatus
    rank:           int
    is_recommended: bool
    exclusion_reason: Optional[str] = None

class FEFORankResponse(BaseModel):
    candidates:          List[FEFOLotCandidate]
    recommended_lot_id:  Optional[UUID]
    strategy_used:       PickingStrategy
    policy_violations:   List[str]

class FEFOValidateIssueRequest(BaseModel):
    lot_id:      UUID
    quantity:    Decimal
    context:     FEFOContext = FEFOContext.production_issue
    product_id:  Optional[UUID] = None
    material_id: Optional[UUID] = None
    warehouse_id: Optional[UUID] = None
    override_reason: Optional[str] = None
    override_by_id:  Optional[UUID] = None

class FEFOValidateIssueResponse(BaseModel):
    allowed:     bool
    requires_approval: bool
    warnings:    List[str]
    errors:      List[str]
    lot_status:  Optional[ShelfLifeStatus]
    remaining_days: Optional[int]

class FEFOValidateShipmentRequest(BaseModel):
    lot_id:      UUID
    quantity:    Decimal
    customer_id: Optional[UUID] = None
    product_id:  Optional[UUID] = None
    material_id: Optional[UUID] = None

class FEFOValidateShipmentResponse(BaseModel):
    allowed:     bool
    requires_approval: bool
    warnings:    List[str]
    errors:      List[str]
    remaining_days:    Optional[int]
    pct_remaining:     Optional[Decimal]
    customer_min_days: Optional[int]

class FEFOAuditLogCreate(BaseModel):
    context:            FEFOContext
    reference_doc:      Optional[str] = None
    reference_doc_type: Optional[str] = None
    product_id:         Optional[UUID] = None
    material_id:        Optional[UUID] = None
    warehouse_id:       Optional[UUID] = None
    customer_id:        Optional[UUID] = None
    recommended_lot_id: Optional[UUID] = None
    actual_lot_id:      Optional[UUID] = None
    recommended_expiry: Optional[date] = None
    actual_expiry:      Optional[date] = None
    is_fefo_compliant:  bool
    override_reason:    Optional[str] = None
    override_approved_by_id: Optional[UUID] = None
    picked_by_id:       Optional[UUID] = None
    quantity:           Optional[Decimal] = None

class FEFOAuditLogOut(_Base):
    id:                 UUID
    context:            FEFOContext
    reference_doc:      Optional[str]
    reference_doc_type: Optional[str]
    product_id:         Optional[UUID]
    material_id:        Optional[UUID]
    warehouse_id:       Optional[UUID]
    customer_id:        Optional[UUID]
    recommended_lot_id: Optional[UUID]
    actual_lot_id:      Optional[UUID]
    recommended_expiry: Optional[date]
    actual_expiry:      Optional[date]
    is_fefo_compliant:  bool
    override_reason:    Optional[str]
    quantity:           Optional[Decimal]
    created_at:         datetime


# ── Retest ────────────────────────────────────────────────────────────────────

class RetestRequestCreate(BaseModel):
    lot_id:          UUID
    reason:          str
    requested_by_id: Optional[UUID] = None
    scheduled_date:  Optional[date]  = None
    assigned_to_id:  Optional[UUID]  = None

class RetestResultCreate(BaseModel):
    result_passed:    bool
    result_notes:     Optional[str] = None
    result_by_id:     Optional[UUID] = None
    new_expiry_date:  Optional[date] = None
    new_retest_date:  Optional[date] = None
    new_release_date: Optional[date] = None

class RetestRequestOut(_Base):
    id:             UUID
    lot_id:         UUID
    request_number: str
    status:         RetestStatus
    reason:         str
    requested_by_id: Optional[UUID]
    requested_at:   Optional[datetime]
    assigned_to_id: Optional[UUID]
    scheduled_date: Optional[date]
    result_passed:  Optional[bool]
    result_notes:   Optional[str]
    result_by_id:   Optional[UUID]
    result_at:      Optional[datetime]
    new_expiry_date:  Optional[date]
    new_retest_date:  Optional[date]
    new_release_date: Optional[date]
    created_at:     datetime
    updated_at:     datetime


# ── Bulk Hold ─────────────────────────────────────────────────────────────────

class BulkHoldCreate(BaseModel):
    lot_id:        Optional[UUID]    = None
    material_id:   Optional[UUID]    = None
    warehouse_id:  Optional[UUID]    = None
    location_ref:  Optional[str]     = None
    creation_time: datetime
    max_hold_hours: Decimal
    notes:         Optional[str]     = None

class BulkHoldOut(_Base):
    id:              UUID
    lot_id:          Optional[UUID]
    material_id:     Optional[UUID]
    warehouse_id:    Optional[UUID]
    location_ref:    Optional[str]
    creation_time:   datetime
    max_hold_hours:  Decimal
    expiry_time:     datetime
    hours_used:      Optional[Decimal]
    pct_hold_used:   Optional[Decimal]
    is_expired:      bool
    is_near_limit:   bool
    is_blocked:      bool
    qc_reassessment_triggered: bool
    disposition_action: Optional[DispositionAction]
    notes:           Optional[str]
    created_at:      datetime


# ── Alerts ────────────────────────────────────────────────────────────────────

class ShelfLifeAlertOut(_Base):
    id:           UUID
    alert_type:   AlertType
    severity:     AlertSeverity
    is_resolved:  bool
    resolved_at:  Optional[datetime]
    lot_id:       Optional[UUID]
    product_id:   Optional[UUID]
    material_id:  Optional[UUID]
    warehouse_id: Optional[UUID]
    customer_id:  Optional[UUID]
    title:        str
    message:      str
    days_remaining:      Optional[int]
    stock_value_at_risk: Optional[Decimal]
    quantity_affected:   Optional[Decimal]
    created_at:   datetime


# ── Disposition ───────────────────────────────────────────────────────────────

class DispositionApproveRequest(BaseModel):
    approved_by_id:  UUID
    execution_notes: Optional[str] = None

class DispositionSuggestionOut(_Base):
    id:               UUID
    lot_id:           UUID
    product_id:       Optional[UUID]
    material_id:      Optional[UUID]
    warehouse_id:     Optional[UUID]
    action:           DispositionAction
    status:           DispositionStatus
    reason:           str
    urgency_score:    Optional[int]
    quantity_affected:  Optional[Decimal]
    financial_exposure: Optional[Decimal]
    days_until_expiry:  Optional[int]
    approved_by_id:   Optional[UUID]
    approved_at:      Optional[datetime]
    execution_notes:  Optional[str]
    created_at:       datetime
    updated_at:       datetime


# ── AI ────────────────────────────────────────────────────────────────────────

class SLAIRecReviewRequest(BaseModel):
    status:      SLAIRecStatus
    reviewed_by_id: UUID
    review_note: Optional[str] = None

class SLAIRecommendationOut(_Base):
    id:              UUID
    agent_type:      SLAIAgentType
    status:          SLAIRecStatus
    lot_id:          Optional[UUID]
    product_id:      Optional[UUID]
    material_id:     Optional[UUID]
    warehouse_id:    Optional[UUID]
    title:           str
    explanation:     str
    recommendation:  str
    confidence_score: Optional[Decimal]
    impact_value_kes: Optional[Decimal]
    reviewed_by_id:  Optional[UUID]
    reviewed_at:     Optional[datetime]
    review_note:     Optional[str]
    created_at:      datetime


# ── Dashboard ─────────────────────────────────────────────────────────────────

class ShelfLifeKPIs(BaseModel):
    total_lots_tracked:    int
    active_lots:           int
    near_expiry_lots:      int
    expired_lots:          int
    blocked_lots:          int
    pending_retest_lots:   int
    near_expiry_value_kes: Decimal
    expired_value_kes:     Decimal
    fefo_compliance_pct:   Optional[Decimal]
    open_alerts:           int
    pending_dispositions:  int

class ShelfLifeDashboard(BaseModel):
    kpis:                    ShelfLifeKPIs
    critical_alerts:         List[ShelfLifeAlertOut]
    near_expiry_lots:        List[LotShelfLifeProfileOut]
    expired_lots:            List[LotShelfLifeProfileOut]
    pending_dispositions:    List[DispositionSuggestionOut]
    pending_ai_recs:         List[SLAIRecommendationOut]
    retest_overdue:          int
    bulk_hold_at_risk:       int


# ── Compliance Report ─────────────────────────────────────────────────────────

class FEFOComplianceRow(BaseModel):
    warehouse_id:   Optional[UUID]
    warehouse_name: Optional[str]
    total_picks:    int
    compliant_picks: int
    non_compliant_picks: int
    compliance_pct: Decimal
    override_count: int

class FEFOComplianceReport(BaseModel):
    period_from:    Optional[date]
    period_to:      Optional[date]
    overall_compliance_pct: Decimal
    rows:           List[FEFOComplianceRow]
    top_overriders: List[dict]
