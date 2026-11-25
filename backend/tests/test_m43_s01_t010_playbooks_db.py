"""M43.S01.T010 playbooks, guided selling and deal plans (run at the M43 gate).

Unit: question validation (unique keys, unknown field mapping refused, show_if must reference an earlier question),
conditional visibility, required answers only for visible questions, typed answers, mapping onto whitelisted fields.
DB (M43_S01_DB=1): author cannot approve own playbook; approving v2 retires v1 (one published per family); a run
records the exact version; stage gate blocks leaving the stage until a completed run exists, then allows it;
deal-plan share link: customer ticks only customer steps; revoked link stops working.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.services import crm_playbook_service as pbs

QS = [{"key": "dm", "text": "Met the decision maker?", "type": "yesno", "required": True},
      {"key": "who", "text": "Who signs?", "type": "text", "required": True, "show_if": {"key": "dm", "equals": False}},
      {"key": "value", "text": "Order value", "type": "number", "maps_to": "expected_revenue"}]


def test_validation_and_conditionals():
    qs = pbs.validate_questions(QS)
    with pytest.raises(pbs.PlaybookError):
        pbs.validate_questions([{"key": "a", "type": "text", "maps_to": "status"}])
    with pytest.raises(pbs.PlaybookError):
        pbs.validate_questions([{"key": "a", "type": "text", "show_if": {"key": "b", "equals": 1}}])
    assert pbs.check_answers(qs, {"dm": True}, complete=True) == {"dm": True}          # 'who' hidden → not required
    with pytest.raises(pbs.PlaybookError):
        pbs.check_answers(qs, {"dm": False}, complete=True)                               # 'who' now required
    with pytest.raises(pbs.PlaybookError):
        pbs.check_answers(qs, {"dm": "yes"}, complete=False)                              # wrong type


def test_mapping():
    from app.models.crm import CRMRecord
    rec = CRMRecord(company_name="POVU Synthetic Outlet")
    changed = pbs.apply_mapping(rec, pbs.validate_questions(QS), {"dm": True, "value": 12500})
    assert changed == ["expected_revenue"] and rec.expected_revenue == Decimal("12500")


DB = pytest.mark.skipif(os.environ.get("M43_S01_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@DB
@pytest.mark.asyncio
async def test_approval_versions_and_stage_gate():
    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMPipelineStage, CRMPlaybook, CRMPlaybookRun, CRMRecord, CRMRecordType
    from app.models.user import User
    from app.services.crm_stage_gate import check_stage_exit
    async with AsyncSessionLocal() as db:
        author = User(id=uuid.uuid4(), email=f"a-{uuid.uuid4().hex[:6]}@povu-demo.test", username=f"syn-{uuid.uuid4().hex[:12]}", hashed_password="x", full_name="A", is_active=True)
        approver = User(id=uuid.uuid4(), email=f"b-{uuid.uuid4().hex[:6]}@povu-demo.test", username=f"syn-{uuid.uuid4().hex[:12]}", hashed_password="x", full_name="B", is_active=True)
        db.add_all([author, approver])
        await db.flush()
        stages = (await db.execute(select(CRMPipelineStage).order_by(CRMPipelineStage.sequence_no).limit(2))).scalars().all()
        rec = CRMRecord(id=uuid.uuid4(), record_type=CRMRecordType.OPPORTUNITY, company_name="POVU Synthetic Outlet",
                        stage_id=stages[0].id)
        db.add(rec)
        p1 = CRMPlaybook(family_id=uuid.uuid4(), version=1, name="Qualify", purpose="STAGE", stage_id=stages[0].id,
                         questions=pbs.validate_questions(QS), blocks_stage_exit=True, status="PENDING_APPROVAL",
                         created_by_id=author.id)
        db.add(p1)
        await db.flush()
        with pytest.raises(pbs.PlaybookError):
            await pbs.publish(db, p1, author)
        await pbs.publish(db, p1, approver)
        p2 = await pbs.new_version(db, p1, author.id)
        p2.status = "PENDING_APPROVAL"
        await pbs.publish(db, p2, approver)
        await db.flush()                              # endpoints commit here; sessions run without autoflush
        assert (p1.status, p2.status) == ("RETIRED", "PUBLISHED")
        with pytest.raises(HTTPException) as e:
            await check_stage_exit(db, rec, stages[1].id)
        assert e.value.status_code == 409
        db.add(CRMPlaybookRun(playbook_id=p1.id, crm_record_id=rec.id, answers={"dm": True}, completed=True,
                              completed_at=datetime.now(timezone.utc), created_at=datetime.now(timezone.utc)))
        await db.flush()
        await check_stage_exit(db, rec, stages[1].id)          # a completed run of any version of the family counts
        await db.rollback()


@DB
@pytest.mark.asyncio
async def test_shared_plan_customer_ticks_only_own_steps():
    from httpx import ASGITransport, AsyncClient

    from app.db.session import AsyncSessionLocal
    from app.main import app
    from app.models.crm import CRMDealPlan, CRMRecord, CRMRecordType
    async with AsyncSessionLocal() as db:
        rec = CRMRecord(id=uuid.uuid4(), record_type=CRMRecordType.OPPORTUNITY, company_name="POVU Synthetic Outlet")
        db.add(rec)
        await db.flush()
        token, h = pbs.share_token()
        plan = CRMDealPlan(crm_record_id=rec.id, title="Path to first order", shared=True, share_token_hash=h,
                           steps=pbs.clean_steps([{"id": "s1", "title": "Send price list", "owner": "us"},
                                                  {"id": "s2", "title": "Confirm shelf space", "owner": "customer"}]))
        db.add(plan)
        await db.commit()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            view = (await c.get(f"/api/v1/public/deal-plans/{token}")).json()
            assert set(view) == {"title", "steps"}
            assert (await c.post(f"/api/v1/public/deal-plans/{token}/steps", json={"step_id": "s1", "done": True})).status_code == 403
            assert (await c.post(f"/api/v1/public/deal-plans/{token}/steps", json={"step_id": "s2", "done": True})).status_code == 200
            plan.shared, plan.share_token_hash = False, None
            await db.commit()
            assert (await c.get(f"/api/v1/public/deal-plans/{token}")).status_code == 404


@pytest.fixture(autouse=True)
async def _dispose_engine():
    """Each test runs in its own event loop: drop pooled connections afterwards (same pattern as other DB tests)."""
    yield
    from app.db.session import engine
    await engine.dispose()
