import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Numeric, Integer, Boolean,
    ForeignKey, Enum, Date, DateTime, JSON, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


# ── Core QC Enums ─────────────────────────────────────────────────────────────

class QCType(str, enum.Enum):
    INCOMING = "INCOMING"
    IN_PROCESS = "IN_PROCESS"
    FINISHED_GOODS = "FINISHED_GOODS"
    RETEST = "RETEST"


class QCStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    PASSED = "PASSED"
    FAILED = "FAILED"
    CONDITIONAL_RELEASE = "CONDITIONAL_RELEASE"
    CANCELLED = "CANCELLED"


class QCDecision(str, enum.Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    CONDITIONAL_RELEASE = "CONDITIONAL_RELEASE"
    REWORK = "REWORK"


class ParameterType(str, enum.Enum):
    NUMERIC = "NUMERIC"
    TEXT = "TEXT"
    BOOLEAN = "BOOLEAN"
    PASS_FAIL = "PASS_FAIL"


# ── QMS Extension Enums ───────────────────────────────────────────────────────

class SamplingMethod(str, enum.Enum):
    FIXED = "FIXED"
    PERCENTAGE = "PERCENTAGE"
    FREQUENCY = "FREQUENCY"
    TIME_BASED = "TIME_BASED"
    CCP_TRIGGERED = "CCP_TRIGGERED"


class HazardType(str, enum.Enum):
    BIOLOGICAL = "BIOLOGICAL"
    CHEMICAL = "CHEMICAL"
    PHYSICAL = "PHYSICAL"
    ALLERGEN = "ALLERGEN"
    RADIOLOGICAL = "RADIOLOGICAL"


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DeviationStatus(str, enum.Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class CorrectiveActionStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    VERIFIED = "VERIFIED"
    OVERDUE = "OVERDUE"


class ReleaseStatus(str, enum.Enum):
    UNRELEASED = "UNRELEASED"
    QUARANTINED = "QUARANTINED"
    ON_HOLD = "ON_HOLD"
    RELEASED = "RELEASED"
    REJECTED = "REJECTED"
    REWORK = "REWORK"
    SCRAPPED = "SCRAPPED"


class QMSAIAgentType(str, enum.Enum):
    QUALITY_RISK_PREDICTOR = "QUALITY_RISK_PREDICTOR"
    DEVIATION_ANALYZER = "DEVIATION_ANALYZER"
    HACCP_ASSISTANT = "HACCP_ASSISTANT"


class QMSAIRecStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"


# ── QC Parameter Template ─────────────────────────────────────────────────────

class QCParameter(Base, TimestampMixin):
    """Reusable test parameter (pH, viscosity, temperature, etc.)."""
    __tablename__ = "qc_parameters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    parameter_type = Column(Enum(ParameterType), nullable=False, default=ParameterType.NUMERIC)
    unit = Column(String(30), nullable=True)
    min_value = Column(Numeric(14, 4), nullable=True)
    max_value = Column(Numeric(14, 4), nullable=True)
    expected_value = Column(String(200), nullable=True)
    is_critical = Column(Boolean, default=False, nullable=False)
    applicable_types = Column(String(100), nullable=False, default="ALL")
    is_active = Column(Boolean, default=True, nullable=False)


# ── QC Inspection Template ────────────────────────────────────────────────────

class QCTemplate(Base, TimestampMixin):
    """Reusable QC inspection template per item/category/process stage."""
    __tablename__ = "qc_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(150), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    qc_type = Column(Enum(QCType), nullable=False)
    qc_sub_type = Column(String(50), nullable=True)  # MIXING/INTERMEDIATE/BULK/PACKAGING/RETEST
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    product_category = Column(String(100), nullable=True)
    sampling_method = Column(Enum(SamplingMethod), nullable=False, default=SamplingMethod.FIXED)
    sample_size = Column(Numeric(10, 3), nullable=True)
    sample_percentage = Column(Numeric(5, 2), nullable=True)
    sampling_frequency = Column(Integer, nullable=True)
    sampling_interval_hours = Column(Numeric(6, 2), nullable=True)
    is_ccp_template = Column(Boolean, default=False, nullable=False)
    is_mandatory = Column(Boolean, default=True, nullable=False)
    blocks_progression = Column(Boolean, default=True, nullable=False)
    release_required = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    parameters = relationship("QCTemplateParameter", back_populates="template",
                              cascade="all, delete-orphan", order_by="QCTemplateParameter.display_order")
    product = relationship("Product", foreign_keys=[product_id])
    material = relationship("Material", foreign_keys=[material_id])


class QCTemplateParameter(Base, TimestampMixin):
    """Parameter line within a QC inspection template."""
    __tablename__ = "qc_template_parameters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("qc_templates.id", ondelete="CASCADE"), nullable=False)
    parameter_id = Column(UUID(as_uuid=True), ForeignKey("qc_parameters.id", ondelete="SET NULL"), nullable=True)
    parameter_name = Column(String(100), nullable=False)
    parameter_type = Column(Enum(ParameterType), nullable=False, default=ParameterType.NUMERIC)
    unit = Column(String(30), nullable=True)
    target_value = Column(String(200), nullable=True)
    min_value = Column(Numeric(14, 4), nullable=True)
    max_value = Column(Numeric(14, 4), nullable=True)
    is_critical = Column(Boolean, default=False, nullable=False)
    is_ccp_parameter = Column(Boolean, default=False, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)

    template = relationship("QCTemplate", back_populates="parameters")
    parameter = relationship("QCParameter", foreign_keys=[parameter_id])


# ── QC Inspection (Core) ──────────────────────────────────────────────────────

class QCInspection(Base, TimestampMixin):
    """Single QC inspection event (incoming, in-process, finished goods, retest)."""
    __tablename__ = "qc_inspections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inspection_no = Column(String(50), unique=True, nullable=False, index=True)
    qc_type = Column(Enum(QCType), nullable=False)
    qc_sub_type = Column(String(50), nullable=True)
    status = Column(Enum(QCStatus), nullable=False, default=QCStatus.PENDING)

    # Template linkage
    template_id = Column(UUID(as_uuid=True), ForeignKey("qc_templates.id", ondelete="SET NULL"), nullable=True)

    # Linked entities
    grn_id = Column(UUID(as_uuid=True), ForeignKey("goods_receipts.id", ondelete="SET NULL"), nullable=True)
    grn_line_id = Column(UUID(as_uuid=True), ForeignKey("grn_lines.id", ondelete="SET NULL"), nullable=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True)
    work_order_id = Column(UUID(as_uuid=True), nullable=True)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="SET NULL"), nullable=True)

    # Item identification
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)
    lot_number = Column(String(100), nullable=True)
    batch_no = Column(String(100), nullable=True)
    sample_size = Column(Numeric(10, 3), nullable=True)
    sample_unit = Column(String(20), nullable=True)

    inspection_date = Column(Date, nullable=False)
    inspector_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)

    # Blocking / release flags
    is_mandatory = Column(Boolean, default=False, nullable=False)
    blocks_progression = Column(Boolean, default=False, nullable=False)
    release_required = Column(Boolean, default=False, nullable=False)
    hold_flag = Column(Boolean, default=False, nullable=False)

    # Decision
    decision = Column(Enum(QCDecision), nullable=True)
    decided_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    decision_notes = Column(Text, nullable=True)
    rework_candidate = Column(Boolean, default=False, nullable=False)
    quarantine_applied = Column(Boolean, default=False, nullable=False)

    # Relationships
    template = relationship("QCTemplate", foreign_keys=[template_id])
    inspector = relationship("User", foreign_keys=[inspector_id])
    decided_by = relationship("User", foreign_keys=[decided_by_id])
    supplier = relationship("Supplier")
    material = relationship("Material")
    product = relationship("Product")
    lot = relationship("Lot")
    production_order = relationship("ProductionOrder")
    test_results = relationship("QCTestResult", back_populates="inspection",
                                cascade="all, delete-orphan", order_by="QCTestResult.created_at")


class QCTestResult(Base, TimestampMixin):
    """Individual test result within an inspection."""
    __tablename__ = "qc_test_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inspection_id = Column(UUID(as_uuid=True), ForeignKey("qc_inspections.id", ondelete="CASCADE"), nullable=False)
    parameter_id = Column(UUID(as_uuid=True), ForeignKey("qc_parameters.id", ondelete="SET NULL"), nullable=True)

    parameter_name = Column(String(100), nullable=False)
    parameter_type = Column(Enum(ParameterType), nullable=False)
    unit = Column(String(30), nullable=True)

    numeric_value = Column(Numeric(14, 4), nullable=True)
    text_value = Column(Text, nullable=True)
    boolean_value = Column(Boolean, nullable=True)

    min_spec = Column(Numeric(14, 4), nullable=True)
    max_spec = Column(Numeric(14, 4), nullable=True)
    expected_text = Column(String(200), nullable=True)

    is_passed = Column(Boolean, nullable=True)
    is_critical = Column(Boolean, default=False, nullable=False)
    tested_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)

    inspection = relationship("QCInspection", back_populates="test_results")
    parameter = relationship("QCParameter")
    tested_by = relationship("User")


# ── HACCP ─────────────────────────────────────────────────────────────────────

class HazardAnalysis(Base, TimestampMixin):
    """HACCP Hazard Analysis record for a process step."""
    __tablename__ = "haccp_hazard_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hazard_no = Column(String(50), nullable=False, unique=True, index=True)
    process_step = Column(String(200), nullable=False)
    hazard_type = Column(Enum(HazardType), nullable=False)
    hazard_description = Column(Text, nullable=False)
    risk_level = Column(Enum(RiskLevel), nullable=False, default=RiskLevel.MEDIUM)
    likelihood_score = Column(Integer, nullable=True)
    severity_score = Column(Integer, nullable=True)
    risk_score = Column(Integer, nullable=True)
    control_measure = Column(Text, nullable=False)
    is_ccp = Column(Boolean, default=False, nullable=False)
    ccp_id = Column(UUID(as_uuid=True), ForeignKey("critical_control_points.id", ondelete="SET NULL"), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    ccp = relationship("CriticalControlPoint", foreign_keys=[ccp_id])
    product = relationship("Product", foreign_keys=[product_id])
    material = relationship("Material", foreign_keys=[material_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])


class CriticalControlPoint(Base, TimestampMixin):
    """Critical Control Point (CCP) definition per HACCP plan."""
    __tablename__ = "critical_control_points"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ccp_no = Column(String(50), nullable=False, unique=True, index=True)
    ccp_name = Column(String(200), nullable=False)
    process_step = Column(String(200), nullable=False)
    hazard_type = Column(Enum(HazardType), nullable=False)
    parameter_name = Column(String(100), nullable=False)
    parameter_unit = Column(String(30), nullable=True)
    critical_limit_min = Column(Numeric(14, 4), nullable=True)
    critical_limit_max = Column(Numeric(14, 4), nullable=True)
    critical_limit_description = Column(Text, nullable=True)
    monitoring_method = Column(String(200), nullable=False)
    monitoring_frequency = Column(String(100), nullable=False)
    monitoring_frequency_hours = Column(Numeric(6, 2), nullable=True)
    corrective_action_description = Column(Text, nullable=False)
    responsible_role = Column(String(100), nullable=True)
    responsible_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verification_method = Column(Text, nullable=True)
    verification_frequency = Column(String(100), nullable=True)
    record_keeping = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    allergen_related = Column(Boolean, default=False, nullable=False)
    cleaning_required = Column(Boolean, default=False, nullable=False)

    monitoring_logs = relationship("CCPMonitoringLog", back_populates="ccp", cascade="all, delete-orphan")
    responsible_user = relationship("User", foreign_keys=[responsible_user_id])
    product = relationship("Product", foreign_keys=[product_id])


class CCPMonitoringLog(Base, TimestampMixin):
    """Real-time or manual CCP monitoring entry during production."""
    __tablename__ = "ccp_monitoring_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ccp_id = Column(UUID(as_uuid=True), ForeignKey("critical_control_points.id", ondelete="CASCADE"), nullable=False, index=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True)
    work_order_id = Column(UUID(as_uuid=True), nullable=True)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="SET NULL"), nullable=True)
    monitoring_datetime = Column(DateTime(timezone=True), nullable=False, index=True)
    recorded_value = Column(Numeric(14, 4), nullable=True)
    recorded_text = Column(String(200), nullable=True)
    is_within_limits = Column(Boolean, nullable=False)
    is_violation = Column(Boolean, default=False, nullable=False)
    deviation_amount = Column(Numeric(14, 4), nullable=True)
    recorded_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    corrective_action_taken = Column(Text, nullable=True)
    corrective_action_id = Column(UUID(as_uuid=True), ForeignKey("corrective_actions.id", ondelete="SET NULL"), nullable=True)
    process_blocked = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)

    ccp = relationship("CriticalControlPoint", back_populates="monitoring_logs")
    production_order = relationship("ProductionOrder", foreign_keys=[production_order_id])
    lot = relationship("Lot", foreign_keys=[lot_id])
    recorded_by = relationship("User", foreign_keys=[recorded_by_id])


# ── Deviation & Corrective Action ─────────────────────────────────────────────

class CorrectiveAction(Base, TimestampMixin):
    """Corrective action record triggered by QC/CCP failure or deviation."""
    __tablename__ = "corrective_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ca_no = Column(String(50), nullable=False, unique=True, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(CorrectiveActionStatus), nullable=False, default=CorrectiveActionStatus.OPEN)
    severity = Column(Enum(RiskLevel), nullable=False, default=RiskLevel.MEDIUM)
    trigger_type = Column(String(50), nullable=True)  # QC_FAILURE/CCP_VIOLATION/DEVIATION/COMPLAINT
    trigger_id = Column(UUID(as_uuid=True), nullable=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="SET NULL"), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    assigned_to_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    due_date = Column(Date, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verified_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    root_cause_analysis = Column(Text, nullable=True)
    effectiveness_check = Column(Text, nullable=True)
    preventive_measures = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    steps = relationship("CorrectiveActionStep", back_populates="corrective_action",
                         cascade="all, delete-orphan", order_by="CorrectiveActionStep.step_no")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    verified_by = relationship("User", foreign_keys=[verified_by_id])
    production_order = relationship("ProductionOrder", foreign_keys=[production_order_id])
    lot = relationship("Lot", foreign_keys=[lot_id])
    product = relationship("Product", foreign_keys=[product_id])
    material = relationship("Material", foreign_keys=[material_id])


class CorrectiveActionStep(Base, TimestampMixin):
    """Step within a corrective action plan."""
    __tablename__ = "corrective_action_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    corrective_action_id = Column(UUID(as_uuid=True), ForeignKey("corrective_actions.id", ondelete="CASCADE"), nullable=False)
    step_no = Column(Integer, nullable=False)
    step_description = Column(Text, nullable=False)
    assigned_to_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    due_date = Column(Date, nullable=True)
    is_completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completion_notes = Column(Text, nullable=True)

    corrective_action = relationship("CorrectiveAction", back_populates="steps")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])


class QCDeviation(Base, TimestampMixin):
    """Deviation record triggered by QC failure or out-of-spec result."""
    __tablename__ = "qc_deviations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deviation_no = Column(String(50), nullable=False, unique=True, index=True)
    inspection_id = Column(UUID(as_uuid=True), ForeignKey("qc_inspections.id", ondelete="SET NULL"), nullable=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="SET NULL"), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    deviation_type = Column(String(100), nullable=False)
    severity = Column(Enum(RiskLevel), nullable=False, default=RiskLevel.MEDIUM)
    status = Column(Enum(DeviationStatus), nullable=False, default=DeviationStatus.OPEN)
    description = Column(Text, nullable=False)
    root_cause = Column(Text, nullable=True)
    immediate_action = Column(Text, nullable=True)
    affected_quantity = Column(Numeric(14, 3), nullable=True)
    affected_uom = Column(String(20), nullable=True)
    reported_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_to_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    due_date = Column(Date, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    corrective_action_id = Column(UUID(as_uuid=True), ForeignKey("corrective_actions.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)

    inspection = relationship("QCInspection", foreign_keys=[inspection_id])
    production_order = relationship("ProductionOrder", foreign_keys=[production_order_id])
    lot = relationship("Lot", foreign_keys=[lot_id])
    product = relationship("Product", foreign_keys=[product_id])
    material = relationship("Material", foreign_keys=[material_id])
    reported_by = relationship("User", foreign_keys=[reported_by_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])
    corrective_action = relationship("CorrectiveAction", foreign_keys=[corrective_action_id])


# ── Lot Quality Status ────────────────────────────────────────────────────────

class LotQualityStatus(Base, TimestampMixin):
    """Per-lot quality and release status — gateway before FEFO and shipment."""
    __tablename__ = "lot_quality_statuses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    qc_status = Column(String(50), nullable=False, default="PENDING")
    release_status = Column(Enum(ReleaseStatus), nullable=False, default=ReleaseStatus.UNRELEASED)
    hold_flag = Column(Boolean, default=False, nullable=False)
    quarantine_flag = Column(Boolean, default=False, nullable=False)
    quarantine_location = Column(String(200), nullable=True)
    hold_reason = Column(Text, nullable=True)
    last_inspection_id = Column(UUID(as_uuid=True), ForeignKey("qc_inspections.id", ondelete="SET NULL"), nullable=True)
    released_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    released_at = Column(DateTime(timezone=True), nullable=True)
    release_notes = Column(Text, nullable=True)
    fefo_eligible = Column(Boolean, default=False, nullable=False)
    shipment_eligible = Column(Boolean, default=False, nullable=False)
    allergen_cleared = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)

    lot = relationship("Lot", foreign_keys=[lot_id])
    last_inspection = relationship("QCInspection", foreign_keys=[last_inspection_id])
    released_by = relationship("User", foreign_keys=[released_by_id])


# ── Allergen Validation ───────────────────────────────────────────────────────

class AllergenValidationRecord(Base, TimestampMixin):
    """Allergen cleaning validation record between production runs."""
    __tablename__ = "allergen_validation_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    validation_no = Column(String(50), nullable=False, unique=True, index=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True)
    previous_product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    current_product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    allergens_present = Column(String(500), nullable=True)
    cleaning_method = Column(Text, nullable=True)
    cleaning_completed_at = Column(DateTime(timezone=True), nullable=True)
    validation_passed = Column(Boolean, nullable=True)
    validated_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    swab_test_result = Column(String(100), nullable=True)
    evidence_notes = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    production_order = relationship("ProductionOrder", foreign_keys=[production_order_id])
    previous_product = relationship("Product", foreign_keys=[previous_product_id])
    current_product = relationship("Product", foreign_keys=[current_product_id])
    validated_by = relationship("User", foreign_keys=[validated_by_id])


# ── QMS AI Recommendations ────────────────────────────────────────────────────

class QMSAIRecommendation(Base, TimestampMixin):
    """AI agent recommendations for quality management and HACCP."""
    __tablename__ = "qms_ai_recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type = Column(Enum(QMSAIAgentType), nullable=False, index=True)
    status = Column(Enum(QMSAIRecStatus), nullable=False, default=QMSAIRecStatus.PENDING)

    inspection_id = Column(UUID(as_uuid=True), ForeignKey("qc_inspections.id", ondelete="SET NULL"), nullable=True)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="SET NULL"), nullable=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True)
    ccp_id = Column(UUID(as_uuid=True), ForeignKey("critical_control_points.id", ondelete="SET NULL"), nullable=True)
    deviation_id = Column(UUID(as_uuid=True), ForeignKey("qc_deviations.id", ondelete="SET NULL"), nullable=True)

    title = Column(String(300), nullable=False)
    explanation = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)
    risk_level = Column(Enum(RiskLevel), nullable=True)
    confidence_score = Column(Numeric(5, 2), nullable=True)
    priority_score = Column(Integer, nullable=True)

    reviewed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_note = Column(Text, nullable=True)

    payload = Column(JSON, nullable=True)

    lot = relationship("Lot", foreign_keys=[lot_id])
    ccp = relationship("CriticalControlPoint", foreign_keys=[ccp_id])
    deviation = relationship("QCDeviation", foreign_keys=[deviation_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
