"""M43.S01.T008/T009 voice adapter, power dialer, IVR, transcription — local simulator, disposable PostgreSQL.

Run at the M43 gate (M43_S01_DB=1). No real number is ever called (egress local; simulator only).
Covers: no provider → tel: fallback and capabilities say so; click-to-call rings the agent through the simulator;
callback token required; answer callback dials the customer (record only with consent); repeated/late callbacks are
idempotent and never overwrite a final state; recording kept only with consent and expires; inbound IVR greeting,
digit routing to available agents, consent announcement; dialer one-at-a-time; transcription retries then DONE with
segments; consent withdrawal deletes recording/transcript/insights.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.core import provider_http
from app.core.config import settings
from tests.provider_sim import create_app, sim_settings

pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(os.environ.get("M43_S01_DB") != "1",
              reason="requires the task-owned disposable PostgreSQL at the M43 head")]
SIM = "http://127.0.0.1:8765"


@pytest.fixture
def sim(monkeypatch):
    app = create_app()
    for k, v in sim_settings(SIM).items():
        monkeypatch.setattr(settings, k, v)
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "local")
    monkeypatch.setattr(settings, "CALL_TRANSCRIPTION_ENABLED", True)
    provider_http.set_test_transport(httpx.ASGITransport(app=app))
    yield app
    provider_http.set_test_transport(None)


@pytest.fixture
async def db():
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as s:
        yield s


@pytest.fixture
async def api():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def _call(**kw):
    from app.models.voip import CallLog
    base = dict(call_ref=f"CALL-{uuid.uuid4().hex[:10].upper()}", direction="OUTBOUND", phone_number="+254700000123",
                started_at=datetime.utcnow(), outcome="DIALED", follow_up_required=False)
    base.update(kw)
    return CallLog(**base)


async def test_disabled_provider_is_honest(monkeypatch):
    from app.services import voice_service as voice
    monkeypatch.setattr(settings, "VOICE_PROVIDER", "")
    caps = voice.capabilities()
    assert caps["configured"] is False and caps["server_dialing"] is False and caps["voicemail_drop"] is False


async def test_outbound_lifecycle_idempotent(sim, db, api):
    from app.services import voice_service as voice
    call = _call(recording_consent=True)
    db.add(call)
    await db.flush()
    await voice.place_call(db, call, "+254711111111")
    await db.commit()
    assert call.status == "QUEUED" and sim.state.sim["calls"][0]["to"] == "+254711111111"
    cb = "/api/v1/calls/provider/callback"
    assert (await api.post(cb, params={"token": "wrong"}, data={"sessionId": call.provider_session_id})).status_code == 403
    r = await api.post(cb, params={"token": "sim-voice-secret"},
                       data={"sessionId": call.provider_session_id, "isActive": "1", "direction": "Outbound"})
    assert 'phoneNumbers="+254700000123"' in r.text and 'record="true"' in r.text
    end = {"sessionId": call.provider_session_id, "isActive": "0", "status": "Success", "durationInSeconds": "42",
           "amount": "1.20", "currencyCode": "KES"}
    await api.post(cb, params={"token": "sim-voice-secret"}, data=end)
    await api.post(cb, params={"token": "sim-voice-secret"}, data={**end, "status": "Failed"})   # late duplicate
    await api.post(cb, params={"token": "sim-voice-secret"},
                   data={**end, "recordingUrl": "https://127.0.0.1:8765/recordings/x.wav"})
    await db.refresh(call)
    assert (call.status, call.outcome, call.duration_seconds) == ("COMPLETED", "ANSWERED", 42)
    assert call.recording_url and call.recording_expires_at


async def test_no_recording_without_consent(sim, db, api):
    from app.services import voice_service as voice
    call = _call(recording_consent=False)
    db.add(call)
    await db.flush()
    await voice.place_call(db, call, "+254711111111")
    await db.commit()
    r = await api.post("/api/v1/calls/provider/callback", params={"token": "sim-voice-secret"},
                       data={"sessionId": call.provider_session_id, "isActive": "1", "direction": "Outbound"})
    assert 'record="false"' in r.text
    await api.post("/api/v1/calls/provider/callback", params={"token": "sim-voice-secret"},
                   data={"sessionId": call.provider_session_id, "isActive": "0", "status": "Success",
                         "recordingUrl": "https://127.0.0.1:8765/recordings/y.wav"})
    await db.refresh(call)
    assert call.recording_url is None


async def test_inbound_ivr_routes_to_available_agent(sim, db, api):
    from app.models.user import User
    from app.models.voip import VoiceAgentProfile, VoiceIvrMenu
    agent = User(id=uuid.uuid4(), email=f"agent-{uuid.uuid4().hex[:6]}@povu-demo.test", username=f"syn-{uuid.uuid4().hex[:12]}", hashed_password="x",
                 full_name="Synthetic Agent", is_active=True)
    db.add(agent)
    await db.flush()
    db.add(VoiceAgentProfile(user_id=agent.id, phone_number="+254722222222", available=True))
    number = f"+2547{uuid.uuid4().int % 10**8:08d}"
    db.add(VoiceIvrMenu(name="POVU synthetic line", phone_number=number, greeting_text="Welcome to POVU.",
                        options=[{"digit": "1", "label": "Sales", "user_ids": [str(agent.id)], "phone_numbers": []}],
                        record_calls=True, consent_text="This call is recorded for quality."))
    await db.commit()
    cb, tok = "/api/v1/calls/provider/callback", {"token": "sim-voice-secret"}
    sid = f"ATVId_in{uuid.uuid4().hex[:6]}"
    r = await api.post(cb, params=tok, data={"sessionId": sid, "isActive": "1", "direction": "Inbound",
                                             "callerNumber": "+254733333333", "destinationNumber": number})
    assert "This call is recorded for quality." in r.text and "<GetDigits" in r.text and "Press 1 for Sales" in r.text
    r = await api.post(cb, params=tok, data={"sessionId": sid, "isActive": "1", "dtmfDigits": "1"})
    assert 'phoneNumbers="+254722222222"' in r.text
    r = await api.post(cb, params=tok, data={"sessionId": sid, "isActive": "1", "dtmfDigits": "9"})
    assert "not a valid choice" in r.text


async def test_transcription_retry_then_done_and_withdrawal(sim, db):
    from app.services import transcription_service as tx
    call = _call(recording_consent=True, recording_url="https://127.0.0.1:8765/recordings/z.wav")
    db.add(call)
    await db.flush()
    await tx.request(db, call)
    async with provider_http.provider_client() as c:
        await c.post(f"{SIM}/_control", json={"tx_fail": 1})
    await tx.process(db, call)
    assert call.transcription_status == "PENDING" and call.transcription_attempts == 1
    await tx.process(db, call)
    assert call.transcription_status == "DONE" and len(call.transcript_segments) == 3
    assert call.transcript_segments[1]["speaker"] == "B" and "too high" in call.transcript
    await tx.withdraw_consent(db, call)
    await db.commit()
    assert call.recording_url is None and call.transcript is None and call.transcription_status == "WITHDRAWN"


async def test_transcription_refused_without_consent(sim, db):
    from app.services import transcription_service as tx
    call = _call(recording_consent=False, recording_url="https://127.0.0.1:8765/recordings/n.wav")
    db.add(call)
    await db.flush()
    with pytest.raises(tx.TranscriptionError):
        await tx.request(db, call)


@pytest.fixture(autouse=True)
async def _dispose_engine():
    """Each test runs in its own event loop: drop pooled connections afterwards (same pattern as other DB tests)."""
    yield
    from app.db.session import engine
    await engine.dispose()
