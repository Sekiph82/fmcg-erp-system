"""M44.S01.T012 e-mail governance and smart content (unit; DB part needs M44_DB=1). Runs at the M44 gate.

Unit: deterministic A/B split (~split %, stable per recipient), smart blocks hidden for non-matching / unknown
audience. DB: A/B winner only with ≥100 per arm and p<0.05 (clear lift → B; tiny lift → no winner); approval gate
blocks scheduling until a second editor approves.
"""
import os
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.services import crm_campaign_service as campaigns
from app.services import email_design_service as eds


def test_ab_split_is_deterministic_and_close_to_pct():
    c = SimpleNamespace(id=uuid.uuid4(), ab_split_pct=30)
    picks = [campaigns.variant_for(c, f"r{i}@povu-demo.test") for i in range(2000)]
    assert picks == [campaigns.variant_for(c, f"r{i}@povu-demo.test") for i in range(2000)]
    assert 0.25 < picks.count("B") / 2000 < 0.35
    assert campaigns.variant_for(SimpleNamespace(id=c.id, ab_split_pct=0), "x@povu-demo.test") == "A"


def test_smart_blocks_follow_audience():
    doc, _ = eds.validate({"blocks": [{"type": "text", "text": "Everyone"},
                                      {"type": "text", "text": "Customers only", "audience": {"lifecycle": ["CUSTOMER"]}},
                                      {"type": "text", "text": "Retail only", "audience": {"channel": ["RETAIL"]}}]})
    cust = eds.render_text(doc, {"lifecycle": "customer", "channel": "WHOLESALE"})
    assert "Customers only" in cust and "Retail only" not in cust
    unknown = eds.render_html(doc, {})
    assert "Everyone" in unknown and "Customers only" not in unknown and "Retail only" not in unknown


DB = pytest.mark.skipif(os.environ.get("M44_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M44_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


async def _arm(db, camp, variant, n, clicks):
    from app.models.crm import CRMEmailEvent, CRMOutboundMessage
    now = datetime.now(timezone.utc)
    for i in range(n):
        m = CRMOutboundMessage(id=uuid.uuid4(), dedupe_key=f"camp:{camp.id}:{variant}{i}@povu-demo.test", purpose="CAMPAIGN",
                               to_email=f"{variant}{i}@povu-demo.test", subject="s", body_text="b", status="SENT",
                               attempts=1, next_attempt_at=now, created_at=now, sent_at=now, ab_variant=variant)
        db.add(m)
        if i < clicks:
            await db.flush()
            db.add(CRMEmailEvent(id=uuid.uuid4(), message_id=m.id, kind="CLICK", is_machine=False, occurred_at=now))
    await db.flush()


async def _segment(db):
    from app.models.marketing import CustomerSegment, SegmentType
    seg = CustomerSegment(id=uuid.uuid4(), segment_name=f"POVU retail {uuid.uuid4().hex[:6]}", segment_type=SegmentType.RETAIL)
    db.add(seg)
    await db.flush()
    return seg


@DB
@pytest.mark.asyncio
async def test_ab_winner_needs_evidence_and_approval_gate():
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMEmailCampaign
    async with AsyncSessionLocal() as db:
        seg = await _segment(db)
        clear = CRMEmailCampaign(id=uuid.uuid4(), name="ab-clear", subject="s", body="b", segment_id=seg.id, ab_split_pct=50)
        noise = CRMEmailCampaign(id=uuid.uuid4(), name="ab-noise", subject="s", body="b", segment_id=seg.id, ab_split_pct=50)
        small = CRMEmailCampaign(id=uuid.uuid4(), name="ab-small", subject="s", body="b", segment_id=seg.id, ab_split_pct=50)
        db.add_all([clear, noise, small])
        await db.flush()
        await _arm(db, clear, "A", 200, 10); await _arm(db, clear, "B", 200, 40)
        await _arm(db, noise, "A", 200, 20); await _arm(db, noise, "B", 200, 23)
        await _arm(db, small, "A", 50, 0); await _arm(db, small, "B", 50, 25)
        assert (await campaigns.ab_result(db, clear))["winner"] == "B"
        assert (await campaigns.ab_result(db, noise))["winner"] is None
        r = await campaigns.ab_result(db, small)
        assert r["winner"] is None and r["p_value"] is None
        await db.rollback()


@DB
@pytest.mark.asyncio
async def test_approval_gate(monkeypatch):
    from fastapi import HTTPException
    from app.api.v1.endpoints import crm_pipeline as ep
    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMEmailCampaign
    monkeypatch.setattr(settings, "MARKETING_EMAIL_APPROVAL_REQUIRED", True)
    alice = SimpleNamespace(username="alice", is_superuser=True)
    bob = SimpleNamespace(username="bob", is_superuser=True)
    async with AsyncSessionLocal() as db:
        seg = await _segment(db)
        c = CRMEmailCampaign(id=uuid.uuid4(), name="appr", subject="s", body="b", segment_id=seg.id)
        db.add(c)
        await db.commit()
        await ep.campaign_approval(str(c.id), "request", db, alice)
        with pytest.raises(HTTPException) as e:
            await ep.campaign_approval(str(c.id), "approve", db, alice)
        assert e.value.status_code == 403
        out = await ep.campaign_approval(str(c.id), "approve", db, bob)
        assert out["approval_status"] == "APPROVED"
