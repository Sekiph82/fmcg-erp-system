"""Co-Packing / Toll Manufacturing models."""
from __future__ import annotations
import uuid
from datetime import datetime, date
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Text, Numeric, Integer, Boolean, DateTime, Date, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class ContractType(str, PyEnum):
    COPACKING = "COPACKING"       # we manufacture for customer's brand
    TOLL_MFG = "TOLL_MFG"         # customer supplies materials, we process
    PRIVATE_LABEL = "PRIVATE_LABEL"


class CoPackingContractStatus(str, PyEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    EXPIRED = "EXPIRED"
    TERMINATED = "TERMINATED"


class ToolStatus(str, PyEnum):
    ACTIVE = "ACTIVE"
    IN_REPAIR = "IN_REPAIR"
    RETIRED = "RETIRED"
    RETURNED = "RETURNED"


class CoPackingContract(Base):
    """Co-packing or toll manufacturing agreement with a customer/brand owner."""
    __tablename__ = "copacking_contracts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_ref = Column(String(50), unique=True, nullable=False, index=True)
    contract_type = Column(Enum(ContractType), nullable=False, default=ContractType.COPACKING)
    customer_name = Column(String(300), nullable=False)
    customer_id = Column(String(100), nullable=True)          # soft FK to customers
    brand_name = Column(String(200), nullable=True)
    product_description = Column(Text, nullable=True)
    sku_count = Column(Integer, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    minimum_order_qty = Column(Numeric(14, 3), nullable=True)
    moq_uom = Column(String(20), default="KG", nullable=False)
    processing_fee_per_unit = Column(Numeric(12, 4), nullable=True)
    currency = Column(String(10), default="KES", nullable=False)
    status = Column(Enum(CoPackingContractStatus), nullable=False, default=CoPackingContractStatus.DRAFT)
    quality_standards = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    runs = relationship("CoPackingRun", back_populates="contract", cascade="all, delete-orphan")
    tools = relationship("CustomerTool", back_populates="contract", cascade="all, delete-orphan")


class CoPackingRun(Base):
    """A production run under a co-packing contract."""
    __tablename__ = "copacking_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_ref = Column(String(50), unique=True, nullable=False, index=True)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("copacking_contracts.id", ondelete="CASCADE"), nullable=False)
    run_date = Column(Date, nullable=False)
    qty_planned = Column(Numeric(14, 3), nullable=True)
    qty_produced = Column(Numeric(14, 3), nullable=True)
    uom = Column(String(20), default="KG", nullable=False)
    batch_ref = Column(String(100), nullable=True)
    processing_fee_total = Column(Numeric(14, 2), nullable=True)
    materials_supplied_by_customer = Column(Boolean, default=False)
    quality_passed = Column(Boolean, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    contract = relationship("CoPackingContract", back_populates="runs")


class CustomerTool(Base):
    """Customer-owned tool/mould/die held at our facility for co-packing."""
    __tablename__ = "customer_tools"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tool_ref = Column(String(50), unique=True, nullable=False, index=True)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("copacking_contracts.id", ondelete="SET NULL"), nullable=True)
    customer_name = Column(String(300), nullable=False)
    tool_name = Column(String(200), nullable=False)
    tool_description = Column(Text, nullable=True)
    tool_type = Column(String(100), nullable=True)       # mould | die | jig | fixture
    serial_number = Column(String(100), nullable=True)
    date_received = Column(Date, nullable=True)
    status = Column(Enum(ToolStatus), nullable=False, default=ToolStatus.ACTIVE)
    units_produced = Column(Integer, default=0, nullable=False)
    max_units_life = Column(Integer, nullable=True)       # tool lifecycle limit
    depreciation_per_unit = Column(Numeric(10, 4), nullable=True)
    storage_location = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    contract = relationship("CoPackingContract", back_populates="tools")
