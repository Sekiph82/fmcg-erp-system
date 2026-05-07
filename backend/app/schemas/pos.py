from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
import uuid

from pydantic import BaseModel, ConfigDict

from app.models.pos import POSSessionStatus, POSPaymentMethod, POSSaleStatus


class POSSaleLineCreate(BaseModel):
    product_id:  uuid.UUID
    qty:         Decimal
    unit_price:  Decimal
    discount_pct: Decimal = Decimal("0")
    tax_rate:    Decimal = Decimal("16")


class POSSaleLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:           uuid.UUID
    line_no:      int
    product_id:   uuid.UUID
    product_name: Optional[str] = None
    product_sku:  Optional[str] = None
    qty:          Decimal
    unit_price:   Decimal
    discount_pct: Decimal
    tax_rate:     Decimal
    line_total:   Decimal


class POSSaleCreate(BaseModel):
    customer_id:    Optional[uuid.UUID]   = None
    payment_method: POSPaymentMethod      = POSPaymentMethod.CASH
    amount_paid:    Optional[Decimal]     = None
    mpesa_ref:      Optional[str]         = None
    notes:          Optional[str]         = None
    lines:          List[POSSaleLineCreate]


class POSSaleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:             uuid.UUID
    sale_no:        str
    session_id:     uuid.UUID
    cashier_id:     Optional[uuid.UUID]
    cashier_name:   Optional[str] = None
    customer_id:    Optional[uuid.UUID]
    customer_name:  Optional[str] = None
    payment_method: POSPaymentMethod
    status:         POSSaleStatus
    subtotal:       Decimal
    discount_total: Decimal
    tax_total:      Decimal
    sale_total:     Decimal
    amount_paid:    Optional[Decimal]
    change_given:   Optional[Decimal]
    mpesa_ref:      Optional[str]
    notes:          Optional[str]
    created_at:     datetime
    lines:          List[POSSaleLineRead] = []


class OpenSessionRequest(BaseModel):
    register_id:   str = "REGISTER-1"
    opening_float: Decimal = Decimal("0")


class CloseSessionRequest(BaseModel):
    closing_cash: Decimal
    notes:        Optional[str] = None


class POSSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                uuid.UUID
    session_no:        str
    cashier_id:        Optional[uuid.UUID]
    cashier_name:      Optional[str] = None
    register_id:       str
    status:            POSSessionStatus
    opened_at:         datetime
    closed_at:         Optional[datetime]
    opening_float:     Decimal
    closing_cash:      Optional[Decimal]
    expected_cash:     Optional[Decimal]
    cash_difference:   Optional[Decimal]
    total_sales:       Decimal
    total_transactions: int
    notes:             Optional[str]
    created_at:        datetime


class POSDashboard(BaseModel):
    today_sales_count:  int
    today_sales_total:  Decimal
    today_cash_total:   Decimal
    today_mpesa_total:  Decimal
    today_card_total:   Decimal
    open_sessions:      int
    avg_basket_value:   Optional[Decimal]
