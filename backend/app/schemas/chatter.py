from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from app.models.chatter import (
    ReferenceType, ActivityType, Visibility,
    CTAIAgentType, CTAIRecStatus,
)


class CommentOut(BaseModel):
    comment_id: str
    activity_id: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    message: str
    created_at: datetime
    edited_at: Optional[datetime] = None
    deleted_flag: bool = False
    model_config = {"from_attributes": True}


class AttachmentOut(BaseModel):
    attachment_id: str
    activity_id: str
    file_name: str
    file_path: Optional[str] = None
    file_size: Optional[str] = None
    content_type: Optional[str] = None
    uploaded_by: Optional[str] = None
    uploaded_at: datetime
    model_config = {"from_attributes": True}


class MentionOut(BaseModel):
    mention_id: str
    mentioned_user: str
    notified_flag: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class ActivityOut(BaseModel):
    activity_id: str
    reference_type: ReferenceType
    reference_id: str
    activity_type: ActivityType
    title: str
    message: Optional[str] = None
    created_by: Optional[str] = None
    visibility: Visibility
    is_pinned: bool
    created_at: datetime
    updated_at: datetime
    comments: List[CommentOut] = []
    attachments: List[AttachmentOut] = []
    mentions: List[MentionOut] = []
    model_config = {"from_attributes": True}


class ActivityPage(BaseModel):
    items: List[ActivityOut]
    total: int
    page: int
    per_page: int
    pages: int


class ActivityCreate(BaseModel):
    reference_type: ReferenceType
    reference_id: str
    activity_type: ActivityType = ActivityType.COMMENT
    title: str
    message: Optional[str] = None
    created_by: Optional[str] = "system"
    visibility: Visibility = Visibility.GLOBAL


class CommentCreate(BaseModel):
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    message: str


class CommentEdit(BaseModel):
    message: str


class AttachmentCreate(BaseModel):
    file_name: str
    file_path: Optional[str] = None
    file_size: Optional[str] = None
    content_type: Optional[str] = None
    uploaded_by: Optional[str] = None


class CTAIRecOut(BaseModel):
    rec_id: str
    agent_type: CTAIAgentType
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    title: str
    body: str
    score: Optional[float] = None
    status: CTAIRecStatus
    rec_metadata: dict = {}
    created_at: datetime
    model_config = {"from_attributes": True}


class CTAIRecAck(BaseModel):
    status: CTAIRecStatus


ActivityOut.model_rebuild()
ActivityPage.model_rebuild()
