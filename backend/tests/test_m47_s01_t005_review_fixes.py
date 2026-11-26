"""M47 final-gate review fixes (unit + DB; the DB part needs M46_DB=1 and web_identities.verified_at).

1 WhatsApp simulate-inbound: admin, demo config, non-production; no keywords, no service window.
2 Form shortening / web-event enrolment only for a VERIFIED web identity; e-mail never filled or subscribed.
3 CPQ quote draft converts SO tax fractions to percentages.   4 report builder SO total uses fraction discounts.
5 chatter fails closed.   6 WhatsApp consent/config rights.   7 signed webhooks bypass the JSON re-serialiser.
8 workflow-hook limit after token match.   12 /metrics non-ASCII header.   13 CMS bundle site settings, ffmpeg whitelist.
15 contact search ignores hidden fields. Synthetic POVU data only.
"""
import hashlib
import hmac
import json
import os
import uuid
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException

from tests.test_m47_s01_t003_audit_fixes import _client, _login, _user

DB = pytest.mark.skipif(os.environ.get("M46_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M46_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def _u(*codes, superuser=False):
    return SimpleNamespace(id=uuid.uuid4(), username="u", is_superuser=superuser, access_scopes=[],
                           roles=[SimpleNamespace(name="r", is_active=True, access_scopes=[],
                                                  permissions=[SimpleNamespace(code=c, is_active=True) for c in codes])])


# ── unit ──────────────────────────────────────────────────────────────────────

def test_chatter_fails_closed_and_new_mappings():
    from app.api.v1.endpoints.chatter import _may
    rep, hr, admin = _u("crm.view"), _u("hr.view"), _u("users.view")
    for open_type in (None, "", "note", "Task", "general"):
        assert _may(rep, open_type)
    assert not _may(rep, "free_note") and _may(admin, "free_note")            # unknown type: staff set only
    assert not _may(rep, "timesheet") and _may(hr, "timesheet") and _may(hr, "appraisal") and _may(hr, "hr_document")
    assert not _may(rep, "expense_claim") and _may(_u("expenses.view"), "expense")
    assert not _may(rep, "document") and _may(_u("documents.view"), "document")


@pytest.mark.asyncio
async def test_chatter_timeline_pin_and_admin_routes(monkeypatch):
    from app.api.v1.endpoints import chatter
    from app.services import chatter_service as cs
    rep = _u("crm.view")
    items = [SimpleNamespace(reference_type="crm_record"), SimpleNamespace(reference_type="invoice"),
             SimpleNamespace(reference_type="note")]

    async def fake_timeline(db, **kw):
        return {"items": list(items), "total": 3, "module_breakdown": [{"module": "invoice", "count": 1},
                                                                       {"module": "crm_record", "count": 1}]}
    monkeypatch.setattr(cs, "get_timeline", fake_timeline)
    out = await chatter.get_timeline(None, None, None, False, 1, 30, db=None, current_user=rep)
    assert [i.reference_type for i in out["items"]] == ["crm_record", "note"]
    assert out["module_breakdown"] == [{"module": "crm_record", "count": 1}]

    pinned = []

    async def fake_get(db, aid):
        return SimpleNamespace(reference_type="invoice")

    async def fake_pin(db, aid):
        pinned.append(aid)
    monkeypatch.setattr(cs, "get_activity", fake_get)
    monkeypatch.setattr(cs, "pin_activity", fake_pin)
    with pytest.raises(HTTPException) as e:
        await chatter.pin_activity("a1", db=None, current_user=rep)
    assert e.value.status_code == 404 and pinned == []
    await chatter.pin_activity("a1", db=None, current_user=_u("sales.view"))
    assert pinned == ["a1"]

    with pytest.raises(HTTPException) as e:
        await chatter.ADMIN(current_user=rep)
    assert e.value.status_code == 403
    await chatter.ADMIN(current_user=_u("users.view"))
    guarded = {r.path for r in chatter.router.routes
               if any(d.dependency is chatter.ADMIN for d in getattr(r, "dependencies", []))}
    assert guarded == {"/stats", "/ai/recs", "/ai/run/activity-summarizer", "/ai/run/follow-up-assistant",
                       "/ai/run/insight-extractor", "/ai/recs/{rec_id}"}


def test_signed_webhook_paths_skip_the_sanitizer():
    from app.core.input_sanitizer import _SKIP_PATHS
    for p in ("/api/v1/whatsapp/webhook", "/api/v1/public/social/meta", "/api/v1/public/mail-events/sendgrid",
              "/api/v1/public/slack/interactions", "/api/v1/public/crm-workflow-hooks/x", "/api/v1/integrations/mpesa/callback",
              "/api/v1/moto-sales/mpesa/callback", "/api/v1/webhooks/inbound/erp"):
        assert any(p.startswith(s) for s in _SKIP_PATHS), p
    assert not any("/api/v1/whatsapp/send/text".startswith(s) for s in _SKIP_PATHS)


@pytest.mark.asyncio
async def test_metrics_non_ascii_header_is_404_not_500(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "METRICS_TOKEN", "povu-metrics-token")
    async with _client() as c:
        r = await c.get("/metrics", headers={"Authorization": b"Bearer \xc3\xbc\xc3\xa7"})
        assert r.status_code == 404
        assert (await c.get("/metrics", headers={"Authorization": "Bearer povu-metrics-token"})).status_code == 200


@pytest.mark.asyncio
async def test_workflow_hook_limit_counts_only_real_tokens(monkeypatch):
    from app.api.v1.endpoints import crm_workflow_hooks_public as hp
    from app.services import crm_workflow_service as wfs

    async def no_hook(db, wid, token):
        return None
    monkeypatch.setattr(wfs, "hook_token_ok", no_hook)
    from app.db.session import get_db
    from app.main import app

    async def no_db():
        yield None
    monkeypatch.setitem(app.dependency_overrides, get_db, no_db)    # never opens a database session
    hp._hits.clear()
    wid = uuid.uuid4()
    async with _client() as c:
        r = await c.post(f"/api/v1/public/crm-workflow-hooks/{wid}", json={"event_id": "e1", "email": "a@povu-demo.test"},
                         headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 401
    assert f"wf:{wid}" not in hp._hits and any(k.startswith("ip:") for k in hp._hits)


@pytest.mark.asyncio
async def test_ffmpeg_reads_local_files_only(monkeypatch):
    from app.services import cms_media_service as media
    calls = []

    async def fake(args):
        calls.append(args)
        return b"x"
    monkeypatch.setattr(media, "_ffmpeg", fake)
    monkeypatch.setattr(media, "file_path", lambda m: "/data/povu.mp4")
    await media.poster_frame(SimpleNamespace(), 1.0)
    await media.trim(SimpleNamespace(mime=next(iter(media.FORMATS))), 0.0, 2.0)
    for a in calls:
        i = a.index("-i")
        assert a[i - 2:i] == ["-protocol_whitelist", "file"]


# ── DB: WhatsApp (1, 6, 7) ────────────────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_whatsapp_simulate_consent_rights_and_compact_signed_webhook(monkeypatch):
    from sqlalchemy import select
    from app.api.v1.endpoints import whatsapp as wa_api
    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    from app.models.whatsapp import WhatsAppConfig, WhatsAppConsent
    from app.schemas.whatsapp import WASimulateInbound
    async with AsyncSessionLocal() as db:
        rep = (await _user(db, ("crm.view", "crm.create", "crm.edit", "sales.view"), "warep5")).username
        viewer = (await _user(db, ("crm.view_all",), "waview5")).username
        mgr = (await _user(db, ("crm.view", "crm.edit_all"), "wamgr5")).username
        admin_u = await _user(db, ("roles.edit",), "waadm5")
        admin = admin_u.username
        demo = WhatsAppConfig(display_name="POVU demo", business_phone_id=f"demo-{uuid.uuid4().hex[:8]}", is_demo_mode=True)
        live = WhatsAppConfig(display_name="POVU live", business_phone_id=f"live-{uuid.uuid4().hex[:8]}", is_demo_mode=False)
        db.add_all([demo, live])
        await db.commit()
        demo_id, live_id, biz = str(demo.id), str(live.id), live.business_phone_id
    n = uuid.uuid4().int % 10**6
    p_new, p_out, p_mgr = f"+2547{n:06d}1", f"+2547{n:06d}2", f"+2547{n:06d}3"
    async with AsyncSessionLocal() as db:
        await wa_api._set_consent(db, p_out, "OPTED_OUT", "inbound:STOP")
        await db.commit()

    async with _client() as c:                      # 6: the coarse module right is not enough
        await _login(c, rep)
        assert (await c.post("/api/v1/whatsapp/consents", json={"phone": p_new, "status": "OPTED_OUT"})).status_code == 403
        assert (await c.get(f"/api/v1/whatsapp/consents/{p_new}")).status_code == 403
        assert (await c.post("/api/v1/whatsapp/configs", json={"display_name": "x"})).status_code == 403
        assert (await c.patch(f"/api/v1/whatsapp/configs/{demo_id}", json={"display_name": "x"})).status_code == 403
        r = await c.post("/api/v1/whatsapp/simulate-inbound", json={"config_id": demo_id, "phone": p_out, "body": "START"})
        assert r.status_code == 403                 # 1: not an admin
    async with _client() as c:
        await _login(c, viewer)
        assert (await c.get(f"/api/v1/whatsapp/consents/{p_new}")).status_code == 200
        assert (await c.post("/api/v1/whatsapp/consents", json={"phone": p_new, "status": "OPTED_OUT"})).status_code == 403
    async with _client() as c:
        await _login(c, mgr)
        assert (await c.patch(f"/api/v1/whatsapp/configs/{demo_id}", json={"display_name": "POVU demo 2"})).status_code == 200
        assert (await c.post("/api/v1/whatsapp/consents", json={"phone": p_mgr, "status": "OPTED_IN", "proof": "Signed at Duka Moja"})).status_code == 200
    async with _client() as c:                      # 1: admin on a demo config: logged, but no keywords and no window
        await _login(c, admin)
        r = await c.post("/api/v1/whatsapp/simulate-inbound", json={"config_id": demo_id, "phone": p_out, "body": "START"})
        assert r.status_code == 201, r.text
        assert r.json()["external_msg_id"].startswith("sim_")
        assert (await c.post("/api/v1/whatsapp/simulate-inbound", json={"config_id": demo_id, "phone": p_new, "body": "Habari"})).status_code == 201
        r = await c.post("/api/v1/whatsapp/simulate-inbound", json={"config_id": live_id, "phone": p_new, "body": "Habari"})
        assert r.status_code == 403                 # live config
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(WhatsAppConsent.status).where(WhatsAppConsent.phone == p_out))).scalar_one() == "OPTED_OUT"
        assert "no WhatsApp opt-in" in (await wa_api.send_blocked_reason(db, p_new))
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        with pytest.raises(HTTPException) as e:
            await wa_api.simulate_inbound(WASimulateInbound(config_id=demo_id, phone=p_new, body="x"), db=db, _=admin_u)
        assert e.value.status_code == 403
        monkeypatch.setattr(settings, "ENVIRONMENT", "development")

    # 7: a compact-JSON body signed with the real secret passes verification and opens the window
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", "t005-app-secret")
    raw = json.dumps({"entry": [{"changes": [{"value": {"metadata": {"phone_number_id": biz}, "contacts": [],
                      "messages": [{"from": p_new.lstrip("+"), "id": f"wamid.{uuid.uuid4().hex}", "type": "text",
                                    "text": {"body": "Bei ya POVU AllClean 1 L?"}}]}}]}]}, separators=(",", ":")).encode()
    sig = "sha256=" + hmac.new(b"t005-app-secret", raw, hashlib.sha256).hexdigest()
    async with _client() as pub:
        r = await pub.post("/api/v1/whatsapp/webhook", content=raw, headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"})
        assert r.status_code == 200, r.text
    async with AsyncSessionLocal() as db:
        assert await wa_api.send_blocked_reason(db, p_new) is None


# ── DB: verified web identity (2) ─────────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_form_shortening_only_for_verified_identity():
    import random
    from sqlalchemy import select
    from app.api.v1.endpoints.crm_lead_forms_public import KnownIn, known_fields
    from app.api.v1.endpoints.portal_self import WebIdentityIn, verify_web_identity
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMContact, CRMContactConsent, CRMLeadForm, CRMRecord
    from app.models.sales import Customer
    from app.services import crm_contact_service as cs
    from app.services import crm_lead_capture_service as capture
    from app.services import web_analytics_service as wa
    attacker_v, victim_v = uuid.uuid4().hex, uuid.uuid4().hex
    victim, slug = f"victim-{uuid.uuid4().hex[:5]}@povu-demo.test", f"t005-{uuid.uuid4().hex[:6]}"
    async with AsyncSessionLocal() as db:
        form = CRMLeadForm(slug=slug, name="T005", title="Order POVU", require_consent=False, active_flag=True,
                           consent_text="Send me POVU offers")
        c = CRMContact(full_name="Amina POVU", email=victim, phone="+254711000333", source="manual")
        cust = Customer(code=f"C-{uuid.uuid4().hex[:6]}", name="Duka Moja", email=victim)
        db.add_all([form, c, cust])
        await db.flush()
        await cs.associate(db, c.id, "customer", cust.id)
        await capture.set_skip_list(db, form, ["company_name", "contact_person_name"])
        for v in (attacker_v, victim_v):
            await wa.record_consent(db, v, True, True)
        await db.flush()
        assert await wa.identify(db, attacker_v, victim)            # anybody can type anybody's address
        await db.commit()
        req = SimpleNamespace(client=SimpleNamespace(host=f"10.7.{random.randint(0, 250)}.{random.randint(1, 250)}"))
        assert await known_fields(slug, KnownIn(visitor=attacker_v), req, db) == {"omit": []}   # unverified: same shape, nothing
        assert await capture.known_values(db, attacker_v) == {}
    async with _client() as anon:
        r = await anon.post(f"/api/v1/public/lead-forms/{slug}/submit", json={"visitor": attacker_v, "consent": True})
        assert r.status_code == 422                                  # nothing filled: company still required
        r = await anon.post(f"/api/v1/public/lead-forms/{slug}/submit",
                            json={"visitor": attacker_v, "company_name": "Attacker Ltd", "consent": True})
        assert r.status_code == 202, r.text
    async with AsyncSessionLocal() as db:
        lead = (await db.execute(select(CRMRecord).where(CRMRecord.source_detail.like(f"form:{slug}%")))).scalars().one()
        assert lead.contact_email is None and lead.contact_person_name is None
        assert (await db.execute(select(CRMContactConsent).where(CRMContactConsent.email == victim))).scalar_one_or_none() is None
        # the signed-in portal user is verified for their own address only
        out = await verify_web_identity(WebIdentityIn(visitor=victim_v), user=SimpleNamespace(email=victim), db=db)
        assert out == {"linked": True, "verified": True}
        assert sorted((await known_fields(slug, KnownIn(visitor=victim_v), req, db))["omit"]) == ["company_name", "contact_person_name"]
        assert await capture.known_values(db, victim_v) == {"company_name": "Duka Moja", "contact_person_name": "Amina POVU"}
        # identifying with a different address drops the verification; the same address keeps it
        assert await wa.identify(db, victim_v, victim.upper())
        assert await wa.verified_email(db, victim_v) == victim
        assert await wa.identify(db, victim_v, "other@povu-demo.test")
        await db.commit()
        assert await wa.verified_email(db, victim_v) is None
        assert (await known_fields(slug, KnownIn(visitor=victim_v), req, db)) == {"omit": []}


@DB
@pytest.mark.asyncio
async def test_web_event_enrolment_needs_verified_identity():
    from datetime import datetime, timedelta, timezone
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMRecord, WebEvent
    from app.models.m47_automation import WebEventDefinition
    from app.services import crm_workflow_service as wfs
    from app.services import web_analytics_service as wa
    tag = uuid.uuid4().hex[:8]
    name, email = f"demo_t005_{tag}", f"buyer-{tag}@povu-demo.test"
    ver = SimpleNamespace(id=uuid.uuid4())
    started = []

    async def fake_start(db, v, rid, key, now):
        started.append(rid)
        return uuid.uuid4()
    async with AsyncSessionLocal() as db:
        db.add_all([WebEventDefinition(name=name, properties={}, active=True), CRMRecord(company_name="Duka Moja", contact_email=email)])
        v = uuid.uuid4().hex
        await wa.record_consent(db, v, True, True)
        await db.flush()
        assert await wa.identify(db, v, email)
        await wa.collect(db, v, uuid.uuid4().hex, [{"event_id": uuid.uuid4().hex, "kind": "CUSTOM", "name": name, "path": "/demo"}])
        await db.flush()
        orig, wfs.start_run = wfs.start_run, fake_start
        try:
            since, now = datetime.now(timezone.utc) - timedelta(minutes=5), datetime.now(timezone.utc)
            assert await wfs._enqueue_web(db, ver, name, since, now) == 0 and started == []
            assert await wa.identify(db, v, email, verified=True)
            await db.flush()
            assert await wfs._enqueue_web(db, ver, name, since, now) == 1 and len(started) == 1
        finally:
            wfs.start_run = orig
        await db.rollback()


# ── DB: CPQ tax (3) and report-builder total (4) ──────────────────────────────

@DB
@pytest.mark.asyncio
async def test_quote_draft_tax_is_a_percentage_and_report_total_uses_fraction_discount():
    from sqlalchemy import select, text
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMRecord
    from app.models.sales import SOLine
    from app.services import cpq_service as cpq
    from app.services.report_builder_service import SQL_MAP
    from tests.test_m47_s01_t009_sales_depth import _world
    s = uuid.uuid4().hex[:5]
    _, rep_id, _, prod_id, so_id, deal_id = await _world(s)        # SO line: 24 × 50, tax 0.16; price book 55
    async with AsyncSessionLocal() as db:
        rec = await db.get(CRMRecord, deal_id)
        d = await cpq.propose_quote(db, rec)
        assert [l["tax_rate"] for l in d["lines"]] == ["16.00"]
        lines = [{"product_id": l["product_id"], "qty": 30, "unit": l["unit"], "tax_rate": l["tax_rate"]} for l in d["lines"]]
        q = await cpq.save_proposed_quote(db, rec, lines, SimpleNamespace(id=rep_id))
        assert q.lines[0].tax_rate == Decimal("16")
        assert q.total_amount == Decimal("1650.0000") and q.tax_amount == Decimal("264.0000") and q.grand_total == Decimal("1914.0000")
        await db.rollback()
        from app.api.v1.endpoints.cpq import DraftLineIn
        assert DraftLineIn(product_id=prod_id, qty=1, tax_rate=16).tax_rate == 16
        with pytest.raises(ValueError):
            DraftLineIn(product_id=prod_id, qty=1, tax_rate=101)

        ln = (await db.execute(select(SOLine).where(SOLine.so_id == so_id))).scalars().one()
        ln.discount_pct = Decimal("0.10")                         # 10 % as a fraction
        await db.commit()
        total = (await db.execute(text(f"SELECT {SQL_MAP['sales_orders']['total_amount']} FROM sales_orders WHERE id = :i"),
                                  {"i": so_id})).scalar_one()
        assert Decimal(total) == Decimal("1080")                  # 24 × 50 × 0.9


# ── DB: CMS bundle site settings (13) ─────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_bundle_cannot_switch_off_approval_or_bypass_site_validators():
    from app.db.session import AsyncSessionLocal
    from app.models.cms import CmsSite
    from app.services import cms_bundle_service as cbs
    k = f"t005-{uuid.uuid4().hex[:6]}"
    base = {"theme": {}, "nav": [], "require_approval": False}
    async with AsyncSessionLocal() as db:
        db.add(CmsSite(key=k, name="POVU site", locales=["en"], default_locale="en", theme={}, nav=[], require_approval=True,
                       domain_status="LOCAL_ONLY", created_by="t005"))
        await db.flush()
        [st] = await cbs.plan(db, {"sites": [{**base, "key": k, "name": "POVU site 2", "locales": ["en", "sw", "xx"],
                                              "default_locale": "sw"}]}, "overwrite")
        assert st["action"] == "update" and st["row"]["require_approval"] is True
        assert st["row"]["locales"] == ["en", "sw"] and st["row"]["default_locale"] == "sw"
        for bad in ({"name": "x" * 151, "locales": ["en"], "default_locale": "en"},
                    {"name": "ok", "locales": ["xx"], "default_locale": "xx"},
                    {"name": "ok", "locales": ["en"], "default_locale": "tr"}):
            [st] = await cbs.plan(db, {"sites": [{**base, "key": k, **bad}]}, "overwrite")
            assert st["action"] == "error", bad
        new = f"{k}-new"
        [st] = await cbs.plan(db, {"sites": [{**base, "key": new, "name": "New POVU", "locales": ["en"], "default_locale": "en"}]}, "overwrite")
        assert st["action"] == "create" and st["row"]["require_approval"] is False   # a new site keeps the bundle's choice
        await db.rollback()


# ── DB: contact search (15) ───────────────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_contact_search_ignores_hidden_fields():
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMContact
    from app.models.m47_platform import FieldPermissionRule
    tag = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        hidden = await _user(db, ("crm.view_all",), "cshid")
        plain = (await _user(db, ("crm.view_all",), "csplain")).username
        db.add(FieldPermissionRule(entity="contact", role_name=hidden.roles[0].name, field_key="email", access="HIDDEN", created_by="t005"))
        db.add(CRMContact(full_name=f"Wanjiru {tag}", email=f"secret-{tag}@povu-demo.test", phone="+254700111222", source="manual"))
        await db.commit()
        hidden = hidden.username
    async with _client() as c:
        await _login(c, hidden)
        assert (await c.get("/api/v1/crm-contacts", params={"q": f"secret-{tag}"})).json() == []
        rows = (await c.get("/api/v1/crm-contacts", params={"q": f"wanjiru {tag}"})).json()
        assert len(rows) == 1 and "email" not in rows[0]
    async with _client() as c:
        await _login(c, plain)
        assert len((await c.get("/api/v1/crm-contacts", params={"q": f"secret-{tag}"})).json()) == 1
