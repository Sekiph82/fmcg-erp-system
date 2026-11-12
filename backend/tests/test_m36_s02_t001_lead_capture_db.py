"""M36.S02.T001 website lead capture on disposable PostgreSQL, through the real app without a login:
consent, honeypot, per-IP rate limit, attribution, e-mail/phone dedupe and lead-code continuity."""
from __future__ import annotations

import os
import re
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal, engine
from app.models.crm import CRMActivity, CRMLeadForm, CRMLeadSubmission, CRMRecord, CRMRecordType

TASK_DB_ENV = "M36_S02_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M36_S02_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m36_s02_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_public_form_creates_attributed_leads_without_login():
    from app.main import app

    s = uuid4().hex[:8]
    slug = f"contact-{s}"
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        db.add(CRMLeadForm(slug=slug, name="Contact", title="Talk to sales", consent_text="You may contact me about products.",
                           require_consent=True, assigned_rep_id="rep-web", sales_region_id="R-WEB"))
        # converted leads keep their LD- code; numeric order must win over string order (LD-100000 > LD-99999)
        db.add(CRMRecord(record_type=CRMRecordType.OPPORTUNITY, company_name=f"Old {s}", lead_code="LD-99999"))
        db.add(CRMRecord(record_type=CRMRecordType.OPPORTUNITY, company_name=f"Older {s}", lead_code="LD-100000"))
        await db.commit()

    def client(ip):
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=(ip, 1234)), base_url="http://test")

    base = {"company_name": f"Duka {s}", "contact_person_name": "Wanjiru", "contact_email": f"Buyer-{s}@Example.com",
            "message": "<script>alert(1)</script> need 200 crates", "consent": True,
            "utm_source": "google", "utm_medium": "cpc", "utm_campaign": "launch", "landing_page": "https://example.invalid/juice"}
    async with client("198.51.100.7") as c:
        assert (await c.get(f"/api/v1/public/lead-forms/{slug}")).json()["require_consent"] is True
        assert (await c.get("/api/v1/crm/lead-forms")).status_code == 401           # admin side still needs login
        assert (await c.post(f"/api/v1/public/lead-forms/{slug}/submit", json={**base, "consent": False})).status_code == 422
        r = await c.post(f"/api/v1/public/lead-forms/{slug}/submit", json=base)
        assert r.status_code == 202
        again = await c.post(f"/api/v1/public/lead-forms/{slug}/submit",
                             json={**base, "contact_email": f"buyer-{s}@example.com", "message": "second"})
        assert again.status_code == 202 and again.json() == r.json()            # same answer: nothing revealed
        bot = await c.post(f"/api/v1/public/lead-forms/{slug}/submit", json={**base, "website": "http://spam.invalid"})
        assert bot.status_code == 202
        bad = await c.post(f"/api/v1/public/lead-forms/{slug}/submit", json={**base, "contact_email": "not-an-email"})
        assert bad.status_code == 422
        for _ in range(1):
            await c.post(f"/api/v1/public/lead-forms/{slug}/submit", json={**base, "company_name": f"Other {uuid4().hex[:4]}",
                                                                          "contact_email": None, "contact_phone": None})
        limited = await c.post(f"/api/v1/public/lead-forms/{slug}/submit", json=base)
        assert limited.status_code == 429  # 5 per IP per 10 minutes, consent rejections included
    async with client("203.0.113.9") as c:
        assert (await c.post(f"/api/v1/public/lead-forms/{slug}/submit",
                             json={**base, "company_name": f"Second shop {s}", "contact_email": None,
                                   "contact_phone": "+254 700 111222"})).status_code == 202
        assert (await c.post("/api/v1/public/lead-forms/no-such-form/submit", json=base)).status_code == 404

    async with AsyncSessionLocal() as db:
        form = (await db.execute(select(CRMLeadForm).where(CRMLeadForm.slug == slug))).scalar_one()
        subs = (await db.execute(select(CRMLeadSubmission).where(CRMLeadSubmission.form_id == form.id)
                                 .order_by(CRMLeadSubmission.received_at))).scalars().all()
        assert [x.status for x in subs] == ["REJECTED", "ACCEPTED", "DUPLICATE", "SPAM", "ACCEPTED", "ACCEPTED"]
        assert subs[0].contact_email is None and subs[0].crm_record_id is None
        assert all(x.ip_hash and "198.51" not in x.ip_hash for x in subs)        # keyed hash, never the raw IP
        first = subs[1]
        assert (first.consent_given, first.consent_text, first.utm_campaign) == (True, "You may contact me about products.", "launch")
        lead = await db.get(CRMRecord, first.crm_record_id)
        assert (lead.contact_email, lead.source_type.value, lead.assigned_rep_id, lead.sales_region_id) == (
            f"buyer-{s}@example.com", "WEBSITE", "rep-web", "R-WEB")
        assert "utm_source=google" in lead.source_detail
        assert "<script" not in lead.notes and "need 200 crates" in lead.notes  # markup stripped on input
        assert lead.lead_code == "LD-100001"
        assert subs[2].crm_record_id == lead.id                                   # duplicate attached, no second lead
        note = (await db.execute(select(CRMActivity).where(CRMActivity.crm_record_id == lead.id))).scalar_one()
        assert note.description == "second"
        assert subs[3].crm_record_id is None                                      # honeypot created nothing
        codes = (await db.execute(select(CRMRecord.lead_code).where(CRMRecord.created_by == "web-form"))).scalars().all()
        assert len(codes) == len(set(codes)) == 3
