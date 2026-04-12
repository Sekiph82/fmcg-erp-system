import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Numeric, Boolean, Integer,
    ForeignKey, Enum, DateTime, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class ZoneType(str, enum.Enum):
    RAW_MATERIAL = "RAW_MATERIAL"
    SEMI_FINISHED = "SEMI_FINISHED"
    FINISHED_GOODS = "FINISHED_GOODS"
    QUARANTINE = "QUARANTINE"
    RETURNS = "RETURNS"
    STAGING = "STAGING"


class StockCountType(str, enum.Enum):
    CYCLE = "CYCLE"
    FULL = "FULL"


class StockCountStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    CANCELLED = "CANCELLED"


class WarehouseZone(Base, TimestampMixin):
    __tablename__ = "warehouse_zones"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "code", name="uq_zone_warehouse_code"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    zone_type = Column(Enum(ZoneType), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    warehouse = relationship("Warehouse")
    locations = relationship(
        "StorageLocation",
        back_populates="zone",
        cascade="all, delete-orphan",
        order_by="StorageLocation.code",
    )


class StorageLocation(Base, TimestampMixin):
    __tablename__ = "storage_locations"
    __table_args__ = (
        UniqueConstraint("zone_id", "code", name="uq_location_zone_code"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("warehouse_zones.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    barcode = Column(String(100), unique=True, nullable=True, index=True)
    max_weight_kg = Column(Numeric(10, 2), nullable=True)
    max_volume_m3 = Column(Numeric(10, 4), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_blocked = Column(Boolean, default=False, nullable=False)

    zone = relationship("WarehouseZone", back_populates="locations")
    # stocks relationship defined via Stock.location_id FK


class StockCount(Base, TimestampMixin):
    __tablename__ = "stock_counts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    count_no = Column(String(50), unique=True, nullable=False, index=True)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("warehouse_zones.id", ondelete="SET NULL"), nullable=True)
    count_type = Column(Enum(StockCountType), nullable=False, default=StockCountType.CYCLE)
    status = Column(Enum(StockCountStatus), nullable=False, default=StockCountStatus.DRAFT)
    scheduled_date = Column(DateTime(timezone=True), nullable=False)
    completed_date = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)

    warehouse = relationship("Warehouse")
    zone = relationship("WarehouseZone")
    creator = relationship("User", foreign_keys=[created_by])
    approver = relationship("User", foreign_keys=[approved_by])
    lines = relationship(
        "StockCountLine",
        back_populates="count",
        cascade="all, delete-orphan",
        order_by="StockCountLine.id",
    )


class StockCountLine(Base, TimestampMixin):
    __tablename__ = "stock_count_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    count_id = Column(UUID(as_uuid=True), ForeignKey("stock_counts.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=True)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="SET NULL"), nullable=True)
    location_id = Column(UUID(as_uuid=True), ForeignKey("storage_locations.id", ondelete="SET NULL"), nullable=True)
    system_quantity = Column(Numeric(14, 3), nullable=False)
    counted_quantity = Column(Numeric(14, 3), nullable=True)
    variance = Column(Numeric(14, 3), nullable=True)
    unit = Column(String(20), nullable=False, default="KG")
    is_counted = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)

    count = relationship("StockCount", back_populates="lines")
    product = relationship("Product")
    material = relationship("Material")
    lot = relationship("Lot")
    location = relationship("StorageLocation")
