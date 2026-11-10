"""M35 — API and service-flow tests on an in-memory session (no PostgreSQL).

Covers authorization, segregation of duties and lifecycle guards for the new
/quality-enterprise routes and the hardened /qms CAPA, CoA, audit and
deviation routes, plus concession-gated conditional release, SPC escalation
and measurement controls on result recording.
"""
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints.qms import router as qms_router
from app.api.v1.endpoints.quality_enterprise import router as qe_router
from app.core.deps import get_current_user, get_db
from app.models.hr import Employee
from app.models.machine_operator import OperatorProfile, OperatorSkillCert
from app.models.quality import (
    CertificateOfAnalysis, CorrectiveAction, CorrectiveActionStatus, CorrectiveActionStep, DeviationStatus,
    InstrumentCalibration, LotQualityStatus, QCDecision, QCDeviation, QCInspection, QCSpecification, QCStatus,
    QCTemplate, QCTemplateParameter, QCTestMethod, QCType, QualityAuditChecklist, QualityConcession,
    RiskLevel, SPCSignal,
)
from app.services import qa_enterprise_service as qa
from app.services import quality_service
from fake_async_db import FakeDB

ALL = ("quality.view", "quality.create", "quality.edit", "quality.approve")


def _user(*codes, uid=None):
    perms = [SimpleNamespace(code=c, is_active=True) for c in codes]
    return SimpleNamespace(id=uid or uuid.uuid4(), is_superuser=False, full_name="u", username="u",
                           roles=[SimpleNamespace(is_active=True, permissions=perms, access_scopes=[])])


AUTHOR, APPROVER = _user(*ALL), _user(*ALL)


class Client:
    """TestClient whose acting user can be switched per request."""

    def __init__(self, db):
        self.db = db
        self.app = FastAPI()
        self.app.include_router(qe_router, prefix="/qe")
        self.app.include_router(qms_router, prefix="/qms")

        async def _db():
            yield db

        self.app.dependency_overrides[get_db] = _db
        self.client = TestClient(self.app)

    def as_(self, user):
        self.app.dependency_overrides[get_current_user] = lambda: user
        return self.client


@pytest.fixture
def env():
    db = FakeDB()
    return db, Client(db)


# ── authorization ────────────────────────────────────────────────────────────

def _qe_routes():
    for route in qe_router.routes:
        for method in route.methods:
            yield method, "/qe" + re.sub(r"\{[^}]+\}", str(uuid.uuid4()), route.path)


@pytest.mark.parametrize("method,path", list(_qe_routes()))
def test_quality_enterprise_routes_require_authentication(method, path):
    app = FastAPI()
    app.include_router(qe_router, prefix="/qe")
    with TestClient(app) as client:
        assert client.request(method, path).status_code == 401


@pytest.mark.parametrize("method,path", [(m, p) for m, p in _qe_routes() if m != "GET" and p != "/qe/aql/evaluate"])
def test_view_only_user_cannot_write(env, method, path):
    _, c = env
    assert c.as_(_user("quality.view")).request(method, path, json={}).status_code == 403


# ── specifications + change control ──────────────────────────────────────────

def _template(db):
    t = db.add(QCTemplate(id=uuid.uuid4(), name="pH", qc_type=QCType.FINISHED_GOODS, is_active=True))
    db.add(QCTemplateParameter(id=uuid.uuid4(), template_id=t.id, parameter_name="pH",
                               parameter_type="NUMERIC", min_value=Decimal("5"), max_value=Decimal("7")))
    return t


def _spec_body(template_id, start, **kw):
    return {"spec_code": "SPEC-PH", "name": "pH", "scope_type": "PROCESS", "process_stage": "MIXING",
            "template_id": str(template_id), "effective_from": start.isoformat(), **kw}


def test_specification_versioning_with_change_control(env):
    db, c = env
    t = _template(db)
    today = date.today()
    v1 = c.as_(AUTHOR).post("/qe/specifications", json=_spec_body(t.id, today)).json()
    assert v1["version"] == 1 and v1["status"] == "DRAFT"
    assert c.as_(AUTHOR).post(f"/qe/specifications/{v1['id']}/approve").status_code == 409
    approved = c.as_(APPROVER).post(f"/qe/specifications/{v1['id']}/approve").json()
    assert approved["status"] == "APPROVED"

    v2 = c.as_(AUTHOR).post("/qe/specifications", json=_spec_body(t.id, today + timedelta(days=10))).json()
    assert v2["version"] == 2
    blocked = c.as_(APPROVER).post(f"/qe/specifications/{v2['id']}/approve")
    assert blocked.status_code == 409 and "change request" in blocked.json()["detail"]

    cr = c.as_(AUTHOR).post("/qe/change-requests", json={
        "title": "Tighten pH", "change_type": "SPECIFICATION", "target_reference": "SPEC-PH",
        "description": "Narrow range", "risk_assessment": "Low"}).json()
    assert c.as_(AUTHOR).post(f"/qe/change-requests/{cr['id']}/transition", json={"status": "SUBMITTED"}).status_code == 200
    assert c.as_(AUTHOR).post(f"/qe/change-requests/{cr['id']}/transition", json={"status": "APPROVED"}).status_code == 409
    assert c.as_(APPROVER).post(f"/qe/change-requests/{cr['id']}/transition", json={"status": "APPROVED"}).status_code == 200

    spec_v2 = next(s for s in db.rows[QCSpecification] if str(s.id) == v2["id"])
    spec_v2.change_request_id = uuid.UUID(cr["id"])
    ok = c.as_(APPROVER).post(f"/qe/specifications/{v2['id']}/approve").json()
    assert ok["status"] == "APPROVED"

    eff_now = c.as_(AUTHOR).get("/qe/specifications/effective", params={"spec_code": "SPEC-PH"}).json()
    eff_later = c.as_(AUTHOR).get("/qe/specifications/effective", params={
        "spec_code": "SPEC-PH", "as_of": (today + timedelta(days=20)).isoformat()}).json()
    assert eff_now["version"] == 1 and eff_now["status"] == "SUPERSEDED"
    assert eff_now["effective_to"] == (today + timedelta(days=9)).isoformat()
    assert eff_later["version"] == 2 and eff_later["parameter_snapshot"][0]["max_value"] == "7"


def test_qc_plan_activation_and_coverage(env):
    db, c = env
    order = uuid.uuid4()
    plan = c.as_(AUTHOR).post("/qe/qc-plans", json={
        "plan_code": "PLAN-1", "name": "Juice", "product_id": str(uuid.uuid4()),
        "steps": [{"sequence": 1, "qc_type": "IN_PROCESS"}, {"sequence": 2, "qc_type": "FINISHED_GOODS"}]}).json()
    assert c.as_(AUTHOR).post(f"/qe/qc-plans/{plan['id']}/activate").status_code == 409
    assert c.as_(APPROVER).post(f"/qe/qc-plans/{plan['id']}/activate").json()["status"] == "ACTIVE"
    db.add(QCInspection(id=uuid.uuid4(), inspection_no="I1", qc_type=QCType.IN_PROCESS, status=QCStatus.PASSED,
                        production_order_id=order, inspection_date=date.today()))
    cov = c.as_(AUTHOR).get(f"/qe/qc-plans/{plan['id']}/coverage",
                            params={"production_order_id": str(order)}).json()
    assert cov["complete"] is False and cov["missing_steps"] == [2]


# ── concessions + conditional release ────────────────────────────────────────

def _deviation(db, lot_id, **kw):
    fields = dict(id=uuid.uuid4(), deviation_no="DEV-1", lot_id=lot_id, deviation_type="OOS", severity=RiskLevel.LOW,
                  status=DeviationStatus.OPEN, description="Brix low", reported_by_id=AUTHOR.id)
    return db.add(QCDeviation(**(fields | kw)))


def test_concession_segregation_and_terms(env):
    db, c = env
    lot = uuid.uuid4()
    dev = _deviation(db, lot)
    con = c.as_(AUTHOR).post("/qe/concessions", json={
        "deviation_id": str(dev.id), "lot_id": str(lot), "justification": "Within customer tolerance"}).json()
    until = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    assert c.as_(AUTHOR).post(f"/qe/concessions/{con['id']}/decide",
                              json={"approve": True, "conditions": "x", "valid_until": until}).status_code == 409
    assert c.as_(APPROVER).post(f"/qe/concessions/{con['id']}/decide", json={"approve": True}).status_code == 409
    ok = c.as_(APPROVER).post(f"/qe/concessions/{con['id']}/decide", json={
        "approve": True, "conditions": "Industrial customers only", "valid_until": until}).json()
    assert ok["status"] == "APPROVED"
    wrong_lot = c.as_(AUTHOR).post("/qe/concessions", json={
        "deviation_id": str(dev.id), "lot_id": str(uuid.uuid4()), "justification": "x"})
    assert wrong_lot.status_code == 422


async def test_conditional_release_requires_active_concession(monkeypatch):
    db = FakeDB()
    lot = uuid.uuid4()
    insp = db.add(QCInspection(id=uuid.uuid4(), inspection_no="I1", qc_type=QCType.FINISHED_GOODS,
                               status=QCStatus.IN_PROGRESS, lot_id=lot, inspection_date=date.today()))
    with pytest.raises(Exception) as exc:
        await quality_service.make_decision(db, insp, QCDecision.CONDITIONAL_RELEASE, APPROVER.id, None, False, False)
    assert getattr(exc.value, "status_code", None) == 422

    async def _noop(*a, **k):
        return 0
    monkeypatch.setattr(quality_service, "_quarantine_lot_stock", _noop)
    import app.services.qms_service as qms_service
    monkeypatch.setattr(qms_service, "update_lot_qc_status_from_inspection", _noop)

    def _concession(deviation):
        return db.add(QualityConcession(
            id=uuid.uuid4(), concession_no=str(uuid.uuid4()), deviation_id=deviation.id, lot_id=lot,
            justification="j", conditions="c", status="APPROVED", requested_by_id=AUTHOR.id,
            decided_by_id=APPROVER.id, valid_until=datetime.now(timezone.utc) + timedelta(days=1)))

    _concession(_deviation(db, lot, deviation_no="DEV-OTHER"))  # same lot, unrelated deviation
    with pytest.raises(Exception) as exc:
        await quality_service.make_decision(db, insp, QCDecision.CONDITIONAL_RELEASE, APPROVER.id, None, False, False)
    assert getattr(exc.value, "status_code", None) == 422

    _concession(_deviation(db, lot, inspection_id=insp.id))
    out = await quality_service.make_decision(db, insp, QCDecision.CONDITIONAL_RELEASE, APPROVER.id, None, False, False)
    assert out.status == QCStatus.CONDITIONAL_RELEASE


async def test_conditional_release_needs_a_lot():
    db = FakeDB()
    insp = db.add(QCInspection(id=uuid.uuid4(), inspection_no="I2", qc_type=QCType.IN_PROCESS,
                               status=QCStatus.IN_PROGRESS, production_order_id=uuid.uuid4(),
                               inspection_date=date.today()))
    with pytest.raises(Exception) as exc:
        await quality_service.make_decision(db, insp, QCDecision.CONDITIONAL_RELEASE, APPROVER.id, None, False, False)
    assert getattr(exc.value, "status_code", None) == 422


# ── retain samples / quality cost ────────────────────────────────────────────

def test_retain_sample_lifecycle(env):
    _, c = env
    today = date.today()
    s = c.as_(AUTHOR).post("/qe/retain-samples", json={
        "lot_id": str(uuid.uuid4()), "quantity": "3", "uom": "bottle", "storage_location": "Retain room A",
        "collected_on": today.isoformat(), "retain_until": (today + timedelta(days=365)).isoformat()}).json()
    assert c.as_(AUTHOR).post(f"/qe/retain-samples/{s['id']}/withdraw",
                              json={"quantity": "4", "reason": "complaint test"}).status_code == 409
    w = c.as_(AUTHOR).post(f"/qe/retain-samples/{s['id']}/withdraw",
                           json={"quantity": "1", "reason": "complaint test"}).json()
    assert w["quantity_remaining"] == "2"
    editor = _user("quality.view", "quality.edit")
    assert c.as_(editor).post(f"/qe/retain-samples/{s['id']}/dispose", json={"reason": "space"}).status_code == 409
    d = c.as_(APPROVER).post(f"/qe/retain-samples/{s['id']}/dispose", json={"reason": "Approved early disposal"}).json()
    assert d["status"] == "DISPOSED" and d["quantity_remaining"] == "0"


def test_quality_cost_summary_endpoint(env):
    db, c = env
    dev = _deviation(db, uuid.uuid4(), severity=RiskLevel.HIGH)
    for cat, amt in (("APPRAISAL", "50"), ("INTERNAL_FAILURE", "150")):
        body = {"category": cat, "amount": amt, "cost_date": date.today().isoformat(), "description": cat}
        if cat == "INTERNAL_FAILURE":
            body["deviation_id"] = str(dev.id)
        r = c.as_(AUTHOR).post("/qe/quality-costs", json=body)
        assert r.status_code == 201
    assert r.json()["risk_level"] == "HIGH"
    s = c.as_(AUTHOR).get("/qe/quality-costs/summary").json()
    assert s["cost_of_poor_quality"] == "150.00" and s["copq_share_pct"] == "75.00"


# ── CAPA / deviation / CoA / audit hardening on /qms ─────────────────────────

def _ca(db, status=CorrectiveActionStatus.IN_PROGRESS, root=None, owner=None, steps=()):
    ca = db.add(CorrectiveAction(id=uuid.uuid4(), ca_no="CA-1", title="t", description="d", status=status,
                                 severity=RiskLevel.MEDIUM, root_cause_analysis=root, assigned_to_id=owner))
    ca.steps = [db.add(CorrectiveActionStep(id=uuid.uuid4(), corrective_action_id=ca.id, step_no=i + 1,
                                            step_description="s", is_completed=done))
                for i, done in enumerate(steps)]
    return ca


def test_capa_lifecycle_guards(env):
    db, c = env
    owner = _user(*ALL)
    ca = _ca(db, owner=owner.id, steps=(True, False))
    assert c.as_(owner).patch(f"/qms/corrective-actions/{ca.id}", json={"status": "VERIFIED"}).status_code == 409
    r = c.as_(owner).patch(f"/qms/corrective-actions/{ca.id}", json={"status": "COMPLETED"})
    assert r.status_code == 409 and "root cause" in r.json()["detail"]
    assert c.as_(owner).post(f"/qms/corrective-actions/{ca.id}/verify",
                             params={"effectiveness_check": "ok"}).status_code == 409
    ca.steps[1].is_completed = True
    assert c.as_(owner).patch(f"/qms/corrective-actions/{ca.id}", json={
        "status": "COMPLETED", "root_cause_analysis": "Worn seal"}).status_code == 200
    assert c.as_(owner).post(f"/qms/corrective-actions/{ca.id}/verify",
                             params={"effectiveness_check": "ok"}).status_code == 409
    assert c.as_(APPROVER).post(f"/qms/corrective-actions/{ca.id}/verify",
                                params={"effectiveness_check": "No recurrence"}).json()["status"] == "VERIFIED"
    assert c.as_(owner).patch(f"/qms/corrective-actions/{ca.id}", json={"title": "x"}).status_code == 409


def test_capa_owner_cannot_dodge_verification_rules(env):
    db, c = env
    owner, colleague = _user(*ALL), _user(*ALL)
    ca = _ca(db, status=CorrectiveActionStatus.COMPLETED, root="Seal", owner=owner.id, steps=(True,))
    reassign = c.as_(owner).patch(f"/qms/corrective-actions/{ca.id}", json={"assigned_to_id": str(colleague.id)})
    assert reassign.status_code == 409
    seed = c.as_(owner).patch(f"/qms/corrective-actions/{ca.id}", json={"effectiveness_check": "looks fine"})
    assert seed.status_code == 409
    assert ca.assigned_to_id == owner.id and ca.effectiveness_check is None


def test_unscoped_deviation_resolution_uses_global_approval(env):
    db, c = env
    dev = _deviation(db, None)
    body = {"status": "RESOLVED", "root_cause": "Sensor drift", "immediate_action": "Recalibrated"}
    assert c.as_(_user("quality.view", "quality.edit")).patch(f"/qms/deviations/{dev.id}", json=body).status_code == 403
    assert c.as_(APPROVER).patch(f"/qms/deviations/{dev.id}", json=body).status_code == 200
    assert dev.status == DeviationStatus.RESOLVED
    assert c.as_(APPROVER).patch(f"/qms/deviations/{dev.id}", json={"root_cause": "edited"}).status_code == 409


def test_capa_edit_requires_quality_permission(env):
    db, c = env
    ca = _ca(db)
    assert c.as_(_user("quality.view")).patch(f"/qms/corrective-actions/{ca.id}",
                                             json={"title": "x"}).status_code == 403


def test_deviation_cannot_move_backwards(env):
    db, c = env
    dev = _deviation(db, uuid.uuid4(), status=DeviationStatus.UNDER_REVIEW)
    r = c.as_(APPROVER).patch(f"/qms/deviations/{dev.id}", json={"status": "OPEN"})
    assert r.status_code == 409
    assert c.as_(_user("quality.view")).post("/qms/deviations", json={
        "deviation_type": "OOS", "description": "d"}).status_code == 403


def test_coa_issue_requires_independent_approver_and_passed_inspection(env):
    db, c = env
    lot = uuid.uuid4()
    insp = db.add(QCInspection(id=uuid.uuid4(), inspection_no="I1", qc_type=QCType.FINISHED_GOODS,
                               status=QCStatus.FAILED, lot_id=lot, inspection_date=date.today()))
    old = db.add(CertificateOfAnalysis(id=uuid.uuid4(), coa_no="COA-0", lot_id=lot, issue_date=date.today(),
                                       status="ISSUED", overall_result="PASS"))
    coa = db.add(CertificateOfAnalysis(id=uuid.uuid4(), coa_no="COA-1", lot_id=lot, inspection_id=insp.id,
                                       issue_date=date.today(), status="DRAFT", overall_result="PASS",
                                       issued_by_id=AUTHOR.id))
    assert c.as_(AUTHOR).post(f"/qms/coa/{coa.id}/issue").status_code == 409
    assert c.as_(APPROVER).post(f"/qms/coa/{coa.id}/issue").status_code == 409
    insp.status = QCStatus.PASSED
    no_status = c.as_(APPROVER).post(f"/qms/coa/{coa.id}/issue")
    assert no_status.status_code == 409 and "release status" in no_status.json()["detail"]
    insp.lot_id = None
    db.add(LotQualityStatus(id=uuid.uuid4(), lot_id=lot, hold_flag=False, quarantine_flag=False))
    assert c.as_(APPROVER).post(f"/qms/coa/{coa.id}/issue").status_code == 409  # inspection not of this lot
    insp.lot_id = lot
    db.rows[LotQualityStatus][0].hold_flag = True
    assert c.as_(APPROVER).post(f"/qms/coa/{coa.id}/issue").status_code == 409
    db.rows[LotQualityStatus][0].hold_flag = False
    assert c.as_(APPROVER).post(f"/qms/coa/{coa.id}/issue").json()["status"] == "ISSUED"
    assert old.status == "SUPERSEDED"
    assert c.as_(_user("quality.view")).post("/qms/coa", json={}).status_code == 403


def test_audit_close_lifecycle_creates_capa_for_failures(env):
    db, c = env
    audit = db.add(QualityAuditChecklist(id=uuid.uuid4(), audit_ref="AUD-1", standard="BRC", audit_type="INTERNAL",
                                         audit_date=date.today(), result="IN_PROGRESS",
                                         items=[{"section": "1", "item": "Policy", "result": "pending"},
                                                {"section": "2", "item": "HACCP", "result": "pending"}]))
    url = f"/qms/audit-checklists/{audit.id}"
    assert c.as_(APPROVER).post(f"{url}/close").status_code == 409
    assert c.as_(AUTHOR).patch(f"{url}/items", json=[{"item_index": 1, "result": "fail"}]).status_code == 422
    assert c.as_(AUTHOR).patch(f"{url}/items", json=[{"item_index": 5, "result": "pass"}]).status_code == 422
    assert c.as_(AUTHOR).patch(f"{url}/items", json=[
        {"item_index": 0, "result": "pass"},
        {"item_index": 1, "result": "fail", "finding": "CCP log gaps"}]).status_code == 200
    closed = c.as_(APPROVER).post(f"{url}/close").json()
    assert closed["corrective_action_id"]
    capa = db.rows[CorrectiveAction][0]
    assert capa.trigger_type == "AUDIT" and capa.trigger_id == audit.id and "CCP log gaps" in capa.description
    assert c.as_(AUTHOR).patch(f"{url}/items", json=[{"item_index": 0, "result": "fail",
                                                       "finding": "x"}]).status_code == 409
    assert c.as_(APPROVER).post(f"{url}/close").status_code == 409


def test_aql_plan_create_validates_and_requires_permission(env):
    _, c = env
    body = {"plan_code": "AQL-1", "plan_name": "Caps", "lot_size_min": 1, "lot_size_max": 500, "sample_size": 50,
            "aql_value": "1.0", "acceptance_number": 2, "rejection_number": 2}
    assert c.as_(_user("quality.view")).post("/qms/aql-plans", json=body).status_code == 403
    assert c.as_(AUTHOR).post("/qms/aql-plans", json=body).status_code == 422
    assert c.as_(AUTHOR).post("/qms/aql-plans", json=body | {"rejection_number": 3}).status_code == 201
    r = c.as_(AUTHOR).post("/qe/aql/evaluate", json={"lot_size": 300, "sample_inspected": 50, "defects_found": 3})
    assert r.json()["decision"] == "REJECT"


# ── complaint / recall → CAPA ────────────────────────────────────────────────

def test_complaint_capa_is_created_once_and_recall_close_waits_for_it(env):
    from app.models.consumer_complaints import ComplaintSeverity, ConsumerComplaint
    from app.models.traceability import RecallHeader, RecallSeverity, RecallStatus, RecallTrigger, RecallType
    from app.services import recall_service

    db, c = env
    comp = db.add(ConsumerComplaint(id=uuid.uuid4(), complaint_ref="CC-1", product_name="Juice",
                                    severity=ComplaintSeverity.SAFETY, description="Glass found"))
    first = c.as_(AUTHOR).post(f"/qe/complaints/{comp.id}/capa").json()
    second = c.as_(AUTHOR).post(f"/qe/complaints/{comp.id}/capa").json()
    assert first["created"] is True and second["created"] is False and first["ca_no"] == second["ca_no"]
    assert db.rows[CorrectiveAction][0].severity == RiskLevel.CRITICAL

    recall = db.add(RecallHeader(id=uuid.uuid4(), recall_no="RCL-1", recall_type=RecallType.market,
                                 recall_reason="Glass", trigger_source=RecallTrigger.complaint,
                                 severity_level=RecallSeverity.critical, status=RecallStatus.contained,
                                 initiation_datetime=datetime.utcnow()))
    import asyncio
    with pytest.raises(recall_service.RecallClosureBlocked, match="live recall"):
        asyncio.run(recall_service.close_recall(db, recall.id))
    c.as_(AUTHOR).post(f"/qe/recalls/{recall.id}/capa")
    links = c.as_(AUTHOR).get("/qe/capa-links", params={"trigger_type": "RECALL", "trigger_id": str(recall.id)}).json()
    assert len(links) == 1

    import asyncio
    with pytest.raises(recall_service.RecallClosureBlocked):
        asyncio.run(recall_service.close_recall(db, recall.id))
    next(ca for ca in db.rows[CorrectiveAction] if ca.trigger_type == "RECALL").status = CorrectiveActionStatus.VERIFIED
    asyncio.run(recall_service.close_recall(db, recall.id))
    assert recall.status == RecallStatus.closed


# ── SPC escalation ───────────────────────────────────────────────────────────

async def test_spc_signals_recorded_once_and_escalated(monkeypatch):
    db = FakeDB()
    product = uuid.uuid4()
    insp = db.add(QCInspection(id=uuid.uuid4(), inspection_no="I1", qc_type=QCType.IN_PROCESS,
                               status=QCStatus.PASSED, product_id=product, lot_id=uuid.uuid4(),
                               inspection_date=date.today()))
    from app.models.quality import QCTestResult
    results = [db.add(QCTestResult(id=uuid.uuid4(), inspection_id=insp.id, parameter_name="Brix",
                                   parameter_type="NUMERIC", numeric_value=Decimal(v)))
               for v in ["10", "10.2", "9.8", "10.1", "9.9", "10", "14"]]

    async def _series(*a, **k):
        return results
    monkeypatch.setattr(qa, "load_spc_series", _series)
    out = await qa.record_spc_signals(db, product, "Brix", AUTHOR.id)
    assert out["new_signals"] >= 1 and out["deviation_id"]
    dev = db.rows[QCDeviation][0]
    assert dev.deviation_type == "SPC_OUT_OF_CONTROL" and dev.severity == RiskLevel.HIGH
    assert dev.inspection_id == insp.id and dev.lot_id == insp.lot_id
    assert dev.corrective_action_id is not None  # HIGH deviations open a CAPA
    again = await qa.record_spc_signals(db, product, "Brix", AUTHOR.id)
    assert again["new_signals"] == 0 and again["deviation_id"] is None
    assert len(db.rows[SPCSignal]) == out["new_signals"]


# ── measurement controls on result recording ─────────────────────────────────

async def test_measurement_controls_instrument_and_skill():
    from app.api.v1.endpoints.quality import _measurement_control_errors

    db = FakeDB()
    skill = uuid.uuid4()
    method = db.add(QCTestMethod(id=uuid.uuid4(), method_code="TM-PH", version=1, name="pH", is_active=True,
                                 requires_instrument=True, instrument_type="pH meter", required_skill_id=skill))
    param = db.add(QCTemplateParameter(id=uuid.uuid4(), template_id=uuid.uuid4(), parameter_name="pH",
                                       parameter_type="NUMERIC", test_method_id=method.id))
    inst = db.add(InstrumentCalibration(id=uuid.uuid4(), instrument_id="PH-01", instrument_name="pH",
                                        instrument_type="pH meter", status="OVERDUE", is_active=True,
                                        next_calibration_due=date.today() - timedelta(days=1)))
    tester = uuid.uuid4()

    errors = await _measurement_control_errors(db, {"template_parameter_id": param.id}, tester)
    assert any("requires a calibrated instrument" in e for e in errors)
    assert any("qualification" in e for e in errors)

    errors = await _measurement_control_errors(
        db, {"template_parameter_id": param.id, "test_method_id": uuid.uuid4()}, tester)
    assert errors == ["The result must use the test method defined on its template parameter."]

    inst.status, inst.next_calibration_due = "CURRENT", date.today() + timedelta(days=90)
    emp = db.add(Employee(id=uuid.uuid4(), user_id=tester))
    op = db.add(OperatorProfile(id=uuid.uuid4(), operator_code="OP1", full_name="Lab", employee_id=emp.id,
                                active_flag=True))
    db.add(OperatorSkillCert(id=uuid.uuid4(), operator_id=op.id, skill_id=skill, approved_flag=True,
                             certification_required=True, certification_expiry=date.today() + timedelta(days=200)))
    data = {"template_parameter_id": param.id, "instrument_calibration_id": inst.id}
    assert await _measurement_control_errors(db, data, tester) == []
    assert data["test_method_id"] == method.id
