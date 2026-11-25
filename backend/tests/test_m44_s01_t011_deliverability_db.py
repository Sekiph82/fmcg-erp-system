"""M44.S01.T011 deliverability (unit; DB part needs M44_DB=1). Runs at the M44 gate.

Mailgun HMAC valid/forged/stale, SendGrid ECDSA with a locally generated key, generic HMAC; unconfigured → 503;
DNS plan/check offline. DB: a complaint for a message we sent suppresses the address; forged (unknown message or
other recipient) is stored but ignored; the same provider event twice is applied once; suppressed address cannot be
mailed afterwards.
"""
import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import datetime, timezone

import pytest

from app.core.config import settings
from app.services import deliverability_service as dv


def _mailgun(key, ts=None, token="tok1", event="complained", mid="abc@povu-demo.test", to="buyer@povu-demo.test"):
    ts = str(int(ts or time.time()))
    sig = hmac.new(key.encode(), f"{ts}{token}".encode(), hashlib.sha256).hexdigest()
    return {"signature": {"timestamp": ts, "token": token, "signature": sig},
            "event-data": {"id": f"ev-{token}", "event": event, "recipient": to, "message": {"headers": {"message-id": mid}}}}


def test_mailgun_signature(monkeypatch):
    monkeypatch.setattr(settings, "MAIL_EVENTS_MAILGUN_SIGNING_KEY", "")
    with pytest.raises(dv.FeedbackError) as e:
        dv.verify_mailgun(_mailgun("k"))
    assert e.value.status_code == 503
    monkeypatch.setattr(settings, "MAIL_EVENTS_MAILGUN_SIGNING_KEY", "sim-key")
    assert dv.verify_mailgun(_mailgun("sim-key"))[0]["kind"] == "COMPLAINED"
    with pytest.raises(dv.FeedbackError):
        dv.verify_mailgun(_mailgun("wrong"))
    with pytest.raises(dv.FeedbackError):
        dv.verify_mailgun(_mailgun("sim-key", ts=time.time() - 3600))


def test_sendgrid_ecdsa(monkeypatch):
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    priv = ec.generate_private_key(ec.SECP256R1())
    der = priv.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    monkeypatch.setattr(settings, "MAIL_EVENTS_SENDGRID_PUBLIC_KEY", base64.b64encode(der).decode())
    raw = json.dumps([{"sg_event_id": "s1", "event": "spamreport", "email": "a@povu-demo.test", "smtp-id": "<x@y>"}]).encode()
    ts = str(int(time.time()))
    sig = base64.b64encode(priv.sign(ts.encode() + raw, ec.ECDSA(hashes.SHA256()))).decode()
    assert dv.verify_sendgrid(raw, sig, ts)[0]["kind"] == "COMPLAINED"
    with pytest.raises(dv.FeedbackError):
        dv.verify_sendgrid(raw + b" ", sig, ts)


def test_dns_plan_and_check():
    plan = dv.dns_plan("mail.povu-demo.test", "mailgun.org")
    assert plan["records"][0]["value"] == "v=spf1 include:mailgun.org ~all"
    res = {r["record"]: r["ok"] for r in dv.check_records("v=spf1 include:mailgun.org ~all", "v=DKIM1; k=rsa; p=" + "A" * 300,
                                                           "v=DMARC1; p=quarantine", "mailgun.org")}
    assert res == {"SPF": True, "DKIM": True, "DMARC": True}
    assert not {r["record"]: r["ok"] for r in dv.check_records("v=spf1 +all", "", "")}["SPF"]


DB = pytest.mark.skipif(os.environ.get("M44_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M44_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


@DB
@pytest.mark.asyncio
async def test_matching_complaint_applied_once_forged_ignored():
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMOutboundMessage
    from app.services import crm_outbound_service as outbound
    to = f"buyer-{uuid.uuid4().hex[:6]}@povu-demo.test"
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        db.add(CRMOutboundMessage(id=uuid.uuid4(), dedupe_key=f"fb:{to}", purpose="MANUAL", to_email=to, subject="s",
                                  body_text="b", status="SENT", attempts=1, next_attempt_at=now, created_at=now,
                                  sent_at=now, provider_message_id="<m1@povu-demo.test>"))
        await db.commit()
        forged = [{"event_id": "f1", "kind": "COMPLAINED", "email": to, "message_id": "other@x"},
                  {"event_id": "f2", "kind": "COMPLAINED", "email": "someone@povu-demo.test", "message_id": "m1@povu-demo.test"}]
        assert (await dv.apply(db, "generic", forged))["ignored"] == 2
        real = [{"event_id": "r1", "kind": "COMPLAINED", "email": to, "message_id": "m1@povu-demo.test"}]
        assert (await dv.apply(db, "generic", real))["applied"] == 1
        assert (await dv.apply(db, "generic", real))["duplicate"] == 1
        await db.commit()
        assert (await outbound.consent_for(db, to)).status == "COMPLAINED"
        again = await outbound.queue(db, to_email=to, subject="x", body="x", purpose="MANUAL", dedupe_key=f"fb2:{to}")
        assert again.status == "SUPPRESSED"
