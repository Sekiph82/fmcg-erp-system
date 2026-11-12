"""M36.S01.T004 CRM automation on disposable PostgreSQL: events from stage history, idempotent runs
under replay and two concurrent workers, conditions, retries with backoff, no replay for new rules."""
from __future__ import annotations

import asyncio
import os
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete, func, select

from app.db.session import AsyncSessionLocal, engine
from app.models.crm import (
    CRMActivity, CRMAutomationRun, CRMPipelineStage, CRMRecord, CRMRecordType, CRMStageHistory, CRMStageType, CRMStatus,
)
from app.models.custom_fields import EntityType, WorkflowTriggerRule
from app.models.notifications import Notification
from app.models.user import User
from app.services import crm_automation_service as auto

TASK_DB_ENV = "M36_S01_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M36_S01_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m36_s01_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _rule(name, trigger, action, payload, **cond):
    return WorkflowTriggerRule(rule_name=name, entity_type=EntityType.CRM_RECORD, trigger_event=trigger,
                               action_type=action, action_payload=payload, active_flag=True,
                               created_at=datetime.utcnow() - timedelta(seconds=5), **cond)


@pytest.mark.asyncio
async def test_rules_run_once_per_event_across_workers_with_retries():
    s = uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        await db.execute(delete(WorkflowTriggerRule).where(WorkflowTriggerRule.entity_type == EntityType.CRM_RECORD))
        prop = CRMPipelineStage(stage_code=f"PROP-{s}", stage_name="Proposal", stage_type=CRMStageType.OPPORTUNITY, sequence_no=5)
        db.add_all([prop, User(email=f"mgr-{s}@example.invalid", username=f"mgr{s}", full_name="Sales Manager", hashed_password="x")])
        db.add_all([
            _rule("Follow up new leads", "created", "create_task", {"subject": "Call new lead", "due_in_days": 1},
                  condition_field="record_type", condition_operator="eq", condition_value="LEAD"),
            _rule("Route proposals", "stage_changed", "assign_owner", {"rep_ids": ["rep-x", "rep-y"]},
                  condition_field="to_stage_code", condition_operator="eq", condition_value=f"PROP-{s}"),
            _rule("Tell manager about wins", "won", "notify", {"usernames": [f"mgr{s}"], "title": "Deal won"}),
            _rule("Broken notify", "won", "notify", {"usernames": ["nobody-here"], "title": "x"}),
        ])
        await db.commit()
        lead = CRMRecord(record_type=CRMRecordType.LEAD, company_name=f"Lead {s}")
        opp = CRMRecord(record_type=CRMRecordType.OPPORTUNITY, company_name=f"Opp {s}", expected_revenue=Decimal("5"))
        db.add_all([lead, opp])
        await db.commit()
        opp.stage_id = prop.id
        await db.commit()
        opp.status = CRMStatus.WON
        await db.commit()
        lead_id, opp_id = lead.id, opp.id

    async with AsyncSessionLocal() as db:
        first = await auto.enqueue(db)
        runs = (await db.execute(select(CRMAutomationRun.rule_name, CRMAutomationRun.event_key))).all()
        hist = (await db.execute(select(CRMStageHistory.from_status, CRMStageHistory.to_status, CRMStageHistory.from_stage_id.isnot(None), CRMStageHistory.to_stage_id.isnot(None)))).all()
        assert first == 4, (runs, hist)
        assert await auto.enqueue(db) == 0          # replaying the same events adds nothing

    async def worker():
        async with AsyncSessionLocal() as db:
            return await auto.process(db)

    a, b = await asyncio.gather(worker(), worker())                 # two API workers at once
    assert a["done"] + b["done"] == 3 and a["retry"] + b["retry"] == 1

    async with AsyncSessionLocal() as db:
        tasks = (await db.execute(select(CRMActivity).where(CRMActivity.crm_record_id == lead_id))).scalars().all()
        assert [t.subject for t in tasks] == ["Call new lead"] and tasks[0].created_by == "automation"
        assert (await db.get(CRMRecord, opp_id)).assigned_rep_id in {"rep-x", "rep-y"}
        assert (await db.execute(select(func.count()).select_from(Notification).where(
            Notification.reference_id == str(opp_id)))).scalar() == 1
        assert (await db.execute(select(func.count()).select_from(CRMActivity).where(
            CRMActivity.crm_record_id == opp_id))).scalar() == 0      # created rule only matches leads

        # the failing rule backs off, then gives up after 5 attempts with the error kept
        now = datetime.now(timezone.utc)
        for i in range(6):
            await auto.process(db, now=now + timedelta(hours=i + 1))
        broken = (await db.execute(select(CRMAutomationRun).where(CRMAutomationRun.rule_name == "Broken notify"))).scalar_one()
        assert (broken.status, broken.attempts) == ("FAILED", 5) and "active user" in broken.error
        done = (await db.execute(select(func.count()).select_from(CRMAutomationRun).where(CRMAutomationRun.status == "DONE"))).scalar()
        assert done == 3                                              # successes were not re-run

        # a rule created now does not fire for those older events
        db.add(WorkflowTriggerRule(rule_name="Late rule", entity_type=EntityType.CRM_RECORD, trigger_event="created",
                                   action_type="create_task", action_payload={"subject": "late"}, active_flag=True))
        await db.commit()
        assert await auto.enqueue(db) == 0

        # pausing then re-enabling a rule (endpoint sets activated_at) does not replay the paused period
        follow = (await db.execute(select(WorkflowTriggerRule).where(WorkflowTriggerRule.rule_name == "Follow up new leads"))).scalar_one()
        follow.active_flag = False
        await db.execute(delete(WorkflowTriggerRule).where(WorkflowTriggerRule.rule_name == "Late rule"))
        await db.commit()
        db.add(CRMRecord(record_type=CRMRecordType.LEAD, company_name=f"Paused-period lead {s}"))
        await db.commit()
        assert await auto.enqueue(db) == 0
        follow.active_flag, follow.activated_at = True, datetime.now(timezone.utc)
        await db.commit()
        assert await auto.enqueue(db) == 0
        db.add(CRMRecord(record_type=CRMRecordType.LEAD, company_name=f"After re-enable {s}"))
        await db.commit()
        assert await auto.enqueue(db) == 1

    with pytest.raises(ValueError):
        auto.validate("created", None, None, "set_field", {"field": "status", "value": "WON"})  # never sets status
