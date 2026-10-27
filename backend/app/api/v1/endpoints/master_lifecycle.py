from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.master_lifecycle import (
    MasterLifecycleError,
    deactivate_master as deactivate_master_record,
    merge_master as merge_master_record,
)
from app.models.master_lifecycle import MasterLifecycleEvent
from app.schemas.master import MasterMergeResult


async def deactivate_master(
    db: AsyncSession,
    model: type[Any],
    entity_type: str,
    record_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> Any:
    record = await deactivate_master_record(db, model, entity_type, record_id, actor_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"{entity_type.title()} not found")
    await db.commit()
    await db.refresh(record)
    return record


async def merge_master(
    db: AsyncSession,
    model: type[Any],
    entity_type: str,
    source_id: uuid.UUID,
    survivor_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> MasterMergeResult:
    try:
        source, survivor = await merge_master_record(
            db, model, entity_type, source_id, survivor_id, actor_id
        )
    except MasterLifecycleError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    if source is None or survivor is None:
        raise HTTPException(status_code=404, detail=f"{entity_type.title()} or survivor not found")
    event = await db.scalar(
        select(MasterLifecycleEvent)
        .where(
            MasterLifecycleEvent.entity_type == entity_type,
            MasterLifecycleEvent.record_id == source.id,
            MasterLifecycleEvent.event_type == "MERGED",
        )
        .order_by(MasterLifecycleEvent.created_at.desc())
        .limit(1)
    )
    if event is None or event.merged_into_id != survivor.id:
        raise HTTPException(500, "Merge lifecycle event was not persisted in the transaction.")
    await db.commit()
    return MasterMergeResult(
        entity_type=entity_type,
        source_id=source.id,
        survivor_id=survivor.id,
        source_is_active=source.is_active,
        lifecycle_event_id=event.id,
    )
