"""Market Intelligence / Competitor Tracking models."""
from __future__ import annotations
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Text, Numeric, Integer, Boolean, DateTime, Date, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base


class OutletType(str, PyEnum):
    SUPERMARKET = "SUPERMARKET"
    HYPERMARKET = "HYPERMARKET"
    CONVENIENCE = "CONVENIENCE"
    WHOLESALE = "WHOLESALE"
    KIOSK = "KIOSK"
    PHARMACY = "PHARMACY"
    ONLINE = "ONLINE"
    OTHER = "OTHER"


class MarketObservation(Base):
    """Field rep shelf-share observation at a retail outlet."""
    __tablename__ = "market_observations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    obs_ref = Column(String(50), unique=True, nullable=False, index=True)
    observer_name = Column(String(200), nullable=True)
    outlet_name = Column(String(300), nullable=False)
    outlet_type = Column(Enum(OutletType), nullable=False, default=OutletType.SUPERMARKET)
    location = Column(String(300), nullable=True)
    category = Column(String(200), nullable=False)         # e.g. Juices | Cooking Oil
    observation_date = Column(Date, nullable=False)

    # Shelf share
    our_brand = Column(String(200), nullable=True)
    our_facings = Column(Integer, nullable=True)           # number of facing positions
    total_facings = Column(Integer, nullable=True)
    our_shelf_share_pct = Column(Numeric(6, 2), nullable=True)  # computed: our/total × 100

    # Promotions observed
    our_promo_active = Column(Boolean, default=False, nullable=False)
    competitor_promo_active = Column(Boolean, default=False, nullable=False)
    competitor_promo_notes = Column(Text, nullable=True)

    # Out of stock flags
    our_oos_flag = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MarketShareEstimate(Base):
    """Monthly market share estimate per category (manual or from external source)."""
    __tablename__ = "market_share_estimates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category = Column(String(200), nullable=False, index=True)
    period_month = Column(String(7), nullable=False, index=True)  # YYYY-MM
    our_brand = Column(String(200), nullable=True)
    our_share_pct = Column(Numeric(6, 2), nullable=True)
    total_market_value_kes = Column(Numeric(18, 2), nullable=True)
    our_value_kes = Column(Numeric(18, 2), nullable=True)
    competitor_shares = Column(JSONB, nullable=True)     # {brand: share_pct}
    source = Column(String(200), nullable=True)          # field | nielsen | IRI | manual
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
