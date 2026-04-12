from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
import uuid

from pydantic import BaseModel, ConfigDict, computed_field

from app.models.quality import QCType, QCStatus, QCDecision, ParameterType


# ── QC Parameter ──────────────────────────────────────────────────────────────

class QCParameterCreate(BaseModel):
    name: str
    description: Optional[str] = None
    parameter_type: ParameterType = ParameterType.NUMERIC
    unit: Optional[str] = None
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None
    expected_value: Optional[str] = None
    is_critical: bool = False
    applicable_types: str = "ALL"


class QCParameterUpdate(BaseModel):
    description: Optional[str] = None
    unit: Optional[str] = None
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None
    expected_value: Optional[str] = None
    is_critical: Optional[bool] = None
    applicable_types: Optional[str] = None
    is_active: Optional[bool] = None


class QCParameterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: Optional[str]
    parameter_type: ParameterType
    unit: Optional[str]
    min_value: Optional[Decimal]
    max_value: Optional[Decimal]
    expected_value: Optional[str]
    is_critical: bool
    applicable_types: str
    is_active: bool


# ── Test Results ──────────────────────────────────────────────────────────────

class QCTestResultCreate(BaseModel):
    parameter_id: Optional[uuid.UUID] = None
    parameter_name: str
    parameter_type: ParameterType
    unit: Optional[str] = None
    numeric_value: Optional[Decimal] = None
    text_value: Optional[str] = None
    boolean_value: Optional[bool] = None
    min_spec: Optional[Decimal] = None
    max_spec: Optional[Decimal] = None
    expected_text: Optional[str] = None
    is_passed: Optional[bool] = None
    is_critical: bool = False
    notes: Optional[str] = None


class QCTestResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    inspection_id: uuid.UUID
    parameter_id: Optional[uuid.UUID]
    parameter_name: str
    parameter_type: ParameterType
    unit: Optional[str]
    numeric_value: Optional[Decimal]
    text_value: Optional[str]
    boolean_value: Optional[bool]
    min_spec: Optional[Decimal]
    max_spec: Optional[Decimal]
    expected_text: Optional[str]
    is_passed: Optional[bool]
    is_critical: bool
    tested_by_id: Optional[uuid.UUID]
    tested_by_name: Optional[str] = None
    notes: Optional[str]
    created_at: datetime

    @computed_field
    @property
    def display_value(self) -> str:
        if self.numeric_value is not None:
            return f"{self.numeric_value} {self.unit or ''}".strip()
        if self.text_value is not None:
            return self.text_value
        if self.boolean_value is not None:
            return "Yes" if self.boolean_value else "No"
        return "—"

    @computed_field
    @property
    def spec_range(self) -> Optional[str]:
        if self.min_spec is not None and self.max_spec is not None:
            return f"{self.min_spec} – {self.max_spec} {self.unit or ''}".strip()
        if self.min_spec is not None:
            return f"≥ {self.min_spec} {self.unit or ''}".strip()
        if self.max_spec is not None:
            return f"≤ {self.max_spec} {self.unit or ''}".strip()
        if self.expected_text:
            return self.expected_text
        return None


# ── QC Inspection ─────────────────────────────────────────────────────────────

class QCInspectionCreate(BaseModel):
    inspection_no: str
    qc_type: QCType
    grn_id: Optional[uuid.UUID] = None
    grn_line_id: Optional[uuid.UUID] = None
    production_order_id: Optional[uuid.UUID] = None
    lot_id: Optional[uuid.UUID] = None
    supplier_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    product_id: Optional[uuid.UUID] = None
    warehouse_id: Optional[uuid.UUID] = None
    lot_number: Optional[str] = None
    batch_no: Optional[str] = None
    sample_size: Optional[Decimal] = None
    sample_unit: Optional[str] = None
    inspection_date: date
    notes: Optional[str] = None


class QCInspectionUpdate(BaseModel):
    inspection_date: Optional[date] = None
    sample_size: Optional[Decimal] = None
    sample_unit: Optional[str] = None
    notes: Optional[str] = None


class QCDecisionRequest(BaseModel):
    decision: QCDecision
    decision_notes: Optional[str] = None
    rework_candidate: bool = False
    apply_quarantine: bool = False


class QCInspectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    inspection_no: str
    qc_type: QCType
    status: QCStatus
    grn_id: Optional[uuid.UUID]
    production_order_id: Optional[uuid.UUID]
    lot_id: Optional[uuid.UUID]
    supplier_id: Optional[uuid.UUID]
    supplier_name: Optional[str] = None
    material_id: Optional[uuid.UUID]
    material_name: Optional[str] = None
    material_code: Optional[str] = None
    product_id: Optional[uuid.UUID]
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    warehouse_id: Optional[uuid.UUID]
    lot_number: Optional[str]
    batch_no: Optional[str]
    sample_size: Optional[Decimal]
    sample_unit: Optional[str]
    inspection_date: date
    inspector_id: Optional[uuid.UUID]
    inspector_name: Optional[str] = None
    notes: Optional[str]
    decision: Optional[QCDecision]
    decided_by_id: Optional[uuid.UUID]
    decided_at: Optional[datetime]
    decision_notes: Optional[str]
    rework_candidate: bool
    quarantine_applied: bool
    created_at: datetime
    test_count: int = 0
    pass_count: int = 0
    fail_count: int = 0
    critical_fail: bool = False


class QCInspectionDetailRead(QCInspectionRead):
    test_results: List[QCTestResultRead] = []


# ── COA (Certificate of Analysis) ─────────────────────────────────────────────

class COATestLine(BaseModel):
    parameter_name: str
    unit: Optional[str]
    spec_range: Optional[str]
    result_value: str
    is_passed: Optional[bool]
    is_critical: bool


class COAReport(BaseModel):
    inspection_no: str
    qc_type: str
    inspection_date: date
    lot_number: Optional[str]
    batch_no: Optional[str]
    product_name: Optional[str]
    product_sku: Optional[str]
    material_name: Optional[str]
    supplier_name: Optional[str]
    inspector_name: Optional[str]
    decision: Optional[str]
    decision_notes: Optional[str]
    decided_at: Optional[datetime]
    overall_result: str   # PASS / FAIL / CONDITIONAL / PENDING
    test_lines: List[COATestLine]


# ── Stats / Reports ────────────────────────────────────────────────────────────

class QCStatsRow(BaseModel):
    period: str
    total_inspections: int
    passed: int
    failed: int
    conditional: int
    pass_rate: float


class RejectionSummaryRow(BaseModel):
    material_name: Optional[str]
    product_name: Optional[str]
    supplier_name: Optional[str]
    total_inspections: int
    total_rejected: int
    rejection_rate: float
    last_rejection_date: Optional[date]
