import uuid
import enum
from datetime import date as date_type
from sqlalchemy import (
    Column, String, Text, Numeric, Integer, Boolean,
    ForeignKey, Enum, Date, DateTime, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class VehicleType(str, enum.Enum):
    MOTORBIKE = "MOTORBIKE"
    VAN = "VAN"
    TRUCK = "TRUCK"
    FOOT = "FOOT"
    OTHER = "OTHER"


class VisitOutcome(str, enum.Enum):
    ORDERED = "ORDERED"
    NO_ORDER = "NO_ORDER"
    CUSTOMER_CLOSED = "CUSTOMER_CLOSED"
    CREDIT_HOLD = "CREDIT_HOLD"
    NOT_FOUND = "NOT_FOUND"


class SalesRep(Base, TimestampMixin):
    """Field sales representative — typically a motorbike agent."""

    __tablename__ = "sales_reps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    region = Column(String(100), nullable=True)
    territory = Column(Text, nullable=True)
    vehicle_type = Column(Enum(VehicleType), nullable=False, default=VehicleType.MOTORBIKE)
    is_active = Column(Boolean, default=True, nullable=False)

    user = relationship("User")
    routes = relationship("SalesRoute", back_populates="assigned_rep",
                          primaryjoin="SalesRoute.assigned_rep_id == SalesRep.id",
                          foreign_keys="SalesRoute.assigned_rep_id")
    daily_targets = relationship("DailyTarget", back_populates="rep", cascade="all, delete-orphan")
    visit_logs = relationship("VisitLog", back_populates="rep", cascade="all, delete-orphan")


class SalesRoute(Base, TimestampMixin):
    """A named geographic route that a sales rep covers."""

    __tablename__ = "sales_routes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    region = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    assigned_rep_id = Column(UUID(as_uuid=True), ForeignKey("sales_reps.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    assigned_rep = relationship("SalesRep", back_populates="routes",
                                 foreign_keys=[assigned_rep_id])
    stops = relationship("RouteStop", back_populates="route",
                          cascade="all, delete-orphan",
                          order_by="RouteStop.stop_sequence")


class RouteStop(Base, TimestampMixin):
    """An ordered customer stop on a sales route."""

    __tablename__ = "route_stops"
    __table_args__ = (UniqueConstraint("route_id", "stop_sequence", name="uq_route_stop_seq"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_id = Column(UUID(as_uuid=True), ForeignKey("sales_routes.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    stop_sequence = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    lat_override = Column(Numeric(10, 7), nullable=True)   # overrides customer GPS if set
    lng_override = Column(Numeric(10, 7), nullable=True)
    priority_score = Column(Numeric(8, 2), nullable=True)  # higher = visit first

    route = relationship("SalesRoute", back_populates="stops")
    customer = relationship("Customer")


class DailyTarget(Base, TimestampMixin):
    """Sales target for a rep on a specific date."""

    __tablename__ = "daily_targets"
    __table_args__ = (UniqueConstraint("rep_id", "target_date", name="uq_rep_date_target"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rep_id = Column(UUID(as_uuid=True), ForeignKey("sales_reps.id", ondelete="CASCADE"), nullable=False)
    route_id = Column(UUID(as_uuid=True), ForeignKey("sales_routes.id", ondelete="SET NULL"), nullable=True)
    target_date = Column(Date, nullable=False)
    target_amount = Column(Numeric(16, 2), nullable=False, default=0)
    target_orders = Column(Integer, nullable=False, default=0)
    # Actuals are derived from orders at query time, but can be cached here
    actual_amount = Column(Numeric(16, 2), nullable=True)
    actual_orders = Column(Integer, nullable=True)
    currency = Column(String(10), nullable=False, default="KES")
    notes = Column(Text, nullable=True)

    rep = relationship("SalesRep", back_populates="daily_targets")
    route = relationship("SalesRoute")


class VisitLog(Base, TimestampMixin):
    """Records a sales rep's visit to a customer outlet."""

    __tablename__ = "visit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rep_id = Column(UUID(as_uuid=True), ForeignKey("sales_reps.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    route_id = Column(UUID(as_uuid=True), ForeignKey("sales_routes.id", ondelete="SET NULL"), nullable=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True)
    visit_date = Column(Date, nullable=False)
    visited_at = Column(DateTime(timezone=True), nullable=True)
    outcome = Column(Enum(VisitOutcome), nullable=False, default=VisitOutcome.NO_ORDER)
    gps_lat = Column(Numeric(10, 7), nullable=True)
    gps_lng = Column(Numeric(10, 7), nullable=True)
    notes = Column(Text, nullable=True)

    rep = relationship("SalesRep", back_populates="visit_logs")
    customer = relationship("Customer")
    route = relationship("SalesRoute")
    order = relationship("SalesOrder")
