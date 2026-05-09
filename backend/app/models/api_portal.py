"""API Developer Portal — API keys and usage logging."""
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class ApiKey(Base):
    __tablename__ = "dev_api_keys"

    key_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), nullable=False, index=True)
    key_name = Column(String(200), nullable=False)
    # Store SHA-256 hash of the actual key — never store raw
    key_prefix = Column(String(10), nullable=False)
    key_hash = Column(String(256), nullable=False, unique=True)
    scopes = Column(Text, nullable=True)             # comma-separated: read,write,admin
    rate_limit_per_min = Column(Integer, default=60, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    description = Column(Text, nullable=True)


class ApiKeyUsageLog(Base):
    __tablename__ = "dev_api_key_usage_logs"

    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_id = Column(UUID(as_uuid=True), ForeignKey("dev_api_keys.key_id", ondelete="CASCADE"), nullable=False, index=True)
    endpoint = Column(String(500), nullable=True)
    method = Column(String(10), nullable=True)
    status_code = Column(Integer, nullable=True)
    response_ms = Column(Integer, nullable=True)
    ip_address = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
