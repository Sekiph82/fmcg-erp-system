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
from app.models.master import Material, Product, Warehouse
from app.schemas.procurement import ProcurementAccessHint
from app.services.inventory_locking import lot_identity, lock_inventory_identity, stock_identity


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
    # Serialize receipt posting by the owning PO before locking the GRN. This
    # also orders different partial receipts against the same PO consistently.
    po_result = await db.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.lines))
        .where(PurchaseOrder.id == grn.po_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    po = po_result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")

    _assert_po_status(po, POStatus.ORDERED, POStatus.PARTIALLY_RECEIVED)

    # Refresh and lock the source receipt before checking its transition. The
    # endpoint may have loaded a stale draft object before another post commits.
    grn_result = await db.execute(
        select(GoodsReceipt)
        .options(selectinload(GoodsReceipt.lines))
        .where(GoodsReceipt.id == grn.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    grn = grn_result.scalar_one_or_none()
    if not grn:
        raise HTTPException(status_code=404, detail="GRN not found")
    if grn.status == GRNStatus.POSTED:
        raise HTTPException(status_code=422, detail="GRN already posted")

    # The gate scope lock shares its transaction boundary with configuration writes,
    # so a concurrently activated receipt gate cannot be skipped during posting.
    from app.services.qms_service import (
        RECEIVING_GATE_TARGET_MODULE,
        RECEIVING_GATE_TRIGGER_EVENT,
        ensure_receiving_quality_gates_pass,
        lock_quality_gate_scope,
    )

    await lock_quality_gate_scope(db, RECEIVING_GATE_TARGET_MODULE, RECEIVING_GATE_TRIGGER_EVENT)
    try:
        await ensure_receiving_quality_gates_pass(db, grn, actor_id=user_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

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
            await lock_inventory_identity(db, lot_identity(
                lot_number=line.lot_number,
                product_id=line.product_id,
                material_id=line.material_id,
            ))
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

        await lock_inventory_identity(db, stock_identity(
            stock_type=stock_type,
            warehouse_id=grn.warehouse_id,
            product_id=line.product_id,
            material_id=line.material_id,
            lot_id=lot_id,
        ))

        stock_result = await db.execute(
            select(Stock)
            .where(and_(*filters))
            .with_for_update()
            .execution_options(populate_existing=True)
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
                select(POLine)
                .where(POLine.id == line.po_line_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            po_line = po_line_result.scalar_one_or_none()
            if po_line:
                po_line.received_quantity += qty

    # Update GRN status
    grn.status = GRNStatus.POSTED

    # Reload PO lines to determine new PO status
    await db.flush()
    po_lines_result = await db.execute(
        select(POLine)
        .where(POLine.po_id == po.id)
        .execution_options(populate_existing=True)
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
    if any(
        Decimal(str(line.accepted_quantity)) > 0
        and bool(line.material_id or line.product_id)
        for line in grn.lines
    ):
        # Keep the physical receipt, cost layer, and GL posting atomic so new
        # stock cannot be consumed before it has a carrying value.
        await post_grn_inventory_valuation(db, grn.id, user_id)
    await db.flush()
    return grn


async def post_grn_inventory_valuation(
    db: AsyncSession,
    grn_id: uuid.UUID,
    user_id: uuid.UUID,
) -> dict:
    """Post a previously received GRN to inventory valuation and the GL.

    Receipt/stock posting remains an operations permission. This separate
    finance.post action applies the configured item valuation method and
    inventory/GRNI mappings atomically, with one idempotent posting event per
    GRN line. No account codes or production account IDs are inferred here.
    """
    from datetime import datetime, timezone
    from decimal import ROUND_HALF_UP

    from app.models.finance import (
        AccountType,
        AccountingPostingBatch,
        ChartOfAccount,
        JournalEntry,
        JournalLine,
        JournalStatus,
        OperationalPostingEvent,
        OperationalPostingStatus,
    )
    from app.models.company import Company
    from app.models.inventory import CostLayer
    from app.services.finance_service import (
        apply_operational_posting_link,
        assert_journal_lines_postable,
        find_inventory_account_mapping,
        get_or_create_operational_posting_event,
        mark_journal_posted,
        mark_operational_posting_posted,
    )

    money_quantum = Decimal("0.0001")
    # Use the same 4-decimal monetary unit scale persisted by StockMovement so
    # inventory layers, movement totals, and GL lines reconcile exactly.
    unit_quantum = money_quantum

    try:
        # Keep the global receipt lock order identical to post_grn (PO -> GRN).
        po_id = await db.scalar(select(GoodsReceipt.po_id).where(GoodsReceipt.id == grn_id))
        if not po_id:
            raise ValueError("GRN not found")
        po_result = await db.execute(
            select(PurchaseOrder)
            .where(PurchaseOrder.id == po_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        po = po_result.scalar_one_or_none()
        if not po:
            raise ValueError("GRN purchase order not found")

        grn_result = await db.execute(
            select(GoodsReceipt)
            .where(GoodsReceipt.id == grn_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        grn = grn_result.scalar_one_or_none()
        if not grn:
            raise ValueError("GRN not found")
        if grn.po_id != po.id:
            raise ValueError("GRN purchase order changed during valuation")
        if grn.status != GRNStatus.POSTED:
            raise ValueError("Inventory valuation can only be posted for a posted GRN")
        if grn.company_id and po.company_id and grn.company_id != po.company_id:
            raise ValueError("GRN and purchase order belong to different companies")
        company_id = grn.company_id or po.company_id
        company = await db.get(Company, company_id) if company_id else None
        if not company or not company.base_currency:
            raise ValueError("GRN needs a company with a configured base currency")
        warehouse = await db.get(Warehouse, grn.warehouse_id)
        if warehouse and warehouse.company_id and warehouse.company_id != company.id:
            raise ValueError("GRN warehouse belongs to a different company")
        po_currency = (po.currency or "").strip().upper()
        base_currency = company.base_currency.strip().upper()
        exchange_rate = Decimal("1") if po_currency == base_currency else Decimal(str(po.exchange_rate or 0))
        if not exchange_rate.is_finite() or exchange_rate <= 0:
            raise ValueError("Purchase order needs a positive saved exchange rate")
        if po_currency != base_currency and exchange_rate == Decimal("1"):
            raise ValueError("Foreign-currency purchase order needs a non-default saved exchange rate before valuation")

        line_result = await db.execute(
            select(GRNLine)
            .where(GRNLine.grn_id == grn.id)
            .order_by(GRNLine.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        lines = list(line_result.scalars().all())
        valuated_lines = [line for line in lines if Decimal(str(line.accepted_quantity)) > 0]
        if not valuated_lines:
            raise ValueError("GRN has no accepted inventory lines to value")

        for line in valuated_lines:
            if bool(line.material_id) == bool(line.product_id):
                raise ValueError(f"Accepted GRN line {line.id} must reference exactly one product or material")

        # An old partial posting is ambiguous and must be reconciled manually;
        # a fully posted retry is safe and has no second valuation or journal.
        statuses = {line.accounting_status for line in valuated_lines}
        if statuses == {OperationalPostingStatus.POSTED}:
            for line in valuated_lines:
                event_result = await db.execute(select(OperationalPostingEvent).where(
                    OperationalPostingEvent.source_module == "procurement",
                    OperationalPostingEvent.source_event == "GRN_INVENTORY_VALUATION_POSTED",
                    OperationalPostingEvent.source_id == str(grn.id),
                    OperationalPostingEvent.source_line_id == str(line.id),
                ))
                event = event_result.scalar_one_or_none()
                batch = await db.get(AccountingPostingBatch, line.posting_batch_id) if line.posting_batch_id else None
                journal = await db.get(JournalEntry, line.journal_entry_id) if line.journal_entry_id else None
                movement = await db.get(StockMovement, line.stock_movement_id) if line.stock_movement_id else None
                if (
                    not event or event.status != OperationalPostingStatus.POSTED
                    or not batch or batch.status.value != "POSTED"
                    or not journal or not journal.is_posted or journal.status != JournalStatus.POSTED
                    or not movement or movement.accounting_status != OperationalPostingStatus.POSTED
                    or event.stock_movement_id != movement.id
                    or event.posting_batch_id != batch.id or batch.journal_entry_id != journal.id
                    or event.journal_entry_id != journal.id
                    or movement.posting_batch_id != batch.id or movement.journal_entry_id != journal.id
                    or journal.posting_batch_id != batch.id
                    or journal.source_module != "procurement"
                    or journal.source_event != "GRN_INVENTORY_VALUATION_POSTED"
                    or journal.source_id != line.id
                ):
                    raise ValueError(f"GRN line {line.id} has inconsistent posted valuation links; manual reconciliation is required")
            return {
                "grn_id": grn.id,
                "status": OperationalPostingStatus.POSTED.value,
                "posted_lines": len(valuated_lines),
                "idempotent_replay": True,
            }
        if any(status is not None for status in statuses):
            raise ValueError("GRN has a partial or failed valuation posting; manual reconciliation is required")

        posted_lines = 0
        for line in valuated_lines:
            if not line.stock_movement_id:
                raise ValueError(f"Accepted GRN line {line.id} has no stock movement")
            if not line.po_line_id:
                raise ValueError(f"Accepted GRN line {line.id} has no purchase-order line price")
            po_line = await db.get(POLine, line.po_line_id)
            if (
                not po_line
                or po_line.po_id != po.id
                or po_line.material_id != line.material_id
                or po_line.product_id != line.product_id
            ):
                raise ValueError(f"GRN line {line.id} does not match its purchase-order item")

            movement_result = await db.execute(
                select(StockMovement)
                .where(StockMovement.id == line.stock_movement_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            movement = movement_result.scalar_one_or_none()
            if (
                not movement
                or movement.movement_type != MovementType.RECEIPT
                or movement.stock_type != (StockType.MATERIAL if line.material_id else StockType.PRODUCT)
                or movement.material_id != line.material_id
                or movement.product_id != line.product_id
                or movement.destination_warehouse_id != grn.warehouse_id
                or movement.quantity != line.accepted_quantity
                or movement.reference_number != grn.grn_no
            ):
                raise ValueError(f"GRN line {line.id} does not resolve to its accepted receipt movement")

            later_outbound = await db.scalar(
                select(StockMovement.id)
                .where(
                    StockMovement.id != movement.id,
                    StockMovement.stock_type == movement.stock_type,
                    StockMovement.material_id == line.material_id,
                    StockMovement.product_id == line.product_id,
                    StockMovement.source_warehouse_id == grn.warehouse_id,
                    StockMovement.movement_type.in_((
                        MovementType.ISSUE, MovementType.TRANSFER,
                        MovementType.ADJUSTMENT, MovementType.WRITE_OFF,
                    )),
                    StockMovement.created_at > movement.created_at,
                )
                .limit(1)
            )
            if later_outbound:
                raise ValueError(
                    f"GRN line {line.id} has outbound stock movements after its unvalued receipt; "
                    "manual inventory and accounting reconciliation is required"
                )

            stock_type = "MATERIAL" if line.material_id else "PRODUCT"
            mapping = await find_inventory_account_mapping(
                db,
                stock_type=stock_type,
                material_id=line.material_id,
                product_id=line.product_id,
            )
            if not mapping or not mapping.inventory_account_id or not mapping.grni_account_id:
                raise ValueError(f"GRN item on line {line.id} needs active inventory and GRNI account mappings")
            method = (mapping.valuation_method or "").strip().upper()
            if method not in {"FIFO", "WEIGHTED_AVG", "STANDARD"}:
                raise ValueError(f"GRN item on line {line.id} needs FIFO, WEIGHTED_AVG, or STANDARD valuation mapping")

            price = Decimal(str(po_line.unit_price))
            quantity = Decimal(str(line.accepted_quantity))
            if not price.is_finite() or price <= 0:
                raise ValueError(f"Purchase-order line {po_line.id} needs a positive unit price")
            actual_unit_cost = (price * exchange_rate).quantize(unit_quantum, rounding=ROUND_HALF_UP)
            actual_amount = (quantity * actual_unit_cost).quantize(money_quantum, rounding=ROUND_HALF_UP)
            if actual_amount <= 0:
                raise ValueError(f"GRN line {line.id} has no positive base-currency receipt value")

            variance_account_id = None
            if method == "STANDARD":
                item = await db.get(Material if line.material_id else Product, line.material_id or line.product_id)
                standard_cost = Decimal(str(item.standard_cost or 0)) if item else Decimal("0")
                if not standard_cost.is_finite() or standard_cost <= 0:
                    raise ValueError(f"GRN item on line {line.id} needs a positive base-currency standard cost")
                valuation_unit_cost = standard_cost.quantize(unit_quantum, rounding=ROUND_HALF_UP)
                variance = actual_amount - (quantity * valuation_unit_cost).quantize(
                    money_quantum, rounding=ROUND_HALF_UP
                )
                if variance:
                    if not mapping.variance_account_id:
                        raise ValueError(f"GRN item on line {line.id} needs a configured variance account")
                    variance_account_id = mapping.variance_account_id
            else:
                # FIFO stores receipt-specific actual cost layers. WEIGHTED_AVG
                # retains actual receipt layers; their aggregate is the moving
                # weighted inventory value used by the valuation report.
                valuation_unit_cost = actual_unit_cost
                variance = Decimal("0")

            valuation_amount = (quantity * valuation_unit_cost).quantize(
                money_quantum, rounding=ROUND_HALF_UP
            )
            account_ids = {mapping.inventory_account_id, mapping.grni_account_id}
            if variance_account_id:
                account_ids.add(variance_account_id)
            account_result = await db.execute(
                select(ChartOfAccount).where(ChartOfAccount.id.in_(account_ids))
            )
            accounts = {account.id: account for account in account_result.scalars().all()}
            inventory_account = accounts.get(mapping.inventory_account_id)
            grni_account = accounts.get(mapping.grni_account_id)
            if not inventory_account or inventory_account.account_type != AccountType.ASSET:
                raise ValueError(f"Inventory mapping for GRN line {line.id} must point to an active asset account")
            if not grni_account or grni_account.account_type != AccountType.LIABILITY:
                raise ValueError(f"GRNI mapping for GRN line {line.id} must point to an active liability account")
            if variance_account_id and accounts[variance_account_id].account_type != AccountType.EXPENSE:
                raise ValueError(f"Variance mapping for GRN line {line.id} must point to an expense account")

            layer_result = await db.execute(
                select(CostLayer)
                .where(CostLayer.movement_id == movement.id)
                .with_for_update()
            )
            layer = layer_result.scalar_one_or_none()
            if layer:
                if (
                    layer.stock_type != (StockType.MATERIAL if line.material_id else StockType.PRODUCT)
                    or layer.material_id != line.material_id
                    or layer.product_id != line.product_id
                    or layer.warehouse_id != grn.warehouse_id
                    or layer.movement_id != movement.id
                    or layer.lot_id != movement.lot_id
                    or layer.qty_received != quantity
                    or layer.qty_remaining != quantity
                    or Decimal(str(layer.unit_cost)) != valuation_unit_cost
                ):
                    raise ValueError(f"GRN receipt movement {movement.id} already has a conflicting cost layer")
            else:
                from app.services.inventory_service import create_cost_layer
                layer = await create_cost_layer(
                    db,
                    stock_type=StockType.MATERIAL if line.material_id else StockType.PRODUCT,
                    product_id=line.product_id,
                    material_id=line.material_id,
                    lot_id=movement.lot_id,
                    warehouse_id=grn.warehouse_id,
                    movement_id=movement.id,
                    receipt_date=grn.received_date,
                    qty=quantity,
                    unit_cost=valuation_unit_cost,
                )

            event, batch, created = await get_or_create_operational_posting_event(
                db,
                source_module="procurement",
                source_event="GRN_INVENTORY_VALUATION_POSTED",
                source_id=grn.id,
                source_line_id=line.id,
                source_ref=grn.grn_no,
                stock_movement_id=movement.id,
                event_date=grn.received_date,
                amount=valuation_amount,
                currency=company.base_currency,
                created_by_id=user_id,
                require_period=True,
            )
            if not created or event.status != OperationalPostingStatus.PENDING:
                raise ValueError(f"A prior valuation event exists for GRN line {line.id}; manual reconciliation is required")

            entry = JournalEntry(
                entry_no=f"GRNVAL-{str(line.id).replace('-', '')}",
                entry_date=grn.received_date,
                description=f"Inventory valuation for GRN {grn.grn_no}",
                source_module="procurement",
                source_event="GRN_INVENTORY_VALUATION_POSTED",
                source_id=line.id,
                source_ref=grn.grn_no,
                company_id=company_id,
                branch_id=grn.branch_id or po.branch_id,
                cost_center_id=grn.cost_center_id or po.cost_center_id,
                status=JournalStatus.DRAFT,
                posting_batch_id=batch.id,
                created_by_id=user_id,
            )
            entry.lines.append(JournalLine(
                account_id=inventory_account.id,
                description=f"Inventory receipt valuation {grn.grn_no}",
                debit=valuation_amount,
                credit=Decimal("0"),
                currency=company.base_currency,
            ))
            if variance > 0:
                entry.lines.append(JournalLine(
                    account_id=variance_account_id or mapping.variance_account_id,
                    description=f"Standard-cost receipt variance {grn.grn_no}",
                    debit=variance,
                    credit=Decimal("0"),
                    currency=company.base_currency,
                ))
            elif variance < 0:
                entry.lines.append(JournalLine(
                    account_id=variance_account_id or mapping.variance_account_id,
                    description=f"Standard-cost receipt variance {grn.grn_no}",
                    debit=Decimal("0"),
                    credit=abs(variance),
                    currency=company.base_currency,
                ))
            entry.lines.append(JournalLine(
                account_id=grni_account.id,
                description=f"Goods received not invoiced {grn.grn_no}",
                debit=Decimal("0"),
                credit=actual_amount,
                currency=company.base_currency,
            ))
            db.add(entry)
            await db.flush()
            await assert_journal_lines_postable(db, entry.lines)
            await mark_journal_posted(db, entry, user_id, require_period=True)
            await mark_operational_posting_posted(
                db,
                event,
                batch,
                journal_entry_id=entry.id,
                posted_by_id=user_id,
            )

            movement.unit_cost = valuation_unit_cost.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            movement.total_cost = valuation_amount
            movement.valuation_method = method
            movement.valuation_amount = valuation_amount
            movement.valuation_currency = company.base_currency
            movement.posting_batch_id = batch.id
            movement.journal_entry_id = entry.id
            movement.accounting_status = OperationalPostingStatus.POSTED
            movement.posting_error = None
            apply_operational_posting_link(line, event, journal_entry_id=entry.id, status=OperationalPostingStatus.POSTED)
            posted_lines += 1

        await db.flush()
        return {
            "grn_id": grn.id,
            "status": OperationalPostingStatus.POSTED.value,
            "posted_lines": posted_lines,
            "idempotent_replay": False,
        }
    except Exception:
        await db.rollback()
        raise


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
