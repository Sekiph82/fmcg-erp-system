import uuid
import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Column, String, Numeric, Integer, ForeignKey, Enum, Date,
    DateTime, Text, Boolean, JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


# ── Enums ────────────────────────────────────────────────────────────────────

class ShelfLifeStatus(str, enum.Enum):
    not_applicable     = "not_applicable"
    active             = "active"
    near_expiry        = "near_expiry"
    expired            = "expired"
    blocked            = "blocked"
    qc_hold            = "qc_hold"
    quarantine         = "quarantine"
    pending_retest     = "pending_retest"
    retested_released  = "retested_released"
    customer_restricted= "customer_restricted"

class PickingStrategy(str, enum.Enum):
    fefo   = "fefo"
    fifo   = "fifo"
    lifo   = "lifo"
    manual = "manual"
    hybrid = "hybrid"   # FEFO then FIFO for same-expiry lots

class ExpiryBlockPolicy(str, enum.Enum):
    block              = "block"
    warn               = "warn"
    allow_with_approval= "allow_with_approval"

class NearExpiryPolicy(str, enum.Enum):
    allow              = "allow"
    warn               = "warn"
    require_approval   = "require_approval"
    block_external     = "block_external"   # block external shipment, allow internal

class ShelfLifeCategory(str, enum.Enum):
    raw            = "raw"
    intermediate   = "intermediate"
    bulk           = "bulk"
    finished_goods = "finished_goods"
    packaging      = "packaging"
    other          = "other"

class RetestStatus(str, enum.Enum):
    pending    = "pending"
    requested  = "requested"
    in_progress= "in_progress"
    passed     = "passed"
    failed     = "failed"
    cancelled  = "cancelled"

class DispositionAction(str, enum.Enum):
    use_urgently        = "use_urgently"
    prioritize_shipment = "prioritize_shipment"
    clearance_channel   = "clearance_channel"
    retest              = "retest"
    quarantine          = "quarantine"
    rework              = "rework"
    scrap               = "scrap"

class DispositionStatus(str, enum.Enum):
    suggested = "suggested"
    approved  = "approved"
    executed  = "executed"
    cancelled = "cancelled"

class AlertType(str, enum.Enum):
    near_expiry          = "near_expiry"
    expired              = "expired"
    bulk_age_limit       = "bulk_age_limit"
    order_blocked        = "order_blocked"
    production_blocked   = "production_blocked"
    retest_overdue       = "retest_overdue"
    high_risk_value      = "high_risk_value"
    poor_compliance      = "poor_compliance"
    unretested_lot       = "unretested_lot"

class AlertSeverity(str, enum.Enum):
    info     = "info"
    warning  = "warning"
    critical = "critical"

class SLAIAgentType(str, enum.Enum):
    expiry_risk_predictor  = "expiry_risk_predictor"
    allocation_optimizer   = "allocation_optimizer"
    compliance_monitor     = "compliance_monitor"

class SLAIRecStatus(str, enum.Enum):
    pending  = "pending"
    accepted = "accepted"
    rejected = "rejected"
    applied  = "applied"

class StrategyScope(str, enum.Enum):
    item_warehouse_location = "item_warehouse_location"
    item_warehouse          = "item_warehouse"
    item_default            = "item_default"
    warehouse_default       = "warehouse_default"
    system_fallback         = "system_fallback"

class CustomerRuleType(str, enum.Enum):
    fixed_days        = "fixed_days"
    percentage        = "percentage"

class FEFOContext(str, enum.Enum):
    production_issue  = "production_issue"
    warehouse_pick    = "warehouse_pick"
    sales_shipment    = "sales_shipment"
    internal_transfer = "internal_transfer"
    line_side_issue   = "line_side_issue"


# ── Master Config ─────────────────────────────────────────────────────────────

class ItemShelfLifeConfig(Base, TimestampMixin):
    """Per-item shelf-life policy configuration."""
    __tablename__ = "item_shelf_life_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    product_id  = Column(UUID(as_uuid=True), ForeignKey("products.id",  ondelete="CASCADE"), nullable=True, index=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="CASCADE"), nullable=True, index=True)

    shelf_life_control_enabled = Column(Boolean, default=True, nullable=False)
    shelf_life_category        = Column(Enum(ShelfLifeCategory), default=ShelfLifeCategory.raw, nullable=False)
    shelf_life_days            = Column(Integer, nullable=True)
    min_remaining_days_issue   = Column(Integer, nullable=True)
    min_remaining_days_ship    = Column(Integer, nullable=True)
    near_expiry_threshold_days = Column(Integer, default=30, nullable=False)

    picking_strategy_default   = Column(Enum(PickingStrategy),     default=PickingStrategy.fefo,  nullable=False)
    expiry_block_policy        = Column(Enum(ExpiryBlockPolicy),   default=ExpiryBlockPolicy.block, nullable=False)
    near_expiry_issue_policy   = Column(Enum(NearExpiryPolicy),    default=NearExpiryPolicy.warn,  nullable=False)
    near_expiry_ship_policy    = Column(Enum(NearExpiryPolicy),    default=NearExpiryPolicy.warn,  nullable=False)

    manufacturing_date_required = Column(Boolean, default=True,  nullable=False)
    expiry_date_required        = Column(Boolean, default=True,  nullable=False)
    retest_date_required        = Column(Boolean, default=False, nullable=False)
    best_before_date_required   = Column(Boolean, default=False, nullable=False)
    allowed_retest              = Column(Boolean, default=False, nullable=False)
    auto_expiry_calculation     = Column(Boolean, default=True,  nullable=False)

    max_hold_hours              = Column(Numeric(10, 2), nullable=True)

    notes = Column(Text, nullable=True)

    product  = relationship("Product",  foreign_keys=[product_id])
    material = relationship("Material", foreign_keys=[material_id])


class PickingStrategyConfig(Base, TimestampMixin):
    """Hierarchical picking strategy: item/warehouse/location specific overrides."""
    __tablename__ = "picking_strategy_configs"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope        = Column(Enum(StrategyScope), nullable=False)
    strategy     = Column(Enum(PickingStrategy), nullable=False)
    is_active    = Column(Boolean, default=True, nullable=False)

    product_id   = Column(UUID(as_uuid=True), ForeignKey("products.id",          ondelete="CASCADE"), nullable=True)
    material_id  = Column(UUID(as_uuid=True), ForeignKey("materials.id",         ondelete="CASCADE"), nullable=True)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id",        ondelete="CASCADE"), nullable=True)
    location_id  = Column(UUID(as_uuid=True), ForeignKey("storage_locations.id", ondelete="CASCADE"), nullable=True)

    effective_from = Column(Date, nullable=True)
    notes          = Column(Text, nullable=True)
    changed_by_id  = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    product   = relationship("Product",         foreign_keys=[product_id])
    material  = relationship("Material",        foreign_keys=[material_id])
    warehouse = relationship("Warehouse",       foreign_keys=[warehouse_id])
    changed_by= relationship("User",            foreign_keys=[changed_by_id])


class CustomerShelfLifeRule(Base, TimestampMixin):
    """Customer / channel / country minimum remaining shelf-life rules."""
    __tablename__ = "customer_shelf_life_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    customer_id       = Column(UUID(as_uuid=True), ForeignKey("customers.id",  ondelete="CASCADE"), nullable=True, index=True)
    customer_group    = Column(String(100), nullable=True)
    country_code      = Column(String(10),  nullable=True)
    channel           = Column(String(100), nullable=True)
    product_id        = Column(UUID(as_uuid=True), ForeignKey("products.id",   ondelete="CASCADE"), nullable=True)
    material_id       = Column(UUID(as_uuid=True), ForeignKey("materials.id",  ondelete="CASCADE"), nullable=True)

    rule_type         = Column(Enum(CustomerRuleType), default=CustomerRuleType.fixed_days, nullable=False)
    min_remaining_days= Column(Integer, nullable=True)
    min_pct_remaining = Column(Numeric(5, 2), nullable=True)

    block_policy      = Column(Enum(ExpiryBlockPolicy), default=ExpiryBlockPolicy.block, nullable=False)
    is_active         = Column(Boolean, default=True, nullable=False)
    notes             = Column(Text, nullable=True)

    customer = relationship("Customer",  foreign_keys=[customer_id])
    product  = relationship("Product",   foreign_keys=[product_id])
    material = relationship("Material",  foreign_keys=[material_id])


# ── Lot Shelf-Life Profile ────────────────────────────────────────────────────

class LotShelfLifeProfile(Base, TimestampMixin):
    """Extended shelf-life status and metadata for each lot/batch."""
    __tablename__ = "lot_shelf_life_profiles"

    id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lot_id  = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    manufacturing_date = Column(Date, nullable=True)
    expiry_date        = Column(Date, nullable=True)
    best_before_date   = Column(Date, nullable=True)
    retest_date        = Column(Date, nullable=True)
    qc_release_date    = Column(Date, nullable=True)

    remaining_shelf_life_days  = Column(Integer, nullable=True)
    age_since_production_days  = Column(Integer, nullable=True)
    age_since_release_days     = Column(Integer, nullable=True)
    original_shelf_life_days   = Column(Integer, nullable=True)
    pct_remaining              = Column(Numeric(5, 2), nullable=True)

    shelf_life_status        = Column(Enum(ShelfLifeStatus), default=ShelfLifeStatus.active, nullable=False)
    near_expiry_flag         = Column(Boolean, default=False, nullable=False)
    expired_flag             = Column(Boolean, default=False, nullable=False)
    blocked_for_issue_flag   = Column(Boolean, default=False, nullable=False)
    blocked_for_shipment_flag= Column(Boolean, default=False, nullable=False)
    blocked_for_consumption_flag = Column(Boolean, default=False, nullable=False)

    hold_reason      = Column(Text, nullable=True)
    last_recalc_at   = Column(DateTime(timezone=True), nullable=True)
    status_changed_at= Column(DateTime(timezone=True), nullable=True)

    lot = relationship("Lot", foreign_keys=[lot_id])


# ── Retest ────────────────────────────────────────────────────────────────────

class RetestRequest(Base, TimestampMixin):
    """Retest workflow for lots with pending retest status."""
    __tablename__ = "retest_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    lot_id         = Column(UUID(as_uuid=True), ForeignKey("lots.id",  ondelete="RESTRICT"), nullable=False, index=True)
    request_number = Column(String(50), nullable=False, unique=True, index=True)
    status         = Column(Enum(RetestStatus), default=RetestStatus.pending, nullable=False)

    reason         = Column(Text, nullable=False)
    requested_by_id= Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    requested_at   = Column(DateTime(timezone=True), nullable=True)

    assigned_to_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    scheduled_date = Column(Date, nullable=True)

    result_passed  = Column(Boolean, nullable=True)
    result_notes   = Column(Text, nullable=True)
    result_by_id   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    result_at      = Column(DateTime(timezone=True), nullable=True)

    new_expiry_date  = Column(Date, nullable=True)
    new_retest_date  = Column(Date, nullable=True)
    new_release_date = Column(Date, nullable=True)

    lot          = relationship("Lot",  foreign_keys=[lot_id])
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    assigned_to  = relationship("User", foreign_keys=[assigned_to_id])
    result_by    = relationship("User", foreign_keys=[result_by_id])


# ── Bulk Hold ─────────────────────────────────────────────────────────────────

class BulkHoldRecord(Base, TimestampMixin):
    """Hold-age tracking for bulk, intermediate, premix, and tank materials."""
    __tablename__ = "bulk_hold_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    lot_id       = Column(UUID(as_uuid=True), ForeignKey("lots.id",       ondelete="RESTRICT"), nullable=True, index=True)
    material_id  = Column(UUID(as_uuid=True), ForeignKey("materials.id",  ondelete="RESTRICT"), nullable=True)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=True)
    location_ref = Column(String(200), nullable=True)

    creation_time     = Column(DateTime(timezone=True), nullable=False)
    max_hold_hours    = Column(Numeric(10, 2), nullable=False)
    expiry_time       = Column(DateTime(timezone=True), nullable=False)

    hours_used        = Column(Numeric(10, 2), nullable=True)
    pct_hold_used     = Column(Numeric(5, 2),  nullable=True)
    is_expired        = Column(Boolean, default=False, nullable=False)
    is_near_limit     = Column(Boolean, default=False, nullable=False)
    is_blocked        = Column(Boolean, default=False, nullable=False)

    qc_reassessment_triggered = Column(Boolean, default=False, nullable=False)
    disposition_action        = Column(Enum(DispositionAction), nullable=True)
    notes                     = Column(Text, nullable=True)

    lot      = relationship("Lot",      foreign_keys=[lot_id])
    material = relationship("Material", foreign_keys=[material_id])
    warehouse= relationship("Warehouse",foreign_keys=[warehouse_id])


# ── Alerts ────────────────────────────────────────────────────────────────────

class ShelfLifeAlert(Base, TimestampMixin):
    """Generated shelf-life alerts for monitoring dashboards and notifications."""
    __tablename__ = "shelf_life_alerts"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_type   = Column(Enum(AlertType),    nullable=False, index=True)
    severity     = Column(Enum(AlertSeverity, name="shelflife_alertseverity"),nullable=False)
    is_resolved  = Column(Boolean, default=False, nullable=False)
    resolved_at  = Column(DateTime(timezone=True), nullable=True)

    lot_id       = Column(UUID(as_uuid=True), ForeignKey("lots.id",       ondelete="SET NULL"), nullable=True, index=True)
    product_id   = Column(UUID(as_uuid=True), ForeignKey("products.id",   ondelete="SET NULL"), nullable=True)
    material_id  = Column(UUID(as_uuid=True), ForeignKey("materials.id",  ondelete="SET NULL"), nullable=True)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)
    customer_id  = Column(UUID(as_uuid=True), ForeignKey("customers.id",  ondelete="SET NULL"), nullable=True)

    title        = Column(String(300), nullable=False)
    message      = Column(Text, nullable=False)
    context_data = Column(JSON, nullable=True)

    days_remaining       = Column(Integer, nullable=True)
    stock_value_at_risk  = Column(Numeric(14, 2), nullable=True)
    quantity_affected    = Column(Numeric(14, 3), nullable=True)

    lot      = relationship("Lot",      foreign_keys=[lot_id])
    product  = relationship("Product",  foreign_keys=[product_id])
    material = relationship("Material", foreign_keys=[material_id])
    warehouse= relationship("Warehouse",foreign_keys=[warehouse_id])
    customer = relationship("Customer", foreign_keys=[customer_id])


# ── Disposition Suggestions ───────────────────────────────────────────────────

class DispositionSuggestion(Base, TimestampMixin):
    """AI/system disposition suggestions for at-risk lots."""
    __tablename__ = "disposition_suggestions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    lot_id        = Column(UUID(as_uuid=True), ForeignKey("lots.id",       ondelete="RESTRICT"), nullable=False, index=True)
    product_id    = Column(UUID(as_uuid=True), ForeignKey("products.id",   ondelete="SET NULL"), nullable=True)
    material_id   = Column(UUID(as_uuid=True), ForeignKey("materials.id",  ondelete="SET NULL"), nullable=True)
    warehouse_id  = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)

    action        = Column(Enum(DispositionAction), nullable=False)
    status        = Column(Enum(DispositionStatus), default=DispositionStatus.suggested, nullable=False)
    reason        = Column(Text, nullable=False)
    urgency_score = Column(Integer, nullable=True)

    quantity_affected   = Column(Numeric(14, 3), nullable=True)
    financial_exposure  = Column(Numeric(14, 2), nullable=True)
    days_until_expiry   = Column(Integer, nullable=True)

    approved_by_id  = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at     = Column(DateTime(timezone=True), nullable=True)
    execution_notes = Column(Text, nullable=True)

    lot          = relationship("Lot",      foreign_keys=[lot_id])
    product      = relationship("Product",  foreign_keys=[product_id])
    material     = relationship("Material", foreign_keys=[material_id])
    warehouse    = relationship("Warehouse",foreign_keys=[warehouse_id])
    approved_by  = relationship("User",     foreign_keys=[approved_by_id])


# ── FEFO Compliance Audit ─────────────────────────────────────────────────────

class FEFOAuditLog(Base, TimestampMixin):
    """Audit trail of every pick/issue/shipment vs FEFO recommendation."""
    __tablename__ = "fefo_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    context            = Column(Enum(FEFOContext), nullable=False, index=True)
    reference_doc      = Column(String(100), nullable=True)
    reference_doc_type = Column(String(50),  nullable=True)

    product_id         = Column(UUID(as_uuid=True), ForeignKey("products.id",   ondelete="SET NULL"), nullable=True)
    material_id        = Column(UUID(as_uuid=True), ForeignKey("materials.id",  ondelete="SET NULL"), nullable=True)
    warehouse_id       = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)
    customer_id        = Column(UUID(as_uuid=True), ForeignKey("customers.id",  ondelete="SET NULL"), nullable=True)

    recommended_lot_id = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="SET NULL"), nullable=True)
    actual_lot_id      = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="SET NULL"), nullable=True)

    recommended_expiry = Column(Date, nullable=True)
    actual_expiry      = Column(Date, nullable=True)

    is_fefo_compliant  = Column(Boolean, nullable=False)
    override_reason    = Column(Text, nullable=True)
    override_approved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    picked_by_id       = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    quantity           = Column(Numeric(14, 3), nullable=True)

    product          = relationship("Product",   foreign_keys=[product_id])
    material         = relationship("Material",  foreign_keys=[material_id])
    warehouse        = relationship("Warehouse", foreign_keys=[warehouse_id])
    customer         = relationship("Customer",  foreign_keys=[customer_id])
    recommended_lot  = relationship("Lot",       foreign_keys=[recommended_lot_id])
    actual_lot       = relationship("Lot",       foreign_keys=[actual_lot_id])
    picked_by        = relationship("User",      foreign_keys=[picked_by_id])
    override_approved_by = relationship("User",  foreign_keys=[override_approved_by_id])


# ── AI Recommendations ────────────────────────────────────────────────────────

class SLAIRecommendation(Base, TimestampMixin):
    """Shelf-life AI agent recommendations."""
    __tablename__ = "sl_ai_recommendations"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type = Column(Enum(SLAIAgentType), nullable=False, index=True)
    status     = Column(Enum(SLAIRecStatus), default=SLAIRecStatus.pending, nullable=False)

    lot_id       = Column(UUID(as_uuid=True), ForeignKey("lots.id",       ondelete="SET NULL"), nullable=True)
    product_id   = Column(UUID(as_uuid=True), ForeignKey("products.id",   ondelete="SET NULL"), nullable=True)
    material_id  = Column(UUID(as_uuid=True), ForeignKey("materials.id",  ondelete="SET NULL"), nullable=True)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)

    title             = Column(String(300), nullable=False)
    explanation       = Column(Text, nullable=False)
    recommendation    = Column(Text, nullable=False)
    confidence_score  = Column(Numeric(5, 2), nullable=True)
    impact_value_kes  = Column(Numeric(14, 2), nullable=True)

    reviewed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at    = Column(DateTime(timezone=True), nullable=True)
    review_note    = Column(Text, nullable=True)

    payload = Column(JSON, nullable=True)

    lot          = relationship("Lot",      foreign_keys=[lot_id])
    product      = relationship("Product",  foreign_keys=[product_id])
    material     = relationship("Material", foreign_keys=[material_id])
    warehouse    = relationship("Warehouse",foreign_keys=[warehouse_id])
    reviewed_by  = relationship("User",     foreign_keys=[reviewed_by_id])


class ExtensionStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ShelfLifeExtension(Base):
    """Formal shelf-life extension request — extends expiry beyond original date."""
    __tablename__ = "sl_extensions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="CASCADE"), nullable=False, index=True)
    lot_number = Column(String(100), nullable=True)
    product_name = Column(String(300), nullable=True)
    original_expiry = Column(Date, nullable=False)
    proposed_expiry = Column(Date, nullable=False)
    extension_days = Column(Integer, nullable=False)
    justification = Column(Text, nullable=False)
    risk_assessment = Column(Text, nullable=True)
    test_results_attached = Column(Boolean, default=False, nullable=False)
    requested_by = Column(String(200), nullable=True)
    status = Column(Enum(ExtensionStatus), nullable=False, default=ExtensionStatus.PENDING)
    approved_by = Column(String(200), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    lot = relationship("Lot", foreign_keys=[lot_id])
