import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, DateTime, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class NPSSurvey(Base, TimestampMixin):
    __tablename__ = "nps_surveys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    target_type = Column(String(20), nullable=False, default="CUSTOMER")  # CUSTOMER | PRODUCT
    trigger = Column(String(20), nullable=False, default="MANUAL")  # DELIVERY | PERIODIC | MANUAL
    question_text = Column(String(500), nullable=False,
                           default="How likely are you to recommend us to a friend or colleague?")
    follow_up_text = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_by = relationship("User", foreign_keys=[created_by_id])
    responses = relationship("NPSResponse", back_populates="survey", cascade="all, delete-orphan")


class NPSResponse(Base, TimestampMixin):
    __tablename__ = "nps_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    survey_id = Column(UUID(as_uuid=True), ForeignKey("nps_surveys.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    so_id = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True)
    score = Column(Integer, nullable=False)        # 0–10
    comment = Column(Text, nullable=True)
    responded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    channel = Column(String(30), nullable=True)    # email | whatsapp | portal | manual

    survey = relationship("NPSSurvey", back_populates="responses")
    customer = relationship("Customer", foreign_keys=[customer_id])
    product = relationship("Product", foreign_keys=[product_id])
