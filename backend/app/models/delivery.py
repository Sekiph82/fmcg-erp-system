import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Numeric, Integer, Boolean,
    ForeignKey, Enum, Date, DateTime,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class TripStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    LOADING = "LOADING"
    IN_TRANSIT = "IN_TRANSIT"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class TripOrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    RESCHEDULED = "RESCHEDULED"


class DeliveryTrip(Base, TimestampMixin):
    """A vehicle trip to deliver multiple orders on a given day."""

    __tablename__ = "delivery_trips"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_no = Column(String(50), unique=True, nullable=False, index=True)
    trip_date = Column(Date, nullable=False)
    vehicle_plate = Column(String(50), nullable=True)
    vehicle_type = Column(String(50), nullable=True)    # e.g. "MOTORBIKE", "3-TON TRUCK"
    driver_name = Column(String(255), nullable=True)
    driver_phone = Column(String(50), nullable=True)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=True)
    rep_id = Column(UUID(as_uuid=True), ForeignKey("sales_reps.id", ondelete="SET NULL"), nullable=True)
    status = Column(Enum(TripStatus), nullable=False, default=TripStatus.PLANNED)
    capacity_kg = Column(Numeric(10, 2), nullable=True)  # max load
    route_notes = Column(Text, nullable=True)
    departed_at = Column(DateTime(timezone=True), nullable=True)
    returned_at = Column(DateTime(timezone=True), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    warehouse = relationship("Warehouse")
    created_by = relationship("User")
    orders = relationship("TripOrder", back_populates="trip",
                          cascade="all, delete-orphan",
                          order_by="TripOrder.delivery_sequence")


class TripOrder(Base, TimestampMixin):
    """Links a shipment to a delivery trip with sequence and status."""

    __tablename__ = "trip_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("delivery_trips.id", ondelete="CASCADE"), nullable=False)
    shipment_id = Column(UUID(as_uuid=True), ForeignKey("shipments.id", ondelete="RESTRICT"), nullable=False)
    delivery_sequence = Column(Integer, nullable=False, default=1)
    status = Column(Enum(TripOrderStatus), nullable=False, default=TripOrderStatus.PENDING)
    failure_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    trip = relationship("DeliveryTrip", back_populates="orders")
    shipment = relationship("Shipment")
    pod = relationship("ProofOfDelivery", back_populates="trip_order", uselist=False)


class ProofOfDelivery(Base, TimestampMixin):
    """Delivery confirmation captured at point of delivery."""

    __tablename__ = "proof_of_deliveries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_id = Column(UUID(as_uuid=True), ForeignKey("shipments.id", ondelete="RESTRICT"), nullable=False)
    trip_order_id = Column(UUID(as_uuid=True), ForeignKey("trip_orders.id", ondelete="SET NULL"), nullable=True)
    received_by = Column(String(255), nullable=True)       # name of person at delivery point
    signature_text = Column(String(255), nullable=True)    # typed confirmation / PIN
    photo_url = Column(Text, nullable=True)                # URL to uploaded photo
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    gps_lat = Column(Numeric(10, 7), nullable=True)
    gps_lng = Column(Numeric(10, 7), nullable=True)
    notes = Column(Text, nullable=True)
    confirmed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    shipment = relationship("Shipment")
    trip_order = relationship("TripOrder", back_populates="pod")
    confirmed_by = relationship("User")
