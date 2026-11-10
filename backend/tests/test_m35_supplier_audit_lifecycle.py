"""M35.S05.T001 — supplier audit lifecycle (in-memory session, no PostgreSQL).

Supplier approvals start PENDING, are granted only on a closed passing audit of
the same supplier by someone other than the audit closer, cannot outlast the
next audit, and a failed supplier audit suspends the supplier's active
approvals and raises a supplier-tagged CAPA.
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints.qms import router as qms_router
from app.core.deps import get_current_user, get_db
from app.models.master import Supplier
from app.models.quality import (
    CorrectiveAction, QualityAuditChecklist, SupplierFoodSafetyApproval, SupplierFoodSafetyStatus,
)
from app.services import qa_enterprise_service as qa
from fake_async_db import FakeDB

ALL = ("quality.view", "quality.create", "quality.edit", "quality.approve")
TODAY = date.today()


def _user(*codes):
    perms = [SimpleNamespace(code=c, is_active=True) for c in codes]
    return SimpleNamespace(id=uuid.uuid4(), is_superuser=False, full_name="u", username="u",
                           roles=[SimpleNamespace(is_active=True, permissions=perms, access_scopes=[])])


AUDITOR, QA_HEAD, VIEWER = _user(*ALL), _user(*ALL), _user("quality.view")


# ── pure rules ───────────────────────────────────────────────────────────────

def _approval(status="PENDING", supplier_id="S1", critical=0, decided_at=None):
    return SimpleNamespace(status=status, supplier_id=supplier_id, critical_findings=critical, decided_at=decided_at)


_NO_NEXT = object()


def _audit(result="PASS", supplier_id="S1", closed=True, closer=None, next_audit=_NO_NEXT, audit_id="AUD"):
    return SimpleNamespace(id=audit_id, result=result, supplier_id=supplier_id,
                           closed_at=datetime.now(timezone.utc) if closed else None, closed_by_id=closer,
                           next_audit_date=TODAY + timedelta(days=365) if next_audit is _NO_NEXT else next_audit)


def _errors(approval, target, audit=None, actor="A", expiry=TODAY + timedelta(days=200), notes=None, latest="AUD"):
    return qa.supplier_approval_decision_errors(approval, target, audit=audit, actor_id=actor, expiry_date=expiry,
                                                notes=notes, today=TODAY, latest_audit_id=latest)


def test_approval_needs_closed_passing_audit_of_same_supplier():
    assert _errors(_approval(), "APPROVED", _audit()) == []
    assert "closed supplier audit" in " ".join(_errors(_approval(), "APPROVED"))
    assert "not performed on this supplier" in " ".join(_errors(_approval(), "APPROVED", _audit(supplier_id="S2")))
    assert "not closed" in " ".join(_errors(_approval(), "APPROVED", _audit(closed=False)))
    assert "does not support APPROVED" in " ".join(_errors(_approval(), "APPROVED", _audit("CONDITIONAL_PASS")))
    assert "does not support CONDITIONAL" in " ".join(
        _errors(_approval(), "CONDITIONAL", _audit("FAIL"), notes="x"))
    assert _errors(_approval(), "CONDITIONAL", _audit("CONDITIONAL_PASS"), notes="Retest in 90 days") == []


def test_approval_segregation_expiry_and_findings():
    assert "closed the audit" in " ".join(_errors(_approval(), "APPROVED", _audit(closer="A"), actor="A"))
    assert "future expiry" in " ".join(_errors(_approval(), "APPROVED", _audit(), expiry=TODAY))
    assert "outlast" in " ".join(_errors(_approval(), "APPROVED", _audit(next_audit=TODAY + timedelta(days=30))))
    assert "overdue" in " ".join(_errors(_approval(), "APPROVED", _audit(next_audit=TODAY - timedelta(days=1)),
                                         expiry=TODAY + timedelta(days=1)))
    assert "critical findings" in " ".join(_errors(_approval(critical=1), "APPROVED", _audit()))
    assert "linked to a supplier" in " ".join(_errors(_approval(supplier_id=None), "APPROVED", _audit()))
    assert "next audit date" in " ".join(_errors(_approval(), "APPROVED", _audit(next_audit=None)))


def test_only_latest_audit_newer_than_last_decision_is_evidence():
    # an older PASS cannot override a later (e.g. failed) audit of the same supplier
    assert "most recent closed audit" in " ".join(_errors(_approval(), "APPROVED", _audit(), latest="NEWER"))
    # a downgrade/suspension made after the audit cannot be undone with that same audit
    later = datetime.now(timezone.utc) + timedelta(minutes=1)
    assert "predates the last decision" in " ".join(
        _errors(_approval("CONDITIONAL", decided_at=later), "APPROVED", _audit()))


def test_transition_map_and_reasons():
    assert "cannot move" in " ".join(_errors(_approval("REJECTED"), "APPROVED", _audit()))
    assert "requires notes" in " ".join(_errors(_approval("APPROVED"), "SUSPENDED"))
    assert _errors(_approval("APPROVED"), "SUSPENDED", notes="Pest finding") == []
    assert _errors(_approval("APPROVED"), "CONDITIONAL", notes="Downgrade") == []  # downgrade needs no audit
    assert _errors(_approval("SUSPENDED"), "PENDING") == []
    assert qa.supplier_approval_needs_audit("CONDITIONAL", "APPROVED")
    assert not qa.supplier_approval_needs_audit("APPROVED", "CONDITIONAL")


# ── API flow ─────────────────────────────────────────────────────────────────

@pytest.fixture
def env():
    db = FakeDB()
    app = FastAPI()
    app.include_router(qms_router, prefix="/qms")

    async def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    client = TestClient(app)

    def as_(user):
        app.dependency_overrides[get_current_user] = lambda: user
        return client

    supplier = db.add(Supplier(id=uuid.uuid4(), code="SUP-1", name="Acme Dairy"))
    return db, as_, supplier


def _run_audit(as_, supplier, results, closer=QA_HEAD, next_audit=TODAY + timedelta(days=365)):
    audit = as_(AUDITOR).post("/qms/audit-checklists", json={
        "standard": "HALAL", "audit_type": "THIRD_PARTY", "audit_date": TODAY.isoformat(),
        "lead_auditor": "J. Auditor", "supplier_id": str(supplier.id)}).json()
    assert audit["supplier_id"] == str(supplier.id)
    body = [{"item_index": i, "result": r, "finding": "gap" if r == "fail" else None} for i, r in enumerate(results)]
    assert as_(AUDITOR).patch(f"/qms/audit-checklists/{audit['id']}/items", json=body).status_code == 200
    params = {"next_audit_date": next_audit.isoformat()} if next_audit else {}
    closed = as_(closer).post(f"/qms/audit-checklists/{audit['id']}/close", params=params)
    assert closed.status_code == 200, closed.text
    return audit["id"], closed.json()


def test_supplier_approval_lifecycle_end_to_end(env):
    db, as_, supplier = env
    body = {"supplier_id": str(supplier.id), "approval_type": "HALAL"}
    assert as_(VIEWER).post("/qms/supplier-food-safety", json=body).status_code == 403
    assert as_(AUDITOR).post("/qms/supplier-food-safety", json=body | {"status": "APPROVED"}).status_code == 422
    assert as_(AUDITOR).post("/qms/supplier-food-safety",
                             json=body | {"supplier_id": str(uuid.uuid4())}).status_code == 404
    fsa = as_(AUDITOR).post("/qms/supplier-food-safety", json=body).json()
    assert fsa["status"] == "PENDING" and fsa["supplier_name"] == "Acme Dairy" and fsa["is_current"] is False

    # direct status/expiry edits are refused; decision needs approve permission and audit evidence
    url = f"/qms/supplier-food-safety/{fsa['id']}"
    assert as_(QA_HEAD).patch(url, params={"status": "APPROVED"}).status_code == 409
    assert as_(QA_HEAD).patch(url, params={"notes": "ok", "major_findings": 2}).status_code == 200
    expiry = (TODAY + timedelta(days=300)).isoformat()
    assert as_(_user("quality.view", "quality.edit")).post(
        f"{url}/decision", json={"status": "APPROVED"}).status_code == 403
    no_audit = as_(QA_HEAD).post(f"{url}/decision", json={"status": "APPROVED", "expiry_date": expiry})
    assert no_audit.status_code == 409 and "closed supplier audit" in no_audit.json()["detail"]

    audit_id, _ = _run_audit(as_, supplier, ["pass"] * 6, next_audit=TODAY + timedelta(days=365))
    decision = {"status": "APPROVED", "audit_checklist_id": audit_id, "expiry_date": expiry}
    same_person = as_(QA_HEAD).post(f"{url}/decision", json=decision)
    assert same_person.status_code == 409 and "closed the audit" in same_person.json()["detail"]
    approved = as_(AUDITOR).post(f"{url}/decision", json=decision).json()
    assert approved["status"] == "APPROVED" and approved["is_current"] is True
    assert approved["audit_checklist_id"] == audit_id and approved["audit_score"] == 100.0
    assert approved["auditor"] == "J. Auditor" and approved["approval_date"] == TODAY.isoformat()
    assert approved["decided_by_id"] == str(AUDITOR.id)

    listed = as_(VIEWER).get("/qms/supplier-food-safety", params={"supplier_id": str(supplier.id)}).json()
    assert [r["id"] for r in listed] == [fsa["id"]]
    assert as_(_user()).get("/qms/supplier-food-safety").status_code == 403

    # a failed re-audit suspends the approval and raises a supplier CAPA
    _, closed = _run_audit(as_, supplier, ["fail"] * 6)
    assert closed["suspended_approval_ids"] == [fsa["id"]]
    row = db.rows[SupplierFoodSafetyApproval][0]
    assert row.status == SupplierFoodSafetyStatus.SUSPENDED and "failed" in row.decision_notes
    capa = next(c for c in db.rows[CorrectiveAction] if c.trigger_type == "AUDIT")
    assert capa.supplier_id == supplier.id

    # suspended → re-audit (PENDING) needs only edit; cannot jump straight back to APPROVED
    assert as_(QA_HEAD).post(f"{url}/decision", json=decision).status_code == 409
    assert as_(_user("quality.edit")).post(f"{url}/decision", json={"status": "PENDING"}).status_code == 200
    # the old PASS audit is no longer evidence: the failed audit is the latest, and it predates the re-audit request
    stale = as_(AUDITOR).post(f"{url}/decision", json=decision)
    assert stale.status_code == 409 and "most recent closed audit" in stale.json()["detail"]
    reaudit_id, _ = _run_audit(as_, supplier, ["pass"] * 6)
    again = as_(AUDITOR).post(f"{url}/decision", json=decision | {"audit_checklist_id": reaudit_id})
    assert again.status_code == 200 and again.json()["status"] == "APPROVED"
    # finding counts are frozen on an active approval
    assert as_(QA_HEAD).patch(url, params={"critical_findings": 1}).status_code == 409


def test_audit_routes_need_view_permission_and_closed_audit_is_frozen(env):
    db, as_, supplier = env
    assert as_(_user()).get("/qms/audit-checklists").status_code == 403
    assert as_(AUDITOR).post("/qms/audit-checklists", json={
        "standard": "BRC", "audit_date": TODAY.isoformat(), "supplier_id": str(uuid.uuid4())}).status_code == 404
    audit = as_(AUDITOR).post("/qms/audit-checklists", json={
        "standard": "HALAL", "audit_date": TODAY.isoformat(), "supplier_id": str(supplier.id)}).json()
    as_(AUDITOR).patch(f"/qms/audit-checklists/{audit['id']}/items",
                       json=[{"item_index": i, "result": "pass"} for i in range(6)])
    no_next = as_(QA_HEAD).post(f"/qms/audit-checklists/{audit['id']}/close")
    assert no_next.status_code == 409 and "next audit date" in no_next.json()["detail"]
    audit_id, _ = _run_audit(as_, supplier, ["pass"] * 6)
    assert as_(AUDITOR).patch(f"/qms/audit-checklists/{audit_id}", params={"notes": "x"}).status_code == 409
    one = as_(VIEWER).get(f"/qms/audit-checklists/{audit_id}").json()
    assert one["supplier_id"] == str(supplier.id) and one["closed_at"]
    filtered = as_(VIEWER).get("/qms/audit-checklists", params={"supplier_id": str(supplier.id)}).json()
    assert audit_id in [a["id"] for a in filtered] and len(filtered) == 2
    assert all(a.supplier_id == supplier.id for a in db.rows[QualityAuditChecklist])
