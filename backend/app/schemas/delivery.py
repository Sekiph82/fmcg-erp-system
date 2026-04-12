from __future__ import annotations
from datetime import date, datetime
from typing import Optional, List
import uuid

from pydantic import BaseModel, ConfigDict
from app.models.delivery import TripStatus, TripOrderStatus


class TripOrderCreate(BaseModel):
    shipment_id: uuid.UUID
    delivery_sequence: int = 1
    notes: Optional[str] = None


class TripOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    shipment_id: uuid.UUID
    shipment_no: Optional[str] = None
    customer_name: Optional[str] = None
    delivery_sequence: int
    status: TripOrderStatus
    failure_reason: Optional[str]
    notes: Optional[str]


class DeliveryTripCreate(BaseModel):
    trip_no: str
    trip_date: date
    vehicle_plate: Optional[str] = None
    vehicle_type: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    warehouse_id: Optional[uuid.UUID] = None
    rep_id: Optional[uuid.UUID] = None
    capacity_kg: Optional[float] = None
    route_notes: Optional[str] = None
    orders: List[TripOrderCreate] = []


class DeliveryTripUpdate(BaseModel):
    vehicle_plate: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    status: Optional[TripStatus] = None
    route_notes: Optional[str] = None
    departed_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None


class DeliveryTripRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    trip_no: str
    trip_date: date
    vehicle_plate: Optional[str]
    vehicle_type: Optional[str]
    driver_name: Optional[str]
    driver_phone: Optional[str]
    warehouse_id: Optional[uuid.UUID]
    rep_id: Optional[uuid.UUID]
    rep_name: Optional[str] = None
    status: TripStatus
    capacity_kg: Optional[float]
    route_notes: Optional[str]
    departed_at: Optional[datetime]
    returned_at: Optional[datetime]
    created_at: datetime
    order_count: int = 0
    orders: List[TripOrderRead] = []


class ProofOfDeliveryCreate(BaseModel):
    shipment_id: uuid.UUID
    trip_order_id: Optional[uuid.UUID] = None
    received_by: Optional[str] = None
    signature_text: Optional[str] = None
    photo_url: Optional[str] = None
    delivered_at: Optional[datetime] = None
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    notes: Optional[str] = None


class ProofOfDeliveryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    shipment_id: uuid.UUID
    trip_order_id: Optional[uuid.UUID]
    received_by: Optional[str]
    signature_text: Optional[str]
    photo_url: Optional[str]
    delivered_at: Optional[datetime]
    gps_lat: Optional[float]
    gps_lng: Optional[float]
    notes: Optional[str]
    confirmed_by_id: Optional[uuid.UUID]
    created_at: datetime
