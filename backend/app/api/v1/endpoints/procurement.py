from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db, require_permission
from app.core.access_control import (
    forbidden_detail,
    has_any_permission,
    require_any_permission,
)
from app.models.finance import OperationalPostingStatus
from app.models.procurement import (
    PurchaseRequisition, PRLine, PurchaseOrder, POLine,
    GoodsReceipt, GRNLine, ImportShipment, SupplierEvaluation,
    RFQRequest, RFQLine, RFQResponse, BlanketPurchaseAgreement, AutoReorderPolicy,
    ProcurementApprovalRule,
    PRStatus, POStatus, RFQStatus, RFQResponseStatus, RFQInvitationStatus,
    RFQEvaluationStatus, RFQEvaluationCriterion, RFQResponseEvaluation, RFQResponseLineQuote,
    BPAStatus,
    RFQAward, RFQAwardAllocation, RFQAwardApproval, RFQAwardStatus,
    RFQAwardApprovalStatus, ProcurementApprovalDocumentType,
)
from decimal import Decimal as _Decimal
from app.models.master import Product, Supplier
from app.models.role import Role
from app.models.user import User
from app.schemas.procurement import (
    PRCreate, PRUpdate, PRRead, PRDetailRead, PRLineCreate, PRLineRead,
    ApprovePRRequest, ConvertPRToPORequest,
    POCreate, POUpdate, PORead, PODetailRead, POLineCreate, POLineRead,
    GRNCreate, GRNRead, GRNDetailRead, GRNLineRead,
    ImportShipmentCreate, ImportShipmentUpdate, ImportShipmentRead,
    SupplierEvaluationCreate, SupplierEvaluationRead, SupplierDashboardRow,
    InboundScheduleRow, DeliveryAlertRow,
    SupplierPaymentCreate, SupplierPaymentRead,
    RFQCreate, RFQUpdate, RFQRead, RFQDetailRead, RFQLineRead, RFQResponseCreate, RFQResponseRead,
    RFQEvaluationMatrixCreate, RFQEvaluationCriterionRead, RFQResponseEvaluationSubmit,
    RFQResponseEvaluationRead,
    RFQAwardProposalCreate, RFQAwardDecision, RFQAwardRead, RFQResponseLineQuoteRead,
    BlanketAgreementCreate, BlanketAgreementUpdate, BlanketAgreementRead,
    AutoReorderPolicyCreate, AutoReorderPolicyUpdate, AutoReorderPolicyRead,
    ProcurementApprovalRuleCreate, ProcurementApprovalRuleUpdate, ProcurementApprovalRuleRead,
)
from app.crud import procurement as crud
from app.services import procurement_service as svc

router = APIRouter()

PROCUREMENT_VIEW_PERMISSIONS = (
    "procurement.view",
    "procurement.view_all",
    "procurement.view_own_scope",
)


def _procurement_forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=403, detail=forbidden_detail(detail))


def _has_broad_procurement_view(user) -> bool:
    return has_any_permission(user, ("procurement.view", "procurement.view_all"))


def _procurement_department(record) -> str | None:
    department = getattr(record, "department", None)
    if department:
        return str(department)
    pr = getattr(record, "pr", None)
    department = getattr(pr, "department", None)
    return str(department) if department else None


def _can_view_procurement_record(user, record) -> bool:
    return svc.build_procurement_access_hint(user, record).can_view


def _require_procurement_view(user, record) -> None:
    svc.ensure_procurement_action_allowed(user, record, "view")


def _require_procurement_action(user, record, action: str) -> None:
    svc.ensure_procurement_action_allowed(user, record, action)


# ── Purchase Requisitions ─────────────────────────────────────────────────────

@router.get("/pr/", response_model=List[PRRead])
async def list_prs(
    status: Optional[PRStatus] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_any_permission(PROCUREMENT_VIEW_PERMISSIONS)),
):
    prs = await crud.list_prs(db, status=status)
    if not _has_broad_procurement_view(current_user):
        prs = [pr for pr in prs if _can_view_procurement_record(current_user, pr)]
    rows = []
    for pr in prs:
        r = PRRead.model_validate(pr)
        r.requester_name = pr.requester.full_name if pr.requester else None
        r.line_count = len(pr.lines)
        r.access = svc.build_procurement_access_hint(current_user, pr)
        rows.append(r)
    return rows


@router.post("/pr/", response_model=PRDetailRead, status_code=201)
async def create_pr(
    body: PRCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_procurement_action(current_user, PurchaseRequisition(**body.model_dump(exclude={"lines"})), "create")
    pr = await crud.create_pr(db, body.model_dump(), current_user.id)
    await db.commit()
    pr = await crud.get_pr(db, pr.id)
    return _build_pr_detail(pr, current_user)


@router.get("/pr/{pr_id}", response_model=PRDetailRead)
async def get_pr(pr_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(require_any_permission(PROCUREMENT_VIEW_PERMISSIONS))):
    pr = await crud.get_pr(db, pr_id)
    if not pr:
        raise HTTPException(404, "PR not found")
    _require_procurement_view(current_user, pr)
    return _build_pr_detail(pr, current_user)


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
    _require_procurement_action(current_user, pr, "edit")
    if pr.status not in (PRStatus.DRAFT,):
        raise HTTPException(422, "Only DRAFT PRs can be edited")
    updates = body.model_dump(exclude_unset=True)
    if "department" in updates and updates["department"] != pr.department:
        _require_procurement_action(current_user, PurchaseRequisition(department=updates["department"]), "edit")
    for k, v in updates.items():
        setattr(pr, k, v)
    await db.commit()
    pr = await crud.get_pr(db, pr_id)
    return _build_pr_detail(pr, current_user)


@router.post("/pr/{pr_id}/submit", response_model=PRRead)
async def submit_pr(pr_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    pr = await crud.get_pr(db, pr_id)
    if not pr:
        raise HTTPException(404, "PR not found")
    _require_procurement_action(current_user, pr, "edit")
    pr = await svc.submit_pr(db, pr)
    await db.commit()
    return _build_pr_read(pr, current_user)


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
    _require_procurement_action(current_user, pr, "approve")
    if body.approve:
        pr = await svc.approve_pr(db, pr, current_user.id)
    else:
        if not body.rejection_reason:
            raise HTTPException(422, "Rejection reason required")
        pr = await svc.reject_pr(db, pr, current_user.id, body.rejection_reason)
    await db.commit()
    return _build_pr_read(pr, current_user)


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
    _require_procurement_action(current_user, pr, "create")
    po = await svc.convert_pr_to_po(db, pr, body.model_dump(), current_user.id)
    await db.commit()
    po = await crud.get_po(db, po.id)
    return _build_po_detail(po, current_user)


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
    _require_procurement_action(current_user, pr, "edit")
    if pr.status != PRStatus.DRAFT:
        raise HTTPException(422, "Only DRAFT PRs can be modified")
    await crud.add_pr_line(db, pr, body.model_dump())
    await db.commit()
    pr = await crud.get_pr(db, pr_id)
    return _build_pr_detail(pr, current_user)


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
    _require_procurement_action(current_user, pr, "edit")
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
    current_user=Depends(require_any_permission(PROCUREMENT_VIEW_PERMISSIONS)),
):
    pos = await crud.list_pos(db, status=status, supplier_id=supplier_id)
    if not _has_broad_procurement_view(current_user):
        pos = [po for po in pos if _can_view_procurement_record(current_user, po)]
    return [_build_po_read(po, current_user) for po in pos]


@router.post("/po/", response_model=PODetailRead, status_code=201)
async def create_po(
    body: POCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    target = PurchaseOrder(**body.model_dump(exclude={"lines"}))
    _require_procurement_action(current_user, target, "create")
    po = await crud.create_po(db, body.model_dump(), current_user.id)
    await db.commit()
    po = await crud.get_po(db, po.id)
    return _build_po_detail(po, current_user)


@router.get("/po/{po_id}", response_model=PODetailRead)
async def get_po(po_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(require_any_permission(PROCUREMENT_VIEW_PERMISSIONS))):
    po = await crud.get_po(db, po_id)
    if not po:
        raise HTTPException(404, "PO not found")
    _require_procurement_view(current_user, po)
    return _build_po_detail(po, current_user)


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
    _require_procurement_action(current_user, po, "edit")
    if po.status not in (POStatus.DRAFT,):
        raise HTTPException(422, "Only DRAFT POs can be edited")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(po, k, v)
    await db.commit()
    po = await crud.get_po(db, po_id)
    return _build_po_detail(po, current_user)


@router.post("/po/{po_id}/approve", response_model=PORead)
async def approve_po(po_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    po = await crud.get_po(db, po_id)
    if not po:
        raise HTTPException(404, "PO not found")
    _require_procurement_action(current_user, po, "approve")
    po = await svc.approve_po(db, po, current_user.id)
    await db.commit()
    return _build_po_read(po, current_user)


@router.post("/po/{po_id}/order", response_model=PORead)
async def mark_ordered(po_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    po = await crud.get_po(db, po_id)
    if not po:
        raise HTTPException(404, "PO not found")
    _require_procurement_action(current_user, po, "edit")
    po = await svc.mark_ordered(db, po)
    await db.commit()
    return _build_po_read(po, current_user)


@router.post("/po/{po_id}/cancel", response_model=PORead)
async def cancel_po(po_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    po = await crud.get_po(db, po_id)
    if not po:
        raise HTTPException(404, "PO not found")
    _require_procurement_action(current_user, po, "edit")
    po = await svc.cancel_po(db, po)
    await db.commit()
    return _build_po_read(po, current_user)


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
    _require_procurement_action(current_user, po, "edit")
    from app.models.procurement import POLine as POLineModel
    db.add(POLineModel(po_id=po_id, **body.model_dump()))
    await db.commit()
    po = await crud.get_po(db, po_id)
    return _build_po_detail(po, current_user)


# ── Goods Receipts ────────────────────────────────────────────────────────────

@router.get("/grn/", response_model=List[GRNRead])
async def list_grns(
    po_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    grns = await crud.list_grns(db, po_id=po_id)
    grns = [g for g in grns if _can_view_procurement_record(current_user, g)]
    return [_build_grn_read(g, current_user) for g in grns]


@router.post("/grn/", response_model=GRNDetailRead, status_code=201)
async def create_grn(
    body: GRNCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    target = GoodsReceipt(**body.model_dump(exclude={"lines"}))
    _require_procurement_action(current_user, target, "receive")
    grn = await crud.create_grn(db, body.model_dump(), current_user.id)
    await db.commit()
    grn = await crud.get_grn(db, grn.id)
    return _build_grn_detail(grn, current_user)


@router.get("/grn/{grn_id}", response_model=GRNDetailRead)
async def get_grn(grn_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    grn = await crud.get_grn(db, grn_id)
    if not grn:
        raise HTTPException(404, "GRN not found")
    _require_procurement_view(current_user, grn)
    return _build_grn_detail(grn, current_user)


@router.post(
    "/grn/{grn_id}/post",
    response_model=GRNDetailRead,
    dependencies=[Depends(require_permission("finance", "post"))],
)
async def post_grn(grn_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    grn = await crud.get_grn(db, grn_id)
    if not grn:
        raise HTTPException(404, "GRN not found")
    _require_procurement_action(current_user, grn, "post")
    try:
        grn = await svc.post_grn(db, grn, current_user.id)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    grn = await crud.get_grn(db, grn_id)
    return _build_grn_detail(grn, current_user)


@router.post(
    "/grn/{grn_id}/valuation/post",
    response_model=GRNDetailRead,
    dependencies=[Depends(require_permission("finance", "post"))],
)
async def post_grn_inventory_valuation(
    grn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Post legacy GRN valuation when its receipt stock remains untouched."""
    grn = await crud.get_grn(db, grn_id)
    if not grn:
        raise HTTPException(404, "GRN not found")
    _require_procurement_view(current_user, grn)
    try:
        await svc.post_grn_inventory_valuation(db, grn_id, current_user.id)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    posted_grn = await crud.get_grn(db, grn_id)
    return _build_grn_detail(posted_grn, current_user)


# ── Import Shipments ──────────────────────────────────────────────────────────

@router.get("/shipments/", response_model=List[ImportShipmentRead])
async def list_shipments(
    po_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ships = await crud.list_shipments(db, po_id=po_id)
    ships = [s for s in ships if _can_view_procurement_record(current_user, s)]
    return [_build_shipment_read(s, current_user) for s in ships]


@router.post("/shipments/", response_model=ImportShipmentRead, status_code=201)
async def create_shipment(
    body: ImportShipmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    target = ImportShipment(**body.model_dump())
    _require_procurement_action(current_user, target, "create")
    ship = await crud.create_shipment(db, body.model_dump())
    await db.commit()
    ship = await crud.get_shipment(db, ship.id)
    return _build_shipment_read(ship, current_user)


@router.get("/shipments/{shipment_id}", response_model=ImportShipmentRead)
async def get_shipment(shipment_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    ship = await crud.get_shipment(db, shipment_id)
    if not ship:
        raise HTTPException(404, "Shipment not found")
    _require_procurement_view(current_user, ship)
    return _build_shipment_read(ship, current_user)


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
    _require_procurement_action(current_user, ship, "edit")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(ship, k, v)
    await db.commit()
    ship = await crud.get_shipment(db, shipment_id)
    return _build_shipment_read(ship, current_user)


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
    _require_procurement_action(current_user, po, "post")
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
    _require_procurement_view(current_user, po)
    return await crud.get_supplier_payments(db, po_id)


# ── Supplier Evaluations ─────────────────���────────────────────────────────���───

@router.get("/evaluations/", response_model=List[SupplierEvaluationRead])
async def list_evaluations(
    supplier_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    evals = await crud.list_evaluations(db, supplier_id=supplier_id)
    evals = [e for e in evals if _can_view_procurement_record(current_user, e)]
    return [_build_eval_read(e, current_user) for e in evals]


@router.post("/evaluations/", response_model=SupplierEvaluationRead, status_code=201)
async def create_evaluation(
    body: SupplierEvaluationCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    target = SupplierEvaluation(**body.model_dump(), evaluator_id=current_user.id)
    _require_procurement_action(current_user, target, "edit")
    ev = await crud.create_evaluation(db, body.model_dump(), current_user.id)
    await db.commit()
    ev = (await crud.list_evaluations(db, supplier_id=body.supplier_id))[0]
    return _build_eval_read(ev, current_user)


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
        avg_overall = await crud.average_supplier_score(db, s.id)
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
            avg_overall=avg_overall,
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

@router.get("/approval-rules", response_model=List[ProcurementApprovalRuleRead])
async def list_approval_rules(
    active_only: bool = True,
    limit: int = Query(200, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_any_permission(("procurement.approve_all", "roles.manage"))),
):
    query = select(ProcurementApprovalRule).order_by(
        ProcurementApprovalRule.document_type,
        ProcurementApprovalRule.approval_level,
        ProcurementApprovalRule.rule_name,
    )
    if active_only:
        query = query.where(ProcurementApprovalRule.is_active.is_(True))
    result = await db.execute(query.limit(limit))
    return list(result.scalars().all())


@router.post("/approval-rules", response_model=ProcurementApprovalRuleRead, status_code=201)
async def create_approval_rule(
    body: ProcurementApprovalRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_any_permission(("procurement.approve_all", "roles.manage"))),
):
    if not body.approver_user_id and not body.approver_role_id:
        raise HTTPException(422, "Approval rule requires approver_user_id or approver_role_id")
    rule = ProcurementApprovalRule(**body.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.patch("/approval-rules/{rule_id}", response_model=ProcurementApprovalRuleRead)
async def update_approval_rule(
    rule_id: uuid.UUID,
    body: ProcurementApprovalRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_any_permission(("procurement.approve_all", "roles.manage"))),
):
    result = await db.execute(select(ProcurementApprovalRule).where(ProcurementApprovalRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Approval rule not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(rule, key, value)
    if not rule.approver_user_id and not rule.approver_role_id:
        raise HTTPException(422, "Approval rule requires approver_user_id or approver_role_id")
    await db.commit()
    await db.refresh(rule)
    return rule


def _with_access(row, current_user, record):
    if current_user is not None:
        row.access = svc.build_procurement_access_hint(current_user, record)
    return row


def _build_pr_read(pr: PurchaseRequisition, current_user=None) -> PRRead:
    r = PRRead.model_validate(pr)
    r.requester_name = pr.requester.full_name if pr.requester else None
    r.line_count = len(pr.lines) if pr.lines else 0
    return _with_access(r, current_user, pr)


def _build_pr_detail(pr: PurchaseRequisition, current_user=None) -> PRDetailRead:
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
    return _with_access(r, current_user, pr)


def _build_po_read(po: PurchaseOrder, current_user=None) -> PORead:
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
    return _with_access(r, current_user, po)


def _build_po_detail(po: PurchaseOrder, current_user=None) -> PODetailRead:
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
    return _with_access(r, current_user, po)


def _grn_valuation_status(grn: GoodsReceipt) -> str:
    inventory_lines = [line for line in (grn.lines or []) if line.accepted_quantity > 0]
    if not inventory_lines:
        return "NOT_REQUIRED"
    if all(line.accounting_status == OperationalPostingStatus.POSTED for line in inventory_lines):
        return "POSTED"
    if any(line.accounting_status == OperationalPostingStatus.POSTED for line in inventory_lines):
        return "PARTIAL"
    return "NOT_POSTED"


def _build_grn_read(grn: GoodsReceipt, current_user=None) -> GRNRead:
    r = GRNRead.model_validate(grn)
    r.po_no = grn.po.po_no if grn.po else None
    r.warehouse_name = grn.warehouse.name if grn.warehouse else None
    r.valuation_status = _grn_valuation_status(grn)
    return _with_access(r, current_user, grn)


def _build_grn_detail(grn: GoodsReceipt, current_user=None) -> GRNDetailRead:
    r = GRNDetailRead.model_validate(grn)
    r.valuation_status = _grn_valuation_status(grn)
    r.po_no = grn.po.po_no if grn.po else None
    r.warehouse_name = grn.warehouse.name if grn.warehouse else None
    lines = []
    for l in (grn.lines or []):
        lr = GRNLineRead.model_validate(l)
        lr.material_name = l.material.name if l.material else None
        lr.product_name = l.product.name if l.product else None
        lines.append(lr)
    r.lines = lines
    return _with_access(r, current_user, grn)


def _build_shipment_read(ship: ImportShipment, current_user=None) -> ImportShipmentRead:
    r = ImportShipmentRead.model_validate(ship)
    if ship.po:
        r.po_no = ship.po.po_no
        r.supplier_name = ship.po.supplier.name if ship.po.supplier else None
    return _with_access(r, current_user, ship)


def _build_eval_read(ev: SupplierEvaluation, current_user=None) -> SupplierEvaluationRead:
    r = SupplierEvaluationRead.model_validate(ev)
    r.po_no = ev.po.po_no if ev.po else None
    return _with_access(r, current_user, ev)


# ── RFQ ────────────────────────────────────────────────────────────────────────

@router.get("/rfq/", response_model=List[RFQRead])
async def list_rfqs(
    status: Optional[RFQStatus] = None,
    limit: int = Query(200, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = select(RFQRequest).options(
        selectinload(RFQRequest.responses).selectinload(RFQResponse.line_quotes),
        selectinload(RFQRequest.responses).selectinload(RFQResponse.supplier),
        selectinload(RFQRequest.lines),
    )
    if status:
        q = q.where(RFQRequest.status == status)
    result = await db.execute(q.order_by(RFQRequest.created_at.desc()).limit(limit))
    rfqs = result.scalars().all()
    rfqs = [rfq for rfq in rfqs if _can_view_procurement_record(current_user, rfq)]
    rows = []
    for r in rfqs:
        row = RFQRead.model_validate(r)
        row.awarded_supplier_name = r.awarded_supplier.name if r.awarded_supplier else None
        row.response_count = sum(response.status == RFQResponseStatus.SUBMITTED for response in r.responses)
        row.invited_count = sum(response.invitation_status == RFQInvitationStatus.ISSUED for response in r.responses)
        row.line_count = len(r.lines)
        row.access = svc.build_procurement_access_hint(current_user, r)
        rows.append(row)
    return rows


@router.post("/rfq/", response_model=RFQDetailRead, status_code=201)
async def create_rfq(
    body: RFQCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rfq_data = body.model_dump(exclude={"supplier_ids", "lines"})
    rfq = RFQRequest(**rfq_data, created_by_id=current_user.id)
    _require_procurement_action(current_user, rfq, "create")
    if body.supplier_ids:
        suppliers_result = await db.execute(select(Supplier).where(Supplier.id.in_(body.supplier_ids)))
        suppliers_by_id = {supplier.id: supplier for supplier in suppliers_result.scalars().all()}
        if any(supplier_id not in suppliers_by_id or not suppliers_by_id[supplier_id].is_active for supplier_id in body.supplier_ids):
            raise HTTPException(422, "RFQ invitations may target only existing active suppliers.")
    db.add(rfq)
    await db.flush()
    for line in body.lines:
        db.add(RFQLine(rfq_id=rfq.id, **line.model_dump()))
    for sid in body.supplier_ids:
        resp = RFQResponse(rfq_id=rfq.id, supplier_id=sid)
        db.add(resp)
    await db.commit()
    result = await db.execute(
        select(RFQRequest).options(
            selectinload(RFQRequest.responses).selectinload(RFQResponse.supplier),
            selectinload(RFQRequest.responses).selectinload(RFQResponse.line_quotes),
            selectinload(RFQRequest.responses).selectinload(RFQResponse.evaluations).selectinload(RFQResponseEvaluation.criterion),
            selectinload(RFQRequest.awarded_supplier),
            selectinload(RFQRequest.lines),
            selectinload(RFQRequest.evaluation_criteria),
        ).where(RFQRequest.id == rfq.id)
    )
    rfq = result.scalar_one()
    return _build_rfq_detail(rfq, current_user)


@router.get("/rfq/{rfq_id}", response_model=RFQDetailRead)
async def get_rfq(
    rfq_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(RFQRequest).options(
            selectinload(RFQRequest.responses).selectinload(RFQResponse.supplier),
            selectinload(RFQRequest.responses).selectinload(RFQResponse.line_quotes),
            selectinload(RFQRequest.responses).selectinload(RFQResponse.evaluations).selectinload(RFQResponseEvaluation.criterion),
            selectinload(RFQRequest.awarded_supplier),
            selectinload(RFQRequest.lines),
            selectinload(RFQRequest.evaluation_criteria),
        ).where(RFQRequest.id == rfq_id)
    )
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(404, "RFQ not found")
    _require_procurement_view(current_user, rfq)
    return _build_rfq_detail(rfq, current_user)


@router.patch("/rfq/{rfq_id}", response_model=RFQDetailRead)
async def update_rfq(
    rfq_id: uuid.UUID,
    body: RFQUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(RFQRequest)
        .options(selectinload(RFQRequest.lines))
        .where(RFQRequest.id == rfq_id)
        .with_for_update()
    )
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(404, "RFQ not found")
    _require_procurement_action(current_user, rfq, "edit")
    update_data = body.model_dump(exclude_unset=True)
    if "awarded_supplier_id" in update_data:
        raise HTTPException(409, "The awarded supplier is controlled by an approved award proposal.")
    requested_status = update_data.pop("status", None)
    if requested_status is not None:
        if requested_status == RFQStatus.AWARDED:
            raise HTTPException(409, "RFQ awards require an approved award proposal; use the award-proposals workflow.")
        elif requested_status == RFQStatus.CANCELLED and rfq.status not in {RFQStatus.AWARDED, RFQStatus.CANCELLED}:
            if update_data:
                raise HTTPException(409, "RFQ terms cannot be changed in the same request as lifecycle cancellation.")
            rfq.status = RFQStatus.CANCELLED
        else:
            raise HTTPException(409, "RFQ lifecycle status is server-controlled; use the dedicated issue or award workflow.")
    elif rfq.status != RFQStatus.DRAFT and update_data:
        raise HTTPException(409, "Issued RFQ terms are locked; only a valid lifecycle transition may be applied.")
    for k, v in update_data.items():
        setattr(rfq, k, v)
    await db.commit()
    result = await db.execute(
        select(RFQRequest).options(
            selectinload(RFQRequest.responses).selectinload(RFQResponse.supplier),
            selectinload(RFQRequest.responses).selectinload(RFQResponse.line_quotes),
            selectinload(RFQRequest.responses).selectinload(RFQResponse.evaluations).selectinload(RFQResponseEvaluation.criterion),
            selectinload(RFQRequest.awarded_supplier),
            selectinload(RFQRequest.lines),
            selectinload(RFQRequest.evaluation_criteria),
        ).where(RFQRequest.id == rfq_id)
    )
    return _build_rfq_detail(result.scalar_one(), current_user)


@router.get("/rfq/{rfq_id}/awards", response_model=List[RFQAwardRead])
async def list_rfq_awards(
    rfq_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rfq_result = await db.execute(select(RFQRequest).where(RFQRequest.id == rfq_id))
    rfq = rfq_result.scalar_one_or_none()
    if rfq is None:
        raise HTTPException(404, "RFQ not found")
    _require_procurement_view(current_user, rfq)
    result = await db.execute(
        select(RFQAward)
        .options(selectinload(RFQAward.allocations), selectinload(RFQAward.approvals))
        .where(RFQAward.rfq_id == rfq_id)
        .order_by(RFQAward.revision_no)
    )
    return list(result.scalars().all())


@router.post("/rfq/{rfq_id}/award-proposals", response_model=RFQAwardRead, status_code=201)
async def create_rfq_award_proposal(
    rfq_id: uuid.UUID,
    body: RFQAwardProposalCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rfq_result = await db.execute(
        select(RFQRequest)
        .options(selectinload(RFQRequest.lines), selectinload(RFQRequest.evaluation_criteria))
        .where(RFQRequest.id == rfq_id)
        .with_for_update()
    )
    rfq = rfq_result.scalar_one_or_none()
    if rfq is None:
        raise HTTPException(404, "RFQ not found")
    _require_procurement_action(current_user, rfq, "edit")
    if rfq.status != RFQStatus.RESPONSES_RECEIVED:
        raise HTTPException(409, "Award proposals require an RFQ with submitted responses.")
    pending_proposal = await db.execute(
        select(RFQAward.id)
        .where(RFQAward.rfq_id == rfq.id, RFQAward.status == RFQAwardStatus.PENDING_APPROVAL)
        .limit(1)
    )
    if pending_proposal.scalar_one_or_none() is not None:
        raise HTTPException(409, "Resolve the existing pending award proposal before submitting another revision.")
    if not rfq.lines and rfq.quantity is None:
        raise HTTPException(409, "This RFQ has no single-item quantity to allocate.")

    response_ids = {allocation.response_id for allocation in body.allocations}
    response_result = await db.execute(
        select(RFQResponse)
        .options(
            selectinload(RFQResponse.supplier),
            selectinload(RFQResponse.line_quotes),
        )
        .where(RFQResponse.rfq_id == rfq.id, RFQResponse.id.in_(response_ids))
        .with_for_update()
    )
    responses = {response.id: response for response in response_result.scalars().all()}
    if set(responses) != response_ids:
        raise HTTPException(422, "Every allocation must reference a bid belonging to this RFQ.")

    rfq_lines = {line.id: line for line in rfq.lines}
    allocated_quantities: dict[uuid.UUID | None, Decimal] = {}
    total_amount = Decimal("0")
    currency = None
    allocations = []
    for requested_allocation in body.allocations:
        if rfq_lines and requested_allocation.rfq_line_id not in rfq_lines:
            raise HTTPException(422, "Every multi-line allocation must name one of this RFQ's lines.")
        if not rfq_lines and requested_allocation.rfq_line_id is not None:
            raise HTTPException(422, "Single-item RFQ allocations must not name a line ID.")
        response = responses[requested_allocation.response_id]
        if response.status != RFQResponseStatus.SUBMITTED:
            raise HTTPException(409, "Only submitted bids can receive an award allocation.")
        if not response.supplier or not response.supplier.is_active:
            raise HTTPException(409, "An inactive or missing supplier cannot receive an award.")
        if response.valid_until is not None and response.valid_until < date.today():
            raise HTTPException(409, "An expired bid cannot receive an award.")
        if rfq.evaluation_criteria and response.evaluation_status != RFQEvaluationStatus.QUALIFIED:
            raise HTTPException(409, "RFQs with an evaluation matrix can award only qualified bids.")
        if requested_allocation.rfq_line_id is not None:
            line_quote = next(
                (quote for quote in response.line_quotes if quote.rfq_line_id == requested_allocation.rfq_line_id),
                None,
            )
            if line_quote is None:
                raise HTTPException(409, "Every awarded multi-line bid must contain an itemized quote for its RFQ line.")
            unit_price = Decimal(str(line_quote.quoted_unit_price))
            response_currency = line_quote.quoted_currency
        else:
            if response.quoted_unit_price is None:
                raise HTTPException(409, "Every awarded bid must include a quoted unit price.")
            unit_price = Decimal(str(response.quoted_unit_price))
            response_currency = response.quoted_currency
        if currency is None:
            currency = response_currency
        elif currency != response_currency:
            raise HTTPException(409, "Award allocations must use one currency; no exchange rate is configured.")
        quantity = requested_allocation.quantity
        line_id = requested_allocation.rfq_line_id
        allocated_quantities[line_id] = allocated_quantities.get(line_id, Decimal("0")) + quantity
        total_amount += unit_price * quantity
        allocations.append((response, line_id, quantity))

    expected_quantities = (
        {line_id: Decimal(str(line.quantity)) for line_id, line in rfq_lines.items()}
        if rfq_lines
        else {None: Decimal(str(rfq.quantity))}
    )
    if allocated_quantities != expected_quantities:
        raise HTTPException(
            422,
            "Award allocations must fully and exactly cover each RFQ item quantity; partial or excess awards are not allowed.",
        )

    # The configured RFQ rules own amount thresholds. Do not invent a default
    # threshold or silently bypass approval when no applicable rule exists.
    rules = await svc.find_procurement_approval_rules(
        db, ProcurementApprovalDocumentType.RFQ, rfq, total_amount, currency
    )
    product_categories = set()
    if rfq.product_id is not None:
        product_category = (
            await db.execute(select(Product.category).where(Product.id == rfq.product_id))
        ).scalar_one_or_none()
        if product_category is not None:
            product_categories.add(getattr(product_category, "value", product_category))
    elif rfq.lines:
        product_ids = {line.product_id for line in rfq.lines if line.product_id is not None}
        if product_ids:
            product_categories.update(
                getattr(category, "value", category)
                for category in (
                    await db.execute(select(Product.category).where(Product.id.in_(product_ids)))
                ).scalars().all()
            )
    matching_rules = []
    allocated_categories = {response.supplier.supplier_category for response, _, _ in allocations}
    for rule in rules:
        if rule.supplier_category and rule.supplier_category not in allocated_categories:
            continue
        if rule.product_category and rule.product_category not in product_categories:
            continue
        if rule.currency is None and (rule.min_amount is not None or rule.max_amount is not None):
            raise HTTPException(
                409,
                f"RFQ award rule '{rule.rule_name}' sets amount limits without a currency; configure its currency before awarding.",
            )
        matching_rules.append(rule)
    if not matching_rules:
        raise HTTPException(409, "No active RFQ award approval rule matches this RFQ, scope, and award amount.")

    approval_assignments = []
    for rule in matching_rules:
        approver_ids = set()
        if rule.approver_user_id is not None:
            assigned = (
                await db.execute(
                    select(User)
                    .options(
                        selectinload(User.roles).selectinload(Role.permissions),
                        selectinload(User.roles).selectinload(Role.access_scopes),
                        selectinload(User.access_scopes),
                    )
                    .where(User.id == rule.approver_user_id, User.is_active.is_(True))
                )
            ).scalar_one_or_none()
            if assigned is not None and svc.can_modify_record(assigned, "procurement", "approve", rfq):
                approver_ids.add(assigned.id)
        if rule.approver_role_id is not None:
            role = (
                await db.execute(
                    select(Role)
                    .options(
                        selectinload(Role.users).selectinload(User.roles).selectinload(Role.permissions),
                        selectinload(Role.users).selectinload(User.roles).selectinload(Role.access_scopes),
                        selectinload(Role.users).selectinload(User.access_scopes),
                    )
                    .where(Role.id == rule.approver_role_id, Role.is_active.is_(True))
                )
            ).scalar_one_or_none()
            if role is not None:
                approver_ids.update(
                    assigned.id for assigned in role.users
                    if assigned.is_active
                    and svc.can_modify_record(assigned, "procurement", "approve", rfq)
                )
        # Enforce separation of duties for the proposal author.
        approver_ids.discard(current_user.id)
        if not approver_ids:
            raise HTTPException(
                409,
                f"RFQ approval rule '{rule.rule_name}' has no active, scoped approver other than the proposal author.",
            )
        approval_assignments.extend((rule, approver_id) for approver_id in approver_ids)

    next_revision = (
        await db.execute(
            select(func.coalesce(func.max(RFQAward.revision_no), 0)).where(RFQAward.rfq_id == rfq.id)
        )
    ).scalar_one() + 1
    award = RFQAward(
        rfq_id=rfq.id,
        revision_no=next_revision,
        status=RFQAwardStatus.PENDING_APPROVAL,
        total_amount=total_amount,
        currency=currency,
        justification=body.justification,
        requested_by_id=current_user.id,
        requested_at=datetime.now(timezone.utc),
    )
    db.add(award)
    await db.flush()

    for response, line_id, quantity in allocations:
        db.add(
            RFQAwardAllocation(
                award_id=award.id,
                response_id=response.id,
                rfq_line_id=line_id,
                quantity=quantity,
            )
        )

    approval_rows = [
        RFQAwardApproval(
            award_id=award.id,
            approval_rule_id=rule.id,
            approval_level=rule.approval_level,
            rule_name=rule.rule_name,
            requires_all_matching_approvers=rule.requires_all_matching_approvers,
            approver_user_id=approver_id,
            decision_status=RFQAwardApprovalStatus.PENDING,
        )
        for rule, approver_id in approval_assignments
    ]
    db.add_all(approval_rows)
    await db.commit()
    result = await db.execute(
        select(RFQAward)
        .options(selectinload(RFQAward.allocations), selectinload(RFQAward.approvals))
        .where(RFQAward.id == award.id)
    )
    return result.scalar_one()


async def _load_award_for_decision(db: AsyncSession, rfq_id: uuid.UUID, award_id: uuid.UUID):
    rfq_result = await db.execute(
        select(RFQRequest).where(RFQRequest.id == rfq_id).with_for_update()
    )
    rfq = rfq_result.scalar_one_or_none()
    if rfq is None:
        raise HTTPException(404, "RFQ not found")
    award_result = await db.execute(
        select(RFQAward)
        .options(selectinload(RFQAward.allocations), selectinload(RFQAward.approvals))
        .where(RFQAward.id == award_id, RFQAward.rfq_id == rfq_id)
        .with_for_update()
    )
    award = award_result.scalar_one_or_none()
    if award is None:
        raise HTTPException(404, "Award proposal not found")
    if award.status != RFQAwardStatus.PENDING_APPROVAL:
        raise HTTPException(409, "Only pending award proposals can be decided.")
    return rfq, award


async def _record_rfq_award_decision(
    rfq: RFQRequest,
    award: RFQAward,
    current_user,
    decision: RFQAwardApprovalStatus,
    comments: Optional[str],
    db: AsyncSession,
) -> RFQAwardRead:
    pending = [row for row in award.approvals if row.decision_status == RFQAwardApprovalStatus.PENDING]
    if not pending:
        raise HTTPException(409, "Award proposal has no pending configured approval step.")
    current_level = min(row.approval_level for row in pending)
    vote = next(
        (
            row for row in pending
            if row.approval_level == current_level and row.approver_user_id == current_user.id
        ),
        None,
    )
    if vote is None:
        raise HTTPException(403, detail=forbidden_detail("This user is not an assigned approver for the current RFQ award step."))

    now = datetime.now(timezone.utc)
    vote.decision_status = decision
    vote.decided_by_id = current_user.id
    vote.decided_at = now
    vote.comments = comments.strip() if comments else None

    if decision == RFQAwardApprovalStatus.REJECTED:
        award.status = RFQAwardStatus.REJECTED
        award.decided_at = now
        for sibling in award.approvals:
            if sibling.decision_status == RFQAwardApprovalStatus.PENDING:
                sibling.decision_status = RFQAwardApprovalStatus.SKIPPED
                sibling.decided_by_id = current_user.id
                sibling.decided_at = now
                sibling.comments = f"Skipped after rejection at approval level {current_level}."
    else:
        # A role rule with requires_all=false is satisfied by one assigned
        # approver. Record the remaining role assignments as skipped.
        if not vote.requires_all_matching_approvers:
            for sibling in award.approvals:
                if (
                    sibling.approval_rule_id == vote.approval_rule_id
                    and sibling.id != vote.id
                    and sibling.decision_status == RFQAwardApprovalStatus.PENDING
                ):
                    sibling.decision_status = RFQAwardApprovalStatus.SKIPPED
                    sibling.decided_by_id = current_user.id
                    sibling.decided_at = now
        rules_by_level: dict[int, dict[uuid.UUID, list[RFQAwardApproval]]] = {}
        for row in award.approvals:
            rules_by_level.setdefault(row.approval_level, {}).setdefault(row.approval_rule_id, []).append(row)
        all_approved = all(
            (
                all(row.decision_status == RFQAwardApprovalStatus.APPROVED for row in group)
                if group[0].requires_all_matching_approvers
                else any(row.decision_status == RFQAwardApprovalStatus.APPROVED for row in group)
            )
            for groups in rules_by_level.values()
            for group in groups.values()
        )
        if all_approved:
            award.status = RFQAwardStatus.APPROVED
            award.decided_at = now
            rfq.status = RFQStatus.AWARDED
            allocated_responses = {allocation.response_id for allocation in award.allocations}
            for response_id in allocated_responses:
                (await db.execute(
                    select(RFQResponse).where(RFQResponse.id == response_id).with_for_update()
                )).scalar_one().status = RFQResponseStatus.AWARDED
            unallocated_responses = (await db.execute(
                select(RFQResponse)
                .where(
                    RFQResponse.rfq_id == rfq.id,
                    RFQResponse.status == RFQResponseStatus.SUBMITTED,
                )
                .with_for_update()
            )).scalars().all()
            for response in unallocated_responses:
                if response.id not in allocated_responses:
                    response.status = RFQResponseStatus.REJECTED
            awarded_supplier_ids = {
                (await db.execute(
                    select(RFQResponse.supplier_id).where(RFQResponse.id == response_id)
                )).scalar_one()
                for response_id in allocated_responses
            }
            rfq.awarded_supplier_id = next(iter(awarded_supplier_ids)) if len(awarded_supplier_ids) == 1 else None

    await db.commit()
    result = await db.execute(
        select(RFQAward)
        .options(selectinload(RFQAward.allocations), selectinload(RFQAward.approvals))
        .where(RFQAward.id == award.id)
    )
    return result.scalar_one()


@router.post("/rfq/{rfq_id}/awards/{award_id}/approve", response_model=RFQAwardRead)
async def approve_rfq_award(
    rfq_id: uuid.UUID,
    award_id: uuid.UUID,
    body: RFQAwardDecision,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rfq, award = await _load_award_for_decision(db, rfq_id, award_id)
    _require_procurement_action(current_user, rfq, "approve")
    return await _record_rfq_award_decision(
        rfq, award, current_user, RFQAwardApprovalStatus.APPROVED, body.comments, db
    )


@router.post("/rfq/{rfq_id}/awards/{award_id}/reject", response_model=RFQAwardRead)
async def reject_rfq_award(
    rfq_id: uuid.UUID,
    award_id: uuid.UUID,
    body: RFQAwardDecision,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rfq, award = await _load_award_for_decision(db, rfq_id, award_id)
    _require_procurement_action(current_user, rfq, "approve")
    if not body.comments or len(body.comments.strip()) < 3:
        raise HTTPException(422, "A rejection reason of at least three characters is required.")
    return await _record_rfq_award_decision(
        rfq, award, current_user, RFQAwardApprovalStatus.REJECTED, body.comments, db
    )


@router.post("/rfq/{rfq_id}/issue-invitations", response_model=RFQDetailRead)
async def issue_rfq_invitations(
    rfq_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(RFQRequest)
        .options(
            selectinload(RFQRequest.responses).selectinload(RFQResponse.supplier),
            selectinload(RFQRequest.responses).selectinload(RFQResponse.line_quotes),
            selectinload(RFQRequest.responses).selectinload(RFQResponse.evaluations).selectinload(RFQResponseEvaluation.criterion),
            selectinload(RFQRequest.awarded_supplier),
            selectinload(RFQRequest.lines),
            selectinload(RFQRequest.evaluation_criteria),
        )
        .where(RFQRequest.id == rfq_id)
        .with_for_update()
    )
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(404, "RFQ not found")
    _require_procurement_action(current_user, rfq, "edit")
    if rfq.status != RFQStatus.DRAFT:
        raise HTTPException(409, "Only a draft RFQ can be issued; invitations are not re-sent implicitly.")
    if not rfq.responses:
        raise HTTPException(409, "Select at least one supplier before issuing this RFQ.")
    inactive = [response.supplier_id for response in rfq.responses if not response.supplier or not response.supplier.is_active]
    if inactive:
        raise HTTPException(409, "All invited suppliers must exist and be active.")
    issued_at = datetime.now(timezone.utc)
    for response in rfq.responses:
        response.invitation_status = RFQInvitationStatus.ISSUED
        response.invitation_issued_at = issued_at
        response.invitation_issued_by_id = current_user.id
    rfq.status = RFQStatus.SENT
    await db.commit()
    return _build_rfq_detail(rfq, current_user)


@router.post("/rfq/{rfq_id}/responses", response_model=RFQResponseRead, status_code=201)
async def add_rfq_response(
    rfq_id: uuid.UUID,
    body: RFQResponseCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(RFQRequest)
        .options(selectinload(RFQRequest.lines))
        .where(RFQRequest.id == rfq_id)
        .with_for_update()
    )
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(404, "RFQ not found")
    _require_procurement_action(current_user, rfq, "edit")
    if rfq.status not in {RFQStatus.SENT, RFQStatus.RESPONSES_RECEIVED}:
        raise HTTPException(409, "Bids can be recorded only after an RFQ has been issued to suppliers.")
    if rfq.response_deadline and rfq.response_deadline < date.today():
        raise HTTPException(409, "The supplier response deadline has passed.")
    existing = await db.execute(
        select(RFQResponse).where(
            RFQResponse.rfq_id == rfq_id,
            RFQResponse.supplier_id == body.supplier_id,
        ).with_for_update()
    )
    resp = existing.scalar_one_or_none()
    if not resp or resp.invitation_status != RFQInvitationStatus.ISSUED:
        raise HTTPException(403, "This supplier was not invited to the RFQ.")
    if resp.status != RFQResponseStatus.PENDING:
        raise HTTPException(409, "A bid is already recorded for this supplier; submitted bids are immutable.")
    supplier = await db.get(Supplier, body.supplier_id)
    if not supplier or not supplier.is_active:
        raise HTTPException(409, "The invited supplier is no longer active.")
    rfq_line_ids = {line.id for line in rfq.lines}
    quoted_line_ids = {quote.rfq_line_id for quote in body.line_quotes}
    if rfq.lines:
        if body.quoted_unit_price is not None or quoted_line_ids != rfq_line_ids:
            raise HTTPException(422, "A multi-line RFQ requires exactly one itemized price for every RFQ line.")
    elif body.line_quotes or body.quoted_unit_price is None:
        raise HTTPException(422, "A single-item RFQ requires one unit price and does not accept line quotes.")
    for key, value in body.model_dump(exclude={"supplier_id", "line_quotes"}).items():
        setattr(resp, key, value)
    for quote in body.line_quotes:
        db.add(
            RFQResponseLineQuote(
                response_id=resp.id,
                rfq_line_id=quote.rfq_line_id,
                quoted_unit_price=quote.quoted_unit_price,
                quoted_currency=quote.quoted_currency,
            )
        )
    resp.status = RFQResponseStatus.SUBMITTED
    resp.submitted_at = datetime.now(timezone.utc)
    resp.submitted_by_id = current_user.id
    rfq.status = RFQStatus.RESPONSES_RECEIVED
    await db.commit()
    resp = (
        await db.execute(
            select(RFQResponse)
            .options(selectinload(RFQResponse.line_quotes))
            .where(RFQResponse.id == resp.id)
        )
    ).scalar_one()
    rr = _build_rfq_response_read(resp)
    supplier_result = await db.execute(select(Supplier).where(Supplier.id == resp.supplier_id))
    s = supplier_result.scalar_one_or_none()
    rr.supplier_name = s.name if s else None
    return rr


@router.post("/rfq/{rfq_id}/evaluation-matrix", response_model=List[RFQEvaluationCriterionRead])
async def create_rfq_evaluation_matrix(
    rfq_id: uuid.UUID,
    body: RFQEvaluationMatrixCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(RFQRequest).where(RFQRequest.id == rfq_id).with_for_update())
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(404, "RFQ not found")
    _require_procurement_action(current_user, rfq, "edit")
    if rfq.status != RFQStatus.SENT:
        raise HTTPException(409, "Configure the evaluation matrix after issuing invitations and before the first bid is received.")
    existing = await db.execute(
        select(RFQEvaluationCriterion.id).where(RFQEvaluationCriterion.rfq_id == rfq_id).limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(409, "The RFQ evaluation matrix already exists and is immutable.")
    criteria = [
        RFQEvaluationCriterion(rfq_id=rfq_id, created_by_id=current_user.id, **item.model_dump())
        for item in body.criteria
    ]
    db.add_all(criteria)
    await db.commit()
    return [RFQEvaluationCriterionRead.model_validate(item) for item in criteria]


@router.put(
    "/rfq/{rfq_id}/responses/{response_id}/evaluations",
    response_model=List[RFQResponseEvaluationRead],
)
async def submit_rfq_response_evaluations(
    rfq_id: uuid.UUID,
    response_id: uuid.UUID,
    body: RFQResponseEvaluationSubmit,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rfq_result = await db.execute(select(RFQRequest).where(RFQRequest.id == rfq_id).with_for_update())
    rfq = rfq_result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(404, "RFQ not found")
    _require_procurement_action(current_user, rfq, "edit")
    if rfq.status != RFQStatus.RESPONSES_RECEIVED:
        raise HTTPException(409, "Only an open RFQ with submitted bids can be evaluated.")

    response_result = await db.execute(
        select(RFQResponse)
        .where(RFQResponse.id == response_id, RFQResponse.rfq_id == rfq_id)
        .with_for_update()
    )
    response = response_result.scalar_one_or_none()
    if not response or response.status != RFQResponseStatus.SUBMITTED:
        raise HTTPException(404, "Submitted supplier bid not found for this RFQ.")

    criteria_result = await db.execute(
        select(RFQEvaluationCriterion)
        .where(RFQEvaluationCriterion.rfq_id == rfq_id)
        .order_by(RFQEvaluationCriterion.code)
    )
    criteria = criteria_result.scalars().all()
    if not criteria:
        raise HTTPException(409, "Configure a technical/commercial evaluation matrix before scoring bids.")
    criterion_ids = {criterion.id for criterion in criteria}
    supplied_ids = {item.criterion_id for item in body.evaluations}
    if supplied_ids != criterion_ids:
        raise HTTPException(422, "Each matrix criterion must be scored exactly once in one evaluation revision.")
    criteria_by_id = {criterion.id: criterion for criterion in criteria}
    inputs_by_id = {item.criterion_id: item for item in body.evaluations}
    for criterion in criteria:
        submitted = inputs_by_id[criterion.id]
        if criterion.is_mandatory and submitted.passes_gate is None:
            raise HTTPException(422, f"Mandatory criterion {criterion.code} requires an explicit pass/fail decision.")
        if not criterion.is_mandatory and submitted.passes_gate is not None:
            raise HTTPException(422, f"Non-mandatory criterion {criterion.code} must not carry a gate decision.")

    latest_revision_result = await db.execute(
        select(RFQResponseEvaluation.criterion_id, func.max(RFQResponseEvaluation.revision_no))
        .where(RFQResponseEvaluation.response_id == response.id)
        .group_by(RFQResponseEvaluation.criterion_id)
    )
    revision_by_criterion = {criterion_id: (revision or 0) for criterion_id, revision in latest_revision_result.all()}
    evaluated_at = datetime.now(timezone.utc)
    evaluation_rows = []
    weighted_total = Decimal("0")
    failed_gate = False
    for criterion_id, item in inputs_by_id.items():
        criterion = criteria_by_id[criterion_id]
        revision_no = revision_by_criterion.get(criterion_id, 0) + 1
        evaluation_rows.append(
            RFQResponseEvaluation(
                response_id=response.id,
                criterion_id=criterion_id,
                revision_no=revision_no,
                score=item.score,
                passes_gate=item.passes_gate,
                comments=item.comments,
                evaluator_id=current_user.id,
                evaluated_at=evaluated_at,
            )
        )
        weighted_total += item.score * criterion.weight_percent / Decimal("100")
        failed_gate = failed_gate or (criterion.is_mandatory and item.passes_gate is False)
    db.add_all(evaluation_rows)
    response.score = weighted_total.quantize(Decimal("0.01"))
    response.evaluation_status = (
        RFQEvaluationStatus.DISQUALIFIED if failed_gate else RFQEvaluationStatus.QUALIFIED
    )
    await db.commit()

    persisted = await db.execute(
        select(RFQResponseEvaluation)
        .options(selectinload(RFQResponseEvaluation.criterion))
        .where(RFQResponseEvaluation.response_id == response.id)
        .order_by(RFQResponseEvaluation.criterion_id, RFQResponseEvaluation.revision_no)
    )
    history = persisted.scalars().all()
    return [_build_evaluation_read(item) for item in history]


def _build_evaluation_read(evaluation: RFQResponseEvaluation) -> RFQResponseEvaluationRead:
    row = RFQResponseEvaluationRead.model_validate(evaluation)
    row.criterion_code = evaluation.criterion.code
    row.criterion_name = evaluation.criterion.name
    row.dimension = evaluation.criterion.dimension
    row.weight_percent = evaluation.criterion.weight_percent
    return row


def _build_rfq_response_read(response: RFQResponse) -> RFQResponseRead:
    fields = (
        "id",
        "rfq_id",
        "supplier_id",
        "quoted_unit_price",
        "quoted_currency",
        "lead_time_days",
        "valid_until",
        "payment_terms",
        "notes",
        "status",
        "invitation_status",
        "invitation_issued_at",
        "invitation_issued_by_id",
        "submitted_at",
        "submitted_by_id",
        "evaluation_status",
        "score",
        "created_at",
    )
    return RFQResponseRead(
        **{field: getattr(response, field) for field in fields},
        line_quotes=[RFQResponseLineQuoteRead.model_validate(item) for item in response.line_quotes],
    )


def _build_rfq_detail(rfq: RFQRequest, current_user=None) -> RFQDetailRead:
    r = RFQDetailRead.model_validate(rfq)
    r.awarded_supplier_name = rfq.awarded_supplier.name if rfq.awarded_supplier else None
    r.response_count = sum(response.status == RFQResponseStatus.SUBMITTED for response in rfq.responses)
    r.invited_count = sum(response.invitation_status == RFQInvitationStatus.ISSUED for response in rfq.responses)
    r.line_count = len(rfq.lines)
    responses = []
    for resp in rfq.responses:
        rr = _build_rfq_response_read(resp)
        rr.supplier_name = resp.supplier.name if resp.supplier else None
        latest_by_criterion = {}
        for evaluation in resp.evaluations:
            previous = latest_by_criterion.get(evaluation.criterion_id)
            if previous is None or evaluation.revision_no > previous.revision_no:
                latest_by_criterion[evaluation.criterion_id] = evaluation
        rr.evaluations = [_build_evaluation_read(item) for item in latest_by_criterion.values()]
        rr.evaluation_history = [_build_evaluation_read(item) for item in resp.evaluations]
        responses.append(rr)
    r.responses = responses
    r.lines = [RFQLineRead.model_validate(line) for line in rfq.lines]
    r.evaluation_criteria = [RFQEvaluationCriterionRead.model_validate(item) for item in rfq.evaluation_criteria]
    return _with_access(r, current_user, rfq)


# ── Blanket Purchase Agreements ───────────────────────────────────────────────

@router.get("/bpa/", response_model=List[BlanketAgreementRead])
async def list_bpas(
    supplier_id: Optional[uuid.UUID] = None,
    status: Optional[BPAStatus] = None,
    limit: int = Query(200, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = select(BlanketPurchaseAgreement).options(
        selectinload(BlanketPurchaseAgreement.supplier)
    )
    if supplier_id:
        q = q.where(BlanketPurchaseAgreement.supplier_id == supplier_id)
    if status:
        q = q.where(BlanketPurchaseAgreement.status == status)
    result = await db.execute(q.order_by(BlanketPurchaseAgreement.valid_to.desc()).limit(limit))
    bpas = result.scalars().all()
    bpas = [b for b in bpas if _can_view_procurement_record(current_user, b)]
    rows = []
    for b in bpas:
        row = BlanketAgreementRead.model_validate(b)
        row.supplier_name = b.supplier.name if b.supplier else None
        row.access = svc.build_procurement_access_hint(current_user, b)
        rows.append(row)
    return rows


@router.post("/bpa/", response_model=BlanketAgreementRead, status_code=201)
async def create_bpa(
    body: BlanketAgreementCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    bpa = BlanketPurchaseAgreement(**body.model_dump(), created_by_id=current_user.id)
    _require_procurement_action(current_user, bpa, "create")
    db.add(bpa)
    await db.commit()
    await db.refresh(bpa)
    result = await db.execute(
        select(BlanketPurchaseAgreement).options(
            selectinload(BlanketPurchaseAgreement.supplier)
        ).where(BlanketPurchaseAgreement.id == bpa.id)
    )
    bpa = result.scalar_one()
    row = BlanketAgreementRead.model_validate(bpa)
    row.supplier_name = bpa.supplier.name if bpa.supplier else None
    row.access = svc.build_procurement_access_hint(current_user, bpa)
    return row


@router.patch("/bpa/{bpa_id}", response_model=BlanketAgreementRead)
async def update_bpa(
    bpa_id: uuid.UUID,
    body: BlanketAgreementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(BlanketPurchaseAgreement).options(
            selectinload(BlanketPurchaseAgreement.supplier)
        ).where(BlanketPurchaseAgreement.id == bpa_id)
    )
    bpa = result.scalar_one_or_none()
    if not bpa:
        raise HTTPException(404, "Agreement not found")
    _require_procurement_action(current_user, bpa, "edit")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(bpa, k, v)
    await db.commit()
    await db.refresh(bpa)
    row = BlanketAgreementRead.model_validate(bpa)
    row.supplier_name = bpa.supplier.name if bpa.supplier else None
    row.access = svc.build_procurement_access_hint(current_user, bpa)
    return row


# ── Auto Reorder Policies ─────────────────────────────────────────────────────

@router.get("/reorder-policies/", response_model=List[AutoReorderPolicyRead])
async def list_reorder_policies(
    active_only: bool = False,
    limit: int = Query(200, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = select(AutoReorderPolicy).options(
        selectinload(AutoReorderPolicy.preferred_supplier)
    )
    if active_only:
        q = q.where(AutoReorderPolicy.active_flag == True)
    result = await db.execute(q.order_by(AutoReorderPolicy.created_at.desc()).limit(limit))
    policies = result.scalars().all()
    policies = [p for p in policies if _can_view_procurement_record(current_user, p)]
    rows = []
    for p in policies:
        row = AutoReorderPolicyRead.model_validate(p)
        row.preferred_supplier_name = p.preferred_supplier.name if p.preferred_supplier else None
        row.access = svc.build_procurement_access_hint(current_user, p)
        rows.append(row)
    return rows


@router.post("/reorder-policies/", response_model=AutoReorderPolicyRead, status_code=201)
async def create_reorder_policy(
    body: AutoReorderPolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    policy = AutoReorderPolicy(**body.model_dump())
    _require_procurement_action(current_user, policy, "create")
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    result = await db.execute(
        select(AutoReorderPolicy).options(
            selectinload(AutoReorderPolicy.preferred_supplier)
        ).where(AutoReorderPolicy.id == policy.id)
    )
    policy = result.scalar_one()
    row = AutoReorderPolicyRead.model_validate(policy)
    row.preferred_supplier_name = policy.preferred_supplier.name if policy.preferred_supplier else None
    row.access = svc.build_procurement_access_hint(current_user, policy)
    return row


@router.patch("/reorder-policies/{policy_id}", response_model=AutoReorderPolicyRead)
async def update_reorder_policy(
    policy_id: uuid.UUID,
    body: AutoReorderPolicyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(AutoReorderPolicy).options(
            selectinload(AutoReorderPolicy.preferred_supplier)
        ).where(AutoReorderPolicy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(404, "Reorder policy not found")
    _require_procurement_action(current_user, policy, "edit")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(policy, k, v)
    await db.commit()
    await db.refresh(policy)
    row = AutoReorderPolicyRead.model_validate(policy)
    row.preferred_supplier_name = policy.preferred_supplier.name if policy.preferred_supplier else None
    row.access = svc.build_procurement_access_hint(current_user, policy)
    return row


@router.delete("/reorder-policies/{policy_id}")
async def delete_reorder_policy(
    policy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(AutoReorderPolicy).where(AutoReorderPolicy.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(404, "Reorder policy not found")
    _require_procurement_action(current_user, policy, "delete")
    await db.delete(policy)
    await db.commit()
    return {"ok": True}
