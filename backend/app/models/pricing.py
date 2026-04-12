import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Numeric, Integer, Boolean,
    ForeignKey, Enum, Date,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class PricingLevel(str, enum.Enum):
    STANDARD = "STANDARD"        # default list price
    REGION = "REGION"            # region-specific override
    DISTRIBUTOR = "DISTRIBUTOR"  # distributor price
    CUSTOMER = "CUSTOMER"        # individual customer price


class PromoType(str, enum.Enum):
    DISCOUNT = "DISCOUNT"        # % or fixed amount off
    BUNDLE = "BUNDLE"            # buy X get Y
    VOLUME = "VOLUME"            # tiered volume discount


class DiscountType(str, enum.Enum):
    PERCENTAGE = "PERCENTAGE"
    FIXED_AMOUNT = "FIXED_AMOUNT"


class PricingRule(Base, TimestampMixin):
    """
    Flexible pricing: per product, with optional scope
    (region / distributor / customer).
    Priority: CUSTOMER > DISTRIBUTOR > REGION > STANDARD
    """

    __tablename__ = "pricing_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    pricing_level = Column(Enum(PricingLevel), nullable=False, default=PricingLevel.STANDARD)
    region = Column(String(100), nullable=True)
    distributor_id = Column(UUID(as_uuid=True), ForeignKey("distributors.id", ondelete="CASCADE"), nullable=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=True)
    unit_price = Column(Numeric(14, 4), nullable=False)
    currency = Column(String(10), nullable=False, default="KES")
    min_quantity = Column(Numeric(14, 3), nullable=True)    # volume threshold
    effective_from = Column(Date, nullable=True)
    effective_to = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)

    product = relationship("Product")
    distributor = relationship("Distributor")
    customer = relationship("Customer")


class Promotion(Base, TimestampMixin):
    """Promotion / deal engine: discounts, bundles, volume offers."""

    __tablename__ = "promotions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    promo_type = Column(Enum(PromoType), nullable=False, default=PromoType.DISCOUNT)
    discount_type = Column(Enum(DiscountType), nullable=True)
    discount_value = Column(Numeric(14, 4), nullable=True)   # % or fixed amount
    min_order_value = Column(Numeric(16, 2), nullable=True)  # min cart value
    buy_quantity = Column(Integer, nullable=True)             # for BUNDLE: buy X
    get_quantity = Column(Integer, nullable=True)             # for BUNDLE: get Y free
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    region = Column(String(100), nullable=True)              # optional region scope

    products = relationship("PromotionProduct", back_populates="promotion",
                             cascade="all, delete-orphan")


class PromotionProduct(Base, TimestampMixin):
    """Products this promotion applies to."""

    __tablename__ = "promotion_products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    promotion_id = Column(UUID(as_uuid=True), ForeignKey("promotions.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    is_free_item = Column(Boolean, default=False, nullable=False)  # for BUNDLE get-free items

    promotion = relationship("Promotion", back_populates="products")
    product = relationship("Product")
