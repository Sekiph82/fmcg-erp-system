from __future__ import annotations

from datetime import date, datetime
from typing import Optional, List
import uuid

from pydantic import BaseModel, ConfigDict

from app.models.inventory import SerialStatus


class SerialNumberCreate(BaseModel):
    serial_no: str
    product_id: uuid.UUID
    lot_id: Optional[uuid.UUID] = None
    warehouse_id: Optional[uuid.UUID] = None
    warranty_expiry: Optional[date] = None
    notes: Optional[str] = None


class SerialBulkCreate(BaseModel):
    serials: List[SerialNumberCreate]


class SerialNumberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    serial_no: str
    product_id: uuid.UUID
    lot_id: Optional[uuid.UUID]
    warehouse_id: Optional[uuid.UUID]
    status: SerialStatus
    warranty_expiry: Optional[date]
    notes: Optional[str]
    created_at: datetime
    product_name: Optional[str] = None
    lot_number: Optional[str] = None
    warehouse_name: Optional[str] = None


class SerialTransferRequest(BaseModel):
    to_status: SerialStatus
    to_warehouse_id: Optional[uuid.UUID] = None
    reference_type: Optional[str] = None
    reference_no: Optional[str] = None


class SerialMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    serial_id: uuid.UUID
    from_status: Optional[SerialStatus]
    to_status: SerialStatus
    from_warehouse_id: Optional[uuid.UUID]
    to_warehouse_id: Optional[uuid.UUID]
    reference_type: Optional[str]
    reference_no: Optional[str]
    created_at: datetime
    from_warehouse_name: Optional[str] = None
    to_warehouse_name: Optional[str] = None
    moved_by_username: Optional[str] = None
