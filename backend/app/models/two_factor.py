from __future__ import annotations
import uuid
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Enum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class TwoFAMethod(str, PyEnum):
    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"


class TwoFASessionStatus(str, PyEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    EXPIRED = "expired"
    FAILED = "failed"


class User2FASettings(Base, TimestampMixin):
    __tablename__ = "user_2fa_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    is_enabled = Column(Boolean, default=False, nullable=False)
    method = Column(Enum(TwoFAMethod), default=TwoFAMethod.TOTP, nullable=False)
    secret_key = Column(String(64), nullable=True)       # TOTP secret
    phone_number = Column(String(20), nullable=True)     # SMS
    email = Column(String(255), nullable=True)           # email OTP override

    user = relationship("User", back_populates="two_fa_settings")
    sessions = relationship("TwoFASession", back_populates="settings", cascade="all, delete-orphan")
    recovery_codes = relationship("RecoveryCode", back_populates="settings", cascade="all, delete-orphan")


class TwoFASession(Base, TimestampMixin):
    """Short-lived challenge record created at login when 2FA is required."""
    __tablename__ = "two_fa_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    settings_id = Column(UUID(as_uuid=True), ForeignKey("user_2fa_settings.id", ondelete="CASCADE"), nullable=False)
    challenge_code = Column(String(10), nullable=True)   # for SMS/email OTP; null for TOTP
    method = Column(Enum(TwoFAMethod), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(Enum(TwoFASessionStatus), default=TwoFASessionStatus.PENDING, nullable=False)
    attempt_count = Column(String(3), default="0", nullable=False)  # stored as string to avoid import

    settings = relationship("User2FASettings", back_populates="sessions")
    user = relationship("User")


class RecoveryCode(Base, TimestampMixin):
    """One-time backup codes for 2FA recovery."""
    __tablename__ = "recovery_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    settings_id = Column(UUID(as_uuid=True), ForeignKey("user_2fa_settings.id", ondelete="CASCADE"), nullable=False)
    code_hash = Column(String(255), nullable=False)      # bcrypt hash
    used = Column(Boolean, default=False, nullable=False)

    settings = relationship("User2FASettings", back_populates="recovery_codes")
