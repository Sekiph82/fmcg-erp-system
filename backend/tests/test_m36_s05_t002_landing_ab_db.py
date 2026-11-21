"""M36.S05.T002 landing pages and A/B tests on disposable PostgreSQL: consistent assignment, once-per-visitor counting,
consent/spam rules from the lead form, statistical guardrails and rights."""
from __future__ import annotations

import os
import re
import uuid
from collections import Counter
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import func, select
from starlette.requests import Request

from app.api.v1.endpoints import crm_landing as staff
from app.api.v1.endpoints import crm_landing_public as public
from app.db.session import AsyncSessionLocal, engine
from app.models.crm import CRMLandingEvent, CRMLeadForm, CRMLeadSubmission
from app.services import crm_landing_service as lp
from app.services import crm_lead_capture_service as capture

TASK_DB_ENV = "M36_S05_T002_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M36_S05_T002_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m36_s05_t002_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _req(ip):
    return Request({"type": "http", "method": "POST", "path": "/", "headers": [], "client": (ip, 5000)})


def _user(*codes):
    perms = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in codes]
    return SimpleNamespace(id=uuid4(), is_superuser=False, access_scopes=[], roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])


@pytest.mark.asyncio
async def test_landing_pages_ab():
    s = uuid4().hex[:8]
    mkt = _user("marketing.edit")
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        form = CRMLeadForm(slug=f"stockists-{s}", name="Stockists", title="Become a POVU stockist", require_consent=True,
                           consent_text="POVU may contact me.")
        db.add(form)
        await db.commit()

        with pytest.raises(HTTPException):
            await staff.WRITE(_user("marketing.view"))
        page = await staff.create_page(staff.PageIn(slug=f"stockist-{s}", name="Stockist drive", lead_form_id=form.id, min_sample=10), db, mkt)
        pid = uuid.UUID(page["id"])
        with pytest.raises(HTTPException) as e:                                 # nothing to show yet
            await staff.set_status(pid, staff.StatusIn(status="LIVE"), db, mkt)
        assert e.value.status_code == 422
        await staff.save_variant(pid, staff.VariantIn(key="A", headline="Stock POVU AllClean", cta_label="Join"), db, mkt)
        await staff.save_variant(pid, staff.VariantIn(key="B", headline="Earn more with POVU", cta_label="Apply now"), db, mkt)
        with pytest.raises(HTTPException):                                       # not live → public 404
            await public.show(f"stockist-{s}", "v" * 20, db)
        await staff.set_status(pid, staff.StatusIn(status="LIVE"), db, mkt)

        # consistent assignment and a fair split
        vis = [f"visitor-{i:06d}-{s}" for i in range(2000)]
        pg = await lp.page_by_slug(db, f"stockist-{s}")
        vs = await lp.variants(db, pid)
        split = Counter(lp.assign(pid, v, vs).key for v in vis)
        assert 850 < split["A"] < 1150 and split["A"] + split["B"] == 2000
        first = await public.show(f"stockist-{s}", vis[0], db)
        again = await public.show(f"stockist-{s}", vis[0], db)
        assert first["variant"] == again["variant"] and first["require_consent"] is True
        assert (await db.execute(select(func.count()).select_from(CRMLandingEvent).where(CRMLandingEvent.page_id == pid))).scalar_one() == 1

        # conversions: consent required; bots (honeypot) never count; each visitor once
        lead = dict(company_name=f"Mama Duka {s}", contact_email=f"m-{s}@shops.example", consent=False)
        with pytest.raises(HTTPException) as e:
            await public.convert(f"stockist-{s}", public.ConvertIn(visitor=vis[0], lead=capture.LeadSubmission(**lead)), _req("41.1.1.1"), db)
        assert e.value.status_code == 422
        await db.rollback()
        lead["consent"] = True
        await public.convert(f"stockist-{s}", public.ConvertIn(visitor=vis[0], lead=capture.LeadSubmission(**lead)), _req("41.1.1.1"), db)
        await public.convert(f"stockist-{s}", public.ConvertIn(visitor=vis[0], lead=capture.LeadSubmission(**lead)), _req("41.1.1.1"), db)
        bot = dict(company_name="spam", consent=True, website="http://spam.example")
        await public.convert(f"stockist-{s}", public.ConvertIn(visitor=vis[1], lead=capture.LeadSubmission(**bot)), _req("41.1.1.2"), db)
        conv = (await db.execute(select(func.count()).select_from(CRMLandingEvent).where(CRMLandingEvent.page_id == pid, CRMLandingEvent.kind == "CONVERT"))).scalar_one()
        assert conv == 1
        sub = (await db.execute(select(CRMLeadSubmission).where(CRMLeadSubmission.form_id == form.id, CRMLeadSubmission.status != "SPAM"))).scalars().first()
        assert sub.landing_page == f"lp:stockist-{s}:{first['variant']}"

        # guardrails: too little data → no verdict
        st = await staff.page_stats(pid, db, mkt)
        assert st["enough_data"] is False and "Not enough data" in st["verdict"]

        # simulate a finished test: A 200 views / 10 conversions, B 200 / 40 → B wins; equal rates → no winner
        from sqlalchemy.dialects.postgresql import insert
        va, vb = {v.key: v for v in vs}["A"], {v.key: v for v in vs}["B"]

        async def fill(variant, views, convs, tag):
            for i in range(views):
                h = f"{tag}-{i}"
                await db.execute(insert(CRMLandingEvent).values(id=uuid4(), page_id=pid, variant_id=variant.id, visitor_hash=h, kind="VIEW", created_at=func.now()).on_conflict_do_nothing())
                if i < convs:
                    await db.execute(insert(CRMLandingEvent).values(id=uuid4(), page_id=pid, variant_id=variant.id, visitor_hash=h, kind="CONVERT", created_at=func.now()).on_conflict_do_nothing())
            await db.commit()
        await fill(va, 200, 10, "a")
        await fill(vb, 200, 40, "b")
        st = await staff.page_stats(pid, db, mkt)
        assert st["enough_data"] and st["verdict"].startswith("Variant B beats A")
        b = next(r for r in st["variants"] if r["key"] == "B")
        assert b["p_value"] < 0.05 and b["ci95_pct"][0] < b["rate_pct"] < b["ci95_pct"][1]
        await fill(va, 230, 40, "a2")       # A catches up: 430 views / 50 conv ≈ 11.6 % vs B 20 % — still B
        p_after = next(r for r in (await staff.page_stats(pid, db, mkt))["variants"] if r["key"] == "B")["p_value"]
        assert p_after is not None
        assert lp._z_test(20, 200, 21, 200) > 0.05                           # same rate → not significant
