from __future__ import annotations

from datetime import datetime
from typing import Optional, List
import uuid

from pydantic import BaseModel, ConfigDict

from app.models.messaging import ChannelType, MemberRole


class ChannelCreate(BaseModel):
    name:           str
    description:    Optional[str]  = None
    module_context: Optional[str]  = None
    member_ids:     List[uuid.UUID] = []


class ChannelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:             uuid.UUID
    name:           str
    slug:           str
    channel_type:   ChannelType
    description:    Optional[str]
    module_context: Optional[str]
    is_archived:    bool
    created_at:     datetime
    member_count:   int = 0
    unread_count:   int = 0


class MessageCreate(BaseModel):
    body:        str
    parent_id:   Optional[uuid.UUID] = None
    link_module: Optional[str]       = None
    link_type:   Optional[str]       = None
    link_id:     Optional[uuid.UUID] = None
    link_ref:    Optional[str]       = None
    mentions:    List[str]           = []   # list of user UUID strings


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:          uuid.UUID
    channel_id:  uuid.UUID
    sender_id:   Optional[uuid.UUID]
    sender_name: Optional[str]       = None
    sender_initials: Optional[str]   = None
    body:        str
    parent_id:   Optional[uuid.UUID]
    is_edited:   bool
    is_deleted:  bool
    created_at:  datetime
    link_module: Optional[str]
    link_type:   Optional[str]
    link_id:     Optional[uuid.UUID]
    link_ref:    Optional[str]
    mentions:    Optional[List[str]]
    reply_count: int = 0


class MessagePage(BaseModel):
    messages:    List[MessageRead]
    has_more:    bool
    oldest_at:   Optional[datetime]


class DMCreate(BaseModel):
    target_user_id: uuid.UUID
