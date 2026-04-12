from pydantic import BaseModel
from typing import Optional, Any, Dict
from datetime import datetime
import uuid


class AuditLogRead(BaseModel):
    id: uuid.UUID
    actor_id: Optional[uuid.UUID] = None
    actor_email: Optional[str] = None
    event_type: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    target_name: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
