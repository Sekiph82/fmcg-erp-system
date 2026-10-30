from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional, List
import uuid

from pydantic import BaseModel, computed_field, ConfigDict, Field, field_validator, model_validator

from app.models.procurement import (
    PRStatus, POStatus, GRNStatus, ImportShipmentStatus, POPaymentStatus,
    RFQStatus, RFQResponseStatus, RFQInvitationStatus, RFQEvaluationDimension, RFQEvaluationStatus,
    RFQAwardStatus, RFQAwardApprovalStatus,
    BPAStatus, ProcurementApprovalDocumentType,
)
from app.models.finance import OperationalPostingStatus


class ProcurementScopeFields(BaseModel):
    company_id: Optional[uuid.UUID] = None
    branch_id: Optional[uuid.UUID] = None
    cost_center_id: Optional[uuid.UUID] = None
    department: Optional[str] = None


class ProcurementAccessHint(BaseModel):
    can_view: bool = True
    can_create: bool = False
    can_edit: bool = False
    can_delete: bool = False
    can_approve: bool = False
    can_receive: bool = False
    can_post: bool = False
    can_cancel: bool = False
    can_export: bool = False
    can_import: bool = False
    view_only: bool = False
    reason: Optional[str] = None


# ── PR Lines ───────────────────────────────────────────────────────────────────

class PRLineCreate(BaseModel):
    line_no: int
    material_id: Optional[uuid.UUID] = None
    product_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    quantity: Decimal
    unit: str = "KG"
    estimated_unit_cost: Optional[Decimal] = None
    preferred_supplier_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class PRLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    line_no: int
    material_id: Optional[uuid.UUID]
    material_name: Optional[str] = None
    material_code: Optional[str] = None
    product_id: Optional[uuid.UUID]
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    description: Optional[str]
    quantity: Decimal
    unit: str
    estimated_unit_cost: Optional[Decimal]
    preferred_supplier_id: Optional[uuid.UUID]
    preferred_supplier_name: Optional[str] = None
    notes: Optional[str]


# ── PR ─────────────────────────────────────────────────────────────────────────

class PRCreate(ProcurementScopeFields):
    pr_no: str
    department: Optional[str] = None
    required_date: date
    notes: Optional[str] = None
    lines: List[PRLineCreate] = []


class PRUpdate(ProcurementScopeFields):
    department: Optional[str] = None
    required_date: Optional[date] = None
    notes: Optional[str] = None


class PRRead(ProcurementScopeFields):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    pr_no: str
    requester_id: uuid.UUID
    requester_name: Optional[str] = None
    department: Optional[str]
    required_date: date
    notes: Optional[str]
    status: PRStatus
    approved_by_id: Optional[uuid.UUID]
    approved_at: Optional[datetime]
    rejection_reason: Optional[str]
    created_at: datetime
    line_count: int = 0
    access: Optional[ProcurementAccessHint] = None


class PRDetailRead(PRRead):
    lines: List[PRLineRead] = []


class ApprovePRRequest(BaseModel):
    approve: bool
    rejection_reason: Optional[str] = None


class ConvertPRToPORequest(BaseModel):
    po_no: str
    supplier_id: uuid.UUID
    order_date: date
    expected_delivery_date: date
    payment_terms: Optional[str] = None
    currency: str = "USD"
    exchange_rate: Decimal = Decimal("1.0")
    notes: Optional[str] = None
    # Optionally override unit prices per PR line
    line_prices: Optional[dict] = None  # {str(pr_line_id): unit_price}


# ── PO Lines ───────────────────────────────────────────────────────────────────

class POLineCreate(BaseModel):
    line_no: int
    material_id: Optional[uuid.UUID] = None
    product_id: Optional[uuid.UUID] = None
    pr_line_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    ordered_quantity: Decimal
    unit: str = "KG"
    unit_price: Decimal = Decimal("0")
    tax_rate: Decimal = Decimal("0")


class POLineRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    line_no: int
    material_id: Optional[uuid.UUID]
    material_name: Optional[str] = None
    material_code: Optional[str] = None
    product_id: Optional[uuid.UUID]
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    pr_line_id: Optional[uuid.UUID]
    description: Optional[str]
    ordered_quantity: Decimal
    unit: str
    unit_price: Decimal
    tax_rate: Decimal
    received_quantity: Decimal

    @computed_field
    @property
    def line_total(self) -> Decimal:
        return (self.ordered_quantity * self.unit_price * (1 + self.tax_rate)).quantize(Decimal("0.01"))

    @computed_field
    @property
    def pending_quantity(self) -> Decimal:
        return max(self.ordered_quantity - self.received_quantity, Decimal("0"))


# ── PO ─────────────────────────────────────────────────────────────────────────

class POCreate(ProcurementScopeFields):
    po_no: str
    supplier_id: uuid.UUID
    order_date: date
    expected_delivery_date: date
    payment_terms: Optional[str] = None
    currency: str = "USD"
    exchange_rate: Decimal = Decimal("1.0")
    notes: Optional[str] = None
    lines: List[POLineCreate] = []


class POUpdate(ProcurementScopeFields):
    expected_delivery_date: Optional[date] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None


class PORead(ProcurementScopeFields):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    po_no: str
    supplier_id: uuid.UUID
    supplier_name: Optional[str] = None
    pr_id: Optional[uuid.UUID]
    pr_no: Optional[str] = None
    order_date: date
    expected_delivery_date: date
    payment_terms: Optional[str]
    currency: str
    exchange_rate: Decimal
    status: POStatus
    notes: Optional[str]
    approved_by_id: Optional[uuid.UUID]
    approved_at: Optional[datetime]
    created_at: datetime
    total_value: Optional[Decimal] = None
    days_until_delivery: Optional[int] = None
    payment_status: POPaymentStatus = POPaymentStatus.PENDING
    payment_method: Optional[str] = None
    mpesa_reference: Optional[str] = None
    paid_amount: Optional[Decimal] = None
    access: Optional[ProcurementAccessHint] = None


class PODetailRead(PORead):
    lines: List[POLineRead] = []


# ── GRN ────────────────────────────────────────────────────────────────────────

class GRNLineCreate(BaseModel):
    po_line_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    product_id: Optional[uuid.UUID] = None
    received_quantity: Decimal
    accepted_quantity: Decimal
    accepted_volume_m3: Optional[Decimal] = Field(
        default=None, gt=0, max_digits=14, decimal_places=6, allow_inf_nan=False
    )
    rejected_quantity: Decimal = Decimal("0")
    unit: str = "KG"
    lot_number: Optional[str] = None
    expiry_date: Optional[date] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_accepted_volume(self):
        if self.accepted_volume_m3 is not None and self.accepted_quantity <= 0:
            raise ValueError("Accepted volume can only be recorded for a line with accepted quantity")
        return self


class GRNCreate(ProcurementScopeFields):
    grn_no: str
    po_id: uuid.UUID
    received_date: date
    warehouse_id: uuid.UUID
    notes: Optional[str] = None
    lines: List[GRNLineCreate]


class GRNLineRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    po_line_id: Optional[uuid.UUID]
    material_id: Optional[uuid.UUID]
    material_name: Optional[str] = None
    product_id: Optional[uuid.UUID]
    product_name: Optional[str] = None
    received_quantity: Decimal
    accepted_quantity: Decimal
    accepted_volume_m3: Optional[Decimal] = None
    rejected_quantity: Decimal
    unit: str
    lot_number: Optional[str]
    expiry_date: Optional[date]
    notes: Optional[str]
    stock_movement_id: Optional[uuid.UUID]
    posting_batch_id: Optional[uuid.UUID] = None
    journal_entry_id: Optional[uuid.UUID] = None
    accounting_status: Optional[OperationalPostingStatus] = None
    posting_error: Optional[str] = None


class GRNRead(ProcurementScopeFields):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    grn_no: str
    po_id: uuid.UUID
    po_no: Optional[str] = None
    received_date: date
    received_by_id: Optional[uuid.UUID]
    warehouse_id: uuid.UUID
    warehouse_name: Optional[str] = None
    notes: Optional[str]
    status: GRNStatus
    valuation_status: Optional[str] = None
    created_at: datetime
    access: Optional[ProcurementAccessHint] = None


class GRNDetailRead(GRNRead):
    lines: List[GRNLineRead] = []


# ── Import Shipment ────────────────────────────────────────────────────────────

class ImportShipmentCreate(ProcurementScopeFields):
    shipment_no: str
    po_id: uuid.UUID
    bl_number: Optional[str] = None
    vessel_name: Optional[str] = None
    port_of_loading: Optional[str] = None
    port_of_discharge: Optional[str] = None
    eta: Optional[date] = None
    customs_ref: Optional[str] = None
    landed_cost_freight: Optional[Decimal] = None
    landed_cost_insurance: Optional[Decimal] = None
    landed_cost_duties: Optional[Decimal] = None
    landed_cost_other: Optional[Decimal] = None
    notes: Optional[str] = None


class ImportShipmentUpdate(ProcurementScopeFields):
    bl_number: Optional[str] = None
    vessel_name: Optional[str] = None
    eta: Optional[date] = None
    ata: Optional[date] = None
    customs_ref: Optional[str] = None
    customs_cleared_at: Optional[datetime] = None
    landed_cost_freight: Optional[Decimal] = None
    landed_cost_insurance: Optional[Decimal] = None
    landed_cost_duties: Optional[Decimal] = None
    landed_cost_other: Optional[Decimal] = None
    status: Optional[ImportShipmentStatus] = None
    notes: Optional[str] = None


class ImportShipmentRead(ProcurementScopeFields):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    shipment_no: str
    po_id: uuid.UUID
    po_no: Optional[str] = None
    supplier_name: Optional[str] = None
    bl_number: Optional[str]
    vessel_name: Optional[str]
    port_of_loading: Optional[str]
    port_of_discharge: Optional[str]
    eta: Optional[date]
    ata: Optional[date]
    customs_ref: Optional[str]
    customs_cleared_at: Optional[datetime]
    landed_cost_freight: Optional[Decimal]
    landed_cost_insurance: Optional[Decimal]
    landed_cost_duties: Optional[Decimal]
    landed_cost_other: Optional[Decimal]
    status: ImportShipmentStatus
    notes: Optional[str]
    created_at: datetime
    access: Optional[ProcurementAccessHint] = None

    @computed_field
    @property
    def total_landed_cost(self) -> Decimal:
        total = Decimal("0")
        for v in [self.landed_cost_freight, self.landed_cost_insurance,
                  self.landed_cost_duties, self.landed_cost_other]:
            if v is not None:
                total += v
        return total


# ── Supplier Evaluation ────────────────────────────────────────────────────────

class SupplierEvaluationCreate(ProcurementScopeFields):
    supplier_id: uuid.UUID
    evaluation_date: date
    po_id: Optional[uuid.UUID] = None
    on_time_delivery_score: Decimal
    quality_score: Decimal
    price_competitiveness_score: Decimal
    responsiveness_score: Decimal
    notes: Optional[str] = None


class SupplierEvaluationRead(ProcurementScopeFields):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    supplier_id: uuid.UUID
    evaluation_date: date
    po_id: Optional[uuid.UUID]
    po_no: Optional[str] = None
    on_time_delivery_score: Decimal
    quality_score: Decimal
    price_competitiveness_score: Decimal
    responsiveness_score: Decimal
    overall_score: Decimal
    evaluator_id: Optional[uuid.UUID]
    notes: Optional[str]
    created_at: datetime
    access: Optional[ProcurementAccessHint] = None


class SupplierDashboardRow(ProcurementScopeFields):
    supplier_id: uuid.UUID
    supplier_name: str
    supplier_code: str
    is_preferred: bool
    lead_time_days: int
    performance_score: Optional[Decimal]
    compliance_notes: Optional[str]
    total_pos: int
    open_pos: int
    overdue_pos: int
    avg_on_time_delivery: Optional[Decimal]
    avg_quality: Optional[Decimal]
    avg_overall: Optional[Decimal]
    last_evaluation_date: Optional[date]
    access: Optional[ProcurementAccessHint] = None


# ── Delivery Planning ─────────────────────────────────────────────────────────

class InboundScheduleRow(BaseModel):
    po_id: uuid.UUID
    po_no: str
    supplier_name: str
    expected_delivery_date: date
    days_until_delivery: int
    status: POStatus
    total_value: Optional[Decimal]
    is_overdue: bool
    has_shipment: bool
    shipment_eta: Optional[date]


class DeliveryAlertRow(BaseModel):
    alert_type: str   # OVERDUE | APPROACHING | NO_SHIPMENT
    po_id: uuid.UUID
    po_no: str
    supplier_name: str
    expected_delivery_date: date
    days_delta: int
    message: str


# ── Supplier Payments ─────────────────────────────────────────────────────────

class SupplierPaymentCreate(ProcurementScopeFields):
    payment_date: date
    amount: Decimal
    method: str = "bank"        # bank | cash | mpesa
    reference: Optional[str] = None
    notes: Optional[str] = None


class SupplierPaymentRead(ProcurementScopeFields):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    po_id: uuid.UUID
    supplier_id: uuid.UUID
    payment_date: date
    amount: Decimal
    method: str
    reference: Optional[str]
    notes: Optional[str]
    created_at: datetime
    access: Optional[ProcurementAccessHint] = None


# ── RFQ ───────────────────────────────────────────────────────────────────────

def _validate_rfq_quantity(value: Decimal) -> None:
    if not value.is_finite() or value <= 0:
        raise ValueError("quantity must be finite and greater than zero")
    if value >= Decimal("100000000000") or value.quantize(Decimal("0.001")) != value:
        raise ValueError("quantity must fit the stored NUMERIC(14, 3) precision and scale")

class RFQLineCreate(BaseModel):
    line_no: int = Field(gt=0)
    material_id: Optional[uuid.UUID] = None
    product_id: Optional[uuid.UUID] = None
    description: Optional[str] = Field(default=None, max_length=500)
    quantity: Decimal = Field(gt=0)
    unit: str = Field(default="KG", min_length=1, max_length=20)
    required_by: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("quantity")
    @classmethod
    def require_finite_positive_quantity(cls, value: Decimal) -> Decimal:
        _validate_rfq_quantity(value)
        return value

    @model_validator(mode="after")
    def require_requirement_identity(self):
        if not any((self.material_id, self.product_id, self.description and self.description.strip())):
            raise ValueError("a sourcing line requires a material, product, or description")
        if not self.unit.strip():
            raise ValueError("unit cannot be blank")
        return self


class RFQLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    line_no: int
    material_id: Optional[uuid.UUID]
    product_id: Optional[uuid.UUID]
    description: Optional[str]
    quantity: Decimal
    unit: str
    required_by: Optional[date]
    notes: Optional[str]

class RFQResponseCreate(BaseModel):
    supplier_id: uuid.UUID
    quoted_unit_price: Optional[Decimal] = Field(default=None, gt=0)
    quoted_currency: str = "KES"
    line_quotes: List["RFQResponseLineQuoteCreate"] = Field(default_factory=list, max_length=100)
    lead_time_days: Optional[int] = Field(default=None, ge=0)
    valid_until: Optional[date] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("quoted_unit_price")
    @classmethod
    def quote_price_must_be_finite_and_representable(cls, value: Optional[Decimal]):
        if value is not None:
            try:
                quantized = value.quantize(Decimal("0.0001"))
            except InvalidOperation as exc:
                raise ValueError("quoted_unit_price must fit a finite positive NUMERIC(14, 4) value") from exc
            if not value.is_finite() or value <= 0 or value >= Decimal("10000000000") or quantized != value:
                raise ValueError("quoted_unit_price must fit a finite positive NUMERIC(14, 4) value")
        return value

    @field_validator("quoted_currency")
    @classmethod
    def quote_currency_must_be_iso_code(cls, value: str):
        normalized = value.strip().upper()
        if len(normalized) != 3 or any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" for character in normalized):
            raise ValueError("quoted_currency must be a three-letter currency code")
        return normalized

    @model_validator(mode="after")
    def itemized_quote_is_exclusive(self):
        if self.line_quotes and self.quoted_unit_price is not None:
            raise ValueError("Use either one single-item quote or itemized line quotes, not both.")
        if self.line_quotes:
            line_ids = [item.rfq_line_id for item in self.line_quotes]
            if len(line_ids) != len(set(line_ids)):
                raise ValueError("each RFQ line may be quoted only once")
            if len({item.quoted_currency for item in self.line_quotes}) != 1:
                raise ValueError("all line quotes in one supplier response must use the same currency")
        return self


class RFQResponseLineQuoteCreate(BaseModel):
    rfq_line_id: uuid.UUID
    quoted_unit_price: Decimal = Field(gt=0)
    quoted_currency: str = "KES"

    @field_validator("quoted_unit_price")
    @classmethod
    def line_quote_price_must_be_finite_and_representable(cls, value: Decimal) -> Decimal:
        try:
            quantized = value.quantize(Decimal("0.0001"))
        except InvalidOperation as exc:
            raise ValueError("line quote must fit a finite positive NUMERIC(14, 4) value") from exc
        if not value.is_finite() or value <= 0 or value >= Decimal("10000000000") or quantized != value:
            raise ValueError("line quote must fit a finite positive NUMERIC(14, 4) value")
        return value

    @field_validator("quoted_currency")
    @classmethod
    def line_quote_currency_must_be_iso_code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 3 or any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" for character in normalized):
            raise ValueError("line quote currency must be a three-letter code")
        return normalized


class RFQResponseLineQuoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    rfq_line_id: uuid.UUID
    quoted_unit_price: Decimal
    quoted_currency: str


RFQResponseCreate.model_rebuild()


class RFQResponseRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    rfq_id: uuid.UUID
    supplier_id: uuid.UUID
    supplier_name: Optional[str] = None
    quoted_unit_price: Optional[Decimal]
    quoted_currency: str
    line_quotes: List[RFQResponseLineQuoteRead] = Field(default_factory=list)
    lead_time_days: Optional[int]
    valid_until: Optional[date]
    payment_terms: Optional[str]
    notes: Optional[str]
    status: RFQResponseStatus
    invitation_status: RFQInvitationStatus
    invitation_issued_at: Optional[datetime]
    invitation_issued_by_id: Optional[uuid.UUID]
    submitted_at: Optional[datetime]
    submitted_by_id: Optional[uuid.UUID]
    evaluation_status: RFQEvaluationStatus
    score: Optional[Decimal]
    evaluations: List["RFQResponseEvaluationRead"] = Field(default_factory=list)
    evaluation_history: List["RFQResponseEvaluationRead"] = Field(default_factory=list)
    created_at: datetime


class RFQCreate(ProcurementScopeFields):
    rfq_no: str
    title: str
    pr_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    product_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    quantity: Optional[Decimal] = Field(default=None, gt=0)
    unit: str = "KG"
    required_by: Optional[date] = None
    response_deadline: Optional[date] = None
    notes: Optional[str] = None
    supplier_ids: List[uuid.UUID] = Field(default_factory=list)
    lines: List[RFQLineCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_legacy_item_or_sourcing_lines(self):
        if self.lines and self.quantity is not None:
            raise ValueError("Provide either the legacy single-item quantity or sourcing event lines, not both.")
        if not self.lines and self.quantity is None:
            raise ValueError("A single-item RFQ requires quantity; a multi-item event requires at least one line.")
        if self.quantity is not None:
            _validate_rfq_quantity(self.quantity)
        if not self.unit.strip():
            raise ValueError("unit cannot be blank")
        if self.lines:
            line_numbers = [line.line_no for line in self.lines]
            if len(set(line_numbers)) != len(line_numbers):
                raise ValueError("sourcing event line numbers must be unique")
        if len(set(self.supplier_ids)) != len(self.supplier_ids):
            raise ValueError("supplier invitations must be unique within an RFQ")
        return self


class RFQUpdate(ProcurementScopeFields):
    title: Optional[str] = None
    description: Optional[str] = None
    response_deadline: Optional[date] = None
    required_by: Optional[date] = None
    notes: Optional[str] = None
    status: Optional[RFQStatus] = None
    awarded_supplier_id: Optional[uuid.UUID] = None


class RFQRead(ProcurementScopeFields):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    rfq_no: str
    pr_id: Optional[uuid.UUID]
    title: str
    material_id: Optional[uuid.UUID]
    product_id: Optional[uuid.UUID]
    description: Optional[str]
    quantity: Optional[Decimal]
    unit: str
    required_by: Optional[date]
    response_deadline: Optional[date]
    status: RFQStatus
    awarded_supplier_id: Optional[uuid.UUID]
    awarded_supplier_name: Optional[str] = None
    notes: Optional[str]
    created_at: datetime
    response_count: int = 0
    invited_count: int = 0
    line_count: int = 0
    access: Optional[ProcurementAccessHint] = None


class RFQEvaluationCriterionCreate(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=200)
    dimension: RFQEvaluationDimension
    weight_percent: Decimal = Field(gt=0, le=100)
    is_mandatory: bool = False

    @field_validator("code")
    @classmethod
    def normalize_criterion_code(cls, value: str) -> str:
        normalized = value.strip().upper().replace(" ", "_")
        if not normalized.replace("_", "").isalnum():
            raise ValueError("criterion code may contain only letters, numbers, and underscores")
        return normalized

    @field_validator("name")
    @classmethod
    def trim_criterion_name(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("criterion name must contain at least two characters")
        return normalized

    @field_validator("weight_percent")
    @classmethod
    def validate_weight_precision(cls, value: Decimal) -> Decimal:
        try:
            quantized = value.quantize(Decimal("0.01"))
        except InvalidOperation as exc:
            raise ValueError("weight_percent must fit NUMERIC(5, 2)") from exc
        if not value.is_finite() or value <= 0 or value > 100 or quantized != value:
            raise ValueError("weight_percent must be finite, positive, and have at most two decimal places")
        return value


class RFQEvaluationMatrixCreate(BaseModel):
    criteria: List[RFQEvaluationCriterionCreate] = Field(min_length=2, max_length=30)

    @model_validator(mode="after")
    def validate_matrix(self):
        codes = [item.code for item in self.criteria]
        if len(set(codes)) != len(codes):
            raise ValueError("evaluation criterion codes must be unique")
        if {item.dimension for item in self.criteria} != {
            RFQEvaluationDimension.TECHNICAL,
            RFQEvaluationDimension.COMMERCIAL,
        }:
            raise ValueError("the evaluation matrix must include technical and commercial criteria")
        if sum((item.weight_percent for item in self.criteria), Decimal("0")) != Decimal("100.00"):
            raise ValueError("evaluation criterion weights must total exactly 100.00 percent")
        return self


class RFQEvaluationCriterionRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    rfq_id: uuid.UUID
    code: str
    name: str
    dimension: RFQEvaluationDimension
    weight_percent: Decimal
    is_mandatory: bool


class RFQResponseEvaluationInput(BaseModel):
    criterion_id: uuid.UUID
    score: Decimal = Field(ge=0, le=100)
    passes_gate: Optional[bool] = None
    comments: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("score")
    @classmethod
    def validate_evaluation_score(cls, value: Decimal) -> Decimal:
        try:
            quantized = value.quantize(Decimal("0.01"))
        except InvalidOperation as exc:
            raise ValueError("evaluation score must fit NUMERIC(5, 2)") from exc
        if not value.is_finite() or value < 0 or value > 100 or quantized != value:
            raise ValueError("evaluation score must be finite and between 0 and 100")
        return value


class RFQResponseEvaluationSubmit(BaseModel):
    evaluations: List[RFQResponseEvaluationInput] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def unique_criteria(self):
        ids = [item.criterion_id for item in self.evaluations]
        if len(ids) != len(set(ids)):
            raise ValueError("each matrix criterion may be scored only once per submission")
        return self


class RFQResponseEvaluationRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    criterion_id: uuid.UUID
    criterion_code: Optional[str] = None
    criterion_name: Optional[str] = None
    dimension: Optional[RFQEvaluationDimension] = None
    weight_percent: Optional[Decimal] = None
    revision_no: int
    score: Decimal
    passes_gate: Optional[bool]
    comments: Optional[str]
    evaluator_id: Optional[uuid.UUID]
    evaluated_at: datetime


class RFQDetailRead(RFQRead):
    responses: List[RFQResponseRead] = Field(default_factory=list)
    lines: List[RFQLineRead] = Field(default_factory=list)
    evaluation_criteria: List[RFQEvaluationCriterionRead] = Field(default_factory=list)


class RFQAwardAllocationCreate(BaseModel):
    response_id: uuid.UUID
    rfq_line_id: Optional[uuid.UUID] = None
    quantity: Decimal = Field(gt=0)

    @field_validator("quantity")
    @classmethod
    def validate_award_quantity(cls, value: Decimal) -> Decimal:
        try:
            quantized = value.quantize(Decimal("0.001"))
        except InvalidOperation as exc:
            raise ValueError("award quantity must fit NUMERIC(14, 3)") from exc
        if not value.is_finite() or value <= 0 or value >= Decimal("100000000000") or quantized != value:
            raise ValueError("award quantity must be finite, positive, and fit NUMERIC(14, 3)")
        return value


class RFQAwardProposalCreate(BaseModel):
    allocations: List[RFQAwardAllocationCreate] = Field(min_length=1, max_length=100)
    justification: str = Field(min_length=3, max_length=1000)

    @field_validator("justification")
    @classmethod
    def trim_award_justification(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("award justification must contain at least three characters")
        return normalized

    @model_validator(mode="after")
    def unique_responses(self):
        allocation_keys = [(item.response_id, item.rfq_line_id) for item in self.allocations]
        if len(allocation_keys) != len(set(allocation_keys)):
            raise ValueError("a supplier bid can appear only once per RFQ line allocation")
        return self


class RFQAwardDecision(BaseModel):
    comments: Optional[str] = Field(default=None, max_length=1000)


class RFQAwardAllocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    response_id: uuid.UUID
    rfq_line_id: Optional[uuid.UUID]
    quantity: Decimal


class RFQAwardApprovalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    approval_rule_id: uuid.UUID
    approval_level: int
    rule_name: str
    requires_all_matching_approvers: bool
    approver_user_id: uuid.UUID
    decision_status: RFQAwardApprovalStatus
    decided_by_id: Optional[uuid.UUID]
    decided_at: Optional[datetime]
    comments: Optional[str]


class RFQAwardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    rfq_id: uuid.UUID
    revision_no: int
    status: RFQAwardStatus
    total_amount: Decimal
    currency: str
    justification: str
    requested_by_id: Optional[uuid.UUID]
    requested_at: datetime
    decided_at: Optional[datetime]
    allocations: List[RFQAwardAllocationRead] = Field(default_factory=list)
    approvals: List[RFQAwardApprovalRead] = Field(default_factory=list)


# ── Blanket Purchase Agreement ─────────────────────────────────────────────────

class BlanketAgreementCreate(ProcurementScopeFields):
    bpa_no: str
    supplier_id: uuid.UUID
    material_id: Optional[uuid.UUID] = None
    product_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    agreed_unit_price: Decimal
    currency: str = "KES"
    agreed_quantity: Optional[Decimal] = None
    unit: str = "KG"
    valid_from: date
    valid_to: date
    payment_terms: Optional[str] = None
    notes: Optional[str] = None


class BlanketAgreementUpdate(ProcurementScopeFields):
    agreed_unit_price: Optional[Decimal] = None
    agreed_quantity: Optional[Decimal] = None
    valid_to: Optional[date] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[BPAStatus] = None


class BlanketAgreementRead(ProcurementScopeFields):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    bpa_no: str
    supplier_id: uuid.UUID
    supplier_name: Optional[str] = None
    material_id: Optional[uuid.UUID]
    product_id: Optional[uuid.UUID]
    description: Optional[str]
    agreed_unit_price: Decimal
    currency: str
    agreed_quantity: Optional[Decimal]
    consumed_quantity: Decimal
    unit: str
    valid_from: date
    valid_to: date
    payment_terms: Optional[str]
    status: BPAStatus
    notes: Optional[str]
    created_at: datetime
    access: Optional[ProcurementAccessHint] = None

    @computed_field
    @property
    def remaining_quantity(self) -> Optional[Decimal]:
        if self.agreed_quantity is not None:
            return self.agreed_quantity - self.consumed_quantity
        return None

    @computed_field
    @property
    def is_expired(self) -> bool:
        from datetime import date as _date
        return self.valid_to < _date.today()


# ── Auto Reorder Policy ────────────────────────────────────────────────────────

class AutoReorderPolicyCreate(ProcurementScopeFields):
    material_id: Optional[uuid.UUID] = None
    product_id: Optional[uuid.UUID] = None
    warehouse_id: Optional[uuid.UUID] = None
    reorder_point: Decimal
    reorder_quantity: Decimal
    max_stock_level: Optional[Decimal] = None
    lead_time_days: int = 7
    preferred_supplier_id: Optional[uuid.UUID] = None
    auto_create_pr: bool = True
    active_flag: bool = True
    notes: Optional[str] = None


class AutoReorderPolicyUpdate(ProcurementScopeFields):
    reorder_point: Optional[Decimal] = None
    reorder_quantity: Optional[Decimal] = None
    max_stock_level: Optional[Decimal] = None
    lead_time_days: Optional[int] = None
    preferred_supplier_id: Optional[uuid.UUID] = None
    auto_create_pr: Optional[bool] = None
    active_flag: Optional[bool] = None
    notes: Optional[str] = None


class AutoReorderPolicyRead(ProcurementScopeFields):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    material_id: Optional[uuid.UUID]
    product_id: Optional[uuid.UUID]
    warehouse_id: Optional[uuid.UUID]
    reorder_point: Decimal
    reorder_quantity: Decimal
    max_stock_level: Optional[Decimal]
    lead_time_days: int
    preferred_supplier_id: Optional[uuid.UUID]
    preferred_supplier_name: Optional[str] = None
    auto_create_pr: bool
    active_flag: bool
    notes: Optional[str]
    created_at: datetime
    access: Optional[ProcurementAccessHint] = None


class ProcurementApprovalRuleBase(ProcurementScopeFields):
    rule_name: str
    document_type: ProcurementApprovalDocumentType
    supplier_category: Optional[str] = None
    product_category: Optional[str] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    currency: Optional[str] = None
    approval_level: int = 1
    approver_user_id: Optional[uuid.UUID] = None
    approver_role_id: Optional[uuid.UUID] = None
    requires_all_matching_approvers: bool = False
    is_active: bool = True
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    notes: Optional[str] = None


class ProcurementApprovalRuleCreate(ProcurementApprovalRuleBase):
    pass


class ProcurementApprovalRuleUpdate(BaseModel):
    rule_name: Optional[str] = None
    document_type: Optional[ProcurementApprovalDocumentType] = None
    company_id: Optional[uuid.UUID] = None
    branch_id: Optional[uuid.UUID] = None
    cost_center_id: Optional[uuid.UUID] = None
    department: Optional[str] = None
    supplier_category: Optional[str] = None
    product_category: Optional[str] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    currency: Optional[str] = None
    approval_level: Optional[int] = None
    approver_user_id: Optional[uuid.UUID] = None
    approver_role_id: Optional[uuid.UUID] = None
    requires_all_matching_approvers: Optional[bool] = None
    is_active: Optional[bool] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    notes: Optional[str] = None


class ProcurementApprovalRuleRead(ProcurementApprovalRuleBase):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    created_at: datetime
