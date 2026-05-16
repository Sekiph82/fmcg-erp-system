from __future__ import annotations

from typing import Optional, List
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.procurement import (
    PurchaseRequisition, PRLine, PurchaseOrder, POLine,
    GoodsReceipt, GRNLine, ImportShipment, SupplierEvaluation, SupplierPayment,
    PRStatus, POStatus,
)


# ── PR ─────────────────────────────────────────────────────────────────────────

async def list_prs(
    db: AsyncSession,
    status: Optional[PRStatus] = None,
    requester_id: Optional[uuid.UUID] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[PurchaseRequisition]:
    q = select(PurchaseRequisition).options(
        selectinload(PurchaseRequisition.requester),
        selectinload(PurchaseRequisition.lines),
    )
    if status:
        q = q.where(PurchaseRequisition.status == status)
    if requester_id:
        q = q.where(PurchaseRequisition.requester_id == requester_id)
    q = q.order_by(PurchaseRequisition.created_at.desc())
    result = await db.execute(q.offset(offset).limit(min(limit, 1000)))
    return list(result.scalars().all())


async def get_pr(db: AsyncSession, pr_id: uuid.UUID) -> Optional[PurchaseRequisition]:
    result = await db.execute(
        select(PurchaseRequisition)
        .options(
            selectinload(PurchaseRequisition.requester),
            selectinload(PurchaseRequisition.approver),
            selectinload(PurchaseRequisition.lines).selectinload(PRLine.material),
            selectinload(PurchaseRequisition.lines).selectinload(PRLine.product),
            selectinload(PurchaseRequisition.lines).selectinload(PRLine.preferred_supplier),
        )
        .where(PurchaseRequisition.id == pr_id)
    )
    return result.scalar_one_or_none()


async def create_pr(
    db: AsyncSession, data: dict, requester_id: uuid.UUID
) -> PurchaseRequisition:
    lines_data = data.pop("lines", [])
    pr = PurchaseRequisition(**data, requester_id=requester_id)
    db.add(pr)
    await db.flush()
    for ld in lines_data:
        db.add(PRLine(pr_id=pr.id, **ld))
    await db.flush()
    await db.refresh(pr)
    return pr


async def add_pr_line(db: AsyncSession, pr: PurchaseRequisition, data: dict) -> PRLine:
    line = PRLine(pr_id=pr.id, **data)
    db.add(line)
    await db.flush()
    return line


async def delete_pr_line(db: AsyncSession, line: PRLine) -> None:
    await db.delete(line)
    await db.flush()


async def get_pr_line(db: AsyncSession, line_id: uuid.UUID) -> Optional[PRLine]:
    result = await db.execute(select(PRLine).where(PRLine.id == line_id))
    return result.scalar_one_or_none()


# ── PO ─────────────────────────────────────────────────────────────────────────

async def list_pos(
    db: AsyncSession,
    status: Optional[POStatus] = None,
    supplier_id: Optional[uuid.UUID] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[PurchaseOrder]:
    q = select(PurchaseOrder).options(
        selectinload(PurchaseOrder.supplier),
        selectinload(PurchaseOrder.pr),
        selectinload(PurchaseOrder.lines),
    )
    if status:
        q = q.where(PurchaseOrder.status == status)
    if supplier_id:
        q = q.where(PurchaseOrder.supplier_id == supplier_id)
    q = q.order_by(PurchaseOrder.created_at.desc())
    result = await db.execute(q.offset(offset).limit(min(limit, 1000)))
    return list(result.scalars().all())


async def get_po(db: AsyncSession, po_id: uuid.UUID) -> Optional[PurchaseOrder]:
    result = await db.execute(
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.supplier),
            selectinload(PurchaseOrder.pr),
            selectinload(PurchaseOrder.approver),
            selectinload(PurchaseOrder.created_by),
            selectinload(PurchaseOrder.lines).selectinload(POLine.material),
            selectinload(PurchaseOrder.lines).selectinload(POLine.product),
            selectinload(PurchaseOrder.goods_receipts).selectinload(GoodsReceipt.lines),
            selectinload(PurchaseOrder.import_shipment),
            selectinload(PurchaseOrder.supplier_payments),
        )
        .where(PurchaseOrder.id == po_id)
    )
    return result.scalar_one_or_none()


async def create_po(db: AsyncSession, data: dict, created_by_id: uuid.UUID) -> PurchaseOrder:
    lines_data = data.pop("lines", [])
    po = PurchaseOrder(**data, created_by_id=created_by_id)
    db.add(po)
    await db.flush()
    for ld in lines_data:
        db.add(POLine(po_id=po.id, **ld))
    await db.flush()
    await db.refresh(po)
    return po


async def get_po_line(db: AsyncSession, line_id: uuid.UUID) -> Optional[POLine]:
    result = await db.execute(select(POLine).where(POLine.id == line_id))
    return result.scalar_one_or_none()


# ── GRN ────────────────────────────────────────────────────────────────────────

async def list_grns(db: AsyncSession, po_id: Optional[uuid.UUID] = None, limit: int = 100, offset: int = 0) -> List[GoodsReceipt]:
    q = select(GoodsReceipt).options(
        selectinload(GoodsReceipt.po),
        selectinload(GoodsReceipt.warehouse),
    )
    if po_id:
        q = q.where(GoodsReceipt.po_id == po_id)
    q = q.order_by(GoodsReceipt.received_date.desc())
    result = await db.execute(q.offset(offset).limit(min(limit, 1000)))
    return list(result.scalars().all())


async def get_grn(db: AsyncSession, grn_id: uuid.UUID) -> Optional[GoodsReceipt]:
    result = await db.execute(
        select(GoodsReceipt)
        .options(
            selectinload(GoodsReceipt.po).selectinload(PurchaseOrder.supplier),
            selectinload(GoodsReceipt.warehouse),
            selectinload(GoodsReceipt.received_by),
            selectinload(GoodsReceipt.lines).selectinload(GRNLine.material),
            selectinload(GoodsReceipt.lines).selectinload(GRNLine.product),
        )
        .where(GoodsReceipt.id == grn_id)
    )
    return result.scalar_one_or_none()


async def create_grn(db: AsyncSession, data: dict, received_by_id: uuid.UUID) -> GoodsReceipt:
    lines_data = data.pop("lines", [])
    grn = GoodsReceipt(**data, received_by_id=received_by_id)
    db.add(grn)
    await db.flush()
    for ld in lines_data:
        db.add(GRNLine(grn_id=grn.id, **ld))
    await db.flush()
    await db.refresh(grn)
    return grn


# ── Import Shipment ────────────────────────────────────────────────────────────

async def list_shipments(
    db: AsyncSession, po_id: Optional[uuid.UUID] = None, limit: int = 100, offset: int = 0
) -> List[ImportShipment]:
    q = select(ImportShipment).options(selectinload(ImportShipment.po).selectinload(PurchaseOrder.supplier))
    if po_id:
        q = q.where(ImportShipment.po_id == po_id)
    q = q.order_by(ImportShipment.created_at.desc())
    result = await db.execute(q.offset(offset).limit(min(limit, 1000)))
    return list(result.scalars().all())


async def get_shipment(db: AsyncSession, shipment_id: uuid.UUID) -> Optional[ImportShipment]:
    result = await db.execute(
        select(ImportShipment)
        .options(selectinload(ImportShipment.po).selectinload(PurchaseOrder.supplier))
        .where(ImportShipment.id == shipment_id)
    )
    return result.scalar_one_or_none()


async def create_shipment(db: AsyncSession, data: dict) -> ImportShipment:
    shipment = ImportShipment(**data)
    db.add(shipment)
    await db.flush()
    await db.refresh(shipment)
    return shipment


# ── Supplier Evaluations ───────────────────────────────────────────────────────

async def list_evaluations(
    db: AsyncSession, supplier_id: Optional[uuid.UUID] = None, limit: int = 200, offset: int = 0
) -> List[SupplierEvaluation]:
    q = select(SupplierEvaluation).options(
        selectinload(SupplierEvaluation.supplier),
        selectinload(SupplierEvaluation.evaluator),
    )
    if supplier_id:
        q = q.where(SupplierEvaluation.supplier_id == supplier_id)
    q = q.order_by(SupplierEvaluation.evaluation_date.desc())
    result = await db.execute(q.offset(offset).limit(min(limit, 1000)))
    return list(result.scalars().all())


async def create_evaluation(
    db: AsyncSession, data: dict, evaluator_id: uuid.UUID
) -> SupplierEvaluation:
    overall = (
        data["on_time_delivery_score"] + data["quality_score"] +
        data["price_competitiveness_score"] + data["responsiveness_score"]
    ) / 4
    eval_obj = SupplierEvaluation(**data, evaluator_id=evaluator_id, overall_score=overall)
    db.add(eval_obj)
    await db.flush()
    # Update supplier.performance_score as rolling average
    from app.models.master import Supplier
    result = await db.execute(select(Supplier).where(Supplier.id == data["supplier_id"]))
    supplier = result.scalar_one_or_none()
    if supplier:
        supplier.performance_score = overall
    await db.flush()
    await db.refresh(eval_obj)
    return eval_obj


# ── Supplier Payments ─────────────────────────────────────────────────────────

async def get_supplier_payments(
    db: AsyncSession, po_id: uuid.UUID, limit: int = 500
) -> List[SupplierPayment]:
    result = await db.execute(
        select(SupplierPayment)
        .where(SupplierPayment.po_id == po_id)
        .order_by(SupplierPayment.created_at)
        .limit(min(limit, 1000))
    )
    return list(result.scalars().all())


async def create_supplier_payment(
    db: AsyncSession, po: PurchaseOrder, data: dict, user_id: uuid.UUID
) -> SupplierPayment:
    from decimal import Decimal
    payment = SupplierPayment(
        po_id=po.id,
        supplier_id=po.supplier_id,
        created_by_id=user_id,
        **data,
    )
    db.add(payment)
    await db.flush()

    # Recalculate payment_status based on total paid vs PO total
    paid_result = await db.execute(
        select(SupplierPayment).where(SupplierPayment.po_id == po.id)
    )
    all_payments = list(paid_result.scalars().all())
    total_paid = sum(p.amount for p in all_payments)

    po_total = sum(
        l.ordered_quantity * l.unit_price * (1 + l.tax_rate)
        for l in po.lines
    ) if po.lines else Decimal("0")

    from app.models.procurement import POPaymentStatus
    if po_total > 0 and total_paid >= po_total - Decimal("0.005"):
        po.payment_status = POPaymentStatus.PAID
    elif total_paid > 0:
        po.payment_status = POPaymentStatus.PARTIALLY_PAID

    # Track latest M-Pesa reference on the PO
    if data.get("method") == "mpesa" and data.get("reference"):
        po.mpesa_reference = data["reference"]
    po.payment_method = data.get("method", po.payment_method)

    await db.flush()
    await db.refresh(payment)
    return payment
