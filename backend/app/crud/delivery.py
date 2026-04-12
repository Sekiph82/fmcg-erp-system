from __future__ import annotations
from typing import Optional, List
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.delivery import DeliveryTrip, TripOrder, ProofOfDelivery, TripStatus
from app.schemas.delivery import DeliveryTripCreate, DeliveryTripUpdate, ProofOfDeliveryCreate


async def list_trips(
    db: AsyncSession,
    *,
    status: Optional[TripStatus] = None,
    limit: int = 50,
) -> List[DeliveryTrip]:
    q = select(DeliveryTrip).options(
        selectinload(DeliveryTrip.orders).selectinload(TripOrder.shipment),
    )
    if status:
        q = q.where(DeliveryTrip.status == status)
    result = await db.execute(q.order_by(DeliveryTrip.trip_date.desc()).limit(limit))
    return list(result.scalars().all())


async def get_trip(db: AsyncSession, trip_id: uuid.UUID) -> Optional[DeliveryTrip]:
    result = await db.execute(
        select(DeliveryTrip)
        .options(
            selectinload(DeliveryTrip.orders).selectinload(TripOrder.shipment),
            selectinload(DeliveryTrip.orders).selectinload(TripOrder.pod),
            selectinload(DeliveryTrip.warehouse),
            selectinload(DeliveryTrip.created_by),
        )
        .where(DeliveryTrip.id == trip_id)
    )
    return result.scalar_one_or_none()


async def create_trip(db: AsyncSession, data: DeliveryTripCreate, created_by_id: uuid.UUID) -> DeliveryTrip:
    orders_data = data.orders
    trip = DeliveryTrip(**data.model_dump(exclude={"orders"}), created_by_id=created_by_id)
    db.add(trip)
    await db.flush()
    for o in orders_data:
        db.add(TripOrder(trip_id=trip.id, **o.model_dump()))
    await db.flush()
    await db.refresh(trip)
    return trip


async def update_trip(db: AsyncSession, trip: DeliveryTrip, data: DeliveryTripUpdate) -> DeliveryTrip:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(trip, k, v)
    await db.flush()
    await db.refresh(trip)
    return trip


async def update_trip_order_status(
    db: AsyncSession,
    trip_order_id: uuid.UUID,
    status: str,
    failure_reason: Optional[str] = None,
) -> Optional[TripOrder]:
    result = await db.execute(select(TripOrder).where(TripOrder.id == trip_order_id))
    to = result.scalar_one_or_none()
    if to:
        from app.models.delivery import TripOrderStatus
        to.status = TripOrderStatus(status)
        if failure_reason:
            to.failure_reason = failure_reason
        await db.flush()
    return to


async def create_pod(
    db: AsyncSession,
    data: ProofOfDeliveryCreate,
    confirmed_by_id: uuid.UUID,
) -> ProofOfDelivery:
    pod = ProofOfDelivery(**data.model_dump(), confirmed_by_id=confirmed_by_id)
    db.add(pod)
    await db.flush()
    await db.refresh(pod)
    return pod


async def get_pod_by_shipment(db: AsyncSession, shipment_id: uuid.UUID) -> Optional[ProofOfDelivery]:
    result = await db.execute(
        select(ProofOfDelivery).where(ProofOfDelivery.shipment_id == shipment_id)
    )
    return result.scalar_one_or_none()


async def list_pods(db: AsyncSession, limit: int = 50) -> List[ProofOfDelivery]:
    result = await db.execute(
        select(ProofOfDelivery)
        .options(selectinload(ProofOfDelivery.shipment))
        .order_by(ProofOfDelivery.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
