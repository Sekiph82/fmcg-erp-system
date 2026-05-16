from __future__ import annotations

import uuid
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.logistics import (
    InternationalShipment, ShipmentContainer, ShipmentPOLink,
    CustomsDocument, CustomsClearance, ArrivalNotification,
    LocalLogisticsCost, LocalCostStatus,
    IntlShipmentStatus, ContainerStatus,
)


# ── Shipments ──────────────────────────────────────────────────────────────────

async def list_shipments(
    db: AsyncSession,
    status: Optional[IntlShipmentStatus] = None,
    limit: int = 100,
) -> List[InternationalShipment]:
    q = (
        select(InternationalShipment)
        .options(
            selectinload(InternationalShipment.containers),
            selectinload(InternationalShipment.po_links).selectinload(ShipmentPOLink.po),
            selectinload(InternationalShipment.clearance),
            selectinload(InternationalShipment.arrival),
        )
        .order_by(InternationalShipment.eta.desc().nullslast(), InternationalShipment.created_at.desc())
    )
    if status:
        q = q.where(InternationalShipment.status == status)
    return list((await db.execute(q.limit(limit))).scalars().all())


async def get_shipment(db: AsyncSession, shipment_id: uuid.UUID) -> Optional[InternationalShipment]:
    result = await db.execute(
        select(InternationalShipment)
        .options(
            selectinload(InternationalShipment.containers),
            selectinload(InternationalShipment.po_links).selectinload(ShipmentPOLink.po).selectinload(
                __import__("app.models.procurement", fromlist=["PurchaseOrder"]).PurchaseOrder.supplier
            ),
            selectinload(InternationalShipment.customs_docs),
            selectinload(InternationalShipment.clearance),
            selectinload(InternationalShipment.arrival),
        )
        .where(InternationalShipment.id == shipment_id)
    )
    return result.scalar_one_or_none()


async def create_shipment(db: AsyncSession, data: dict, user_id: uuid.UUID) -> InternationalShipment:
    ship = InternationalShipment(**data, created_by_id=user_id)
    db.add(ship)
    await db.flush()
    # Auto-create ArrivalNotification
    arrival = ArrivalNotification(
        shipment_id=ship.id,
        eta_original=data.get("eta"),
        eta_revised=data.get("eta"),
    )
    db.add(arrival)
    await db.flush()
    await db.refresh(ship)
    return ship


async def update_shipment(db: AsyncSession, ship: InternationalShipment, data: dict) -> InternationalShipment:
    for k, v in data.items():
        if v is not None:
            setattr(ship, k, v)
    # Sync ETA to arrival notification if it changed
    if "eta" in data and ship.arrival:
        if not ship.arrival.eta_revised:
            ship.arrival.eta_revised = data["eta"]
    await db.flush()
    await db.refresh(ship)
    return ship


# ── Containers ─────────────────────────────────────────────────────────────────

async def list_containers(
    db: AsyncSession,
    shipment_id: Optional[uuid.UUID] = None,
    status: Optional[ContainerStatus] = None,
    limit: int = 200,
    offset: int = 0,
) -> List[ShipmentContainer]:
    q = (
        select(ShipmentContainer)
        .options(selectinload(ShipmentContainer.shipment))
        .order_by(ShipmentContainer.container_no)
    )
    if shipment_id:
        q = q.where(ShipmentContainer.shipment_id == shipment_id)
    if status:
        q = q.where(ShipmentContainer.status == status)
    return list((await db.execute(q.offset(offset).limit(min(limit, 1000)))).scalars().all())


async def create_container(db: AsyncSession, data: dict) -> ShipmentContainer:
    c = ShipmentContainer(**data)
    db.add(c)
    await db.flush()
    await db.refresh(c)
    return c


async def update_container(db: AsyncSession, c: ShipmentContainer, data: dict) -> ShipmentContainer:
    for k, v in data.items():
        if v is not None:
            setattr(c, k, v)
    await db.flush()
    await db.refresh(c)
    return c


async def get_container(db: AsyncSession, cid: uuid.UUID) -> Optional[ShipmentContainer]:
    result = await db.execute(
        select(ShipmentContainer)
        .options(selectinload(ShipmentContainer.shipment))
        .where(ShipmentContainer.id == cid)
    )
    return result.scalar_one_or_none()


# ── PO Links ───────────────────────────────────────────────────────────────────

async def list_po_links(db: AsyncSession, shipment_id: uuid.UUID) -> List[ShipmentPOLink]:
    q = (
        select(ShipmentPOLink)
        .options(
            selectinload(ShipmentPOLink.po).selectinload(
                __import__("app.models.procurement", fromlist=["PurchaseOrder"]).PurchaseOrder.supplier
            )
        )
        .where(ShipmentPOLink.shipment_id == shipment_id)
    )
    return list((await db.execute(q)).scalars().all())


async def add_po_link(db: AsyncSession, shipment_id: uuid.UUID, po_id: uuid.UUID, notes: Optional[str]) -> ShipmentPOLink:
    link = ShipmentPOLink(shipment_id=shipment_id, po_id=po_id, notes=notes)
    db.add(link)
    await db.flush()
    await db.refresh(link)
    return link


async def remove_po_link(db: AsyncSession, link_id: uuid.UUID) -> None:
    result = await db.execute(select(ShipmentPOLink).where(ShipmentPOLink.id == link_id))
    link = result.scalar_one_or_none()
    if link:
        await db.delete(link)
        await db.flush()


# ── Customs Documents ──────────────────────────────────────────────────────────

async def list_customs_docs(db: AsyncSession, shipment_id: uuid.UUID) -> List[CustomsDocument]:
    q = (
        select(CustomsDocument)
        .where(CustomsDocument.shipment_id == shipment_id)
        .order_by(CustomsDocument.doc_type, CustomsDocument.created_at)
    )
    return list((await db.execute(q)).scalars().all())


async def create_customs_doc(db: AsyncSession, data: dict) -> CustomsDocument:
    doc = CustomsDocument(**data)
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return doc


async def update_customs_doc(db: AsyncSession, doc: CustomsDocument, data: dict) -> CustomsDocument:
    for k, v in data.items():
        if v is not None:
            setattr(doc, k, v)
    await db.flush()
    await db.refresh(doc)
    return doc


async def get_customs_doc(db: AsyncSession, doc_id: uuid.UUID) -> Optional[CustomsDocument]:
    result = await db.execute(select(CustomsDocument).where(CustomsDocument.id == doc_id))
    return result.scalar_one_or_none()


# ── Customs Clearance ──────────────────────────────────────────────────────────

async def get_clearance(db: AsyncSession, shipment_id: uuid.UUID) -> Optional[CustomsClearance]:
    result = await db.execute(
        select(CustomsClearance).where(CustomsClearance.shipment_id == shipment_id)
    )
    return result.scalar_one_or_none()


async def create_clearance(db: AsyncSession, data: dict) -> CustomsClearance:
    cl = CustomsClearance(**data)
    db.add(cl)
    await db.flush()
    await db.refresh(cl)
    return cl


async def update_clearance(db: AsyncSession, cl: CustomsClearance, data: dict) -> CustomsClearance:
    for k, v in data.items():
        if v is not None:
            setattr(cl, k, v)
    await db.flush()
    await db.refresh(cl)
    return cl


# ── Arrival Notifications ──────────────────────────────────────────────────────

async def list_arrivals(db: AsyncSession, limit: int = 50) -> List[ArrivalNotification]:
    q = (
        select(ArrivalNotification)
        .options(selectinload(ArrivalNotification.shipment))
        .order_by(ArrivalNotification.created_at.desc())
    )
    return list((await db.execute(q.limit(limit))).scalars().all())


async def get_arrival(db: AsyncSession, shipment_id: uuid.UUID) -> Optional[ArrivalNotification]:
    result = await db.execute(
        select(ArrivalNotification)
        .options(selectinload(ArrivalNotification.shipment))
        .where(ArrivalNotification.shipment_id == shipment_id)
    )
    return result.scalar_one_or_none()


async def update_arrival(db: AsyncSession, arrival: ArrivalNotification, data: dict) -> ArrivalNotification:
    for k, v in data.items():
        if v is not None:
            setattr(arrival, k, v)
    # Propagate ATA to shipment
    if data.get("ata") and arrival.shipment:
        arrival.shipment.ata = data["ata"]
        if arrival.shipment.status == IntlShipmentStatus.IN_TRANSIT:
            arrival.shipment.status = IntlShipmentStatus.ARRIVED_PORT
    if data.get("delivery_date") and arrival.shipment:
        arrival.shipment.status = IntlShipmentStatus.DELIVERED
    await db.flush()
    await db.refresh(arrival)
    return arrival


# ── Local Logistics Costs ──────────────────────────────────────────────────────

async def list_local_costs(db: AsyncSession, shipment_id: uuid.UUID) -> List[LocalLogisticsCost]:
    q = (
        select(LocalLogisticsCost)
        .where(LocalLogisticsCost.shipment_id == shipment_id)
        .order_by(LocalLogisticsCost.created_at)
    )
    return list((await db.execute(q)).scalars().all())


async def create_local_cost(db: AsyncSession, data: dict, user_id: uuid.UUID) -> LocalLogisticsCost:
    cost = LocalLogisticsCost(**data, recorded_by_id=user_id)
    db.add(cost)
    await db.flush()
    await db.refresh(cost)
    return cost


async def get_local_cost(db: AsyncSession, cost_id: uuid.UUID) -> Optional[LocalLogisticsCost]:
    result = await db.execute(
        select(LocalLogisticsCost).where(LocalLogisticsCost.id == cost_id)
    )
    return result.scalar_one_or_none()


async def update_local_cost(db: AsyncSession, cost: LocalLogisticsCost, data: dict) -> LocalLogisticsCost:
    for k, v in data.items():
        if v is not None:
            setattr(cost, k, v)
    await db.flush()
    await db.refresh(cost)
    return cost


async def delete_local_cost(db: AsyncSession, cost: LocalLogisticsCost) -> None:
    await db.delete(cost)
    await db.flush()
