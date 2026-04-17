import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Numeric, Boolean, Integer,
    ForeignKey, Enum, DateTime, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class ProductionPlanStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ProductionOrderStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    RELEASED = "RELEASED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class DowntimeReason(str, enum.Enum):
    BREAKDOWN = "BREAKDOWN"
    MAINTENANCE = "MAINTENANCE"
    CHANGEOVER = "CHANGEOVER"
    MATERIAL_SHORTAGE = "MATERIAL_SHORTAGE"
    QUALITY_HOLD = "QUALITY_HOLD"
    OTHER = "OTHER"


class ProductionPlan(Base, TimestampMixin):
    __tablename__ = "production_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_no = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(ProductionPlanStatus), nullable=False, default=ProductionPlanStatus.DRAFT)
    planned_date = Column(DateTime(timezone=True), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    creator = relationship("User", foreign_keys=[created_by])
    lines = relationship(
        "ProductionPlanLine",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="ProductionPlanLine.line_no",
    )


class ProductionPlanLine(Base, TimestampMixin):
    __tablename__ = "production_plan_lines"
    __table_args__ = (
        UniqueConstraint("plan_id", "line_no", name="uq_plan_line_no"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("production_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    line_no = Column(Integer, nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=False)
    target_quantity = Column(Numeric(14, 3), nullable=False)
    uom = Column(String(20), nullable=False, default="KG")
    target_warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False)
    planned_date = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    plan = relationship("ProductionPlan", back_populates="lines")
    product = relationship("Product")
    recipe = relationship("Recipe")
    target_warehouse = relationship("Warehouse")
    production_orders = relationship("ProductionOrder", back_populates="plan_line")


class ProductionOrder(Base, TimestampMixin):
    __tablename__ = "production_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_no = Column(String(50), unique=True, nullable=False, index=True)
    plan_line_id = Column(UUID(as_uuid=True), ForeignKey("production_plan_lines.id", ondelete="SET NULL"), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=False)
    planned_quantity = Column(Numeric(14, 3), nullable=False)
    actual_quantity = Column(Numeric(14, 3), nullable=True)
    batch_no = Column(String(100), nullable=True, index=True)
    uom = Column(String(20), nullable=False, default="KG")
    status = Column(Enum(ProductionOrderStatus), nullable=False, default=ProductionOrderStatus.PLANNED)
    target_warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False)
    source_warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=True)
    scheduled_start = Column(DateTime(timezone=True), nullable=False)
    scheduled_end = Column(DateTime(timezone=True), nullable=False)
    actual_start = Column(DateTime(timezone=True), nullable=True)
    actual_end = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)

    # ── Costing (populated by production_cost_service.compute_order_cost) ─────
    total_material_cost    = Column(Numeric(18, 4), nullable=True)
    total_labor_cost       = Column(Numeric(18, 4), nullable=True)
    total_machine_cost     = Column(Numeric(18, 4), nullable=True)
    total_energy_cost      = Column(Numeric(18, 4), nullable=True)
    total_cost             = Column(Numeric(18, 4), nullable=True)
    cost_per_unit          = Column(Numeric(18, 6), nullable=True)
    standard_cost_per_unit = Column(Numeric(18, 6), nullable=True)
    cost_variance_pct      = Column(Numeric(10, 4), nullable=True)
    costing_finalized_at   = Column(DateTime(timezone=True), nullable=True)

    plan_line = relationship("ProductionPlanLine", back_populates="production_orders")
    product = relationship("Product", foreign_keys=[product_id])
    recipe = relationship("Recipe")
    target_warehouse = relationship("Warehouse", foreign_keys=[target_warehouse_id])
    source_warehouse = relationship("Warehouse", foreign_keys=[source_warehouse_id])
    creator = relationship("User", foreign_keys=[created_by])
    consumptions = relationship(
        "MaterialConsumption",
        back_populates="production_order",
        cascade="all, delete-orphan",
    )
    fg_receipts = relationship(
        "FinishedGoodsReceipt",
        back_populates="production_order",
        cascade="all, delete-orphan",
    )
    downtime_logs = relationship(
        "DowntimeLog",
        back_populates="production_order",
        cascade="all, delete-orphan",
        order_by="DowntimeLog.start_time",
    )


class MaterialConsumption(Base, TimestampMixin):
    __tablename__ = "material_consumptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="SET NULL"), nullable=True)
    standard_quantity = Column(Numeric(14, 4), nullable=False)
    actual_quantity = Column(Numeric(14, 4), nullable=False)
    variance_quantity = Column(Numeric(14, 4), nullable=False, default=0)
    unit = Column(String(20), nullable=False)
    source_warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False)
    stock_movement_id = Column(UUID(as_uuid=True), ForeignKey("stock_movements.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)

    production_order = relationship("ProductionOrder", back_populates="consumptions")
    material = relationship("Material")
    lot = relationship("Lot")
    source_warehouse = relationship("Warehouse")
    stock_movement = relationship("StockMovement")


class FinishedGoodsReceipt(Base, TimestampMixin):
    __tablename__ = "finished_goods_receipts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Numeric(14, 3), nullable=False)
    uom = Column(String(20), nullable=False)
    lot_number = Column(String(100), nullable=True)
    batch_no = Column(String(100), nullable=True)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False)
    stock_movement_id = Column(UUID(as_uuid=True), ForeignKey("stock_movements.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)

    production_order = relationship("ProductionOrder", back_populates="fg_receipts")
    product = relationship("Product")
    warehouse = relationship("Warehouse")
    stock_movement = relationship("StockMovement")


class DowntimeLog(Base, TimestampMixin):
    __tablename__ = "downtime_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    machine_id = Column(String(100), nullable=True, index=True)
    reason = Column(Enum(DowntimeReason), nullable=False, default=DowntimeReason.OTHER)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    production_order = relationship("ProductionOrder", back_populates="downtime_logs")
