from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional
import uuid

from pydantic import BaseModel, Field


class KBCategoryBase(BaseModel):
    slug: str
    name: str
    description: Optional[str] = None
    parent_id: Optional[uuid.UUID] = None
    display_order: int = 0
    is_active: bool = True
    icon: Optional[str] = None


class KBCategoryCreate(KBCategoryBase):
    pass


class KBCategoryUpdate(BaseModel):
    slug: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[uuid.UUID] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None
    icon: Optional[str] = None


class KBCategoryRead(KBCategoryBase):
    id: uuid.UUID
    created_at: Any
    updated_at: Any

    model_config = {"from_attributes": True}


class KBArticleBase(BaseModel):
    slug: str
    title: str
    summary: Optional[str] = None
    content_md: str = ""
    category_id: Optional[uuid.UUID] = None
    tags: list[str] = Field(default_factory=list)
    status: str = "DRAFT"
    access_level: str = "all"
    is_featured: bool = False
    is_internal_only: bool = True
    company_id: Optional[uuid.UUID] = None
    department_id: Optional[str] = None
    factory_id: Optional[str] = None
    module_key: Optional[str] = None
    review_due_date: Optional[date] = None
    access_scope_type: Optional[str] = None
    access_scope_id: Optional[str] = None


class KBArticleCreate(KBArticleBase):
    pass


class KBArticleUpdate(BaseModel):
    slug: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    content_md: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    tags: Optional[list[str]] = None
    status: Optional[str] = None
    access_level: Optional[str] = None
    is_featured: Optional[bool] = None
    is_internal_only: Optional[bool] = None
    company_id: Optional[uuid.UUID] = None
    department_id: Optional[str] = None
    factory_id: Optional[str] = None
    module_key: Optional[str] = None
    review_due_date: Optional[date] = None
    access_scope_type: Optional[str] = None
    access_scope_id: Optional[str] = None
    change_summary: Optional[str] = None


class KBArticleRead(KBArticleBase):
    id: uuid.UUID
    version: int
    author_id: Optional[uuid.UUID] = None
    last_editor_id: Optional[uuid.UUID] = None
    published_by_id: Optional[uuid.UUID] = None
    archived_by_id: Optional[uuid.UUID] = None
    published_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    view_count: int
    created_at: Any
    updated_at: Any

    model_config = {"from_attributes": True}


class KBArticleRevisionRead(BaseModel):
    id: uuid.UUID
    article_id: uuid.UUID
    version_no: int
    title: str
    content_md: str
    change_summary: Optional[str] = None
    changed_by_id: Optional[uuid.UUID] = None
    created_at: Any
    updated_at: Any

    model_config = {"from_attributes": True}
