"""M47.S01.T010 platform and service depth: field-level permissions, contact (smart) properties, lead-form shortening,
Slack routing / interactive approvals, ad audience and conversion uploads.

Side tables instead of new columns on existing tables (crm_lead_forms), so existing queries keep working before and
after the migration."""
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class FieldPermissionRule(Base):
    """Role → field → HIDDEN | READ_ONLY for an entity ("contact" or "co:<custom object key>")."""
    __tablename__ = "field_permission_rules"
    __table_args__ = (UniqueConstraint("entity", "role_name", "field_key", name="uq_field_permission_rule"),)

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity     = Column(String(60), nullable=False, index=True)
    role_name  = Column(String(100), nullable=False)
    field_key  = Column(String(60), nullable=False)
    access     = Column(String(10), nullable=False)          # HIDDEN | READ_ONLY
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CRMContactProperty(Base):
    """Extra contact properties; source SMART = rule-filled from activity (recomputed daily), MANUAL = typed."""
    __tablename__ = "crm_contact_properties"

    contact_id = Column(UUID(as_uuid=True), ForeignKey("crm_contacts.id", ondelete="CASCADE"), primary_key=True)
    key        = Column(String(60), primary_key=True)
    value      = Column(Text, nullable=True)
    source     = Column(String(10), nullable=False, default="MANUAL")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LeadFormSetting(Base):
    """Per lead form: fields to leave out for a recognised visitor whose value is already known."""
    __tablename__ = "crm_lead_form_settings"

    form_id       = Column(UUID(as_uuid=True), ForeignKey("crm_lead_forms.id", ondelete="CASCADE"), primary_key=True)
    skip_if_known = Column(JSON, nullable=False, default=list)


class SlackRoute(Base):
    """Event type → Slack incoming-webhook (one channel per webhook). Without a route the global webhook is used."""
    __tablename__ = "crm_slack_routes"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type    = Column(String(10), nullable=False, unique=True)     # DEAL | TICKET | APPROVAL | APPROVE
    channel_label = Column(String(80), nullable=False)
    webhook_url_stored = Column("webhook_url", Text, nullable=False)   # encrypted at rest (the URL is a secret)
    active        = Column(Boolean, nullable=False, default=True)
    created_by    = Column(String(100), nullable=True)
    created_at    = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    @property
    def webhook_url(self) -> str:
        from app.services.webhook_service import _read_webhook_secret
        return _read_webhook_secret(self.webhook_url_stored) or ""


def seal_webhook(url: str) -> str:
    from app.services.webhook_service import _store_webhook_secret
    return _store_webhook_secret(url)


class SlackUserLink(Base):
    """Slack user ↔ ERP user, created by the signed-in ERP user for their own account (their verified e-mail)."""
    __tablename__ = "crm_slack_user_links"

    slack_user_id = Column(String(40), primary_key=True)
    user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    email         = Column(String(254), nullable=False)
    verified_at   = Column(DateTime(timezone=True), nullable=False)


class AdsAudienceUpload(Base):
    __tablename__ = "ads_audience_uploads"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audience_id          = Column(UUID(as_uuid=True), ForeignKey("mkt_audiences.id", ondelete="CASCADE"), nullable=False, index=True)
    provider             = Column(String(10), nullable=False)
    account_id           = Column(UUID(as_uuid=True), ForeignKey("ads_accounts.id", ondelete="SET NULL"), nullable=True)
    external_audience_id = Column(String(200), nullable=True)
    sent_count           = Column(Integer, nullable=False, default=0)
    status               = Column(String(15), nullable=False)          # UPLOADED | FAILED
    error                = Column(String(500), nullable=True)
    created_by_id        = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at           = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AdsConversionUpload(Base):
    """One row per (provider, won deal / paid invoice): a conversion is uploaded once."""
    __tablename__ = "ads_conversion_uploads"
    __table_args__ = (UniqueConstraint("provider", "source_type", "source_id", name="uq_ads_conversion_upload"),)

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider    = Column(String(10), nullable=False)
    source_type = Column(String(10), nullable=False)       # DEAL | INVOICE
    source_id   = Column(UUID(as_uuid=True), nullable=False)
    status      = Column(String(10), nullable=False)       # UPLOADED | FAILED
    error       = Column(String(500), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
