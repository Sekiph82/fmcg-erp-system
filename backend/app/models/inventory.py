import uuid
from datetime import date
from sqlalchemy import Column, String, Numeric, Integer, ForeignKey, Enum, Date, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.db.base import Base, TimestampMixin


class MovementType(str, enum.Enum):
    RECEIPT = "RECEIPT"           # Goods received from supplier
    ISSUE = "ISSUE"               # Goods issued for production/sale
    TRANSFER = "TRANSFER"         # Warehouse transfer
    ADJUSTMENT = "ADJUSTMENT"     # Manual adjustment
    RETURN = "RETURN"             # Customer/supplier return
    WRITE_OFF = "WRITE_OFF"       # Expired/damaged write-off


class StockType(str, enum.Enum):
    PRODUCT = "PRODUCT"
    MATERIAL = "MATERIAL"


class Stock(Base, TimestampMixin):
    """Current on-hand stock per warehouse, per product/material, per lot."""
    __tablename__ = "stocks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stock_type = Column(Enum(StockType), nullable=False)

    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=True)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="RESTRICT"), nullable=True)

    quantity_on_hand = Column(Numeric(14, 3), default=0, nullable=False)
    quantity_reserved = Column(Numeric(14, 3), default=0, nullable=False)
    quantity_available = Column(Numeric(14, 3), default=0, nullable=False)
    is_blocked = Column(Boolean, default=False, nullable=False)
    location_id = Column(UUID(as_uuid=True), ForeignKey("storage_locations.id", ondelete="SET NULL"), nullable=True, index=True)

    warehouse = relationship("Warehouse", back_populates="stocks")
    product = relationship("Product", back_populates="stocks")
    material = relationship("Material", back_populates="stocks")
    lot = relationship("Lot", back_populates="stocks")


class Lot(Base, TimestampMixin):
    """Batch / lot tracking."""
    __tablename__ = "lots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lot_number = Column(String(100), nullable=False, index=True)
    batch_number = Column(String(100), nullable=True)
    manufacture_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    is_quarantine = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)

    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=True)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)

    stocks = relationship("Stock", back_populates="lot")
    movements = relationship("StockMovement", back_populates="lot")


class StockMovement(Base, TimestampMixin):
    """Every quantity change is recorded here as an immutable ledger entry."""
    __tablename__ = "stock_movements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference_number = Column(String(100), nullable=False, index=True)
    movement_type = Column(Enum(MovementType), nullable=False)
    stock_type = Column(Enum(StockType), nullable=False)
    movement_date = Column(Date, nullable=False)

    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=True)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="RESTRICT"), nullable=True)

    source_warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=True)
    destination_warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=True)

    quantity = Column(Numeric(14, 3), nullable=False)
    unit_cost = Column(Numeric(14, 4), nullable=True)
    total_cost = Column(Numeric(16, 4), nullable=True)

    notes = Column(Text, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    lot = relationship("Lot", back_populates="movements")
    source_warehouse = relationship("Warehouse", foreign_keys=[source_warehouse_id], back_populates="movements_from")
    destination_warehouse = relationship("Warehouse", foreign_keys=[destination_warehouse_id], back_populates="movements_to")
    created_by = relationship("User")
