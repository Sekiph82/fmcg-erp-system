"""Pydantic schemas for the Quality Management System (QMS) + HACCP module."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.quality import (
    QCType, QCStatus, QCDecision, ParameterType,
    SamplingMethod, HazardType, RiskLevel,
    DeviationStatus, CorrectiveActionStatus, ReleaseStatus,
    QMSAIAgentType, QMSAIRecStatus,
    AuditStandard, AuditType, AuditResult,
)


# ── QC Template ───────────────────────────────────────────────────────────────

class QCTemplateParameterBase(BaseModel):
    parameter_id: Optional[uuid.UUID] = None
    parameter_name: str
    parameter_type: ParameterType = ParameterType.NUMERIC
    unit: Optional[str] = None
    target_value: Optional[str] = None
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None
    is_critical: bool = False
    is_ccp_parameter: bool = False
    display_order: int = 0


class QCTemplateParameterCreate(QCTemplateParameterBase):
    pass


class QCTemplateParameterRead(QCTemplateParameterBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    template_id: uuid.UUID
    created_at: datetime


class QCTemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    qc_type: QCType
    qc_sub_type: Optional[str] = None
    product_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    product_category: Optional[str] = None
    sampling_method: SamplingMethod = SamplingMethod.FIXED
    sample_size: Optional[Decimal] = None
    sample_percentage: Optional[Decimal] = None
    sampling_frequency: Optional[int] = None
    sampling_interval_hours: Optional[Decimal] = None
    is_ccp_template: bool = False
    is_mandatory: bool = True
    blocks_progression: bool = True
    release_required: bool = True
    is_active: bool = True


class QCTemplateCreate(QCTemplateBase):
    parameters: List[QCTemplateParameterCreate] = []


class QCTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_mandatory: Optional[bool] = None
    blocks_progression: Optional[bool] = None
    release_required: Optional[bool] = None
    sampling_method: Optional[SamplingMethod] = None
    sample_size: Optional[Decimal] = None
    sample_percentage: Optional[Decimal] = None
    sampling_frequency: Optional[int] = None
    sampling_interval_hours: Optional[Decimal] = None
    is_active: Optional[bool] = None


class QCTemplateRead(QCTemplateBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    parameters: List[QCTemplateParameterRead] = []
    product_name: Optional[str] = None
    material_name: Optional[str] = None


# ── Hazard Analysis ───────────────────────────────────────────────────────────

class HazardAnalysisBase(BaseModel):
    process_step: str
    hazard_type: HazardType
    hazard_description: str
    risk_level: RiskLevel = RiskLevel.MEDIUM
    likelihood_score: Optional[int] = Field(None, ge=1, le=5)
    severity_score: Optional[int] = Field(None, ge=1, le=5)
    control_measure: str
    is_ccp: bool = False
    ccp_id: Optional[uuid.UUID] = None
    product_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    review_date: Optional[date] = None
    notes: Optional[str] = None
    is_active: bool = True


class HazardAnalysisCreate(HazardAnalysisBase):
    pass


class HazardAnalysisUpdate(BaseModel):
    hazard_description: Optional[str] = None
    risk_level: Optional[RiskLevel] = None
    likelihood_score: Optional[int] = None
    severity_score: Optional[int] = None
    control_measure: Optional[str] = None
    is_ccp: Optional[bool] = None
    ccp_id: Optional[uuid.UUID] = None
    review_date: Optional[date] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class HazardAnalysisRead(HazardAnalysisBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    hazard_no: str
    risk_score: Optional[int] = None
    created_at: datetime
    product_name: Optional[str] = None
    material_name: Optional[str] = None


# ── Critical Control Point ────────────────────────────────────────────────────

class CCPBase(BaseModel):
    ccp_name: str
    process_step: str
    hazard_type: HazardType
    parameter_name: str
    parameter_unit: Optional[str] = None
    critical_limit_min: Optional[Decimal] = None
    critical_limit_max: Optional[Decimal] = None
    critical_limit_description: Optional[str] = None
    monitoring_method: str
    monitoring_frequency: str
    monitoring_frequency_hours: Optional[Decimal] = None
    corrective_action_description: str
    responsible_role: Optional[str] = None
    responsible_user_id: Optional[uuid.UUID] = None
    verification_method: Optional[str] = None
    verification_frequency: Optional[str] = None
    record_keeping: Optional[str] = None
    product_id: Optional[uuid.UUID] = None
    allergen_related: bool = False
    cleaning_required: bool = False
    is_active: bool = True


class CCPCreate(CCPBase):
    pass


class CCPUpdate(BaseModel):
    ccp_name: Optional[str] = None
    critical_limit_min: Optional[Decimal] = None
    critical_limit_max: Optional[Decimal] = None
    critical_limit_description: Optional[str] = None
    monitoring_method: Optional[str] = None
    monitoring_frequency: Optional[str] = None
    corrective_action_description: Optional[str] = None
    responsible_user_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None


class CCPRead(CCPBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    ccp_no: str
    created_at: datetime
    product_name: Optional[str] = None
    recent_violations: int = 0
    last_monitored_at: Optional[datetime] = None


# ── CCP Monitoring Log ────────────────────────────────────────────────────────

class CCPMonitoringCreate(BaseModel):
    ccp_id: uuid.UUID
    production_order_id: Optional[uuid.UUID] = None
    work_order_id: Optional[uuid.UUID] = None
    lot_id: Optional[uuid.UUID] = None
    monitoring_datetime: datetime
    recorded_value: Optional[Decimal] = None
    recorded_text: Optional[str] = None
    corrective_action_taken: Optional[str] = None
    notes: Optional[str] = None


class CCPMonitoringRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    ccp_id: uuid.UUID
    production_order_id: Optional[uuid.UUID] = None
    lot_id: Optional[uuid.UUID] = None
    monitoring_datetime: datetime
    recorded_value: Optional[Decimal] = None
    recorded_text: Optional[str] = None
    is_within_limits: bool
    is_violation: bool
    deviation_amount: Optional[Decimal] = None
    recorded_by_id: Optional[uuid.UUID] = None
    corrective_action_taken: Optional[str] = None
    corrective_action_id: Optional[uuid.UUID] = None
    process_blocked: bool
    notes: Optional[str] = None
    created_at: datetime
    ccp_name: Optional[str] = None
    recorded_by_name: Optional[str] = None


# ── Corrective Action ─────────────────────────────────────────────────────────

class CorrectiveActionStepBase(BaseModel):
    step_no: int
    step_description: str
    assigned_to_id: Optional[uuid.UUID] = None
    due_date: Optional[date] = None


class CorrectiveActionStepCreate(CorrectiveActionStepBase):
    pass


class CorrectiveActionStepRead(CorrectiveActionStepBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    corrective_action_id: uuid.UUID
    is_completed: bool
    completed_at: Optional[datetime] = None
    completion_notes: Optional[str] = None
    created_at: datetime


class CorrectiveActionBase(BaseModel):
    title: str
    description: str
    severity: RiskLevel = RiskLevel.MEDIUM
    trigger_type: Optional[str] = None
    trigger_id: Optional[uuid.UUID] = None
    production_order_id: Optional[uuid.UUID] = None
    lot_id: Optional[uuid.UUID] = None
    product_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    assigned_to_id: Optional[uuid.UUID] = None
    due_date: Optional[date] = None
    root_cause_analysis: Optional[str] = None
    preventive_measures: Optional[str] = None
    notes: Optional[str] = None


class CorrectiveActionCreate(CorrectiveActionBase):
    steps: List[CorrectiveActionStepCreate] = []


class CorrectiveActionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CorrectiveActionStatus] = None
    assigned_to_id: Optional[uuid.UUID] = None
    due_date: Optional[date] = None
    root_cause_analysis: Optional[str] = None
    effectiveness_check: Optional[str] = None
    preventive_measures: Optional[str] = None
    pdca_closed_at: Optional[datetime] = None
    notes: Optional[str] = None


class CorrectiveActionRead(CorrectiveActionBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    ca_no: str
    status: CorrectiveActionStatus
    steps: List[CorrectiveActionStepRead] = []
    completed_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    pdca_closed_at: Optional[datetime] = None
    created_at: datetime
    assigned_to_name: Optional[str] = None
    product_name: Optional[str] = None
    steps_total: int = 0
    steps_completed: int = 0


# ── QC Deviation ──────────────────────────────────────────────────────────────

class QCDeviationBase(BaseModel):
    inspection_id: Optional[uuid.UUID] = None
    production_order_id: Optional[uuid.UUID] = None
    lot_id: Optional[uuid.UUID] = None
    product_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    deviation_type: str
    severity: RiskLevel = RiskLevel.MEDIUM
    description: str
    root_cause: Optional[str] = None
    immediate_action: Optional[str] = None
    affected_quantity: Optional[Decimal] = None
    affected_uom: Optional[str] = None
    assigned_to_id: Optional[uuid.UUID] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None


class QCDeviationCreate(QCDeviationBase):
    pass


class QCDeviationUpdate(BaseModel):
    status: Optional[DeviationStatus] = None
    root_cause: Optional[str] = None
    immediate_action: Optional[str] = None
    assigned_to_id: Optional[uuid.UUID] = None
    due_date: Optional[date] = None
    corrective_action_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class QCDeviationRead(QCDeviationBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    deviation_no: str
    status: DeviationStatus
    corrective_action_id: Optional[uuid.UUID] = None
    reported_by_id: Optional[uuid.UUID] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    product_name: Optional[str] = None
    material_name: Optional[str] = None
    assigned_to_name: Optional[str] = None


# ── Lot Quality Status ────────────────────────────────────────────────────────

class LotQualityStatusRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    lot_id: uuid.UUID
    qc_status: str
    release_status: ReleaseStatus
    hold_flag: bool
    quarantine_flag: bool
    quarantine_location: Optional[str] = None
    hold_reason: Optional[str] = None
    last_inspection_id: Optional[uuid.UUID] = None
    released_by_id: Optional[uuid.UUID] = None
    released_at: Optional[datetime] = None
    release_notes: Optional[str] = None
    fefo_eligible: bool
    shipment_eligible: bool
    allergen_cleared: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class LotReleaseRequest(BaseModel):
    lot_id: uuid.UUID
    release_notes: Optional[str] = None
    override_reason: Optional[str] = None


class LotHoldRequest(BaseModel):
    lot_id: uuid.UUID
    hold_reason: str
    quarantine: bool = False
    quarantine_location: Optional[str] = None


# ── Allergen Validation ───────────────────────────────────────────────────────

class AllergenValidationCreate(BaseModel):
    production_order_id: Optional[uuid.UUID] = None
    previous_product_id: Optional[uuid.UUID] = None
    current_product_id: Optional[uuid.UUID] = None
    allergens_present: Optional[str] = None
    cleaning_method: Optional[str] = None
    cleaning_completed_at: Optional[datetime] = None
    validation_passed: Optional[bool] = None
    swab_test_result: Optional[str] = None
    evidence_notes: Optional[str] = None
    notes: Optional[str] = None


class AllergenValidationRead(AllergenValidationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    validation_no: str
    validated_by_id: Optional[uuid.UUID] = None
    created_at: datetime
    previous_product_name: Optional[str] = None
    current_product_name: Optional[str] = None


# ── QMS AI Recommendations ────────────────────────────────────────────────────

class QMSAIRecRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    agent_type: QMSAIAgentType
    status: QMSAIRecStatus
    lot_id: Optional[uuid.UUID] = None
    production_order_id: Optional[uuid.UUID] = None
    ccp_id: Optional[uuid.UUID] = None
    deviation_id: Optional[uuid.UUID] = None
    title: str
    explanation: str
    recommendation: str
    risk_level: Optional[RiskLevel] = None
    confidence_score: Optional[Decimal] = None
    priority_score: Optional[int] = None
    reviewed_by_id: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None
    review_note: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    created_at: datetime


class QMSAIRecReview(BaseModel):
    status: QMSAIRecStatus
    review_note: Optional[str] = None


# ── Dashboard ─────────────────────────────────────────────────────────────────

class QMSDashboard(BaseModel):
    total_inspections: int = 0
    pending_inspections: int = 0
    passed_today: int = 0
    failed_today: int = 0
    conditional_today: int = 0
    pass_rate_7d: float = 0.0
    open_deviations: int = 0
    critical_deviations: int = 0
    open_corrective_actions: int = 0
    overdue_corrective_actions: int = 0
    active_ccps: int = 0
    ccp_violations_7d: int = 0
    lots_on_hold: int = 0
    lots_quarantined: int = 0
    lots_pending_release: int = 0
    allergen_validations_pending: int = 0
    ai_recommendations_pending: int = 0


class QCGateCheck(BaseModel):
    lot_id: uuid.UUID
    stage: Optional[str] = None
    blocked: bool
    reason: Optional[str] = None
    inspection_id: Optional[uuid.UUID] = None
    inspection_no: Optional[str] = None
    inspection_status: Optional[str] = None


# ── Quality Audit Checklist ────────────────────────────────────────────────────

class AuditChecklistBase(BaseModel):
    standard: AuditStandard
    audit_type: AuditType = AuditType.INTERNAL
    audit_date: date
    scheduled_date: Optional[date] = None
    recurrence_days: Optional[int] = None
    conducted_by: Optional[str] = None
    lead_auditor: Optional[str] = None
    scope: Optional[str] = None
    items: Optional[Any] = None
    major_findings: Optional[str] = None
    minor_findings: Optional[str] = None
    recommendations: Optional[str] = None
    next_audit_date: Optional[date] = None
    notes: Optional[str] = None


class AuditChecklistCreate(AuditChecklistBase):
    pass


class AuditChecklistUpdate(BaseModel):
    audit_date: Optional[date] = None
    scheduled_date: Optional[date] = None
    recurrence_days: Optional[int] = None
    conducted_by: Optional[str] = None
    lead_auditor: Optional[str] = None
    scope: Optional[str] = None
    items: Optional[Any] = None
    result: Optional[AuditResult] = None
    major_findings: Optional[str] = None
    minor_findings: Optional[str] = None
    recommendations: Optional[str] = None
    next_audit_date: Optional[date] = None
    certificate_issued: Optional[bool] = None
    notes: Optional[str] = None


class AuditChecklistRead(AuditChecklistBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    audit_ref: str
    total_items: Optional[int] = None
    passed_items: Optional[int] = None
    score_pct: Optional[Decimal] = None
    result: AuditResult
    certificate_issued: bool
    created_at: datetime
