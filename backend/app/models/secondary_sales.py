import uuid
import enum
from decimal import Decimal
from sqlalchemy import (
    Column, String, Text, Numeric, Boolean, Integer,
    ForeignKey, Enum, DateTime, Date, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class UploadSource(str, enum.Enum):
    POS = "POS"
    ERP_INTEGRATION = "ERP_INTEGRATION"
    MANUAL_CSV = "MANUAL_CSV"
    MOBILE = "MOBILE"
    API = "API"


class SecondarySalesStatus(str, enum.Enum):
    PENDING = "PENDING"
    VALIDATED = "VALIDATED"
    PROCESSED = "PROCESSED"
    REJECTED = "REJECTED"


class RetailChannel(str, enum.Enum):
    SUPERMARKET = "SUPERMARKET"
    KIOSK = "KIOSK"
    WHOLESALE = "WHOLESALE"
    PHARMACY = "PHARMACY"
    HOTEL = "HOTEL"
    ONLINE = "ONLINE"
    OTHER = "OTHER"


class RetailerMaster(Base, TimestampMixin):
    __tablename__ = "retailer_masters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    distributor_id = Column(UUID(as_uuid=True), ForeignKey("distributors.id", ondelete="SET NULL"), nullable=True, index=True)
    retailer_code = Column(String(50), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    location = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    channel = Column(Enum(RetailChannel), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    distributor = relationship("Distributor")
    sales_lines = relationship("SecondarySalesLine", back_populates="retailer")


class SecondarySalesHeader(Base, TimestampMixin):
    __tablename__ = "secondary_sales_headers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference_no = Column(String(50), unique=True, nullable=False, index=True)
    distributor_id = Column(UUID(as_uuid=True), ForeignKey("distributors.id", ondelete="RESTRICT"), nullable=False, index=True)
    period_from = Column(Date, nullable=False)
    period_to = Column(Date, nullable=False)
    upload_source = Column(Enum(UploadSource), nullable=False, default=UploadSource.MANUAL_CSV)
    upload_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(SecondarySalesStatus), nullable=False, default=SecondarySalesStatus.PENDING)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)
    validation_errors = Column(Text, nullable=True)
    total_lines = Column(Integer, nullable=False, default=0)
    total_value = Column(Numeric(18, 2), nullable=False, default=0)

    distributor = relationship("Distributor")
    uploader = relationship("User", foreign_keys=[uploaded_by])
    lines = relationship(
        "SecondarySalesLine",
        back_populates="header",
        cascade="all, delete-orphan",
    )


class SecondarySalesLine(Base, TimestampMixin):
    __tablename__ = "secondary_sales_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    header_id = Column(UUID(as_uuid=True), ForeignKey("secondary_sales_headers.id", ondelete="CASCADE"), nullable=False, index=True)
    retailer_id = Column(UUID(as_uuid=True), ForeignKey("retailer_masters.id", ondelete="SET NULL"), nullable=True)
    retailer_name = Column(String(255), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    product_sku = Column(String(100), nullable=True)
    quantity_sold = Column(Numeric(14, 3), nullable=False)
    unit_price = Column(Numeric(14, 4), nullable=True)
    total_value = Column(Numeric(18, 2), nullable=True)
    sale_date = Column(Date, nullable=True)
    is_valid = Column(Boolean, default=True, nullable=False)
    validation_note = Column(Text, nullable=True)

    header = relationship("SecondarySalesHeader", back_populates="lines")
    retailer = relationship("RetailerMaster", back_populates="sales_lines")
    product = relationship("Product")


class DistributorInventorySnapshot(Base, TimestampMixin):
    __tablename__ = "distributor_inventory_snapshots"
    __table_args__ = (
        UniqueConstraint("distributor_id", "product_id", "snapshot_date", name="uq_dist_inv_snapshot"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    distributor_id = Column(UUID(as_uuid=True), ForeignKey("distributors.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    stock_qty = Column(Numeric(14, 3), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    sell_through_rate = Column(Numeric(7, 4), nullable=True)
    days_of_stock = Column(Numeric(7, 1), nullable=True)
    notes = Column(Text, nullable=True)

    distributor = relationship("Distributor")
    product = relationship("Product")
