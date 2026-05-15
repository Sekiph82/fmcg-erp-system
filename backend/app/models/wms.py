import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Numeric, Boolean, Integer,
    ForeignKey, Enum, DateTime, UniqueConstraint, CheckConstraint,
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


class LocationType(str, enum.Enum):
    RACK = "RACK"
    BIN = "BIN"
    FLOOR = "FLOOR"
    COLD_STORAGE = "COLD_STORAGE"


class PutawayRuleType(str, enum.Enum):
    FIXED = "FIXED"
    ZONE = "ZONE"
    CATEGORY = "CATEGORY"
    RANDOM = "RANDOM"
    NEAREST = "NEAREST"


class PutawayTaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class PickingTaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    PICKED = "PICKED"
    PACKED = "PACKED"
    CANCELLED = "CANCELLED"


class PackingStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class ReplenishmentStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class HandlingUnitType(str, enum.Enum):
    PALLET = "PALLET"
    CARTON = "CARTON"
    TOTE = "TOTE"
    CRATE = "CRATE"
    CONTAINER = "CONTAINER"


class HandlingUnitStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    ON_HOLD = "ON_HOLD"
    SHIPPED = "SHIPPED"
    CONSUMED = "CONSUMED"
    VOID = "VOID"


class PickWaveStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    RELEASED = "RELEASED"
    IN_PROGRESS = "IN_PROGRESS"
    PICKED = "PICKED"
    CANCELLED = "CANCELLED"
    CLOSED = "CLOSED"


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
    location_type = Column(Enum(LocationType), nullable=True)
    current_utilization_pct = Column(Numeric(5, 2), nullable=True, default=0)
    min_qty = Column(Numeric(14, 3), nullable=True)
    max_qty = Column(Numeric(14, 3), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_blocked = Column(Boolean, default=False, nullable=False)

    zone = relationship("WarehouseZone", back_populates="locations")
    # stocks relationship defined via Stock.location_id FK


class PutawayRule(Base, TimestampMixin):
    __tablename__ = "putaway_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_code = Column(String(50), unique=True, nullable=False, index=True)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_type = Column(Enum(PutawayRuleType), nullable=False)
    priority = Column(Integer, nullable=False, default=100)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    category = Column(String(100), nullable=True)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("warehouse_zones.id", ondelete="SET NULL"), nullable=True)
    location_id = Column(UUID(as_uuid=True), ForeignKey("storage_locations.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)

    warehouse = relationship("Warehouse")
    zone = relationship("WarehouseZone")
    location = relationship("StorageLocation", foreign_keys=[location_id])
    product = relationship("Product")


class PutawayTask(Base, TimestampMixin):
    __tablename__ = "putaway_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_no = Column(String(50), unique=True, nullable=False, index=True)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    lot_number = Column(String(100), nullable=True)
    quantity = Column(Numeric(14, 3), nullable=False)
    weight_kg = Column(Numeric(10, 2), nullable=True)
    volume_m3 = Column(Numeric(10, 4), nullable=True)
    suggested_location_id = Column(UUID(as_uuid=True), ForeignKey("storage_locations.id", ondelete="SET NULL"), nullable=True)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(Enum(PutawayTaskStatus), nullable=False, default=PutawayTaskStatus.PENDING)
    receipt_ref = Column(String(100), nullable=True)
    override_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    warehouse = relationship("Warehouse")
    product = relationship("Product")
    material = relationship("Material")
    suggested_location = relationship("StorageLocation", foreign_keys=[suggested_location_id])
    assignee = relationship("User", foreign_keys=[assigned_to])
    execution = relationship("PutawayExecution", back_populates="task", uselist=False)


class PutawayExecution(Base, TimestampMixin):
    __tablename__ = "putaway_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("putaway_tasks.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    actual_location_id = Column(UUID(as_uuid=True), ForeignKey("storage_locations.id", ondelete="RESTRICT"), nullable=False)
    executed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    executed_at = Column(DateTime(timezone=True), nullable=False)
    is_variance = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)

    task = relationship("PutawayTask", back_populates="execution")
    actual_location = relationship("StorageLocation", foreign_keys=[actual_location_id])
    executor = relationship("User", foreign_keys=[executed_by])


class HandlingUnit(Base, TimestampMixin):
    __tablename__ = "wms_handling_units"
    __table_args__ = (
        UniqueConstraint("license_plate", name="uq_wms_handling_units_license_plate"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    license_plate = Column(String(100), nullable=False, unique=True, index=True)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True)
    location_id = Column(UUID(as_uuid=True), ForeignKey("storage_locations.id", ondelete="SET NULL"), nullable=True, index=True)
    parent_hu_id = Column(UUID(as_uuid=True), ForeignKey("wms_handling_units.id", ondelete="SET NULL"), nullable=True, index=True)
    hu_type = Column(Enum(HandlingUnitType, name="wms_handling_unit_type"), nullable=False)
    status = Column(Enum(HandlingUnitStatus, name="wms_handling_unit_status"), nullable=False, default=HandlingUnitStatus.OPEN, index=True)
    gross_weight_kg = Column(Numeric(12, 3), nullable=True)
    net_weight_kg = Column(Numeric(12, 3), nullable=True)
    volume_m3 = Column(Numeric(12, 4), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    warehouse = relationship("Warehouse")
    location = relationship("StorageLocation", foreign_keys=[location_id])
    parent = relationship("HandlingUnit", remote_side=[id], foreign_keys=[parent_hu_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    items = relationship("HandlingUnitItem", back_populates="handling_unit", cascade="all, delete-orphan")


class HandlingUnitItem(Base, TimestampMixin):
    __tablename__ = "wms_handling_unit_items"
    __table_args__ = (
        CheckConstraint(
            "(stock_type = 'PRODUCT' AND product_id IS NOT NULL AND material_id IS NULL) OR "
            "(stock_type = 'MATERIAL' AND material_id IS NOT NULL AND product_id IS NULL)",
            name="ck_wms_hu_items_stock_type_item",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    handling_unit_id = Column(UUID(as_uuid=True), ForeignKey("wms_handling_units.id", ondelete="CASCADE"), nullable=False, index=True)
    stock_type = Column(Enum("PRODUCT", "MATERIAL", name="stocktype"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=True, index=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=True, index=True)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="SET NULL"), nullable=True, index=True)
    quantity = Column(Numeric(14, 3), nullable=False)
    unit = Column(String(20), nullable=False)

    handling_unit = relationship("HandlingUnit", back_populates="items")
    product = relationship("Product")
    material = relationship("Material")
    lot = relationship("Lot")


class PickWave(Base, TimestampMixin):
    __tablename__ = "wms_pick_waves"
    __table_args__ = (
        UniqueConstraint("wave_no", name="uq_wms_pick_waves_wave_no"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wave_no = Column(String(50), nullable=False, unique=True, index=True)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True)
    status = Column(Enum(PickWaveStatus, name="wms_pick_wave_status"), nullable=False, default=PickWaveStatus.DRAFT, index=True)
    priority = Column(Integer, nullable=False, default=100)
    planned_start_at = Column(DateTime(timezone=True), nullable=True, index=True)
    planned_end_at = Column(DateTime(timezone=True), nullable=True)
    released_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    released_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    warehouse = relationship("Warehouse")
    released_by = relationship("User", foreign_keys=[released_by_id])
    tasks = relationship("PickingTask", back_populates="wave")


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


class PickingTask(Base, TimestampMixin):
    __tablename__ = "wms_picking_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_no = Column(String(50), unique=True, nullable=False, index=True)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False)
    shipment_id = Column(UUID(as_uuid=True), ForeignKey("shipments.id", ondelete="SET NULL"), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="SET NULL"), nullable=True)
    from_location_id = Column(UUID(as_uuid=True), ForeignKey("storage_locations.id", ondelete="SET NULL"), nullable=True)
    wave_id = Column(UUID(as_uuid=True), ForeignKey("wms_pick_waves.id", ondelete="SET NULL"), nullable=True, index=True)
    requested_qty = Column(Numeric(14, 3), nullable=False)
    unit = Column(String(20), nullable=False, default="PCS")
    picked_qty = Column(Numeric(14, 3), nullable=True)
    assigned_to_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(Enum(PickingTaskStatus), nullable=False, default=PickingTaskStatus.PENDING)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    fefo_enforced = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)

    warehouse = relationship("Warehouse")
    product = relationship("Product")
    lot = relationship("Lot")
    from_location = relationship("StorageLocation", foreign_keys=[from_location_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    wave = relationship("PickWave", back_populates="tasks")


class PackingRecord(Base, TimestampMixin):
    __tablename__ = "wms_packing_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    packing_no = Column(String(50), unique=True, nullable=False, index=True)
    shipment_id = Column(UUID(as_uuid=True), ForeignKey("shipments.id", ondelete="SET NULL"), nullable=True)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False)
    box_count = Column(Integer, nullable=False, default=1)
    pallet_count = Column(Integer, nullable=False, default=0)
    total_weight_kg = Column(Numeric(10, 2), nullable=True)
    total_volume_m3 = Column(Numeric(10, 4), nullable=True)
    carrier = Column(String(100), nullable=True)
    tracking_number = Column(String(100), nullable=True)
    status = Column(Enum(PackingStatus), nullable=False, default=PackingStatus.OPEN)
    packed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    packed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    warehouse = relationship("Warehouse")
    packed_by = relationship("User", foreign_keys=[packed_by_id])


class ReplenishmentTask(Base, TimestampMixin):
    __tablename__ = "wms_replenishment_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_no = Column(String(50), unique=True, nullable=False, index=True)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False)
    location_id = Column(UUID(as_uuid=True), ForeignKey("storage_locations.id", ondelete="RESTRICT"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    current_qty = Column(Numeric(14, 3), nullable=False, default=0)
    min_qty = Column(Numeric(14, 3), nullable=False)
    requested_qty = Column(Numeric(14, 3), nullable=False)
    fulfilled_qty = Column(Numeric(14, 3), nullable=False, default=0)
    unit = Column(String(20), nullable=False, default="PCS")
    status = Column(Enum(ReplenishmentStatus), nullable=False, default=ReplenishmentStatus.PENDING)
    assigned_to_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    warehouse = relationship("Warehouse")
    location = relationship("StorageLocation")
    product = relationship("Product")
    material = relationship("Material")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
