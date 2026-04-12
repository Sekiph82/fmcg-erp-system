import uuid
import enum
from sqlalchemy import Column, String, Text, Numeric, Integer, Boolean, ForeignKey, Enum, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class DistributorStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class Distributor(Base, TimestampMixin):
    """Distributor / dealer in the distribution network."""

    __tablename__ = "distributors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    contact_person = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)   # e.g. "Nairobi", "Mombasa", "Western"
    territory = Column(Text, nullable=True)        # free-text description of coverage area
    credit_limit = Column(Numeric(16, 2), nullable=True)
    payment_terms_days = Column(Integer, default=30, nullable=False)
    currency = Column(String(10), nullable=False, default="KES")
    status = Column(Enum(DistributorStatus), nullable=False, default=DistributorStatus.ACTIVE)
    notes = Column(Text, nullable=True)

    # Distributor may operate from a specific warehouse
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)
    warehouse = relationship("Warehouse")

    # Relationships
    customers = relationship("Customer", back_populates="distributor",
                             primaryjoin="Customer.distributor_id == Distributor.id",
                             foreign_keys="Customer.distributor_id")
    pricing_tiers = relationship("DistributorPricingTier", back_populates="distributor",
                                  cascade="all, delete-orphan")


class DistributorPricingTier(Base, TimestampMixin):
    """Product-level pricing override for a specific distributor."""

    __tablename__ = "distributor_pricing_tiers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    distributor_id = Column(UUID(as_uuid=True), ForeignKey("distributors.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    unit_price = Column(Numeric(14, 4), nullable=False)
    currency = Column(String(10), nullable=False, default="KES")
    min_quantity = Column(Numeric(14, 3), nullable=True)  # volume threshold
    effective_from = Column(Date, nullable=True)
    effective_to = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    distributor = relationship("Distributor", back_populates="pricing_tiers")
    product = relationship("Product")
