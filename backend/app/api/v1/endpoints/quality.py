from __future__ import annotations

from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.deps import get_current_user, get_db
from app.core.access_control import (
    can_modify_scope,
    can_view_scope,
    forbidden_detail,
    has_any_permission,
    require_any_permission,
)
from app.models.quality import QCInspection, QCTestResult, QCParameter, QCType, QCStatus
from app.models.master import Supplier, Material, Product
from app.schemas.quality import (
    QCParameterCreate, QCParameterUpdate, QCParameterRead,
    QCTestResultCreate, QCTestResultRead,
    QCInspectionCreate, QCInspectionUpdate, QCInspectionRead, QCInspectionDetailRead,
    QCDecisionRequest,
    COAReport, RejectionSummaryRow,
)
from app.crud import quality as crud
from app.services import quality_service as svc

router = APIRouter()

QUALITY_VIEW_PERMISSIONS = (
    "quality.view",
    "quality.view_all",
    "quality.view_own_scope",
)


def _quality_forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=403, detail=forbidden_detail(detail))


def _has_broad_quality_view(user) -> bool:
    return has_any_permission(user, ("quality.view", "quality.view_all"))


def _product_category(product) -> str | None:
    category = getattr(product, "category", None)
    if category is None:
        return None
    return str(getattr(category, "value", category))


def _quality_scopes(inspection: QCInspection) -> list[tuple[str, str]]:
    scopes: list[tuple[str, str]] = []
    warehouse_id = getattr(inspection, "warehouse_id", None)
    if warehouse_id:
        scopes.append(("warehouse", str(warehouse_id)))
    category = _product_category(getattr(inspection, "product", None))
    if category:
        scopes.append(("product_category", category))
    return list(dict.fromkeys(scopes))


def _can_view_inspection(user, inspection: QCInspection) -> bool:
    if _has_broad_quality_view(user):
        return True
    return any(can_view_scope(user, "quality", scope_type, scope_id) for scope_type, scope_id in _quality_scopes(inspection))


def _require_inspection_view(user, inspection: QCInspection) -> None:
    if not _can_view_inspection(user, inspection):
        raise _quality_forbidden("You can view quality records only inside your assigned quality scope.")


def _require_inspection_action(user, inspection: QCInspection, action: str) -> None:
    if has_any_permission(user, (f"quality.{action}_all",)):
        return
    if any(can_modify_scope(user, "quality", action, scope_type, scope_id) for scope_type, scope_id in _quality_scopes(inspection)):
        return
    raise _quality_forbidden("You can view this quality record but cannot modify it in this scope.")


# ── QC Parameters ─────────────────────────────────────────────────────────────

@router.get("/parameters/", response_model=List[QCParameterRead])
async def list_parameters(
    qc_type: Optional[QCType] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await crud.list_parameters(db, qc_type=qc_type, active_only=active_only)


@router.post("/parameters/", response_model=QCParameterRead, status_code=201)
async def create_parameter(
    body: QCParameterCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    p = await crud.create_parameter(db, body.model_dump())
    await db.commit()
    return p


@router.get("/parameters/{param_id}", response_model=QCParameterRead)
async def get_parameter(param_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    p = await crud.get_parameter(db, param_id)
    if not p:
        raise HTTPException(404, "Parameter not found")
    return p


@router.patch("/parameters/{param_id}", response_model=QCParameterRead)
async def update_parameter(
    param_id: uuid.UUID,
    body: QCParameterUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    p = await crud.get_parameter(db, param_id)
    if not p:
        raise HTTPException(404, "Parameter not found")
    p = await crud.update_parameter(db, p, body.model_dump(exclude_unset=True))
    await db.commit()
    return p


@router.delete("/parameters/{param_id}", status_code=204)
async def delete_parameter(
    param_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from fastapi import Response
    p = await crud.get_parameter(db, param_id)
    if not p:
        raise HTTPException(404, "Parameter not found")
    await db.delete(p)
    await db.commit()
    return Response(status_code=204)


# ── QC Inspections ────────────────────────────────────────────────────────────

@router.get("/inspections/", response_model=List[QCInspectionRead])
async def list_inspections(
    qc_type: Optional[QCType] = None,
    status: Optional[QCStatus] = None,
    supplier_id: Optional[uuid.UUID] = None,
    material_id: Optional[uuid.UUID] = None,
    product_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_any_permission(QUALITY_VIEW_PERMISSIONS)),
):
    inspections = await crud.list_inspections(
        db, qc_type=qc_type, status=status,
        supplier_id=supplier_id, material_id=material_id, product_id=product_id,
    )
    if not _has_broad_quality_view(current_user):
        inspections = [inspection for inspection in inspections if _can_view_inspection(current_user, inspection)]
    return [_build_read(i) for i in inspections]


@router.post("/inspections/", response_model=QCInspectionDetailRead, status_code=201)
async def create_inspection(
    body: QCInspectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_inspection_action(current_user, QCInspection(warehouse_id=body.warehouse_id), "create")
    insp = await crud.create_inspection(db, body.model_dump(), current_user.id)
    await db.commit()
    insp = await crud.get_inspection(db, insp.id)
    return _build_detail(insp)


@router.get("/inspections/{inspection_id}", response_model=QCInspectionDetailRead)
async def get_inspection(inspection_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(require_any_permission(QUALITY_VIEW_PERMISSIONS))):
    insp = await crud.get_inspection(db, inspection_id)
    if not insp:
        raise HTTPException(404, "Inspection not found")
    _require_inspection_view(current_user, insp)
    return _build_detail(insp)


@router.patch("/inspections/{inspection_id}", response_model=QCInspectionDetailRead)
async def update_inspection(
    inspection_id: uuid.UUID,
    body: QCInspectionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    insp = await crud.get_inspection(db, inspection_id)
    if not insp:
        raise HTTPException(404, "Inspection not found")
    _require_inspection_action(current_user, insp, "edit")
    if insp.status not in (QCStatus.PENDING, QCStatus.IN_PROGRESS):
        raise HTTPException(422, "Cannot edit a completed inspection")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(insp, k, v)
    await db.commit()
    insp = await crud.get_inspection(db, inspection_id)
    return _build_detail(insp)


@router.post("/inspections/{inspection_id}/results", response_model=QCInspectionDetailRead, status_code=201)
async def add_test_result(
    inspection_id: uuid.UUID,
    body: QCTestResultCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    insp = await crud.get_inspection(db, inspection_id)
    if not insp:
        raise HTTPException(404, "Inspection not found")
    _require_inspection_action(current_user, insp, "edit")
    if insp.status not in (QCStatus.PENDING, QCStatus.IN_PROGRESS):
        raise HTTPException(422, "Cannot add results to a completed inspection")

    data = body.model_dump()
    # Auto-evaluate is_passed from spec limits if not explicitly set
    tr_obj = QCTestResult(inspection_id=inspection_id, tested_by_id=current_user.id, **data)
    if tr_obj.is_passed is None:
        tr_obj.is_passed = svc.auto_evaluate_result(tr_obj)

    await crud.add_test_result(db, insp, data | {"is_passed": tr_obj.is_passed}, current_user.id)
    await db.commit()
    insp = await crud.get_inspection(db, inspection_id)
    return _build_detail(insp)


@router.delete("/inspections/{inspection_id}/results/{result_id}", status_code=204)
async def delete_test_result(
    inspection_id: uuid.UUID,
    result_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    insp = await crud.get_inspection(db, inspection_id)
    if not insp or insp.status not in (QCStatus.PENDING, QCStatus.IN_PROGRESS):
        raise HTTPException(422, "Cannot modify a completed inspection")
    _require_inspection_action(current_user, insp, "edit")
    tr = await crud.get_test_result(db, result_id)
    if not tr or tr.inspection_id != inspection_id:
        raise HTTPException(404, "Result not found")
    await crud.delete_test_result(db, tr)
    await db.commit()


@router.post("/inspections/{inspection_id}/decide", response_model=QCInspectionDetailRead)
async def decide_inspection(
    inspection_id: uuid.UUID,
    body: QCDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    insp = await crud.get_inspection(db, inspection_id)
    if not insp:
        raise HTTPException(404, "Inspection not found")
    _require_inspection_action(current_user, insp, "approve")
    insp = await svc.make_decision(
        db, insp,
        decision=body.decision,
        decided_by_id=current_user.id,
        decision_notes=body.decision_notes,
        rework_candidate=body.rework_candidate,
        apply_quarantine=body.apply_quarantine,
    )
    await db.commit()
    insp = await crud.get_inspection(db, inspection_id)
    return _build_detail(insp)


@router.post("/inspections/{inspection_id}/release-quarantine", response_model=QCInspectionDetailRead)
async def release_quarantine(
    inspection_id: uuid.UUID,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    insp = await crud.get_inspection(db, inspection_id)
    if not insp:
        raise HTTPException(404, "Inspection not found")
    _require_inspection_action(current_user, insp, "release")
    await svc.release_qc_quarantine(db, insp, current_user.id, notes)
    await db.commit()
    insp = await crud.get_inspection(db, inspection_id)
    return _build_detail(insp)


# ── QC for GRN / Order (convenience) ──────────────────────────────��──────────

@router.post("/create-for-grn", response_model=QCInspectionDetailRead, status_code=201)
async def create_inspection_for_grn(
    grn_id: uuid.UUID = Query(...),
    grn_line_id: uuid.UUID = Query(...),
    material_id: Optional[uuid.UUID] = Query(None),
    supplier_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    lot_number: Optional[str] = Query(None),
    inspection_no: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_inspection_action(current_user, QCInspection(warehouse_id=warehouse_id), "create")
    insp = await svc.create_qc_for_grn_line(
        db, grn_id=grn_id, grn_line_id=grn_line_id,
        material_id=material_id, supplier_id=supplier_id,
        warehouse_id=warehouse_id, lot_number=lot_number,
        inspection_no=inspection_no, inspector_id=current_user.id,
    )
    await db.commit()
    insp = await crud.get_inspection(db, insp.id)
    return _build_detail(insp)


@router.post("/create-for-order", response_model=QCInspectionDetailRead, status_code=201)
async def create_inspection_for_order(
    production_order_id: uuid.UUID = Query(...),
    product_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    lot_number: Optional[str] = Query(None),
    batch_no: Optional[str] = Query(None),
    inspection_no: str = Query(...),
    qc_type: QCType = Query(QCType.IN_PROCESS),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_inspection_action(current_user, QCInspection(warehouse_id=warehouse_id), "create")
    insp = await svc.create_qc_for_order(
        db, production_order_id=production_order_id,
        product_id=product_id, warehouse_id=warehouse_id,
        lot_number=lot_number, batch_no=batch_no,
        inspection_no=inspection_no, inspector_id=current_user.id,
        qc_type=qc_type,
    )
    await db.commit()
    insp = await crud.get_inspection(db, insp.id)
    return _build_detail(insp)


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/inspections/{inspection_id}/coa", response_model=COAReport)
async def get_coa(
    inspection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_any_permission(QUALITY_VIEW_PERMISSIONS)),
):
    insp = await crud.get_inspection(db, inspection_id)
    if not insp:
        raise HTTPException(404, "Inspection not found")
    _require_inspection_view(current_user, insp)
    return svc.generate_coa(insp)


@router.get("/reports/rejections", response_model=List[RejectionSummaryRow])
async def rejection_summary(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    groups = await svc.get_rejection_summary(db)
    rows = []
    for g in groups:
        mat_name = prod_name = sup_name = None
        if g["material_id"]:
            r = await db.execute(select(Material).where(Material.id == g["material_id"]))
            m = r.scalar_one_or_none()
            mat_name = m.name if m else None
        if g["product_id"]:
            r = await db.execute(select(Product).where(Product.id == g["product_id"]))
            p = r.scalar_one_or_none()
            prod_name = p.name if p else None
        if g["supplier_id"]:
            r = await db.execute(select(Supplier).where(Supplier.id == g["supplier_id"]))
            s = r.scalar_one_or_none()
            sup_name = s.name if s else None

        total = g["total"]
        rejected = g["rejected"]
        rows.append(RejectionSummaryRow(
            material_name=mat_name,
            product_name=prod_name,
            supplier_name=sup_name,
            total_inspections=total,
            total_rejected=rejected,
            rejection_rate=round(rejected / total * 100, 2) if total else 0.0,
            last_rejection_date=g["last_rejection"],
        ))
    rows.sort(key=lambda r: r.rejection_rate, reverse=True)
    return rows


# ── Builders ──────────────────────────────────────────────────────────────────

def _build_read(insp: QCInspection) -> QCInspectionRead:
    r = QCInspectionRead.model_validate(insp)
    r.supplier_name = insp.supplier.name if insp.supplier else None
    r.material_name = insp.material.name if insp.material else None
    r.material_code = insp.material.code if insp.material else None
    r.product_name = insp.product.name if insp.product else None
    r.product_sku = insp.product.sku if insp.product else None
    r.inspector_name = insp.inspector.full_name if insp.inspector else None
    results = insp.test_results or []
    r.test_count = len(results)
    r.pass_count = sum(1 for t in results if t.is_passed is True)
    r.fail_count = sum(1 for t in results if t.is_passed is False)
    r.critical_fail = any(t.is_critical and t.is_passed is False for t in results)
    return r


def _build_detail(insp: QCInspection) -> QCInspectionDetailRead:
    r = QCInspectionDetailRead.model_validate(insp)
    r.supplier_name = insp.supplier.name if insp.supplier else None
    r.material_name = insp.material.name if insp.material else None
    r.material_code = insp.material.code if insp.material else None
    r.product_name = insp.product.name if insp.product else None
    r.product_sku = insp.product.sku if insp.product else None
    r.inspector_name = insp.inspector.full_name if insp.inspector else None
    results = insp.test_results or []
    r.test_count = len(results)
    r.pass_count = sum(1 for t in results if t.is_passed is True)
    r.fail_count = sum(1 for t in results if t.is_passed is False)
    r.critical_fail = any(t.is_critical and t.is_passed is False for t in results)

    trs = []
    for t in results:
        tr = QCTestResultRead.model_validate(t)
        tr.tested_by_name = t.tested_by.full_name if t.tested_by else None
        trs.append(tr)
    r.test_results = trs
    return r
