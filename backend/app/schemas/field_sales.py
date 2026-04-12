from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
import uuid

from pydantic import BaseModel, ConfigDict
from app.models.field_sales import VehicleType, VisitOutcome


class SalesRepCreate(BaseModel):
    code: str
    name: str
    phone: Optional[str] = None
    region: Optional[str] = None
    territory: Optional[str] = None
    vehicle_type: VehicleType = VehicleType.MOTORBIKE
    user_id: Optional[uuid.UUID] = None


class SalesRepUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    region: Optional[str] = None
    territory: Optional[str] = None
    vehicle_type: Optional[VehicleType] = None
    is_active: Optional[bool] = None
    user_id: Optional[uuid.UUID] = None


class SalesRepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    name: str
    phone: Optional[str]
    region: Optional[str]
    territory: Optional[str]
    vehicle_type: VehicleType
    is_active: bool
    user_id: Optional[uuid.UUID]
    created_at: datetime


class RouteStopCreate(BaseModel):
    customer_id: uuid.UUID
    stop_sequence: int
    notes: Optional[str] = None


class RouteStopRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    customer_id: uuid.UUID
    customer_name: Optional[str] = None
    stop_sequence: int
    notes: Optional[str]


class SalesRouteCreate(BaseModel):
    code: str
    name: str
    region: Optional[str] = None
    description: Optional[str] = None
    assigned_rep_id: Optional[uuid.UUID] = None
    stops: List[RouteStopCreate] = []


class SalesRouteUpdate(BaseModel):
    name: Optional[str] = None
    region: Optional[str] = None
    description: Optional[str] = None
    assigned_rep_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None


class SalesRouteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    name: str
    region: Optional[str]
    description: Optional[str]
    assigned_rep_id: Optional[uuid.UUID]
    rep_name: Optional[str] = None
    is_active: bool
    stop_count: int = 0
    stops: List[RouteStopRead] = []


class DailyTargetCreate(BaseModel):
    rep_id: uuid.UUID
    route_id: Optional[uuid.UUID] = None
    target_date: date
    target_amount: Decimal
    target_orders: int = 0
    currency: str = "KES"
    notes: Optional[str] = None


class DailyTargetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    rep_id: uuid.UUID
    rep_name: Optional[str] = None
    route_id: Optional[uuid.UUID]
    route_name: Optional[str] = None
    target_date: date
    target_amount: Decimal
    target_orders: int
    actual_amount: Optional[Decimal]
    actual_orders: Optional[int]
    currency: str
    notes: Optional[str]


class VisitLogCreate(BaseModel):
    rep_id: uuid.UUID
    customer_id: uuid.UUID
    route_id: Optional[uuid.UUID] = None
    order_id: Optional[uuid.UUID] = None
    visit_date: date
    visited_at: Optional[datetime] = None
    outcome: VisitOutcome = VisitOutcome.NO_ORDER
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    notes: Optional[str] = None


class VisitLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    rep_id: uuid.UUID
    rep_name: Optional[str] = None
    customer_id: uuid.UUID
    customer_name: Optional[str] = None
    route_id: Optional[uuid.UUID]
    order_id: Optional[uuid.UUID]
    visit_date: date
    visited_at: Optional[datetime]
    outcome: VisitOutcome
    gps_lat: Optional[Decimal]
    gps_lng: Optional[Decimal]
    notes: Optional[str]
    created_at: datetime


class RepPerformance(BaseModel):
    rep_id: uuid.UUID
    rep_name: str
    period_start: date
    period_end: date
    total_visits: int
    orders_created: int
    total_sales_amount: Decimal
    target_amount: Decimal
    achievement_pct: float
    currency: str = "KES"
