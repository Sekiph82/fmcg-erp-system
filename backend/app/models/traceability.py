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


# ── Enums ─────────────────────────────────────────────────────────────────────

class TraceEventType(str, enum.Enum):
    receipt       = "receipt"
    issue         = "issue"
    consumption   = "consumption"
    transformation= "transformation"
    packaging     = "packaging"
    shipment      = "shipment"
    return_event  = "return_event"
    rework        = "rework"
    scrap         = "scrap"
    transfer      = "transfer"
    quarantine    = "quarantine"
    recall_action = "recall_action"
    adjustment    = "adjustment"

class TraceItemStage(str, enum.Enum):
    supplier     = "supplier"
    grn          = "grn"
    raw_stock    = "raw_stock"
    prepared     = "prepared"
    intermediate = "intermediate"
    bulk         = "bulk"
    finished_good= "finished_good"
    packaging    = "packaging"
    quarantine   = "quarantine"
    rework       = "rework"
    scrapped     = "scrapped"
    shipped      = "shipped"
    returned     = "returned"

class GenealogyRelType(str, enum.Enum):
    prepared_from   = "prepared_from"
    intermediate_from = "intermediate_from"
    bulk_from       = "bulk_from"
    packed_from     = "packed_from"
    reworked_from   = "reworked_from"
    repacked_from   = "repacked_from"
    returned_from   = "returned_from"
    received_from   = "received_from"
    split_from      = "split_from"
    merged_from     = "merged_from"

class RecallType(str, enum.Enum):
    internal    = "internal"
    customer    = "customer"
    market      = "market"
    regulatory  = "regulatory"
    mock_recall = "mock_recall"

class RecallTrigger(str, enum.Enum):
    qc              = "qc"
    complaint       = "complaint"
    supplier_notice = "supplier_notice"
    audit           = "audit"
    regulatory      = "regulatory"
    manual          = "manual"

class RecallSeverity(str, enum.Enum):
    low      = "low"
    medium   = "medium"
    high     = "high"
    critical = "critical"

class RecallStatus(str, enum.Enum):
    draft        = "draft"
    under_review = "under_review"
    active       = "active"
    contained    = "contained"
    in_progress  = "in_progress"
    completed    = "completed"
    closed       = "closed"
    cancelled    = "cancelled"

class RecallActionType(str, enum.Enum):
    quarantine          = "quarantine"
    shipment_block      = "shipment_block"
    customer_notify     = "customer_notify"
    distributor_notify  = "distributor_notify"
    internal_hold       = "internal_hold"
    return_request      = "return_request"
    destroy             = "destroy"
    rework              = "rework"
    regulatory_report   = "regulatory_report"
    followup_call       = "followup_call"
    closeout_verification = "closeout_verification"

class RecallActionStatus(str, enum.Enum):
    pending    = "pending"
    in_progress= "in_progress"
    completed  = "completed"
    cancelled  = "cancelled"
    overdue    = "overdue"

class RecallRiskStatus(str, enum.Enum):
    low      = "low"
    medium   = "medium"
    high     = "high"
    critical = "critical"

class TRRecAIAgentType(str, enum.Enum):
    scope_validator          = "scope_validator"
    risk_prioritizer         = "risk_prioritizer"
    investigation_assistant  = "investigation_assistant"

class TRRecAIRecStatus(str, enum.Enum):
    pending  = "pending"
    accepted = "accepted"
    rejected = "rejected"
    applied  = "applied"


# ── Traceability Events ───────────────────────────────────────────────────────

class TraceEvent(Base, TimestampMixin):
    """Immutable traceability event header — one per movement/transformation."""
    __tablename__ = "trace_events"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trace_event_type    = Column(Enum(TraceEventType), nullable=False, index=True)
    event_datetime      = Column(DateTime(timezone=True), nullable=False, index=True)
    reference_number    = Column(String(100), nullable=True, index=True)

    source_document_type= Column(String(60),  nullable=True)
    source_document_id  = Column(UUID(as_uuid=True), nullable=True, index=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True)
    work_order_id       = Column(UUID(as_uuid=True), nullable=True)

    plant_id            = Column(String(100), nullable=True)
    warehouse_id        = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)
    performed_by_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    notes               = Column(Text, nullable=True)
    is_recall_event     = Column(Boolean, default=False, nullable=False)
    recall_id           = Column(UUID(as_uuid=True), ForeignKey("recall_headers.id", ondelete="SET NULL"), nullable=True, index=True)

    lines        = relationship("TraceEventLine",    back_populates="event", cascade="all, delete-orphan")
    warehouse    = relationship("Warehouse",          foreign_keys=[warehouse_id])
    performed_by = relationship("User",              foreign_keys=[performed_by_id])
    approved_by  = relationship("User",              foreign_keys=[approved_by_id])


class TraceEventLine(Base, TimestampMixin):
    """One item movement within a trace event (source lot → destination lot)."""
    __tablename__ = "trace_event_lines"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id        = Column(UUID(as_uuid=True), ForeignKey("trace_events.id", ondelete="CASCADE"), nullable=False, index=True)

    product_id      = Column(UUID(as_uuid=True), ForeignKey("products.id",  ondelete="SET NULL"), nullable=True)
    material_id     = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)

    source_lot_id   = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="SET NULL"), nullable=True, index=True)
    child_lot_id    = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="SET NULL"), nullable=True, index=True)

    quantity        = Column(Numeric(14, 3), nullable=False)
    uom             = Column(String(30), nullable=True)

    source_stage    = Column(Enum(TraceItemStage), nullable=True)
    dest_stage      = Column(Enum(TraceItemStage), nullable=True)

    source_location_id = Column(UUID(as_uuid=True), ForeignKey("storage_locations.id", ondelete="SET NULL"), nullable=True)
    dest_location_id   = Column(UUID(as_uuid=True), ForeignKey("storage_locations.id", ondelete="SET NULL"), nullable=True)

    quality_status    = Column(String(50), nullable=True)
    movement_reason   = Column(String(100), nullable=True)

    linked_customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id",  ondelete="SET NULL"), nullable=True)
    linked_shipment_id = Column(UUID(as_uuid=True), nullable=True)
    linked_supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id",  ondelete="SET NULL"), nullable=True)
    linked_grn_id      = Column(UUID(as_uuid=True), nullable=True)

    notes = Column(Text, nullable=True)

    event      = relationship("TraceEvent",        back_populates="lines")
    product    = relationship("Product",           foreign_keys=[product_id])
    material   = relationship("Material",          foreign_keys=[material_id])
    source_lot = relationship("Lot",              foreign_keys=[source_lot_id])
    child_lot  = relationship("Lot",              foreign_keys=[child_lot_id])
    customer   = relationship("Customer",          foreign_keys=[linked_customer_id])
    supplier   = relationship("Supplier",          foreign_keys=[linked_supplier_id])


class LotGenealogyLink(Base, TimestampMixin):
    """Directed graph edge: parent_lot → child_lot (the genealogy graph)."""
    __tablename__ = "lot_genealogy_links"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_lot_id       = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="CASCADE"), nullable=False, index=True)
    child_lot_id        = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type   = Column(Enum(GenealogyRelType), nullable=False)

    source_document_type= Column(String(60), nullable=True)
    source_document_id  = Column(UUID(as_uuid=True), nullable=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True)

    quantity_linked     = Column(Numeric(14, 3), nullable=True)
    uom                 = Column(String(30), nullable=True)

    parent_stage        = Column(Enum(TraceItemStage), nullable=True)
    child_stage         = Column(Enum(TraceItemStage), nullable=True)

    notes               = Column(Text, nullable=True)

    parent_lot = relationship("Lot", foreign_keys=[parent_lot_id])
    child_lot  = relationship("Lot", foreign_keys=[child_lot_id])


# ── Recall Models ─────────────────────────────────────────────────────────────

class RecallHeader(Base, TimestampMixin):
    """Recall master record."""
    __tablename__ = "recall_headers"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recall_no            = Column(String(50), nullable=False, unique=True, index=True)
    recall_type          = Column(Enum(RecallType),    nullable=False)
    recall_reason        = Column(Text, nullable=False)
    trigger_source       = Column(Enum(RecallTrigger), nullable=False)
    severity_level       = Column(Enum(RecallSeverity),nullable=False, default=RecallSeverity.medium)
    status               = Column(Enum(RecallStatus),  nullable=False, default=RecallStatus.draft, index=True)

    initiation_datetime  = Column(DateTime(timezone=True), nullable=False)
    initiated_by_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_id       = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at          = Column(DateTime(timezone=True), nullable=True)

    source_lot_id        = Column(UUID(as_uuid=True), ForeignKey("lots.id",      ondelete="SET NULL"), nullable=True, index=True)
    source_product_id    = Column(UUID(as_uuid=True), ForeignKey("products.id",  ondelete="SET NULL"), nullable=True)
    source_material_id   = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    source_supplier_id   = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)

    target_market        = Column(String(200), nullable=True)
    country_scope        = Column(String(500), nullable=True)
    product_scope_notes  = Column(Text, nullable=True)

    linked_qc_case_id    = Column(UUID(as_uuid=True), nullable=True)
    linked_complaint_id  = Column(UUID(as_uuid=True), nullable=True)

    scope_calculated_at  = Column(DateTime(timezone=True), nullable=True)
    contained_at         = Column(DateTime(timezone=True), nullable=True)
    completed_at         = Column(DateTime(timezone=True), nullable=True)
    closed_at            = Column(DateTime(timezone=True), nullable=True)

    total_affected_qty   = Column(Numeric(14, 3), nullable=True)
    total_affected_customers = Column(Integer, nullable=True)
    recovery_pct         = Column(Numeric(5, 2), nullable=True)

    effectiveness_score  = Column(Numeric(5, 2), nullable=True)
    time_to_trace_hours  = Column(Numeric(8, 2), nullable=True)
    time_to_contain_hours= Column(Numeric(8, 2), nullable=True)
    sla_target_hours     = Column(Numeric(8, 2), nullable=True, default=72)  # 72h default SLA

    notes                = Column(Text, nullable=True)

    scope_lines    = relationship("RecallScopeLine",     back_populates="recall", cascade="all, delete-orphan")
    actions        = relationship("RecallAction",        back_populates="recall", cascade="all, delete-orphan")
    customer_impacts = relationship("RecallCustomerImpact", back_populates="recall", cascade="all, delete-orphan")
    returns        = relationship("RecallReturnRecord",  back_populates="recall", cascade="all, delete-orphan")
    ai_recs        = relationship("TRRecAIRecommendation", back_populates="recall", cascade="all, delete-orphan")

    source_lot     = relationship("Lot",      foreign_keys=[source_lot_id])
    source_product = relationship("Product",  foreign_keys=[source_product_id])
    source_material= relationship("Material", foreign_keys=[source_material_id])
    initiated_by   = relationship("User",     foreign_keys=[initiated_by_id])
    approved_by    = relationship("User",     foreign_keys=[approved_by_id])


class RecallScopeLine(Base, TimestampMixin):
    """One affected lot/batch within a recall scope."""
    __tablename__ = "recall_scope_lines"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recall_id   = Column(UUID(as_uuid=True), ForeignKey("recall_headers.id", ondelete="CASCADE"), nullable=False, index=True)

    affected_item_id    = Column(UUID(as_uuid=True), ForeignKey("products.id",  ondelete="SET NULL"), nullable=True)
    affected_material_id= Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    affected_lot_id     = Column(UUID(as_uuid=True), ForeignKey("lots.id",      ondelete="SET NULL"), nullable=True, index=True)
    affected_warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)

    affected_qty_total      = Column(Numeric(14, 3), default=0, nullable=False)
    affected_qty_in_stock   = Column(Numeric(14, 3), default=0, nullable=False)
    affected_qty_in_transit = Column(Numeric(14, 3), default=0, nullable=False)
    affected_qty_shipped    = Column(Numeric(14, 3), default=0, nullable=False)
    affected_qty_returned   = Column(Numeric(14, 3), default=0, nullable=False)
    affected_qty_quarantined= Column(Numeric(14, 3), default=0, nullable=False)
    affected_qty_scrapped   = Column(Numeric(14, 3), default=0, nullable=False)
    affected_qty_reworked   = Column(Numeric(14, 3), default=0, nullable=False)

    affected_customer_count = Column(Integer, default=0, nullable=False)
    risk_status             = Column(Enum(RecallRiskStatus), default=RecallRiskStatus.medium, nullable=False)
    action_status           = Column(Enum(RecallActionStatus), default=RecallActionStatus.pending, nullable=False)

    hold_placed         = Column(Boolean, default=False, nullable=False)
    hold_placed_at      = Column(DateTime(timezone=True), nullable=True)

    notes = Column(Text, nullable=True)

    recall        = relationship("RecallHeader",    back_populates="scope_lines")
    affected_item = relationship("Product",         foreign_keys=[affected_item_id])
    affected_material = relationship("Material",    foreign_keys=[affected_material_id])
    affected_lot  = relationship("Lot",             foreign_keys=[affected_lot_id])
    affected_warehouse = relationship("Warehouse",  foreign_keys=[affected_warehouse_id])


class RecallAction(Base, TimestampMixin):
    """Recall action item — what must be done, by whom, by when."""
    __tablename__ = "recall_actions"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recall_id   = Column(UUID(as_uuid=True), ForeignKey("recall_headers.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(Enum(RecallActionType), nullable=False)
    status      = Column(Enum(RecallActionStatus), default=RecallActionStatus.pending, nullable=False)

    target_entity_type = Column(String(60),  nullable=True)
    target_entity_id   = Column(UUID(as_uuid=True), nullable=True)
    target_description = Column(String(300), nullable=True)

    assigned_to_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    due_date           = Column(Date, nullable=True)
    completed_at       = Column(DateTime(timezone=True), nullable=True)
    completed_by_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    evidence_note      = Column(Text, nullable=True)
    notes              = Column(Text, nullable=True)

    recall       = relationship("RecallHeader", back_populates="actions")
    assigned_to  = relationship("User",         foreign_keys=[assigned_to_id])
    completed_by = relationship("User",         foreign_keys=[completed_by_id])


class RecallCustomerImpact(Base, TimestampMixin):
    """Per-customer impact record within a recall."""
    __tablename__ = "recall_customer_impacts"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recall_id   = Column(UUID(as_uuid=True), ForeignKey("recall_headers.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id",      ondelete="SET NULL"), nullable=True, index=True)

    customer_name       = Column(String(200), nullable=True)
    contact_info        = Column(String(300), nullable=True)
    country_code        = Column(String(10),  nullable=True)
    channel             = Column(String(100), nullable=True)

    affected_lot_id     = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="SET NULL"), nullable=True)
    shipment_reference  = Column(String(100), nullable=True)
    delivery_date       = Column(Date, nullable=True)
    qty_delivered       = Column(Numeric(14, 3), nullable=True)
    qty_remaining_open  = Column(Numeric(14, 3), nullable=True)

    notification_sent   = Column(Boolean, default=False, nullable=False)
    notification_sent_at= Column(DateTime(timezone=True), nullable=True)
    notification_method = Column(String(50), nullable=True)

    return_requested    = Column(Boolean, default=False, nullable=False)
    return_confirmed    = Column(Boolean, default=False, nullable=False)
    qty_returned        = Column(Numeric(14, 3), nullable=True)

    follow_up_owner_id  = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    priority_rank       = Column(Integer, nullable=True)
    risk_level          = Column(Enum(RecallRiskStatus), nullable=True)
    notes               = Column(Text, nullable=True)

    recall       = relationship("RecallHeader", back_populates="customer_impacts")
    customer     = relationship("Customer",     foreign_keys=[customer_id])
    affected_lot = relationship("Lot",          foreign_keys=[affected_lot_id])
    follow_up_owner = relationship("User",      foreign_keys=[follow_up_owner_id])


class RecallReturnRecord(Base, TimestampMixin):
    """Quantity return tracking per recall scope line / customer."""
    __tablename__ = "recall_return_records"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recall_id   = Column(UUID(as_uuid=True), ForeignKey("recall_headers.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id",      ondelete="SET NULL"), nullable=True)
    lot_id      = Column(UUID(as_uuid=True), ForeignKey("lots.id",           ondelete="SET NULL"), nullable=True)

    qty_requested   = Column(Numeric(14, 3), nullable=True)
    qty_confirmed   = Column(Numeric(14, 3), nullable=True)
    qty_received    = Column(Numeric(14, 3), nullable=True)
    qty_destroyed_at_customer = Column(Numeric(14, 3), nullable=True)
    qty_quarantined_on_return  = Column(Numeric(14, 3), nullable=True)
    qty_reworked    = Column(Numeric(14, 3), nullable=True)
    qty_written_off = Column(Numeric(14, 3), nullable=True)

    return_date     = Column(Date, nullable=True)
    return_ref      = Column(String(100), nullable=True)
    discrepancy     = Column(Numeric(14, 3), nullable=True)

    return_refused  = Column(Boolean, default=False, nullable=False)
    follow_up_required = Column(Boolean, default=False, nullable=False)
    evidence_notes  = Column(Text, nullable=True)

    recall   = relationship("RecallHeader", back_populates="returns")
    customer = relationship("Customer",     foreign_keys=[customer_id])
    lot      = relationship("Lot",          foreign_keys=[lot_id])


class TRRecAIRecommendation(Base, TimestampMixin):
    """AI agent recommendations for traceability and recall management."""
    __tablename__ = "tr_rec_ai_recommendations"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type = Column(Enum(TRRecAIAgentType), nullable=False, index=True)
    status     = Column(Enum(TRRecAIRecStatus), default=TRRecAIRecStatus.pending, nullable=False)

    recall_id    = Column(UUID(as_uuid=True), ForeignKey("recall_headers.id", ondelete="SET NULL"), nullable=True, index=True)
    lot_id       = Column(UUID(as_uuid=True), ForeignKey("lots.id",           ondelete="SET NULL"), nullable=True)
    customer_id  = Column(UUID(as_uuid=True), ForeignKey("customers.id",      ondelete="SET NULL"), nullable=True)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id",     ondelete="SET NULL"), nullable=True)

    title            = Column(String(300), nullable=False)
    explanation      = Column(Text, nullable=False)
    recommendation   = Column(Text, nullable=False)
    confidence_score = Column(Numeric(5, 2), nullable=True)
    priority_score   = Column(Integer, nullable=True)

    reviewed_by_id   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at      = Column(DateTime(timezone=True), nullable=True)
    review_note      = Column(Text, nullable=True)

    payload = Column(JSON, nullable=True)

    recall      = relationship("RecallHeader", back_populates="ai_recs")
    lot         = relationship("Lot",          foreign_keys=[lot_id])
    customer    = relationship("Customer",     foreign_keys=[customer_id])
    warehouse   = relationship("Warehouse",    foreign_keys=[warehouse_id])
    reviewed_by = relationship("User",         foreign_keys=[reviewed_by_id])


# ── Recall Communication Templates ───────────────────────────────────────────

class RecallAudience(str, enum.Enum):
    CONSUMER   = "CONSUMER"
    RETAILER   = "RETAILER"
    REGULATOR  = "REGULATOR"
    INTERNAL   = "INTERNAL"
    MEDIA      = "MEDIA"


class RecallCommunicationTemplate(Base, TimestampMixin):
    """Predefined message templates for recall communications."""
    __tablename__ = "recall_communication_templates"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name         = Column(String(200), nullable=False)
    audience     = Column(Enum(RecallAudience), nullable=False, index=True)
    recall_type  = Column(String(50), nullable=True)   # null = all types
    severity_level = Column(String(50), nullable=True) # null = all severities
    subject      = Column(String(500), nullable=False)
    body         = Column(Text, nullable=False)         # supports {{recall_no}}, {{product}}, {{lot}} placeholders
    channel      = Column(String(50), nullable=False, default="EMAIL")  # EMAIL / SMS / WHATSAPP
    language     = Column(String(10), nullable=False, default="en")
    is_active    = Column(Boolean, default=True, nullable=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_by = relationship("User", foreign_keys=[created_by_id])


# ── Recall Status Audit Log (immutable) ──────────────────────────────────────

class RecallStatusLog(Base, TimestampMixin):
    """Immutable log of every status change on a recall. Never updated or deleted."""
    __tablename__ = "recall_status_logs"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recall_id      = Column(UUID(as_uuid=True), ForeignKey("recall_headers.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    from_status    = Column(String(50), nullable=True)
    to_status      = Column(String(50), nullable=False)
    changed_by_id  = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    changed_at     = Column(DateTime(timezone=True), nullable=False)
    reason         = Column(Text, nullable=True)
    system_note    = Column(String(500), nullable=True)  # auto-generated context

    changed_by = relationship("User", foreign_keys=[changed_by_id])


# ── Recall Evidence Attachment ────────────────────────────────────────────────

class RecallEvidence(Base, TimestampMixin):
    """Documents / photos attached to a recall as evidence."""
    __tablename__ = "recall_evidence"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recall_id   = Column(UUID(as_uuid=True), ForeignKey("recall_headers.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    title       = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    file_url    = Column(String(1000), nullable=True)
    file_name   = Column(String(500), nullable=True)
    file_type   = Column(String(100), nullable=True)  # PDF / JPEG / etc.
    evidence_type = Column(String(100), nullable=True)  # LAB_REPORT / PHOTO / REGULATORY / CUSTOMER_COMPLAINT
    uploaded_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])
