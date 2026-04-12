from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid

from app.db.session import get_db
from app.core.deps import require_permission
from app.crud import audit as crud
from app.schemas.audit import AuditLogRead

router = APIRouter()


@router.get(
    "/",
    response_model=List[AuditLogRead],
    dependencies=[Depends(require_permission("audit", "view"))],
)
async def list_audit_logs(
    event_type: Optional[str] = Query(None),
    actor_id: Optional[uuid.UUID] = Query(None),
    target_type: Optional[str] = Query(None),
    target_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await crud.list_audit_logs(
        db,
        event_type=event_type,
        actor_id=actor_id,
        target_type=target_type,
        target_id=target_id,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/user/{user_id}",
    response_model=List[AuditLogRead],
    dependencies=[Depends(require_permission("audit", "view"))],
)
async def user_login_history(
    user_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Returns all audit events where the actor is the specified user."""
    return await crud.list_audit_logs(
        db,
        actor_id=user_id,
        skip=skip,
        limit=limit,
    )
