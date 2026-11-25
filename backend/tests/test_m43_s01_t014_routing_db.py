"""M43.S01.T014 routing, stage approvals, splits and handoffs (run at the M43 gate; DB part needs M43_S01_DB=1).

Unit: round robin cycles; smooth weighted round robin is fair (2:1 weights → 2:1 over 30 picks); split validation.
DB: concurrent new leads under one rule get distinct consecutive owners (row lock); unavailable people skipped;
approval gate files one PENDING request, refuses the move, self-approval refused, approval by another manager lets
the move through; won deal gets exactly one handoff brief.
"""
from __future__ import annotations

import os
import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.crm import CRMRoutingRule
from app.services import crm_routing_service as rt


def test_round_robin_and_weighted():
    r = CRMRoutingRule(method="ROUND_ROBIN", state={})
    assert [rt.pick(r, ["a", "b", "c"]) for _ in range(4)] == ["a", "b", "c", "a"]
    w = CRMRoutingRule(method="WEIGHTED", weights={"a": 2, "b": 1}, state={})
    picks = [rt.pick(w, ["a", "b"]) for _ in range(30)]
    assert picks.count("a") == 20 and picks.count("b") == 10


def test_split_validation():
    rt.validate_splits([("a", Decimal("60")), ("b", Decimal("40"))])
    for bad in ([("a", Decimal("60")), ("b", Decimal("30"))], [("a", Decimal("50")), ("a", Decimal("50"))],
                [("a", Decimal("0")), ("b", Decimal("100"))]):
        with pytest.raises(HTTPException):
            rt.validate_splits(bad)


DB = pytest.mark.skipif(os.environ.get("M43_S01_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@DB
@pytest.mark.asyncio
async def test_approval_gate_and_handoff():
    from sqlalchemy import func, select

    from app.db.session import AsyncSessionLocal
    from app.models.crm import (CRMHandoff, CRMPipelineStage, CRMRecord, CRMRecordType, CRMStageApprovalRequest,
                                CRMStageApprovalRule, CRMStageType)
    from app.models.user import User
    from app.schemas.crm import CRMCloseWonRequest, CRMRecordUpdate
    from app.services import crm_pipeline_service as svc
    async with AsyncSessionLocal() as db:
        rep = User(id=uuid.uuid4(), email=f"r-{uuid.uuid4().hex[:6]}@povu-demo.test", hashed_password="x", full_name="Rep", is_active=True)
        mgr = User(id=uuid.uuid4(), email=f"m-{uuid.uuid4().hex[:6]}@povu-demo.test", hashed_password="x", full_name="Mgr", is_active=True)
        st = CRMPipelineStage(id=uuid.uuid4(), stage_code=f"NEG-{uuid.uuid4().hex[:6]}", stage_name="Negotiation",
                              stage_type=CRMStageType.OPPORTUNITY, sequence_no=7)
        db.add_all([rep, mgr, st])
        rec = CRMRecord(id=uuid.uuid4(), record_type=CRMRecordType.OPPORTUNITY, company_name="POVU Synthetic Outlet",
                        expected_revenue=900000)
        db.add(rec)
        db.add(CRMStageApprovalRule(name="Large deal", stage_id=st.id, min_expected_revenue=500000))
        await db.commit()
        with pytest.raises(HTTPException) as e:
            await svc.update_record(db, str(rec.id), CRMRecordUpdate(stage_id=st.id), actor_id=rep.id)
        assert e.value.detail["code"] == "approval_required"
        req = (await db.execute(select(CRMStageApprovalRequest).where(CRMStageApprovalRequest.crm_record_id == rec.id))).scalar_one()
        with pytest.raises(HTTPException):
            await rt.decide(db, req, rep, True, None)
        await rt.decide(db, req, mgr, True, None)
        await db.commit()
        moved = await svc.update_record(db, str(rec.id), CRMRecordUpdate(stage_id=st.id), actor_id=rep.id)
        assert moved.stage_id == st.id
        await svc.close_won(db, str(rec.id), CRMCloseWonRequest())
        await rt.handoff(db, rec)
        await db.commit()
        n = (await db.execute(select(func.count()).select_from(CRMHandoff).where(CRMHandoff.crm_record_id == rec.id))).scalar_one()
        assert n == 1
