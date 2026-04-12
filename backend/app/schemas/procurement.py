from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
import uuid

from pydantic import BaseModel, computed_field, ConfigDict

from app.models.procurement import PRStatus, POStatus, GRNStatus, ImportShipmentStatus, POPaymentStatus


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

class PRCreate(BaseModel):
    pr_no: str
    department: Optional[str] = None
    required_date: date
    notes: Optional[str] = None
    lines: List[PRLineCreate] = []


class PRUpdate(BaseModel):
    department: Optional[str] = None
    required_date: Optional[date] = None
    notes: Optional[str] = None


class PRRead(BaseModel):
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

class POCreate(BaseModel):
    po_no: str
    supplier_id: uuid.UUID
    order_date: date
    expected_delivery_date: date
    payment_terms: Optional[str] = None
    currency: str = "USD"
    exchange_rate: Decimal = Decimal("1.0")
    notes: Optional[str] = None
    lines: List[POLineCreate] = []


class POUpdate(BaseModel):
    expected_delivery_date: Optional[date] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None


class PORead(BaseModel):
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


class PODetailRead(PORead):
    lines: List[POLineRead] = []


# ── GRN ────────────────────────────────────────────────────────────────────────

class GRNLineCreate(BaseModel):
    po_line_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    product_id: Optional[uuid.UUID] = None
    received_quantity: Decimal
    accepted_quantity: Decimal
    rejected_quantity: Decimal = Decimal("0")
    unit: str = "KG"
    lot_number: Optional[str] = None
    expiry_date: Optional[date] = None
    notes: Optional[str] = None


class GRNCreate(BaseModel):
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
    rejected_quantity: Decimal
    unit: str
    lot_number: Optional[str]
    expiry_date: Optional[date]
    notes: Optional[str]
    stock_movement_id: Optional[uuid.UUID]


class GRNRead(BaseModel):
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
    created_at: datetime


class GRNDetailRead(GRNRead):
    lines: List[GRNLineRead] = []


# ── Import Shipment ────────────────────────────────────────────────────────────

class ImportShipmentCreate(BaseModel):
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


class ImportShipmentUpdate(BaseModel):
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


class ImportShipmentRead(BaseModel):
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

class SupplierEvaluationCreate(BaseModel):
    supplier_id: uuid.UUID
    evaluation_date: date
    po_id: Optional[uuid.UUID] = None
    on_time_delivery_score: Decimal
    quality_score: Decimal
    price_competitiveness_score: Decimal
    responsiveness_score: Decimal
    notes: Optional[str] = None


class SupplierEvaluationRead(BaseModel):
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


class SupplierDashboardRow(BaseModel):
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

class SupplierPaymentCreate(BaseModel):
    payment_date: date
    amount: Decimal
    method: str = "bank"        # bank | cash | mpesa
    reference: Optional[str] = None
    notes: Optional[str] = None


class SupplierPaymentRead(BaseModel):
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
