"""M45 identity: audited impersonation and notification policies (T023), staff single sign-on (T016)."""
import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class ImpersonationSession(Base):
    """A support session in which `actor` acts as `target` (never a superuser), time-boxed, with a reason."""
    __tablename__ = "auth_impersonations"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reason       = Column(String(500), nullable=False)
    started_at   = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at   = Column(DateTime(timezone=True), nullable=False)
    ended_at     = Column(DateTime(timezone=True), nullable=True)
    ended_reason = Column(String(20), nullable=True)          # ENDED | EXPIRED


class NotificationPolicy(Base):
    """Company-wide default for one notification type and channel; mandatory ones cannot be switched off by users."""
    __tablename__ = "nc_notification_policies"
    __table_args__ = (UniqueConstraint("notification_type", "channel", name="uq_nc_notification_policy"),)

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notification_type = Column(String(30), nullable=False)
    channel           = Column(String(20), nullable=False)
    default_enabled   = Column(Boolean, nullable=False, default=True)
    mandatory         = Column(Boolean, nullable=False, default=False)
    updated_by        = Column(String(100), nullable=True)
    updated_at        = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SSOConfig(Base):
    """One identity provider for staff sign-in (OIDC now; SAML stays unavailable without a maintained library)."""
    __tablename__ = "auth_sso_configs"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id      = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, unique=True)
    protocol        = Column(String(6), nullable=False, default="OIDC")
    name            = Column(String(100), nullable=False)
    issuer          = Column(String(300), nullable=False)
    client_id       = Column(String(200), nullable=False)
    client_secret   = Column(Text, nullable=True)                 # encrypted with the app key
    scopes          = Column(String(200), nullable=False, default="openid email profile")
    role_mapping    = Column(JSON, nullable=False, default=dict)  # {"idp-group": "ERP role name"}
    enforced        = Column(Boolean, nullable=False, default=False)  # password login blocked except break-glass
    break_glass     = Column(JSON, nullable=False, default=list)  # usernames still allowed to use a password
    active          = Column(Boolean, nullable=False, default=False)
    updated_by      = Column(String(100), nullable=True)
    updated_at      = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SSOState(Base):
    """One authorization request: state, nonce and PKCE verifier, single use, short-lived."""
    __tablename__ = "auth_sso_states"

    state        = Column(String(64), primary_key=True)
    config_id    = Column(UUID(as_uuid=True), ForeignKey("auth_sso_configs.id", ondelete="CASCADE"), nullable=False)
    nonce        = Column(String(64), nullable=False)
    verifier     = Column(String(128), nullable=False)
    redirect_to  = Column(String(300), nullable=True)
    created_at   = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    used_at      = Column(DateTime(timezone=True), nullable=True)
