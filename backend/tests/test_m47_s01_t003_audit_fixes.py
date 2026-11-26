"""M47.S01.T003 audit fixes (unit + DB; the DB part needs M46_DB=1, the M47 tables and whatsapp_consents created).

1 WhatsApp opt-in / STOP opt-out; 2 staff mailbox send honours CRM suppression; 3 calendar list scoped to own events;
4 meeting-recap AI/transcription only with participants' consent; 5 recovery-code attempt cap; 6 WhatsApp token
encrypted at rest and never returned. Synthetic POVU data only.
"""
import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace

import httpx
import pytest

DB = pytest.mark.skipif(os.environ.get("M46_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
PW = uuid.uuid4().hex + "Aa1!"


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M46_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def _client():
    from app.main import app
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test")


# ── unit ──────────────────────────────────────────────────────────────────────

def test_whatsapp_token_encrypted_and_legacy_plaintext_readable():
    from app.models.whatsapp import WhatsAppConfig
    from app.schemas.whatsapp import WAConfigRead
    c = WhatsAppConfig(display_name="POVU WA", api_token="EAAG-povu-test-token-1234")
    assert c.api_token_stored.startswith("enc:v2:") and "1234" not in c.api_token_stored
    assert c.api_token == "EAAG-povu-test-token-1234" and c.api_token_hint == "••••1234"
    c.api_token_stored = "legacy-plain-token-9876"          # row written before the fix
    assert c.api_token == "legacy-plain-token-9876" and c.api_token_hint == "••••9876"
    c.api_token = None
    assert c.api_token_stored is None and c.api_token_hint is None
    assert "api_token" not in WAConfigRead.model_fields


def test_stop_keywords_exact_and_case_insensitive():
    from app.api.v1.endpoints.whatsapp import STOP_WORDS, norm_phone
    for w in ("stop", " Stop ", "UNSUBSCRIBE", "acha", "Dur"):
        assert w.strip().upper() in STOP_WORDS
    for w in ("stop please", "durum", "achana"):
        assert w.strip().upper() not in STOP_WORDS
    assert norm_phone("+254 700-000 101") == "+254700000101" and norm_phone("") == ""


def test_calendar_is_mine_and_redact():
    from app.services import calendar_service as cs
    me = SimpleNamespace(id=uuid.uuid4(), username="amina", email="Amina@povu-demo.test", is_superuser=False, roles=[])
    own = SimpleNamespace(created_by="amina", participants=[])
    attend = SimpleNamespace(created_by="juma", participants=[SimpleNamespace(user_id=None, participant_email="amina@povu-demo.test")])
    other = SimpleNamespace(created_by="juma", participants=[SimpleNamespace(user_id="x", participant_email="juma@povu-demo.test")])
    assert cs.is_mine(own, me) and cs.is_mine(attend, me) and not cs.is_mine(other, me)
    r = cs.redact({"event_id": "e", "event_title": "Visit", "description": "secret", "location": "Duka Moja",
                   "participants": [{"participant_email": "x@povu-demo.test"}], "bookings": [{}]})
    assert r["description"] is None and r["location"] is None and r["participants"] == [] and r["redacted"]


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


async def _login(c, username):
    r = await c.post("/api/v1/auth/login", data={"username": username, "password": PW})
    assert r.status_code == 200, r.text


CRM = ("crm.view", "crm.create", "crm.edit", "sales.view")


# ── 1 + 6: WhatsApp ───────────────────────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_whatsapp_opt_in_stop_and_encrypted_token(monkeypatch):
    from sqlalchemy import func, select, text
    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    from app.models.whatsapp import WhatsAppConsent, WhatsAppMessage
    async with AsyncSessionLocal() as db:
        rep = (await _user(db, CRM + ("crm.edit_all",), "warep")).username   # M47 review: consent/config need edit_all
        await db.commit()
    n = uuid.uuid4().int % 10**6
    p1, p2, p3, p4 = (f"+2547{n:06d}{i}" for i in range(1, 5))
    biz = f"povu-biz-{uuid.uuid4().hex[:8]}"
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", "t003-app-secret")

    async def inbound(phone, body):   # M47 review: only a signed webhook message counts (simulate-inbound no longer does)
        raw = json.dumps({"entry": [{"changes": [{"value": {"metadata": {"phone_number_id": biz}, "contacts": [],
                          "messages": [{"from": phone.lstrip("+"), "id": f"wamid.{uuid.uuid4().hex}", "type": "text",
                                        "text": {"body": body}}]}}]}]}).encode()
        sig = "sha256=" + hmac.new(b"t003-app-secret", raw, hashlib.sha256).hexdigest()
        async with _client() as pub:
            r = await pub.post("/api/v1/whatsapp/webhook", content=raw,
                               headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"})
        assert r.status_code == 200, r.text
        return r
    async with _client() as c:
        await _login(c, rep)
        r = await c.post("/api/v1/whatsapp/configs", json={"display_name": "POVU Sales", "api_token": "EAAG-povu-secret-5678",
                                                           "business_phone_id": biz, "is_demo_mode": True})
        assert r.status_code == 201, r.text
        cfg = r.json()
        assert "EAAG" not in r.text and cfg["api_token_hint"] == "••••5678"
        async with AsyncSessionLocal() as db:
            raw = (await db.execute(text("SELECT api_token FROM whatsapp_configs WHERE id = :i"), {"i": cfg["id"]})).scalar_one()
        assert raw.startswith("enc:v2:") and "5678" not in raw
        listed = (await c.get("/api/v1/whatsapp/configs")).text
        assert "EAAG" not in listed

        send = lambda phone: c.post("/api/v1/whatsapp/send/text", json={"config_id": cfg["id"], "phone": phone, "body": "POVU AllClean 1 L offer"})
        r = await send(p1)
        assert r.status_code == 422 and "no WhatsApp opt-in" in r.json()["detail"]
        assert (await c.post("/api/v1/whatsapp/consents", json={"phone": p1, "status": "OPTED_IN"})).status_code == 422
        r = await c.post("/api/v1/whatsapp/consents", json={"phone": p1, "status": "OPTED_IN", "proof": "Signed form at Duka Moja"})
        assert r.status_code == 200, r.text
        assert (await send(p1)).status_code == 201

        # customer replies STOP (any case): opted out, acknowledged once even when it arrives twice
        sim = inbound
        await sim(p1, " stop ")
        await sim(p1, "STOP")
        r = await send(p1)
        assert r.status_code == 422 and "opted out" in r.json()["detail"]
        r = await c.post("/api/v1/whatsapp/send/template", json={"config_id": cfg["id"], "phone": p1, "template_name": "order_confirmation"})
        assert r.status_code == 422
        r = await c.post("/api/v1/whatsapp/consents", json={"phone": p1, "status": "OPTED_IN", "proof": "phoned"})
        assert r.status_code == 409          # staff never override the customer's STOP
        # Swahili / Turkish keywords; ack in the customer's language
        await sim(p2, "Acha")
        await sim(p3, "dur")
        # a customer who just wrote to us can be answered within 24 h without a stored opt-in
        await sim(p4, "Habari, bei ya POVU WhiteCare 1 kg?")
        assert (await send(p4)).status_code == 201
        # START lifts the opt-out (customer's own action)
        await sim(p1, "start")
        assert (await send(p1)).status_code == 201
    async with AsyncSessionLocal() as db:
        acks = lambda ph: db.execute(select(WhatsAppMessage.body).where(
            WhatsAppMessage.phone == ph, WhatsAppMessage.linked_module == "whatsapp_consent"))
        a1 = (await acks(p1)).scalars().all()
        assert len(a1) == 1 and a1[0].startswith("You will no longer")
        assert (await acks(p2)).scalars().one().startswith("Hutapokea")
        assert (await acks(p3)).scalars().one().startswith("Artık")
        st = dict((await db.execute(select(WhatsAppConsent.phone, WhatsAppConsent.status).where(
            WhatsAppConsent.phone.in_((p1, p2, p3))))).all())
        assert st == {p1: "OPTED_IN", p2: "OPTED_OUT", p3: "OPTED_OUT"}

    # the signed Meta webhook path handles UNSUBSCRIBE too
    p5 = f"2547{n:06d}5"
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", "t003-app-secret")
    payload = json.dumps({"entry": [{"changes": [{"value": {"metadata": {"phone_number_id": biz}, "contacts": [],
                                                            "messages": [{"from": p5, "id": f"wamid.{uuid.uuid4().hex}", "type": "text",
                                                                          "text": {"body": "Unsubscribe"}}]}}]}]}).encode()
    sig = "sha256=" + hmac.new(b"t003-app-secret", payload, hashlib.sha256).hexdigest()
    async with _client() as pub:
        r = await pub.post("/api/v1/whatsapp/webhook", content=payload, headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"})
        assert r.status_code == 200, r.text
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(WhatsAppConsent.status).where(WhatsAppConsent.phone == "+" + p5))).scalar_one() == "OPTED_OUT"
        assert (await db.execute(select(func.count()).select_from(WhatsAppMessage).where(
            WhatsAppMessage.phone == "+" + p5, WhatsAppMessage.linked_module == "whatsapp_consent"))).scalar_one() == 1


# ── 2: staff mailbox suppression ──────────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_mailbox_send_refuses_suppressed_addresses(monkeypatch):
    from app.db.session import AsyncSessionLocal
    from app.models.email_integration import EmailAccount, EmailProvider
    from app.services import crm_outbound_service as out
    from app.services import email_mailbox_service as mbx
    sent = []
    monkeypatch.setattr(mbx, "smtp_send", lambda *a: sent.append(a[-1]["To"]))
    s = uuid.uuid4().hex[:6]
    bounced, complained, unsub, ok = (f"{k}-{s}@povu.example.com" for k in ("bounced", "complained", "unsub", "duka"))
    async with AsyncSessionLocal() as db:
        u = await _user(db, CRM, "mailer")
        acc = EmailAccount(provider=EmailProvider.SMTP, email_address=f"rep-{s}@povu-demo.test", created_by_id=u.id,
                           imap_host="imap.povu-demo.test", imap_port=993, smtp_host="smtp.povu-demo.test", smtp_port=465,
                           username="rep", secret_enc=mbx.encrypt("pw"), is_active=True)
        db.add(acc)
        for addr, st in ((bounced, "BOUNCED"), (complained, "COMPLAINED"), (unsub, "UNSUBSCRIBED")):
            await out.record_consent(db, addr, st, "test")
        await db.commit()
        acc_id, uname = str(acc.id), u.username
    async with _client() as c:
        await _login(c, uname)
        mail = lambda to, cc=(): c.post("/api/v1/email/send", json={"account_id": acc_id, "to_emails": list(to), "cc_emails": list(cc),
                                                                    "subject": "POVU price list", "body_text": "Hello"})
        for addr, word in ((bounced, "bounced"), (complained, "complained"), (unsub, "unsubscribed")):
            r = await mail([addr])
            assert r.status_code == 422 and addr in r.json()["detail"] and word in r.json()["detail"], r.text
        r = await mail([ok], [unsub.upper()])
        assert r.status_code == 422 and unsub in r.json()["detail"]
        assert sent == []
        r = await mail([ok])
        assert r.status_code == 201, r.text
        assert sent == [ok]


# ── 3: calendar scope ─────────────────────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_calendar_events_scoped_to_owner_and_participants():
    from app.db.session import AsyncSessionLocal
    from app.models.calendar import CalendarEvent, EventParticipant
    async with AsyncSessionLocal() as db:
        owner = await _user(db, CRM, "calown")
        guest = await _user(db, CRM, "calguest")
        mailguest = await _user(db, CRM, "calmail")
        outsider = await _user(db, CRM, "calout")
        admin = await _user(db, ("users.edit", "crm.view"), "caladm")
        start = datetime.utcnow() + timedelta(days=2)
        ev = CalendarEvent(event_title="POVU WhiteCare 1 kg listing at Duka Moja", start_datetime=start, end_datetime=start + timedelta(hours=1),
                           created_by=owner.username, description="Private: discount 7%", location="Duka Moja back office")
        db.add(ev)
        await db.flush()
        db.add_all([EventParticipant(event_id=ev.event_id, user_id=str(guest.id), participant_name="Guest"),
                    EventParticipant(event_id=ev.event_id, participant_email=mailguest.email.upper(), participant_name="Mail guest")])
        await db.commit()
        eid = ev.event_id
        names = {k: v.username for k, v in dict(owner=owner, guest=guest, mailguest=mailguest, outsider=outsider, admin=admin).items()}
    for who, expect in (("owner", "full"), ("guest", "full"), ("mailguest", "full"), ("outsider", None), ("admin", "redacted")):
        async with _client() as c:
            await _login(c, names[who])
            rows = [e for e in (await c.get("/api/v1/calendar/events")).json() if e["event_id"] == eid]
            one = await c.get(f"/api/v1/calendar/events/{eid}")
            if expect is None:
                assert rows == [] and one.status_code == 404, who
            elif expect == "full":
                assert rows[0]["description"] == "Private: discount 7%" and len(rows[0]["participants"]) == 2, who
                assert one.json()["location"] == "Duka Moja back office"
            else:
                assert rows[0]["description"] is None and rows[0]["location"] is None and rows[0]["participants"] == [], who
                assert rows[0]["event_title"] and one.status_code == 200 and one.json()["description"] is None


# ── 4: meeting recap consent ──────────────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_meeting_recap_needs_participant_consent_for_ai(monkeypatch):
    from app.db.session import AsyncSessionLocal
    from app.models.meetings import MeetingRecord
    from app.services import sales_ai_service as ai
    from app.services import transcription_service as ts
    calls = {"ai": 0, "asr": 0}
    t = "Amina: We agreed to list POVU WhiteCare 1 kg at Duka Moja.\nJuma: I will send the price list tomorrow.\nAmina: Fine."

    async def fake_ai(db, prompt, system, schema):
        calls["ai"] += 1
        return {"decisions": [{"quote": "We agreed to list POVU WhiteCare 1 kg at Duka Moja."}], "action_items": []}

    async def fake_asr(raw):
        calls["asr"] += 1
        return {"segments": [{"speaker": "Amina", "text": "We agreed to list POVU WhiteCare 1 kg at Duka Moja today."}]}
    monkeypatch.setattr(ai, "structured", fake_ai)
    monkeypatch.setattr(ts, "adapter", lambda: "http")
    monkeypatch.setattr(ts, "_http", fake_asr)
    async with AsyncSessionLocal() as db:
        u = await _user(db, CRM, "recap")
        m = MeetingRecord(id=uuid.uuid4(), title="Duka Moja review", platform="jitsi", host_id=u.id,
                          scheduled_at=datetime.utcnow() + timedelta(days=1), duration_minutes=30, status="SCHEDULED", attendees=[])
        db.add(m)
        await db.commit()
        mid, uname = m.id, u.username
    url = f"/api/v1/sales-depth/meetings/{mid}/transcript"
    audio = {"file": ("call.mp3", b"ID3" + b"\x00" * 50, "audio/mpeg")}
    async with _client() as c:
        await _login(c, uname)
        r = await c.post(url, files=audio)
        assert r.status_code == 422 and "agreed" in r.json()["detail"] and calls["asr"] == 0
        r = await c.post(url, data={"text": t})                     # no consent: local rules recap, nothing sent to the AI
        assert r.status_code == 200 and r.json()["engine"] == "rules" and r.json()["participants_consented"] is False
        assert calls["ai"] == 0
        r = await c.post(url, data={"text": t, "participants_consented": "true"})
        assert r.status_code == 200 and r.json()["engine"] == "ai" and r.json()["participants_consented"] is True
        assert r.json()["recap"]["consent"]["attested_by"] == uname and calls["ai"] == 1
        r = await c.post(url, files=audio, data={"participants_consented": "true"})
        assert r.status_code == 200, r.text
        assert calls["asr"] == 1 and r.json()["source"] == "TRANSCRIPTION"


# ── 5: recovery-code attempt cap ──────────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_recovery_code_attempts_are_capped():
    from app.api.v1.endpoints.two_factor import MAX_ATTEMPTS
    from app.core import totp as totp_utils
    from app.crud import two_factor as tfa_crud
    from app.db.session import AsyncSessionLocal
    from app.models.two_factor import TwoFAMethod
    good = "ABCDE-23456"
    async with AsyncSessionLocal() as db:
        u = await _user(db, ("crm.view",), "tfa")
        st = await tfa_crud.get_or_create_2fa_settings(db, u.id, TwoFAMethod.TOTP)
        await tfa_crud.create_recovery_codes(db, u.id, st.id, [good])
        sess = await tfa_crud.create_2fa_session(db, u.id, st.id, TwoFAMethod.TOTP)
        await db.commit()
        token = totp_utils.create_pending_2fa_token(str(u.id), str(sess.id))
    async with _client() as c:
        for i in range(MAX_ATTEMPTS):
            r = await c.post("/api/v1/auth/2fa/use-recovery-code", json={"session_token": token, "code": f"WRONG-{i:05d}"})
            assert r.status_code == 401, r.text
        r = await c.post("/api/v1/auth/2fa/use-recovery-code", json={"session_token": token, "code": good})
        assert r.status_code in (401, 429), r.text           # the correct code no longer works on this session
        assert "access_token" not in r.text
