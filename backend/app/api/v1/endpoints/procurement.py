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
from app.core.access_control import (
    forbidden_detail,
    has_any_permission,
    require_any_permission,
)
from app.models.procurement import (
    PurchaseRequisition, PRLine, PurchaseOrder, POLine,
    GoodsReceipt, GRNLine, ImportShipment, SupplierEvaluation,
    RFQRequest, RFQResponse, BlanketPurchaseAgreement, AutoReorderPolicy,
    ProcurementApprovalRule,
    PRStatus, POStatus, RFQStatus, RFQResponseStatus, BPAStatus,
)
from decimal import Decimal as _Decimal
from app.models.master import Supplier
from app.schemas.procurement import (
    PRCreate, PRUpdate, PRRead, PRDetailRead, PRLineCreate, PRLineRead,
    ApprovePRRequest, ConvertPRToPORequest,
    POCreate, POUpdate, PORead, PODetailRead, POLineCreate, POLineRead,
    GRNCreate, GRNRead, GRNDetailRead, GRNLineRead,
    ImportShipmentCreate, ImportShipmentUpdate, ImportShipmentRead,
    SupplierEvaluationCreate, SupplierEvaluationRead, SupplierDashboardRow,
    InboundScheduleRow, DeliveryAlertRow,
    SupplierPaymentCreate, SupplierPaymentRead,
    RFQCreate, RFQUpdate, RFQRead, RFQDetailRead, RFQResponseCreate, RFQResponseRead,
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


@router.post("/grn/{grn_id}/post", response_model=GRNDetailRead)
async def post_grn(grn_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    grn = await crud.get_grn(db, grn_id)
    if not grn:
        raise HTTPException(404, "GRN not found")
    _require_procurement_action(current_user, grn, "post")
    grn = await svc.post_grn(db, grn, current_user.id)
    await db.commit()
    grn = await crud.get_grn(db, grn_id)
    return _build_grn_detail(grn, current_user)


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


def _build_grn_read(grn: GoodsReceipt, current_user=None) -> GRNRead:
    r = GRNRead.model_validate(grn)
    r.po_no = grn.po.po_no if grn.po else None
    r.warehouse_name = grn.warehouse.name if grn.warehouse else None
    return _with_access(r, current_user, grn)


def _build_grn_detail(grn: GoodsReceipt, current_user=None) -> GRNDetailRead:
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
    q = select(RFQRequest).options(selectinload(RFQRequest.responses))
    if status:
        q = q.where(RFQRequest.status == status)
    result = await db.execute(q.order_by(RFQRequest.created_at.desc()).limit(limit))
    rfqs = result.scalars().all()
    rfqs = [rfq for rfq in rfqs if _can_view_procurement_record(current_user, rfq)]
    rows = []
    for r in rfqs:
        row = RFQRead.model_validate(r)
        row.awarded_supplier_name = r.awarded_supplier.name if r.awarded_supplier else None
        row.response_count = len(r.responses)
        row.access = svc.build_procurement_access_hint(current_user, r)
        rows.append(row)
    return rows


@router.post("/rfq/", response_model=RFQDetailRead, status_code=201)
async def create_rfq(
    body: RFQCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rfq_data = body.model_dump(exclude={"supplier_ids"})
    rfq = RFQRequest(**rfq_data, created_by_id=current_user.id)
    _require_procurement_action(current_user, rfq, "create")
    db.add(rfq)
    await db.flush()
    for sid in body.supplier_ids:
        resp = RFQResponse(rfq_id=rfq.id, supplier_id=sid)
        db.add(resp)
    await db.commit()
    result = await db.execute(
        select(RFQRequest).options(
            selectinload(RFQRequest.responses).selectinload(RFQResponse.supplier),
            selectinload(RFQRequest.awarded_supplier),
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
            selectinload(RFQRequest.awarded_supplier),
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
    result = await db.execute(select(RFQRequest).where(RFQRequest.id == rfq_id))
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(404, "RFQ not found")
    _require_procurement_action(current_user, rfq, "edit")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(rfq, k, v)
    await db.commit()
    result = await db.execute(
        select(RFQRequest).options(
            selectinload(RFQRequest.responses).selectinload(RFQResponse.supplier),
            selectinload(RFQRequest.awarded_supplier),
        ).where(RFQRequest.id == rfq_id)
    )
    return _build_rfq_detail(result.scalar_one(), current_user)


@router.post("/rfq/{rfq_id}/responses", response_model=RFQResponseRead, status_code=201)
async def add_rfq_response(
    rfq_id: uuid.UUID,
    body: RFQResponseCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(RFQRequest).where(RFQRequest.id == rfq_id))
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(404, "RFQ not found")
    _require_procurement_action(current_user, rfq, "edit")
    existing = await db.execute(
        select(RFQResponse).where(
            RFQResponse.rfq_id == rfq_id,
            RFQResponse.supplier_id == body.supplier_id,
        )
    )
    resp = existing.scalar_one_or_none()
    if resp:
        for k, v in body.model_dump(exclude_unset=True).items():
            setattr(resp, k, v)
        resp.status = RFQResponseStatus.SUBMITTED
    else:
        resp = RFQResponse(**body.model_dump(), rfq_id=rfq_id, status=RFQResponseStatus.SUBMITTED)
        db.add(resp)
    if rfq.status == RFQStatus.SENT:
        rfq.status = RFQStatus.RESPONSES_RECEIVED
    await db.commit()
    await db.refresh(resp)
    rr = RFQResponseRead.model_validate(resp)
    supplier_result = await db.execute(select(Supplier).where(Supplier.id == resp.supplier_id))
    s = supplier_result.scalar_one_or_none()
    rr.supplier_name = s.name if s else None
    return rr


def _build_rfq_detail(rfq: RFQRequest, current_user=None) -> RFQDetailRead:
    r = RFQDetailRead.model_validate(rfq)
    r.awarded_supplier_name = rfq.awarded_supplier.name if rfq.awarded_supplier else None
    r.response_count = len(rfq.responses)
    responses = []
    for resp in rfq.responses:
        rr = RFQResponseRead.model_validate(resp)
        rr.supplier_name = resp.supplier.name if resp.supplier else None
        responses.append(rr)
    r.responses = responses
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
