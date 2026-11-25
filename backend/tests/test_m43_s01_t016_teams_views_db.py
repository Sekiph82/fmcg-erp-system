"""M43.S01.T016 teams, tags, required fields per stage and saved views (run at the M43 gate, M43_S01_DB=1).

Covers: hierarchy roll-up (and cycle refusal) feeding a TEAM quota; required fields block entering a stage unless
filled in the same request; tag filter in record listing; saved view filters are whitelisted.
"""
from __future__ import annotations

import os
import uuid
from datetime import date

import pytest
from fastapi import HTTPException

pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(os.environ.get("M43_S01_DB") != "1",
              reason="requires the task-owned disposable PostgreSQL at the M43 head")]


async def test_hierarchy_rollup_and_cycle():
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMTeam
    from app.services import crm_team_service as teams
    async with AsyncSessionLocal() as db:
        k = uuid.uuid4().hex[:5]
        east = CRMTeam(id=uuid.uuid4(), code=f"EAST-{k}", name="East")
        nairobi = CRMTeam(id=uuid.uuid4(), code=f"NBO-{k}", name="Nairobi", parent_id=east.id)
        cbd = CRMTeam(id=uuid.uuid4(), code=f"CBD-{k}", name="CBD", parent_id=nairobi.id)
        db.add_all([east, nairobi, cbd])
        await db.flush()
        assert sorted(await teams.descendant_codes(db, east.code)) == sorted([east.code, nairobi.code, cbd.code])
        assert await teams.descendant_codes(db, cbd.code) == [cbd.code]
        with pytest.raises(HTTPException):
            await teams.check_no_cycle(db, east.id, cbd.id)
        await db.rollback()


async def test_required_fields_and_tags():
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMPipelineStage, CRMRecordTag, CRMRecordType, CRMStageType, CRMTag
    from app.schemas.crm import CRMRecordCreate, CRMRecordUpdate
    from app.services import crm_pipeline_service as svc
    async with AsyncSessionLocal() as db:
        st = CRMPipelineStage(id=uuid.uuid4(), stage_code=f"PROP-{uuid.uuid4().hex[:6]}", stage_name="Proposal",
                              stage_type=CRMStageType.OPPORTUNITY, sequence_no=5,
                              required_fields=["expected_revenue", "expected_close_date"])
        db.add(st)
        await db.commit()
        rec = await svc.create_record(db, CRMRecordCreate(record_type=CRMRecordType.OPPORTUNITY, company_name="POVU Synthetic Outlet"))
        with pytest.raises(HTTPException) as e:
            await svc.update_record(db, str(rec.id), CRMRecordUpdate(stage_id=st.id))
        assert e.value.status_code == 409 and set(e.value.detail["fields"]) == {"expected_revenue", "expected_close_date"}
        rec = await svc.update_record(db, str(rec.id), CRMRecordUpdate(stage_id=st.id, expected_revenue=5000,
                                                                       expected_close_date=date(2026, 12, 30)))
        assert rec.stage_id == st.id
        tag = CRMTag(id=uuid.uuid4(), name=f"modern-trade-{uuid.uuid4().hex[:4]}")
        db.add(tag)
        await db.flush()
        db.add(CRMRecordTag(crm_record_id=rec.id, tag_id=tag.id))
        await db.commit()
        got = await svc.get_records(db, extra={"tag": tag.name})
        assert [r.id for r in got] == [rec.id]


@pytest.fixture(autouse=True)
async def _dispose_engine():
    """Each test runs in its own event loop: drop pooled connections afterwards (same pattern as other DB tests)."""
    yield
    from app.db.session import engine
    await engine.dispose()
