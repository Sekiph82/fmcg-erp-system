"""
IoT / Machine Integration Service — placeholder.

Ingests machine events (counters, status, alarms, speed, temperature)
from production line equipment and stores them for correlation with
production orders and maintenance records.

Integration path:
  Machine/PLC/SCADA → POST /api/v1/integrations/iot/events
  (supports JSON body or future MQTT bridge)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integrations import MachineEvent

logger = logging.getLogger(__name__)


async def ingest_event(
    db: AsyncSession,
    machine_id: str,
    event_type: str,
    value_str: Optional[str] = None,
    value_numeric: Optional[float] = None,
    unit: Optional[str] = None,
    machine_name: Optional[str] = None,
    production_order_id: Optional[str] = None,
    received_at: Optional[datetime] = None,
    raw_payload: Optional[str] = None,
) -> MachineEvent:
    """Record one machine event. Call from the ingest endpoint."""
    event = MachineEvent(
        machine_id=machine_id,
        machine_name=machine_name,
        event_type=event_type,
        value_str=value_str,
        value_numeric=value_numeric,
        unit=unit,
        production_order_id=uuid.UUID(production_order_id) if production_order_id else None,
        received_at=received_at or datetime.now(timezone.utc),
        raw_payload=raw_payload,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


async def list_events(
    db: AsyncSession,
    machine_id: Optional[str] = None,
    event_type: Optional[str] = None,
    hours: int = 24,
    limit: int = 200,
) -> List[MachineEvent]:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    q = (
        select(MachineEvent)
        .where(MachineEvent.received_at >= since)
        .order_by(MachineEvent.received_at.desc())
    )
    if machine_id:
        q = q.where(MachineEvent.machine_id == machine_id)
    if event_type:
        q = q.where(MachineEvent.event_type == event_type)
    result = await db.execute(q.limit(limit))
    return list(result.scalars().all())


async def get_machine_status_summary(db: AsyncSession) -> List[dict]:
    """Return the latest event per machine for a status dashboard."""
    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)

    # Latest event per machine
    subq = (
        select(
            MachineEvent.machine_id,
            func.max(MachineEvent.received_at).label("last_seen"),
        )
        .group_by(MachineEvent.machine_id)
        .subquery()
    )

    latest_q = (
        select(MachineEvent)
        .join(
            subq,
            and_(
                MachineEvent.machine_id == subq.c.machine_id,
                MachineEvent.received_at == subq.c.last_seen,
            ),
        )
    )
    result = await db.execute(latest_q)
    latest_events = list(result.scalars().all())

    # Count per machine in last 24h
    count_q = (
        select(MachineEvent.machine_id, func.count(MachineEvent.id))
        .where(MachineEvent.received_at >= since_24h)
        .group_by(MachineEvent.machine_id)
    )
    count_result = await db.execute(count_q)
    counts = {r[0]: r[1] for r in count_result}

    return [
        {
            "machine_id": e.machine_id,
            "machine_name": e.machine_name,
            "last_event_type": e.event_type,
            "last_value": e.value_str or (str(e.value_numeric) if e.value_numeric is not None else None),
            "last_seen": e.received_at,
            "event_count_24h": counts.get(e.machine_id, 0),
        }
        for e in latest_events
    ]
