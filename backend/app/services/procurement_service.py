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

from app.core.access_control import (
    can_modify_record,
    can_view_record,
    forbidden_detail,
)
from app.models.procurement import (
    PurchaseRequisition, PRLine, PurchaseOrder, POLine,
    GoodsReceipt, GRNLine, PRStatus, POStatus, GRNStatus,
    ProcurementApprovalDocumentType, ProcurementApprovalRule,
)
from app.models.inventory import Stock, Lot, StockMovement, MovementType, StockType
from app.models.master import Material, Warehouse
from app.schemas.procurement import ProcurementAccessHint


PROCUREMENT_SCOPE_FIELDS = ("company_id", "branch_id", "cost_center_id", "department")


PROCUREMENT_ACTION_STATUSES: dict[str, dict[str, set[str]]] = {
    "pr": {
        "edit": {PRStatus.DRAFT.value},
        "submit": {PRStatus.DRAFT.value},
        "approve": {PRStatus.PENDING_APPROVAL.value},
        "convert": {PRStatus.APPROVED.value},
        "cancel": {PRStatus.DRAFT.value, PRStatus.PENDING_APPROVAL.value},
    },
    "po": {
        "edit": {POStatus.DRAFT.value},
        "approve": {POStatus.DRAFT.value},
        "order": {POStatus.APPROVED.value},
        "receive": {POStatus.ORDERED.value, POStatus.PARTIALLY_RECEIVED.value},
        "cancel": {POStatus.DRAFT.value, POStatus.APPROVED.value, POStatus.ORDERED.value},
    },
    "grn": {
        "edit": {GRNStatus.DRAFT.value},
        "receive": {GRNStatus.DRAFT.value},
        "post": {GRNStatus.DRAFT.value},
        "cancel": {GRNStatus.DRAFT.value},
    },
}


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

def _status_value(record) -> str | None:
    status_value = getattr(record, "status", None)
    if status_value is None:
        return None
    return str(getattr(status_value, "value", status_value))


def procurement_document_key(record) -> str:
    if isinstance(record, PurchaseRequisition):
        return "pr"
    if isinstance(record, PurchaseOrder):
        return "po"
    if isinstance(record, GoodsReceipt):
        return "grn"
    name = record.__class__.__name__.lower()
    if "requisition" in name:
        return "pr"
    if "order" in name:
        return "po"
    if "receipt" in name or "grn" in name:
        return "grn"
    return name


def inherit_procurement_scope(target, source, overwrite: bool = False) -> None:
    for field_name in PROCUREMENT_SCOPE_FIELDS:
        if not hasattr(target, field_name) or not hasattr(source, field_name):
            continue
        if overwrite or getattr(target, field_name, None) is None:
            setattr(target, field_name, getattr(source, field_name, None))


def can_change_procurement_status(record, action: str) -> bool:
    document_key = procurement_document_key(record)
    allowed_statuses = PROCUREMENT_ACTION_STATUSES.get(document_key, {}).get(action)
    if not allowed_statuses:
        return True
    return _status_value(record) in allowed_statuses


def build_procurement_access_hint(user, record) -> ProcurementAccessHint:
    can_view = can_view_record(user, "procurement", record)
    actions = {
        "can_create": can_modify_record(user, "procurement", "create", record),
        "can_edit": can_change_procurement_status(record, "edit") and can_modify_record(user, "procurement", "edit", record),
        "can_delete": can_change_procurement_status(record, "delete") and can_modify_record(user, "procurement", "delete", record),
        "can_approve": can_change_procurement_status(record, "approve") and can_modify_record(user, "procurement", "approve", record),
        "can_receive": can_change_procurement_status(record, "receive") and can_modify_record(user, "procurement", "receive", record),
        "can_post": can_change_procurement_status(record, "post") and can_modify_record(user, "procurement", "post", record),
        "can_cancel": can_change_procurement_status(record, "cancel") and can_modify_record(user, "procurement", "cancel", record),
        "can_export": can_modify_record(user, "procurement", "export", record),
        "can_import": can_modify_record(user, "procurement", "import", record),
    }
    mutation_allowed = any(actions.values())
    reason = None
    if can_view and not mutation_allowed:
        reason = "You can view this procurement record but cannot modify it in this scope or status."
    return ProcurementAccessHint(
        can_view=can_view,
        view_only=can_view and not mutation_allowed,
        reason=reason,
        **actions,
    )


def ensure_procurement_action_allowed(user, record, action: str) -> None:
    if not can_change_procurement_status(record, action):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Procurement record status does not allow {action}.",
        )
    allowed = can_view_record(user, "procurement", record) if action == "view" else can_modify_record(user, "procurement", action, record)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=forbidden_detail("You can view this procurement record only if your permissions and scopes allow it."),
        )


def procurement_document_amount(record) -> Decimal | None:
    lines = getattr(record, "lines", None)
    if not lines:
        return None
    total = Decimal("0")
    has_amount = False
    for line in lines:
        quantity = getattr(line, "ordered_quantity", None) or getattr(line, "quantity", None)
        unit_price = getattr(line, "unit_price", None) or getattr(line, "estimated_unit_cost", None)
        if quantity is None or unit_price is None:
            continue
        total += Decimal(str(quantity)) * Decimal(str(unit_price))
        has_amount = True
    return total if has_amount else None


async def find_procurement_approval_rules(
    db: AsyncSession,
    document_type: ProcurementApprovalDocumentType,
    record,
    amount: Decimal | None = None,
) -> list[ProcurementApprovalRule]:
    today = date.today()
    amount_value = amount if amount is not None else procurement_document_amount(record)

    filters = [
        ProcurementApprovalRule.document_type == document_type,
        ProcurementApprovalRule.is_active.is_(True),
        (ProcurementApprovalRule.effective_from.is_(None) | (ProcurementApprovalRule.effective_from <= today)),
        (ProcurementApprovalRule.effective_to.is_(None) | (ProcurementApprovalRule.effective_to >= today)),
    ]
    for field_name in PROCUREMENT_SCOPE_FIELDS:
        value = getattr(record, field_name, None)
        if value is not None:
            rule_field = getattr(ProcurementApprovalRule, field_name)
            filters.append(rule_field.is_(None) | (rule_field == value))
    if amount_value is not None:
        filters.append(ProcurementApprovalRule.min_amount.is_(None) | (ProcurementApprovalRule.min_amount <= amount_value))
        filters.append(ProcurementApprovalRule.max_amount.is_(None) | (ProcurementApprovalRule.max_amount >= amount_value))

    result = await db.execute(
        select(ProcurementApprovalRule)
        .where(*filters)
        .order_by(ProcurementApprovalRule.approval_level, ProcurementApprovalRule.rule_name)
    )
    return list(result.scalars().all())


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
    inherit_procurement_scope(po, pr)
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
