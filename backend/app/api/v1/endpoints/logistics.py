from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user, require_permission
from app.models.user import User
from app.models.logistics import (
    InternationalShipment, ShipmentContainer, ShipmentPOLink, ShipmentOwnershipEvent,
    CustomsDocument, CustomsClearance, CustomsClearanceMilestone, ArrivalNotification,
    LocalLogisticsCost,
    IntlShipmentStatus, InventoryOwnerStatus, ContainerStatus, ClearanceStatus,
)
from app.models.procurement import POStatus, PurchaseOrder
import app.crud.logistics as crud
import app.services.logistics_service as svc
from app.schemas.logistics import (
    ShipmentCreate, ShipmentUpdate, ShipmentRead,
    ContainerCreate, ContainerUpdate, ContainerRead,
    POLinkCreate, POLinkRead,
    ShipmentOwnershipUpdate, ShipmentOwnershipEventRead,
    CustomsDocCreate, CustomsDocUpdate, CustomsDocRead,
    ClearanceCreate, ClearanceUpdate, ClearanceRead,
    ClearanceMilestoneCreate, ClearanceMilestoneRead,
    ArrivalCreate, ArrivalUpdate, ArrivalRead,
    LocalCostCreate, LocalCostUpdate, LocalCostRead, LocalCostSummary,
    ShipmentDashboardRow,
)

router = APIRouter()

SHIPMENT_STATUS_TRANSITIONS: dict[IntlShipmentStatus, set[IntlShipmentStatus]] = {
    IntlShipmentStatus.DRAFT: {IntlShipmentStatus.BOOKING_CONFIRMED, IntlShipmentStatus.CANCELLED},
    IntlShipmentStatus.BOOKING_CONFIRMED: {IntlShipmentStatus.CARGO_LOADED, IntlShipmentStatus.CANCELLED},
    IntlShipmentStatus.CARGO_LOADED: {IntlShipmentStatus.IN_TRANSIT},
    IntlShipmentStatus.IN_TRANSIT: {IntlShipmentStatus.ARRIVED_PORT},
    IntlShipmentStatus.ARRIVED_PORT: set(),
    IntlShipmentStatus.CUSTOMS_HOLD: set(),
    IntlShipmentStatus.CUSTOMS_CLEARED: {IntlShipmentStatus.OUT_FOR_DELIVERY},
    IntlShipmentStatus.OUT_FOR_DELIVERY: {IntlShipmentStatus.DELIVERED},
    IntlShipmentStatus.DELIVERED: set(),
    IntlShipmentStatus.CANCELLED: set(),
}

CLEARANCE_STATUS_TRANSITIONS: dict[ClearanceStatus, set[ClearanceStatus]] = {
    ClearanceStatus.PENDING: {ClearanceStatus.DOCS_SUBMITTED, ClearanceStatus.HELD},
    ClearanceStatus.DOCS_SUBMITTED: {ClearanceStatus.UNDER_REVIEW, ClearanceStatus.HELD},
    ClearanceStatus.UNDER_REVIEW: {
        ClearanceStatus.EXAM_REQUESTED, ClearanceStatus.DUTY_ASSESSED, ClearanceStatus.HELD,
    },
    ClearanceStatus.EXAM_REQUESTED: {
        ClearanceStatus.UNDER_REVIEW, ClearanceStatus.DUTY_ASSESSED, ClearanceStatus.HELD,
    },
    ClearanceStatus.DUTY_ASSESSED: {ClearanceStatus.DUTY_PAID, ClearanceStatus.HELD},
    ClearanceStatus.DUTY_PAID: {ClearanceStatus.CLEARED, ClearanceStatus.HELD},
    ClearanceStatus.HELD: {ClearanceStatus.UNDER_REVIEW},
    ClearanceStatus.CLEARED: set(),
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _s_read(s, *, include_counts: bool = True) -> ShipmentRead:
    from datetime import date
    today = date.today()
    eta = s.eta
    days_to_eta = None
    if eta and not s.ata:
        days_to_eta = (eta - today).days
    return ShipmentRead(
        id=str(s.id),
        shipment_no=s.shipment_no,
        mode=s.mode,
        origin_country=s.origin_country,
        origin_city=s.origin_city,
        origin_port=s.origin_port,
        destination_country=s.destination_country,
        destination_city=s.destination_city,
        destination_port=s.destination_port,
        final_destination=s.final_destination,
        carrier=s.carrier,
        vessel_name=s.vessel_name,
        voyage_no=s.voyage_no,
        bl_number=s.bl_number,
        planned_departure=s.planned_departure,
        actual_departure=s.actual_departure,
        eta=s.eta,
        ata=s.ata,
        status=s.status,
        incoterm=s.incoterm,
        currency=s.currency,
        freight_cost=float(s.freight_cost) if s.freight_cost else None,
        insurance_cost=float(s.insurance_cost) if s.insurance_cost else None,
        total_cbm=float(s.total_cbm) if s.total_cbm else None,
        total_weight_kg=float(s.total_weight_kg) if s.total_weight_kg else None,
        forwarder=s.forwarder,
        notes=s.notes,
        created_at=s.created_at,
        container_count=len(s.containers) if hasattr(s, "containers") and s.containers else 0,
        po_count=len(s.po_links) if hasattr(s, "po_links") and s.po_links else 0,
        days_to_eta=days_to_eta,
    )


def _c_read(c) -> ContainerRead:
    return ContainerRead(
        id=str(c.id),
        shipment_id=str(c.shipment_id),
        shipment_no=c.shipment.shipment_no if c.shipment else None,
        container_no=c.container_no,
        seal_no=c.seal_no,
        container_type=c.container_type,
        tare_weight_kg=float(c.tare_weight_kg) if c.tare_weight_kg else None,
        gross_weight_kg=float(c.gross_weight_kg) if c.gross_weight_kg else None,
        cbm=float(c.cbm) if c.cbm else None,
        contents_summary=c.contents_summary,
        status=c.status,
        customs_release_no=c.customs_release_no,
        demurrage_free_days=c.demurrage_free_days,
        notes=c.notes,
        created_at=c.created_at,
    )


def _link_read(link) -> POLinkRead:
    po = link.po if hasattr(link, "po") and link.po else None
    po_total = (
        sum(
            (
                (
                    line.ordered_quantity * line.unit_price * (Decimal("1") + line.tax_rate)
                ).quantize(Decimal("0.01"))
                for line in po.lines
            ),
            start=Decimal("0.00"),
        )
        if po and po.lines else None
    )
    return POLinkRead(
        id=str(link.id),
        shipment_id=str(link.shipment_id),
        po_id=str(link.po_id),
        po_no=po.po_no if po else None,
        supplier_name=po.supplier.name if po and po.supplier else None,
        po_total=float(po_total) if po_total is not None else None,
        inventory_owner_status=link.inventory_owner_status,
        notes=link.notes,
        created_at=link.created_at,
    )


def _ownership_event_read(event) -> ShipmentOwnershipEventRead:
    actor_name = None
    if event.changed_by is not None:
        actor_name = getattr(event.changed_by, "full_name", None)
        if not actor_name:
            actor_name = " ".join(
                part for part in (
                    getattr(event.changed_by, "first_name", None),
                    getattr(event.changed_by, "last_name", None),
                ) if part
            ) or getattr(event.changed_by, "username", None)
    return ShipmentOwnershipEventRead(
        id=str(event.id),
        shipment_po_link_id=str(event.shipment_po_link_id),
        previous_owner=event.previous_owner,
        new_owner=event.new_owner,
        source_reference=event.source_reference,
        notes=event.notes,
        effective_at=event.effective_at,
        changed_by_id=str(event.changed_by_id) if event.changed_by_id else None,
        changed_by_name=actor_name,
        created_at=event.created_at,
    )


def _doc_read(d) -> CustomsDocRead:
    return CustomsDocRead(
        id=str(d.id),
        shipment_id=str(d.shipment_id),
        doc_type=d.doc_type,
        doc_no=d.doc_no,
        doc_date=d.doc_date,
        issuer=d.issuer,
        description=d.description,
        file_ref=d.file_ref,
        status=d.status,
        created_at=d.created_at,
    )


def _cl_read(cl) -> ClearanceRead:
    return ClearanceRead(
        id=str(cl.id),
        shipment_id=str(cl.shipment_id),
        entry_no=cl.entry_no,
        agent_name=cl.agent_name,
        submission_date=cl.submission_date,
        examination_date=cl.examination_date,
        clearance_date=cl.clearance_date,
        status=cl.status,
        cif_value_usd=float(cl.cif_value_usd) if cl.cif_value_usd else None,
        import_duty=float(cl.import_duty) if cl.import_duty else None,
        vat=float(cl.vat) if cl.vat else None,
        idf_fee=float(cl.idf_fee) if cl.idf_fee else None,
        railway_development_levy=float(cl.railway_development_levy) if cl.railway_development_levy else None,
        other_charges=float(cl.other_charges) if cl.other_charges else None,
        total_taxes_kes=float(cl.total_taxes_kes) if cl.total_taxes_kes else None,
        kra_pin=cl.kra_pin,
        notes=cl.notes,
        created_at=cl.created_at,
    )


def _arr_read(a) -> ArrivalRead:
    return ArrivalRead(
        id=str(a.id),
        shipment_id=str(a.shipment_id),
        eta_original=a.eta_original,
        eta_revised=a.eta_revised,
        eta_alert_sent=a.eta_alert_sent,
        ata=a.ata,
        port_discharge_date=a.port_discharge_date,
        customs_clearance_date=a.customs_clearance_date,
        delivery_date=a.delivery_date,
        grn_id=str(a.grn_id) if a.grn_id else None,
        notes=a.notes,
        created_at=a.created_at,
    )


# ── Shipments ──────────────────────────────────────────────────────────────────

@router.get("/shipments/", response_model=List[ShipmentRead])
async def list_shipments(
    status: Optional[IntlShipmentStatus] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    ships = await crud.list_shipments(db, status=status)
    return [_s_read(s) for s in ships]


@router.post("/shipments/", response_model=ShipmentRead, status_code=status.HTTP_201_CREATED)
async def create_shipment(
    body: ShipmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count_res = await db.execute(select(func.count()).select_from(InternationalShipment))
    count = count_res.scalar() or 0
    data = body.model_dump()
    # Use provided shipment_no or auto-generate
    if not data.get("shipment_no"):
        data["shipment_no"] = svc.next_shipment_no(count)
    ship = await crud.create_shipment(db, data, current_user.id)
    await db.commit()
    ship = await crud.get_shipment(db, ship.id)
    return _s_read(ship)


@router.get("/shipments/{shipment_id}", response_model=ShipmentRead)
async def get_shipment(
    shipment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    ship = await crud.get_shipment(db, shipment_id)
    if not ship:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return _s_read(ship)


@router.patch("/shipments/{shipment_id}", response_model=ShipmentRead)
async def update_shipment(
    shipment_id: uuid.UUID,
    body: ShipmentUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("logistics", "edit")),
):
    ship = await crud.get_shipment_for_update(db, shipment_id)
    if not ship:
        raise HTTPException(status_code=404, detail="Shipment not found")
    changes = body.model_dump(exclude_none=True)
    requested_status = changes.get("status")
    if requested_status is not None and requested_status != ship.status:
        if requested_status in {IntlShipmentStatus.CUSTOMS_HOLD, IntlShipmentStatus.CUSTOMS_CLEARED}:
            raise HTTPException(status_code=409, detail="Customs shipment status must be recorded through a clearance milestone")
        allowed = SHIPMENT_STATUS_TRANSITIONS.get(ship.status, set())
        if requested_status not in allowed:
            raise HTTPException(
                status_code=409,
                detail=f"Shipment status cannot move from {ship.status.value} to {requested_status.value}",
            )
    ship = await crud.update_shipment(db, ship, changes)
    await db.commit()
    ship = await crud.get_shipment(db, shipment_id)
    return _s_read(ship)


# ── Containers ─────────────────────────────────────────────────────────────────

@router.get("/containers/", response_model=List[ContainerRead])
async def list_containers(
    shipment_id: Optional[uuid.UUID] = None,
    status: Optional[ContainerStatus] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("logistics", "view")),
):
    containers = await crud.list_containers(db, shipment_id=shipment_id, status=status)
    return [_c_read(c) for c in containers]


@router.post("/containers/", response_model=ContainerRead, status_code=status.HTTP_201_CREATED)
async def create_container(
    body: ContainerCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("logistics", "create")),
):
    data = body.model_dump()
    data["shipment_id"] = uuid.UUID(data["shipment_id"])
    if await db.get(InternationalShipment, data["shipment_id"]) is None:
        raise HTTPException(status_code=404, detail="Shipment not found")
    c = await crud.create_container(db, data)
    await db.commit()
    c = await crud.get_container(db, c.id)
    return _c_read(c)


@router.patch("/containers/{container_id}", response_model=ContainerRead)
async def update_container(
    container_id: uuid.UUID,
    body: ContainerUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("logistics", "edit")),
):
    c = await crud.get_container(db, container_id)
    if not c:
        raise HTTPException(status_code=404, detail="Container not found")
    c = await crud.update_container(db, c, body.model_dump(exclude_none=True))
    await db.commit()
    c = await crud.get_container(db, container_id)
    return _c_read(c)


# ── PO Links ───────────────────────────────────────────────────────────────────

@router.get("/shipments/{shipment_id}/po-links", response_model=List[POLinkRead])
async def list_po_links(
    shipment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("logistics", "view")),
):
    links = await crud.list_po_links(db, shipment_id)
    return [_link_read(lk) for lk in links]


@router.post("/shipments/{shipment_id}/po-links", response_model=POLinkRead, status_code=status.HTTP_201_CREATED)
async def add_po_link(
    shipment_id: uuid.UUID,
    body: POLinkCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("logistics", "create")),
):
    shipment = await db.get(InternationalShipment, shipment_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail="Shipment not found")
    po = await db.get(PurchaseOrder, body.po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if po.status not in {POStatus.APPROVED, POStatus.ORDERED, POStatus.PARTIALLY_RECEIVED}:
        raise HTTPException(status_code=409, detail="Purchase order must be approved or open before shipment linkage")
    if await crud.get_po_link(db, shipment_id, body.po_id):
        raise HTTPException(status_code=409, detail="Purchase order is already linked to this shipment")
    try:
        link = await crud.add_po_link(db, shipment_id, body.po_id, body.notes)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Purchase order is already linked to this shipment")
    links = await crud.list_po_links(db, shipment_id)
    fresh = next((lk for lk in links if lk.id == link.id), link)
    return _link_read(fresh)


@router.delete("/po-links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_po_link(
    link_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("logistics", "edit")),
):
    try:
        await crud.remove_po_link(db, link_id)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="A PO link with ownership history cannot be removed")


@router.get(
    "/shipments/{shipment_id}/po-links/{link_id}/ownership-events",
    response_model=List[ShipmentOwnershipEventRead],
)
async def list_shipment_ownership_events(
    shipment_id: uuid.UUID,
    link_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("logistics", "view")),
):
    link = await crud.get_po_link_by_id(db, link_id)
    if link is None or link.shipment_id != shipment_id:
        raise HTTPException(status_code=404, detail="Shipment purchase-order link not found")
    events = await crud.list_ownership_events(db, link_id)
    return [_ownership_event_read(event) for event in events]


@router.post(
    "/shipments/{shipment_id}/po-links/{link_id}/ownership",
    response_model=ShipmentOwnershipEventRead,
    status_code=status.HTTP_201_CREATED,
)
async def record_shipment_inventory_ownership(
    shipment_id: uuid.UUID,
    link_id: uuid.UUID,
    body: ShipmentOwnershipUpdate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("logistics", "edit")),
):
    link = await crud.get_po_link_by_id(db, link_id, for_update=True)
    if link is None or link.shipment_id != shipment_id:
        raise HTTPException(status_code=404, detail="Shipment purchase-order link not found")
    shipment = await crud.get_shipment_for_update(db, shipment_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail="Shipment not found")
    if shipment.status not in {
        IntlShipmentStatus.CARGO_LOADED,
        IntlShipmentStatus.IN_TRANSIT,
        IntlShipmentStatus.ARRIVED_PORT,
        IntlShipmentStatus.CUSTOMS_HOLD,
        IntlShipmentStatus.CUSTOMS_CLEARED,
        IntlShipmentStatus.OUT_FOR_DELIVERY,
    }:
        raise HTTPException(status_code=409, detail="Ownership can be recorded only after cargo is loaded and before delivery")
    if body.new_owner == InventoryOwnerStatus.UNCONFIRMED:
        raise HTTPException(status_code=422, detail="Select a confirmed owner; UNCONFIRMED is recorded until evidence is supplied")
    source_reference = body.source_reference.strip()
    if not source_reference:
        raise HTTPException(status_code=422, detail="A contract or shipping-document reference is required")
    if link.inventory_owner_status == body.new_owner.value:
        raise HTTPException(status_code=409, detail="The recorded owner is already current")

    event = ShipmentOwnershipEvent(
        shipment_po_link_id=link.id,
        previous_owner=link.inventory_owner_status,
        new_owner=body.new_owner.value,
        source_reference=source_reference,
        notes=body.notes.strip() if body.notes and body.notes.strip() else None,
        effective_at=datetime.now(timezone.utc),
        changed_by_id=actor.id,
    )
    link.inventory_owner_status = body.new_owner.value
    db.add(event)
    await db.commit()
    await db.refresh(event)
    event = await crud.list_ownership_events(db, link.id)
    return _ownership_event_read(event[-1])


# ── Customs Documents ──────────────────────────────────────────────────────────

@router.get("/shipments/{shipment_id}/documents", response_model=List[CustomsDocRead])
async def list_customs_docs(
    shipment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    docs = await crud.list_customs_docs(db, shipment_id)
    return [_doc_read(d) for d in docs]


@router.post("/documents/", response_model=CustomsDocRead, status_code=status.HTTP_201_CREATED)
async def create_customs_doc(
    body: CustomsDocCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    data = body.model_dump()
    data["shipment_id"] = uuid.UUID(data["shipment_id"])
    doc = await crud.create_customs_doc(db, data)
    await db.commit()
    return _doc_read(doc)


@router.patch("/documents/{doc_id}", response_model=CustomsDocRead)
async def update_customs_doc(
    doc_id: uuid.UUID,
    body: CustomsDocUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    doc = await crud.get_customs_doc(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    doc = await crud.update_customs_doc(db, doc, body.model_dump(exclude_none=True))
    await db.commit()
    return _doc_read(doc)


# ── Customs Clearance ──────────────────────────────────────────────────────────

@router.get("/shipments/{shipment_id}/clearance", response_model=ClearanceRead)
async def get_clearance(
    shipment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("logistics", "view")),
):
    cl = await crud.get_clearance(db, shipment_id)
    if not cl:
        raise HTTPException(status_code=404, detail="No clearance record")
    return _cl_read(cl)


@router.post("/clearance/", response_model=ClearanceRead, status_code=status.HTTP_201_CREATED)
async def create_clearance(
    body: ClearanceCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("logistics", "create")),
):
    data = body.model_dump()
    data["shipment_id"] = uuid.UUID(data["shipment_id"])
    cl = await crud.create_clearance(db, data)
    await db.commit()
    return _cl_read(cl)


@router.patch("/clearance/{clearance_id}", response_model=ClearanceRead)
async def update_clearance(
    clearance_id: uuid.UUID,
    body: ClearanceUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("logistics", "edit")),
):
    cl = await crud.get_clearance_for_update(db, clearance_id)
    if not cl:
        raise HTTPException(status_code=404, detail="Clearance not found")
    cl = await crud.update_clearance(db, cl, body.model_dump(exclude_none=True))
    await db.commit()
    return _cl_read(cl)


def _clearance_milestone_read(event: CustomsClearanceMilestone) -> ClearanceMilestoneRead:
    actor_name = None
    if event.changed_by is not None:
        actor_name = getattr(event.changed_by, "full_name", None)
        if not actor_name:
            actor_name = " ".join(
                part for part in (
                    getattr(event.changed_by, "first_name", None),
                    getattr(event.changed_by, "last_name", None),
                ) if part
            ) or getattr(event.changed_by, "username", None)
    return ClearanceMilestoneRead(
        id=str(event.id),
        clearance_id=str(event.clearance_id),
        previous_status=event.previous_status,
        new_status=event.new_status,
        source_reference=event.source_reference,
        notes=event.notes,
        effective_at=event.effective_at,
        changed_by_id=str(event.changed_by_id),
        changed_by_name=actor_name,
        created_at=event.created_at,
    )


@router.get(
    "/shipments/{shipment_id}/clearance/milestones",
    response_model=List[ClearanceMilestoneRead],
)
async def list_clearance_milestones(
    shipment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("logistics", "view")),
):
    clearance = await crud.get_clearance(db, shipment_id)
    if clearance is None:
        raise HTTPException(status_code=404, detail="Clearance record not found")
    milestones = await crud.list_clearance_milestones(db, clearance.id)
    return [_clearance_milestone_read(event) for event in milestones]


@router.post(
    "/shipments/{shipment_id}/clearance/milestones",
    response_model=ClearanceMilestoneRead,
    status_code=status.HTTP_201_CREATED,
)
async def record_clearance_milestone(
    shipment_id: uuid.UUID,
    body: ClearanceMilestoneCreate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("logistics", "edit")),
):
    clearance = await crud.get_clearance(db, shipment_id)
    if clearance is None:
        raise HTTPException(status_code=404, detail="Clearance record not found")
    clearance = await crud.get_clearance_for_update(db, clearance.id)
    shipment = await crud.get_shipment_for_update(db, shipment_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail="Shipment not found")
    if shipment.status not in {IntlShipmentStatus.ARRIVED_PORT, IntlShipmentStatus.CUSTOMS_HOLD}:
        raise HTTPException(status_code=409, detail="Customs milestones can be recorded only after port arrival and before warehouse delivery")

    previous = clearance.status
    if body.new_status not in CLEARANCE_STATUS_TRANSITIONS.get(previous, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Clearance status cannot move from {previous.value} to {body.new_status.value}",
        )
    if body.new_status == ClearanceStatus.HELD and not (body.notes and body.notes.strip()):
        raise HTTPException(status_code=422, detail="A hold reason is required when recording HELD")
    source_reference = body.source_reference.strip()
    if not source_reference:
        raise HTTPException(status_code=422, detail="A supporting customs or shipment reference is required")

    occurred_at = datetime.now(timezone.utc)
    event = CustomsClearanceMilestone(
        clearance_id=clearance.id,
        previous_status=previous.value,
        new_status=body.new_status.value,
        source_reference=source_reference,
        notes=body.notes.strip() if body.notes and body.notes.strip() else None,
        effective_at=occurred_at,
        changed_by_id=actor.id,
    )
    clearance.status = body.new_status
    if body.new_status == ClearanceStatus.DOCS_SUBMITTED:
        clearance.submission_date = occurred_at.date()
    elif body.new_status == ClearanceStatus.EXAM_REQUESTED:
        clearance.examination_date = occurred_at.date()
    elif body.new_status == ClearanceStatus.CLEARED:
        clearance.clearance_date = occurred_at.date()
        arrival = await crud.get_arrival(db, shipment_id)
        if arrival is not None:
            arrival.customs_clearance_date = occurred_at.date()
        shipment.status = IntlShipmentStatus.CUSTOMS_CLEARED
    elif body.new_status == ClearanceStatus.HELD:
        shipment.status = IntlShipmentStatus.CUSTOMS_HOLD

    db.add(event)
    await db.flush()
    event_id = event.id
    await db.commit()
    event = await crud.get_clearance_milestone(db, event_id)
    if event is None:
        raise HTTPException(status_code=500, detail="Recorded customs milestone could not be reloaded")
    return _clearance_milestone_read(event)


# ── Arrival Notifications ──────────────────────────────────────────────────────

@router.get("/arrivals/", response_model=List[ArrivalRead])
async def list_arrivals(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    arrivals = await crud.list_arrivals(db)
    return [_arr_read(a) for a in arrivals]


@router.get("/arrivals/alerts", response_model=List[ShipmentRead])
async def eta_alerts(
    days_ahead: int = 14,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    ships = await svc.get_eta_alerts(db, days_ahead=days_ahead)
    return [_s_read(s) for s in ships]


@router.get("/shipments/{shipment_id}/arrival", response_model=ArrivalRead)
async def get_arrival(
    shipment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    arr = await crud.get_arrival(db, shipment_id)
    if not arr:
        raise HTTPException(status_code=404, detail="Arrival record not found")
    return _arr_read(arr)


@router.patch("/shipments/{shipment_id}/arrival", response_model=ArrivalRead)
async def update_arrival(
    shipment_id: uuid.UUID,
    body: ArrivalUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    arr = await crud.get_arrival(db, shipment_id)
    if not arr:
        raise HTTPException(status_code=404, detail="Arrival record not found")
    data = body.model_dump(exclude_none=True)
    if data.get("grn_id"):
        data["grn_id"] = uuid.UUID(data["grn_id"])
    arr = await crud.update_arrival(db, arr, data)
    await db.commit()
    return _arr_read(arr)


# ── Local Logistics Costs ──────────────────────────────────────────────────────

def _cost_read(c) -> LocalCostRead:
    return LocalCostRead(
        id=str(c.id),
        shipment_id=str(c.shipment_id),
        cost_type=c.cost_type,
        description=c.description,
        vendor_name=c.vendor_name,
        amount_kes=float(c.amount_kes),
        payment_method=c.payment_method,
        payment_status=c.payment_status,
        paid_date=c.paid_date,
        mpesa_reference=c.mpesa_reference,
        mpesa_phone=c.mpesa_phone,
        notes=c.notes,
        created_at=c.created_at,
    )


@router.get("/shipments/{shipment_id}/local-costs", response_model=LocalCostSummary)
async def list_local_costs(
    shipment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    costs = await crud.list_local_costs(db, shipment_id)
    rows = [_cost_read(c) for c in costs]
    total = sum(r.amount_kes for r in rows)
    paid = sum(r.amount_kes for r in rows if r.payment_status.value == "PAID")
    return LocalCostSummary(
        shipment_id=str(shipment_id),
        total_kes=round(total, 2),
        paid_kes=round(paid, 2),
        pending_kes=round(total - paid, 2),
        by_type=rows,
    )


@router.post("/shipments/{shipment_id}/local-costs", response_model=LocalCostRead, status_code=status.HTTP_201_CREATED)
async def create_local_cost(
    shipment_id: uuid.UUID,
    body: LocalCostCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = body.model_dump(exclude={"shipment_id"})
    data["shipment_id"] = shipment_id
    cost = await crud.create_local_cost(db, data, current_user.id)
    await db.commit()
    return _cost_read(cost)


@router.patch("/local-costs/{cost_id}", response_model=LocalCostRead)
async def update_local_cost(
    cost_id: uuid.UUID,
    body: LocalCostUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    cost = await crud.get_local_cost(db, cost_id)
    if not cost:
        raise HTTPException(status_code=404, detail="Cost record not found")
    cost = await crud.update_local_cost(db, cost, body.model_dump(exclude_none=True))
    await db.commit()
    return _cost_read(cost)


@router.delete("/local-costs/{cost_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_local_cost(
    cost_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    cost = await crud.get_local_cost(db, cost_id)
    if not cost:
        raise HTTPException(status_code=404, detail="Cost record not found")
    await crud.delete_local_cost(db, cost)
    await db.commit()


# ── Dashboard ──────────────────────────────────────────────────────────────────

@router.get("/dashboard/", response_model=List[ShipmentDashboardRow])
async def logistics_dashboard(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await svc.get_dashboard_rows(db)
