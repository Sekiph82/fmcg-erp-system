"""M48.S01.T022 remediation of the T015 M36 audit (consent and outbound), one regression per finding.

F1 double opt-in (form + chat → PENDING + CONSENT mail; signed expiring link; SUBSCRIBED only on confirm with time and
IP hash; unsubscribe protection kept; campaigns need SUBSCRIBED). F2 production URL validator and dedicated
UNSUBSCRIBE_SECRET with previous keys and SECRET_KEY fallback. F7 retention purge and consent anonymisation.
F8 INVOICE not blocked by UNSUBSCRIBED. F11 Mailgun token replay. Unit parts run always; DB parts need M48_DB=1.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from starlette.requests import Request

from app.core.config import Settings, settings
from app.services import crm_outbound_service as outbound
from app.services import deliverability_service as dv

DB = pytest.mark.skipif(os.environ.get("M48_DB") != "1", reason="requires the disposable M48 PostgreSQL")
STRONG = "Zq8#Lp2!Vw9@Rt4$Kx7%Mn3^Hb6&Jc1*Yd5"


def _req(ip: str) -> Request:
    return Request({"type": "http", "method": "POST", "path": "/", "headers": [], "client": (ip, 5000)})


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M48_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


# ── F2 unit ───────────────────────────────────────────────────────────────────

def _prod(**kw):
    base = dict(ENVIRONMENT="production", SECRET_KEY=STRONG, WEBHOOK_SECRET_ENCRYPTION_KEY=STRONG[::-1] + "Q",
                PASSWORD_REQUIRE_SPECIAL=True, SEED_DEMO_DATA=False, SEED_INITIAL_ADMIN=False, AUTH_COOKIE_SECURE=True,
                SYNC_INITIAL_ADMIN_PASSWORD=False, OTP_DEV_DELIVERY_MODE=False, REDIS_PASSWORD=STRONG,
                TWO_FACTOR_EMAIL_ENABLED=False, ERP_SEED_MANAGEMENT_USERS=False,
                PUBLIC_APP_URL="https://erp.povu-demo.test", PUBLIC_API_URL="https://api.povu-demo.test")
    base.update(kw)
    return Settings(_env_file=None, **base)


def test_f2_production_refuses_local_or_http_urls_when_outbound_enabled():
    assert _prod(CRM_OUTBOUND_EMAIL_ENABLED=True).CRM_OUTBOUND_EMAIL_ENABLED
    assert _prod(CRM_OUTBOUND_EMAIL_ENABLED=False, PUBLIC_APP_URL="http://localhost:3000")   # off: not checked
    for bad in ({"PUBLIC_APP_URL": "http://erp.povu-demo.test"}, {"PUBLIC_API_URL": "https://localhost:8000"},
                {"PUBLIC_API_URL": "https://127.0.0.1"}, {"PUBLIC_APP_URL": "https://app.localhost"}):
        with pytest.raises(ValueError, match="public https URL"):
            _prod(CRM_OUTBOUND_EMAIL_ENABLED=True, **bad)
    with pytest.raises(ValueError, match="UNSUBSCRIBE_SECRET"):
        _prod(UNSUBSCRIBE_SECRET="short")


def test_f2_dedicated_unsubscribe_secret_with_previous_keys_and_fallback(monkeypatch):
    monkeypatch.setattr(settings, "UNSUBSCRIBE_SECRET", "")
    monkeypatch.setattr(settings, "UNSUBSCRIBE_PREVIOUS_SECRETS", "")
    old = outbound.unsubscribe_token("Buyer@example.com")
    # blank secret = SECRET_KEY, byte-identical to the pre-M48 format (links already delivered keep working)
    raw = b"buyer@example.com"
    legacy_sig = hmac.new(settings.SECRET_KEY.encode(), b"unsub:" + raw, hashlib.sha256).digest()[:16]
    assert old.split(".")[1] == outbound._enc(legacy_sig)
    assert outbound.email_from_token(old) == "buyer@example.com"
    monkeypatch.setattr(settings, "UNSUBSCRIBE_SECRET", "n" * 40)
    assert outbound.email_from_token(old) is None                       # old key not trusted unless listed
    monkeypatch.setattr(settings, "UNSUBSCRIBE_PREVIOUS_SECRETS", f"other-key, {settings.SECRET_KEY}")
    assert outbound.email_from_token(old) == "buyer@example.com"     # rotated: still verified
    new = outbound.unsubscribe_token("buyer@example.com")
    assert new != old and outbound.email_from_token(new) == "buyer@example.com"
    assert outbound.email_from_token(new[:-2] + "AA") is None


def test_f1_confirm_token_signed_and_expiring(monkeypatch):
    monkeypatch.setattr(settings, "UNSUBSCRIBE_SECRET", "")
    t = outbound.confirm_token("grace@example.com")
    assert outbound.email_from_confirm_token(t) == "grace@example.com"
    assert outbound.email_from_token(t) is None                         # not usable as an unsubscribe token
    part, exp, sig = t.split(".")
    assert outbound.email_from_confirm_token(f"{part}.{int(exp) + 999}.{sig}") is None   # expiry is signed
    assert outbound.email_from_confirm_token(outbound.confirm_token("grace@example.com", now=time.time() - 4 * 86400)) is None
    other = outbound._enc(b"victim@example.com")
    assert outbound.email_from_confirm_token(f"{other}.{exp}.{sig}") is None


# ── F11 unit part ─────────────────────────────────────────────────────────────

def _mailgun(key, token, event_id, ts=None):
    ts = str(int(ts or time.time()))
    sig = hmac.new(key.encode(), f"{ts}{token}".encode(), hashlib.sha256).hexdigest()
    return {"signature": {"timestamp": ts, "token": token, "signature": sig},
            "event-data": {"id": event_id, "event": "complained", "recipient": "x@example.com",
                           "message": {"headers": {"message-id": "m@example.com"}}}}


# ── DB ────────────────────────────────────────────────────────────────────────

async def _form(db, s, company_id=None):
    from app.models.crm import CRMLeadForm
    form = CRMLeadForm(slug=f"t022-{s}", name="POVU AllClean enquiry", title="Enquiry", require_consent=False,
                       consent_text="POVU may e-mail me about home care products.", company_id=company_id)
    db.add(form)
    await db.commit()
    return form


@DB
@pytest.mark.asyncio
async def test_f1_form_and_chat_double_opt_in(monkeypatch):
    from app.api.v1.endpoints import chat_public, crm_consent_confirm_public as public
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMContactConsent, CRMOutboundMessage
    from app.services import crm_lead_capture_service as capture

    monkeypatch.setattr(settings, "UNSUBSCRIBE_SECRET", "")
    s = uuid4().hex[:8]
    email, quitter, chatter = f"grace-{s}@example.com", f"quit-{s}@example.com", f"chat-{s}@example.com"
    async with AsyncSessionLocal() as db:
        form = await _form(db, s)
        await capture.submit(db, form, capture.LeadSubmission(company_name="POVU Duka", contact_email=email, consent=True),
                             f"41.1.{int(s[:2], 16)}.1")
        row = await outbound.consent_for(db, email)
        assert row.status == "PENDING" and row.confirmed_at is None
        mails = (await db.execute(select(CRMOutboundMessage).where(CRMOutboundMessage.to_email == email))).scalars().all()
        assert len(mails) == 1 and mails[0].purpose == "CONSENT" and mails[0].status == "QUEUED"
        assert outbound._with_footer(mails[0])[1] == {} and not mails[0].track_engagement
        # a second submission the same day sends no second e-mail
        await capture.submit(db, form, capture.LeadSubmission(company_name="POVU Duka", contact_email=email, consent=True),
                             f"41.2.{int(s[:2], 16)}.1")
        assert len((await db.execute(select(CRMOutboundMessage).where(CRMOutboundMessage.to_email == email))).scalars().all()) == 1
        # campaigns still need SUBSCRIBED
        c = await outbound.queue(db, to_email=email, subject="Offer", body="b", purpose="CAMPAIGN", dedupe_key=f"c1:{email}")
        assert c.status == "SUPPRESSED" and c.status_reason == "no marketing consent on record"

        token = parse_qs(urlparse(mails[0].body_text.split("\n")[3]).query)["t"][0]
        got = await public.check_confirmation(token, db)                # GET (scanner prefetch) changes nothing
        assert got["pending"] and not got["subscribed"] and (await outbound.consent_for(db, email)).status == "PENDING"
        with pytest.raises(HTTPException) as e:
            await public.confirm_subscription(_req("41.9.9.9"), token[:-3] + "xyz", db)
        assert e.value.status_code == 404
        done = await public.confirm_subscription(_req("41.9.9.9"), token, db)
        assert done["subscribed"]
        row = await outbound.consent_for(db, email)
        assert row.status == "SUBSCRIBED" and row.confirmed_at is not None
        assert row.confirm_ip_hash == capture.ip_hash("41.9.9.9") and "41.9.9.9" not in row.confirm_ip_hash
        c2 = await outbound.queue(db, to_email=email, subject="Offer", body="b", purpose="CAMPAIGN", dedupe_key=f"c2:{email}")
        assert c2.status == "QUEUED"

        # UNSUBSCRIBED protection stays: no confirmation mail, and an old link cannot re-subscribe
        await outbound.record_consent(db, quitter, "PENDING", "form:x")
        old_link = outbound.confirm_token(quitter)
        await outbound.record_consent(db, quitter, "UNSUBSCRIBED", "unsubscribe-link")
        await db.commit()
        await capture.submit(db, form, capture.LeadSubmission(company_name="POVU Duka", contact_email=quitter, consent=True),
                             f"41.3.{int(s[:2], 16)}.1")
        assert not (await db.execute(select(CRMOutboundMessage).where(CRMOutboundMessage.to_email == quitter))).scalars().all()
        res = await public.confirm_subscription(_req("41.9.9.8"), old_link, db)
        assert res["blocked"] and (await outbound.consent_for(db, quitter)).status == "UNSUBSCRIBED"

        # chat consent is PENDING too
        started = await chat_public.start_chat(chat_public.StartIn(name="Chat", email=chatter, consent=True), _req("41.7.7.7"), db)
        assert started["session_id"]
        assert (await db.execute(select(CRMContactConsent.status).where(CRMContactConsent.email == chatter))).scalar_one() == "PENDING"
        assert (await db.execute(select(CRMOutboundMessage.purpose).where(CRMOutboundMessage.to_email == chatter))).scalar_one() == "CONSENT"


@DB
@pytest.mark.asyncio
async def test_f8_invoice_not_blocked_by_unsubscribe():
    from app.db.session import AsyncSessionLocal
    s = uuid4().hex[:8]
    gone, bounced = f"gone-{s}@example.com", f"bnc-{s}@example.com"
    async with AsyncSessionLocal() as db:
        await outbound.record_consent(db, gone, "UNSUBSCRIBED", "unsubscribe-link")
        await outbound.record_consent(db, bounced, "BOUNCED", "bounce report")
        inv = await outbound.queue(db, to_email=gone, subject="Invoice", body="pay", purpose="INVOICE", dedupe_key=f"i1:{gone}")
        man = await outbound.queue(db, to_email=gone, subject="Hi", body="b", purpose="MANUAL", dedupe_key=f"m1:{gone}")
        inv_b = await outbound.queue(db, to_email=bounced, subject="Invoice", body="pay", purpose="INVOICE", dedupe_key=f"i2:{bounced}")
        await db.commit()
        assert inv.status == "QUEUED" and man.status == "SUPPRESSED" and inv_b.status == "SUPPRESSED"
        await outbound.record_consent(db, gone, "COMPLAINED", "fbl")
        assert await outbound._blocked_reason(db, gone, "INVOICE") == "address is complained"


@DB
@pytest.mark.asyncio
async def test_f7_retention_purge_and_consent_anonymisation():
    from app.db.session import AsyncSessionLocal
    from app.models.audit_log import AuditLog
    from app.models.crm import CRMContactConsent, CRMLeadSubmission
    from app.services import crm_lead_capture_service as capture

    s = uuid4().hex[:8]
    old = datetime.now(timezone.utc) - timedelta(days=800)
    person, pend = f"erase-{s}@example.com", f"pend-{s}@example.com"
    async with AsyncSessionLocal() as db:
        form = await _form(db, s)
        fid = form.id
        db.add_all([CRMLeadSubmission(form_id=form.id, received_at=old, status="ACCEPTED", contact_email=f"o-{s}@example.com"),
                    CRMLeadSubmission(form_id=form.id, received_at=datetime.now(timezone.utc), status="ACCEPTED",
                                      contact_email=person),
                    CRMContactConsent(email=pend, status="PENDING", source="form:x", updated_at=old)])
        await db.commit()
        counts = await capture.purge_retention(db)
        await db.commit()
        assert counts["lead_submissions"] >= 1 and counts["pending_consents"] >= 1
        assert set(counts) == {"lead_submissions", "email_events", "landing_events", "document_views", "signer_codes",
                               "pending_consents"}
        left = (await db.execute(select(CRMLeadSubmission.contact_email).where(CRMLeadSubmission.form_id == form.id))).scalars().all()
        assert left == [person]
        assert await outbound.consent_for(db, pend) is None

        # anonymise: address gone, status/timestamps/text kept, suppression still applies
        row = await outbound.record_consent(db, person, "UNSUBSCRIBED", "unsubscribe-link", "No more mail.")
        kept_at = row.updated_at
        await db.commit()
        assert await outbound.anonymise_consent(db, person, "dpo@example.com") == 2
        await db.commit()
        db.expire_all()
        assert not (await db.execute(select(CRMContactConsent).where(CRMContactConsent.email == person))).first()
        erased = (await db.execute(select(CRMContactConsent).where(
            CRMContactConsent.email == outbound.erased_email(person)))).scalar_one()
        assert erased.status == "UNSUBSCRIBED" and erased.updated_at == kept_at and erased.consent_text == "No more mail."
        assert (await db.execute(select(CRMLeadSubmission.contact_email).where(CRMLeadSubmission.form_id == fid))).scalar_one() is None
        assert (await db.execute(select(AuditLog).where(AuditLog.event_type == "CONSENT_ANONYMISED",
                                                       AuditLog.target_id == erased.email))).scalars().first()
        # the erased address typed into a form again: still suppressed, no confirmation e-mail, campaigns blocked
        form = await db.get(type(form), fid)
        await capture.submit(db, form, capture.LeadSubmission(company_name="POVU Duka", contact_email=person, consent=True),
                             f"41.4.{int(s[:2], 16)}.1")
        assert (await outbound.consent_for(db, person)).status == "UNSUBSCRIBED"
        q = await outbound.queue(db, to_email=person, subject="x", body="x", purpose="MANUAL", dedupe_key=f"m:{person}")
        assert q.status == "SUPPRESSED"
        assert await outbound.anonymise_consent(db, person, "dpo@example.com") >= 0      # second erasure: no conflict
        await db.commit()


@DB
@pytest.mark.asyncio
async def test_f11_mailgun_token_replay_rejected(monkeypatch):
    from app.db.session import AsyncSessionLocal
    from app.models.crm import MailFeedbackEvent, MailWebhookToken

    monkeypatch.setattr(settings, "MAIL_EVENTS_MAILGUN_SIGNING_KEY", "sim-key")
    tok = f"tok-{uuid4().hex}"
    async with AsyncSessionLocal() as db:
        first = await dv.apply(db, "mailgun", dv.verify_mailgun(_mailgun("sim-key", tok, f"ev1-{tok}")))
        await db.commit()
        assert first["ignored"] == 1 and "replayed" not in first
        # the captured signature reused with other event data: refused, nothing stored
        replay = await dv.apply(db, "mailgun", dv.verify_mailgun(_mailgun("sim-key", tok, f"ev2-{tok}")))
        await db.commit()
        assert replay["replayed"] == 1 and replay["ignored"] == 0
        assert not (await db.execute(select(MailFeedbackEvent).where(MailFeedbackEvent.event_id == f"ev2-{tok}"))).first()
        # tokens outside the window are pruned
        stale = f"stale-{uuid4().hex}"
        db.add(MailWebhookToken(token=stale, signed_at=datetime.now(timezone.utc) - timedelta(seconds=dv.MAX_AGE + 60)))
        await db.commit()
        await dv.apply(db, "mailgun", dv.verify_mailgun(_mailgun("sim-key", f"t3-{uuid4().hex}", f"ev3-{tok}")))
        await db.commit()
        assert await db.get(MailWebhookToken, stale) is None and await db.get(MailWebhookToken, tok) is not None
