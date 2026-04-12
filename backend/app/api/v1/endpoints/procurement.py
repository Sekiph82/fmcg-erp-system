from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db
from app.models.procurement import (
    PurchaseRequisition, PRLine, PurchaseOrder, POLine,
    GoodsReceipt, GRNLine, ImportShipment, SupplierEvaluation,
    PRStatus, POStatus,
)
from decimal import Decimal as _Decimal
from app.models.master import Supplier
from app.schemas.procurement import (
    PRCreate, PRUpdate, PRRead, PRDetailRead, PRLineCreate,
    ApprovePRRequest, ConvertPRToPORequest,
    POCreate, POUpdate, PORead, PODetailRead, POLineCreate,
    GRNCreate, GRNRead, GRNDetailRead,
    ImportShipmentCreate, ImportShipmentUpdate, ImportShipmentRead,
    SupplierEvaluationCreate, SupplierEvaluationRead, SupplierDashboardRow,
    InboundScheduleRow, DeliveryAlertRow,
    SupplierPaymentCreate, SupplierPaymentRead,
)
from app.crud import procurement as crud
from app.services import procurement_service as svc

router = APIRouter()


# ── Purchase Requisitions ─────────────────────────────────────────────────────

@router.get("/pr/", response_model=List[PRRead])
async def list_prs(
    status: Optional[PRStatus] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    prs = await crud.list_prs(db, status=status)
    rows = []
    for pr in prs:
        r = PRRead.model_validate(pr)
        r.requester_name = pr.requester.full_name if pr.requester else None
        r.line_count = len(pr.lines)
        rows.append(r)
    return rows


@router.post("/pr/", response_model=PRDetailRead, status_code=201)
async def create_pr(
    body: PRCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pr = await crud.create_pr(db, body.model_dump(), current_user.id)
    await db.commit()
    pr = await crud.get_pr(db, pr.id)
    return _build_pr_detail(pr)


@router.get("/pr/{pr_id}", response_model=PRDetailRead)
async def get_pr(pr_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    pr = await crud.get_pr(db, pr_id)
    if not pr:
        raise HTTPException(404, "PR not found")
    return _build_pr_detail(pr)


@router.patch("/pr/{pr_id}", response_model=PRDetailRead)
async def update_pr(
    pr_id: uuid.UUID,
    body: PRUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pr = await crud.get_pr(db, pr_id)
    if not pr:
        raise HTTPException(404, "PR not found")
    if pr.status not in (PRStatus.DRAFT,):
        raise HTTPException(422, "Only DRAFT PRs can be edited")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(pr, k, v)
    await db.commit()
    pr = await crud.get_pr(db, pr_id)
    return _build_pr_detail(pr)


@router.post("/pr/{pr_id}/submit", response_model=PRRead)
async def submit_pr(pr_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    pr = await crud.get_pr(db, pr_id)
    if not pr:
        raise HTTPException(404, "PR not found")
    pr = await svc.submit_pr(db, pr)
    await db.commit()
    return _build_pr_read(pr)


@router.post("/pr/{pr_id}/approve", response_model=PRRead)
async def approve_pr(
    pr_id: uuid.UUID,
    body: ApprovePRRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pr = await crud.get_pr(db, pr_id)
    if not pr:
        raise HTTPException(404, "PR not found")
    if body.approve:
        pr = await svc.approve_pr(db, pr, current_user.id)
    else:
        if not body.rejection_reason:
            raise HTTPException(422, "Rejection reason required")
        pr = await svc.reject_pr(db, pr, current_user.id, body.rejection_reason)
    await db.commit()
    return _build_pr_read(pr)


@router.post("/pr/{pr_id}/convert", response_model=PODetailRead, status_code=201)
async def convert_pr_to_po(
    pr_id: uuid.UUID,
    body: ConvertPRToPORequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pr = await crud.get_pr(db, pr_id)
    if not pr:
        raise HTTPException(404, "PR not found")
    po = await svc.convert_pr_to_po(db, pr, body.model_dump(), current_user.id)
    await db.commit()
    po = await crud.get_po(db, po.id)
    return _build_po_detail(po)


@router.post("/pr/{pr_id}/lines", response_model=PRDetailRead, status_code=201)
async def add_pr_line(
    pr_id: uuid.UUID,
    body: PRLineCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pr = await crud.get_pr(db, pr_id)
    if not pr:
        raise HTTPException(404, "PR not found")
    if pr.status != PRStatus.DRAFT:
        raise HTTPException(422, "Only DRAFT PRs can be modified")
    await crud.add_pr_line(db, pr, body.model_dump())
    await db.commit()
    pr = await crud.get_pr(db, pr_id)
    return _build_pr_detail(pr)


@router.delete("/pr/{pr_id}/lines/{line_id}", status_code=204)
async def delete_pr_line(
    pr_id: uuid.UUID,
    line_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pr = await crud.get_pr(db, pr_id)
    if not pr or pr.status != PRStatus.DRAFT:
        raise HTTPException(422, "Only DRAFT PRs can be modified")
    line = await crud.get_pr_line(db, line_id)
    if not line or line.pr_id != pr_id:
        raise HTTPException(404, "Line not found")
    await crud.delete_pr_line(db, line)
    await db.commit()


# ── Purchase Orders ───────────────────────────────────────────────────────────

@router.get("/po/", response_model=List[PORead])
async def list_pos(
    status: Optional[POStatus] = None,
    supplier_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pos = await crud.list_pos(db, status=status, supplier_id=supplier_id)
    return [_build_po_read(po) for po in pos]


@router.post("/po/", response_model=PODetailRead, status_code=201)
async def create_po(
    body: POCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    po = await crud.create_po(db, body.model_dump(), current_user.id)
    await db.commit()
    po = await crud.get_po(db, po.id)
    return _build_po_detail(po)


@router.get("/po/{po_id}", response_model=PODetailRead)
async def get_po(po_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    po = await crud.get_po(db, po_id)
    if not po:
        raise HTTPException(404, "PO not found")
    return _build_po_detail(po)


@router.patch("/po/{po_id}", response_model=PODetailRead)
async def update_po(
    po_id: uuid.UUID,
    body: POUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    po = await crud.get_po(db, po_id)
    if not po:
        raise HTTPException(404, "PO not found")
    if po.status not in (POStatus.DRAFT,):
        raise HTTPException(422, "Only DRAFT POs can be edited")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(po, k, v)
    await db.commit()
    po = await crud.get_po(db, po_id)
    return _build_po_detail(po)


@router.post("/po/{po_id}/approve", response_model=PORead)
async def approve_po(po_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    po = await crud.get_po(db, po_id)
    if not po:
        raise HTTPException(404, "PO not found")
    po = await svc.approve_po(db, po, current_user.id)
    await db.commit()
    return _build_po_read(po)


@router.post("/po/{po_id}/order", response_model=PORead)
async def mark_ordered(po_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    po = await crud.get_po(db, po_id)
    if not po:
        raise HTTPException(404, "PO not found")
    po = await svc.mark_ordered(db, po)
    await db.commit()
    return _build_po_read(po)


@router.post("/po/{po_id}/cancel", response_model=PORead)
async def cancel_po(po_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    po = await crud.get_po(db, po_id)
    if not po:
        raise HTTPException(404, "PO not found")
    po = await svc.cancel_po(db, po)
    await db.commit()
    return _build_po_read(po)


@router.post("/po/{po_id}/lines", response_model=PODetailRead, status_code=201)
async def add_po_line(
    po_id: uuid.UUID,
    body: POLineCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    po = await crud.get_po(db, po_id)
    if not po or po.status != POStatus.DRAFT:
        raise HTTPException(422, "Only DRAFT POs can be modified")
    from app.models.procurement import POLine as POLineModel
    db.add(POLineModel(po_id=po_id, **body.model_dump()))
    await db.commit()
    po = await crud.get_po(db, po_id)
    return _build_po_detail(po)


# ── Goods Receipts ────────────────────────────────────────────────────────────

@router.get("/grn/", response_model=List[GRNRead])
async def list_grns(
    po_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    grns = await crud.list_grns(db, po_id=po_id)
    return [_build_grn_read(g) for g in grns]


@router.post("/grn/", response_model=GRNDetailRead, status_code=201)
async def create_grn(
    body: GRNCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    grn = await crud.create_grn(db, body.model_dump(), current_user.id)
    await db.commit()
    grn = await crud.get_grn(db, grn.id)
    return _build_grn_detail(grn)


@router.get("/grn/{grn_id}", response_model=GRNDetailRead)
async def get_grn(grn_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    grn = await crud.get_grn(db, grn_id)
    if not grn:
        raise HTTPException(404, "GRN not found")
    return _build_grn_detail(grn)


@router.post("/grn/{grn_id}/post", response_model=GRNDetailRead)
async def post_grn(grn_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    grn = await crud.get_grn(db, grn_id)
    if not grn:
        raise HTTPException(404, "GRN not found")
    grn = await svc.post_grn(db, grn, current_user.id)
    await db.commit()
    grn = await crud.get_grn(db, grn_id)
    return _build_grn_detail(grn)


# ── Import Shipments ──────────────────────────────────────────────────────────

@router.get("/shipments/", response_model=List[ImportShipmentRead])
async def list_shipments(
    po_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ships = await crud.list_shipments(db, po_id=po_id)
    return [_build_shipment_read(s) for s in ships]


@router.post("/shipments/", response_model=ImportShipmentRead, status_code=201)
async def create_shipment(
    body: ImportShipmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ship = await crud.create_shipment(db, body.model_dump())
    await db.commit()
    ship = await crud.get_shipment(db, ship.id)
    return _build_shipment_read(ship)


@router.get("/shipments/{shipment_id}", response_model=ImportShipmentRead)
async def get_shipment(shipment_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    ship = await crud.get_shipment(db, shipment_id)
    if not ship:
        raise HTTPException(404, "Shipment not found")
    return _build_shipment_read(ship)


@router.patch("/shipments/{shipment_id}", response_model=ImportShipmentRead)
async def update_shipment(
    shipment_id: uuid.UUID,
    body: ImportShipmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ship = await crud.get_shipment(db, shipment_id)
    if not ship:
        raise HTTPException(404, "Shipment not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(ship, k, v)
    await db.commit()
    ship = await crud.get_shipment(db, shipment_id)
    return _build_shipment_read(ship)


# ── Supplier Payments ───────────────────────────────��────────────────────────

@router.post("/po/{po_id}/payments", response_model=SupplierPaymentRead, status_code=201)
async def record_supplier_payment(
    po_id: uuid.UUID,
    body: SupplierPaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    po = await crud.get_po(db, po_id)
    if not po:
        raise HTTPException(404, "PO not found")
    if po.status == POStatus.CANCELLED:
        raise HTTPException(422, "Cannot record payment for a cancelled PO")
    payment = await crud.create_supplier_payment(db, po, body.model_dump(), current_user.id)
    await db.commit()
    await db.refresh(payment)
    return payment


@router.get("/po/{po_id}/payments", response_model=List[SupplierPaymentRead])
async def list_supplier_payments(
    po_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    po = await crud.get_po(db, po_id)
    if not po:
        raise HTTPException(404, "PO not found")
    return await crud.get_supplier_payments(db, po_id)


# ── Supplier Evaluations ─────────────────���────────────────────────────────���───

@router.get("/evaluations/", response_model=List[SupplierEvaluationRead])
async def list_evaluations(
    supplier_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    evals = await crud.list_evaluations(db, supplier_id=supplier_id)
    return [_build_eval_read(e) for e in evals]


@router.post("/evaluations/", response_model=SupplierEvaluationRead, status_code=201)
async def create_evaluation(
    body: SupplierEvaluationCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ev = await crud.create_evaluation(db, body.model_dump(), current_user.id)
    await db.commit()
    ev = (await crud.list_evaluations(db, supplier_id=body.supplier_id))[0]
    return _build_eval_read(ev)


@router.get("/suppliers/dashboard", response_model=List[SupplierDashboardRow])
async def supplier_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from sqlalchemy import case
    from datetime import date as date_cls

    result = await db.execute(
        select(Supplier).options(selectinload(Supplier.materials))
        .where(Supplier.is_active == True)  # noqa: E712
        .order_by(Supplier.name)
    )
    suppliers = result.scalars().all()

    rows = []
    today = date_cls.today()
    for s in suppliers:
        # PO stats
        po_result = await db.execute(
            select(PurchaseOrder).where(PurchaseOrder.supplier_id == s.id)
        )
        pos = list(po_result.scalars().all())
        open_statuses = {POStatus.DRAFT, POStatus.APPROVED, POStatus.ORDERED, POStatus.PARTIALLY_RECEIVED}
        open_pos = [p for p in pos if p.status in open_statuses]
        overdue_pos = [
            p for p in open_pos
            if p.status in {POStatus.ORDERED, POStatus.PARTIALLY_RECEIVED}
            and p.expected_delivery_date < today
        ]

        # Evaluation stats
        eval_result = await db.execute(
            select(SupplierEvaluation)
            .where(SupplierEvaluation.supplier_id == s.id)
            .order_by(SupplierEvaluation.evaluation_date.desc())
        )
        evals = list(eval_result.scalars().all())
        avg_otd = (sum(float(e.on_time_delivery_score) for e in evals) / len(evals)) if evals else None
        avg_qual = (sum(float(e.quality_score) for e in evals) / len(evals)) if evals else None
        avg_overall = (sum(float(e.overall_score) for e in evals) / len(evals)) if evals else None
        last_eval = evals[0].evaluation_date if evals else None

        rows.append(SupplierDashboardRow(
            supplier_id=s.id,
            supplier_name=s.name,
            supplier_code=s.code,
            is_preferred=s.is_preferred,
            lead_time_days=s.lead_time_days,
            performance_score=s.performance_score,
            compliance_notes=s.compliance_notes,
            total_pos=len(pos),
            open_pos=len(open_pos),
            overdue_pos=len(overdue_pos),
            avg_on_time_delivery=Decimal(str(round(avg_otd, 2))) if avg_otd is not None else None,
            avg_quality=Decimal(str(round(avg_qual, 2))) if avg_qual is not None else None,
            avg_overall=Decimal(str(round(avg_overall, 2))) if avg_overall is not None else None,
            last_evaluation_date=last_eval,
        ))
    return rows


# ── Delivery Planning ─────────────────────────────────────────────────────────

@router.get("/delivery/schedule", response_model=List[InboundScheduleRow])
async def inbound_schedule(
    days_ahead: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await svc.get_inbound_schedule(db, days_ahead=days_ahead)


@router.get("/delivery/alerts", response_model=List[DeliveryAlertRow])
async def delivery_alerts(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await svc.get_delivery_alerts(db)


# ── Builder helpers ───────────────────────────────────────────────────────────

def _build_pr_read(pr: PurchaseRequisition) -> PRRead:
    r = PRRead.model_validate(pr)
    r.requester_name = pr.requester.full_name if pr.requester else None
    r.line_count = len(pr.lines) if pr.lines else 0
    return r


def _build_pr_detail(pr: PurchaseRequisition) -> PRDetailRead:
    r = PRDetailRead.model_validate(pr)
    r.requester_name = pr.requester.full_name if pr.requester else None
    r.line_count = len(pr.lines) if pr.lines else 0
    lines = []
    for l in (pr.lines or []):
        lr = PRLineRead.model_validate(l)
        lr.material_name = l.material.name if l.material else None
        lr.material_code = l.material.code if l.material else None
        lr.product_name = l.product.name if l.product else None
        lr.product_sku = l.product.sku if l.product else None
        lr.preferred_supplier_name = l.preferred_supplier.name if l.preferred_supplier else None
        lines.append(lr)
    r.lines = lines
    return r


def _build_po_read(po: PurchaseOrder) -> PORead:
    from datetime import date as date_cls
    r = PORead.model_validate(po)
    r.supplier_name = po.supplier.name if po.supplier else None
    r.pr_no = po.pr.pr_no if po.pr else None
    today = date_cls.today()
    r.days_until_delivery = (po.expected_delivery_date - today).days
    if po.lines:
        r.total_value = sum(l.ordered_quantity * l.unit_price for l in po.lines)
    if po.supplier_payments:
        r.paid_amount = sum(p.amount for p in po.supplier_payments)
    return r


def _build_po_detail(po: PurchaseOrder) -> PODetailRead:
    r = PODetailRead.model_validate(po)
    r.supplier_name = po.supplier.name if po.supplier else None
    r.pr_no = po.pr.pr_no if po.pr else None
    from datetime import date as date_cls
    today = date_cls.today()
    r.days_until_delivery = (po.expected_delivery_date - today).days
    lines = []
    for l in (po.lines or []):
        lr = POLineRead.model_validate(l)
        lr.material_name = l.material.name if l.material else None
        lr.material_code = l.material.code if l.material else None
        lr.product_name = l.product.name if l.product else None
        lr.product_sku = l.product.sku if l.product else None
        lines.append(lr)
    r.lines = lines
    if lines:
        r.total_value = sum(l.line_total for l in lines)
    if po.supplier_payments:
        r.paid_amount = sum(p.amount for p in po.supplier_payments)
    return r


def _build_grn_read(grn: GoodsReceipt) -> GRNRead:
    r = GRNRead.model_validate(grn)
    r.po_no = grn.po.po_no if grn.po else None
    r.warehouse_name = grn.warehouse.name if grn.warehouse else None
    return r


def _build_grn_detail(grn: GoodsReceipt) -> GRNDetailRead:
    r = GRNDetailRead.model_validate(grn)
    r.po_no = grn.po.po_no if grn.po else None
    r.warehouse_name = grn.warehouse.name if grn.warehouse else None
    lines = []
    for l in (grn.lines or []):
        lr = GRNLineRead.model_validate(l)
        lr.material_name = l.material.name if l.material else None
        lr.product_name = l.product.name if l.product else None
        lines.append(lr)
    r.lines = lines
    return r


def _build_shipment_read(ship: ImportShipment) -> ImportShipmentRead:
    r = ImportShipmentRead.model_validate(ship)
    if ship.po:
        r.po_no = ship.po.po_no
        r.supplier_name = ship.po.supplier.name if ship.po.supplier else None
    return r


def _build_eval_read(ev: SupplierEvaluation) -> SupplierEvaluationRead:
    r = SupplierEvaluationRead.model_validate(ev)
    r.po_no = ev.po.po_no if ev.po else None
    return r
