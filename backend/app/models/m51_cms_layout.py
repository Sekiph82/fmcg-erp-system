"""M51.S01.T002 global CMS components, themes, templates and site layout.

One versioned, approval-gated library: a component is a header, footer, navigation, reusable section/component, brand
theme (tokens) or page template. Pages reference components by key (block type "component"), so publishing a new
component version updates every page; rollback re-publishes an older version. Content is validated typed data only.
"""
import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


def _id():
    return Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _ts():
    return Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CmsComponent(Base):
    __tablename__ = "cms_components"
    __table_args__ = (UniqueConstraint("site_id", "key", name="uq_cms_component_key"),)

    id              = _id()
    site_id         = Column(UUID(as_uuid=True), ForeignKey("cms_sites.id", ondelete="CASCADE"), nullable=False, index=True)
    key             = Column(String(40), nullable=False)
    kind            = Column(String(14), nullable=False)    # HEADER | FOOTER | NAV | SECTION | COMPONENT | THEME | PAGE_TEMPLATE
    name            = Column(String(150), nullable=False)
    draft           = Column(JSON, nullable=False, default=dict)
    status          = Column(String(10), nullable=False, default="DRAFT")   # DRAFT | IN_REVIEW | APPROVED | PUBLISHED
    live_version_id = Column(UUID(as_uuid=True), nullable=True)
    submitted_by    = Column(String(100), nullable=True)
    approved_by     = Column(String(100), nullable=True)
    created_by      = Column(String(100), nullable=True)
    updated_by      = Column(String(100), nullable=True)
    created_at      = _ts()
    updated_at      = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class CmsComponentVersion(Base):
    """Approval evidence: who approved and published each frozen version (archive on downgrade)."""
    __tablename__ = "cms_component_versions"
    __table_args__ = (UniqueConstraint("component_id", "version", name="uq_cms_component_version"),)

    id           = _id()
    component_id = Column(UUID(as_uuid=True), ForeignKey("cms_components.id", ondelete="CASCADE"), nullable=False, index=True)
    version      = Column(Integer, nullable=False)
    name         = Column(String(150), nullable=False)
    content      = Column(JSON, nullable=False)
    note         = Column(String(200), nullable=True)
    approved_by  = Column(String(100), nullable=True)
    published_by = Column(String(100), nullable=True)
    published_at = _ts()


class CmsSiteLayout(Base):
    """Which published components frame every page of a site (a page may override or hide each slot)."""
    __tablename__ = "cms_site_layouts"

    id         = _id()
    site_id    = Column(UUID(as_uuid=True), ForeignKey("cms_sites.id", ondelete="CASCADE"), nullable=False, unique=True)
    header_key = Column(String(40), nullable=True)
    footer_key = Column(String(40), nullable=True)
    nav_key    = Column(String(40), nullable=True)
    theme_key  = Column(String(40), nullable=True)
    updated_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
