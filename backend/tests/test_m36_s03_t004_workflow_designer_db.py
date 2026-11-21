"""M36.S03.T004 visual workflow designer on disposable PostgreSQL: graph validation (cycles, reachability, branches,
action settings), side-effect-free simulation, versioning with publish/rollback rights, and execution with
condition branches, delays, approvals and actions."""
from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import func, select

from app.api.v1.endpoints import crm_workflows as api
from app.db.session import AsyncSessionLocal, engine
from app.models.crm import CRMActivity, CRMRecord, CRMStageHistory, CRMTemperature, CRMWorkflowRun
from app.services import crm_workflow_service as wfs

TASK_DB_ENV = "M36_S03_T004_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M36_S03_T004_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m36_s03_t004_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _user(*codes):
    perms = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in codes]
    return SimpleNamespace(id=uuid4(), username="wf", is_superuser=False, access_scopes=[], roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])


def graph(delay_days=0):
    return {"nodes": [
        {"id": "t", "type": "trigger", "config": {"event": "created"}},
        {"id": "hot", "type": "condition", "config": {"field": "temperature", "operator": "eq", "value": "HOT"}},
        {"id": "wait", "type": "delay", "config": {"days": delay_days}},
        {"id": "ok", "type": "approval", "config": {"title": "Big POVU deal: assign key account manager?"}},
        {"id": "task", "type": "action", "config": {"action_type": "create_task", "payload": {"subject": "Call the buyer about POVU AllClean", "due_in_days": 1}}},
        {"id": "end", "type": "end"}, {"id": "end2", "type": "end"}],
        "edges": [{"from": "t", "to": "hot"}, {"from": "hot", "to": "wait", "branch": "yes"}, {"from": "hot", "to": "end2", "branch": "no"},
                  {"from": "wait", "to": "ok"}, {"from": "ok", "to": "task", "branch": "yes"}, {"from": "ok", "to": "end", "branch": "no"},
                  {"from": "task", "to": "end"}]}


@pytest.mark.asyncio
async def test_workflow_designer():
    s = uuid4().hex[:8]
    editor, approver, viewer = _user("crm.edit_all"), _user("crm.approve"), _user("crm.view_all")

    # validation
    assert wfs.validate(graph()) == []
    g = graph(); g["edges"].append({"from": "task", "to": "hot"}); g["edges"] = [e for e in g["edges"] if not (e["from"] == "task" and e["to"] == "end")]
    assert any("loops" in p for p in wfs.validate(g))
    g = graph(); g["nodes"].append({"id": "orphan", "type": "end"})
    assert any("Not reachable" in p for p in wfs.validate(g))
    g = graph(); g["edges"] = [e for e in g["edges"] if e.get("branch") != "no" or e["from"] != "hot"]
    assert any("'yes' and one 'no'" in p for p in wfs.validate(g))
    g = graph(); g["nodes"][4]["config"]["payload"] = {}
    assert any("subject" in p for p in wfs.validate(g))
    g = graph(); g["nodes"][0]["id"] = "x" * 41
    assert any("40 characters" in p for p in wfs.validate(g))
    assert wfs.validate({"nodes": ["junk"], "edges": []}) == ["Steps and connections must be objects."]
    g = graph(); g["nodes"].append({"id": "t2", "type": "trigger", "config": {"event": "won"}})
    assert any("Exactly one trigger" in p for p in wfs.validate(g))

    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]

        from app.models.user import User
        db.add(User(id=approver.id, email=f"apr-{s}@povu.example", username=f"apr{s}", full_name="Approver", hashed_password="x"))
        await db.commit()
        # rights: viewers cannot draft, editors cannot publish
        with pytest.raises(HTTPException):
            await api.EDIT(viewer)
        with pytest.raises(HTTPException):
            await api.PUBLISH(editor)

        wf = await api.create_workflow(api.WorkflowIn(name=f"Hot lead escalation {s}"), db, editor)
        wid = uuid.UUID(wf["id"])
        bad = await api.save_draft(wid, api.GraphIn(graph={"nodes": [], "edges": []}), db, editor)
        assert bad["problems"]
        with pytest.raises(HTTPException) as e:                                    # invalid versions never go live
            await api.publish(uuid.UUID(bad["id"]), db, approver)
        assert e.value.status_code == 422
        v1 = await api.save_draft(wid, api.GraphIn(graph=graph()), db, editor)
        assert v1["problems"] == [] and v1["version_no"] == 2

        # notify steps may only name users with company-wide CRM view
        bad_g = graph(); bad_g["nodes"][4]["config"] = {"action_type": "notify", "payload": {"usernames": ["nobody-" + s], "title": "x"}}
        drafted = await api.save_draft(wid, api.GraphIn(graph=bad_g), db, editor)
        assert any("company-wide CRM view" in p for p in drafted["problems"])
        with pytest.raises(HTTPException) as e:
            await api.publish(uuid.UUID(drafted["id"]), db, approver)
        assert e.value.status_code == 422

        # simulation changes nothing
        rec = CRMRecord(company_name=f"Mama Duka {s}", temperature=CRMTemperature.HOT)
        cold = CRMRecord(company_name=f"Cold Shop {s}", temperature=CRMTemperature.COLD)
        db.add_all([rec, cold])
        await db.commit()
        sim = await api.simulate(api.SimulateIn(graph=graph(), crm_record_id=rec.id), db, viewer)
        assert [st["node"] for st in sim["steps"]] == ["t", "hot", "wait", "ok", "task", "end"]
        sim_no = await api.simulate(api.SimulateIn(graph=graph(), crm_record_id=cold.id), db, viewer)
        assert [st["node"] for st in sim_no["steps"]] == ["t", "hot", "end2"]
        assert (await db.execute(select(func.count()).select_from(CRMActivity).where(CRMActivity.crm_record_id == rec.id))).scalar_one() == 0

        await api.publish(uuid.UUID(v1["id"]), db, approver)
        rid, cid = rec.id, cold.id

        # execution: events after publishing only
        now = datetime.now(timezone.utc)
        db.add_all([CRMStageHistory(crm_record_id=rid, to_status="OPEN", changed_at=now + timedelta(seconds=1)),
                    CRMStageHistory(crm_record_id=cid, to_status="OPEN", changed_at=now + timedelta(seconds=1))])
        await db.commit()
        assert await wfs.enqueue(db, now + timedelta(seconds=5)) == 2
        assert await wfs.enqueue(db, now + timedelta(seconds=6)) == 0              # each event once
        await wfs.process(db, now=now + timedelta(seconds=10))
        runs = {r.crm_record_id: r for r in (await db.execute(select(CRMWorkflowRun))).scalars().all()}
        assert runs[cid].status == "DONE"                                            # cold → "no" branch → end
        hot = runs[rid]
        assert hot.status == "WAITING_APPROVAL"
        with pytest.raises(HTTPException):                                          # editors cannot approve
            await api.PUBLISH(editor)
        out = await api.decide(hot.id, api.DecisionIn(approve=True), db, approver)
        assert out["status"] == "DONE"
        acts = (await db.execute(select(CRMActivity).where(CRMActivity.crm_record_id == rid))).scalars().all()
        assert [a.subject for a in acts] == ["Call the buyer about POVU AllClean"]
        with pytest.raises(HTTPException) as e:                                     # decided once
            await api.decide(hot.id, api.DecisionIn(approve=True), db, approver)
        assert e.value.status_code == 409

        # a new version with a 2-day delay; rollback re-publishes v1
        v2 = await api.save_draft(wid, api.GraphIn(graph=graph(delay_days=2)), db, editor)
        await api.publish(uuid.UUID(v2["id"]), db, approver)
        later = datetime.now(timezone.utc) + timedelta(minutes=1)
        rec2 = CRMRecord(company_name=f"Second Duka {s}", temperature=CRMTemperature.HOT)
        db.add(rec2)
        await db.flush()
        db.add(CRMStageHistory(crm_record_id=rec2.id, to_status="OPEN", changed_at=later))
        await db.commit()
        r2id = rec2.id
        await wfs.enqueue(db, later + timedelta(seconds=5))
        await wfs.process(db, now=later + timedelta(seconds=10))
        run2 = (await db.execute(select(CRMWorkflowRun).where(CRMWorkflowRun.crm_record_id == r2id).order_by(CRMWorkflowRun.created_at))).scalars().first()
        assert run2.status == "WAITING" and run2.resume_at > later + timedelta(days=1)
        await wfs.process(db, now=later + timedelta(days=3))
        await db.refresh(run2)
        assert run2.status == "WAITING_APPROVAL"

        info = await api.get_workflow(wid, db, viewer)
        assert [v["status"] for v in info["versions"]] == ["PUBLISHED", "DRAFT", "ARCHIVED", "DRAFT"]
        await api.publish(uuid.UUID(v1["id"]), db, approver)                       # rollback
        info = await api.get_workflow(wid, db, viewer)
        assert {v["version_no"]: v["status"] for v in info["versions"]} == {4: "ARCHIVED", 3: "DRAFT", 2: "PUBLISHED", 1: "DRAFT"}
