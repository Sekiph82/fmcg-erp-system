from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
import uuid

from pydantic import BaseModel, ConfigDict
from app.models.returns_mgmt import ReturnReason, ReturnCondition, ReturnStatus


class ReturnLineCreate(BaseModel):
    product_id: uuid.UUID
    lot_id: Optional[uuid.UUID] = None
    quantity: Decimal
    unit: str = "PCS"
    unit_price: Decimal = Decimal("0")
    return_reason: Optional[ReturnReason] = None
    condition: ReturnCondition = ReturnCondition.RESALEABLE
    notes: Optional[str] = None


class ReturnLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: Optional[str] = None
    lot_id: Optional[uuid.UUID]
    quantity: Decimal
    unit: str
    unit_price: Decimal
    return_reason: Optional[ReturnReason]
    condition: ReturnCondition
    notes: Optional[str]

    @property
    def line_total(self) -> Decimal:
        return (self.quantity * self.unit_price).quantize(Decimal("0.01"))


class ReturnOrderCreate(BaseModel):
    return_no: str
    original_so_id: Optional[uuid.UUID] = None
    customer_id: uuid.UUID
    return_date: date
    reason: ReturnReason = ReturnReason.OTHER
    notes: Optional[str] = None
    lines: List[ReturnLineCreate] = []


class ReturnOrderUpdate(BaseModel):
    reason: Optional[ReturnReason] = None
    notes: Optional[str] = None
    status: Optional[ReturnStatus] = None
    credit_note_no: Optional[str] = None


class ReturnOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    return_no: str
    original_so_id: Optional[uuid.UUID]
    customer_id: uuid.UUID
    customer_name: Optional[str] = None
    return_date: date
    reason: ReturnReason
    status: ReturnStatus
    notes: Optional[str]
    credit_note_no: Optional[str]
    approved_at: Optional[datetime]
    created_at: datetime
    lines: List[ReturnLineRead] = []
    line_count: int = 0
