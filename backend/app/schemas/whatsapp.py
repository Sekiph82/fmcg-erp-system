from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Any
import uuid

from pydantic import BaseModel, ConfigDict

from app.models.whatsapp import WAMessageDirection, WAMessageType, WAMessageStatus


class WAConfigCreate(BaseModel):
    display_name:         str
    business_phone_id:    Optional[str] = None
    business_phone_no:    Optional[str] = None
    api_token:            Optional[str] = None
    webhook_verify_token: Optional[str] = None
    provider:             str = "META"
    is_demo_mode:         bool = True


class WAConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                   uuid.UUID
    display_name:         str
    business_phone_no:    Optional[str]
    provider:             str
    is_active:            bool
    is_demo_mode:         bool
    created_at:           datetime


class WASendText(BaseModel):
    config_id:         uuid.UUID
    phone:             str            # E.164 e.g. +254712345678
    body:              str
    contact_name:      Optional[str]  = None
    linked_module:     Optional[str]  = None
    linked_object_id:  Optional[uuid.UUID] = None
    linked_object_ref: Optional[str]  = None


class WASendTemplate(BaseModel):
    config_id:         uuid.UUID
    phone:             str
    template_name:     str
    variables:         List[str] = []   # ordered values for {{1}}, {{2}}
    contact_name:      Optional[str]  = None
    linked_module:     Optional[str]  = None
    linked_object_id:  Optional[uuid.UUID] = None
    linked_object_ref: Optional[str]  = None


class WAMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                uuid.UUID
    config_id:         uuid.UUID
    direction:         WAMessageDirection
    message_type:      WAMessageType
    status:            WAMessageStatus
    phone:             str
    contact_name:      Optional[str]
    body:              Optional[str]
    template_name:     Optional[str]
    template_vars:     Optional[List[str]]
    external_msg_id:   Optional[str]
    error_message:     Optional[str]
    delivered_at:      Optional[datetime]
    read_at:           Optional[datetime]
    linked_module:     Optional[str]
    linked_object_id:  Optional[uuid.UUID]
    linked_object_ref: Optional[str]
    sent_by_id:        Optional[uuid.UUID]
    created_at:        datetime


class WATemplateCreate(BaseModel):
    template_name:  str
    display_name:   str
    category:       str = "UTILITY"
    language:       str = "en"
    header_text:    Optional[str] = None
    body_template:  str
    footer_text:    Optional[str] = None
    buttons:        Optional[List[dict]] = None
    variable_count: int = 0
    module_context: Optional[str] = None


class WATemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:             uuid.UUID
    template_name:  str
    display_name:   str
    category:       str
    language:       str
    header_text:    Optional[str]
    body_template:  str
    footer_text:    Optional[str]
    buttons:        Optional[List[Any]]
    variable_count: int
    module_context: Optional[str]
    is_active:      bool
    created_at:     datetime


class WASimulateInbound(BaseModel):
    config_id:         uuid.UUID
    phone:             str
    body:              str
    contact_name:      Optional[str]  = None
    linked_module:     Optional[str]  = None
    linked_object_id:  Optional[uuid.UUID] = None
    linked_object_ref: Optional[str]  = None
