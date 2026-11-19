from __future__ import annotations
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.deps import get_current_user, require_permission
from app.crud import delivery as crud
from app.models.delivery import TripStatus
from app.schemas.delivery import (
    DeliveryTripCreate, DeliveryTripUpdate, DeliveryTripRead,
    ProofOfDeliveryCreate, ProofOfDeliveryRead,
)

router = APIRouter()


# ── Delivery Trips ────────────────────────────────────────────────────────────

@router.get("/trips", response_model=List[DeliveryTripRead],
            dependencies=[Depends(require_permission("sales", "view"))])
async def list_trips(
    status: Optional[TripStatus] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    trips = await crud.list_trips(db, status=status, limit=limit)
    result = []
    for t in trips:
        td = DeliveryTripRead.model_validate(t)
        td.order_count = len(t.orders)
        result.append(td)
    return result


async def _driver_logins(db: AsyncSession) -> list[dict]:
    """Active logins of staff who can drive a trip: an active employee or sales rep linked to a user."""
    from sqlalchemy import or_, select
    from app.models.field_sales import SalesRep
    from app.models.hr import Employee, EmployeeStatus
    from app.models.user import User

    rows = (await db.execute(
        select(User.id, User.full_name, User.username).where(User.is_active.is_(True), or_(
            User.id.in_(select(Employee.user_id).where(Employee.user_id.is_not(None), Employee.status == EmployeeStatus.ACTIVE)),
            User.id.in_(select(SalesRep.user_id).where(SalesRep.user_id.is_not(None), SalesRep.is_active.is_(True)))))
        .order_by(User.full_name))).all()
    return [{"id": str(r.id), "name": r.full_name or r.username} for r in rows]


@router.get("/driver-logins", dependencies=[Depends(require_permission("sales", "create"))])
async def driver_logins(db: AsyncSession = Depends(get_db)):
    """Who can be set as a trip's driver; that person then sees the trip in the Field App (My deliveries)."""
    return await _driver_logins(db)


@router.post("/trips", response_model=DeliveryTripRead, status_code=201,
             dependencies=[Depends(require_permission("sales", "create"))])
async def create_trip(
    data: DeliveryTripCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if data.driver_user_id and str(data.driver_user_id) not in {d["id"] for d in await _driver_logins(db)}:
        raise HTTPException(422, "The driver must be an active employee or sales rep login.")
    trip = await crud.create_trip(db, data, current_user.id)
    await db.commit()
    trip = await crud.get_trip(db, trip.id)  # reload with orders: the response reads them (lazy load fails after commit)
    td = DeliveryTripRead.model_validate(trip)
    td.order_count = len(trip.orders)
    return td


@router.get("/trips/{trip_id}", response_model=DeliveryTripRead,
            dependencies=[Depends(require_permission("sales", "view"))])
async def get_trip(trip_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    trip = await crud.get_trip(db, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Delivery trip not found")
    td = DeliveryTripRead.model_validate(trip)
    td.order_count = len(trip.orders)
    return td


@router.patch("/trips/{trip_id}", response_model=DeliveryTripRead,
              dependencies=[Depends(require_permission("sales", "edit"))])
async def update_trip(
    trip_id: uuid.UUID,
    data: DeliveryTripUpdate,
    db: AsyncSession = Depends(get_db),
):
    trip = await crud.get_trip(db, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Delivery trip not found")
    if data.driver_user_id and str(data.driver_user_id) not in {d["id"] for d in await _driver_logins(db)}:
        raise HTTPException(422, "The driver must be an active employee or sales rep login.")
    trip = await crud.update_trip(db, trip, data)
    await db.commit()
    td = DeliveryTripRead.model_validate(trip)
    td.order_count = len(trip.orders)
    return td


@router.post("/trips/{trip_id}/orders/{trip_order_id}/status",
             dependencies=[Depends(require_permission("sales", "edit"))])
async def update_order_status(
    trip_id: uuid.UUID,
    trip_order_id: uuid.UUID,
    status: str,
    failure_reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    to = await crud.update_trip_order_status(db, trip_order_id, status, failure_reason)
    if not to:
        raise HTTPException(status_code=404, detail="Trip order not found")
    await db.commit()
    return {"ok": True}


# ── Proof of Delivery ─────────────────────────────────────────────────────────

@router.get("/pod", response_model=List[ProofOfDeliveryRead],
            dependencies=[Depends(require_permission("sales", "view"))])
async def list_pods(limit: int = Query(50, le=200), db: AsyncSession = Depends(get_db)):
    return await crud.list_pods(db, limit=limit)


@router.get("/pod/shipment/{shipment_id}", response_model=ProofOfDeliveryRead,
            dependencies=[Depends(require_permission("sales", "view"))])
async def get_pod(shipment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    pod = await crud.get_pod_by_shipment(db, shipment_id)
    if not pod:
        raise HTTPException(status_code=404, detail="POD not found")
    return pod


@router.post("/pod", response_model=ProofOfDeliveryRead, status_code=201,
             dependencies=[Depends(require_permission("sales", "create"))])
async def create_pod(
    data: ProofOfDeliveryCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pod = await crud.create_pod(db, data, current_user.id)
    # Mark the shipment as DELIVERED
    from app.models.sales import Shipment, ShipmentStatus
    from sqlalchemy import select
    res = await db.execute(select(Shipment).where(Shipment.id == data.shipment_id))
    shipment = res.scalar_one_or_none()
    if shipment and shipment.status == ShipmentStatus.DISPATCHED:
        shipment.status = ShipmentStatus.DELIVERED
    await db.commit()
    return pod
