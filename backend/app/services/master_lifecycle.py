from __future__ import annotations

import uuid
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.master_lifecycle import MasterLifecycleEvent


RecordT = TypeVar("RecordT")


class MasterLifecycleError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


async def deactivate_master(
    db: AsyncSession,
    model: type[RecordT],
    entity_type: str,
    record_id: uuid.UUID,
    actor_id: uuid.UUID | None,
) -> RecordT | None:
    record = await db.scalar(select(model).where(model.id == record_id).with_for_update())
    if record is None:
        return None
    if not record.is_active:
        return record

    record.is_active = False
    db.add(MasterLifecycleEvent(
        entity_type=entity_type,
        record_id=record.id,
        event_type="DEACTIVATED",
        actor_id=actor_id,
    ))
    await db.flush()
    return record


async def merge_master(
    db: AsyncSession,
    model: type[RecordT],
    entity_type: str,
    source_id: uuid.UUID,
    survivor_id: uuid.UUID,
    actor_id: uuid.UUID | None,
) -> tuple[RecordT | None, RecordT | None]:
    if source_id == survivor_id:
        raise MasterLifecycleError("invalid_merge", "A record cannot be merged into itself.")

    # Lock both records in stable order to prevent concurrent merges or a target
    # being deactivated between validation and commit.
    records = list((await db.scalars(
        select(model)
        .where(model.id.in_((source_id, survivor_id)))
        .order_by(model.id)
        .with_for_update()
    )).all())
    by_id = {record.id: record for record in records}
    source = by_id.get(source_id)
    survivor = by_id.get(survivor_id)
    if source is None or survivor is None:
        return source, survivor
    if not source.is_active:
        raise MasterLifecycleError("source_inactive", "Only an active record can be merged.")
    if not survivor.is_active:
        raise MasterLifecycleError("survivor_inactive", "The surviving record must be active.")

    source.is_active = False
    db.add(MasterLifecycleEvent(
        entity_type=entity_type,
        record_id=source.id,
        event_type="MERGED",
        merged_into_id=survivor.id,
        actor_id=actor_id,
    ))
    # Deliberately leave all pre-existing foreign keys and history untouched.
    await db.flush()
    return source, survivor
