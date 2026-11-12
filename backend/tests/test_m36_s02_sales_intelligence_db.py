"""M36.S02.T002-T004 on disposable PostgreSQL: explainable lead scoring, stage history, filtered weighted
forecast with snapshots (currencies never mixed) and funnel analytics reconciled to source records."""
from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete, func, select

from app.db.session import AsyncSessionLocal, engine
from app.models.crm import (
    CRMActivity, CRMActivityResult, CRMLossReason, CRMPipelineStage, CRMRecord, CRMRecordType, CRMScoreHistory,
    CRMScoreRule, CRMSourceType, CRMStageHistory, CRMStageType, CRMStatus, CRMWinLoss,
)
from app.services import crm_intelligence_service as intel

TASK_DB_ENV = "M36_S02_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M36_S02_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m36_s02_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_scoring_forecast_and_funnel_against_source_records():
    s = uuid4().hex[:8]
    rep_a, rep_b = f"rep-a-{s}", f"rep-b-{s}"
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        await db.execute(delete(CRMScoreRule))  # this test owns the rule table of its database
        st = [CRMPipelineStage(stage_code=f"{c}-{s}", stage_name=f"{c} {s}", stage_type=CRMStageType.OPPORTUNITY,
                               default_probability=p, sequence_no=n)
              for n, (c, p) in enumerate([("QUAL", 20), ("PROP", 50), ("NEGO", 80)], start=1)]
        nurture = CRMPipelineStage(stage_code=f"NURT-{s}", stage_name=f"NURT {s}", stage_type=CRMStageType.NURTURING,
                                   default_probability=0, sequence_no=99)
        db.add_all(st + [nurture])
        await db.flush()

        # ── scoring with built-in defaults (fixes the never-matching source bonus)
        lead = CRMRecord(record_type=CRMRecordType.LEAD, company_name=f"Lead {s}", source_type=CRMSourceType.REFERRAL,
                         qualified_flag=True, expected_revenue=Decimal("600000"), assigned_rep_id=rep_a)
        db.add(lead)
        await db.flush()
        db.add_all([CRMActivity(crm_record_id=lead.id, activity_type="CALL", subject="x",
                                result_status=CRMActivityResult.COMPLETED) for _ in range(7)])
        await db.commit()
        lead_id = lead.id

    async with AsyncSessionLocal() as db:
        rec = await intel.rescore_record(db, str(lead_id), "tester")
        # 20 source + 20 qualified + 10 + 5 revenue + min(7*5, 30) activities = 85
        assert (rec.lead_score, rec.temperature.value) == (85, "HOT")
        again = await intel.rescore_record(db, str(lead_id), "tester")
        assert again.lead_score == 85
        history = await intel.score_history(db, str(lead_id))
        assert len(history) == 1 and history[0]["score"] == 85  # unchanged rescore adds no history
        assert {b["rule"]: b["points"] for b in history[0]["breakdown"]}["Completed activities"] == 30

        # configured rules replace defaults; history explains the change
        db.add(CRMScoreRule(name="Beverage segment", category="FIT", field="industry_segment", operator="eq",
                            value="beverage", points=40))
        await db.commit()
        rec = await intel.rescore_record(db, str(lead_id), "tester")
        assert (rec.lead_score, rec.temperature.value) == (0, "COLD")  # segment unset -> rule does not apply
        h = await intel.score_history(db, str(lead_id))
        assert (h[0]["previous_score"], h[0]["score"]) == (85, 0) and h[0]["breakdown"][0]["points"] == 0
        await db.execute(delete(CRMScoreRule))
        await db.commit()

        # ── stage history captured on every write path; forecast by month and currency
        today = date.today().replace(day=15)
        opp1 = CRMRecord(record_type=CRMRecordType.OPPORTUNITY, company_name=f"A {s}", stage_id=st[0].id,
                         expected_revenue=Decimal("1000"), probability_pct=Decimal("50"), currency="KES",
                         expected_close_date=today, assigned_rep_id=rep_a)
        opp2 = CRMRecord(record_type=CRMRecordType.OPPORTUNITY, company_name=f"B {s}", stage_id=st[0].id,
                         expected_revenue=Decimal("400"), probability_pct=Decimal("25"), currency="USD",
                         expected_close_date=today, assigned_rep_id=rep_b)
        opp3 = CRMRecord(record_type=CRMRecordType.OPPORTUNITY, company_name=f"C {s}", stage_id=st[0].id,
                         expected_revenue=Decimal("900"), probability_pct=Decimal("80"), currency="KES",
                         expected_close_date=today, assigned_rep_id=rep_a)
        parked = CRMRecord(record_type=CRMRecordType.OPPORTUNITY, company_name=f"D {s}", stage_id=st[0].id,
                           expected_revenue=Decimal("10"), currency="KES", assigned_rep_id=rep_a)
        db.add_all([opp1, opp2, opp3, parked])
        await db.commit()
        parked.stage_id = nurture.id  # parked in nurturing: must not count as reaching later steps
        await db.commit()
        opp1.stage_id = st[1].id
        await db.commit()
        opp1.stage_id = st[2].id
        await db.commit()
        opp3.stage_id = st[1].id
        opp3.status = CRMStatus.LOST
        db.add(CRMWinLoss(crm_record_id=opp3.id, final_status="LOST", close_date=date.today(),
                          loss_reason_code=CRMLossReason.PRICE_TOO_HIGH))
        await db.commit()
        transitions = (await db.execute(select(CRMStageHistory).where(CRMStageHistory.crm_record_id == opp1.id)
                                        .order_by(CRMStageHistory.changed_at))).scalars().all()
        assert [t.to_stage_id for t in transitions] == [st[0].id, st[1].id, st[2].id]

        detail = await intel.forecast_detail(db, 3, assigned_rep_id=None)
        month = today.strftime("%Y-%m")
        mine = {(r["month"], r["currency"]): r for r in detail["rows"]}
        kes, usd = mine[(month, "KES")], mine[(month, "USD")]
        assert kes["deal_count"] >= 1 and usd["deal_count"] >= 1   # never summed across currencies
        only_a = await intel.forecast_detail(db, 3, assigned_rep_id=rep_a)
        a_row = next(r for r in only_a["rows"] if r["month"] == month and r["currency"] == "KES")
        assert (a_row["expected_revenue"], a_row["weighted_revenue"], a_row["deal_count"]) == (1000.0, 500.0, 1)  # lost opp3 excluded
        snap = await intel.save_snapshot(db, only_a, "Q-test", None)
        assert intel.snapshot_out(snap, with_rows=True)["rows"] == only_a["rows"]

        # ── funnel reconciled to these records only (rep filter scopes the data set)
        f = await intel.funnel(db, date_from=date.today() - timedelta(days=1), date_to=date.today(), assigned_rep_id=rep_a)
        reached = {row["stage"]: row["reached"] for row in f["funnel"] if row["stage"].endswith(s)}
        assert reached == {f"QUAL {s}": 3, f"PROP {s}": 2, f"NEGO {s}": 1}  # lead has no stage; nurturing excluded
        rep_row = next(r for r in f["reps"] if r["assigned_rep_id"] == rep_a)
        assert (rep_row["total"], rep_row["open"], rep_row["lost"], rep_row["win_rate_pct"]) == (4, 3, 1, 0.0)
        with pytest.raises(ValueError, match="finite"):
            intel.validate_rule("expected_revenue", "gt", "NaN")
        assert {"reason": "PRICE_TOO_HIGH", "count": 1} in f["loss_reasons"]
        nego_age = next(a for a in f["aging"] if a["stage"] == f"NEGO {s}")
        assert (nego_age["open"], nego_age["avg_days"]) == (1, 0.0)
        future = await intel.funnel(db, date_from=date.today() + timedelta(days=1), assigned_rep_id=rep_a)
        assert future["records"] == 0  # date boundary excludes today's records
