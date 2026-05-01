from pydantic import BaseModel
from typing import Optional, List, Any
from decimal import Decimal
from datetime import datetime, date
import uuid

from app.models.secondary_sales import (
    UploadSource, SecondarySalesStatus, RetailChannel,
)


# ── Retailer Master ───────────────────────────────────────────────────────────

class RetailerCreate(BaseModel):
    distributor_id: Optional[uuid.UUID] = None
    retailer_code: Optional[str] = None
    name: str
    location: Optional[str] = None
    city: Optional[str] = None
    channel: Optional[RetailChannel] = None
    is_active: bool = True


class RetailerRead(RetailerCreate):
    id: uuid.UUID
    distributor_name: Optional[str] = None
    model_config = {"from_attributes": True}


# ── Secondary Sales Lines ─────────────────────────────────────────────────────

class SecondarySalesLineInput(BaseModel):
    retailer_id: Optional[uuid.UUID] = None
    retailer_name: Optional[str] = None
    product_id: Optional[uuid.UUID] = None
    product_sku: Optional[str] = None
    quantity_sold: Decimal
    unit_price: Optional[Decimal] = None
    total_value: Optional[Decimal] = None
    sale_date: Optional[date] = None


class SecondarySalesLineRead(BaseModel):
    id: uuid.UUID
    header_id: uuid.UUID
    retailer_id: Optional[uuid.UUID] = None
    retailer_name: Optional[str] = None
    product_id: Optional[uuid.UUID] = None
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    quantity_sold: Decimal
    unit_price: Optional[Decimal] = None
    total_value: Optional[Decimal] = None
    sale_date: Optional[date] = None
    is_valid: bool
    validation_note: Optional[str] = None
    model_config = {"from_attributes": True}


# ── Secondary Sales Header ────────────────────────────────────────────────────

class SecondarySalesUpload(BaseModel):
    distributor_id: uuid.UUID
    period_from: date
    period_to: date
    upload_source: UploadSource = UploadSource.MANUAL_CSV
    notes: Optional[str] = None
    lines: List[SecondarySalesLineInput]


class SecondarySalesRead(BaseModel):
    id: uuid.UUID
    reference_no: str
    distributor_id: uuid.UUID
    distributor_name: Optional[str] = None
    period_from: date
    period_to: date
    upload_source: UploadSource
    upload_date: Optional[datetime] = None
    status: SecondarySalesStatus
    notes: Optional[str] = None
    validation_errors: Optional[str] = None
    total_lines: int
    total_value: Decimal
    model_config = {"from_attributes": True}


class SecondarySalesDetail(SecondarySalesRead):
    lines: List[SecondarySalesLineRead] = []


# ── Distributor Inventory Snapshot ────────────────────────────────────────────

class InventorySnapshotCreate(BaseModel):
    distributor_id: uuid.UUID
    product_id: uuid.UUID
    stock_qty: Decimal
    snapshot_date: date
    notes: Optional[str] = None


class InventorySnapshotRead(InventorySnapshotCreate):
    id: uuid.UUID
    distributor_name: Optional[str] = None
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    sell_through_rate: Optional[Decimal] = None
    days_of_stock: Optional[Decimal] = None
    model_config = {"from_attributes": True}


# ── Reports ───────────────────────────────────────────────────────────────────

class SellThroughRow(BaseModel):
    distributor_id: uuid.UUID
    distributor_name: str
    product_sku: str
    product_name: str
    sell_in_qty: Decimal
    sell_out_qty: Decimal
    sell_through_rate: Decimal
    stock_at_distributor: Optional[Decimal] = None
    days_of_stock: Optional[Decimal] = None
    status: str


class DistributorPerformanceRow(BaseModel):
    distributor_id: uuid.UUID
    distributor_name: str
    total_sell_out_value: Decimal
    total_sell_out_qty: Decimal
    line_count: int
    period: str


class ProductSellThroughRow(BaseModel):
    product_id: uuid.UUID
    product_sku: str
    product_name: str
    total_qty_sold: Decimal
    total_value: Decimal
    distributor_count: int
    avg_sell_through_rate: Optional[Decimal] = None


# ── AI Outputs ────────────────────────────────────────────────────────────────

class AIInsightResult(BaseModel):
    agent: str
    insights: List[str]
    details: Optional[List[dict]] = None
    generated_at: str
