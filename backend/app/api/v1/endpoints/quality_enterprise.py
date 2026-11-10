"""M35 QC/QA enterprise API: specifications, QC plans, test methods, AQL, SPC,
concessions, quality cost, retain samples, change control and CAPA links."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission
from app.core.deps import get_current_user, get_db
from app.models.consumer_complaints import ConsumerComplaint
from app.models.quality import (
    AQLSamplingPlan, CorrectiveAction, QCDeviation, QCInspection, QCPlan, QCPlanStep, QCSpecification,
    QCTemplate, QCTemplateParameter, QCTestMethod, QualityChangeRequest, QualityConcession,
    QualityCostEntry, RetainSample, RetainSampleMovement, RiskLevel,
)
from app.models.traceability import RecallHeader
from app.services import qa_enterprise_service as qa
from app.services import qms_service as qms_svc

router = APIRouter()

_PERMS = {
    "view": ("quality.view", "quality.view_all"),
    "create": ("quality.create", "quality.create_all"),
    "edit": ("quality.edit", "quality.edit_all"),
    "approve": ("quality.approve", "quality.approve_all"),
}


def _need(*actions: str):
    permissions = tuple(p for a in actions for p in _PERMS[a])
    action = "/".join(actions)

    async def _check(current_user=Depends(get_current_user)):
        if not has_any_permission(current_user, permissions):
            raise HTTPException(status_code=403, detail=f"Quality {action} permission is required.")
        return current_user
    return _check


def _fail(status: int, errors: list[str]):
    if errors:
        raise HTTPException(status_code=status, detail=" ".join(errors))


def _row(obj, *fields) -> dict:
    out = {"id": str(obj.id)}
    for f in fields:
        v = getattr(obj, f)
        out[f] = str(v) if isinstance(v, (uuid.UUID, Decimal)) else v.isoformat() if isinstance(v, (date, datetime)) else v
    return out


async def _locked(db: AsyncSession, model, obj_id):
    obj = (await db.execute(select(model).where(model.id == obj_id).with_for_update())).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
    return obj


# ── Test methods ─────────────────────────────────────────────────────────────

class TestMethodIn(BaseModel):
    method_code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    standard_reference: Optional[str] = None
    description: Optional[str] = None
    instrument_type: Optional[str] = None
    requires_instrument: bool = False
    required_skill_id: Optional[uuid.UUID] = None


_METHOD_FIELDS = ("method_code", "version", "name", "standard_reference", "instrument_type",
                  "requires_instrument", "required_skill_id", "is_active")


@router.get("/test-methods")
async def list_test_methods(db: AsyncSession = Depends(get_db), _=Depends(_need("view"))):
    rows = await db.execute(select(QCTestMethod).order_by(QCTestMethod.method_code, QCTestMethod.version))
    return [_row(m, *_METHOD_FIELDS) for m in rows.scalars().all()]


@router.post("/test-methods", status_code=201)
async def create_test_method(body: TestMethodIn, db: AsyncSession = Depends(get_db), _=Depends(_need("create"))):
    if body.requires_instrument and not body.instrument_type:
        raise HTTPException(status_code=422, detail="An instrument type is required when an instrument is required.")
    latest = (await db.execute(
        select(func.max(QCTestMethod.version)).where(QCTestMethod.method_code == body.method_code)
    )).scalar()
    method = QCTestMethod(**body.model_dump(), version=(latest or 0) + 1)
    db.add(method)
    await db.commit()
    return _row(method, *_METHOD_FIELDS)


@router.put("/template-parameters/{parameter_id}/test-method")
async def link_template_parameter_method(parameter_id: uuid.UUID, test_method_id: Optional[uuid.UUID] = None,
                                         db: AsyncSession = Depends(get_db), _=Depends(_need("edit"))):
    param = await _locked(db, QCTemplateParameter, parameter_id)
    if test_method_id is not None:
        method = await db.get(QCTestMethod, test_method_id)
        if method is None or not method.is_active:
            raise HTTPException(status_code=422, detail="The test method is missing or inactive.")
    param.test_method_id = test_method_id
    await db.commit()
    return {"id": str(param.id), "test_method_id": str(test_method_id) if test_method_id else None}


# ── Change control ───────────────────────────────────────────────────────────

class ChangeRequestIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    change_type: Literal["SPECIFICATION", "QC_PLAN", "TEST_METHOD", "PROCESS", "OTHER"]
    target_reference: Optional[str] = None
    description: str = Field(min_length=1)
    risk_assessment: Optional[str] = None


class TransitionIn(BaseModel):
    status: Literal["SUBMITTED", "APPROVED", "REJECTED", "IMPLEMENTED", "CLOSED", "CANCELLED"]
    notes: Optional[str] = None


_CR_FIELDS = ("cr_no", "title", "change_type", "target_reference", "status", "requested_by_id",
              "decided_by_id", "decided_at", "implemented_at", "closed_at")


@router.get("/change-requests")
async def list_change_requests(status: Optional[str] = None, db: AsyncSession = Depends(get_db),
                               _=Depends(_need("view"))):
    q = select(QualityChangeRequest).order_by(QualityChangeRequest.created_at.desc())
    if status:
        q = q.where(QualityChangeRequest.status == status)
    return [_row(c, *_CR_FIELDS) for c in (await db.execute(q)).scalars().all()]


@router.post("/change-requests", status_code=201)
async def create_change_request(body: ChangeRequestIn, db: AsyncSession = Depends(get_db),
                                user=Depends(_need("create"))):
    cr = QualityChangeRequest(cr_no=qa.new_reference("QCR"), requested_by_id=user.id, **body.model_dump())
    db.add(cr)
    await db.commit()
    return _row(cr, *_CR_FIELDS)


@router.post("/change-requests/{cr_id}/transition")
async def transition_change_request(cr_id: uuid.UUID, body: TransitionIn, db: AsyncSession = Depends(get_db),
                                    user=Depends(_need("edit", "approve"))):
    needed = "approve" if body.status in {"APPROVED", "REJECTED", "CLOSED"} else "edit"
    if not has_any_permission(user, _PERMS[needed]):
        raise HTTPException(status_code=403, detail=f"Quality {needed} permission is required.")
    cr = await _locked(db, QualityChangeRequest, cr_id)
    _fail(409, qa.change_request_transition_errors(cr, body.status, user.id, body.notes))
    now = datetime.now(timezone.utc)
    if body.status in {"APPROVED", "REJECTED"}:
        cr.decided_by_id, cr.decided_at, cr.decision_notes = user.id, now, body.notes
    elif body.status == "IMPLEMENTED":
        cr.implemented_by_id, cr.implemented_at = user.id, now
    elif body.status == "CLOSED":
        cr.verification_notes, cr.closed_at = body.notes or cr.verification_notes, now
    cr.status = body.status
    await db.commit()
    return _row(cr, *_CR_FIELDS)


# ── Specifications ───────────────────────────────────────────────────────────

class SpecificationIn(BaseModel):
    spec_code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    scope_type: Literal["PRODUCT", "MATERIAL", "PROCESS"]
    product_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    process_stage: Optional[str] = None
    template_id: uuid.UUID
    effective_from: date
    change_request_id: Optional[uuid.UUID] = None
    change_reason: Optional[str] = None


_SPEC_FIELDS = ("spec_code", "version", "name", "scope_type", "product_id", "material_id", "process_stage",
                "template_id", "status", "effective_from", "effective_to", "change_request_id",
                "created_by_id", "approved_by_id", "approved_at")


@router.get("/specifications")
async def list_specifications(spec_code: Optional[str] = None, db: AsyncSession = Depends(get_db),
                              _=Depends(_need("view"))):
    q = select(QCSpecification).order_by(QCSpecification.spec_code, QCSpecification.version)
    if spec_code:
        q = q.where(QCSpecification.spec_code == spec_code)
    return [_row(s, *_SPEC_FIELDS) for s in (await db.execute(q)).scalars().all()]


@router.get("/specifications/effective")
async def get_effective_specification(spec_code: str, as_of: Optional[date] = None,
                                      db: AsyncSession = Depends(get_db), _=Depends(_need("view"))):
    specs = (await db.execute(select(QCSpecification).where(QCSpecification.spec_code == spec_code))).scalars().all()
    spec = qa.effective_spec(specs, as_of or date.today())
    if spec is None:
        raise HTTPException(status_code=404, detail="No effective specification for that date.")
    return _row(spec, *_SPEC_FIELDS) | {"parameter_snapshot": spec.parameter_snapshot}


@router.post("/specifications", status_code=201)
async def create_specification(body: SpecificationIn, db: AsyncSession = Depends(get_db),
                               user=Depends(_need("create"))):
    template = await db.get(QCTemplate, body.template_id)
    if template is None or not template.is_active:
        raise HTTPException(status_code=422, detail="The specification template is missing or inactive.")
    latest = (await db.execute(
        select(func.max(QCSpecification.version)).where(QCSpecification.spec_code == body.spec_code)
    )).scalar()
    spec = QCSpecification(**body.model_dump(), version=(latest or 0) + 1, status="DRAFT", created_by_id=user.id)
    db.add(spec)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="The specification scope or version is invalid.") from exc
    return _row(spec, *_SPEC_FIELDS)


@router.post("/specifications/{spec_id}/approve")
async def approve_specification(spec_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                                user=Depends(_need("approve"))):
    spec = await _locked(db, QCSpecification, spec_id)
    siblings = (await db.execute(
        select(QCSpecification).where(QCSpecification.spec_code == spec.spec_code).with_for_update()
    )).scalars().all()
    cr = await db.get(QualityChangeRequest, spec.change_request_id) if spec.change_request_id else None
    _fail(409, qa.spec_approval_errors(spec, user.id, cr))
    params = (await db.execute(
        select(QCTemplateParameter).where(QCTemplateParameter.template_id == spec.template_id)
        .order_by(QCTemplateParameter.display_order)
    )).scalars().all()
    spec.parameter_snapshot = [
        {"parameter_name": p.parameter_name, "parameter_type": qa._v(p.parameter_type), "unit": p.unit,
         "target_value": p.target_value, "min_value": str(p.min_value) if p.min_value is not None else None,
         "max_value": str(p.max_value) if p.max_value is not None else None, "is_critical": p.is_critical,
         "test_method_id": str(p.test_method_id) if p.test_method_id else None}
        for p in params
    ]
    qa.supersede_previous(siblings, spec)
    spec.status, spec.approved_by_id, spec.approved_at = "APPROVED", user.id, datetime.now(timezone.utc)
    await db.commit()
    return _row(spec, *_SPEC_FIELDS)


# ── QC plans ─────────────────────────────────────────────────────────────────

class PlanStepIn(BaseModel):
    sequence: int = Field(ge=1)
    qc_type: Literal["INCOMING", "IN_PROCESS", "FINISHED_GOODS", "RETEST"]
    qc_sub_type: Optional[str] = None
    spec_code: Optional[str] = None
    is_mandatory: bool = True
    blocks_progression: bool = True


class PlanIn(BaseModel):
    plan_code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    product_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    steps: list[PlanStepIn] = Field(min_length=1)


def _plan_out(plan: QCPlan, steps) -> dict:
    return _row(plan, "plan_code", "version", "name", "product_id", "material_id", "status",
                "created_by_id", "approved_by_id") | {
        "steps": [{"sequence": s.sequence, "qc_type": s.qc_type, "qc_sub_type": s.qc_sub_type,
                   "spec_code": s.spec_code, "is_mandatory": s.is_mandatory} for s in steps]}


@router.post("/qc-plans", status_code=201)
async def create_qc_plan(body: PlanIn, db: AsyncSession = Depends(get_db), user=Depends(_need("create"))):
    if body.product_id is None and body.material_id is None:
        raise HTTPException(status_code=422, detail="A QC plan needs a product or a material.")
    if len({s.sequence for s in body.steps}) != len(body.steps):
        raise HTTPException(status_code=422, detail="Step sequences must be unique.")
    latest = (await db.execute(select(func.max(QCPlan.version)).where(QCPlan.plan_code == body.plan_code))).scalar()
    plan = QCPlan(plan_code=body.plan_code, version=(latest or 0) + 1, name=body.name, product_id=body.product_id,
                  material_id=body.material_id, status="DRAFT", created_by_id=user.id)
    db.add(plan)
    await db.flush()
    steps = [QCPlanStep(plan_id=plan.id, **s.model_dump()) for s in body.steps]
    db.add_all(steps)
    await db.commit()
    return _plan_out(plan, steps)


@router.post("/qc-plans/{plan_id}/activate")
async def activate_qc_plan(plan_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(_need("approve"))):
    plan = await _locked(db, QCPlan, plan_id)
    if plan.status != "DRAFT":
        raise HTTPException(status_code=409, detail="Only a DRAFT plan can be activated.")
    if plan.created_by_id == user.id:
        raise HTTPException(status_code=409, detail="The plan author cannot activate it.")
    active = (await db.execute(
        select(QCPlan).where(QCPlan.plan_code == plan.plan_code, QCPlan.status == "ACTIVE").with_for_update()
    )).scalars().all()
    for old in active:
        old.status = "RETIRED"
    plan.status, plan.approved_by_id, plan.approved_at = "ACTIVE", user.id, datetime.now(timezone.utc)
    await db.commit()
    steps = (await db.execute(select(QCPlanStep).where(QCPlanStep.plan_id == plan.id))).scalars().all()
    return _plan_out(plan, steps)


@router.get("/qc-plans/{plan_id}/coverage")
async def qc_plan_coverage(plan_id: uuid.UUID, production_order_id: Optional[uuid.UUID] = None,
                           lot_id: Optional[uuid.UUID] = None, db: AsyncSession = Depends(get_db),
                           _=Depends(_need("view"))):
    if production_order_id is None and lot_id is None:
        raise HTTPException(status_code=422, detail="Give a production order or a lot.")
    plan = await db.get(QCPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="QC plan not found")
    steps = (await db.execute(select(QCPlanStep).where(QCPlanStep.plan_id == plan_id))).scalars().all()
    q = select(QCInspection)
    q = q.where(QCInspection.production_order_id == production_order_id) if production_order_id \
        else q.where(QCInspection.lot_id == lot_id)
    inspections = (await db.execute(q)).scalars().all()
    return qa.plan_coverage(steps, inspections)


# ── AQL / SPC ────────────────────────────────────────────────────────────────

class AQLEvaluateIn(BaseModel):
    lot_size: int = Field(ge=1)
    applies_to: str = "INCOMING"
    product_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    sample_inspected: int = Field(ge=0)
    defects_found: int = Field(ge=0)


@router.post("/aql/evaluate")
async def evaluate_aql(body: AQLEvaluateIn, db: AsyncSession = Depends(get_db), _=Depends(_need("view"))):
    plans = (await db.execute(select(AQLSamplingPlan).where(AQLSamplingPlan.is_active.is_(True)))).scalars().all()
    plan = qa.select_aql_plan(plans, body.lot_size, body.applies_to, body.product_id, body.material_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="No active AQL plan covers this lot size.")
    return {"plan_id": str(plan.id), "plan_code": plan.plan_code, "sample_size": plan.sample_size,
            **qa.evaluate_aql(plan, body.sample_inspected, body.defects_found)}


_QCTypeParam = Optional[Literal["INCOMING", "IN_PROCESS", "FINISHED_GOODS", "RETEST"]]


@router.get("/spc/chart")
async def spc_chart(product_id: uuid.UUID, parameter_name: str, limit: int = Query(100, ge=2, le=500),
                    qc_type: _QCTypeParam = None, db: AsyncSession = Depends(get_db), _=Depends(_need("view"))):
    results = await qa.load_spc_series(db, product_id, parameter_name, limit, qc_type)
    if len(results) < 2:
        raise HTTPException(status_code=422, detail="At least two numeric results are needed.")
    return qa.analyse_spc(results) | {
        "points": [{"test_result_id": str(r.id), "value": float(r.numeric_value),
                    "recorded_at": r.created_at.isoformat() if r.created_at else None} for r in results]}


@router.post("/spc/evaluate")
async def spc_evaluate(product_id: uuid.UUID, parameter_name: str, limit: int = Query(100, ge=2, le=500),
                       qc_type: _QCTypeParam = None, db: AsyncSession = Depends(get_db),
                       user=Depends(_need("create"))):
    try:
        out = await qa.record_spc_signals(db, product_id, parameter_name, user.id, limit, qc_type)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="A concurrent SPC evaluation recorded these signals; retry.") from exc
    return out


# ── Concessions ──────────────────────────────────────────────────────────────

class ConcessionIn(BaseModel):
    deviation_id: uuid.UUID
    lot_id: uuid.UUID
    justification: str = Field(min_length=1)
    quantity_limit: Optional[Decimal] = Field(default=None, gt=0)
    uom: Optional[str] = None


class ConcessionDecisionIn(BaseModel):
    approve: bool
    conditions: Optional[str] = None
    valid_until: Optional[datetime] = None
    notes: Optional[str] = None


_CONCESSION_FIELDS = ("concession_no", "deviation_id", "lot_id", "quantity_limit", "uom", "conditions", "status",
                      "valid_until", "requested_by_id", "decided_by_id", "decided_at")


@router.get("/concessions")
async def list_concessions(lot_id: Optional[uuid.UUID] = None, db: AsyncSession = Depends(get_db),
                           _=Depends(_need("view"))):
    q = select(QualityConcession).order_by(QualityConcession.created_at.desc())
    if lot_id:
        q = q.where(QualityConcession.lot_id == lot_id)
    return [_row(c, *_CONCESSION_FIELDS) for c in (await db.execute(q)).scalars().all()]


@router.post("/concessions", status_code=201)
async def request_concession(body: ConcessionIn, db: AsyncSession = Depends(get_db), user=Depends(_need("create"))):
    deviation = await db.get(QCDeviation, body.deviation_id)
    if deviation is None or qa._v(deviation.status) == "CLOSED":
        raise HTTPException(status_code=422, detail="A concession needs an open deviation.")
    if deviation.lot_id is not None and deviation.lot_id != body.lot_id:
        raise HTTPException(status_code=422, detail="The deviation belongs to a different lot.")
    c = QualityConcession(concession_no=qa.new_reference("CON"), requested_by_id=user.id, status="PENDING",
                          **body.model_dump())
    db.add(c)
    await db.commit()
    return _row(c, *_CONCESSION_FIELDS)


@router.post("/concessions/{concession_id}/decide")
async def decide_concession(concession_id: uuid.UUID, body: ConcessionDecisionIn,
                            db: AsyncSession = Depends(get_db), user=Depends(_need("approve"))):
    c = await _locked(db, QualityConcession, concession_id)
    if body.approve:
        c.conditions = body.conditions or c.conditions
        c.valid_until = body.valid_until
    _fail(409, qa.concession_decision_errors(c, user.id, body.approve))
    c.status = "APPROVED" if body.approve else "REJECTED"
    c.decided_by_id, c.decided_at, c.decision_notes = user.id, datetime.now(timezone.utc), body.notes
    await db.commit()
    return _row(c, *_CONCESSION_FIELDS)


@router.post("/concessions/{concession_id}/revoke")
async def revoke_concession(concession_id: uuid.UUID, notes: str = Query(min_length=1),
                            db: AsyncSession = Depends(get_db), user=Depends(_need("approve"))):
    c = await _locked(db, QualityConcession, concession_id)
    if c.status != "APPROVED":
        raise HTTPException(status_code=409, detail="Only an approved concession can be revoked.")
    if user.id == c.requested_by_id:
        raise HTTPException(status_code=409, detail="The requester cannot revoke their own concession.")
    c.status, c.decided_by_id, c.decided_at, c.decision_notes = "REVOKED", user.id, datetime.now(timezone.utc), notes
    await db.commit()
    return _row(c, *_CONCESSION_FIELDS)


# ── Quality cost ─────────────────────────────────────────────────────────────

class QualityCostIn(BaseModel):
    category: Literal["PREVENTION", "APPRAISAL", "INTERNAL_FAILURE", "EXTERNAL_FAILURE"]
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    currency: str = Field(default="KES", min_length=3, max_length=3)
    cost_date: date
    description: str = Field(min_length=1)
    risk_level: Optional[Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]] = None
    deviation_id: Optional[uuid.UUID] = None
    corrective_action_id: Optional[uuid.UUID] = None
    recall_id: Optional[uuid.UUID] = None
    complaint_id: Optional[uuid.UUID] = None
    lot_id: Optional[uuid.UUID] = None
    supplier_id: Optional[uuid.UUID] = None


@router.post("/quality-costs", status_code=201)
async def record_quality_cost(body: QualityCostIn, db: AsyncSession = Depends(get_db),
                              user=Depends(_need("create"))):
    data = body.model_dump()
    if data["risk_level"] is None and data["deviation_id"]:
        deviation = await db.get(QCDeviation, data["deviation_id"])
        data["risk_level"] = qa._v(deviation.severity) if deviation else None
    entry = QualityCostEntry(entry_no=qa.new_reference("QCOST"), recorded_by_id=user.id, **data)
    db.add(entry)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=422, detail="A linked quality record does not exist.") from exc
    return _row(entry, "entry_no", "category", "amount", "currency", "cost_date", "risk_level")


@router.get("/quality-costs/summary")
async def quality_cost_summary(date_from: Optional[date] = None, date_to: Optional[date] = None,
                               db: AsyncSession = Depends(get_db), _=Depends(_need("view"))):
    q = select(QualityCostEntry)
    if date_from:
        q = q.where(QualityCostEntry.cost_date >= date_from)
    if date_to:
        q = q.where(QualityCostEntry.cost_date <= date_to)
    return qa.summarize_quality_costs((await db.execute(q)).scalars().all())


# ── Retain samples ───────────────────────────────────────────────────────────

class RetainSampleIn(BaseModel):
    lot_id: uuid.UUID
    product_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    quantity: Decimal = Field(gt=0)
    uom: str = Field(min_length=1, max_length=20)
    storage_location: str = Field(min_length=1, max_length=200)
    storage_condition: Optional[str] = None
    collected_on: date
    retain_until: date


class RetainMoveIn(BaseModel):
    quantity: Optional[Decimal] = None
    reason: str = Field(min_length=1)


_RETAIN_FIELDS = ("sample_no", "lot_id", "quantity", "quantity_remaining", "uom", "storage_location",
                  "collected_on", "retain_until", "status")


@router.get("/retain-samples")
async def list_retain_samples(lot_id: Optional[uuid.UUID] = None, due_only: bool = False,
                              db: AsyncSession = Depends(get_db), _=Depends(_need("view"))):
    q = select(RetainSample).order_by(RetainSample.retain_until)
    if lot_id:
        q = q.where(RetainSample.lot_id == lot_id)
    samples = (await db.execute(q)).scalars().all()
    if due_only:
        samples = qa.retain_samples_due(samples)
    return [_row(s, *_RETAIN_FIELDS) for s in samples]


@router.post("/retain-samples", status_code=201)
async def register_retain_sample(body: RetainSampleIn, db: AsyncSession = Depends(get_db),
                                 user=Depends(_need("create"))):
    if body.retain_until < body.collected_on:
        raise HTTPException(status_code=422, detail="retain_until must not be before collected_on.")
    sample = RetainSample(sample_no=qa.new_reference("RS"), quantity_remaining=body.quantity, status="STORED",
                          created_by_id=user.id, **body.model_dump())
    db.add(sample)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=422, detail="The lot does not exist.") from exc
    return _row(sample, *_RETAIN_FIELDS)


@router.post("/retain-samples/{sample_id}/withdraw")
async def withdraw_retain_sample(sample_id: uuid.UUID, body: RetainMoveIn, db: AsyncSession = Depends(get_db),
                                 user=Depends(_need("edit"))):
    sample = await _locked(db, RetainSample, sample_id)
    qty = body.quantity if body.quantity is not None else Decimal("0")
    _fail(409, qa.retain_withdraw_errors(sample, qty))
    sample.quantity_remaining -= qty
    if sample.quantity_remaining == 0:
        sample.status = "DEPLETED"
    db.add(RetainSampleMovement(retain_sample_id=sample.id, movement_type="WITHDRAW", quantity=qty,
                                reason=body.reason, performed_by_id=user.id))
    await db.commit()
    return _row(sample, *_RETAIN_FIELDS)


@router.post("/retain-samples/{sample_id}/dispose")
async def dispose_retain_sample(sample_id: uuid.UUID, body: RetainMoveIn, db: AsyncSession = Depends(get_db),
                                user=Depends(_need("edit"))):
    sample = await _locked(db, RetainSample, sample_id)
    early_ok = has_any_permission(user, _PERMS["approve"])
    _fail(409, qa.retain_dispose_errors(sample, body.reason, early_ok))
    db.add(RetainSampleMovement(retain_sample_id=sample.id, movement_type="DISPOSE",
                                quantity=sample.quantity_remaining, reason=body.reason, performed_by_id=user.id))
    sample.quantity_remaining = Decimal("0")
    sample.status = "DISPOSED"
    await db.commit()
    return _row(sample, *_RETAIN_FIELDS)


# ── Complaint / recall → CAPA ────────────────────────────────────────────────

_SEVERITY_FOR_COMPLAINT = {"SAFETY": RiskLevel.CRITICAL, "FOREIGN_OBJECT": RiskLevel.HIGH}
_SEVERITY_FOR_RECALL = {"critical": RiskLevel.CRITICAL, "high": RiskLevel.HIGH, "medium": RiskLevel.MEDIUM,
                        "low": RiskLevel.LOW}


async def _open_linked_capa(db: AsyncSession, trigger_type: str, trigger_id: uuid.UUID, title: str,
                            description: str, severity: RiskLevel) -> tuple[CorrectiveAction, bool]:
    existing = (await db.execute(
        select(CorrectiveAction).where(CorrectiveAction.trigger_type == trigger_type,
                                       CorrectiveAction.trigger_id == trigger_id)
        .order_by(CorrectiveAction.created_at.desc())
    )).scalars().first()
    if existing is not None and qa._v(existing.status) != "VERIFIED":
        return existing, False
    ca = await qms_svc.create_corrective_action(db, {
        "title": title, "description": description, "severity": severity,
        "trigger_type": trigger_type, "trigger_id": trigger_id,
    })
    return ca, True


@router.post("/complaints/{complaint_id}/capa", status_code=201)
async def capa_from_complaint(complaint_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                              _=Depends(_need("create"))):
    complaint = await db.get(ConsumerComplaint, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    ca, created = await _open_linked_capa(
        db, "COMPLAINT", complaint.id, f"CAPA for complaint {complaint.complaint_ref}",
        f"{complaint.product_name} lot {complaint.lot_number or '-'}: {complaint.description}",
        _SEVERITY_FOR_COMPLAINT.get(qa._v(complaint.severity), RiskLevel.MEDIUM))
    await db.commit()
    return {"corrective_action_id": str(ca.id), "ca_no": ca.ca_no, "created": created}


@router.post("/recalls/{recall_id}/capa", status_code=201)
async def capa_from_recall(recall_id: uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(_need("create"))):
    recall = await db.get(RecallHeader, recall_id)
    if recall is None:
        raise HTTPException(status_code=404, detail="Recall not found")
    ca, created = await _open_linked_capa(
        db, "RECALL", recall.id, f"CAPA for recall {recall.recall_no}", recall.recall_reason,
        _SEVERITY_FOR_RECALL.get(qa._v(recall.severity_level), RiskLevel.HIGH))
    await db.commit()
    return {"corrective_action_id": str(ca.id), "ca_no": ca.ca_no, "created": created}


@router.get("/capa-links")
async def capa_links(trigger_type: Literal["COMPLAINT", "RECALL", "AUDIT", "DEVIATION"], trigger_id: uuid.UUID,
                     db: AsyncSession = Depends(get_db), _=Depends(_need("view"))):
    rows = (await db.execute(
        select(CorrectiveAction).where(CorrectiveAction.trigger_type == trigger_type,
                                       CorrectiveAction.trigger_id == trigger_id)
    )).scalars().all()
    return [_row(c, "ca_no", "title", "status", "severity", "due_date") | {"status": qa._v(c.status),
                                                                           "severity": qa._v(c.severity)}
            for c in rows]
