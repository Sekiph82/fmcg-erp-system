from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── Van ───────────────────────────────────────────────────────────────────────

class VanCreate(BaseModel):
    van_code: str
    plate_number: Optional[str] = None
    driver_id: Optional[UUID] = None
    route_id: Optional[UUID] = None
    warehouse_id: Optional[UUID] = None
    capacity_kg: Optional[Decimal] = None
    notes: Optional[str] = None


class VanUpdate(BaseModel):
    plate_number: Optional[str] = None
    driver_id: Optional[UUID] = None
    route_id: Optional[UUID] = None
    warehouse_id: Optional[UUID] = None
    capacity_kg: Optional[Decimal] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class VanOut(BaseModel):
    id: UUID
    van_code: str
    plate_number: Optional[str]
    driver_id: Optional[UUID]
    route_id: Optional[UUID]
    warehouse_id: Optional[UUID]
    capacity_kg: Optional[Decimal]
    status: str
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ── Van Stock ─────────────────────────────────────────────────────────────────

class VanStockOut(BaseModel):
    id: UUID
    van_id: UUID
    item_id: UUID
    batch_id: Optional[UUID]
    quantity: Decimal
    reserved_qty: Decimal
    unit_cost: Optional[Decimal]
    uom: str
    model_config = {"from_attributes": True}


class StockLoadLine(BaseModel):
    item_id: UUID
    batch_id: Optional[UUID] = None
    quantity: Decimal = Field(gt=0)
    uom: str = "PCS"
    unit_cost: Optional[Decimal] = None


class StockLoadRequest(BaseModel):
    lines: List[StockLoadLine]
    notes: Optional[str] = None


# ── Visit ─────────────────────────────────────────────────────────────────────

class VisitCreate(BaseModel):
    customer_id: UUID
    route_date: date
    sequence_no: Optional[int] = None
    planned_time: Optional[datetime] = None
    offline_id: Optional[str] = None
    notes: Optional[str] = None


class VisitCheckIn(BaseModel):
    gps_lat: Optional[Decimal] = None
    gps_lng: Optional[Decimal] = None


class VisitCheckOut(BaseModel):
    notes: Optional[str] = None


class VisitOut(BaseModel):
    id: UUID
    van_id: UUID
    route_id: Optional[UUID]
    customer_id: UUID
    route_date: date
    sequence_no: Optional[int]
    planned_time: Optional[datetime]
    check_in_time: Optional[datetime]
    check_out_time: Optional[datetime]
    status: str
    gps_lat: Optional[Decimal]
    gps_lng: Optional[Decimal]
    missed_reason: Optional[str]
    offline_id: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Transaction ───────────────────────────────────────────────────────────────

class TxnLineCreate(BaseModel):
    item_id: UUID
    batch_id: Optional[UUID] = None
    uom: str = "PCS"
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    discount_pct: Decimal = Field(ge=0, default=0)
    tax_pct: Decimal = Field(ge=0, default=0)
    return_reason: Optional[str] = None
    notes: Optional[str] = None


class TxnCreate(BaseModel):
    customer_id: UUID
    visit_id: Optional[UUID] = None
    txn_type: str = "SALE"
    txn_datetime: datetime
    lines: List[TxnLineCreate]
    price_list_id: Optional[UUID] = None
    offline_id: Optional[str] = None
    device_id: Optional[str] = None
    notes: Optional[str] = None


class TxnLineOut(BaseModel):
    id: UUID
    txn_id: UUID
    item_id: UUID
    batch_id: Optional[UUID]
    uom: str
    quantity: Decimal
    unit_price: Decimal
    discount_pct: Decimal
    discount_amt: Decimal
    tax_pct: Decimal
    tax_amt: Decimal
    line_total: Decimal
    return_reason: Optional[str]
    model_config = {"from_attributes": True}


class TxnOut(BaseModel):
    id: UUID
    txn_no: str
    van_id: UUID
    route_id: Optional[UUID]
    customer_id: UUID
    visit_id: Optional[UUID]
    driver_id: Optional[UUID]
    txn_type: str
    txn_datetime: datetime
    status: str
    payment_status: str
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    balance_due: Decimal
    currency: str
    linked_so_id: Optional[UUID]
    offline_id: Optional[str]
    synced_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    lines: List[TxnLineOut] = []
    payments: List["PaymentOut"] = []
    model_config = {"from_attributes": True}


# ── Payment ───────────────────────────────────────────────────────────────────

class PaymentCreate(BaseModel):
    method: str
    amount: Decimal = Field(gt=0)
    reference_no: Optional[str] = None
    collected_at: datetime
    notes: Optional[str] = None


class PaymentOut(BaseModel):
    id: UUID
    txn_id: UUID
    method: str
    amount: Decimal
    reference_no: Optional[str]
    collected_at: datetime
    receipt_no: Optional[str]
    notes: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


TxnOut.model_rebuild()


# ── Reconciliation ────────────────────────────────────────────────────────────

class ReconciliationCreate(BaseModel):
    route_date: date
    closing_stock: Optional[Dict[str, float]] = None
    notes: Optional[str] = None


class ReconciliationOut(BaseModel):
    id: UUID
    van_id: UUID
    route_date: date
    status: str
    opening_stock: Optional[Dict]
    closing_stock: Optional[Dict]
    sales_qty: Optional[Dict]
    returns_qty: Optional[Dict]
    discrepancy: Optional[Dict]
    total_sales: Optional[Decimal]
    total_cash: Optional[Decimal]
    total_mpesa: Optional[Decimal]
    total_credit: Optional[Decimal]
    total_returns: Optional[Decimal]
    submitted_by: Optional[UUID]
    approved_by: Optional[UUID]
    approved_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Offline Sync ──────────────────────────────────────────────────────────────

class SyncPayload(BaseModel):
    visits: List[VisitCreate] = []
    transactions: List[TxnCreate] = []
    payments: List[Dict[str, Any]] = []  # {offline_txn_id, payment}
    device_id: Optional[str] = None


class SyncResult(BaseModel):
    visits_created: int = 0
    txns_created: int = 0
    payments_created: int = 0
    errors: List[str] = []
    duplicates_skipped: int = 0


# ── AI ────────────────────────────────────────────────────────────────────────

class VSAIRecOut(BaseModel):
    id: UUID
    agent_type: str
    status: str
    severity: str
    title: str
    body: str
    data: Optional[dict]
    van_id: Optional[UUID]
    driver_id: Optional[UUID]
    route_id: Optional[UUID]
    created_at: datetime
    model_config = {"from_attributes": True}


class VSAIRecAck(BaseModel):
    status: str
