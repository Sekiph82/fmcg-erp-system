"""M46 Content & Digital Experience Hub: sites, pages, blog, SEO, dynamic tables, CTAs, personalization experiments,
memberships and media, brand-voice content studio.

Content is stored as validated block documents (never raw HTML). Drafts live on the page row; the public sees only a
published version snapshot (cms_page_versions), so staging and rollback are a matter of which snapshot is live.
"""
import uuid

from sqlalchemy import JSON, BigInteger, Boolean, Column, DateTime, Float, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


def _id():
    return Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _ts():
    return Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CmsSite(Base):
    """One website (multisite = several rows). The custom domain is configuration only: until activation the site is
    served locally at /site/<key>."""
    __tablename__ = "cms_sites"

    id               = _id()
    key              = Column(String(40), nullable=False, unique=True)
    name             = Column(String(150), nullable=False)
    default_locale   = Column(String(5), nullable=False, default="en")
    locales          = Column(JSON, nullable=False, default=lambda: ["en"])
    domain           = Column(String(200), nullable=True)
    domain_status    = Column(String(15), nullable=False, default="LOCAL_ONLY")   # LOCAL_ONLY | DNS_PENDING (activation: M47)
    theme            = Column(JSON, nullable=False, default=dict)
    nav              = Column(JSON, nullable=False, default=list)                   # [{label, path, locale?}]
    require_approval = Column(Boolean, nullable=False, default=True)
    created_by       = Column(String(100), nullable=True)
    created_at       = _ts()


class CmsPage(Base):
    """A page, blog post or dynamic-page template in one locale. translation_group ties locales of the same page."""
    __tablename__ = "cms_pages"
    __table_args__ = (UniqueConstraint("site_id", "locale", "path", name="uq_cms_page_path"),)

    id                = _id()
    site_id           = Column(UUID(as_uuid=True), ForeignKey("cms_sites.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id         = Column(UUID(as_uuid=True), ForeignKey("cms_pages.id", ondelete="SET NULL"), nullable=True)
    kind              = Column(String(10), nullable=False, default="PAGE")     # PAGE | POST | DYNAMIC
    locale            = Column(String(5), nullable=False, default="en")
    translation_group = Column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4, index=True)
    translation_state = Column(String(12), nullable=False, default="SOURCE")   # SOURCE | NEEDS_REVIEW | REVIEWED | STALE
    slug              = Column(String(120), nullable=False)
    path              = Column(String(400), nullable=False)
    title             = Column(String(200), nullable=False)
    draft             = Column(JSON, nullable=False, default=dict)             # {blocks, seo, faq}
    status            = Column(String(10), nullable=False, default="DRAFT")    # DRAFT | IN_REVIEW | APPROVED | PUBLISHED | ARCHIVED
    live_version_id   = Column(UUID(as_uuid=True), nullable=True)
    access            = Column(String(8), nullable=False, default="PUBLIC")    # PUBLIC | MEMBERS
    access_list_id    = Column(UUID(as_uuid=True), ForeignKey("cms_access_lists.id", ondelete="SET NULL"), nullable=True)
    table_id          = Column(UUID(as_uuid=True), ForeignKey("cms_tables.id", ondelete="SET NULL"), nullable=True)   # DYNAMIC
    author            = Column(String(120), nullable=True)
    category          = Column(String(80), nullable=True)
    tags              = Column(JSON, nullable=False, default=list)
    publish_at        = Column(DateTime(timezone=True), nullable=True)         # scheduled publish of an APPROVED page
    submitted_by      = Column(String(100), nullable=True)
    approved_by       = Column(String(100), nullable=True)
    updated_by        = Column(String(100), nullable=True)
    created_at        = _ts()
    updated_at        = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class CmsPageVersion(Base):
    __tablename__ = "cms_page_versions"
    __table_args__ = (UniqueConstraint("page_id", "version", name="uq_cms_page_version"),)

    id           = _id()
    page_id      = Column(UUID(as_uuid=True), ForeignKey("cms_pages.id", ondelete="CASCADE"), nullable=False, index=True)
    version      = Column(Integer, nullable=False)
    title        = Column(String(200), nullable=False)
    content      = Column(JSON, nullable=False)
    note         = Column(String(200), nullable=True)
    published_by = Column(String(100), nullable=True)
    published_at = _ts()


class CmsRedirect(Base):
    __tablename__ = "cms_redirects"
    __table_args__ = (UniqueConstraint("site_id", "from_path", name="uq_cms_redirect_from"),)

    id        = _id()
    site_id   = Column(UUID(as_uuid=True), ForeignKey("cms_sites.id", ondelete="CASCADE"), nullable=False)
    from_path = Column(String(400), nullable=False)
    to_path   = Column(String(400), nullable=False)
    code      = Column(Integer, nullable=False, default=301)
    auto      = Column(Boolean, nullable=False, default=False)     # created when a published slug changed
    hits      = Column(Integer, nullable=False, default=0)
    created_at = _ts()


class CmsTable(Base):
    """HubDB-like dynamic data table; published rows feed table blocks and dynamic pages."""
    __tablename__ = "cms_tables"
    __table_args__ = (UniqueConstraint("site_id", "key", name="uq_cms_table_key"),)

    id        = _id()
    site_id   = Column(UUID(as_uuid=True), ForeignKey("cms_sites.id", ondelete="CASCADE"), nullable=False)
    key       = Column(String(40), nullable=False)
    name      = Column(String(150), nullable=False)
    columns   = Column(JSON, nullable=False)                      # [{key, label, type: text|number|url|image}]
    published = Column(Boolean, nullable=False, default=False)
    created_at = _ts()


class CmsTableRow(Base):
    __tablename__ = "cms_table_rows"
    __table_args__ = (UniqueConstraint("table_id", "slug", name="uq_cms_row_slug"),)

    id       = _id()
    table_id = Column(UUID(as_uuid=True), ForeignKey("cms_tables.id", ondelete="CASCADE"), nullable=False, index=True)
    slug     = Column(String(120), nullable=False)
    values   = Column(JSON, nullable=False)
    position = Column(Integer, nullable=False, default=0)


class CmsCta(Base):
    __tablename__ = "cms_ctas"
    __table_args__ = (UniqueConstraint("site_id", "key", name="uq_cms_cta_key"),)

    id      = _id()
    site_id = Column(UUID(as_uuid=True), ForeignKey("cms_sites.id", ondelete="CASCADE"), nullable=False)
    key     = Column(String(40), nullable=False)
    label   = Column(String(80), nullable=False)
    href    = Column(String(400), nullable=False)
    style   = Column(String(10), nullable=False, default="primary")
    views   = Column(Integer, nullable=False, default=0)
    clicks  = Column(Integer, nullable=False, default=0)


class CmsKeyword(Base):
    """Keyword plan rows from a local import. Volume/difficulty are only what the import says (null = no data)."""
    __tablename__ = "cms_keywords"
    __table_args__ = (UniqueConstraint("site_id", "locale", "keyword", name="uq_cms_keyword"),)

    id          = _id()
    site_id     = Column(UUID(as_uuid=True), ForeignKey("cms_sites.id", ondelete="CASCADE"), nullable=False)
    locale      = Column(String(5), nullable=False, default="en")
    keyword     = Column(String(120), nullable=False)
    volume      = Column(Integer, nullable=True)
    difficulty  = Column(Integer, nullable=True)
    source      = Column(String(60), nullable=False, default="import")
    target_page = Column(UUID(as_uuid=True), ForeignKey("cms_pages.id", ondelete="SET NULL"), nullable=True)


class CmsExperiment(Base):
    """A/B or multi-armed-bandit test on one block of a page. Counts per variant: {variant: {"n": views, "c": conversions}}."""
    __tablename__ = "cms_experiments"
    __table_args__ = (UniqueConstraint("page_id", "key", name="uq_cms_experiment_key"),)

    id       = _id()
    page_id  = Column(UUID(as_uuid=True), ForeignKey("cms_pages.id", ondelete="CASCADE"), nullable=False)
    key      = Column(String(40), nullable=False)
    mode     = Column(String(6), nullable=False, default="AB")      # AB | BANDIT
    variants = Column(JSON, nullable=False)                          # ["a", "b", ...]
    counts   = Column(JSON, nullable=False, default=dict)
    status   = Column(String(8), nullable=False, default="RUNNING")  # RUNNING | STOPPED
    created_at = _ts()


class CmsExperimentEvent(Base):
    """Attribution: which variant a (hashed) visitor saw and whether they converted; one row per visitor+kind."""
    __tablename__ = "cms_experiment_events"
    __table_args__ = (UniqueConstraint("experiment_id", "visitor_hash", "kind", name="uq_cms_exp_event"),)

    id            = _id()
    experiment_id = Column(UUID(as_uuid=True), ForeignKey("cms_experiments.id", ondelete="CASCADE"), nullable=False, index=True)
    visitor_hash  = Column(String(64), nullable=False)
    variant       = Column(String(20), nullable=False)
    kind          = Column(String(8), nullable=False)               # VIEW | CONVERT
    created_at    = _ts()


class CmsAccessList(Base):
    """Members-only access: portal accounts listed explicitly, or matched by account type."""
    __tablename__ = "cms_access_lists"

    id            = _id()
    name          = Column(String(150), nullable=False, unique=True)
    account_ids   = Column(JSON, nullable=False, default=list)       # portal_accounts.id strings
    account_types = Column(JSON, nullable=False, default=list)       # e.g. ["DISTRIBUTOR"]
    revoked_ids   = Column(JSON, nullable=False, default=list)       # explicit revocations win over types
    created_at    = _ts()


class CmsMedia(Base):
    """Locally stored video/audio (podcast episodes too) with WebVTT captions; served to members per access list."""
    __tablename__ = "cms_media"

    id             = _id()
    kind           = Column(String(6), nullable=False)               # VIDEO | AUDIO
    title          = Column(String(200), nullable=False)
    mime           = Column(String(40), nullable=False)
    size           = Column(BigInteger, nullable=False)
    sha256         = Column(String(64), nullable=False)
    storage_path   = Column(String(400), nullable=False)
    captions       = Column(JSON, nullable=False, default=dict)      # {locale: vtt text}
    podcast        = Column(String(120), nullable=True)              # show name; episodes ordered by created_at
    access_list_id = Column(UUID(as_uuid=True), ForeignKey("cms_access_lists.id", ondelete="SET NULL"), nullable=True)
    public         = Column(Boolean, nullable=False, default=False)
    duration_s     = Column(Integer, nullable=True)
    created_by     = Column(String(100), nullable=True)
    created_at     = _ts()


class CmsMediaView(Base):
    """A play by a signed-in portal user (anonymous public plays keep a keyed visitor hash only)."""
    __tablename__ = "cms_media_views"

    id                = _id()
    media_id          = Column(UUID(as_uuid=True), ForeignKey("cms_media.id", ondelete="CASCADE"), nullable=False, index=True)
    portal_account_id = Column(UUID(as_uuid=True), ForeignKey("portal_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    portal_user_id    = Column(UUID(as_uuid=True), ForeignKey("portal_users.id", ondelete="SET NULL"), nullable=True)
    viewer_hash       = Column(String(64), nullable=False)
    seconds           = Column(Integer, nullable=False, default=0)
    created_at        = _ts()


class CsBrandProfile(Base):
    """Brand voice rules for the content studio (one active profile per brand key)."""
    __tablename__ = "cs_brand_profiles"

    id            = _id()
    key           = Column(String(40), nullable=False, unique=True)
    name          = Column(String(150), nullable=False)
    voice         = Column(Text, nullable=False, default="")
    banned_terms  = Column(JSON, nullable=False, default=list)
    terminology   = Column(JSON, nullable=False, default=dict)       # {"wrong": "right"}
    claim_terms   = Column(JSON, nullable=False, default=list)       # words that make a sentence a claim needing evidence
    evidence      = Column(JSON, nullable=False, default=list)       # [{id, text, source}] approved facts that may be cited
    asset_ids     = Column(JSON, nullable=False, default=list)       # approved brand_assets used as reference
    monthly_budget = Column(Numeric(10, 2), nullable=False, default=0)   # AI spend cap (USD); 0 = deterministic only
    created_at    = _ts()


class CsDraft(Base):
    __tablename__ = "cs_drafts"

    id          = _id()
    profile_id  = Column(UUID(as_uuid=True), ForeignKey("cs_brand_profiles.id", ondelete="CASCADE"), nullable=False)
    channel     = Column(String(12), nullable=False)                 # web | blog | email | social | sms | whatsapp
    template    = Column(String(30), nullable=False)
    brief       = Column(Text, nullable=False)
    body        = Column(Text, nullable=False)
    engine      = Column(String(20), nullable=False)                 # rules | provider name
    cost        = Column(Numeric(10, 4), nullable=False, default=0)
    findings    = Column(JSON, nullable=False, default=list)         # brand / claims review
    history     = Column(JSON, nullable=False, default=list)         # [{at, by, action, body?}]
    status      = Column(String(10), nullable=False, default="DRAFT")   # DRAFT | IN_REVIEW | APPROVED | REJECTED
    source_id   = Column(UUID(as_uuid=True), ForeignKey("cs_drafts.id", ondelete="SET NULL"), nullable=True)   # repurposed from
    created_by  = Column(String(100), nullable=False)
    approved_by = Column(String(100), nullable=True)
    created_at  = _ts()


class CsUsage(Base):
    __tablename__ = "cs_usage"
    __table_args__ = (UniqueConstraint("profile_id", "month", name="uq_cs_usage_month"),)

    id         = _id()
    profile_id = Column(UUID(as_uuid=True), ForeignKey("cs_brand_profiles.id", ondelete="CASCADE"), nullable=False)
    month      = Column(String(7), nullable=False)
    spent      = Column(Float, nullable=False, default=0)
    calls      = Column(Integer, nullable=False, default=0)
