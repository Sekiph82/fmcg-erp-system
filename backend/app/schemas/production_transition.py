from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProductionTransitionEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_seq: int
    entity_type: str
    entity_id: UUID
    parent_entity_type: str
    parent_entity_id: UUID
    action: str
    from_status: Optional[str]
    to_status: Optional[str]
    actor_id: Optional[UUID]
    actor_session_id: Optional[UUID]
    actor_label: str
    created_at: datetime
