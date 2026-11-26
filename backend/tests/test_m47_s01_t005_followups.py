"""M47 final-gate review follow-ups (DB part needs M46_DB=1).

Inbound-mail authentication trusts only our server's Authentication-Results; Slack route webhooks are encrypted at
rest; scheduled workflows page through every record (no silent cap); public video calls are rate limited.
"""
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage

import pytest

DB = pytest.mark.skipif(os.environ.get("M46_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M46_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def _msg(*auth):
    m = EmailMessage()
    m["From"] = "duka@example.com"
    for a in auth:
        m["Authentication-Results"] = a
    m.set_content("unsubscribe")
    return m


def test_only_our_authentication_results_are_trusted(monkeypatch):
    from app.core.config import settings
    from app.services.email_mailbox_service import _verified
    monkeypatch.setattr(settings, "MAIL_AUTHSERV_ID", "")
    # the top header (added by our server) says fail; a sender-written header lower down claims pass
    assert not _verified(_msg("mx.povu.example.com; dmarc=fail header.from=example.com", "evil; dmarc=pass"), "duka@example.com")
    assert _verified(_msg("mx.povu.example.com; dmarc=pass header.from=example.com"), "duka@example.com")
    monkeypatch.setattr(settings, "MAIL_AUTHSERV_ID", "mx.povu.example.com")
    assert not _verified(_msg("forged.example; dmarc=pass"), "duka@example.com")
    assert _verified(_msg("forged.example; dmarc=fail", "mx.povu.example.com; dmarc=pass"), "duka@example.com")


def test_slack_route_webhook_is_sealed():
    from app.models.m47_platform import SlackRoute, seal_webhook
    url = "https://hooks.slack.com/services/T000/B000/povu-secret"
    sealed = seal_webhook(url)
    assert sealed.startswith("enc:") and "povu-secret" not in sealed
    assert SlackRoute(webhook_url_stored=sealed).webhook_url == url


@DB
@pytest.mark.asyncio
async def test_scheduled_trigger_pages_through_all_records(monkeypatch):
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMRecord
    from app.services import crm_workflow_service as wfs
    from tests.test_m47_s01_t008_automation_data import NBO, _graph, _published, _runs, _staff
    monkeypatch.setattr(wfs, "MAX_SCHEDULED_PER_OCCURRENCE", 2)      # force several pages
    tag = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        editor, approver = await _staff(db, "ed", ("crm.edit_all",)), await _staff(db, "ap", ("crm.approve",))
        recs = [CRMRecord(company_name=f"POVU Duka {i} {tag}", industry_segment=f"seg-{tag}") for i in range(5)]
        db.add_all(recs)
        await db.commit()
        match = {"field": "industry_segment", "operator": "eq", "value": f"seg-{tag}"}
        _, ver = await _published(db, _graph({"event": "scheduled", "schedule": {"kind": "daily", "time": "08:00", "match": match}}), editor, approver)
        d = (datetime.now(NBO) + timedelta(days=1)).date()
        await wfs.enqueue(db, datetime(d.year, d.month, d.day, 9, 30, tzinfo=NBO).astimezone(timezone.utc))
        assert {r.crm_record_id for r in await _runs(db, ver)} == {r.id for r in recs}   # all five, not just the first page


@DB
@pytest.mark.asyncio
async def test_public_video_is_rate_limited(monkeypatch):
    import httpx
    from app.api.v1.endpoints import sales_depth_public as pub
    from app.main import app
    monkeypatch.setattr(pub, "PER_MINUTE", 3)
    pub._hits.clear()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("198.51.100.7", 1)), base_url="http://erp.test") as c:
        codes = [(await c.get(f"/api/v1/public/video/{uuid.uuid4().hex}")).status_code for _ in range(4)]
    assert codes[:3] == [404, 404, 404] and codes[3] == 429
    pub._hits.clear()
