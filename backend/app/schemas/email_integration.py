from __future__ import annotations

from datetime import datetime
from typing import Optional, List
import uuid

from pydantic import BaseModel, ConfigDict

from app.models.email_integration import EmailProvider


class EmailAccountCreate(BaseModel):
    provider:      EmailProvider
    email_address: str
    display_name:  Optional[str] = None
    sync_enabled:  bool = True


class EmailAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:            uuid.UUID
    provider:      EmailProvider
    email_address: str
    display_name:  Optional[str]
    is_active:     bool
    sync_enabled:  bool
    last_sync_at:  Optional[datetime]
    sync_error:    Optional[str]
    created_at:    datetime


class EmailMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                  uuid.UUID
    thread_id:           uuid.UUID
    from_email:          str
    from_name:           Optional[str]
    to_emails:           List[str]
    cc_emails:           Optional[List[str]]
    subject:             str
    body_text:           Optional[str]
    received_at:         datetime
    is_inbound:          bool
    is_read:             bool
    has_attachments:     bool
    sent_by_id:          Optional[uuid.UUID]


class EmailThreadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                uuid.UUID
    account_id:        uuid.UUID
    subject:           str
    snippet:           Optional[str]
    participants:      Optional[List[str]]
    is_read:           bool
    message_count:     int
    last_message_at:   Optional[datetime]
    linked_module:     Optional[str]
    linked_object_id:  Optional[uuid.UUID]
    linked_object_ref: Optional[str]
    created_at:        datetime
    messages:          List[EmailMessageRead] = []


class SendEmailRequest(BaseModel):
    account_id:        uuid.UUID
    to_emails:         List[str]
    cc_emails:         List[str] = []
    subject:           str
    body_text:         str
    linked_module:     Optional[str]       = None
    linked_object_id:  Optional[uuid.UUID] = None
    linked_object_ref: Optional[str]       = None
    thread_id:         Optional[uuid.UUID] = None   # reply to existing thread


class EmailTemplateCreate(BaseModel):
    name:             str
    module:           Optional[str] = None
    subject_template: str
    body_template:    str


class EmailTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:               uuid.UUID
    name:             str
    module:           Optional[str]
    subject_template: str
    body_template:    str
    is_active:        bool
    created_at:       datetime
