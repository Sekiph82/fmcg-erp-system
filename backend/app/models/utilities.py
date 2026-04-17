import uuid
import enum
from sqlalchemy import Column, String, Text, Numeric, Integer, Boolean, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class ConfigCategory(str, enum.Enum):
    COMPANY = "COMPANY"
    SYSTEM = "SYSTEM"
    FINANCE = "FINANCE"
    NOTIFICATIONS = "NOTIFICATIONS"
    OPERATIONS = "OPERATIONS"


class SystemConfig(Base, TimestampMixin):
    """Key-value system configuration store."""
    __tablename__ = "system_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(100), nullable=False, unique=True, index=True)
    value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    category = Column(Enum(ConfigCategory), nullable=False, default=ConfigCategory.SYSTEM)
    is_editable = Column(Boolean, default=True, nullable=False)

    updated_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = relationship("User", foreign_keys=[updated_by_id])


class UomConversion(Base, TimestampMixin):
    """Unit-of-measure conversion factors. factor: 1 from_uom = factor to_uom."""
    __tablename__ = "uom_conversions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_uom = Column(String(20), nullable=False)
    to_uom = Column(String(20), nullable=False)
    factor = Column(Numeric(20, 8), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by = relationship("User", foreign_keys=[created_by_id])


class NumberSeries(Base, TimestampMixin):
    """Document auto-numbering sequences. e.g. PO-0001, INV-0001."""
    __tablename__ = "number_series"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module = Column(String(60), nullable=False, unique=True, index=True)
    label = Column(String(100), nullable=False)
    prefix = Column(String(20), nullable=False)
    suffix = Column(String(20), nullable=True)
    current_number = Column(Integer, nullable=False, default=0)
    padding = Column(Integer, nullable=False, default=4)
    is_active = Column(Boolean, default=True, nullable=False)


class Currency(Base, TimestampMixin):
    """ISO 4217 currency registry with exchange rates relative to base currency."""
    __tablename__ = "currencies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(10), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    symbol = Column(String(10), nullable=False)
    exchange_rate = Column(Numeric(18, 6), nullable=False, default=1)
    is_base = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
