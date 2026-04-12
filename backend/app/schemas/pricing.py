from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
import uuid

from pydantic import BaseModel, ConfigDict
from app.models.pricing import PricingLevel, PromoType, DiscountType


class PricingRuleCreate(BaseModel):
    product_id: uuid.UUID
    pricing_level: PricingLevel = PricingLevel.STANDARD
    region: Optional[str] = None
    distributor_id: Optional[uuid.UUID] = None
    customer_id: Optional[uuid.UUID] = None
    unit_price: Decimal
    currency: str = "KES"
    min_quantity: Optional[Decimal] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    notes: Optional[str] = None


class PricingRuleUpdate(BaseModel):
    unit_price: Optional[Decimal] = None
    min_quantity: Optional[Decimal] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class PricingRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: Optional[str] = None
    pricing_level: PricingLevel
    region: Optional[str]
    distributor_id: Optional[uuid.UUID]
    distributor_name: Optional[str] = None
    customer_id: Optional[uuid.UUID]
    customer_name: Optional[str] = None
    unit_price: Decimal
    currency: str
    min_quantity: Optional[Decimal]
    effective_from: Optional[date]
    effective_to: Optional[date]
    is_active: bool
    notes: Optional[str]
    created_at: datetime


class PromotionProductCreate(BaseModel):
    product_id: uuid.UUID
    is_free_item: bool = False


class PromotionCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    promo_type: PromoType = PromoType.DISCOUNT
    discount_type: Optional[DiscountType] = None
    discount_value: Optional[Decimal] = None
    min_order_value: Optional[Decimal] = None
    buy_quantity: Optional[int] = None
    get_quantity: Optional[int] = None
    start_date: date
    end_date: date
    region: Optional[str] = None
    products: List[PromotionProductCreate] = []


class PromotionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    discount_value: Optional[Decimal] = None
    min_order_value: Optional[Decimal] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None


class PromotionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    name: str
    description: Optional[str]
    promo_type: PromoType
    discount_type: Optional[DiscountType]
    discount_value: Optional[Decimal]
    min_order_value: Optional[Decimal]
    buy_quantity: Optional[int]
    get_quantity: Optional[int]
    start_date: date
    end_date: date
    is_active: bool
    region: Optional[str]
    product_ids: List[uuid.UUID] = []
    created_at: datetime
