from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime
from app.db.session import get_db
from app.schemas.calendar import (
    ResourceOut, ResourceCreate, ResourceUpdate,
    EventOut, EventCreate, EventUpdate,
    BookingOut, BookingCreate,
    AvailabilityCheck, SlotRequest,
    CAIRecOut, CAIRecAck,
)
from app.services import calendar_service

router = APIRouter()


# ── Resources ─────────────────────────────────────────────────────────────────

@router.get("/resources", response_model=List[ResourceOut])
async def list_resources(
    resource_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await calendar_service.list_resources(db, resource_type, status)


@router.post("/resources", response_model=ResourceOut)
async def create_resource(data: ResourceCreate, db: AsyncSession = Depends(get_db)):
    return await calendar_service.create_resource(db, data)


@router.patch("/resources/{resource_id}", response_model=ResourceOut)
async def update_resource(
    resource_id: str, data: ResourceUpdate, db: AsyncSession = Depends(get_db)
):
    try:
        return await calendar_service.update_resource(db, resource_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Events ────────────────────────────────────────────────────────────────────

@router.get("/events")
async def list_events(
    start: Optional[str] = None,
    end: Optional[str] = None,
    event_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    start_dt = datetime.fromisoformat(start) if start else None
    end_dt = datetime.fromisoformat(end) if end else None
    return await calendar_service.list_events(db, start_dt, end_dt, event_type, status)


@router.post("/events", response_model=EventOut)
async def create_event(data: EventCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await calendar_service.create_event(db, data)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/events/{event_id}", response_model=EventOut)
async def get_event(event_id: str, db: AsyncSession = Depends(get_db)):
    e = await calendar_service.get_event(db, event_id)
    if not e:
        raise HTTPException(404, "Event not found")
    return e


@router.patch("/events/{event_id}", response_model=EventOut)
async def update_event(
    event_id: str, data: EventUpdate, db: AsyncSession = Depends(get_db)
):
    try:
        return await calendar_service.update_event(db, event_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.delete("/events/{event_id}")
async def cancel_event(event_id: str, db: AsyncSession = Depends(get_db)):
    try:
        await calendar_service.cancel_event(db, event_id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Bookings ──────────────────────────────────────────────────────────────────

@router.get("/bookings", response_model=List[BookingOut])
async def list_bookings(
    resource_id: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    start_dt = datetime.fromisoformat(start) if start else None
    end_dt = datetime.fromisoformat(end) if end else None
    return await calendar_service.list_bookings(db, resource_id, start_dt, end_dt, status)


@router.post("/bookings", response_model=BookingOut)
async def create_booking(data: BookingCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await calendar_service.create_booking(db, data)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/bookings/{booking_id}/confirm", response_model=BookingOut)
async def confirm_booking(booking_id: str, db: AsyncSession = Depends(get_db)):
    try:
        return await calendar_service.confirm_booking(db, booking_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.delete("/bookings/{booking_id}")
async def cancel_booking(booking_id: str, db: AsyncSession = Depends(get_db)):
    try:
        await calendar_service.cancel_booking(db, booking_id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Availability ──────────────────────────────────────────────────────────────

@router.post("/availability/check")
async def check_availability(data: AvailabilityCheck, db: AsyncSession = Depends(get_db)):
    ok, conflicts = await calendar_service.check_availability(
        db, data.resource_id, data.start_datetime, data.end_datetime, data.exclude_booking_id
    )
    return {"available": ok, "conflicts": len(conflicts)}


@router.post("/availability/slots")
async def get_available_slots(data: SlotRequest, db: AsyncSession = Depends(get_db)):
    return await calendar_service.get_available_slots(db, data)


# ── Recurrence ────────────────────────────────────────────────────────────────

@router.post("/recurrences/{recurrence_id}/exceptions")
async def add_recurrence_exception(
    recurrence_id: str, date: str, db: AsyncSession = Depends(get_db)
):
    try:
        await calendar_service.add_recurrence_exception(db, recurrence_id, date)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── AI ────────────────────────────────────────────────────────────────────────

@router.get("/ai/recs", response_model=List[CAIRecOut])
async def list_ai_recs(db: AsyncSession = Depends(get_db)):
    return await calendar_service.list_ai_recs(db)


@router.post("/ai/run/schedule-optimizer")
async def run_schedule_optimizer(db: AsyncSession = Depends(get_db)):
    count = await calendar_service.run_schedule_optimizer(db)
    return {"generated": count}


@router.post("/ai/run/conflict-resolver")
async def run_conflict_resolver(db: AsyncSession = Depends(get_db)):
    count = await calendar_service.run_conflict_resolver(db)
    return {"generated": count}


@router.patch("/ai/recs/{rec_id}", response_model=CAIRecOut)
async def ack_ai_rec(rec_id: str, data: CAIRecAck, db: AsyncSession = Depends(get_db)):
    try:
        return await calendar_service.ack_ai_rec(db, rec_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))
