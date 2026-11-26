"""M49.S01.T004 contact center: queues, presence, IVR, consent, callbacks, transfer, Twilio signature - local simulator.

Needs the disposable PostgreSQL (M49_DB=1). The Twilio webhook is exercised through a mini app that mounts the same router
(the public-route allow-list entry lives in module_registry, a shared file). No real carrier is ever called.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import os
import uuid
from datetime import datetime
from types import SimpleNamespace
from urllib.parse import urlencode

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.core import provider_http
from app.core.config import settings
from tests.provider_sim import voice2_app as v2

pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(os.environ.get("M49_DB") != "1", reason="requires the disposable PostgreSQL")]
SIM = "http://127.0.0.1:8767"
WH = "/api/v1/calls/cc/twilio/webhook"


@pytest.fixture(autouse=True)
async def _engine():
    from app.db.base import Base
    from app.db.session import engine
    import app.models.m49_voice as m
    tables = [t.__table__ for t in (m.VoiceQueue, m.VoiceQueueEntry, m.VoicePresence, m.VoiceCallback, m.VoiceTransfer,
                                    m.VoiceCallDisposition, m.VoiceVoicemail, m.VoiceProviderEvent, m.TranscriptJob, m.TranscriptEdit)]
    async with engine.begin() as c:
        await c.run_sync(lambda s: Base.metadata.create_all(s, tables=tables, checkfirst=True))
    yield
    await engine.dispose()


@pytest.fixture
def sim(monkeypatch):
    app = v2.create_app()
    for k, v in v2.sim_settings(SIM).items():
        monkeypatch.setitem(settings.__dict__, k, v)   # new settings are read with getattr(...), not declared fields
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "local")
    monkeypatch.setattr("app.services.voice_carrier._BACKOFF", 0)
    provider_http.set_test_transport(httpx.ASGITransport(app=app))
    yield app
    provider_http.set_test_transport(None)


@pytest.fixture
async def wh():
    from app.api.v1.endpoints import voice_cc
    mini = FastAPI()
    mini.include_router(voice_cc.router, prefix="/api/v1/calls/cc")
    async with AsyncClient(transport=ASGITransport(app=mini), base_url="http://test") as c:
        async def post(step, form, token=v2.AUTH_TOKEN, sign=True, **q):
            path = f"{WH}?" + urlencode({"step": step, **q})
            headers = {}
            if sign:
                data = "https://erp.povu-demo.test" + path + "".join(k + form[k] for k in sorted(form))
                headers["X-Twilio-Signature"] = base64.b64encode(hmac.new(token.encode(), data.encode(), hashlib.sha1).digest()).decode()
            return await c.post(path, data=form, headers=headers)
        yield post


@pytest.fixture
async def db():
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as s:
        yield s


def _num() -> str:
    return f"+2547{uuid.uuid4().int % 10**8:08d}"


async def _agent(db, perms=(), phone=None, status="AVAILABLE", mgr=False):
    from app.models.user import User
    from app.models.voip import VoiceAgentProfile
    from app.services import contact_center_service as cc
    u = User(id=uuid.uuid4(), email=f"a-{uuid.uuid4().hex[:6]}@povu-demo.test", username=f"syn-{uuid.uuid4().hex[:12]}",
             hashed_password="x", full_name="Synthetic Agent", is_active=True)
    db.add(u)
    await db.flush()
    phone = _num() if phone is None else phone
    db.add(VoiceAgentProfile(user_id=u.id, phone_number=phone, available=False))
    await db.flush()
    await cc.set_presence(db, u.id, status)
    plist = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in perms]
    ns = SimpleNamespace(id=u.id, username=u.username, email=u.email, full_name=u.full_name, is_superuser=mgr, access_scopes=[],
                         roles=[SimpleNamespace(name="r", is_active=True, permissions=plist, access_scopes=[])])
    ns.phone = phone
    return ns


async def _queue(db, members, **kw):
    from app.models.m49_voice import VoiceQueue
    q = VoiceQueue(name=f"POVU line {uuid.uuid4().hex[:8]}", member_user_ids=[str(m.id) for m in members], **kw)
    db.add(q)
    await db.flush()
    return q


async def _menu(db, queue, record=False):
    from app.models.voip import VoiceIvrMenu
    number = _num()
    db.add(VoiceIvrMenu(name="POVU synthetic line", phone_number=number, greeting_text="Welcome to POVU.", record_calls=record,
                        consent_text="This call may be recorded for quality." if record else None,
                        options=[{"digit": "1", "label": "Sales", "user_ids": [], "phone_numbers": [], "queue_id": str(queue.id)}]))
    await db.commit()
    return number


async def _inbound(wh, number, caller=None, record=False, digit="1"):
    sid, caller = "CA" + uuid.uuid4().hex, caller or _num()
    base = {"CallSid": sid, "Direction": "inbound", "From": caller, "To": number}
    r = await wh("voice", base)
    assert r.status_code == 200
    if record:
        assert "Press 1 to agree to recording" in r.text and "<Gather" in r.text
        r = await wh("consent", {**base, "Digits": "1" if record == "yes" else "2"}, ref=_ref(r))
    return sid, caller, base, r


def _ref(r) -> str:
    import re
    return re.search(r"ref=(CALL-[0-9A-F]+)", r.text).group(1)


# ── signature ────────────────────────────────────────────────────────────────

async def test_bad_or_missing_signature_is_403_and_nothing_changes(sim, wh, db):
    from app.models.voip import CallLog
    form = {"CallSid": "CA" + uuid.uuid4().hex, "Direction": "inbound", "From": _num(), "To": _num()}
    assert (await wh("voice", form, token="wrong-token")).status_code == 403
    assert (await wh("voice", form, sign=False)).status_code == 403
    assert (await wh("voice", form)).status_code == 200
    assert (await db.execute(select(func.count()).select_from(CallLog).where(CallLog.provider_session_id == form["CallSid"]))).scalar() == 1


async def test_unanswered_inbound_stays_no_answer_after_completed_status(sim, wh, db):
    from app.models.m49_voice import VoiceCallback
    from app.models.voip import CallLog
    sid, caller, base, r = await _inbound(wh, _num())                    # no IVR menu on this number
    await db.rollback()
    call = (await db.execute(select(CallLog).where(CallLog.provider_session_id == sid))).scalar_one()
    assert call.outcome == "NO_ANSWER" and call.follow_up_required
    assert (await db.execute(select(VoiceCallback).where(VoiceCallback.phone_number == caller))).scalars().first() is not None
    assert (await wh("status", {**base, "CallStatus": "completed"})).status_code == 200
    await db.rollback()
    await db.refresh(call)
    assert call.outcome == "NO_ANSWER" and call.follow_up_required and call.status == "COMPLETED"


async def test_no_configured_token_fails_closed(sim, wh, monkeypatch):
    monkeypatch.setitem(settings.__dict__, "VOICE_TWILIO_AUTH_TOKEN", "")
    assert (await wh("voice", {"CallSid": "CA1", "Direction": "inbound"}, token="")).status_code == 403


# ── routing and presence ─────────────────────────────────────────────────────

async def test_longest_idle_routing_busy_hold_and_release(sim, wh, db):
    a1, a2 = await _agent(db), await _agent(db)
    q = await _queue(db, [a1, a2], max_wait_seconds=600)
    qid = str(q.id)
    number = await _menu(db, q)
    out = []
    for _ in range(3):
        sid, _c, base, r = await _inbound(wh, number)
        r = await wh("menu", {**base, "Digits": "1"}, ref=_ref(r))
        out.append((sid, base, r))
    assert f"<Number>{a1.phone}</Number>" in out[0][2].text            # a1 became idle first
    assert f"<Number>{a2.phone}</Number>" in out[1][2].text
    assert "<Pause" in out[2][2].text and "queue_poll" in out[2][2].text   # nobody free: hold
    from app.models.m49_voice import VoicePresence
    assert (await db.get(VoicePresence, a1.id)).status == "BUSY"
    # first call ends -> a1 free; the held caller's poll gets a1; a replayed status event changes nothing
    sid1, base1, r1 = out[0]
    ref1 = _ref(r1)
    st = {**base1, "CallStatus": "completed", "CallDuration": "42", "SequenceNumber": "3"}
    assert (await wh("status", st, ref=ref1)).status_code == 200
    assert (await wh("status", st, ref=ref1)).status_code == 200
    await db.rollback()
    assert (await db.get(VoicePresence, a1.id, populate_existing=True)).status == "AVAILABLE"
    r = await wh("queue_poll", out[2][1], ref=_ref(out[2][2]), queue=qid)
    assert f"<Number>{a1.phone}</Number>" in r.text


async def test_presence_rules_and_board(sim, db):
    from app.api.v1.endpoints import voice_cc as api
    mgr = await _agent(db, perms=("crm.view_all", "crm.edit_all"), status="OFFLINE")
    nophone = await _agent(db, phone="", status="OFFLINE")
    with pytest.raises(HTTPException) as e:
        await api.my_presence(api.PresenceIn(status="AVAILABLE"), db, nophone)
    assert e.value.status_code == 409
    assert (await api.my_presence(api.PresenceIn(status="AVAILABLE"), db, mgr))["status"] == "AVAILABLE"
    b = await api.board(db, mgr)
    assert any(a["user_id"] == str(mgr.id) and a["status"] == "AVAILABLE" for a in b["agents"])
    plain = await _agent(db, status="AVAILABLE")
    assert [a["user_id"] for a in (await api.board(db, plain))["agents"]] == [str(plain.id)]   # no view-all: only self
    with pytest.raises(HTTPException) as e:
        await api.create_queue(api.QueueIn(name=f"x-{uuid.uuid4().hex[:6]}"), db, plain)
    assert e.value.status_code == 403


# ── consent ──────────────────────────────────────────────────────────────────

async def test_recording_consent_accept_and_refusal(sim, wh, db):
    from app.models.voip import CallLog
    agent = await _agent(db)
    q = await _queue(db, [agent])
    number = await _menu(db, q, record=True)
    for choice, expect in (("yes", True), ("no", False)):
        await db.rollback()
        sid, _c, base, r = await _inbound(wh, number, record=choice)
        ref = _ref(r)
        r = await wh("menu", {**base, "Digits": "1"}, ref=ref)
        assert ('record="record-from-answer-dual"' in r.text) is expect
        assert ('record="do-not-record"' in r.text) is (not expect)
        await wh("recording", {**base, "RecordingSid": "RE" + uuid.uuid4().hex, "RecordingStatus": "completed",
                               "RecordingUrl": f"{SIM.replace('http', 'https')}/recordings/x-en.wav"}, ref=ref)
        call = (await db.execute(select(CallLog).where(CallLog.provider_session_id == sid))).scalar_one()
        await db.refresh(call)
        assert call.recording_consent is expect
        assert bool(call.recording_url) is expect and bool(call.recording_expires_at) is expect
        if not expect:
            assert call.consent_note.startswith("declined")
        from app.services import contact_center_service as cc
        await cc.release_agent(db, call)
        await db.commit()


# ── callbacks ────────────────────────────────────────────────────────────────

async def test_missed_call_callback_is_idempotent(sim, wh, db):
    from app.api.v1.endpoints import voice_cc as api
    from app.models.m49_voice import VoiceCallback
    q = await _queue(db, [], max_wait_seconds=0, overflow="CALLBACK")
    number = await _menu(db, q)
    caller = _num()
    for _ in range(2):                                                      # two separate missed calls, same number
        sid, _c, base, r = await _inbound(wh, number, caller=caller)
        ref = _ref(r)
        r = await wh("menu", {**base, "Digits": "1"}, ref=ref)
        assert "call you back" in r.text
        await wh("menu", {**base, "Digits": "1"}, ref=ref)                  # replayed menu step: no extra count
    await db.rollback()
    rows = (await db.execute(select(VoiceCallback).where(VoiceCallback.phone_number == caller))).scalars().all()
    assert len(rows) == 1 and rows[0].state == "PENDING" and rows[0].missed_count == 2
    # staff duplicate request and concurrent requests: still one open callback
    mgr = await _agent(db, perms=("crm.edit_all",))
    again = await api.add_callback(api.CallbackIn(phone_number=caller), SimpleNamespace(status_code=201), db, mgr)
    assert again["duplicate"] is True and again["id"] == str(rows[0].id)
    fresh = _num()
    from app.db.session import AsyncSessionLocal
    from app.services import contact_center_service as cc

    async def one():
        async with AsyncSessionLocal() as s:
            cb, created = await cc.request_callback(s, fresh, None, None)
            await s.commit()
            return created
    created = await asyncio.gather(*(one() for _ in range(4)))
    assert sorted(created) == [False, False, False, True]
    await db.rollback()
    assert (await db.execute(select(func.count()).select_from(VoiceCallback).where(VoiceCallback.phone_number == fresh))).scalar() == 1


async def test_callback_completion_attempts(sim, db):
    from app.api.v1.endpoints import voice_cc as api
    from app.services import contact_center_service as cc
    agent = await _agent(db, perms=("crm.edit_all",))      # F5: completing a callback needs manager rights or queue membership
    cb, _ = await cc.request_callback(db, _num(), None, None)
    await db.commit()
    for _ in range(2):
        r = await api.finish_callback(cb.id, api.CallbackDone(outcome="NO_ANSWER"), db, agent)
        assert r["state"] == "PENDING"
    assert (await api.finish_callback(cb.id, api.CallbackDone(outcome="NO_ANSWER"), db, agent))["state"] == "EXPIRED"
    with pytest.raises(HTTPException):
        await api.finish_callback(cb.id, api.CallbackDone(outcome="ANSWERED"), db, agent)


async def test_voicemail_overflow_stored_once(sim, wh, db):
    from app.models.m49_voice import VoiceVoicemail
    q = await _queue(db, [], max_wait_seconds=0, overflow="VOICEMAIL")
    number = await _menu(db, q)
    sid, _c, base, r = await _inbound(wh, number)
    ref = _ref(r)
    r = await wh("menu", {**base, "Digits": "1"}, ref=ref)
    assert "<Record" in r.text
    rec = {**base, "RecordingSid": "RE" + uuid.uuid4().hex, "RecordingStatus": "completed", "RecordingDuration": "17",
           "RecordingUrl": f"{SIM.replace('http', 'https')}/recordings/vm-en.wav"}
    for _ in range(2):
        await wh("recording", rec, ref=ref, queue=str(q.id))
    await db.rollback()
    rows = (await db.execute(select(VoiceVoicemail).where(VoiceVoicemail.provider_recording_id == rec["RecordingSid"]))).scalars().all()
    assert len(rows) == 1 and rows[0].duration_seconds == 17 and rows[0].expires_at > datetime.now(rows[0].expires_at.tzinfo)


# ── transfer ─────────────────────────────────────────────────────────────────

async def _live_call(db, sim, agent, direction="INBOUND"):
    from app.models.voip import CallLog
    sid = "CA" + uuid.uuid4().hex
    sim.state.sim["calls"][sid] = {"sid": sid, "status": "in-progress", "form": {}}
    call = CallLog(call_ref=f"CALL-{uuid.uuid4().hex[:10].upper()}", direction=direction, phone_number=_num(), agent_id=agent.id,
                   provider="twilio", provider_session_id=sid, status="ANSWERED", started_at=datetime.utcnow())
    db.add(call)
    await db.commit()
    return call


async def test_cold_and_warm_transfer(sim, wh, db):
    from app.api.v1.endpoints import voice_cc as api
    me, target = await _agent(db, status="BUSY"), await _agent(db)
    call = await _live_call(db, sim, me)
    t = await api.transfer(call.id, api.TransferIn(kind="COLD", to_user_id=target.id), db, me)
    assert t["state"] == "COMPLETED"
    up = sim.state.sim["updates"][-1]
    assert up["sid"] == call.provider_session_id and f"<Number>{target.phone}</Number>" in up["Twiml"]
    # warm: the target must accept the announcement before the customer is moved
    call2 = await _live_call(db, sim, me)
    t = await api.transfer(call2.id, api.TransferIn(kind="WARM", to_user_id=target.id), db, me)
    assert t["state"] == "CONSULTING" and sim.state.sim["created"][-1]["form"]["To"] == [target.phone]
    with pytest.raises(HTTPException) as e:                                   # not accepted yet
        await api.complete_transfer(uuid.UUID(t["id"]), db, me)
    assert e.value.status_code == 409
    ref = call2.call_ref
    await db.rollback()                                                       # a failed request releases its row lock
    before = len(sim.state.sim["updates"])
    r = await wh("consult_twiml", {"CallSid": "CA" + uuid.uuid4().hex}, ref=ref, transfer=t["id"])
    assert "Press 1 to accept" in r.text
    await wh("consult_accept", {"CallSid": "CA" + uuid.uuid4().hex, "Digits": "1"}, ref=ref, transfer=t["id"])
    done = await api.complete_transfer(uuid.UUID(t["id"]), db, me)
    assert done["state"] == "COMPLETED" and len(sim.state.sim["updates"]) == before + 1
    # a declined consult never moves the customer
    call3 = await _live_call(db, sim, me)
    t3 = await api.transfer(call3.id, api.TransferIn(kind="WARM", to_number=_num()), db, me)
    await wh("consult_accept", {"CallSid": "CA" + uuid.uuid4().hex, "Digits": "2"}, ref=call3.call_ref, transfer=t3["id"])
    with pytest.raises(HTTPException):
        await api.complete_transfer(uuid.UUID(t3["id"]), db, me)
    await db.rollback()


async def test_transfer_refused_when_unsupported_or_target_unavailable(sim, db, monkeypatch):
    from app.api.v1.endpoints import voice_cc as api
    me, away = await _agent(db, status="BUSY"), await _agent(db, status="AWAY")
    call = await _live_call(db, sim, me)
    with pytest.raises(HTTPException) as e:
        await api.transfer(call.id, api.TransferIn(kind="COLD", to_user_id=away.id), db, me)
    assert e.value.status_code == 409 and "not available" in e.value.detail
    out = await _live_call(db, sim, me, direction="OUTBOUND")
    with pytest.raises(HTTPException) as e:
        await api.transfer(out.id, api.TransferIn(kind="COLD", to_number=_num()), db, me)
    assert "inbound" in e.value.detail.lower()
    monkeypatch.setattr(settings, "VOICE_PROVIDER", "africastalking")
    for k, v in {"VOICE_AT_USERNAME": "sandbox", "VOICE_AT_API_KEY": "k", "VOICE_AT_PHONE_NUMBER": "+254700000000"}.items():
        monkeypatch.setattr(settings, k, v)
    with pytest.raises(HTTPException) as e:
        await api.transfer(call.id, api.TransferIn(kind="WARM", to_number=_num()), db, me)
    assert "mid-call control" in e.value.detail


async def test_capability_matrix_marks_unsupported_with_reason(sim, monkeypatch):
    from app.services import voice_service as voice
    caps = voice.capabilities()["matrix"]
    assert caps["cold_transfer"]["state"] == "SUPPORTED" and caps["signature_verification"]["state"] == "SUPPORTED"
    monkeypatch.setattr(settings, "VOICE_PROVIDER", "")
    none = voice.capabilities()["matrix"]
    assert all(v["state"] == "UNSUPPORTED" and v["reason"] for v in none.values())
    monkeypatch.setattr(settings, "VOICE_PROVIDER", "africastalking")
    for k, v in {"VOICE_AT_USERNAME": "sandbox", "VOICE_AT_API_KEY": "k", "VOICE_AT_PHONE_NUMBER": "+254700000000"}.items():
        monkeypatch.setattr(settings, k, v)
    at = voice.capabilities()["matrix"]
    assert at["cold_transfer"]["state"] == "UNSUPPORTED" and at["queue_hold"]["state"] == "UNVERIFIED" and at["queue_hold"]["reason"]


# ── carrier faults, unknown outcome, reconciliation ──────────────────────────

async def test_place_call_retries_then_fails_clean_and_unknown_is_reconciled(sim, db, monkeypatch):
    from app.models.voip import CallLog
    from app.services import voice_service as voice
    ctl = lambda body: sim.state.sim["faults"]["twilio"].extend(body)  # noqa: E731

    def mk():
        c = CallLog(call_ref=f"CALL-{uuid.uuid4().hex[:10].upper()}", direction="OUTBOUND", phone_number=_num(), outcome="DIALED",
                    started_at=datetime.utcnow(), status="QUEUED")
        db.add(c)
        return c
    ok = mk()
    await db.flush()
    ctl([429, 500])                                                         # two transient faults then success
    await voice.place_call(db, ok, "+254711111111")
    assert ok.status == "QUEUED" and ok.provider == "twilio" and ok.provider_session_id.startswith("CA")
    form = sim.state.sim["created"][-1]["form"]
    assert form["To"] == ["+254711111111"] and form["StatusCallbackEvent"] == ["initiated", "ringing", "answered", "completed"]
    assert form["Url"][0].startswith("https://erp.povu-demo.test/api/v1/calls/cc/twilio/webhook?step=voice")
    bad = mk()
    await db.flush()
    ctl([500, 500, 500])
    with pytest.raises(voice.VoiceError):
        await voice.place_call(db, bad, "+254711111111")
    assert bad.status == "FAILED" and bad.provider_session_id is None
    bad_number = mk()
    await db.flush()
    with pytest.raises(voice.VoiceError):
        await voice.place_call(db, bad_number, "123")                       # 21211 is never retried
    assert len(sim.state.sim["created"]) == 1
    # lost answer: outcome unknown -> not re-sent; later verification applies the carrier's real state
    from app.services import contact_center_service as cc
    monkeypatch.setattr("httpx.AsyncClient.request", _timeout_once(httpx.AsyncClient.request))
    unk = mk()
    await db.flush()
    with pytest.raises(voice.VoiceError):
        await voice.place_call(db, unk, "+254722222222")
    assert unk.status == "UNKNOWN" and unk.provider_session_id is None
    live = await _live_call(db, sim, await _agent(db, status="BUSY"))
    sim.state.sim["calls"][live.provider_session_id]["status"] = "completed"
    await cc.verify_status(db, live)
    assert live.status == "COMPLETED" and live.outcome == "ANSWERED"


def _timeout_once(orig):
    state = {"n": 0}

    async def req(self, method, url, **kw):
        if method == "POST" and "/Calls.json" in str(url) and state["n"] == 0:
            state["n"] += 1
            raise httpx.ReadTimeout("simulated")
        return await orig(self, method, url, **kw)
    return req


# ── outbound queue, disposition, Africa's Talking queue routing ──────────────

async def test_outbound_queue_disposition_and_at_queue_routing(sim, db, monkeypatch):
    from app.api.v1.endpoints import voice_cc as api
    from app.models.m49_voice import VoiceCallback
    mgr = await _agent(db, perms=("crm.edit_all",), mgr=True)
    rep = await _agent(db)
    monkeypatch.setattr(settings, "VOICE_PROVIDER", "")                       # no carrier: tel: fallback
    q = await _queue(db, [rep], direction="OUTBOUND")
    await db.commit()
    nums = [_num(), _num()]
    assert (await api.add_outbound(q.id, api.OutboundItems(phone_numbers=nums + nums[:1]), db, mgr))["added"] == 2
    first = await api.next_outbound(q.id, db, rep)
    second = await api.next_outbound(q.id, db, rep)
    assert first["call"]["dial"] == "tel:" + nums[0] and second["call"]["dial"] == "tel:" + nums[1]
    assert (await api.next_outbound(q.id, db, rep))["call"] is None
    from app.models.voip import CallLog
    call = (await db.execute(select(CallLog).where(CallLog.id == uuid.UUID(first["call"]["id"])))).scalar_one()
    d = await api.set_disposition(call.id, api.DispositionIn(code="CALLBACK_REQUESTED", note="asked for Friday"), db, rep)
    assert d["code"] == "CALLBACK_REQUESTED"
    await db.rollback()
    assert (await db.execute(select(VoiceCallback).where(VoiceCallback.phone_number == nums[0]))).scalar_one().state == "PENDING"
    with pytest.raises(HTTPException) as e:                                   # another agent cannot touch it
        await api.set_disposition(call.id, api.DispositionIn(code="SALE"), db, await _agent(db))
    assert e.value.status_code == 404
    # Africa's Talking: IVR digit -> queue agent, no hold (UNVERIFIED), full queue -> callback
    for k, v in {"VOICE_PROVIDER": "africastalking", "VOICE_AT_USERNAME": "sandbox", "VOICE_AT_API_KEY": "k",
                 "VOICE_AT_PHONE_NUMBER": "+254700000000", "VOICE_CALLBACK_SECRET": "s3cret"}.items():
        monkeypatch.setattr(settings, k, v)
    aq = await _queue(db, [rep], max_wait_seconds=30)
    number = await _menu(db, aq)
    from app.services import voice_service as voice
    sid, caller = f"ATVId_{uuid.uuid4().hex[:8]}", _num()
    await voice.handle_callback(db, {"sessionId": sid, "isActive": "1", "direction": "Inbound", "callerNumber": caller, "destinationNumber": number})
    xml = await voice.handle_callback(db, {"sessionId": sid, "isActive": "1", "dtmfDigits": "1"})
    assert f'phoneNumbers="{rep.phone}"' in xml
    sid2, caller2 = f"ATVId_{uuid.uuid4().hex[:8]}", _num()
    await voice.handle_callback(db, {"sessionId": sid2, "isActive": "1", "direction": "Inbound", "callerNumber": caller2, "destinationNumber": number})
    xml = await voice.handle_callback(db, {"sessionId": sid2, "isActive": "1", "dtmfDigits": "1"})
    assert "call you back" in xml and "phoneNumbers" not in xml
    await db.commit()
    assert (await db.execute(select(VoiceCallback).where(VoiceCallback.phone_number == caller2))).scalar_one().state == "PENDING"
