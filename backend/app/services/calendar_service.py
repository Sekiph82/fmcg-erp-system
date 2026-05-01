from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from app.models.calendar import (
    CalendarResource, CalendarEvent, EventParticipant,
    ResourceBooking, RecurrenceRule, CAIRecommendation,
    EventStatus, ResourceStatus, BookingStatus,
    CAIAgentType, CAIRecStatus, RecurrenceFrequency,
)
from app.schemas.calendar import (
    ResourceCreate, ResourceUpdate, EventCreate, EventUpdate,
    BookingCreate, SlotRequest, CAIRecAck,
)


# ── Resources ─────────────────────────────────────────────────────────────────

async def list_resources(
    db: AsyncSession,
    resource_type: Optional[str] = None,
    status: Optional[str] = None,
) -> list:
    q = select(CalendarResource)
    if resource_type:
        q = q.where(CalendarResource.resource_type == resource_type)
    if status:
        q = q.where(CalendarResource.status == status)
    result = await db.execute(q.order_by(CalendarResource.name))
    return result.scalars().all()


async def create_resource(db: AsyncSession, data: ResourceCreate) -> CalendarResource:
    r = CalendarResource(**data.model_dump())
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return r


async def update_resource(db: AsyncSession, resource_id: str, data: ResourceUpdate) -> CalendarResource:
    result = await db.execute(
        select(CalendarResource).where(CalendarResource.resource_id == resource_id)
    )
    r = result.scalar_one_or_none()
    if not r:
        raise ValueError("Resource not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(r, k, v)
    await db.commit()
    await db.refresh(r)
    return r


# ── Availability ──────────────────────────────────────────────────────────────

async def check_availability(
    db: AsyncSession,
    resource_id: str,
    start: datetime,
    end: datetime,
    exclude_booking_id: Optional[str] = None,
) -> Tuple[bool, list]:
    q = select(ResourceBooking).where(
        and_(
            ResourceBooking.resource_id == resource_id,
            ResourceBooking.status != BookingStatus.CANCELLED,
            ResourceBooking.start_datetime < end,
            ResourceBooking.end_datetime > start,
        )
    )
    if exclude_booking_id:
        q = q.where(ResourceBooking.booking_id != exclude_booking_id)
    result = await db.execute(q)
    conflicts = result.scalars().all()
    return len(conflicts) == 0, conflicts


async def get_available_slots(db: AsyncSession, data: SlotRequest) -> list:
    try:
        date = datetime.fromisoformat(data.date)
    except ValueError:
        date = datetime.utcnow()
    start_of_day = date.replace(hour=8, minute=0, second=0, microsecond=0)
    step = 30
    total_steps = int((10 * 60) / step)
    slots = []
    for i in range(total_steps):
        slot_start = start_of_day + timedelta(minutes=step * i)
        slot_end = slot_start + timedelta(minutes=data.duration_minutes)
        if slot_end.hour > 18 or (slot_end.hour == 18 and slot_end.minute > 0):
            break
        all_ok = True
        for rid in data.resource_ids:
            ok, _ = await check_availability(db, rid, slot_start, slot_end)
            if not ok:
                all_ok = False
                break
        if all_ok:
            slots.append({"start": slot_start.isoformat(), "end": slot_end.isoformat()})
        if len(slots) >= data.max_slots:
            break
    return slots


# ── Recurrence helpers ────────────────────────────────────────────────────────

def _generate_occurrences(event: CalendarEvent, rec: RecurrenceRule, start: datetime, end: datetime) -> list:
    occurrences = []
    duration = event.end_datetime - event.start_datetime
    current = event.start_datetime
    exception_dates = set(rec.exceptions or [])
    count = 0
    max_iter = 500

    while current <= end and max_iter > 0:
        max_iter -= 1
        date_str = current.date().isoformat()

        if current >= start and date_str not in exception_dates:
            occurrences.append({
                "event_id": f"{event.event_id}_{date_str}",
                "event_title": event.event_title,
                "event_type": event.event_type,
                "start_datetime": current.isoformat(),
                "end_datetime": (current + duration).isoformat(),
                "all_day_flag": event.all_day_flag,
                "created_by": event.created_by,
                "description": event.description,
                "location": event.location,
                "status": event.status,
                "source_module": event.source_module,
                "source_ref_id": event.source_ref_id,
                "recurrence_id": event.recurrence_id,
                "created_at": event.created_at.isoformat() if event.created_at else None,
                "participants": [],
                "bookings": [],
            })
            count += 1
            if rec.max_occurrences and count >= rec.max_occurrences:
                break

        if rec.frequency == RecurrenceFrequency.DAILY:
            current += timedelta(days=rec.interval)
        elif rec.frequency == RecurrenceFrequency.WEEKLY:
            current += timedelta(weeks=rec.interval)
        elif rec.frequency == RecurrenceFrequency.MONTHLY:
            month = current.month + rec.interval
            year = current.year + (month - 1) // 12
            month = (month - 1) % 12 + 1
            try:
                current = current.replace(year=year, month=month)
            except ValueError:
                break
        else:
            current += timedelta(days=rec.interval)

        if rec.end_date and current > rec.end_date:
            break

    return occurrences


# ── Events ────────────────────────────────────────────────────────────────────

async def _load_event(db: AsyncSession, event_id: str) -> Optional[CalendarEvent]:
    result = await db.execute(
        select(CalendarEvent)
        .options(
            selectinload(CalendarEvent.participants),
            selectinload(CalendarEvent.bookings),
        )
        .where(CalendarEvent.event_id == event_id)
    )
    return result.scalar_one_or_none()


async def list_events(
    db: AsyncSession,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    event_type: Optional[str] = None,
    status: Optional[str] = None,
) -> list:
    q = select(CalendarEvent).options(
        selectinload(CalendarEvent.participants),
        selectinload(CalendarEvent.bookings),
        selectinload(CalendarEvent.recurrence),
    )
    if start:
        q = q.where(CalendarEvent.end_datetime >= start)
    if end:
        q = q.where(CalendarEvent.start_datetime <= end)
    if event_type:
        q = q.where(CalendarEvent.event_type == event_type)
    if status:
        q = q.where(CalendarEvent.status == status)
    result = await db.execute(q.order_by(CalendarEvent.start_datetime))
    events = result.scalars().all()

    if start and end:
        direct = [e for e in events if not e.recurrence_id]
        recurring = [e for e in events if e.recurrence_id]
        virtual = []
        for ev in recurring:
            if ev.recurrence:
                virtual.extend(_generate_occurrences(ev, ev.recurrence, start, end))
        return [_event_to_dict(e) for e in direct] + virtual

    return [_event_to_dict(e) for e in events]


def _event_to_dict(e: CalendarEvent) -> dict:
    return {
        "event_id": e.event_id,
        "event_title": e.event_title,
        "event_type": e.event_type,
        "start_datetime": e.start_datetime.isoformat() if e.start_datetime else None,
        "end_datetime": e.end_datetime.isoformat() if e.end_datetime else None,
        "all_day_flag": e.all_day_flag,
        "created_by": e.created_by,
        "description": e.description,
        "location": e.location,
        "status": e.status,
        "source_module": e.source_module,
        "source_ref_id": e.source_ref_id,
        "recurrence_id": e.recurrence_id,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "participants": [
            {
                "participant_id": p.participant_id,
                "event_id": p.event_id,
                "participant_name": p.participant_name,
                "participant_email": p.participant_email,
                "role": p.role,
                "response_status": p.response_status,
            }
            for p in (e.participants or [])
        ],
        "bookings": [
            {
                "booking_id": b.booking_id,
                "resource_id": b.resource_id,
                "status": b.status,
                "start_datetime": b.start_datetime.isoformat() if b.start_datetime else None,
                "end_datetime": b.end_datetime.isoformat() if b.end_datetime else None,
            }
            for b in (e.bookings or [])
        ],
    }


async def get_event(db: AsyncSession, event_id: str) -> Optional[CalendarEvent]:
    return await _load_event(db, event_id)


async def create_event(db: AsyncSession, data: EventCreate) -> CalendarEvent:
    recurrence_id = None
    if data.recurrence:
        rec = RecurrenceRule(**data.recurrence.model_dump())
        db.add(rec)
        await db.flush()
        recurrence_id = rec.recurrence_id

    event = CalendarEvent(
        event_title=data.event_title,
        event_type=data.event_type,
        start_datetime=data.start_datetime,
        end_datetime=data.end_datetime,
        all_day_flag=data.all_day_flag,
        created_by=data.created_by,
        description=data.description,
        location=data.location,
        source_module=data.source_module,
        source_ref_id=data.source_ref_id,
        recurrence_id=recurrence_id,
    )
    db.add(event)
    await db.flush()

    for p in data.participants:
        db.add(EventParticipant(event_id=event.event_id, **p.model_dump()))

    for rid in data.resource_ids:
        ok, _ = await check_availability(db, rid, data.start_datetime, data.end_datetime)
        if not ok:
            raise ValueError(f"Resource {rid} has a booking conflict for this time slot")
        db.add(ResourceBooking(
            event_id=event.event_id,
            resource_id=rid,
            start_datetime=data.start_datetime,
            end_datetime=data.end_datetime,
        ))

    await db.commit()
    return await _load_event(db, event.event_id)


async def update_event(db: AsyncSession, event_id: str, data: EventUpdate) -> CalendarEvent:
    event = await _load_event(db, event_id)
    if not event:
        raise ValueError("Event not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(event, k, v)
    await db.commit()
    return await _load_event(db, event_id)


async def cancel_event(db: AsyncSession, event_id: str) -> None:
    event = await _load_event(db, event_id)
    if not event:
        raise ValueError("Event not found")
    event.status = EventStatus.CANCELLED
    for b in event.bookings:
        b.status = BookingStatus.CANCELLED
    await db.commit()


# ── Bookings ──────────────────────────────────────────────────────────────────

async def list_bookings(
    db: AsyncSession,
    resource_id: Optional[str] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    status: Optional[str] = None,
) -> list:
    q = select(ResourceBooking)
    if resource_id:
        q = q.where(ResourceBooking.resource_id == resource_id)
    if start:
        q = q.where(ResourceBooking.end_datetime >= start)
    if end:
        q = q.where(ResourceBooking.start_datetime <= end)
    if status:
        q = q.where(ResourceBooking.status == status)
    result = await db.execute(q.order_by(ResourceBooking.start_datetime))
    return result.scalars().all()


async def create_booking(db: AsyncSession, data: BookingCreate) -> ResourceBooking:
    ok, _ = await check_availability(db, data.resource_id, data.start_datetime, data.end_datetime)
    if not ok:
        raise ValueError("Resource has a booking conflict for this time slot")
    b = ResourceBooking(**data.model_dump())
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


async def confirm_booking(db: AsyncSession, booking_id: str) -> ResourceBooking:
    result = await db.execute(
        select(ResourceBooking).where(ResourceBooking.booking_id == booking_id)
    )
    b = result.scalar_one_or_none()
    if not b:
        raise ValueError("Booking not found")
    b.status = BookingStatus.CONFIRMED
    await db.commit()
    await db.refresh(b)
    return b


async def cancel_booking(db: AsyncSession, booking_id: str) -> None:
    result = await db.execute(
        select(ResourceBooking).where(ResourceBooking.booking_id == booking_id)
    )
    b = result.scalar_one_or_none()
    if not b:
        raise ValueError("Booking not found")
    b.status = BookingStatus.CANCELLED
    await db.commit()


# ── Recurrence exceptions ─────────────────────────────────────────────────────

async def add_recurrence_exception(db: AsyncSession, recurrence_id: str, exception_date: str) -> None:
    result = await db.execute(
        select(RecurrenceRule).where(RecurrenceRule.recurrence_id == recurrence_id)
    )
    r = result.scalar_one_or_none()
    if not r:
        raise ValueError("Recurrence rule not found")
    exceptions = list(r.exceptions or [])
    if exception_date not in exceptions:
        exceptions.append(exception_date)
    r.exceptions = exceptions
    await db.commit()


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def list_ai_recs(db: AsyncSession) -> list:
    result = await db.execute(
        select(CAIRecommendation).order_by(CAIRecommendation.created_at.desc())
    )
    return result.scalars().all()


async def ack_ai_rec(db: AsyncSession, rec_id: str, data: CAIRecAck) -> CAIRecommendation:
    result = await db.execute(
        select(CAIRecommendation).where(CAIRecommendation.rec_id == rec_id)
    )
    r = result.scalar_one_or_none()
    if not r:
        raise ValueError("Recommendation not found")
    r.status = data.status
    await db.commit()
    await db.refresh(r)
    return r


async def run_schedule_optimizer(db: AsyncSession) -> int:
    now = datetime.utcnow()
    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=7)
    available_hours = 40.0

    resources = await list_resources(db)
    recs = []
    for r in resources:
        if r.status != ResourceStatus.ACTIVE:
            continue
        result = await db.execute(
            select(ResourceBooking).where(
                and_(
                    ResourceBooking.resource_id == r.resource_id,
                    ResourceBooking.status != BookingStatus.CANCELLED,
                    ResourceBooking.start_datetime >= week_start,
                    ResourceBooking.end_datetime <= week_end,
                )
            )
        )
        bookings = result.scalars().all()
        total_h = sum(
            (b.end_datetime - b.start_datetime).total_seconds() / 3600 for b in bookings
        )
        utilization = total_h / available_hours
        if utilization < 0.20:
            recs.append(CAIRecommendation(
                agent_type=CAIAgentType.SCHEDULE_OPTIMIZER,
                title=f"Low utilization: {r.name}",
                body=(
                    f"{r.name} ({r.resource_type.value}) is only "
                    f"{round(utilization * 100, 1)}% utilized this week "
                    f"({round(total_h, 1)}h booked of {available_hours:.0f}h available). "
                    "Consider allocating it to pending tasks or production activities."
                ),
                score=round((1 - utilization) * 100, 1),
                rec_metadata={
                    "resource_id": r.resource_id,
                    "utilization_pct": round(utilization * 100, 1),
                },
            ))
    for rec in recs[:10]:
        db.add(rec)
    await db.commit()
    return len(recs)


async def run_conflict_resolver(db: AsyncSession) -> int:
    now = datetime.utcnow()
    next_30d = now + timedelta(days=30)

    result = await db.execute(
        select(ResourceBooking).where(
            and_(
                ResourceBooking.status != BookingStatus.CANCELLED,
                ResourceBooking.start_datetime >= now,
                ResourceBooking.start_datetime <= next_30d,
            )
        ).order_by(ResourceBooking.resource_id, ResourceBooking.start_datetime)
    )
    bookings = result.scalars().all()

    by_resource: dict = {}
    for b in bookings:
        by_resource.setdefault(b.resource_id, []).append(b)

    recs = []
    for resource_id, bkgs in by_resource.items():
        for i in range(len(bkgs) - 1):
            a, b = bkgs[i], bkgs[i + 1]
            gap_min = (b.start_datetime - a.end_datetime).total_seconds() / 60
            if a.end_datetime > b.start_datetime:
                recs.append(CAIRecommendation(
                    agent_type=CAIAgentType.CONFLICT_RESOLVER,
                    title="Overlapping bookings detected",
                    body=(
                        f"Resource {resource_id} has overlapping bookings: one ends "
                        f"{a.end_datetime.strftime('%Y-%m-%d %H:%M')} and another starts "
                        f"{b.start_datetime.strftime('%Y-%m-%d %H:%M')}. Review and reschedule."
                    ),
                    score=95.0,
                    rec_metadata={
                        "resource_id": resource_id,
                        "booking_a": a.booking_id,
                        "booking_b": b.booking_id,
                    },
                ))
            elif 0 < gap_min < 15:
                recs.append(CAIRecommendation(
                    agent_type=CAIAgentType.CONFLICT_RESOLVER,
                    title="Back-to-back bookings with <15 min buffer",
                    body=(
                        f"Resource {resource_id} has consecutive bookings with only "
                        f"{round(gap_min)}min between them on "
                        f"{b.start_datetime.strftime('%Y-%m-%d')}. "
                        "Consider adding buffer time for setup or transition."
                    ),
                    score=55.0,
                    rec_metadata={"resource_id": resource_id, "gap_minutes": round(gap_min)},
                ))

    for rec in recs[:10]:
        db.add(rec)
    await db.commit()
    return len(recs)
