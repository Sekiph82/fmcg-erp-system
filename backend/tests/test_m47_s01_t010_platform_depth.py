"""M47.S01.T010 platform and service depth (unit + DB; DB tests need M46_DB=1 and the T010 tables).

Field-level permissions, form shortening + smart properties, ticket pipelines, Slack routing + interactive approvals,
campaign / nurture agent templates, ad audience + conversion uploads against the local simulators. Synthetic POVU
data only (povu-demo.test addresses)."""
import os
import time
import uuid
from datetime import date, datetime, timedelta, timezone

import httpx
import pytest

DB = pytest.mark.skipif(os.environ.get("M46_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
PW = uuid.uuid4().hex + "Aa1!"
SECRET = "sim-slack-signing-secret"


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M46_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def _app():
    """The real app plus this task's routers (the coordinator registers them in module_registry)."""
    from app.main import app
    if not getattr(app.state, "t010_routes", False):
        from app.api.v1.endpoints import platform_depth, platform_depth_public
        app.include_router(platform_depth.router, prefix="/api/v1/platform-depth")
        app.include_router(platform_depth_public.router, prefix="/api/v1/public/slack")
        app.state.t010_routes = True
    return app


def _client(ip: str = "127.0.0.1"):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=_app(), client=(ip, 50000)), base_url="http://erp.test")


# ── unit ──────────────────────────────────────────────────────────────────────

def test_field_rule_helpers():
    from app.services import sensitive_service as sens
    out = sens.strip_hidden({"phone": "+254700000001", "notes": "x", "properties": {"phone": 1, "tier": "A"}, "data": {"serial": "S1"}},
                            {"phone": "HIDDEN", "serial": "HIDDEN", "notes": "READ_ONLY"})
    assert "phone" not in out and "phone" not in out["properties"] and "serial" not in out["data"] and out["notes"] == "x"
    assert out["hidden_fields"] == ["phone", "serial"]
    sens.check_write({"notes": "READ_ONLY"}, {"notes": "same"}, {"notes": "same"})          # unchanged value is fine
    with pytest.raises(PermissionError):
        sens.check_write({"notes": "READ_ONLY"}, {"notes": "new"}, {"notes": "same"})


def test_slack_signature(monkeypatch):
    from app.services import messaging_service as ms
    from tests.provider_sim.slack_app import signed_interaction
    monkeypatch.delenv("SLACK_SIGNING_SECRET", raising=False)
    with pytest.raises(ms.MessagingError, match="NOT_CONFIGURED"):
        ms.verify_slack(b"x", str(int(time.time())), "v0=00")
    monkeypatch.setenv("SLACK_SIGNING_SECRET", SECRET)
    body, h = signed_interaction(SECRET, "U1", "approve:x")
    assert ms.verify_slack(body, h["X-Slack-Request-Timestamp"], h["X-Slack-Signature"])
    assert not ms.verify_slack(body + b"1", h["X-Slack-Request-Timestamp"], h["X-Slack-Signature"])
    old, ho = signed_interaction(SECRET, "U1", "approve:x", ts=int(time.time()) - 301)
    assert not ms.verify_slack(old, ho["X-Slack-Request-Timestamp"], ho["X-Slack-Signature"])
    other, hx = signed_interaction("another-secret", "U1", "approve:x")
    assert not ms.verify_slack(other, hx["X-Slack-Request-Timestamp"], hx["X-Slack-Signature"])


def test_hashing_normalises():
    import hashlib
    from app.services import ads_adapters as ads
    assert ads.hash_email("  Duka.Moja@POVU-demo.test ") == hashlib.sha256(b"duka.moja@povu-demo.test").hexdigest()
    assert ads.hash_phone("0712 345 678", plus=True) == hashlib.sha256(b"+254712345678").hexdigest()
    assert ads.hash_phone("0712 345 678", plus=False) == hashlib.sha256(b"254712345678").hexdigest()
    assert ads.hash_email("not-an-email") is None and ads.hash_phone("", plus=True) is None


def test_agent_templates_validate():
    from app.services import agent_service as ags
    for key in ("campaign_planner", "nurture_sequence"):
        v = ags.validate(ags.TEMPLATES[key]["definition"])
        assert v["order"] == ["s1", "s2", "s3", "s4"]
    assert ags.TOOLS["draft_campaign"]["draft"] and not ags.TOOLS["draft_campaign"]["write"]


# ── helpers ───────────────────────────────────────────────────────────────────

async def _user(db, perms: tuple, tag: str):
    from sqlalchemy import select
    from app.core.security import hash_password
    from app.models.role import Permission, Role
    from app.models.user import User
    u = User(username=f"{tag}-{uuid.uuid4().hex[:6]}", email=f"{tag}-{uuid.uuid4().hex[:6]}@povu-demo.test", full_name=tag.title(),
             hashed_password=hash_password(PW), is_active=True)
    role = Role(name=f"{tag}-{uuid.uuid4().hex[:6]}", is_active=True)
    for code in perms:
        p = (await db.execute(select(Permission).where(Permission.code == code))).scalar_one_or_none()
        if p is None:
            p = Permission(code=code, name=code, module=code.split(".")[0], action=code.split(".")[1], is_active=True)
            db.add(p)
            await db.flush()
        role.permissions.append(p)
    u.roles.append(role)
    db.add_all([role, u])
    await db.flush()
    return u


async def _loaded(db, uid):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.role import Role
    from app.models.user import User
    return (await db.execute(select(User).options(selectinload(User.roles).selectinload(Role.permissions))
                             .where(User.id == uid))).scalar_one()


async def _login(c, username):
    r = await c.post("/api/v1/auth/login", data={"username": username, "password": PW})
    assert r.status_code == 200, r.text


# ── 1. field-level permissions ────────────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_field_permissions_read_and_write():
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        admin = await _user(db, ("roles.manage", "crm.view_all", "crm.edit_all"), "dataadmin")
        rep = await _user(db, ("crm.view_all", "crm.edit_all"), "rep")
        await db.commit()
        rep_role, admin_name, rep_name = rep.roles[0].name, admin.username, rep.username
    async with _client() as ca, _client() as cr:
        await _login(ca, admin_name)
        await _login(cr, rep_name)
        # rules are managed by data admins only
        assert (await cr.put("/api/v1/platform-depth/field-permissions", json={"entity": "contact", "role_name": rep_role,
                                                                              "field_key": "phone", "access": "HIDDEN"})).status_code == 403
        for key, acc in (("phone", "HIDDEN"), ("notes", "READ_ONLY")):
            r = await ca.put("/api/v1/platform-depth/field-permissions", json={"entity": "contact", "role_name": rep_role,
                                                                              "field_key": key, "access": acc})
            assert r.status_code == 200, r.text
        r = await ca.post("/api/v1/crm-contacts", json={"full_name": "Amina POVU", "email": f"amina-{uuid.uuid4().hex[:5]}@example.com",
                                                         "phone": "+254700111222", "notes": "Prefers POVU AllClean 1 L"})
        assert r.status_code == 201, r.text
        cid = r.json()["id"]
        # read: hidden key removed for the rep (detail and list), visible for the exempt admin
        d = (await cr.get(f"/api/v1/crm-contacts/{cid}")).json()
        assert "phone" not in d and d["notes"] == "Prefers POVU AllClean 1 L" and d["hidden_fields"] == ["phone"]
        assert all("phone" not in x for x in (await cr.get("/api/v1/crm-contacts")).json())
        assert (await ca.get(f"/api/v1/crm-contacts/{cid}")).json()["phone"] == "+254700111222"
        # write: hidden / read-only changes refused; unchanged / left-out restricted fields keep their stored value
        base = {"full_name": "Amina POVU", "email": d["email"], "notes": "Prefers POVU AllClean 1 L"}
        assert (await cr.put(f"/api/v1/crm-contacts/{cid}", json={**base, "phone": "+254700999999"})).status_code == 403
        assert (await cr.put(f"/api/v1/crm-contacts/{cid}", json={**base, "notes": "changed"})).status_code == 403
        r = await cr.put(f"/api/v1/crm-contacts/{cid}", json={**base, "job_title": "Buyer"})
        assert r.status_code == 200, r.text
        assert (await ca.get(f"/api/v1/crm-contacts/{cid}")).json()["phone"] == "+254700111222"
        assert (await ca.put(f"/api/v1/crm-contacts/{cid}", json={**base, "notes": "admin may"})).status_code == 200
        # custom object fields
        fz = f"fz{uuid.uuid4().hex[:8]}"
        t = await ca.post("/api/v1/custom-objects/types", json={"key": fz, "label": "Freezer", "fields": [
            {"key": "site", "type": "text"}, {"key": "serial", "type": "text"}, {"key": "capacity", "type": "number"}]})
        assert t.status_code == 201, t.text
        for key, acc in (("serial", "HIDDEN"), ("capacity", "READ_ONLY")):
            assert (await ca.put("/api/v1/platform-depth/field-permissions", json={"entity": f"co:{fz}", "role_name": rep_role,
                                                                                  "field_key": key, "access": acc})).status_code == 200
        assert (await ca.put("/api/v1/platform-depth/field-permissions", json={"entity": f"co:{fz}", "role_name": rep_role,
                                                                              "field_key": "nope", "access": "HIDDEN"})).status_code == 422
        rec = await ca.post(f"/api/v1/custom-objects/{fz}/records", json={"data": {"site": "Duka Moja", "serial": "FZ-001", "capacity": 200}})
        assert rec.status_code == 201, rec.text
        rid = rec.json()["id"]
        g = (await cr.get(f"/api/v1/custom-objects/{fz}/records/{rid}")).json()
        assert "serial" not in g["data"] and g["data"]["capacity"] == 200
        assert "serial" not in (await cr.get(f"/api/v1/custom-objects/{fz}/export.csv")).text
        assert (await cr.put(f"/api/v1/custom-objects/{fz}/records/{rid}", json={"data": {"site": "x", "serial": "FZ-9", "capacity": 200}})).status_code == 403
        assert (await cr.put(f"/api/v1/custom-objects/{fz}/records/{rid}", json={"data": {"site": "x", "capacity": 300}})).status_code == 403
        ok = await cr.put(f"/api/v1/custom-objects/{fz}/records/{rid}", json={"data": {"site": "Duka Mbili", "capacity": 200}})
        assert ok.status_code == 200, ok.text
        full = (await ca.get(f"/api/v1/custom-objects/{fz}/records/{rid}")).json()["data"]
        assert full == {"site": "Duka Mbili", "serial": "FZ-001", "capacity": 200.0}


# ── 2. form shortening + smart properties ─────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_form_shortening_and_smart_properties():
    from sqlalchemy import select
    from app.api.v1.endpoints.crm_lead_forms_public import KnownIn, known_fields
    from app.db.session import AsyncSessionLocal
    from app.models.crm import (CRMActivity, CRMActivityResult, CRMActivityType, CRMContact, CRMLeadForm, CRMRecord,
                                CRMRecordType)
    from app.models.m47_platform import CRMContactProperty
    from app.models.sales import Customer, SalesOrder
    from app.services import crm_contact_service as cs
    from app.services import crm_lead_capture_service as capture
    from app.services import web_analytics_service as wa
    vid, stranger = uuid.uuid4().hex, uuid.uuid4().hex
    email, slug = f"wanjiru-{uuid.uuid4().hex[:5]}@povu-demo.test", f"t010-{uuid.uuid4().hex[:6]}"
    async with AsyncSessionLocal() as db:
        form = CRMLeadForm(slug=slug, name="T010", title="Order POVU", require_consent=False, active_flag=True)
        c = CRMContact(full_name="Wanjiru POVU", email=email, phone="+254711000222", source="manual")
        cust = Customer(code=f"C-{uuid.uuid4().hex[:6]}", name="Duka Moja", email=email)
        db.add_all([form, c, cust])
        await db.flush()
        await cs.associate(db, c.id, "customer", cust.id)
        await capture.set_skip_list(db, form, ["company_name", "contact_person_name"])
        for bad in (["message"], ["contact_email"], ["contact_phone"]):   # M47 review: identifying fields are always typed
            with pytest.raises(ValueError):
                await capture.set_skip_list(db, form, bad)
        await wa.record_consent(db, vid, True, True)
        await db.flush()
        assert await wa.identify(db, vid, email, verified=True)   # M47 review: only a verified identity is recognised
        await db.commit()
        from types import SimpleNamespace
        req = SimpleNamespace(client=SimpleNamespace(host=f"10.9.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}"))
        omit = (await known_fields(slug, KnownIn(visitor=vid), req, db))["omit"]
        assert sorted(omit) == ["company_name", "contact_person_name"]
        assert (await known_fields(slug, KnownIn(visitor=stranger), req, db)) == {"omit": []}
        from fastapi import HTTPException
        from app.api.v1.endpoints import crm_lead_forms_public as lfp
        for _ in range(lfp.KNOWN_LIMIT[0] - 2):
            await known_fields(slug, KnownIn(visitor=stranger), req, db)
        with pytest.raises(HTTPException) as e:                   # per-IP rate limit on the lookup
            await known_fields(slug, KnownIn(visitor=stranger), req, db)
        assert e.value.status_code == 429
    import random
    async with _client(f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}") as anon:
        r = await anon.post(f"/api/v1/public/lead-forms/{slug}/submit", json={"visitor": vid})   # company + name filled for the verified visitor
        assert r.status_code == 202, r.text
        assert email not in r.text and "+254711000222" not in r.text            # nothing is echoed back
        r = await anon.post(f"/api/v1/public/lead-forms/{slug}/submit", json={"visitor": stranger, "contact_email": "x@example.com"})
        assert r.status_code == 422
    async with AsyncSessionLocal() as db:
        lead = (await db.execute(select(CRMRecord).where(CRMRecord.source_detail.like(f"form:{slug}%")))).scalars().one()
        assert lead.contact_person_name == "Wanjiru POVU" and lead.company_name == "Duka Moja"
        assert lead.contact_email is None and lead.contact_phone is None     # identifying fields are never filled
        await wa.record_consent(db, vid, True, False)            # marketing consent withdrawn → no longer recognised
        await db.commit()
        assert await capture.omitted(db, await db.get(CRMLeadForm, form.id), vid) == []
        # smart properties from activity
        rec = CRMRecord(record_type=CRMRecordType.LEAD, company_name="Duka Moja", contact_email=email, created_by="t010",
                        activities=[], interest_lines=[])
        db.add(rec)
        await db.flush()
        await cs.associate(db, c.id, "crm_record", rec.id)
        now = datetime.now(timezone.utc)
        for t in (CRMActivityType.CALL, CRMActivityType.CALL, CRMActivityType.EMAIL):
            db.add(CRMActivity(crm_record_id=rec.id, activity_type=t, subject="Follow-up", result_status=CRMActivityResult.COMPLETED))
        db.add(CRMActivity(crm_record_id=rec.id, activity_type=CRMActivityType.NOTE, subject="Visit note",
                           notes="Shop owner: #objection: shelf price of POVU WhiteCare 1 kg too high", result_status=CRMActivityResult.COMPLETED))
        db.add(SalesOrder(order_no=f"SO-{uuid.uuid4().hex[:6]}", customer_id=cust.id, order_date=date(2026, 11, 20),
                          requested_delivery_date=date(2026, 11, 22)))
        await db.commit()
        assert await cs.recompute_smart_properties(db, [c.id]) == 3
        await db.commit()
        props = {p.key: (p.value, p.source) for p in (await db.execute(select(CRMContactProperty).where(
            CRMContactProperty.contact_id == c.id))).scalars()}
        assert props == {"last_order_date": ("2026-11-20", "SMART"), "preferred_channel": ("CALL", "SMART"),
                         "last_objection": ("shelf price of POVU WhiteCare 1 kg too high", "SMART")}
        assert await cs.recompute_smart_properties(db, [c.id]) == 0                 # idempotent
        _ = now


# ── 3. ticket pipelines ──────────────────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_ticket_pipelines():
    from app.db.session import AsyncSessionLocal
    from app.models.service_desk import TicketSLA
    async with AsyncSessionLocal() as db:
        lead = await _user(db, ("crm.view", "crm.edit", "crm.edit_all", "helpdesk.view", "helpdesk.edit"), "svclead")
        agent = await _user(db, ("crm.view", "crm.edit", "helpdesk.view", "helpdesk.edit"), "agent")
        stranger = await _user(db, ("procurement.view",), "nosupport")
        viewer = await _user(db, ("crm.view",), "viewer")
        await db.commit()
        ln, an, sn, vn = lead.username, agent.username, stranger.username, viewer.username
    async with _client() as cl, _client() as ca:
        await _login(cl, ln)
        await _login(ca, an)
        t = await ca.post("/api/v1/helpdesk/", json={"subject": "POVU AllClean 1 L carton short", "category": "DELIVERY", "priority": "HIGH"})
        assert t.status_code == 201, t.text
        tid = t.json()["id"]
        ps = (await ca.get("/api/v1/helpdesk/pipelines")).json()
        default = next(p for p in ps if p["is_default"])
        assert [s["name"] for s in default["stages"]][:3] == ["New", "In progress", "Waiting on customer"]
        assert (await ca.get(f"/api/v1/helpdesk/{tid}/stage")).json()["stage"] == "New"     # existing ticket, no row yet
        assert (await ca.post("/api/v1/helpdesk/pipelines", json={"name": "Returns", "stages": [{"name": "Open", "status": "OPEN"}]})).status_code == 403
        bad = await cl.post("/api/v1/helpdesk/pipelines", json={"name": "Bad", "stages": [{"name": "X", "status": "NOPE"}]})
        assert bad.status_code == 422
        r = await cl.post("/api/v1/helpdesk/pipelines", json={"name": f"Returns {uuid.uuid4().hex[:4]}", "stages": [
            {"name": "Logged", "status": "OPEN"}, {"name": "Collecting", "status": "IN_PROGRESS", "pauses_sla": True},
            {"name": "Credited", "status": "RESOLVED"}]})
        assert r.status_code == 201, r.text
        wait = next(s for s in default["stages"] if s["name"] == "Waiting on customer")
        m = (await ca.post(f"/api/v1/helpdesk/{tid}/stage", json={"stage_id": wait["id"]})).json()
        assert m["status"] == "IN_PROGRESS" and m["sla_paused"]
        async with AsyncSessionLocal() as db:
            assert (await db.get(TicketSLA, uuid.UUID(tid))).paused_at is not None
        res = next(s for s in default["stages"] if s["name"] == "Resolved")
        assert (await ca.post(f"/api/v1/helpdesk/{tid}/stage", json={"stage_id": res["id"]})).json()["status"] == "RESOLVED"
        detail = (await ca.get(f"/api/v1/helpdesk/{tid}")).json()
        assert detail["status"] == "RESOLVED" and detail["resolved_at"]
        async with AsyncSessionLocal() as db:
            assert (await db.get(TicketSLA, uuid.UUID(tid))).paused_at is None
        # service-desk routes need the helpdesk rights (T003 audit): view to read, edit (or an agent profile) to act
        async with _client() as cs_, _client() as cv:
            await _login(cs_, sn)
            await _login(cv, vn)
            assert (await cs_.get("/api/v1/service-desk/overview")).status_code == 403
            assert (await cs_.get(f"/api/v1/service-desk/tickets/{tid}")).status_code == 403
            for path in (f"/api/v1/service-desk/tickets/{tid}/pause", f"/api/v1/service-desk/tickets/{tid}/route",
                         f"/api/v1/service-desk/tickets/{tid}/macro/{uuid.uuid4()}"):
                assert (await cs_.post(path)).status_code == 403
                assert (await cv.post(path)).status_code == 403          # view only: no writes
            assert (await cv.get(f"/api/v1/service-desk/tickets/{tid}")).status_code == 200
            assert (await ca.post(f"/api/v1/service-desk/tickets/{tid}/route")).status_code == 200
        board = (await ca.get(f"/api/v1/helpdesk/pipelines/{default['id']}/board")).json()
        assert [t["id"] for s in board["stages"] if s["name"] == "Resolved" for t in s["tickets"]].count(tid) == 1


# ── 4. Slack routing + interactive approvals ─────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_slack_routes_and_interactive_approval(monkeypatch):
    from app.core import provider_http
    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    from app.models.workflow import ApprovalModule, ApprovalRequest, ApprovalStatus, ApprovalStep
    from app.services import messaging_service as ms
    from tests.provider_sim.slack_app import create_slack_app, signed_interaction
    monkeypatch.setattr(settings, "SLACK_WEBHOOK_URL", "")
    monkeypatch.delenv("SLACK_SIGNING_SECRET", raising=False)
    async with AsyncSessionLocal() as db:
        from sqlalchemy import delete
        from app.models.crm import SlackDelivery
        from app.models.m47_platform import SlackRoute
        await db.execute(delete(SlackRoute))          # disposable DB: start without routes or queued notices
        await db.execute(delete(SlackDelivery))
        from sqlalchemy import update
        await db.execute(update(ApprovalRequest).where(ApprovalRequest.status == ApprovalStatus.PENDING)
                         .values(status=ApprovalStatus.CANCELLED))
        admin = await _user(db, ("crm.view_all", "crm.edit_all"), "slackadmin")
        approver = await _user(db, ("procurement.view",), "approver")
        requester = await _user(db, ("procurement.view",), "requester")
        outsider = await _user(db, ("procurement.view",), "outsider")
        requester.roles.append(approver.roles[0])               # holds the role, but it is their own request
        await db.flush()
        req = ApprovalRequest(module=ApprovalModule.PURCHASE_ORDER, object_id=uuid.uuid4(), object_ref="PO-POVU-1",
                              status=ApprovalStatus.PENDING, current_level=1, max_level=1, requested_by_id=requester.id)
        db.add(req)
        await db.flush()
        db.add(ApprovalStep(request_id=req.id, level=1, required_role=approver.roles[0].name, status=ApprovalStatus.PENDING,
                            sla_deadline=datetime.now(timezone.utc) + timedelta(hours=24)))
        await db.commit()
        names = {k: u.username for k, u in (("admin", admin), ("approver", approver), ("requester", requester), ("outsider", outsider))}
        rid = str(req.id)
    sx = uuid.uuid4().hex[:6].upper()              # Slack ids unique per run
    sim = create_slack_app()
    provider_http.set_test_transport(httpx.ASGITransport(app=sim))
    try:
        async with _client() as c:
            # no secret → interaction endpoint NOT_CONFIGURED
            body, h = signed_interaction(SECRET, "U0", f"approve:{rid}")
            assert (await c.post("/api/v1/public/slack/interactions", content=body, headers=h)).status_code == 503
            async with AsyncSessionLocal() as db:
                assert (await ms.slack_tick(db))["status"] == "NOT_CONFIGURED"     # no webhook, no route
            await _login(c, names["admin"])
            assert (await c.put("/api/v1/platform-depth/slack/routes", json={"event_type": "APPROVE", "channel_label": "#approvals",
                                                                             "webhook_url": "https://evil.example.com/x"})).status_code == 422
            r = await c.put("/api/v1/platform-depth/slack/routes", json={"event_type": "APPROVE", "channel_label": "#approvals",
                                                                         "webhook_url": "http://slack.test/services/T1/B1/K1"})
            assert r.status_code == 200, r.text
            assert "K1" not in (await c.get("/api/v1/platform-depth/slack/routes")).text          # webhook secret not shown
        monkeypatch.setenv("SLACK_SIGNING_SECRET", SECRET)
        async with AsyncSessionLocal() as db:
            out = await ms.slack_tick(db)
        assert out["status"] == "OK" and out["sent"] == 1
        post = sim.state.posts[0]
        assert post["path"] == "/services/T1/B1/K1"
        assert [e["value"] for e in post["body"]["blocks"][1]["elements"]] == [f"approve:{rid}", f"reject:{rid}"]
        assert "PO-POVU-1" not in str(post["body"])                         # only the kind of item goes to Slack
        for key, slack_id in (("approver", f"U2APPROVER{sx}"), ("requester", f"U1REQUEST{sx}"), ("outsider", f"U3OUTSIDE{sx}")):
            async with _client() as c:
                await _login(c, names[key])
                assert (await c.put("/api/v1/platform-depth/slack/link", json={"slack_user_id": slack_id})).status_code == 200
        async with _client() as c:
            await _login(c, names["outsider"])
            assert (await c.put("/api/v1/platform-depth/slack/link", json={"slack_user_id": f"U2APPROVER{sx}"})).status_code == 409
        async with _client() as anon:
            async def click(slack_id, value, secret=SECRET, ts=None):
                b, hh = signed_interaction(secret, slack_id, value, ts)
                return await anon.post("/api/v1/public/slack/interactions", content=b, headers=hh)
            assert (await click(f"U2APPROVER{sx}", f"approve:{rid}", secret="wrong")).status_code == 401
            assert (await click(f"U2APPROVER{sx}", f"approve:{rid}", ts=int(time.time()) - 600)).status_code == 401
            assert "not linked" in (await click(f"UNKNOWN1{sx}", f"approve:{rid}")).json()["text"]
            assert "may not decide" in (await click(f"U3OUTSIDE{sx}", f"approve:{rid}")).json()["text"]
            assert "other than the requester" in (await click(f"U1REQUEST{sx}", f"approve:{rid}")).json()["text"]
            assert (await click(f"U2APPROVER{sx}", f"approve:{rid}")).json()["text"].startswith("Approved by")
            assert "no longer waiting" in (await click(f"U2APPROVER{sx}", f"reject:{rid}")).json()["text"]
        async with AsyncSessionLocal() as db:
            assert (await db.get(ApprovalRequest, uuid.UUID(rid))).status == ApprovalStatus.APPROVED
    finally:
        provider_http.set_test_transport(None)


# ── 5. campaign / nurture agent templates ─────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_campaign_and_nurture_templates_draft_only():
    from types import SimpleNamespace
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.models.crm import MarketingAudience
    from app.models.marketing import Campaign
    from app.services import agent_service as ags
    async with AsyncSessionLocal() as db:
        owner = await _user(db, ("marketing.view", "marketing.create"), "marketer")
        aud = MarketingAudience(name=f"Nairobi shops {uuid.uuid4().hex[:4]}", rules={"all": []}, member_count=3, require_consent=True)
        db.add(aud)
        await db.commit()
        user = await _loaded(db, owner.id)
        cfg = await ags.settings_get(db)
        inputs = {"goal": "Launch POVU WhiteCare 1 kg in Nairobi", "audience": aud.name}
        agent = SimpleNamespace(name="Campaign planner")
        sim = await ags.run(db, agent, ags.TEMPLATES["campaign_planner"]["definition"], user, inputs, simulate=True,
                            job_ref="sim", cfg=cfg, budget_tokens=20000)
        assert sim["final"]["would_draft"] == "draft_campaign"
        assert (await db.execute(select(Campaign).where(Campaign.owner_user_id == owner.id))).first() is None   # simulate writes nothing
        for key in ("campaign_planner", "nurture_sequence"):
            out = await ags.run(db, agent, ags.TEMPLATES[key]["definition"], user, inputs, simulate=False, job_ref="run",
                                cfg=cfg, budget_tokens=20000)
            assert out["final"]["status"] == "DRAFT" and len(out["proposals"]) == 1
        await db.commit()
        rows = list((await db.execute(select(Campaign).where(Campaign.owner_user_id == owner.id))).scalars())
        assert len(rows) == 2 and {getattr(r.status, "value", r.status) for r in rows} == {"DRAFT"}
        assert {getattr(r.approval_status, "value", r.approval_status) for r in rows} == {"PENDING"}   # waits in the approval queue
        assert any("E-mail 3" in r.notes for r in rows) and all("Nothing has been sent" in r.notes for r in rows)
        with pytest.raises(ags.AgentError):
            await ags.run(db, agent, ags.TEMPLATES["campaign_planner"]["definition"], user, {**inputs, "audience": "missing"},
                          simulate=True, job_ref="sim", cfg=cfg, budget_tokens=20000)


# ── 6. ad audiences + conversions against the simulator ──────────────────────

@DB
@pytest.mark.asyncio
async def test_ad_audience_and_conversion_uploads(monkeypatch):
    import json
    from sqlalchemy import select
    from app.core import provider_http
    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    from app.models.crm import AdAccount, CRMContactConsent, CRMRecord, CRMRecordType, CRMStatus, MarketingAudience, MarketingAudienceMember
    from app.models.m47_platform import AdsConversionUpload
    from app.models.sales import Customer
    from tests.provider_sim.ads_app import ads_sim_settings
    from tests.provider_sim.ads_lists_app import create_lists_app
    for k, v in ads_sim_settings("http://ads.test").items():
        monkeypatch.setattr(settings, k, v)
    monkeypatch.setattr(settings, "AUDIENCE_EXPORT_ENABLED", True)
    monkeypatch.setenv("META_PIXEL_ID", "998877")
    monkeypatch.setenv("GOOGLE_ADS_CONVERSION_ACTION", "customers/4445556666/conversionActions/55")
    tag = uuid.uuid4().hex[:5]
    yes, no = f"duka-{tag}@povu-demo.test", f"nope-{tag}@povu-demo.test"
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        from sqlalchemy import delete
        await db.execute(delete(AdAccount))            # disposable DB: start without connected accounts
        mk = await _user(db, ("marketing.view", "marketing.edit"), "ads")
        c1 = Customer(code=f"A-{tag}", name="Duka Moja", email=yes, phone="0712345678")
        c2 = Customer(code=f"B-{tag}", name="Duka Mbili", email=no, phone="0712000000")
        # require_consent=False on the audience: ad uploads still send only consented people (T003 audit)
        aud = MarketingAudience(name=f"Ads {tag}", rules={"all": []}, require_consent=False, member_count=2)
        db.add_all([c1, c2, aud, CRMContactConsent(email=yes, status="SUBSCRIBED", updated_at=now),
                    CRMContactConsent(email=no, status="UNSUBSCRIBED", updated_at=now)])
        await db.flush()
        db.add_all([MarketingAudienceMember(audience_id=aud.id, customer_id=c1.id, email=yes, added_at=now),
                    MarketingAudienceMember(audience_id=aud.id, customer_id=c2.id, email=no, added_at=now)])
        won = CRMRecord(record_type=CRMRecordType.OPPORTUNITY, company_name="Duka Moja", contact_email=yes, status=CRMStatus.WON,
                        expected_revenue=12500, currency="KES", created_by="t010", activities=[], interest_lines=[])
        db.add(won)
        await db.commit()
        aid, name = str(aud.id), mk.username
    sim = create_lists_app()
    provider_http.set_test_transport(httpx.ASGITransport(app=sim))
    try:
        async with _client() as c:
            await _login(c, name)
            r = await c.post(f"/api/v1/audiences/{aid}/upload/meta")
            assert r.status_code == 200 and r.json()["status"] == "NOT_CONFIGURED"       # no ad account connected
            assert (await c.post("/api/v1/audiences/conversion-uploads/google")).json()["status"] == "NOT_CONFIGURED"
            async with AsyncSessionLocal() as db:
                db.add_all([AdAccount(provider="meta", external_id="1001", name="POVU Synthetic Meta", currency="KES"),
                            AdAccount(provider="google", external_id="444-555-6666", name="POVU Synthetic Google", currency="KES")])
                await db.commit()
            for p in ("meta", "google"):
                r = await c.post(f"/api/v1/audiences/{aid}/upload/{p}")
                assert r.status_code == 200 and r.json()["status"] == "UPLOADED" and r.json()["sent"] == 1, r.text   # consent-filtered
            for p in ("meta", "google"):
                r = await c.post(f"/api/v1/audiences/conversion-uploads/{p}")
                assert r.status_code == 200 and r.json()["status"] == "OK" and r.json()["uploaded"] >= 1, r.text
                assert (await c.post(f"/api/v1/audiences/conversion-uploads/{p}")).json()["uploaded"] == 0      # once only
        wire = json.dumps([b for _, b in sim.state.calls])
        for raw in (yes, no, "0712345678", "254712345678", "+254712345678", "Duka Moja"):
            assert raw not in wire                                                   # no raw PII left the ERP
        kinds = [k for k, _ in sim.state.calls]
        assert kinds.count("meta_users") == 1 and "google_addOperations" in kinds and "google_run" in kinds
        assert "meta_events" in kinds and "google_conversions" in kinds
        async with AsyncSessionLocal() as db:
            rows = list((await db.execute(select(AdsConversionUpload).where(AdsConversionUpload.source_id == won.id))).scalars())
            assert {r.provider for r in rows} == {"meta", "google"} and {r.status for r in rows} == {"UPLOADED"}
    finally:
        provider_http.set_test_transport(None)


def test_live_egress_refuses_simulator(monkeypatch):
    """With PROVIDER_EGRESS=live the local simulator host is refused (and the Slack route validator refuses it too)."""
    from app.core import provider_http
    from app.core.config import settings
    from app.services import messaging_service as ms
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "live")
    with pytest.raises(provider_http.EgressBlocked):
        provider_http.check_egress("http://ads.test/meta/v21.0/act_1/customaudiences")
    assert not ms.valid_webhook("http://slack.test/services/T/B/K")
    assert ms.valid_webhook("https://hooks.slack.com/services/T/B/K")
