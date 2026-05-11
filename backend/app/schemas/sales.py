from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
import uuid

from pydantic import BaseModel, ConfigDict, computed_field

from app.models.sales import (
    CustomerChannel, SOStatus, ShipmentStatus, InvoiceStatus,
    PaymentMethod, SOPaymentStatus, MpesaTxStatus, CustomerType,
)


# ── Customer ──────────────────────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    code: str
    name: str
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    delivery_address: Optional[str] = None
    delivery_city: Optional[str] = None
    delivery_country: Optional[str] = None
    channel: CustomerChannel = CustomerChannel.WHOLESALE
    payment_terms_days: int = 30
    credit_limit: Optional[Decimal] = None
    tax_id: Optional[str] = None
    currency: str = "USD"
    notes: Optional[str] = None
    customer_type: Optional[CustomerType] = None
    region: Optional[str] = None
    segment: Optional[str] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    delivery_address: Optional[str] = None
    delivery_city: Optional[str] = None
    delivery_country: Optional[str] = None
    channel: Optional[CustomerChannel] = None
    payment_terms_days: Optional[int] = None
    credit_limit: Optional[Decimal] = None
    currency: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    is_prepaid: Optional[bool] = None
    customer_type: Optional[CustomerType] = None
    region: Optional[str] = None
    segment: Optional[str] = None


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    name: str
    contact_person: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    city: Optional[str]
    country: Optional[str]
    delivery_address: Optional[str]
    delivery_city: Optional[str]
    delivery_country: Optional[str]
    channel: CustomerChannel
    payment_terms_days: int
    credit_limit: Optional[Decimal]
    tax_id: Optional[str]
    currency: str
    notes: Optional[str]
    is_active: bool
    is_prepaid: bool
    customer_type: Optional[CustomerType] = None
    region: Optional[str] = None
    segment: Optional[str] = None
    created_at: datetime


# ── SO Lines ──────────────────────────────────────────────────────────────────

class SOLineCreate(BaseModel):
    line_no: int
    product_id: uuid.UUID
    ordered_quantity: Decimal
    unit: str = "PCS"
    unit_price: Decimal = Decimal("0")
    discount_pct: Decimal = Decimal("0")
    tax_rate: Decimal = Decimal("0")
    cost_price: Optional[Decimal] = None
    notes: Optional[str] = None


class SOLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    line_no: int
    product_id: uuid.UUID
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    ordered_quantity: Decimal
    unit: str
    unit_price: Decimal
    discount_pct: Decimal
    tax_rate: Decimal
    allocated_quantity: Decimal
    shipped_quantity: Decimal
    cost_price: Optional[Decimal] = None
    notes: Optional[str]

    @computed_field
    @property
    def net_price(self) -> Decimal:
        return (self.unit_price * (1 - self.discount_pct)).quantize(Decimal("0.0001"))

    @computed_field
    @property
    def line_total(self) -> Decimal:
        return (self.ordered_quantity * self.net_price * (1 + self.tax_rate)).quantize(Decimal("0.01"))

    @computed_field
    @property
    def pending_quantity(self) -> Decimal:
        return max(self.ordered_quantity - self.shipped_quantity, Decimal("0"))

    @computed_field
    @property
    def unallocated_quantity(self) -> Decimal:
        return max(self.ordered_quantity - self.allocated_quantity, Decimal("0"))

    @computed_field
    @property
    def gross_margin(self) -> Optional[Decimal]:
        if self.cost_price is None:
            return None
        revenue = self.net_price
        if revenue == 0:
            return None
        return ((revenue - self.cost_price) / revenue * 100).quantize(Decimal("0.01"))


# ── Sales Order ───────────────────────────────────────────────────────────────

class SOCreate(BaseModel):
    order_no: str
    customer_id: uuid.UUID
    order_date: date
    requested_delivery_date: date
    warehouse_id: Optional[uuid.UUID] = None
    currency: str = "USD"
    notes: Optional[str] = None
    payment_method: PaymentMethod = PaymentMethod.CASH
    lines: List[SOLineCreate] = []
    # Marketing linkage
    campaign_id: Optional[uuid.UUID] = None
    promotion_id: Optional[uuid.UUID] = None
    crm_segment_id: Optional[uuid.UUID] = None


class SOUpdate(BaseModel):
    requested_delivery_date: Optional[date] = None
    warehouse_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class SORead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    order_no: str
    customer_id: uuid.UUID
    customer_name: Optional[str] = None
    order_date: date
    requested_delivery_date: date
    status: SOStatus
    warehouse_id: Optional[uuid.UUID]
    warehouse_name: Optional[str] = None
    currency: str
    notes: Optional[str]
    confirmed_at: Optional[datetime]
    created_at: datetime
    total_value: Optional[Decimal] = None
    line_count: int = 0
    days_until_delivery: Optional[int] = None
    payment_method: PaymentMethod = PaymentMethod.CASH
    payment_status: SOPaymentStatus = SOPaymentStatus.PENDING
    mpesa_reference: Optional[str] = None
    mpesa_request_id: Optional[str] = None
    # Marketing linkage
    campaign_id: Optional[uuid.UUID] = None
    promotion_id: Optional[uuid.UUID] = None
    crm_segment_id: Optional[uuid.UUID] = None
    source: Optional[str] = None


class SODetailRead(SORead):
    lines: List[SOLineRead] = []


# ── Shipment ──────────────────────────────────────────────────────────────────

class ShipmentLineCreate(BaseModel):
    so_line_id: Optional[uuid.UUID] = None
    product_id: uuid.UUID
    lot_id: Optional[uuid.UUID] = None
    quantity: Decimal
    unit: str = "PCS"


class ShipmentCreate(BaseModel):
    shipment_no: str
    so_id: uuid.UUID
    warehouse_id: uuid.UUID
    scheduled_date: date
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    delivery_notes: Optional[str] = None
    lines: List[ShipmentLineCreate] = []


class ShipmentLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    so_line_id: Optional[uuid.UUID]
    product_id: uuid.UUID
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    lot_id: Optional[uuid.UUID]
    lot_number: Optional[str] = None
    quantity: Decimal
    unit: str
    is_picked: bool
    picked_by_id: Optional[uuid.UUID]
    stock_movement_id: Optional[uuid.UUID]


class ShipmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    shipment_no: str
    so_id: uuid.UUID
    so_no: Optional[str] = None
    customer_name: Optional[str] = None
    warehouse_id: uuid.UUID
    warehouse_name: Optional[str] = None
    status: ShipmentStatus
    scheduled_date: date
    dispatched_date: Optional[date]
    carrier: Optional[str]
    tracking_number: Optional[str]
    delivery_notes: Optional[str]
    created_at: datetime
    line_count: int = 0
    picked_count: int = 0


class ShipmentDetailRead(ShipmentRead):
    lines: List[ShipmentLineRead] = []


# ── Invoice ───────────────────────────────────────────────────────────────────

class InvoiceLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    description: Optional[str]
    quantity: Decimal
    unit: str
    unit_price: Decimal
    discount_pct: Decimal
    tax_rate: Decimal
    line_total: Decimal


class InvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    invoice_no: str
    so_id: uuid.UUID
    so_no: Optional[str] = None
    shipment_id: Optional[uuid.UUID]
    customer_id: uuid.UUID
    customer_name: Optional[str] = None
    invoice_date: date
    due_date: date
    status: InvoiceStatus
    currency: str
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    notes: Optional[str]
    created_at: datetime

    @computed_field
    @property
    def outstanding_balance(self) -> Decimal:
        return max(self.total_amount - self.paid_amount, Decimal("0"))

    @computed_field
    @property
    def days_overdue(self) -> Optional[int]:
        from datetime import date as date_cls
        today = date_cls.today()
        if self.status in (InvoiceStatus.PAID,):
            return None
        delta = (today - self.due_date).days
        return delta if delta > 0 else None


class InvoiceDetailRead(InvoiceRead):
    lines: List[InvoiceLineRead] = []


# ── Payment ───────────────────────────────────────────────────────────────────

class PaymentCreate(BaseModel):
    payment_date: date
    amount: Decimal
    reference: Optional[str] = None
    notes: Optional[str] = None


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    invoice_id: uuid.UUID
    payment_date: date
    amount: Decimal
    reference: Optional[str]
    notes: Optional[str]
    created_at: datetime


# ── Allocation / Dispatch ─────────────────────────────────────────────────────

class AllocateSORequest(BaseModel):
    warehouse_id: uuid.UUID


class DispatchShipmentRequest(BaseModel):
    dispatched_date: Optional[date] = None


class InvoiceFromShipmentRequest(BaseModel):
    invoice_no: str
    invoice_date: date
    due_date: date
    notes: Optional[str] = None


# ── Reports / Dashboard ───────────────────────────────────────────────────────

class OutstandingInvoiceRow(BaseModel):
    invoice_id: uuid.UUID
    invoice_no: str
    customer_name: str
    invoice_date: date
    due_date: date
    total_amount: Decimal
    paid_amount: Decimal
    outstanding_balance: Decimal
    days_overdue: Optional[int]
    status: InvoiceStatus


class SalesSummary(BaseModel):
    total_orders: int
    confirmed_orders: int
    total_order_value: Decimal
    total_invoiced: Decimal
    total_collected: Decimal
    outstanding_balance: Decimal
    overdue_invoices: int


# ── M-Pesa ────────────────────────────────────────────────────────────────────

class MpesaPaymentRequest(BaseModel):
    phone_number: str           # e.g. 254712345678
    amount: Decimal


class MpesaCallbackPayload(BaseModel):
    """Safaricom Daraja STK Push callback shape (simplified)."""
    checkout_request_id: str    # maps to mpesa_request_id
    result_code: int            # 0 = success
    result_description: str
    mpesa_receipt_number: Optional[str] = None   # present on success
    amount: Optional[Decimal] = None
    phone_number: Optional[str] = None


class MpesaTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    so_id: uuid.UUID
    phone_number: str
    amount: Decimal
    mpesa_request_id: Optional[str]
    mpesa_reference: Optional[str]
    status: MpesaTxStatus
    result_code: Optional[int]
    result_description: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime] = None


# ── Customer Statement ────────────────────────────────────────────────────────

class StatementInvoiceRow(BaseModel):
    invoice_id: uuid.UUID
    invoice_no: str
    so_no: Optional[str]
    invoice_date: date
    due_date: date
    total_amount: Decimal
    paid_amount: Decimal
    outstanding_balance: Decimal
    status: InvoiceStatus
    days_overdue: Optional[int]
    age_bucket: str  # CURRENT | 1-30 | 31-60 | 61-90 | 90+


class AgedBalanceSummary(BaseModel):
    current: Decimal = Decimal("0")
    days_1_30: Decimal = Decimal("0")
    days_31_60: Decimal = Decimal("0")
    days_61_90: Decimal = Decimal("0")
    days_90_plus: Decimal = Decimal("0")
    total_outstanding: Decimal = Decimal("0")


class CustomerStatement(BaseModel):
    customer_id: uuid.UUID
    customer_name: str
    customer_code: str
    credit_limit: Optional[Decimal]
    credit_used: Decimal
    credit_available: Optional[Decimal]
    as_of_date: date
    invoices: List[StatementInvoiceRow] = []
    aged_balance: AgedBalanceSummary


class CreditCheckResult(BaseModel):
    customer_id: uuid.UUID
    customer_name: str
    credit_limit: Optional[Decimal]
    credit_used: Decimal
    credit_available: Optional[Decimal]
    order_value: Decimal
    would_exceed: bool
    can_confirm: bool
    message: str


# ── Order Margin ──────────────────────────────────────────────────────────────

class OrderMarginLineRow(BaseModel):
    line_no: int
    product_id: uuid.UUID
    product_name: Optional[str]
    ordered_quantity: Decimal
    unit: str
    unit_price: Decimal
    discount_pct: Decimal
    net_price: Decimal
    cost_price: Optional[Decimal]
    line_revenue: Decimal
    line_cost: Optional[Decimal]
    gross_margin_pct: Optional[Decimal]


class OrderMarginSummary(BaseModel):
    so_id: uuid.UUID
    order_no: str
    customer_name: Optional[str]
    total_revenue: Decimal
    total_cost: Optional[Decimal]
    gross_profit: Optional[Decimal]
    gross_margin_pct: Optional[Decimal]
    lines_with_cost: int
    lines_without_cost: int
    lines: List[OrderMarginLineRow] = []
