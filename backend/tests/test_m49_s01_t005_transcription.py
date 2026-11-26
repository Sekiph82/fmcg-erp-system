"""M49.S01.T005 multilingual transcription, speaker labels, review/edit/withdraw, redaction, fallback - local simulator.

Needs the disposable PostgreSQL (M49_DB=1). No real provider is ever called; audio are tiny synthetic fixtures served by
the simulator. No accuracy figure exists anywhere in this feature, and the tests assert that.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.core import provider_http
from app.core.config import settings
from tests.provider_sim import voice2_app as v2
from tests.test_m49_s01_t004_contact_center import _agent, _engine  # noqa: F401  (autouse fixture creates the tables)

pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(os.environ.get("M49_DB") != "1", reason="requires the disposable PostgreSQL")]
SIM = "http://127.0.0.1:8767"
REC = "https://127.0.0.1:8767/recordings/"


@pytest.fixture
def sim(monkeypatch):
    app = v2.create_app()
    for k, v in v2.sim_settings(SIM).items():
        monkeypatch.setitem(settings.__dict__, k, v)
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "local")
    monkeypatch.setattr("app.services.transcription_pipeline_service._BACKOFF", 0)
    provider_http.set_test_transport(httpx.ASGITransport(app=app))
    yield app
    provider_http.set_test_transport(None)


@pytest.fixture
async def db():
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as s:
        yield s


async def _call(db, agent, lang="en", consent=True):
    from app.models.voip import CallLog
    c = CallLog(call_ref=f"CALL-{uuid.uuid4().hex[:10].upper()}", direction="INBOUND", phone_number="+254700000999", agent_id=agent.id,
                started_at=datetime.utcnow(), recording_consent=consent, recording_url=f"{REC}c{uuid.uuid4().hex[:4]}-{lang}.wav",
                recording_expires_at=datetime.now(timezone.utc) + timedelta(days=30))
    db.add(c)
    await db.commit()
    return c


def _start(api, call, **kw):
    return api.StartIn(source_type=kw.pop("source_type", "call"), source_id=call.id, **kw)


async def test_engines_are_honest_and_no_engine_is_not_available(sim, db, monkeypatch):
    from app.api.v1.endpoints import transcripts as api
    me = await _agent(db)
    e = {x["key"]: x for x in (await api.engines(me))["engines"]}
    assert e["openai"]["state"] == "AVAILABLE" and e["local"]["state"] == "NOT_AVAILABLE" and "pip install faster-whisper" in e["local"]["note"]
    assert e["openai"]["languages"] == {"en": "SUPPORTED", "sw": "SUPPORTED", "tr": "SUPPORTED"}
    call = await _call(db, me)
    with pytest.raises(HTTPException) as err:                                   # asking for the missing local engine
        await api.start(_start(api, call, engine="local"), db, me)
    assert err.value.status_code == 409 and "NOT_AVAILABLE" in err.value.detail and "faster-whisper" in err.value.detail
    monkeypatch.setitem(settings.__dict__, "TRANSCRIPTION_OPENAI_API_KEY", "")
    with pytest.raises(HTTPException) as err:
        await api.start(_start(api, call), db, me)
    assert err.value.status_code == 409 and "type the transcript manually" in err.value.detail


@pytest.mark.parametrize("lang,word", [("en", "price"), ("sw", "Bei ya POVU"), ("tr", "fiyati")])
async def test_language_selection_timestamps_and_provider_request(sim, db, lang, word):
    from app.api.v1.endpoints import transcripts as api
    me = await _agent(db)
    call = await _call(db, me, lang)
    job = await api.start(_start(api, call, language=lang), db, me)
    assert job["status"] == "DONE" and job["engine"] == "openai" and job["model"] == "whisper-1"
    assert sim.state.sim["openai_seen"][-1] == {"model": "whisper-1", "format": "verbose_json", "language": lang}
    assert job["language_detected"] == lang and any(word in s["text"] for s in job["segments"])
    assert [s["start"] for s in job["segments"]] == [0.0, 3.4, 8.1] and all(s["speaker"] is None for s in job["segments"])
    q = job["quality"]
    assert set(q) == {"segments", "speakers", "flags", "provider_signals", "note"} and q["flags"] == []
    assert q["provider_signals"] == {"mean_avg_logprob": -0.25, "max_no_speech_prob": 0.02} and "no accuracy" in q["note"]


async def test_auto_language_detected_and_diarization_labels(sim, db):
    from app.api.v1.endpoints import transcripts as api
    me = await _agent(db)
    call = await _call(db, me, "tr")
    job = await api.start(_start(api, call, language="auto"), db, me)
    assert sim.state.sim["openai_seen"][-1]["language"] is None and job["language_detected"] == "tr"
    await api.withdraw(uuid.UUID(job["id"]), db, me)
    d = await api.start(_start(api, call, language="sw", diarize=True), db, me)
    assert sim.state.sim["openai_seen"][-1]["model"] == "gpt-4o-transcribe-diarize"
    assert [s["speaker"] for s in d["segments"]] == ["A", "B", "A"] and d["quality"]["speakers"] == ["A", "B"]
    assert any("UNVERIFIED" in w for w in d["warnings"])                           # sw diarization is not claimed


async def test_pii_is_redacted_before_storage(sim, db):
    from app.api.v1.endpoints import transcripts as api
    from app.models.m49_voice import TranscriptJob
    me = await _agent(db)
    job = await api.start(_start(api, await _call(db, me), language="en"), db, me)
    text = " ".join(s["text"] for s in job["segments"])
    assert "agent@example.com" not in text and "[email]" in text and "712 345 678" not in text and job["redacted_segments"] == 2
    stored = (await db.get(TranscriptJob, uuid.UUID(job["id"])))
    assert "agent@example.com" not in str(stored.segments)


async def test_provider_failures_retry_then_fail_clean_then_manual_fallback(sim, db):
    from app.api.v1.endpoints import transcripts as api
    me = await _agent(db)
    sim.state.sim["faults"]["openai"] += [429]                                      # transient: retried inside the adapter
    ok = await api.start(_start(api, await _call(db, me), language="en"), db, me)
    assert ok["status"] == "DONE"
    sim.state.sim["faults"]["openai"] += [401]                                      # bad credentials: never retried
    call = await _call(db, me)
    bad = await api.start(_start(api, call, language="en"), db, me)
    assert bad["status"] == "FAILED" and bad["error_code"] == "PROVIDER_AUTH" and sim.state.sim["faults"]["openai"] == []
    sim.state.sim["faults"]["openai"] += [503, 503, 503]                            # provider down for the whole retry budget
    call2 = await _call(db, me)
    down = await api.start(_start(api, call2, language="sw"), db, me)
    assert down["status"] == "FAILED" and down["error_code"] == "PROVIDER_UNAVAILABLE" and down["segments"] == []
    man = await api.manual(uuid.UUID(down["id"]), api.ManualIn(text="Habari yako.\nNitakupigia kesho."), db, me)
    assert man["status"] == "DONE" and man["engine"] == "manual" and [s["text"] for s in man["segments"]] == ["Habari yako.", "Nitakupigia kesho."]
    assert man["quality"]["note"].startswith("Typed by a person")
    retried = await api.retry(uuid.UUID(bad["id"]), db, me)                         # provider fixed -> retry works
    assert retried["status"] == "DONE"
    with pytest.raises(HTTPException) as e:                                         # only failed jobs take manual text
        await api.manual(uuid.UUID(retried["id"]), api.ManualIn(text="abc def"), db, me)
    assert e.value.status_code == 409


async def test_consent_and_access_rules(sim, db):
    from app.api.v1.endpoints import transcripts as api
    me, other = await _agent(db), await _agent(db)
    nocon = await api.start(_start(api, await _call(db, me, consent=False)), db, me)
    assert nocon["status"] == "FAILED" and nocon["error_code"] == "NO_CONSENTED_RECORDING"
    call = await _call(db, me)
    with pytest.raises(HTTPException) as e:
        await api.start(_start(api, call), db, other)
    assert e.value.status_code == 404
    job = await api.start(_start(api, call), db, me)
    with pytest.raises(HTTPException) as e:
        await api.edit_segment(uuid.UUID(job["id"]), 0, api.SegmentPatch(text="x"), db, other)
    assert e.value.status_code == 404
    with pytest.raises(HTTPException) as e:                                         # one live transcript per source
        await api.start(_start(api, call), db, me)
    assert e.value.status_code == 409
    mgr = await _agent(db, perms=("crm.edit_all",))
    assert (await api.get_job(uuid.UUID(job["id"]), db, mgr))["id"] == job["id"]


async def test_review_edit_approve_feeds_coaching_then_withdraw(sim, db, monkeypatch):
    from app.api.v1.endpoints import transcripts as api
    from app.models.crm import CRMConversationInsight
    from app.models.m49_voice import TranscriptEdit
    from app.models.voip import CallLog
    from app.services import conversation_intel_service as ci
    monkeypatch.setattr(settings, "CONVERSATION_INTELLIGENCE_ENABLED", True)
    me = await _agent(db)
    call = await _call(db, me)
    cid = call.id
    job = await api.start(_start(api, call, language="en"), db, me)
    jid = uuid.UUID(job["id"])
    assert (await db.get(CallLog, cid)).transcript is None                          # a machine draft feeds nothing
    seg = await api.edit_segment(jid, 1, api.SegmentPatch(text="The price is too high. Call Wanjiru on 0712 345 678.", speaker="Customer"), db, me)
    assert seg["edited"] is True and seg["speaker"] == "Customer" and "0712 345 678" not in seg["text"]   # typed PII redacted too
    trail = (await db.execute(select(TranscriptEdit).where(TranscriptEdit.job_id == jid))).scalars().all()
    assert len(trail) == 1 and trail[0].old_text.startswith("The price of POVU AllClean") and trail[0].new_speaker == "Customer"
    ok = await api.approve(jid, db, me)
    assert ok["review_status"] == "REVIEWED"
    call = await db.get(CallLog, cid, populate_existing=True)
    assert call.transcription_status == "DONE" and "Customer: The price is too high" in call.transcript and call.transcript_language == "en"
    insight = await ci.analyse(db, "call", cid, me)                                 # existing coaching consumes the approved text
    assert any(f["kind"] == "objection" and "too high" in f["quote"] for f in insight.findings)
    await db.commit()
    await api.edit_segment(jid, 2, api.SegmentPatch(text="I will send you a quote on Monday."), db, me)   # post-approval fix re-feeds
    assert "on Monday" in (await db.get(CallLog, cid, populate_existing=True)).transcript
    w = await api.withdraw(jid, db, me)
    assert w["status"] == "WITHDRAWN" and w["segments"] == [] and w["quality"] is None
    call = await db.get(CallLog, cid, populate_existing=True)
    assert call.transcript is None and call.transcription_status == "WITHDRAWN" and call.recording_consent is True
    assert (await db.execute(select(func.count()).select_from(CRMConversationInsight).where(CRMConversationInsight.source_id == cid))).scalar() == 0
    assert (await db.execute(select(func.count()).select_from(TranscriptEdit).where(TranscriptEdit.job_id == jid))).scalar() == 0
    assert (await api.withdraw(jid, db, me))["status"] == "WITHDRAWN"               # idempotent
    with pytest.raises(HTTPException) as e:
        await api.edit_segment(jid, 0, api.SegmentPatch(text="x"), db, me)
    assert e.value.status_code == 409
    again = await api.start(_start(api, call), db, me)                             # a fresh transcription is allowed afterwards
    assert again["status"] == "DONE"


async def test_meeting_transcript_feeds_recap_draft_and_withdraw(sim, db):
    from app.api.v1.endpoints import transcripts as api
    from app.models.m47_sales_depth import MeetingRecap
    from app.models.meetings import MeetingRecord
    me = await _agent(db)
    m = MeetingRecord(title="POVU distributor review", scheduled_at=datetime.utcnow(), host_id=me.id, recording_url=f"{REC}m1-en.wav")
    db.add(m)
    await db.commit()
    mid = m.id
    with pytest.raises(HTTPException) as e:
        await api.start(api.StartIn(source_type="meeting", source_id=mid), db, me)
    assert e.value.status_code == 422
    job = await api.start(api.StartIn(source_type="meeting", source_id=mid, language="en", participants_consented=True), db, me)
    assert job["status"] == "DONE" and await db.get(MeetingRecap, mid) is None
    await api.approve(uuid.UUID(job["id"]), db, me)
    r = await db.get(MeetingRecap, mid, populate_existing=True)
    assert r.source == "TRANSCRIPTION" and r.approved_at is None and "quote by Friday" in r.transcript
    await api.withdraw(uuid.UUID(job["id"]), db, me)
    assert await db.get(MeetingRecap, mid, populate_existing=True) is None


async def test_retention_purges_expired_transcripts(sim, db):
    from app.api.v1.endpoints import transcripts as api
    from app.models.m49_voice import TranscriptJob
    from app.services import contact_center_service as cc
    me = await _agent(db)
    job = await api.start(_start(api, await _call(db, me)), db, me)
    j = await db.get(TranscriptJob, uuid.UUID(job["id"]))
    assert j.expires_at > datetime.now(timezone.utc)
    j.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    await db.commit()
    assert (await cc.purge_expired(db))["transcripts"] >= 1
    await db.commit()
    j = await db.get(TranscriptJob, uuid.UUID(job["id"]), populate_existing=True)
    assert j.status == "EXPIRED" and j.segments is None and j.quality is None
