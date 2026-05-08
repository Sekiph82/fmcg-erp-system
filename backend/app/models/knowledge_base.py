import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class KBArticleStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class KBCategory(Base, TimestampMixin):
    __tablename__ = "kb_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("kb_categories.id", ondelete="SET NULL"), nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    icon = Column(String(50), nullable=True)

    parent = relationship("KBCategory", remote_side=[id], foreign_keys=[parent_id])
    articles = relationship("KBArticle", back_populates="category")


class KBArticle(Base, TimestampMixin):
    __tablename__ = "kb_articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    title = Column(String(300), nullable=False)
    summary = Column(Text, nullable=True)
    content_md = Column(Text, nullable=False, default="")
    category_id = Column(UUID(as_uuid=True), ForeignKey("kb_categories.id", ondelete="SET NULL"), nullable=True)
    tags = Column(JSON, default=list)
    status = Column(String(20), nullable=False, default="DRAFT")
    version = Column(Integer, nullable=False, default=1)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    last_editor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    published_at = Column(DateTime, nullable=True)
    view_count = Column(Integer, default=0, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)
    access_level = Column(String(30), nullable=False, default="all")

    category = relationship("KBCategory", back_populates="articles")
    author = relationship("User", foreign_keys=[author_id])
    last_editor = relationship("User", foreign_keys=[last_editor_id])
    revisions = relationship("KBArticleRevision", back_populates="article",
                             cascade="all, delete-orphan",
                             order_by="KBArticleRevision.version_no.desc()")


class KBArticleRevision(Base, TimestampMixin):
    __tablename__ = "kb_article_revisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id = Column(UUID(as_uuid=True), ForeignKey("kb_articles.id", ondelete="CASCADE"), nullable=False)
    version_no = Column(Integer, nullable=False)
    title = Column(String(300), nullable=False)
    content_md = Column(Text, nullable=False)
    change_summary = Column(String(500), nullable=True)
    changed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    article = relationship("KBArticle", back_populates="revisions")
    changed_by = relationship("User", foreign_keys=[changed_by_id])
