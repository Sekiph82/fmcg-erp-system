"""Delegated OAuth 2.0 connections to external providers (M43.S00.T004; used by M43.S01 mail and calendar).

One row per (user, provider, purpose). Tokens are Fernet-encrypted and wiped on disconnect; scopes and the
provider account e-mail are kept for audit. OAuth "state" rows are single-use and expire after 10 minutes.
"""
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base, TimestampMixin


class OAuthConnection(Base, TimestampMixin):
    __tablename__ = "oauth_connections"
    __table_args__ = (UniqueConstraint("user_id", "provider", "purpose", name="uq_oauth_conn_user_provider_purpose"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(20), nullable=False)          # google | microsoft
    purpose = Column(String(20), nullable=False)           # mail | calendar
    status = Column(String(20), nullable=False, default="CONNECTED")  # CONNECTED | ERROR | REVOKED
    account_email = Column(String(255), nullable=True)
    scopes = Column(JSONB, nullable=False, default=list)
    access_token_enc = Column(Text, nullable=True)
    refresh_token_enc = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    sync_cursor = Column(JSONB, nullable=True)             # provider cursor: Gmail historyId, Graph deltaLink, syncToken
    last_error = Column(String(500), nullable=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)


class OAuthState(Base):
    __tablename__ = "oauth_states"

    state = Column(String(64), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(20), nullable=False)
    purpose = Column(String(20), nullable=False)
    code_verifier_enc = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
