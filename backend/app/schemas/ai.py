from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class AIPromptCreate(BaseModel):
    key: str
    version: int = 1
    title: str
    module: Optional[str] = None
    prompt_type: str = "system"
    content: str
    variables: Optional[List[str]] = None
    notes: Optional[str] = None


class AIPromptUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    variables: Optional[List[str]] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class AIPromptRead(BaseModel):
    id: uuid.UUID
    key: str
    version: int
    title: str
    module: Optional[str]
    prompt_type: str
    content: str
    variables: Optional[List[str]]
    is_active: bool
    notes: Optional[str]
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
