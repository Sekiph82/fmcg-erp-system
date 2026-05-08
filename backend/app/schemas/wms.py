from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
from datetime import datetime, date
import uuid

from app.models.wms import (
    ZoneType, StockCountType, StockCountStatus,
    PutawayRuleType, PutawayTaskStatus, LocationType,
    PickingTaskStatus, PackingStatus, ReplenishmentStatus,
)


# ── Zones ─────────────────────────────────────────────────────────────────────

class WarehouseZoneCreate(BaseModel):
    warehouse_id: uuid.UUID
    code: str
    name: str
    zone_type: ZoneType
    description: Optional[str] = None
    is_active: bool = True


class WarehouseZoneRead(WarehouseZoneCreate):
    id: uuid.UUID
    warehouse_name: Optional[str] = None
    location_count: int = 0
    model_config = {"from_attributes": True}


# ── Storage Locations ─────────────────────────────────────────────────────────

class StorageLocationCreate(BaseModel):
    zone_id: uuid.UUID
    code: str
    name: str
    barcode: Optional[str] = None
    max_weight_kg: Optional[Decimal] = None
    max_volume_m3: Optional[Decimal] = None
    location_type: Optional[LocationType] = None
    is_active: bool = True
    is_blocked: bool = False


class StorageLocationUpdate(BaseModel):
    name: Optional[str] = None
    barcode: Optional[str] = None
    max_weight_kg: Optional[Decimal] = None
    max_volume_m3: Optional[Decimal] = None
    location_type: Optional[LocationType] = None
    current_utilization_pct: Optional[Decimal] = None
    is_active: Optional[bool] = None
    is_blocked: Optional[bool] = None


class StorageLocationRead(StorageLocationCreate):
    id: uuid.UUID
    zone_code: Optional[str] = None
    zone_name: Optional[str] = None
    zone_type: Optional[ZoneType] = None
    warehouse_id: Optional[uuid.UUID] = None
    warehouse_name: Optional[str] = None
    current_utilization_pct: Optional[Decimal] = None
    model_config = {"from_attributes": True}


class ScanLocationResult(BaseModel):
    location: StorageLocationRead
    stock_lines: List[dict] = []


# ── Stock Count ───────────────────────────────────────────────────────────────

class StockCountCreate(BaseModel):
    count_no: str
    warehouse_id: uuid.UUID
    zone_id: Optional[uuid.UUID] = None
    count_type: StockCountType = StockCountType.CYCLE
    scheduled_date: datetime
    notes: Optional[str] = None


class StockCountRead(BaseModel):
    id: uuid.UUID
    count_no: str
    warehouse_id: uuid.UUID
    zone_id: Optional[uuid.UUID] = None
    count_type: StockCountType
    status: StockCountStatus
    scheduled_date: datetime
    completed_date: Optional[datetime] = None
    created_by: Optional[uuid.UUID] = None
    approved_by: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    warehouse_name: Optional[str] = None
    zone_name: Optional[str] = None
    total_lines: int = 0
    counted_lines: int = 0
    model_config = {"from_attributes": True}


class StockCountLineRead(BaseModel):
    id: uuid.UUID
    count_id: uuid.UUID
    product_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    lot_id: Optional[uuid.UUID] = None
    location_id: Optional[uuid.UUID] = None
    system_quantity: Decimal
    counted_quantity: Optional[Decimal] = None
    variance: Optional[Decimal] = None
    unit: str
    is_counted: bool
    notes: Optional[str] = None
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    material_name: Optional[str] = None
    material_code: Optional[str] = None
    lot_number: Optional[str] = None
    location_code: Optional[str] = None
    model_config = {"from_attributes": True}


class StockCountDetailRead(StockCountRead):
    lines: List[StockCountLineRead] = []


class RecordCountRequest(BaseModel):
    counted_quantity: Decimal
    notes: Optional[str] = None


# ── WMS Operations ────────────────────────────────────────────────────────────

class PutawayRequest(BaseModel):
    product_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    warehouse_id: uuid.UUID
    location_id: uuid.UUID
    lot_number: Optional[str] = None
    quantity: Decimal
    reference: str
    notes: Optional[str] = None


class PickRequest(BaseModel):
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    location_id: Optional[uuid.UUID] = None
    lot_number: Optional[str] = None
    quantity: Decimal
    reference: str
    notes: Optional[str] = None


class QuarantineRequest(BaseModel):
    warehouse_id: uuid.UUID
    product_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    lot_number: Optional[str] = None
    reason: str
    notes: Optional[str] = None


class ReleaseQuarantineRequest(BaseModel):
    warehouse_id: uuid.UUID
    product_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    lot_number: Optional[str] = None
    notes: Optional[str] = None


# ── FEFO Suggestion ───────────────────────────────────────────────────────────

class FEFOSuggestion(BaseModel):
    lot_id: uuid.UUID
    lot_number: str
    expiry_date: Optional[date] = None
    manufacture_date: Optional[date] = None
    available_quantity: Decimal
    location_code: Optional[str] = None
    days_to_expiry: Optional[int] = None


# ── Reports ───────────────────────────────────────────────────────────────────

class NearExpiryRow(BaseModel):
    lot_number: str
    product_id: Optional[uuid.UUID] = None
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    material_id: Optional[uuid.UUID] = None
    material_name: Optional[str] = None
    expiry_date: date
    days_to_expiry: int
    warehouse_name: str
    quantity_available: Decimal
    is_expired: bool


class LowStockRow(BaseModel):
    product_id: Optional[uuid.UUID] = None
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    warehouse_name: str
    quantity_available: Decimal
    reorder_point: Decimal
    shortage: Decimal


class StockAgingRow(BaseModel):
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    lot_number: Optional[str] = None
    warehouse_name: str
    quantity_on_hand: Decimal
    first_received_date: Optional[str] = None
    age_days: Optional[int] = None
    age_bucket: str  # "0-30", "31-60", "61-90", "90+"
    is_blocked: bool


class LotTraceRow(BaseModel):
    event_type: str  # "MOVEMENT" | "CONSUMPTION" | "FG_RECEIPT"
    event_date: str
    reference: str
    description: str
    quantity: Decimal
    warehouse_name: Optional[str] = None
    order_no: Optional[str] = None


class LotTraceResult(BaseModel):
    lot_number: str
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    material_name: Optional[str] = None
    expiry_date: Optional[date] = None
    manufacture_date: Optional[date] = None
    events: List[LotTraceRow]


# ── Putaway Rules ─────────────────────────────────────────────────────────────

class PutawayRuleCreate(BaseModel):
    rule_code: str
    warehouse_id: uuid.UUID
    rule_type: PutawayRuleType
    priority: int = 100
    product_id: Optional[uuid.UUID] = None
    category: Optional[str] = None
    zone_id: Optional[uuid.UUID] = None
    location_id: Optional[uuid.UUID] = None
    is_active: bool = True
    notes: Optional[str] = None


class PutawayRuleUpdate(BaseModel):
    rule_type: Optional[PutawayRuleType] = None
    priority: Optional[int] = None
    product_id: Optional[uuid.UUID] = None
    category: Optional[str] = None
    zone_id: Optional[uuid.UUID] = None
    location_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class PutawayRuleRead(PutawayRuleCreate):
    id: uuid.UUID
    warehouse_name: Optional[str] = None
    zone_name: Optional[str] = None
    location_code: Optional[str] = None
    product_name: Optional[str] = None
    model_config = {"from_attributes": True}


# ── Putaway Tasks ─────────────────────────────────────────────────────────────

class PutawayTaskCreate(BaseModel):
    warehouse_id: uuid.UUID
    product_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    lot_number: Optional[str] = None
    quantity: Decimal
    weight_kg: Optional[Decimal] = None
    volume_m3: Optional[Decimal] = None
    receipt_ref: Optional[str] = None
    notes: Optional[str] = None


class PutawayTaskRead(BaseModel):
    id: uuid.UUID
    task_no: str
    warehouse_id: uuid.UUID
    product_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    lot_number: Optional[str] = None
    quantity: Decimal
    weight_kg: Optional[Decimal] = None
    volume_m3: Optional[Decimal] = None
    suggested_location_id: Optional[uuid.UUID] = None
    assigned_to: Optional[uuid.UUID] = None
    status: PutawayTaskStatus
    receipt_ref: Optional[str] = None
    override_reason: Optional[str] = None
    notes: Optional[str] = None
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    material_name: Optional[str] = None
    suggested_location_code: Optional[str] = None
    warehouse_name: Optional[str] = None
    assignee_name: Optional[str] = None
    model_config = {"from_attributes": True}


# ── Putaway Execution ─────────────────────────────────────────────────────────

class PutawayExecuteRequest(BaseModel):
    actual_location_id: uuid.UUID
    override_reason: Optional[str] = None
    notes: Optional[str] = None


class PutawayExecutionRead(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    actual_location_id: uuid.UUID
    executed_by: Optional[uuid.UUID] = None
    executed_at: datetime
    is_variance: bool
    notes: Optional[str] = None
    actual_location_code: Optional[str] = None
    model_config = {"from_attributes": True}


# ── Suggest Location ──────────────────────────────────────────────────────────

class SuggestLocationResult(BaseModel):
    location_id: Optional[uuid.UUID] = None
    location_code: Optional[str] = None
    zone_name: Optional[str] = None
    rule_applied: Optional[str] = None
    confidence: str = "AUTO"


# ── Picking Tasks ──────────────────────────────────────────────────────────────

class PickingTaskCreate(BaseModel):
    task_no: str
    warehouse_id: uuid.UUID
    shipment_id: Optional[uuid.UUID] = None
    product_id: uuid.UUID
    lot_id: Optional[uuid.UUID] = None
    from_location_id: Optional[uuid.UUID] = None
    requested_qty: Decimal
    unit: str = "PCS"
    assigned_to_id: Optional[uuid.UUID] = None
    fefo_enforced: bool = True
    notes: Optional[str] = None


class PickingTaskUpdate(BaseModel):
    status: Optional[PickingTaskStatus] = None
    picked_qty: Optional[Decimal] = None
    assigned_to_id: Optional[uuid.UUID] = None
    from_location_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class PickingTaskRead(BaseModel):
    id: uuid.UUID
    task_no: str
    warehouse_id: uuid.UUID
    warehouse_name: Optional[str] = None
    shipment_id: Optional[uuid.UUID]
    product_id: uuid.UUID
    product_name: Optional[str] = None
    lot_id: Optional[uuid.UUID]
    lot_number: Optional[str] = None
    from_location_id: Optional[uuid.UUID]
    from_location_code: Optional[str] = None
    requested_qty: Decimal
    unit: str
    picked_qty: Optional[Decimal]
    assigned_to_id: Optional[uuid.UUID]
    assignee_name: Optional[str] = None
    status: PickingTaskStatus
    fefo_enforced: bool
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Packing Records ────────────────────────────────────────────────────────────

class PackingRecordCreate(BaseModel):
    packing_no: str
    warehouse_id: uuid.UUID
    shipment_id: Optional[uuid.UUID] = None
    box_count: int = 1
    pallet_count: int = 0
    total_weight_kg: Optional[Decimal] = None
    total_volume_m3: Optional[Decimal] = None
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    notes: Optional[str] = None


class PackingRecordUpdate(BaseModel):
    box_count: Optional[int] = None
    pallet_count: Optional[int] = None
    total_weight_kg: Optional[Decimal] = None
    total_volume_m3: Optional[Decimal] = None
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    status: Optional[PackingStatus] = None
    notes: Optional[str] = None


class PackingRecordRead(BaseModel):
    id: uuid.UUID
    packing_no: str
    shipment_id: Optional[uuid.UUID]
    warehouse_id: uuid.UUID
    warehouse_name: Optional[str] = None
    box_count: int
    pallet_count: int
    total_weight_kg: Optional[Decimal]
    total_volume_m3: Optional[Decimal]
    carrier: Optional[str]
    tracking_number: Optional[str]
    status: PackingStatus
    packed_by_id: Optional[uuid.UUID]
    packed_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Replenishment Tasks ────────────────────────────────────────────────────────

class ReplenishmentTaskCreate(BaseModel):
    task_no: str
    warehouse_id: uuid.UUID
    location_id: uuid.UUID
    product_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    current_qty: Decimal = Decimal("0")
    min_qty: Decimal
    requested_qty: Decimal
    unit: str = "PCS"
    assigned_to_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class ReplenishmentTaskUpdate(BaseModel):
    status: Optional[ReplenishmentStatus] = None
    fulfilled_qty: Optional[Decimal] = None
    assigned_to_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class ReplenishmentTaskRead(BaseModel):
    id: uuid.UUID
    task_no: str
    warehouse_id: uuid.UUID
    warehouse_name: Optional[str] = None
    location_id: uuid.UUID
    location_code: Optional[str] = None
    product_id: Optional[uuid.UUID]
    product_name: Optional[str] = None
    material_id: Optional[uuid.UUID]
    current_qty: Decimal
    min_qty: Decimal
    requested_qty: Decimal
    fulfilled_qty: Decimal
    unit: str
    status: ReplenishmentStatus
    assigned_to_id: Optional[uuid.UUID]
    completed_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}
