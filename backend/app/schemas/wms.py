from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
from datetime import datetime, date
import uuid

from app.models.wms import ZoneType, StockCountType, StockCountStatus


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
    is_active: bool = True
    is_blocked: bool = False


class StorageLocationUpdate(BaseModel):
    name: Optional[str] = None
    barcode: Optional[str] = None
    max_weight_kg: Optional[Decimal] = None
    max_volume_m3: Optional[Decimal] = None
    is_active: Optional[bool] = None
    is_blocked: Optional[bool] = None


class StorageLocationRead(StorageLocationCreate):
    id: uuid.UUID
    zone_code: Optional[str] = None
    zone_name: Optional[str] = None
    zone_type: Optional[ZoneType] = None
    warehouse_id: Optional[uuid.UUID] = None
    warehouse_name: Optional[str] = None
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
