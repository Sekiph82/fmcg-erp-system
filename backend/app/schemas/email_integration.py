from __future__ import annotations

from datetime import datetime
from typing import Optional, List
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.email_integration import EmailProvider


def _one_line(v: Optional[str]) -> Optional[str]:
    if v is not None and any(ord(c) < 32 for c in v):
        raise ValueError("must be a single line without control characters")
    return v


class MailboxSettings(BaseModel):
    """IMAP/SMTP login. Hosts/ports default by provider (Gmail, Microsoft 365); the password is write-only."""
    imap_host:     Optional[str] = Field(None, max_length=255)
    imap_port:     Optional[int] = Field(None, ge=1, le=65535)
    smtp_host:     Optional[str] = Field(None, max_length=255)
    smtp_port:     Optional[int] = Field(None, ge=1, le=65535)
    username:      Optional[str] = Field(None, max_length=255)
    password:      Optional[str] = Field(None, min_length=1, max_length=500)


class EmailAccountCreate(MailboxSettings):
    provider:      EmailProvider
    email_address: EmailStr
    display_name:  Optional[str] = Field(None, max_length=255)
    sync_enabled:  bool = True

    _name_one_line = field_validator("display_name")(classmethod(lambda cls, v: _one_line(v)))


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
    imap_host:     Optional[str] = None
    imap_port:     Optional[int] = None
    smtp_host:     Optional[str] = None
    smtp_port:     Optional[int] = None
    username:      Optional[str] = None
    connected:     bool = False


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
    attachments:         Optional[List[dict]] = None
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
    to_emails:         List[EmailStr] = Field(min_length=1, max_length=50)
    cc_emails:         List[EmailStr] = Field(default_factory=list, max_length=50)
    subject:           str = Field(min_length=1, max_length=900)
    body_text:         str = Field(max_length=200_000)

    _subject_one_line = field_validator("subject")(classmethod(lambda cls, v: _one_line(v)))
    linked_module:     Optional[str]       = None
    linked_object_id:  Optional[uuid.UUID] = None
    linked_object_ref: Optional[str]       = None
    thread_id:         Optional[uuid.UUID] = None   # reply to existing thread


class EmailTemplateCreate(BaseModel):
    name:             str = Field(min_length=1, max_length=200)
    module:           Optional[str] = Field(None, max_length=50)
    subject_template: str = Field(min_length=1, max_length=1000)
    body_template:    str = Field(min_length=1, max_length=50000)


class EmailTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:               uuid.UUID
    name:             str
    module:           Optional[str]
    subject_template: str
    body_template:    str
    is_active:        bool
    created_at:       datetime
