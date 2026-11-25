"""M43.S01.T013 sales workspace (run at the M43 gate; DB part needs M43_S01_DB=1).

Unit: monthly recurrence keeps month ends valid. DB: completing a repeating task creates the next one once (second
completion of the same task or a retry creates nothing more); per-contact frequency cap suppresses the extra
message (manual, sequence and campaign alike); send-time suggestion refuses to guess on thin evidence; deal summary
uses stored facts only.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.services import crm_workspace_service as ws


def test_monthly_recurrence_month_end():
    assert ws._next_due(datetime(2026, 1, 31, 9), "MONTHLY", 1) == datetime(2026, 2, 28, 9)
    assert ws._next_due(datetime(2028, 1, 31, 9), "MONTHLY", 1) == datetime(2028, 2, 29, 9)
    assert ws._next_due(datetime(2026, 12, 15, 9), "WEEKLY", 2) == datetime(2026, 12, 29, 9)


DB = pytest.mark.skipif(os.environ.get("M43_S01_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@DB
@pytest.mark.asyncio
async def test_repeat_once_cap_and_send_time(monkeypatch):
    from sqlalchemy import func, select

    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMActivity, CRMActivityType, CRMOutboundMessage, CRMRecord, CRMRecordType
    from app.services import crm_outbound_service as outbound
    async with AsyncSessionLocal() as db:
        rec = CRMRecord(id=uuid.uuid4(), record_type=CRMRecordType.OPPORTUNITY, company_name="POVU Synthetic Outlet")
        db.add(rec)
        act = CRMActivity(id=uuid.uuid4(), crm_record_id=rec.id, activity_type=CRMActivityType.CALL, subject="Weekly stock check",
                          due_datetime=datetime(2026, 12, 7, 9), recurrence_rule="WEEKLY", recurrence_every=1)
        db.add(act)
        await db.flush()
        a = await ws.spawn_next(db, act)
        b = await ws.spawn_next(db, act)
        assert a is not None and b is None and a.due_datetime == datetime(2026, 12, 14, 9)
        monkeypatch.setattr(settings, "CRM_CONTACT_EMAIL_CAP_PER_WEEK", 2)
        email = f"shop-{uuid.uuid4().hex[:6]}@povu-demo.test"
        now = datetime.now(timezone.utc)
        for i in range(2):
            db.add(CRMOutboundMessage(id=uuid.uuid4(), dedupe_key=f"cap:{email}:{i}", purpose="MANUAL", to_email=email,
                                      subject="s", body_text="b", status="SENT", attempts=1, next_attempt_at=now,
                                      created_at=now, sent_at=now - timedelta(days=1)))
        await db.flush()
        third = await outbound.queue(db, to_email=email, subject="Third", body="x", purpose="MANUAL", dedupe_key=f"cap:{email}:3")
        assert third.status == "SUPPRESSED" and "frequency cap" in third.status_reason
        hint = await ws.send_time(db, email)
        assert hint["suggested_hour"] is None and hint["evidence"] == 0
        s = await ws.deal_summary(db, rec)
        assert "POVU Synthetic Outlet" in s["summary"] and s["facts_only"]
        await db.rollback()
