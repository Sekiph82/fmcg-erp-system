from pydantic import BaseModel
from typing import Optional, Any, Dict, List
from datetime import datetime
import uuid


class OperationalLogRead(BaseModel):
    id: uuid.UUID
    module_name: str
    entity_type: str
    entity_id: Optional[str] = None
    action_type: str
    status: str
    error_message: Optional[str] = None
    request_payload: Optional[Dict[str, Any]] = None
    response_payload: Optional[Dict[str, Any]] = None
    created_by_id: Optional[uuid.UUID] = None
    created_by_email: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OperationalLogCreate(BaseModel):
    module_name: str
    entity_type: str
    entity_id: Optional[str] = None
    action_type: str
    status: str = "SUCCESS"
    error_message: Optional[str] = None
    request_payload: Optional[Dict[str, Any]] = None
    response_payload: Optional[Dict[str, Any]] = None
    created_by_id: Optional[uuid.UUID] = None
    created_by_email: Optional[str] = None


class MpesaStatusHistoryRead(BaseModel):
    id: uuid.UUID
    transaction_id: uuid.UUID
    old_status: Optional[str] = None
    new_status: str
    reason: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LogsPageResponse(BaseModel):
    items: List[OperationalLogRead]
    total: int
    skip: int
    limit: int
