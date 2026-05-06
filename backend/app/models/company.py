import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Boolean, Integer,
    ForeignKey, Enum, DateTime, Numeric, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class CompanyUserRole(str, enum.Enum):
    ADMIN  = "ADMIN"
    USER   = "USER"
    VIEWER = "VIEWER"


class Company(Base, TimestampMixin):
    """Legal entity / business unit."""
    __tablename__ = "companies"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name             = Column(String(255), nullable=False)
    short_code       = Column(String(20), unique=True, nullable=False, index=True)
    registration_no  = Column(String(100), nullable=True)
    tax_pin          = Column(String(50),  nullable=True)   # KRA PIN for Kenya
    country          = Column(String(50),  nullable=False, default="Kenya")
    base_currency    = Column(String(10),  nullable=False, default="KES")
    address          = Column(Text,        nullable=True)
    phone            = Column(String(50),  nullable=True)
    email            = Column(String(255), nullable=True)
    website          = Column(String(255), nullable=True)
    logo_url         = Column(String(500), nullable=True)
    is_active        = Column(Boolean,     default=True, nullable=False)
    is_default       = Column(Boolean,     default=False, nullable=False)
    created_by_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_by   = relationship("User", foreign_keys=[created_by_id])
    branches     = relationship("Branch", back_populates="company", cascade="all, delete-orphan")
    user_access  = relationship("UserCompanyAccess", back_populates="company", cascade="all, delete-orphan")


class Branch(Base, TimestampMixin):
    """Physical branch / plant / office of a company."""
    __tablename__ = "branches"
    __table_args__ = (UniqueConstraint("company_id", "branch_code", name="uq_branch_code"),)

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id   = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    name         = Column(String(255), nullable=False)
    branch_code  = Column(String(20),  nullable=False)
    branch_type  = Column(String(50),  nullable=True)   # FACTORY / WAREHOUSE / OFFICE / RETAIL
    address      = Column(Text,        nullable=True)
    city         = Column(String(100), nullable=True)
    phone        = Column(String(50),  nullable=True)
    is_active    = Column(Boolean,     default=True, nullable=False)
    is_default   = Column(Boolean,     default=False, nullable=False)

    company = relationship("Company", back_populates="branches")


class UserCompanyAccess(Base, TimestampMixin):
    """Grant a user access to a specific company."""
    __tablename__ = "user_company_access"
    __table_args__ = (UniqueConstraint("user_id", "company_id", name="uq_user_company"),)

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id",    ondelete="CASCADE"), nullable=False, index=True)
    company_id  = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    role        = Column(Enum(CompanyUserRole), nullable=False, default=CompanyUserRole.USER)
    is_default  = Column(Boolean, default=False, nullable=False)
    granted_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    user       = relationship("User", foreign_keys=[user_id])
    company    = relationship("Company", back_populates="user_access")
    granted_by = relationship("User", foreign_keys=[granted_by_id])
