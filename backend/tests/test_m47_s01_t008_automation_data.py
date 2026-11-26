"""M47.S01.T008 automation and data depth (unit + DB; the DB part needs M46_DB=1 and the T008 tables).

Scheduled (daily / weekly / relative-date) and inbound-webhook workflow triggers with an idempotent run ledger,
custom web-event definitions (property validation, web_event trigger), web-behaviour audience conditions, and
portal / shop usage as a customer-health signal. Explicit tick times stand in for a frozen clock. POVU data only.
"""
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import httpx
import pytest

from app.services import audience_service as aus
from app.services import crm_workflow_service as wfs
from app.services import customer_intel_service as ci
from app.services import web_analytics_service as wa

DB = pytest.mark.skipif(os.environ.get("M46_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
NBO = ZoneInfo("Africa/Nairobi")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M46_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def _graph(trigger: dict) -> dict:
    return {"nodes": [{"id": "t", "type": "trigger", "config": trigger},
                      {"id": "task", "type": "action", "config": {"action_type": "create_task",
                                                                  "payload": {"subject": "Call about POVU AllClean 1 L"}}},
                      {"id": "end", "type": "end"}],
            "edges": [{"from": "t", "to": "task"}, {"from": "task", "to": "end"}]}


# ── unit ──────────────────────────────────────────────────────────────────────

def test_schedule_validation_and_occurrence():
    ok = [{"event": "scheduled", "schedule": {"kind": "daily", "time": "08:00"}},
          {"event": "scheduled", "schedule": {"kind": "weekly", "time": "09:30", "weekday": 0}},
          {"event": "scheduled", "schedule": {"kind": "relative", "time": "07:00", "property": "expected_close_date", "offset_days": -7}},
          {"event": "inbound_webhook"}, {"event": "web_event", "name": "demo_requested"}]
    for t in ok:
        assert wfs.validate(_graph(t)) == [], t
    bad = [({"event": "scheduled", "schedule": {"kind": "daily", "time": "25:00"}}, "HH:MM"),
           ({"event": "scheduled", "schedule": {"kind": "weekly", "time": "09:00"}}, "weekday"),
           ({"event": "scheduled", "schedule": {"kind": "relative", "time": "09:00", "property": "company_name", "offset_days": 1}}, "date property"),
           ({"event": "scheduled", "schedule": {"kind": "daily", "time": "09:00", "tz": "Mars/Base"}}, "time zone"),
           ({"event": "scheduled", "schedule": {"kind": "daily", "time": "09:00", "match": {"field": "notes", "operator": "eq"}}}, "filter"),
           ({"event": "web_event", "name": "has space"}, "defined event"), ({"event": "hourly"}, "trigger event")]
    for t, needle in bad:
        assert any(needle in p for p in wfs.validate(_graph(t))), (t, wfs.validate(_graph(t)))
    # frozen clock: Wednesday 2026-11-25 10:00 Nairobi (07:00 UTC)
    now = datetime(2026, 11, 25, 7, 0, tzinfo=timezone.utc)
    assert wfs.occurrence({"kind": "daily", "time": "08:00"}, now) == datetime(2026, 11, 25, 5, 0, tzinfo=timezone.utc)
    assert wfs.occurrence({"kind": "daily", "time": "11:00"}, now) == datetime(2026, 11, 24, 8, 0, tzinfo=timezone.utc)
    assert wfs.occurrence({"kind": "weekly", "time": "09:00", "weekday": 0}, now) == datetime(2026, 11, 23, 6, 0, tzinfo=timezone.utc)
    assert wfs.occurrence({"kind": "weekly", "time": "11:00", "weekday": 2}, now) == datetime(2026, 11, 18, 8, 0, tzinfo=timezone.utc)
    assert wfs.occurrence({"kind": "daily", "time": "08:00", "tz": "UTC"}, now) == datetime(2026, 11, 24, 8, 0, tzinfo=timezone.utc)


def test_event_definition_and_property_cleaning():
    name, props = wa.validate_definition(" demo_requested ", {"product": "string", "cartons": "number", "trial": "boolean"})
    assert name == "demo_requested"
    for n, p in (("has space", {}), ("ok", {"Bad-Name": "string"}), ("ok", {"x": "date"}), ("ok", {f"p{i}": "string" for i in range(21)})):
        with pytest.raises(ValueError):
            wa.validate_definition(n, p)
    clean = wa.clean_properties(props, {"product": "POVU WhiteCare 1 kg", "cartons": 3, "trial": True, "unknown": "x",
                                        "email": "a@b.c"})
    assert clean == {"product": "POVU WhiteCare 1 kg", "cartons": 3, "trial": True}
    assert wa.clean_properties(props, {"cartons": "3", "trial": 1, "product": 5}) == {}          # wrong types dropped
    assert wa.clean_properties(props, {"cartons": True}) == {}                                  # a bool is not a number


def test_web_audience_rules():
    with pytest.raises(aus.AudienceError):
        aus.validate({"all": [{"field": "visited_path", "op": "eq", "value": "/pricing"}]})     # prefix only
    with pytest.raises(aus.AudienceError):
        aus.validate({"all": [{"field": "web_event", "op": "occurred", "value": "x", "days": 0}]})
    with pytest.raises(aus.AudienceError):
        aus.validate({"all": [{"field": "channel", "op": "prefix", "value": "R"}]})            # web ops only for web fields
    r = aus.validate({"all": [{"field": "visited_path", "op": "prefix", "value": "/pricing", "days": 7},
                              {"field": "web_event", "op": "occurred", "value": "demo_requested"},
                              {"field": "intent_score", "op": "gte", "value": "10"}]})
    now = datetime(2026, 11, 26, tzinfo=timezone.utc)
    facts = {"_now": now, "intent_score": 12.0, "web": [("PAGE", None, "/pricing/povu-allclean", now - timedelta(days=2)),
                                                       ("CUSTOM", "demo_requested", "/demo", now - timedelta(days=20))]}
    assert aus.matches(r, facts)
    assert not aus.matches(r, {**facts, "intent_score": 9.0})
    assert not aus.matches(r, {**facts, "web": [("PAGE", None, "/pricing", now - timedelta(days=8)), facts["web"][1]]})
    assert not aus.matches(r, {**facts, "web": facts["web"][:1]})
    assert not aus.matches(r, {"_now": now, "intent_score": None, "web": []})


def test_usage_component_and_missing():
    f = ci.Features(orders_total=5, last_order=date(2026, 11, 20), orders_90=3, typical_gap=14.0, revenue_90=1000.0, nps_last=9)
    assert "usage" not in ci.health_components(f, date(2026, 11, 26))       # no portal account: not scored as zero
    f.has_portal = True
    assert ci.health_components(f, date(2026, 11, 26))["usage"] == 0.0
    f.usage.update(logins_30d=2, logins_90d=3)
    assert ci.health_components(f, date(2026, 11, 26))["usage"] == 50.0
    f.usage.update(self_service_orders_90d=2)
    assert ci.health_components(f, date(2026, 11, 26))["usage"] == 100.0
    assert len(f.vector(date(2026, 11, 26))) == len(ci.FEATURES) == 10


# ── DB helpers ────────────────────────────────────────────────────────────────

async def _staff(db, tag: str, perms: tuple):
    from app.models.user import User
    u = User(username=f"{tag}-{uuid.uuid4().hex[:6]}", email=f"{tag}-{uuid.uuid4().hex[:6]}@povu-demo.test",
             full_name=tag.title(), hashed_password="x", is_active=True)
    db.add(u)
    await db.flush()
    plist = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in perms]
    return SimpleNamespace(id=u.id, username=u.username, email=u.email, full_name=u.full_name, is_superuser=False,
                           access_scopes=[], roles=[SimpleNamespace(name="r", is_active=True, permissions=plist, access_scopes=[])])


async def _published(db, graph: dict, editor, approver):
    from app.api.v1.endpoints import crm_workflows as api
    wf = await api.create_workflow(api.WorkflowIn(name=f"POVU flow {uuid.uuid4().hex[:8]}"), db, editor)
    wid = uuid.UUID(wf["id"])
    v = await api.save_draft(wid, api.GraphIn(graph=graph), db, editor)
    assert v["problems"] == []
    await api.publish(uuid.UUID(v["id"]), db, approver)
    return wid, uuid.UUID(v["id"])


async def _runs(db, version_id):
    from sqlalchemy import select
    from app.models.crm import CRMWorkflowRun
    return list((await db.execute(select(CRMWorkflowRun).where(CRMWorkflowRun.version_id == version_id))).scalars())


# ── DB ────────────────────────────────────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_scheduled_daily_weekly_and_relative_enrol_once_per_occurrence():
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMActivity, CRMRecord, CRMStatus, CRMWorkflow, CRMWorkflowVersion
    tag = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        editor, approver = await _staff(db, "ed", ("crm.edit_all",)), await _staff(db, "ap", ("crm.approve",))
        close = (datetime.now(NBO) + timedelta(days=10)).date()
        a = CRMRecord(company_name=f"Duka Moja {tag}", industry_segment=f"seg-{tag}", expected_close_date=close)
        b = CRMRecord(company_name=f"Duka Mbili {tag}", industry_segment=f"seg-{tag}")
        won = CRMRecord(company_name=f"Duka Won {tag}", industry_segment=f"seg-{tag}", status=CRMStatus.WON, expected_close_date=close)
        other = CRMRecord(company_name=f"Duka Other {tag}", industry_segment=f"other-{tag}", expected_close_date=close)
        db.add_all([a, b, won, other])
        await db.commit()
        match = {"field": "industry_segment", "operator": "eq", "value": f"seg-{tag}"}
        _, daily = await _published(db, _graph({"event": "scheduled", "schedule": {"kind": "daily", "time": "08:00", "match": match}}), editor, approver)
        _, weekly = await _published(db, _graph({"event": "scheduled", "schedule": {"kind": "weekly", "time": "08:00", "weekday": 0, "match": match}}), editor, approver)
        _, rel = await _published(db, _graph({"event": "scheduled", "schedule": {
            "kind": "relative", "time": "07:00", "property": "expected_close_date", "offset_days": -7, "match": match}}), editor, approver)
        a_id, b_id = a.id, b.id

        def at(d: date, hh: int) -> datetime:
            return datetime(d.year, d.month, d.day, hh, 30, tzinfo=NBO).astimezone(timezone.utc)
        day1 = (datetime.now(NBO) + timedelta(days=1)).date()
        await wfs.enqueue(db, at(day1, 9))
        assert {r.crm_record_id for r in await _runs(db, daily)} == {a_id, b_id}     # open + filter only (not WON, not other)
        await wfs.enqueue(db, at(day1, 10))
        await wfs.enqueue(db, at(day1, 23))
        assert len(await _runs(db, daily)) == 2                                         # same occurrence: once
        await wfs.enqueue(db, at(day1 + timedelta(days=1), 9))
        assert len(await _runs(db, daily)) == 4                                         # next day: next occurrence
        await wfs.enqueue(db, at(day1 + timedelta(days=1), 7))                         # before 08:00: still yesterday's
        assert len(await _runs(db, daily)) == 4

        monday = day1 + timedelta(days=14 - day1.weekday())                            # a Monday after every tick so far
        n_before = len(await _runs(db, weekly))
        await wfs.enqueue(db, at(monday, 9))
        await wfs.enqueue(db, at(monday + timedelta(days=2), 9))                       # Wednesday: same weekly occurrence
        assert len(await _runs(db, weekly)) == n_before + 2

        fire = close - timedelta(days=7)
        await wfs.enqueue(db, at(fire - timedelta(days=1), 9))
        assert await _runs(db, rel) == []                                               # 8 days before: not yet
        await wfs.enqueue(db, at(fire, 6))
        assert await _runs(db, rel) == []                                               # right day, before 07:00
        await wfs.enqueue(db, at(fire, 8))
        await wfs.enqueue(db, at(fire, 12))
        runs = await _runs(db, rel)
        assert [r.crm_record_id for r in runs] == [a_id]                                # only the record 7 days before close
        assert runs[0].event_key == f"rel:expected_close_date:{close.isoformat()}:{a_id}"
        await wfs.process(db, now=at(fire, 12) + timedelta(seconds=5))
        acts = (await db.execute(select(CRMActivity.subject).where(CRMActivity.crm_record_id == a_id))).scalars().all()
        assert "Call about POVU AllClean 1 L" in acts
        # the close date moves: a new occurrence for the new date, never a second run for the old one
        rec = await db.get(CRMRecord, a_id)
        rec.expected_close_date = close + timedelta(days=3)
        await db.commit()
        await wfs.enqueue(db, at(fire + timedelta(days=3), 8))
        assert len(await _runs(db, rel)) == 2
        for v in (daily, weekly, rel):   # leave no live schedule behind in the shared template-cloned DB
            ver = await db.get(CRMWorkflowVersion, v)
            ver.status = "ARCHIVED"
            (await db.get(CRMWorkflow, ver.workflow_id)).published_version_id = None
        await db.commit()


@DB
@pytest.mark.asyncio
async def test_inbound_webhook_token_auth_and_replay():
    from fastapi import FastAPI, HTTPException
    from sqlalchemy import select
    from app.api.v1.endpoints import crm_workflow_hooks_public as pub
    from app.api.v1.endpoints import crm_workflows as api
    from app.db.session import AsyncSessionLocal
    from app.models.audit_log import AuditLog
    from app.models.crm import CRMRecord
    from app.models.m47_automation import CRMWorkflowHook
    tag = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        editor, approver = await _staff(db, "ed", ("crm.edit_all",)), await _staff(db, "ap", ("crm.approve",))
        rec = CRMRecord(company_name=f"Duka Moja {tag}", contact_email=f"Buyer-{tag}@povu-demo.test")
        db.add(rec)
        await db.commit()
        rid = rec.id
        wid, ver = await _published(db, _graph({"event": "inbound_webhook"}), editor, approver)
        with pytest.raises(HTTPException):
            await api.PUBLISH(editor)                                                   # editors cannot mint tokens
        issued = await api.issue_webhook_token(wid, db, approver)
        token = issued["token"]
        hook = await db.get(CRMWorkflowHook, wid)
        assert hook.token_digest != token and token not in hook.token_digest and len(hook.token_digest) == 64
        assert (await api.get_workflow(wid, db, None))["webhook"]["token_hint"] == token[-4:]
        assert "token" not in (await api.get_workflow(wid, db, None))["webhook"]           # never shown again

    app = FastAPI()
    app.include_router(pub.router, prefix="/public/crm-workflow-hooks")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test") as c:
        url = f"/public/crm-workflow-hooks/{wid}"
        assert (await c.post(url, json={"event_id": "evt-1", "record_id": str(rid)})).status_code == 401
        assert (await c.post(url, json={"event_id": "evt-1", "record_id": str(rid)},
                             headers={"Authorization": "Bearer wfh_wrong"})).status_code == 401
        h = {"Authorization": f"Bearer {token}"}
        r = await c.post(url, json={"event_id": "evt-1", "record_id": str(rid)}, headers=h)
        assert r.status_code == 200 and r.json()["enrolled"] is True
        r2 = await c.post(url, json={"event_id": "evt-1", "record_id": str(rid)}, headers=h)
        assert r2.status_code == 200 and r2.json() == {"enrolled": False, "duplicate": True, "run_id": r.json()["run_id"]}
        r3 = await c.post(url, json={"event_id": "evt-2", "email": f"buyer-{tag}@POVU-demo.test"}, headers=h)
        assert r3.status_code == 200 and r3.json()["enrolled"] is True                    # by e-mail, case-insensitive
        assert (await c.post(url, json={"event_id": "evt-3", "email": "nobody@povu-demo.test"}, headers=h)).status_code == 404
        assert (await c.post(url, json={"event_id": "bad id!", "record_id": str(rid)}, headers=h)).status_code == 422
        assert (await c.post(url, json={"event_id": "evt-4", "record_id": str(rid), "email": "x@povu-demo.test"}, headers=h)).status_code == 422
        async with AsyncSessionLocal() as db:
            runs = await _runs(db, ver)
            assert sorted(r.event_key for r in runs) == ["hook:evt-1", "hook:evt-2"] and {r.crm_record_id for r in runs} == {rid}
            new = (await api.issue_webhook_token(wid, db, approver))["token"]            # rotate
        assert (await c.post(url, json={"event_id": "evt-5", "record_id": str(rid)}, headers=h)).status_code == 401
        assert (await c.post(url, json={"event_id": "evt-5", "record_id": str(rid)},
                             headers={"Authorization": f"Bearer {new}"})).status_code == 200
        async with AsyncSessionLocal() as db:
            await api.revoke_webhook_token(wid, db, approver)
            events = set((await db.execute(select(AuditLog.event_type).where(AuditLog.target_id == str(wid)))).scalars())
            assert {"crm_workflow.hook_created", "crm_workflow.hook_rotated", "crm_workflow.hook_revoked"} <= events
        assert (await c.post(url, json={"event_id": "evt-6", "record_id": str(rid)},
                             headers={"Authorization": f"Bearer {new}"})).status_code == 401
        pub._hits.clear()
        for i in range(60):
            await c.post(url, json={"event_id": f"r{i}", "record_id": str(rid)})
        assert (await c.post(url, json={"event_id": "r61", "record_id": str(rid)})).status_code == 429   # rate-limited
        pub._hits.clear()


@DB
@pytest.mark.asyncio
async def test_event_definitions_collector_and_web_event_trigger():
    from fastapi import HTTPException
    from sqlalchemy import select
    from app.api.v1.endpoints import crm_workflows as api
    from app.api.v1.endpoints import web_analytics as wep
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMRecord, WebEvent
    from app.models.m47_automation import WebEventProperty
    tag = uuid.uuid4().hex[:8]
    ev_name = f"demo_requested_{tag}"
    async with AsyncSessionLocal() as db:
        editor, approver = await _staff(db, "ed", ("crm.edit_all",)), await _staff(db, "ap", ("crm.approve",))
        viewer = await _staff(db, "mv", ("marketing.view",))
        with pytest.raises(HTTPException) as e:
            await wep.create_definition(wep.DefinitionIn(name=ev_name, properties={"product": "string"}), db, viewer)
        assert e.value.status_code == 403
        d = await wep.create_definition(wep.DefinitionIn(name=ev_name, description="Demo form on the POVU site",
                                                         properties={"product": "string", "cartons": "number"}), db, editor)
        assert d["properties"] == {"product": "string", "cartons": "number"}
        with pytest.raises(HTTPException) as e:
            await wep.create_definition(wep.DefinitionIn(name=ev_name), db, editor)
        assert e.value.status_code == 409
        assert any(x["name"] == ev_name for x in await wep.list_definitions(db))

        # unknown definition cannot go live
        from app.api.v1.endpoints.crm_workflows import GraphIn, WorkflowIn
        wf = await api.create_workflow(WorkflowIn(name=f"POVU web {tag}"), db, editor)
        bad = await api.save_draft(uuid.UUID(wf["id"]), GraphIn(graph=_graph({"event": "web_event", "name": f"nope_{tag}"})), db, editor)
        with pytest.raises(HTTPException) as e:
            await api.publish(uuid.UUID(bad["id"]), db, approver)
        assert e.value.status_code == 422
        _, ver = await _published(db, _graph({"event": "web_event", "name": ev_name}), editor, approver)

        email = f"buyer-{tag}@povu-demo.test"
        rec = CRMRecord(company_name=f"Duka Moja {tag}", contact_email=email)
        db.add(rec)
        await db.commit()
        rid = rec.id
        v, s = uuid.uuid4().hex, uuid.uuid4().hex
        ev = {"event_id": uuid.uuid4().hex, "kind": "CUSTOM", "name": ev_name, "path": "/demo",
              "properties": {"product": "POVU AllClean 1 L", "cartons": 4, "phone": "0700000000", "cartons_x": "a"}}
        assert (await wa.collect(db, v, s, [ev]))["stored"] == 0                          # no analytics consent: nothing
        await wa.record_consent(db, v, analytics=True, marketing=False)
        await db.flush()
        out = await wa.collect(db, v, s, [ev, {"event_id": uuid.uuid4().hex, "kind": "CUSTOM", "name": f"undefined_{tag}",
                                               "path": "/x", "properties": {"product": "POVU WhiteCare 1 kg"}}])
        assert out["stored"] == 2 and out["dropped_properties"] == 3
        await db.commit()
        rows = (await db.execute(select(WebEvent.name, WebEventProperty.properties).outerjoin(
            WebEventProperty, WebEventProperty.event_id == WebEvent.id).where(WebEvent.visitor_hash == wa.hashed("v", v)))).all()
        assert dict(rows) == {ev_name: {"product": "POVU AllClean 1 L", "cartons": 4}, f"undefined_{tag}": None}

        t0 = datetime.now(timezone.utc) + timedelta(seconds=5)
        await wfs.enqueue(db, t0)
        assert await _runs(db, ver) == []                       # anonymous visitor (no marketing consent): no enrolment
        assert not await wa.identify(db, v, email)
        await wa.record_consent(db, v, analytics=True, marketing=True)
        await db.flush()
        assert await wa.identify(db, v, email)
        ev2 = {**ev, "event_id": uuid.uuid4().hex}
        await wa.collect(db, v, s, [ev2])
        await db.commit()
        await wfs.enqueue(db, t0 + timedelta(seconds=3))
        assert await _runs(db, ver) == []                       # M47 review: a typed, unverified e-mail never enrols
        assert await wa.identify(db, v, email, verified=True)   # e.g. the signed-in portal user's own address
        await db.commit()
        await wfs.enqueue(db, t0 + timedelta(seconds=5))
        await wfs.enqueue(db, t0 + timedelta(seconds=10))
        runs = await _runs(db, ver)
        assert {r.crm_record_id for r in runs} == {rid} and len(runs) == 2      # identified now: both events, once each
        await wa.forget(db, v)
        await db.commit()
        assert (await db.execute(select(WebEventProperty).join(WebEvent, WebEvent.id == WebEventProperty.event_id)
                                 .where(WebEvent.visitor_hash == wa.hashed("v", v)))).first() is None


@DB
@pytest.mark.asyncio
async def test_web_behaviour_audiences():
    from app.db.session import AsyncSessionLocal
    from app.models.crm import MarketingAudience
    from app.models.sales import Customer, CustomerChannel
    from app.services import crm_outbound_service as outbound
    tag = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        cons = Customer(code=f"WA-Y-{tag}", name="POVU Outlet Web", email=f"web-{tag}@povu-demo.test",
                        channel=CustomerChannel.RETAIL, segment=f"web-{tag}")
        nocons = Customer(code=f"WA-N-{tag}", name="POVU Outlet No Mail", email=f"nomail-{tag}@povu-demo.test",
                          channel=CustomerChannel.RETAIL, segment=f"web-{tag}")
        quiet = Customer(code=f"WA-Q-{tag}", name="POVU Outlet Quiet", email=f"quiet-{tag}@povu-demo.test",
                         channel=CustomerChannel.RETAIL, segment=f"web-{tag}")
        db.add_all([cons, nocons, quiet])
        await db.flush()
        for c in (cons, quiet):
            await outbound.record_consent(db, c.email, "SUBSCRIBED", "test")
        for c in (cons, nocons):
            v = uuid.uuid4().hex
            await wa.record_consent(db, v, analytics=True, marketing=True)
            await db.flush()
            assert await wa.identify(db, v, c.email)
            await wa.collect(db, v, uuid.uuid4().hex, [
                {"event_id": uuid.uuid4().hex, "kind": "PAGE", "path": "/pricing/povu-allclean"},
                {"event_id": uuid.uuid4().hex, "kind": "CUSTOM", "name": f"demo_{tag}", "path": "/demo"}])
        await db.flush()
        seg = {"field": "segment", "op": "eq", "value": f"web-{tag}"}
        for cond in ({"field": "visited_path", "op": "prefix", "value": "/pricing", "days": 30},
                     {"field": "web_event", "op": "occurred", "value": f"demo_{tag}", "days": 14},
                     {"field": "intent_score", "op": "gte", "value": 2.5}):
            a = MarketingAudience(name=f"web-{cond['field']}-{tag}", rules=aus.validate({"all": [seg, cond]}))
            db.add(a)
            await db.flush()
            await aus.recompute(db, a)
            assert (a.member_count, a.blocked_count) == (1, 1), cond   # consented member; matched-but-unconsented blocked
        a = MarketingAudience(name=f"web-none-{tag}", rules=aus.validate({"all": [seg, {"field": "visited_path", "op": "prefix", "value": "/careers"}]}))
        db.add(a)
        await db.flush()
        await aus.recompute(db, a)
        assert (a.member_count, a.blocked_count) == (0, 0)
        ex = MarketingAudience(name=f"web-ex-{tag}", rules=aus.validate({"all": [seg], "exclude": [{"field": "web_event", "op": "occurred", "value": f"demo_{tag}"}]}))
        db.add(ex)
        await db.flush()
        await aus.recompute(db, ex)
        assert ex.member_count == 1                                                    # only the quiet, consented outlet
        await db.rollback()


@DB
@pytest.mark.asyncio
async def test_portal_usage_in_health_and_churn():
    from app.db.session import AsyncSessionLocal
    from app.models.portal import PortalAccount, PortalActivityLog, PortalActivityType, PortalUser
    from app.models.sales import Customer, SalesOrder, SOStatus
    tag = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        today = date.today()
        user_c = Customer(code=f"US-{tag}", name="POVU Shop User", currency="KES", email=f"shop-{tag}@povu-demo.test")
        plain = Customer(code=f"PL-{tag}", name="POVU Offline Outlet", currency="KES")
        db.add_all([user_c, plain])
        await db.flush()
        for c in (user_c, plain):
            for k in range(4):
                d = today - timedelta(days=10 + 14 * k)
                db.add(SalesOrder(order_no=f"SO-{tag}-{c.code}-{k}", customer_id=c.id, order_date=d, requested_delivery_date=d,
                                  status=SOStatus.INVOICED, currency="KES"))
        acc = PortalAccount(account_code=f"PA-{tag}", linked_customer_id=str(user_c.id), primary_contact_email=user_c.email)
        db.add(acc)
        await db.flush()
        pu = PortalUser(portal_account_id=acc.id, full_name="Duka Moja Buyer", email=f"pu-{tag}@povu-demo.test")
        db.add(pu)
        await db.flush()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for days, kind, ref in ((2, PortalActivityType.LOGIN, None), (40, PortalActivityType.LOGIN, None),
                                (3, PortalActivityType.OTHER, "catalog_view"), (200, PortalActivityType.LOGIN, None)):
            db.add(PortalActivityLog(portal_user_id=pu.id, portal_account_id=acc.id, activity_type=kind, reference_type=ref,
                                     activity_datetime=now - timedelta(days=days)))
        db.add(SalesOrder(order_no=f"WEB-{tag}", customer_id=user_c.id, order_date=today, requested_delivery_date=today,
                          status=SOStatus.DRAFT, currency="KES", offline_id=f"portal:{acc.id}:{tag}"))
        await db.flush()
        as_of = today + timedelta(days=1)                       # everything strictly before the cut-off counts
        h = await ci.health(db, [user_c.id, plain.id], as_of)
        u = h[user_c.id]["usage"]
        assert (u["logins_30d"], u["logins_90d"], u["catalog_views_30d"], u["self_service_orders_90d"]) == (1, 2, 1, 1)
        assert h[user_c.id]["components"]["usage"] == 80.0 and "usage" not in h[user_c.id]["missing"]
        assert "usage" not in h[plain.id]["components"] and "usage" in h[plain.id]["missing"]
        assert h[plain.id]["usage"]["note"].startswith("no portal")
        assert h[user_c.id]["score"] is not None and h[plain.id]["score"] is not None
        early = await ci.health(db, [user_c.id], today - timedelta(days=5))       # cut-off before the activity: no leakage
        assert early[user_c.id]["usage"]["logins_30d"] == 0 and early[user_c.id]["usage"]["catalog_views_30d"] == 0
        fs = await ci.features(db, [user_c.id], as_of)
        named = dict(zip(ci.FEATURES, fs[user_c.id].vector(as_of)))
        assert named["log_usage_90d"] > 0
        # an older 9-feature churn model keeps working
        from app.models.customer_intel import CIModel
        old = CIModel(kind="CHURN", status="ACTIVE", params={"mean": [0.0] * 9, "std": [1.0] * 9, "coef": [0.1] * 9,
                                                              "intercept": 0.0, "features": ci.FEATURES[:9]},
                      metrics={}, trained_by="test")
        db.add(old)
        await db.flush()
        res = await ci.churn(db, [user_c.id], as_of)
        assert res[user_c.id]["method"] == "model" and 0 <= res[user_c.id]["probability"] <= 1
        await db.rollback()
