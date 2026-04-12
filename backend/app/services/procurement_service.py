"""
Procurement business logic service.

Key operations:
  - approve_pr / reject_pr
  - convert_pr_to_po  (creates PO + POLines from approved PR)
  - approve_po / mark_ordered
  - post_grn  (receives stock via inventory_service.stock_entry / material receipt)
  - update_po_receipt_status  (PARTIALLY_RECEIVED / RECEIVED after GRN post)
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.procurement import (
    PurchaseRequisition, PRLine, PurchaseOrder, POLine,
    GoodsReceipt, GRNLine, PRStatus, POStatus, GRNStatus,
)
from app.models.inventory import Stock, Lot, StockMovement, MovementType, StockType
from app.models.master import Material, Warehouse


# ── Guards ────────────────────────────────────────────────────────────────────

def _assert_pr_status(pr: PurchaseRequisition, *allowed: PRStatus) -> None:
    if pr.status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"PR is {pr.status}; allowed: {[s.value for s in allowed]}",
        )


def _assert_po_status(po: PurchaseOrder, *allowed: POStatus) -> None:
    if po.status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"PO is {po.status}; allowed: {[s.value for s in allowed]}",
        )


# ── PR lifecycle ──────────────────────────────────────────────────────────────

async def approve_pr(
    db: AsyncSession,
    pr: PurchaseRequisition,
    approver_id: uuid.UUID,
) -> PurchaseRequisition:
    _assert_pr_status(pr, PRStatus.PENDING_APPROVAL)
    pr.status = PRStatus.APPROVED
    pr.approved_by_id = approver_id
    pr.approved_at = datetime.now(timezone.utc)
    pr.rejection_reason = None
    await db.flush()
    return pr


async def reject_pr(
    db: AsyncSession,
    pr: PurchaseRequisition,
    approver_id: uuid.UUID,
    reason: str,
) -> PurchaseRequisition:
    _assert_pr_status(pr, PRStatus.PENDING_APPROVAL)
    pr.status = PRStatus.REJECTED
    pr.approved_by_id = approver_id
    pr.approved_at = datetime.now(timezone.utc)
    pr.rejection_reason = reason
    await db.flush()
    return pr


async def submit_pr(db: AsyncSession, pr: PurchaseRequisition) -> PurchaseRequisition:
    _assert_pr_status(pr, PRStatus.DRAFT)
    if not pr.lines:
        raise HTTPException(status_code=422, detail="PR must have at least one line before submission")
    pr.status = PRStatus.PENDING_APPROVAL
    await db.flush()
    return pr


# ── PR → PO conversion ────────────────────────────────────────────────────────

async def convert_pr_to_po(
    db: AsyncSession,
    pr: PurchaseRequisition,
    req: dict,
    created_by_id: uuid.UUID,
) -> PurchaseOrder:
    _assert_pr_status(pr, PRStatus.APPROVED)

    line_prices: dict = req.pop("line_prices") or {}
    po = PurchaseOrder(
        **req,
        pr_id=pr.id,
        created_by_id=created_by_id,
    )
    db.add(po)
    await db.flush()

    for i, pr_line in enumerate(pr.lines, start=1):
        unit_price = Decimal(str(line_prices.get(str(pr_line.id), pr_line.estimated_unit_cost or 0)))
        db.add(POLine(
            po_id=po.id,
            pr_line_id=pr_line.id,
            line_no=i,
            material_id=pr_line.material_id,
            product_id=pr_line.product_id,
            description=pr_line.description,
            ordered_quantity=pr_line.quantity,
            unit=pr_line.unit,
            unit_price=unit_price,
        ))

    pr.status = PRStatus.CONVERTED
    await db.flush()
    await db.refresh(po)
    return po


# ── PO lifecycle ──────────────────────────────────────────────────────────────

async def approve_po(
    db: AsyncSession,
    po: PurchaseOrder,
    approver_id: uuid.UUID,
) -> PurchaseOrder:
    _assert_po_status(po, POStatus.DRAFT)
    po.status = POStatus.APPROVED
    po.approved_by_id = approver_id
    po.approved_at = datetime.now(timezone.utc)
    await db.flush()
    return po


async def mark_ordered(db: AsyncSession, po: PurchaseOrder) -> PurchaseOrder:
    _assert_po_status(po, POStatus.APPROVED)
    po.status = POStatus.ORDERED
    await db.flush()
    return po


async def cancel_po(db: AsyncSession, po: PurchaseOrder) -> PurchaseOrder:
    _assert_po_status(po, POStatus.DRAFT, POStatus.APPROVED, POStatus.ORDERED)
    po.status = POStatus.CANCELLED
    await db.flush()
    return po


# ── GRN / Receipt posting ─────────────────────────────────────────────────────

async def post_grn(
    db: AsyncSession,
    grn: GoodsReceipt,
    user_id: uuid.UUID,
) -> GoodsReceipt:
    if grn.status == GRNStatus.POSTED:
        raise HTTPException(status_code=422, detail="GRN already posted")

    po_result = await db.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.lines))
        .where(PurchaseOrder.id == grn.po_id)
    )
    po = po_result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")

    _assert_po_status(po, POStatus.ORDERED, POStatus.PARTIALLY_RECEIVED)

    # Reload GRN lines with relationships
    grn_result = await db.execute(
        select(GoodsReceipt)
        .options(selectinload(GoodsReceipt.lines))
        .where(GoodsReceipt.id == grn.id)
    )
    grn = grn_result.scalar_one()

    for line in grn.lines:
        if line.accepted_quantity <= 0:
            continue

        item_id = line.material_id or line.product_id
        if not item_id:
            continue

        stock_type = StockType.MATERIAL if line.material_id else StockType.PRODUCT
        qty = Decimal(str(line.accepted_quantity))

        # Create or reuse lot
        lot_id: Optional[uuid.UUID] = None
        if line.lot_number:
            lot_result = await db.execute(
                select(Lot).where(
                    and_(
                        Lot.lot_number == line.lot_number,
                        Lot.material_id == line.material_id if line.material_id else Lot.product_id == line.product_id,
                    )
                )
            )
            lot = lot_result.scalar_one_or_none()
            if not lot:
                lot = Lot(
                    lot_number=line.lot_number,
                    material_id=line.material_id,
                    product_id=line.product_id,
                    expiry_date=line.expiry_date,
                    supplier_id=po.supplier_id,
                )
                db.add(lot)
                await db.flush()
            lot_id = lot.id

        # Stock movement
        movement = StockMovement(
            reference_number=grn.grn_no,
            movement_type=MovementType.RECEIPT,
            stock_type=stock_type,
            movement_date=grn.received_date,
            material_id=line.material_id,
            product_id=line.product_id,
            lot_id=lot_id,
            destination_warehouse_id=grn.warehouse_id,
            quantity=qty,
            notes=f"GRN receipt against PO {po.po_no}",
            created_by_id=user_id,
        )
        db.add(movement)
        await db.flush()
        line.stock_movement_id = movement.id

        # Upsert stock row
        filters = [
            Stock.warehouse_id == grn.warehouse_id,
            Stock.stock_type == stock_type,
        ]
        if line.material_id:
            filters.append(Stock.material_id == line.material_id)
        else:
            filters.append(Stock.product_id == line.product_id)
        filters.append(Stock.lot_id == lot_id if lot_id else Stock.lot_id.is_(None))

        stock_result = await db.execute(
            select(Stock).where(and_(*filters)).with_for_update()
        )
        stock = stock_result.scalar_one_or_none()
        if stock:
            stock.quantity_on_hand += qty
            stock.quantity_available = stock.quantity_on_hand - stock.quantity_reserved
        else:
            db.add(Stock(
                stock_type=stock_type,
                warehouse_id=grn.warehouse_id,
                material_id=line.material_id,
                product_id=line.product_id,
                lot_id=lot_id,
                quantity_on_hand=qty,
                quantity_reserved=Decimal("0"),
                quantity_available=qty,
            ))

        # Update PO line received_quantity
        if line.po_line_id:
            po_line_result = await db.execute(
                select(POLine).where(POLine.id == line.po_line_id).with_for_update()
            )
            po_line = po_line_result.scalar_one_or_none()
            if po_line:
                po_line.received_quantity += qty

    # Update GRN status
    grn.status = GRNStatus.POSTED

    # Reload PO lines to determine new PO status
    await db.flush()
    po_lines_result = await db.execute(
        select(POLine).where(POLine.po_id == po.id)
    )
    po_lines = list(po_lines_result.scalars().all())
    fully_received = all(
        line.received_quantity >= line.ordered_quantity for line in po_lines
    )
    any_received = any(line.received_quantity > 0 for line in po_lines)
    if fully_received:
        po.status = POStatus.RECEIVED
    elif any_received:
        po.status = POStatus.PARTIALLY_RECEIVED

    await db.flush()
    return grn


# ── Delivery Planning ─────────────────────────────────────────────────────────

async def get_inbound_schedule(
    db: AsyncSession,
    days_ahead: int = 30,
) -> list:
    from datetime import timedelta
    from app.models.procurement import ImportShipment
    today = date.today()
    cutoff = today + timedelta(days=days_ahead)

    result = await db.execute(
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.supplier),
            selectinload(PurchaseOrder.import_shipment),
        )
        .where(
            PurchaseOrder.status.in_([
                POStatus.ORDERED, POStatus.PARTIALLY_RECEIVED
            ]),
            PurchaseOrder.expected_delivery_date <= cutoff,
        )
        .order_by(PurchaseOrder.expected_delivery_date)
    )
    pos = result.scalars().all()

    from app.schemas.procurement import InboundScheduleRow
    rows = []
    for po in pos:
        days_delta = (po.expected_delivery_date - today).days
        total_val = sum(
            (l.ordered_quantity * l.unit_price) for l in po.lines
        ) if po.lines else None
        rows.append(InboundScheduleRow(
            po_id=po.id,
            po_no=po.po_no,
            supplier_name=po.supplier.name if po.supplier else "—",
            expected_delivery_date=po.expected_delivery_date,
            days_until_delivery=days_delta,
            status=po.status,
            total_value=total_val,
            is_overdue=days_delta < 0,
            has_shipment=po.import_shipment is not None,
            shipment_eta=po.import_shipment.eta if po.import_shipment else None,
        ))
    return rows


async def get_delivery_alerts(db: AsyncSession) -> list:
    from datetime import timedelta
    from app.schemas.procurement import DeliveryAlertRow
    today = date.today()

    result = await db.execute(
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.supplier),
            selectinload(PurchaseOrder.import_shipment),
        )
        .where(
            PurchaseOrder.status.in_([
                POStatus.ORDERED, POStatus.PARTIALLY_RECEIVED
            ])
        )
    )
    pos = result.scalars().all()

    alerts = []
    for po in pos:
        days_delta = (po.expected_delivery_date - today).days
        supplier_name = po.supplier.name if po.supplier else "—"

        if days_delta < 0:
            alerts.append(DeliveryAlertRow(
                alert_type="OVERDUE",
                po_id=po.id,
                po_no=po.po_no,
                supplier_name=supplier_name,
                expected_delivery_date=po.expected_delivery_date,
                days_delta=days_delta,
                message=f"PO {po.po_no} is {abs(days_delta)} day(s) overdue",
            ))
        elif days_delta <= 7:
            alerts.append(DeliveryAlertRow(
                alert_type="APPROACHING",
                po_id=po.id,
                po_no=po.po_no,
                supplier_name=supplier_name,
                expected_delivery_date=po.expected_delivery_date,
                days_delta=days_delta,
                message=f"PO {po.po_no} arriving in {days_delta} day(s)",
            ))

        if po.import_shipment is None and days_delta <= 14:
            alerts.append(DeliveryAlertRow(
                alert_type="NO_SHIPMENT",
                po_id=po.id,
                po_no=po.po_no,
                supplier_name=supplier_name,
                expected_delivery_date=po.expected_delivery_date,
                days_delta=days_delta,
                message=f"PO {po.po_no} has no import shipment linked",
            ))

    alerts.sort(key=lambda a: a.days_delta)
    return alerts
