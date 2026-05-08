import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, DateTime, Numeric, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class LoyaltyTier(Base, TimestampMixin):
    __tablename__ = "loyalty_tiers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tier_code = Column(String(30), unique=True, nullable=False, index=True)
    tier_name = Column(String(100), nullable=False)
    min_lifetime_points = Column(Integer, nullable=False, default=0)
    points_per_100_spend = Column(Numeric(6, 2), nullable=False, default=1)
    discount_pct = Column(Numeric(5, 2), nullable=False, default=0)
    perks = Column(JSON, default=list)
    color = Column(String(20), nullable=True, default="#6b7280")
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, nullable=False)

    accounts = relationship("CustomerLoyaltyAccount", back_populates="tier")


class CustomerLoyaltyAccount(Base, TimestampMixin):
    __tablename__ = "customer_loyalty_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"),
                         nullable=False, unique=True, index=True)
    tier_id = Column(UUID(as_uuid=True), ForeignKey("loyalty_tiers.id", ondelete="SET NULL"), nullable=True)
    total_points = Column(Integer, nullable=False, default=0)
    lifetime_points = Column(Integer, nullable=False, default=0)
    enrolled_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_activity_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)

    customer = relationship("Customer", foreign_keys=[customer_id])
    tier = relationship("LoyaltyTier", back_populates="accounts")
    transactions = relationship("LoyaltyTransaction", back_populates="account",
                                cascade="all, delete-orphan",
                                order_by="LoyaltyTransaction.created_at.desc()")


class LoyaltyTransaction(Base, TimestampMixin):
    __tablename__ = "loyalty_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("customer_loyalty_accounts.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    transaction_type = Column(String(20), nullable=False)  # EARN | REDEEM | EXPIRE | BONUS | ADJUST
    points_delta = Column(Integer, nullable=False)          # positive = earn, negative = redeem/expire
    reference_type = Column(String(50), nullable=True)      # SALES_ORDER | MANUAL | PROMOTION
    reference_id = Column(String(100), nullable=True)
    description = Column(String(300), nullable=True)
    balance_after = Column(Integer, nullable=False, default=0)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    account = relationship("CustomerLoyaltyAccount", back_populates="transactions")
    created_by = relationship("User", foreign_keys=[created_by_id])
