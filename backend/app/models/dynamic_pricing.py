"""Dynamic / AI Pricing Engine — competitor tracking and price recommendations."""
from __future__ import annotations
import uuid
from datetime import datetime, date
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Text, Numeric, Boolean, DateTime, Date, Enum, Integer
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class PriceChannel(str, PyEnum):
    MODERN_TRADE = "MODERN_TRADE"
    DISTRIBUTOR = "DISTRIBUTOR"
    EXPORT = "EXPORT"
    VAN_SALES = "VAN_SALES"
    ONLINE = "ONLINE"
    WHOLESALE = "WHOLESALE"


class RecommendationStatus(str, PyEnum):
    PENDING = "PENDING"
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class CompetitorPrice(Base):
    """Manual or imported competitor price observation."""
    __tablename__ = "dp_competitor_prices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_name = Column(String(300), nullable=False, index=True)
    our_sku = Column(String(100), nullable=True)            # links to our product SKU
    competitor_name = Column(String(200), nullable=False)
    competitor_sku = Column(String(100), nullable=True)
    price = Column(Numeric(14, 4), nullable=False)
    currency = Column(String(10), default="KES", nullable=False)
    channel = Column(Enum(PriceChannel), nullable=False, default=PriceChannel.MODERN_TRADE)
    pack_size = Column(String(100), nullable=True)
    observed_date = Column(Date, nullable=False)
    source = Column(String(200), nullable=True)             # field rep | web scrape | nielsen | manual
    location = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    recorded_by = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PriceRecommendation(Base):
    """AI/rule-based price recommendation per product + channel."""
    __tablename__ = "dp_price_recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(String(100), nullable=True, index=True)    # soft FK
    product_name = Column(String(300), nullable=False)
    our_sku = Column(String(100), nullable=True)
    channel = Column(Enum(PriceChannel), nullable=False)
    current_price = Column(Numeric(14, 4), nullable=True)
    recommended_price = Column(Numeric(14, 4), nullable=False)
    floor_price = Column(Numeric(14, 4), nullable=True)    # min margin protection
    avg_competitor_price = Column(Numeric(14, 4), nullable=True)
    margin_pct = Column(Numeric(7, 3), nullable=True)       # estimated margin %
    confidence_score = Column(Integer, nullable=True)       # 0–100
    rationale = Column(Text, nullable=True)
    trigger = Column(String(100), nullable=True)            # COMPETITOR_UNDERCUT | LOW_MARGIN | HIGH_DEMAND | MANUAL
    status = Column(Enum(RecommendationStatus), nullable=False, default=RecommendationStatus.PENDING)
    applied_by = Column(String(200), nullable=True)
    applied_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
