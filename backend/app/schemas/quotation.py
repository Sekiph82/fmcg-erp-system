from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
import uuid

from pydantic import BaseModel, ConfigDict

from app.models.quotation import QuoteStatus


class QuotationLineCreate(BaseModel):
    line_no:      int
    product_id:   Optional[uuid.UUID] = None
    description:  Optional[str]       = None
    qty:          Decimal
    unit:         str = "PCS"
    unit_price:   Decimal
    discount_pct: Decimal = Decimal("0")
    tax_rate:     Decimal = Decimal("0")


class QuotationLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:           uuid.UUID
    line_no:      int
    product_id:   Optional[uuid.UUID]
    product_sku:  Optional[str]  = None
    product_name: Optional[str]  = None
    description:  Optional[str]
    qty:          Decimal
    unit:         str
    unit_price:   Decimal
    discount_pct: Decimal
    tax_rate:     Decimal
    line_total:   Decimal


class QuotationCreate(BaseModel):
    customer_id:   uuid.UUID
    quote_date:    date
    valid_until:   Optional[date]    = None
    currency:      str               = "KES"
    discount_pct:  Decimal           = Decimal("0")
    notes:         Optional[str]     = None
    internal_notes: Optional[str]   = None
    lines:         List[QuotationLineCreate] = []


class QuotationUpdate(BaseModel):
    valid_until:   Optional[date]   = None
    currency:      Optional[str]    = None
    discount_pct:  Optional[Decimal] = None
    notes:         Optional[str]    = None
    internal_notes: Optional[str]  = None
    lines:         Optional[List[QuotationLineCreate]] = None


class QuotationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:              uuid.UUID
    quote_no:        str
    version:         int
    customer_id:     uuid.UUID
    customer_name:   Optional[str]  = None
    customer_code:   Optional[str]  = None
    status:          QuoteStatus
    quote_date:      date
    valid_until:     Optional[date]
    currency:        str
    discount_pct:    Decimal
    total_amount:    Optional[Decimal]
    tax_amount:      Optional[Decimal]
    grand_total:     Optional[Decimal]
    sent_at:         Optional[datetime]
    accepted_at:     Optional[datetime]
    rejected_at:     Optional[datetime]
    lost_reason:     Optional[str]
    converted_so_id: Optional[uuid.UUID]
    created_by_id:   Optional[uuid.UUID]
    notes:           Optional[str]
    created_at:      datetime
    lines:           List[QuotationLineRead] = []


class QuoteRejectRequest(BaseModel):
    lost_reason: Optional[str] = None


class QuoteDashboard(BaseModel):
    total_quotes:     int
    draft_count:      int
    sent_count:       int
    accepted_count:   int
    rejected_count:   int
    expired_count:    int
    converted_count:  int
    win_rate_pct:     Optional[Decimal]
    total_pipeline:   Decimal    # sum of grand_total for SENT quotes
