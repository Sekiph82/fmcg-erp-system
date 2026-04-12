from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.logistics import (
    InternationalShipment, ShipmentContainer, ShipmentPOLink,
    CustomsDocument, CustomsClearance, ArrivalNotification,
    IntlShipmentStatus, CustomsDocStatus, ClearanceStatus,
)
from app.schemas.logistics import ShipmentDashboardRow


async def get_dashboard_rows(db: AsyncSession) -> List[ShipmentDashboardRow]:
    """Enriched shipment list for Turkey→Kenya visibility dashboard."""
    q = (
        select(InternationalShipment)
        .options(
            selectinload(InternationalShipment.containers),
            selectinload(InternationalShipment.po_links),
            selectinload(InternationalShipment.customs_docs),
            selectinload(InternationalShipment.clearance),
            selectinload(InternationalShipment.arrival),
        )
        .where(InternationalShipment.status != IntlShipmentStatus.CANCELLED)
        .order_by(InternationalShipment.eta.asc().nullslast(), InternationalShipment.created_at.desc())
    )
    shipments = list((await db.execute(q)).scalars().all())

    today = date.today()
    rows = []
    for s in shipments:
        eta_effective = (s.arrival.eta_revised if s.arrival and s.arrival.eta_revised else s.eta)
        days_to_eta: Optional[int] = None
        if eta_effective and not s.ata:
            days_to_eta = (eta_effective - today).days

        has_overdue_docs = any(
            d.status in (CustomsDocStatus.DRAFT, CustomsDocStatus.REJECTED)
            for d in s.customs_docs
        )

        rows.append(ShipmentDashboardRow(
            shipment_id=str(s.id),
            shipment_no=s.shipment_no,
            mode=s.mode,
            status=s.status,
            carrier=s.carrier,
            vessel_name=s.vessel_name,
            bl_number=s.bl_number,
            origin_port=s.origin_port,
            destination_port=s.destination_port,
            planned_departure=s.planned_departure,
            eta=s.eta,
            eta_revised=s.arrival.eta_revised if s.arrival else None,
            ata=s.ata,
            days_to_eta=days_to_eta,
            container_count=len(s.containers),
            po_count=len(s.po_links),
            clearance_status=s.clearance.status if s.clearance else None,
            total_taxes_kes=float(s.clearance.total_taxes_kes) if s.clearance and s.clearance.total_taxes_kes else None,
            has_overdue_docs=has_overdue_docs,
        ))

    return rows


async def get_eta_alerts(db: AsyncSession, days_ahead: int = 14) -> List[InternationalShipment]:
    """Shipments arriving within `days_ahead` days that haven't been delivered."""
    today = date.today()
    cutoff = today + timedelta(days=days_ahead)
    q = (
        select(InternationalShipment)
        .options(selectinload(InternationalShipment.arrival))
        .where(
            InternationalShipment.eta.isnot(None),
            InternationalShipment.eta <= cutoff,
            InternationalShipment.status.in_([
                IntlShipmentStatus.BOOKING_CONFIRMED,
                IntlShipmentStatus.CARGO_LOADED,
                IntlShipmentStatus.IN_TRANSIT,
            ]),
        )
        .order_by(InternationalShipment.eta)
    )
    return list((await db.execute(q)).scalars().all())


def next_shipment_no(count: int) -> str:
    return f"ISH-{count + 1:05d}"
