from __future__ import annotations
import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Boolean, Integer, Float,
    ForeignKey, Text, Enum as SAEnum, JSON, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.db.base import Base


class FieldType(str, enum.Enum):
    TEXT = "text"
    LONG_TEXT = "long_text"
    NUMBER = "number"
    DECIMAL = "decimal"
    CURRENCY = "currency"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    REFERENCE = "reference"
    FILE_ATTACHMENT = "file_attachment"
    URL = "url"
    EMAIL = "email"
    PHONE = "phone"
    COMPUTED = "computed"


class EntityType(str, enum.Enum):
    CUSTOMER = "customer"
    SUPPLIER = "supplier"
    PRODUCT = "product"
    SALES_ORDER = "sales_order"
    PURCHASE_ORDER = "purchase_order"
    PRODUCTION_ORDER = "production_order"
    EMPLOYEE = "employee"
    ASSET = "asset"
    CONTRACT = "contract"
    CRM_RECORD = "crm_record"
    EXPENSE = "expense"
    LOT = "lot"


class ValidationRuleType(str, enum.Enum):
    REQUIRED = "required"
    MIN = "min"
    MAX = "max"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    REGEX = "regex"
    UNIQUE = "unique"
    REFERENCE_EXISTS = "reference_exists"


class CFAIAgentType(str, enum.Enum):
    FIELD_DESIGN_ASSISTANT = "field_design_assistant"
    DATA_QUALITY_MONITOR = "data_quality_monitor"
    REPORTING_ASSISTANT = "reporting_assistant"


class CFAIRecStatus(str, enum.Enum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    ACTIONED = "actioned"
    DISMISSED = "dismissed"


class CustomFieldDefinition(Base):
    __tablename__ = "cf_definitions"
    __table_args__ = (
        UniqueConstraint("field_code", "entity_type", name="uq_cf_code_entity"),
    )

    custom_field_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    field_code = Column(String(100), nullable=False)
    field_label = Column(String(200), nullable=False)
    entity_type = Column(SAEnum(EntityType), nullable=False)
    field_type = Column(SAEnum(FieldType), nullable=False)
    help_text = Column(Text)
    placeholder = Column(String(200))
    default_value = Column(String(500))
    required_flag = Column(Boolean, default=False)
    unique_flag = Column(Boolean, default=False)
    searchable_flag = Column(Boolean, default=True)
    filterable_flag = Column(Boolean, default=True)
    reportable_flag = Column(Boolean, default=True)
    importable_flag = Column(Boolean, default=True)
    exportable_flag = Column(Boolean, default=True)
    sensitive_flag = Column(Boolean, default=False)
    active_flag = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    section_label = Column(String(100))
    reference_entity = Column(String(50))
    formula = Column(Text)
    created_by = Column(String(100), default="system")
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    options = relationship(
        "CustomFieldOption", back_populates="field", cascade="all, delete-orphan",
        order_by="CustomFieldOption.display_order",
    )
    validation_rules = relationship(
        "CustomFieldValidationRule", back_populates="field", cascade="all, delete-orphan"
    )


class CustomFieldOption(Base):
    __tablename__ = "cf_options"

    option_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    custom_field_id = Column(
        String(36), ForeignKey("cf_definitions.custom_field_id", ondelete="CASCADE"), nullable=False
    )
    option_value = Column(String(100), nullable=False)
    option_label = Column(String(200), nullable=False)
    display_order = Column(Integer, default=0)
    active_flag = Column(Boolean, default=True)

    field = relationship("CustomFieldDefinition", back_populates="options")


class CustomFieldValue(Base):
    __tablename__ = "cf_values"
    __table_args__ = (
        UniqueConstraint("custom_field_id", "entity_id", name="uq_cf_value"),
    )

    value_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    custom_field_id = Column(
        String(36), ForeignKey("cf_definitions.custom_field_id", ondelete="CASCADE"), nullable=False
    )
    entity_type = Column(SAEnum(EntityType), nullable=False)
    entity_id = Column(String(36), nullable=False)
    value_text = Column(Text)
    value_number = Column(Float)
    value_date = Column(DateTime)
    value_boolean = Column(Boolean)
    value_json = Column(JSON)
    file_ref = Column(String(500))
    updated_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CustomFieldValidationRule(Base):
    __tablename__ = "cf_validation_rules"

    validation_rule_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    custom_field_id = Column(
        String(36), ForeignKey("cf_definitions.custom_field_id", ondelete="CASCADE"), nullable=False
    )
    rule_type = Column(SAEnum(ValidationRuleType), nullable=False)
    rule_value = Column(String(500))
    error_message = Column(String(300))
    active_flag = Column(Boolean, default=True)

    field = relationship("CustomFieldDefinition", back_populates="validation_rules")


class CFAIRecommendation(Base):
    __tablename__ = "cf_ai_recommendations"

    rec_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_type = Column(SAEnum(CFAIAgentType), nullable=False)
    entity_type = Column(String(50), nullable=True)
    title = Column(String(300))
    body = Column(Text)
    score = Column(Float, nullable=True)
    status = Column(SAEnum(CFAIRecStatus), default=CFAIRecStatus.PENDING)
    rec_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
