"""M36.S02.T005 segment e-mail campaigns on disposable PostgreSQL with a real local SMTP server (Mailpit):
audience by segment and company, consent and suppression, one message per address, cancel/withdraw,
order attribution."""
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
from app.models.sales import Customer, CustomerChannel, SalesOrder
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
        # a recipient orders within 30 days -> one converted customer; an unrelated customer's order does not count
        db.add_all([
            SalesOrder(order_no=f"SO-C-{s}", customer_id=msgs[f"b-{s}@example.com"].customer_id,
                       order_date=date.today(), requested_delivery_date=date.today()),
            SalesOrder(order_no=f"SO-X-{s}", customer_id=people["other"].id, order_date=date.today(),
                       requested_delivery_date=date.today()),
        ])
        await db.commit()
        assert (await campaigns.stats(db, camp))["converted_customers"] == 1

        # cancelling the later campaign before its time: it never expands
        later = await db.get(CRMEmailCampaign, later.id)
        later.status = "CANCELLED"
        await db.commit()
        assert await campaigns.expand_due(db, now=datetime.now(timezone.utc) + timedelta(days=2)) == 0
