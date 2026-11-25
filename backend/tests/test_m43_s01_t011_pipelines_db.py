"""M43.S01.T011 multiple pipelines (run at the M43 gate, M43_S01_DB=1; the migration part runs in the gate's
upgrade-from-previous-head step: every pre-existing stage and record lands in the default pipeline, none lost).

Covers: two synthetic pipelines with their own stages; a record follows its stage's pipeline on create and move;
pipeline-scoped stage list, forecast and funnel; automation rule can condition on pipeline_id.
"""
from __future__ import annotations

import os
import uuid
from datetime import date, timedelta

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(os.environ.get("M43_S01_DB") != "1",
              reason="requires the task-owned disposable PostgreSQL at the M43 head")]


async def test_two_pipelines_scope_forecast_and_funnel():
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMPipeline, CRMPipelineStage, CRMRecordType, CRMStageType
    from app.schemas.crm import CRMRecordCreate, CRMRecordUpdate
    from app.services import crm_automation_service as auto
    from app.services import crm_intelligence_service as intel
    from app.services import crm_pipeline_service as svc
    async with AsyncSessionLocal() as db:
        a = CRMPipeline(id=uuid.uuid4(), name=f"Distributor onboarding {uuid.uuid4().hex[:4]}")
        b = CRMPipeline(id=uuid.uuid4(), name=f"Key accounts {uuid.uuid4().hex[:4]}")
        db.add_all([a, b])
        sa1 = CRMPipelineStage(id=uuid.uuid4(), stage_code=f"A1-{uuid.uuid4().hex[:6]}", stage_name="Applied",
                               stage_type=CRMStageType.OPPORTUNITY, sequence_no=1, pipeline_id=a.id, default_probability=20)
        sb1 = CRMPipelineStage(id=uuid.uuid4(), stage_code=f"B1-{uuid.uuid4().hex[:6]}", stage_name="Pitch",
                               stage_type=CRMStageType.OPPORTUNITY, sequence_no=1, pipeline_id=b.id, default_probability=40)
        db.add_all([sa1, sb1])
        await db.commit()
        rec = await svc.create_record(db, CRMRecordCreate(record_type=CRMRecordType.OPPORTUNITY, company_name="POVU Synthetic Outlet",
                                                          stage_id=sa1.id, expected_revenue=1000,
                                                          expected_close_date=date.today() + timedelta(days=5)))
        assert rec.pipeline_id == a.id
        assert [s.id for s in await svc.get_stages(db, pipeline_id=str(b.id))] == [sb1.id]
        rec = await svc.update_record(db, str(rec.id), CRMRecordUpdate(stage_id=sb1.id))
        assert rec.pipeline_id == b.id
        fa = await svc.get_forecast(db, months_ahead=2, pipeline_id=str(a.id))
        fb = await svc.get_forecast(db, months_ahead=2, pipeline_id=str(b.id))
        assert sum(m["deal_count"] for m in fa) == 0 and sum(m["deal_count"] for m in fb) == 1
        f = await intel.funnel(db, pipeline_id=str(b.id))
        assert [row["stage_id"] for row in f["funnel"]] == [str(sb1.id)]
        auto.validate("stage_changed", "pipeline_id", "eq", "create_task", {"subject": "Call the new distributor"})


@pytest.fixture(autouse=True)
async def _dispose_engine():
    """Each test runs in its own event loop: drop pooled connections afterwards (same pattern as other DB tests)."""
    yield
    from app.db.session import engine
    await engine.dispose()
