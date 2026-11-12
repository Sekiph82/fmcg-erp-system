"""M36.S00.T004 findings: CRM writes need edit rights + record scope; aggregates need company-wide view;
mailboxes are personal; demo inbox sync never runs outside development."""
from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import crm_pipeline, email_integration
from app.core.deps import get_current_user, get_db
from app.models.crm import CRMActivity, CRMRecord, CRMRecordType, CRMStatus
from app.models.email_integration import EmailAccount, EmailThread

REGION_IN, REGION_OUT = "R-NAIROBI", "R-MOMBASA"


def _scope(region):
    return SimpleNamespace(scope_type="sales_region", scope_id=region, scope_name=None, is_active=True,
                           can_view=True, can_edit=True, can_create=True, can_cancel=False, can_delete=False,
                           can_approve=False)


def _user(*codes, regions=(), superuser=False):
    perms = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in codes]
    role = SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[_scope(r) for r in regions])
    return SimpleNamespace(id=uuid.uuid4(), is_superuser=superuser, roles=[role], access_scopes=[],
                           full_name="u", username="u", email="u@example.invalid")


IN_REC = CRMRecord(id=uuid.uuid4(), record_type=CRMRecordType.OPPORTUNITY, company_name="In scope",
                   sales_region_id=REGION_IN, status=CRMStatus.OPEN)
OUT_REC = CRMRecord(id=uuid.uuid4(), record_type=CRMRecordType.OPPORTUNITY, company_name="Other region",
                    sales_region_id=REGION_OUT, status=CRMStatus.OPEN)
OUT_ACT = CRMActivity(id=uuid.uuid4(), crm_record_id=OUT_REC.id)


class _DB:
    def __init__(self, objects):
        self.objects = objects

    async def get(self, _model, key):
        return self.objects.get(str(key))


@pytest.fixture
def crm(monkeypatch):
    records = {str(IN_REC.id): IN_REC, str(OUT_REC.id): OUT_REC}

    async def get_record(_db, record_id):
        return records.get(str(record_id))

    async def ok(*_a, **_k):
        return []

    monkeypatch.setattr(crm_pipeline.svc, "get_record", get_record)
    for name in ("get_record_360", "get_activities", "get_dashboard", "get_forecast", "create_stage", "seed_default_stages"):
        monkeypatch.setattr(crm_pipeline.svc, name, ok)
    app = FastAPI()
    app.include_router(crm_pipeline.router, prefix="/crm")

    async def _db():
        yield _DB({str(OUT_ACT.id): OUT_ACT})

    app.dependency_overrides[get_db] = _db

    def as_(user):
        app.dependency_overrides[get_current_user] = lambda: user
        return TestClient(app)

    return as_


def test_scoped_viewer_cannot_read_other_regions_360_or_activities(crm):
    c = crm(_user("crm.view_own_region", regions=[REGION_IN]))
    assert c.get(f"/crm/records/{OUT_REC.id}/360").status_code == 403
    assert c.get(f"/crm/activities?record_id={OUT_REC.id}").status_code == 403
    assert c.get(f"/crm/records/{IN_REC.id}/360").status_code != 403
    assert c.get("/crm/activities").status_code == 403          # all records' activities
    assert c.get("/crm/dashboard").status_code == 403           # company-wide aggregates
    assert c.get("/crm/forecast").status_code == 403


def test_view_only_users_cannot_change_pipeline_or_records(crm):
    c = crm(_user("crm.view_all"))
    assert c.get("/crm/dashboard").status_code == 200
    assert c.post("/crm/stages/seed-defaults").status_code == 403
    assert c.post("/crm/activities", json={"crm_record_id": str(IN_REC.id), "activity_type": "CALL",
                                           "subject": "x"}).status_code in (403, 422)
    assert c.post(f"/crm/records/{IN_REC.id}/update-score").status_code == 403
    assert c.post("/crm/ai/run-pipeline-risk").status_code == 403


def test_scoped_editor_cannot_touch_out_of_scope_records(crm):
    c = crm(_user("crm.view_own_region", "crm.edit_own_region", regions=[REGION_IN]))
    assert c.post(f"/crm/activities/{OUT_ACT.id}/complete", json={"result_status": "COMPLETED"}).status_code == 403
    assert c.post(f"/crm/records/{OUT_REC.id}/update-score").status_code == 403
    assert c.post(f"/crm/records/{IN_REC.id}/interest-lines",
                  json={"crm_record_id": str(OUT_REC.id), "product_id": str(uuid.uuid4())}).status_code == 422
    assert c.post("/crm/stages/seed-defaults").status_code == 403  # pipeline config is company-wide


def test_company_wide_editor_can_configure(crm):
    assert crm(_user("crm.view_all", "crm.edit_all")).post("/crm/stages/seed-defaults").status_code == 200


# ── mailboxes ────────────────────────────────────────────────────────────────

class _MailDB(_DB):
    async def execute(self, _q):
        raise AssertionError("listing is not exercised here")

    async def commit(self):
        return None


def _mail_client(user, objects):
    app = FastAPI()
    app.include_router(email_integration.router, prefix="/email")

    async def _db():
        yield _MailDB(objects)

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def test_mailboxes_are_personal_and_demo_sync_is_dev_only(monkeypatch):
    owner, other = _user(), _user()
    account = EmailAccount(id=uuid.uuid4(), email_address="rep@example.invalid", created_by_id=owner.id,
                           is_active=True)
    thread = EmailThread(id=uuid.uuid4(), account_id=account.id, subject="s")
    objects = {str(account.id): account, str(thread.id): thread}
    c = _mail_client(other, objects)
    assert c.delete(f"/email/accounts/{account.id}").status_code == 404
    assert c.post("/email/send", json={"account_id": str(account.id), "to_emails": ["x@example.invalid"],
                                       "subject": "s", "body_text": "b"}).status_code == 404
    monkeypatch.setattr(email_integration.settings, "ENVIRONMENT", "production")
    assert _mail_client(owner, objects).post(f"/email/sync/{account.id}").status_code == 501
