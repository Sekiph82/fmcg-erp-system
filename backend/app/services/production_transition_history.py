from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.production_transition import ProductionTransitionEvent


PRODUCTION_ORDER = "PRODUCTION_ORDER"
WORK_ORDER = "WORK_ORDER"
EXEC_PRODUCTION_ORDER = "EXEC_PRODUCTION_ORDER"
EXEC_WORK_ORDER = "EXEC_WORK_ORDER"


def status_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(getattr(value, "value", value))


def record_transition(
    db: AsyncSession,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    parent_entity_type: str,
    parent_entity_id: uuid.UUID,
    action: str,
    actor_id: Optional[uuid.UUID] = None,
    actor_session_id: Optional[uuid.UUID] = None,
    actor_label: Optional[str] = None,
    from_status: Any = None,
    to_status: Any = None,
) -> None:
    if (actor_id is None) == (actor_session_id is None):
        raise ValueError("Exactly one authenticated user or operator session is required for transition history")
    label = actor_label or (str(actor_id) if actor_id is not None else None)
    if not label or not label.strip():
        raise ValueError("A non-empty actor label is required for production transition history")
    db.add(
        ProductionTransitionEvent(
            entity_type=entity_type,
            entity_id=entity_id,
            parent_entity_type=parent_entity_type,
            parent_entity_id=parent_entity_id,
            action=action,
            actor_id=actor_id,
            actor_session_id=actor_session_id,
            actor_label=label.strip(),
            from_status=status_value(from_status),
            to_status=status_value(to_status),
        )
    )


async def record_shop_floor_transition(
    db: AsyncSession,
    *,
    session_id: Optional[uuid.UUID],
    entity_id: uuid.UUID,
    parent_entity_id: uuid.UUID,
    action: str,
    from_status: Any,
    to_status: Any,
) -> None:
    if session_id is None:
        raise ValueError("An active shop-floor operator session is required for transition history")
    from app.models.shop_floor import SFSession

    result = await db.execute(
        select(SFSession)
        .where(SFSession.id == session_id)
        .with_for_update()
    )
    session = result.scalar_one_or_none()
    if session is None or session.status != "ACTIVE":
        raise ValueError("A valid active shop-floor operator session is required")
    if not session.operator_name or not session.operator_name.strip():
        raise ValueError("The operator session must identify its operator")
    record_transition(
        db,
        entity_type=EXEC_WORK_ORDER,
        entity_id=entity_id,
        parent_entity_type=EXEC_PRODUCTION_ORDER,
        parent_entity_id=parent_entity_id,
        action=action,
        actor_session_id=session.id,
        actor_label=session.operator_name,
        from_status=from_status,
        to_status=to_status,
    )


async def list_parent_history(
    db: AsyncSession, parent_entity_type: str, parent_entity_id: uuid.UUID
) -> list[ProductionTransitionEvent]:
    result = await db.execute(
        select(ProductionTransitionEvent)
        .where(
            ProductionTransitionEvent.parent_entity_type == parent_entity_type,
            ProductionTransitionEvent.parent_entity_id == parent_entity_id,
        )
        .order_by(
            ProductionTransitionEvent.event_seq,
        )
    )
    return list(result.scalars().all())


async def list_entity_history(
    db: AsyncSession, entity_type: str, entity_id: uuid.UUID
) -> list[ProductionTransitionEvent]:
    result = await db.execute(
        select(ProductionTransitionEvent)
        .where(
            ProductionTransitionEvent.entity_type == entity_type,
            ProductionTransitionEvent.entity_id == entity_id,
        )
        .order_by(
            ProductionTransitionEvent.event_seq,
        )
    )
    return list(result.scalars().all())
