import uuid
from sqlalchemy import Column, String, Text, Numeric, Boolean, Integer, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum


class SupplierPaymentMethod(str, enum.Enum):
    BANK = "bank"
    CASH = "cash"
    MPESA = "mpesa"

from app.db.base import Base, TimestampMixin


class UnitOfMeasure(str, enum.Enum):
    PCS = "PCS"
    KG = "KG"
    G = "G"
    L = "L"
    ML = "ML"
    BOX = "BOX"
    CARTON = "CARTON"
    PALLET = "PALLET"


class ProductCategory(str, enum.Enum):
    FOOD = "FOOD"
    BEVERAGE = "BEVERAGE"
    PERSONAL_CARE = "PERSONAL_CARE"
    HOUSEHOLD = "HOUSEHOLD"
    OTHER = "OTHER"


class MaterialType(str, enum.Enum):
    RAW = "RAW"
    PACKAGING = "PACKAGING"
    SEMI_FINISHED = "SEMI_FINISHED"
    CONSUMABLE = "CONSUMABLE"


class WarehouseType(str, enum.Enum):
    FINISHED_GOODS = "FINISHED_GOODS"
    RAW_MATERIAL = "RAW_MATERIAL"
    TRANSIT = "TRANSIT"
    RETURNS = "RETURNS"


class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    contact_person = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    tax_id = Column(String(100), nullable=True)
    payment_terms_days = Column(Integer, default=30, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    lead_time_days = Column(Integer, default=0, nullable=False)
    is_preferred = Column(Boolean, default=False, nullable=False)
    performance_score = Column(Numeric(5, 2), nullable=True)
    compliance_notes = Column(Text, nullable=True)
    preferred_payment_method = Column(Enum(SupplierPaymentMethod), nullable=True)
    mpesa_phone_number = Column(String(20), nullable=True)

    materials = relationship("Material", back_populates="supplier")


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku = Column(String(100), unique=True, nullable=False, index=True)
    barcode = Column(String(100), unique=True, nullable=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(Enum(ProductCategory), nullable=False)
    uom = Column(Enum(UnitOfMeasure), nullable=False, default=UnitOfMeasure.PCS)
    units_per_carton = Column(Integer, default=1, nullable=False)
    weight_kg = Column(Numeric(10, 3), nullable=True)
    shelf_life_days = Column(Integer, nullable=True)
    reorder_point = Column(Numeric(12, 3), default=0, nullable=False)
    standard_cost = Column(Numeric(14, 4), nullable=True)
    selling_price = Column(Numeric(14, 4), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    stocks = relationship("Stock", back_populates="product")


class Material(Base, TimestampMixin):
    __tablename__ = "materials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    material_type = Column(Enum(MaterialType), nullable=False)
    uom = Column(Enum(UnitOfMeasure), nullable=False, default=UnitOfMeasure.KG)
    weight_kg = Column(Numeric(10, 3), nullable=True)
    reorder_point = Column(Numeric(12, 3), default=0, nullable=False)
    standard_cost = Column(Numeric(14, 4), nullable=True)
    lead_time_days = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    supplier = relationship("Supplier", back_populates="materials")

    stocks = relationship("Stock", back_populates="material")


class Warehouse(Base, TimestampMixin):
    __tablename__ = "warehouses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    warehouse_type = Column(Enum(WarehouseType), nullable=False)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    capacity_sqm = Column(Numeric(10, 2), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    stocks = relationship("Stock", back_populates="warehouse")
    movements_from = relationship("StockMovement", foreign_keys="StockMovement.source_warehouse_id", back_populates="source_warehouse")
    movements_to = relationship("StockMovement", foreign_keys="StockMovement.destination_warehouse_id", back_populates="destination_warehouse")
