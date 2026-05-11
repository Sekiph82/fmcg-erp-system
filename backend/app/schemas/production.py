from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
import uuid

from app.models.production import (
    ProductionPlanStatus, ProductionOrderStatus, DowntimeReason,
)
from app.models.finance import OperationalPostingStatus


# ── Production Plan Line ──────────────────────────────────────────────────────

class PlanLineCreate(BaseModel):
    line_no: int
    product_id: uuid.UUID
    recipe_id: uuid.UUID
    target_quantity: Decimal
    uom: str = "KG"
    target_warehouse_id: uuid.UUID
    planned_date: Optional[datetime] = None
    notes: Optional[str] = None


class PlanLineRead(PlanLineCreate):
    id: uuid.UUID
    plan_id: uuid.UUID
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    recipe_name: Optional[str] = None
    recipe_version: Optional[str] = None
    target_warehouse_name: Optional[str] = None
    model_config = {"from_attributes": True}


# ── Production Plan ───────────────────────────────────────────────────────────

class ProductionPlanCreate(BaseModel):
    plan_no: str
    name: str
    description: Optional[str] = None
    planned_date: datetime


class ProductionPlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    planned_date: Optional[datetime] = None


class ProductionPlanRead(BaseModel):
    id: uuid.UUID
    plan_no: str
    name: str
    description: Optional[str] = None
    status: ProductionPlanStatus
    planned_date: datetime
    created_by: Optional[uuid.UUID] = None
    model_config = {"from_attributes": True}


class ProductionPlanDetailRead(ProductionPlanRead):
    lines: List[PlanLineRead] = []


# ── Production Order ──────────────────────────────────────────────────────────

class ProductionOrderCreate(BaseModel):
    order_no: str
    plan_line_id: Optional[uuid.UUID] = None
    product_id: uuid.UUID
    recipe_id: uuid.UUID
    planned_quantity: Decimal
    uom: str = "KG"
    batch_no: Optional[str] = None
    target_warehouse_id: uuid.UUID
    source_warehouse_id: Optional[uuid.UUID] = None
    scheduled_start: datetime
    scheduled_end: datetime
    notes: Optional[str] = None


class ProductionOrderRead(BaseModel):
    id: uuid.UUID
    order_no: str
    plan_line_id: Optional[uuid.UUID] = None
    product_id: uuid.UUID
    recipe_id: uuid.UUID
    planned_quantity: Decimal
    actual_quantity: Optional[Decimal] = None
    batch_no: Optional[str] = None
    uom: str
    status: ProductionOrderStatus
    target_warehouse_id: uuid.UUID
    source_warehouse_id: Optional[uuid.UUID] = None
    scheduled_start: datetime
    scheduled_end: datetime
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    created_by: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    recipe_name: Optional[str] = None
    target_warehouse_name: Optional[str] = None
    model_config = {"from_attributes": True}


# ── Material Consumption ──────────────────────────────────────────────────────

class MaterialConsumptionRead(BaseModel):
    id: uuid.UUID
    production_order_id: uuid.UUID
    material_id: uuid.UUID
    lot_id: Optional[uuid.UUID] = None
    standard_quantity: Decimal
    actual_quantity: Decimal
    variance_quantity: Decimal
    unit: str
    source_warehouse_id: uuid.UUID
    stock_movement_id: Optional[uuid.UUID] = None
    posting_batch_id: Optional[uuid.UUID] = None
    journal_entry_id: Optional[uuid.UUID] = None
    accounting_status: Optional[OperationalPostingStatus] = None
    posting_error: Optional[str] = None
    notes: Optional[str] = None
    material_name: Optional[str] = None
    material_code: Optional[str] = None
    lot_number: Optional[str] = None
    source_warehouse_name: Optional[str] = None
    model_config = {"from_attributes": True}


# ── Finished Goods Receipt ────────────────────────────────────────────────────

class FinishedGoodsReceiptRead(BaseModel):
    id: uuid.UUID
    production_order_id: uuid.UUID
    product_id: uuid.UUID
    quantity: Decimal
    uom: str
    lot_number: Optional[str] = None
    batch_no: Optional[str] = None
    warehouse_id: uuid.UUID
    stock_movement_id: Optional[uuid.UUID] = None
    posting_batch_id: Optional[uuid.UUID] = None
    journal_entry_id: Optional[uuid.UUID] = None
    accounting_status: Optional[OperationalPostingStatus] = None
    posting_error: Optional[str] = None
    notes: Optional[str] = None
    warehouse_name: Optional[str] = None
    model_config = {"from_attributes": True}


# ── Downtime ──────────────────────────────────────────────────────────────────

class DowntimeLogCreate(BaseModel):
    machine_id: Optional[str] = None
    reason: DowntimeReason = DowntimeReason.OTHER
    start_time: Optional[datetime] = None
    notes: Optional[str] = None


class DowntimeLogClose(BaseModel):
    end_time: Optional[datetime] = None
    notes: Optional[str] = None


class DowntimeLogRead(BaseModel):
    id: uuid.UUID
    production_order_id: uuid.UUID
    machine_id: Optional[str] = None
    reason: DowntimeReason
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    model_config = {"from_attributes": True}


# ── OEE ───────────────────────────────────────────────────────────────────────

class OEEMetrics(BaseModel):
    order_id: uuid.UUID
    order_no: str
    scheduled_minutes: float
    actual_minutes: Optional[float] = None
    downtime_minutes: float
    availability: float
    performance: float
    quality: float
    oee: float


# ── Execution requests ────────────────────────────────────────────────────────

class CompleteOrderRequest(BaseModel):
    actual_quantity: Decimal
    fg_lot_number: Optional[str] = None
    fg_expiry_date: Optional[str] = None
    source_warehouse_id: Optional[uuid.UUID] = None
    consume_materials: bool = True
    notes: Optional[str] = None


# ── Production Order Detail (full) ────────────────────────────────────────────

class ProductionOrderDetailRead(ProductionOrderRead):
    consumptions: List[MaterialConsumptionRead] = []
    fg_receipts: List[FinishedGoodsReceiptRead] = []
    downtime_logs: List[DowntimeLogRead] = []
    oee: Optional[OEEMetrics] = None


# ── Reports ───────────────────────────────────────────────────────────────────

class ProductionReportRow(BaseModel):
    date: str
    order_no: str
    product_name: str
    product_sku: str
    planned_quantity: Decimal
    actual_quantity: Optional[Decimal]
    variance: Optional[Decimal]
    variance_pct: Optional[float]
    status: ProductionOrderStatus
    batch_no: Optional[str]
    downtime_minutes: float


class DowntimeSummaryRow(BaseModel):
    reason: str
    count: int
    total_minutes: float
    machine_id: Optional[str]


class ProductionSummary(BaseModel):
    total_orders: int
    completed_orders: int
    in_progress_orders: int
    planned_quantity_total: Decimal
    actual_quantity_total: Decimal
    overall_variance: Decimal
    total_downtime_minutes: float
    avg_oee: Optional[float]
    orders: List[ProductionReportRow]
    downtime_summary: List[DowntimeSummaryRow]
