"""M36.S02.T005 segment e-mail campaigns on disposable PostgreSQL with a real local SMTP server (Mailpit):
audience by segment and company, consent and suppression, one message per address, cancel/withdraw,
order attribution, per-campaign failure isolation and the route validations."""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.core.config import settings
from app.db.session import AsyncSessionLocal, engine
from app.models.company import Company
from app.models.crm import CRMEmailCampaign, CRMOutboundMessage
from app.models.marketing import CRMProfile, CustomerSegment, SegmentType
from app.models.sales import Customer, CustomerChannel, SalesOrder, SOStatus
from app.services import crm_campaign_service as campaigns
from app.services import crm_outbound_service as outbound

TASK_DB_ENV = "M36_S02_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M36_S02_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m36_s02_[a-f0-9]{24}")
SMTP = os.environ.get("SMTP_TEST_SERVER", "")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1" or not SMTP.startswith("127.0.0.1:"),
                                reason="requires the task-owned disposable PostgreSQL and a local test SMTP server")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_segment_campaign_consent_company_dedupe_cancel_and_attribution(monkeypatch):
    s = uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        ours, theirs = Company(name=f"Ours {s}", short_code=f"O{s}"), Company(name=f"Theirs {s}", short_code=f"T{s}")
        seg = CustomerSegment(segment_name=f"Kiosks {s}", segment_type=list(SegmentType)[0])
        db.add_all([ours, theirs, seg])
        await db.flush()
        people = {}
        for key, company in (("a", ours), ("b", ours), ("dup", ours), ("other", theirs), ("noconsent", ours), ("quit", ours)):
            email = f"{'a' if key == 'dup' else key}-{s}@example.com"            # dup shares a's address
            c = Customer(code=f"C-{key}-{s}", name=f"{key.title()} Kiosk", contact_person=key.title(), email=email,
                         channel=CustomerChannel.RETAIL, currency="KES", company_id=company.id)
            db.add(c)
            await db.flush()
            db.add(CRMProfile(customer_id=c.id, segment_id=seg.id))
            people[key] = c
            if key not in ("noconsent",):
                await outbound.record_consent(db, email, "SUBSCRIBED", "form:test", "ok")
        await outbound.record_consent(db, f"quit-{s}@example.com", "UNSUBSCRIBED", "unsubscribe-link")
        camp = CRMEmailCampaign(name=f"Launch {s}", subject="New juice for {company_name}", body="Hi {contact_name}",
                                segment_id=seg.id, company_id=ours.id, status="SCHEDULED",
                                scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=1))
        later = CRMEmailCampaign(name=f"Later {s}", subject="x", body="y", segment_id=seg.id, company_id=ours.id,
                                 status="SCHEDULED", scheduled_at=datetime.now(timezone.utc) + timedelta(days=1))
        db.add_all([camp, later])
        await db.commit()
        preview = await campaigns.audience_preview(db, camp)
        assert preview == {"customers": 5, "addresses": 4, "with_consent": 2}  # other company excluded; dup shares an address

        assert await campaigns.expand_due(db) == 4
        assert await campaigns.expand_due(db) == 0                              # already queued: nothing twice
        await db.refresh(later)
        assert later.status == "SCHEDULED"                                      # not due yet
        msgs = {m.to_email: m for m in (await db.execute(select(CRMOutboundMessage).where(
            CRMOutboundMessage.dedupe_key.like(f"camp:{camp.id}:%")))).scalars()}
        assert set(msgs) == {f"{k}-{s}@example.com" for k in ("a", "b", "noconsent", "quit")}
        assert msgs[f"a-{s}@example.com"].subject in {"New juice for A Kiosk", "New juice for Dup Kiosk"}
        assert (msgs[f"noconsent-{s}@example.com"].status, msgs[f"quit-{s}@example.com"].status) == ("SUPPRESSED", "SUPPRESSED")

    host, port = SMTP.split(":")
    for k, v in (("CRM_OUTBOUND_EMAIL_ENABLED", True), ("SMTP_HOST", host), ("SMTP_PORT", int(port)),
                 ("SMTP_USE_TLS", False), ("SMTP_USERNAME", "")):
        monkeypatch.setattr(settings, k, v)
    async with AsyncSessionLocal() as db:
        await outbound.deliver_due(db)
        camp = await db.get(CRMEmailCampaign, camp.id)
        st = await campaigns.stats(db, camp)
        assert st["by_status"].get("SENT") == 2 and st["by_status"].get("SUPPRESSED") == 2
        # a recipient's confirmed order within 30 days counts once; a draft order, an unrelated customer's order and
        # an order booked under another company do not
        a_id = msgs[f"a-{s}@example.com"].customer_id
        db.add_all([
            SalesOrder(order_no=f"SO-C-{s}", customer_id=msgs[f"b-{s}@example.com"].customer_id, company_id=ours.id,
                       status=SOStatus.CONFIRMED, order_date=date.today(), requested_delivery_date=date.today()),
            SalesOrder(order_no=f"SO-D-{s}", customer_id=a_id, company_id=ours.id, status=SOStatus.DRAFT,
                       order_date=date.today(), requested_delivery_date=date.today()),
            SalesOrder(order_no=f"SO-T-{s}", customer_id=a_id, company_id=theirs.id, status=SOStatus.CONFIRMED,
                       order_date=date.today(), requested_delivery_date=date.today()),
            SalesOrder(order_no=f"SO-X-{s}", customer_id=people["other"].id, company_id=theirs.id,
                       status=SOStatus.CONFIRMED, order_date=date.today(), requested_delivery_date=date.today()),
        ])
        await db.commit()
        assert (await campaigns.stats(db, camp))["converted_customers"] == 1

        # cancelling the later campaign before its time: it never expands
        later = await db.get(CRMEmailCampaign, later.id)
        later.status = "CANCELLED"
        await db.commit()
        assert await campaigns.expand_due(db, now=datetime.now(timezone.utc) + timedelta(days=2)) == 0


@pytest.mark.asyncio
async def test_failing_campaign_is_isolated_and_routes_validate(monkeypatch):
    import httpx
    from types import SimpleNamespace

    from app.core.deps import get_current_user
    from app.main import app

    s = uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        co = Company(name=f"Co {s}", short_code=f"C{s}")
        seg, empty, off = (CustomerSegment(segment_name=f"{n} {s}", segment_type=list(SegmentType)[0], is_active=act)
                           for n, act in (("Seg", True), ("Empty", True), ("Off", False)))
        db.add_all([co, seg, empty, off])
        await db.flush()
        c = Customer(code=f"C-{s}", name="Shop", contact_person=None, email=f"shop-{s}@example.com",
                     channel=CustomerChannel.RETAIL, currency="KES", company_id=co.id)
        db.add(c)
        await db.flush()
        db.add(CRMProfile(customer_id=c.id, segment_id=seg.id))
        past = datetime.now(timezone.utc) - timedelta(minutes=1)
        bad = CRMEmailCampaign(name=f"Bad {s}", subject="s", body="b", segment_id=seg.id, company_id=co.id,
                               status="SCHEDULED", scheduled_at=past - timedelta(minutes=1))
        good = CRMEmailCampaign(name=f"Good {s}", subject="Hi {contact_name}", body="Save {discount} now",
                                segment_id=seg.id, company_id=co.id, status="SCHEDULED", scheduled_at=past)
        db.add_all([bad, good])
        await db.commit()
        ids = {k: v.id for k, v in (("co", co), ("seg", seg), ("empty", empty), ("off", off), ("bad", bad), ("good", good))}

        real_queue = outbound.queue

        async def flaky(db_, **kw):
            if kw["dedupe_key"].startswith(f"camp:{ids['bad']}:"):
                raise RuntimeError("boom")
            return await real_queue(db_, **kw)
        monkeypatch.setattr(outbound, "queue", flaky)
        assert await campaigns.expand_due(db) == 1                       # the failure does not block the good one
        monkeypatch.setattr(outbound, "queue", real_queue)
        db.expire_all()
        assert (await db.get(CRMEmailCampaign, ids["bad"])).status == "FAILED"
        assert (await db.get(CRMEmailCampaign, ids["good"])).status == "QUEUED"
        msg = (await db.execute(select(CRMOutboundMessage).where(
            CRMOutboundMessage.dedupe_key.like(f"camp:{ids['good']}:%")))).scalar_one()
        assert msg.subject == "Hi Shop" and msg.body_text.startswith("Save {discount} now")  # fallback name; braces kept

    user = SimpleNamespace(id=uuid4(), username="mkt", email="m@example.com", full_name="M", is_superuser=False,
                           is_active=True, access_scopes=[], roles=[SimpleNamespace(name="r", is_active=True, access_scopes=[],
                           permissions=[SimpleNamespace(code=x, module="crm", action=x.split(".")[1], is_active=True)
                                        for x in ("crm.view", "crm.edit_all")])])
    app.dependency_overrides[get_current_user] = lambda: user
    base = {"name": "N", "subject": "S", "body": "B"}
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as cl:
            post = lambda **kw: cl.post("/api/v1/crm/email-campaigns", json={**base, **kw})
            assert (await post(segment_id=str(ids["seg"]))).status_code == 422                          # company required
            assert (await post(segment_id=str(ids["seg"]), company_id=str(uuid4()))).status_code == 422  # unknown company
            assert (await post(segment_id=str(ids["off"]), company_id=str(ids["co"]))).status_code == 422  # inactive seg
            r = await post(segment_id=str(ids["seg"]), company_id=str(ids["co"]), body="Hi {contact_nam}")
            assert r.status_code == 422 and "{contact_nam}" in r.json()["detail"]
            empty_c = (await post(segment_id=str(ids["empty"]), company_id=str(ids["co"]))).json()
            assert (await cl.post(f"/api/v1/crm/email-campaigns/{empty_c['id']}/schedule")).status_code == 422  # no audience
            ok = (await post(segment_id=str(ids["seg"]), company_id=str(ids["co"]))).json()
            sched = f"/api/v1/crm/email-campaigns/{ok['id']}/schedule"
            assert (await cl.post(sched, params={"at": "2030-01-01T09:00:00"})).status_code == 422          # naive time
            assert (await cl.post(sched, params={"at": "2030-01-01T09:00:00+03:00"})).json()["status"] == "SCHEDULED"
            assert (await cl.post(f"/api/v1/crm/email-campaigns/{ids['bad']}/schedule")).json()["status"] == "SCHEDULED"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
