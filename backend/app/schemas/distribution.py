from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
import uuid

from pydantic import BaseModel, ConfigDict
from app.models.distribution import DistributorStatus


class DistributorCreate(BaseModel):
    code: str
    name: str
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    territory: Optional[str] = None
    credit_limit: Optional[Decimal] = None
    payment_terms_days: int = 30
    currency: str = "KES"
    warehouse_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class DistributorUpdate(BaseModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    territory: Optional[str] = None
    credit_limit: Optional[Decimal] = None
    payment_terms_days: Optional[int] = None
    status: Optional[DistributorStatus] = None
    warehouse_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class DistributorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    name: str
    contact_person: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    city: Optional[str]
    region: Optional[str]
    territory: Optional[str]
    credit_limit: Optional[Decimal]
    payment_terms_days: int
    currency: str
    status: DistributorStatus
    warehouse_id: Optional[uuid.UUID]
    notes: Optional[str]
    created_at: datetime


class DistributorPricingTierCreate(BaseModel):
    product_id: uuid.UUID
    unit_price: Decimal
    currency: str = "KES"
    min_quantity: Optional[Decimal] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None


class DistributorPricingTierRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    distributor_id: uuid.UUID
    product_id: uuid.UUID
    product_name: Optional[str] = None
    unit_price: Decimal
    currency: str
    min_quantity: Optional[Decimal]
    effective_from: Optional[date]
    effective_to: Optional[date]
    is_active: bool
