from pydantic import BaseModel, model_validator
from typing import Optional
from decimal import Decimal
from datetime import date
import uuid

from app.models.inventory import MovementType, StockType


class LotBase(BaseModel):
    lot_number: str
    batch_number: Optional[str] = None
    manufacture_date: Optional[date] = None
    expiry_date: Optional[date] = None
    is_quarantine: bool = False
    notes: Optional[str] = None
    product_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    supplier_id: Optional[uuid.UUID] = None


class LotCreate(LotBase):
    pass


class LotUpdate(BaseModel):
    batch_number: Optional[str] = None
    expiry_date: Optional[date] = None
    is_quarantine: Optional[bool] = None
    notes: Optional[str] = None


class LotRead(LotBase):
    id: uuid.UUID
    model_config = {"from_attributes": True}


class StockRead(BaseModel):
    id: uuid.UUID
    stock_type: StockType
    warehouse_id: uuid.UUID
    product_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    lot_id: Optional[uuid.UUID] = None
    quantity_on_hand: Decimal
    quantity_reserved: Decimal
    quantity_available: Decimal

    model_config = {"from_attributes": True}


class StockMovementBase(BaseModel):
    reference_number: str
    movement_type: MovementType
    stock_type: StockType
    movement_date: date
    product_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    lot_id: Optional[uuid.UUID] = None
    source_warehouse_id: Optional[uuid.UUID] = None
    destination_warehouse_id: Optional[uuid.UUID] = None
    quantity: Decimal
    unit_cost: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def check_item_set(self):
        if self.stock_type == StockType.PRODUCT and not self.product_id:
            raise ValueError("product_id required for PRODUCT stock type")
        if self.stock_type == StockType.MATERIAL and not self.material_id:
            raise ValueError("material_id required for MATERIAL stock type")
        return self


class StockMovementCreate(StockMovementBase):
    pass


class StockMovementRead(StockMovementBase):
    id: uuid.UUID
    created_by_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}


# ── Business operation request schemas ─────────────────────────────────────────

class StockEntryRequest(BaseModel):
    """Receive stock into a warehouse (IN)."""
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: Decimal
    lot_number: Optional[str] = None
    expiry_date: Optional[date] = None
    unit_cost: Optional[Decimal] = None
    reference: str
    notes: Optional[str] = None


class StockIssueRequest(BaseModel):
    """Issue stock out of a warehouse (OUT)."""
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: Decimal
    lot_number: Optional[str] = None
    reference: str
    notes: Optional[str] = None


class StockTransferRequest(BaseModel):
    """Transfer stock between warehouses."""
    product_id: uuid.UUID
    from_warehouse_id: uuid.UUID
    to_warehouse_id: uuid.UUID
    quantity: Decimal
    lot_number: Optional[str] = None
    reference: str
    notes: Optional[str] = None


# ── Enriched read schemas ──────────────────────────────────────────────────────

class StockSummaryRead(BaseModel):
    """Stock record enriched with product/warehouse/lot names."""
    id: uuid.UUID
    stock_type: StockType
    product_id: Optional[uuid.UUID] = None
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    warehouse_id: uuid.UUID
    warehouse_code: str
    warehouse_name: str
    lot_id: Optional[uuid.UUID] = None
    lot_number: Optional[str] = None
    expiry_date: Optional[date] = None
    quantity_on_hand: Decimal
    quantity_reserved: Decimal
    quantity_available: Decimal
    is_below_reorder: bool = False

    model_config = {"from_attributes": False}


class MovementDetailRead(StockMovementRead):
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    source_warehouse_name: Optional[str] = None
    destination_warehouse_name: Optional[str] = None
    created_by_username: Optional[str] = None
