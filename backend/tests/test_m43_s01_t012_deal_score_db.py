"""M43.S01.T012 deal score and buying groups (run at the M43 gate, M43_S01_DB=1).

Deterministic score for synthetic deals: unknown factors are listed as missing and excluded (not scored as zero);
every factor carries its reason; buying-group coverage warns about missing decision maker / buyer / champion;
a blocker lowers the factor; trend stores at most one snapshot per day.
"""
from __future__ import annotations

import os
import uuid

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(os.environ.get("M43_S01_DB") != "1",
              reason="requires the task-owned disposable PostgreSQL at the M43 head")]


async def test_score_missing_data_and_buying_group():
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMContact, CRMRecord, CRMRecordType
    from app.services import crm_contact_service as cs
    from app.services import crm_deal_score_service as ds
    async with AsyncSessionLocal() as db:
        rec = CRMRecord(id=uuid.uuid4(), record_type=CRMRecordType.OPPORTUNITY, company_name="POVU Synthetic Outlet")
        db.add(rec)
        await db.flush()
        bare = await ds.score(db, rec)
        assert {"stage", "activity", "buying_group", "customer"} <= set(bare["missing"])
        assert all(f["reason"] for f in bare["factors"])
        dm = CRMContact(full_name="Synthetic Owner")
        champ = CRMContact(full_name="Synthetic Shop Manager")
        db.add_all([dm, champ])
        await db.flush()
        await cs.associate(db, dm.id, "crm_record", rec.id, "decision_maker")
        await cs.associate(db, champ.id, "crm_record", rec.id, "champion")
        bg = await ds.buying_group(db, rec)
        assert bg["coverage"] == 0.67 and bg["missing"] == ["buyer/finance"]
        with_group = await ds.score(db, rec)
        blocker = CRMContact(full_name="Synthetic Competitor Loyalist")
        db.add(blocker)
        await db.flush()
        await cs.associate(db, blocker.id, "crm_record", rec.id, "blocker")
        with_blocker = await ds.score(db, rec)
        bgf = lambda r: next(f["value"] for f in r["factors"] if f["factor"] == "buying_group")  # noqa: E731
        assert bgf(with_blocker) < bgf(with_group)
        a = await ds.score_with_trend(db, rec)
        b = await ds.score_with_trend(db, rec)
        assert len(b["trend"]) == len(a["trend"]) == 1
        await db.rollback()


@pytest.fixture(autouse=True)
async def _dispose_engine():
    """Each test runs in its own event loop: drop pooled connections afterwards (same pattern as other DB tests)."""
    yield
    from app.db.session import engine
    await engine.dispose()
