"""M51.S01.T009 secure visitor e-mail verification (DB part M51_DB=1). Mail goes only to the local outbox."""
import os
import random
import re
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text

from tests.m51_s01_seo_common import client_for, ensure_tables, setv, staff

DB = pytest.mark.skipif(os.environ.get("M51_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
PUB = "/api/v1/public/visitor-verify"
STAFF = "/api/v1/visitor-verification"


@pytest.fixture(autouse=True)
async def _cleanup():
    yield
    if os.environ.get("M51_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def ids():
    return {"visitor": uuid.uuid4().hex, "session": uuid.uuid4().hex}


def new_ip():
    return f"198.51.{random.randint(1, 250)}.{random.randint(1, 250)}"


def addr():
    return f"visitor-{uuid.uuid4().hex[:8]}@example.com"


async def req(c, who, email, consent=True, **kw):
    return await c.post(f"{PUB}/request", json={**who, "email": email, "consent": consent, **kw})


async def outbox_for(email):
    from app.db.session import AsyncSessionLocal
    from app.models.m51_seo import M51VisitorMailOutbox
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(M51VisitorMailOutbox).where(M51VisitorMailOutbox.to_email == email.lower())
                                 .order_by(M51VisitorMailOutbox.created_at))).scalars().all()
    return rows


def parse(body):
    return re.search(r"#t=([\w-]+)", body).group(1), re.search(r"code: (\d{6})", body).group(1)


async def setup_env(monkeypatch):
    await ensure_tables()
    setv(monkeypatch, "M51_VERIFY_MAIL_MODE", "outbox")
    setv(monkeypatch, "PUBLIC_APP_URL", "http://localhost:3000")


@DB
@pytest.mark.asyncio
async def test_anti_enumeration_identical_answers_and_limits(monkeypatch):
    await setup_env(monkeypatch)
    ip, known, who = new_ip(), addr(), ids()
    async with client_for(ip=ip) as c:
        a = await req(c, who, known)
        assert a.status_code == 200 and len(await outbox_for(known)) == 1
        outs = [a.json()]
        outs.append((await req(c, ids(), addr(), consent=False)).json())               # no consent: nothing stored or sent
        assert await outbox_for("nobody") == []
        e2 = addr()
        outs.append((await req(c, ids(), e2)).json())
        for _ in range(3):                                                             # per-address limit (3/h): still the same answer
            outs.append((await req(c, ids(), known)).json())
        assert len(await outbox_for(known)) == 3, "4th and 5th request must be silently dropped"
        v = ids()
        for _ in range(6):                                                              # per-visitor limit (5/h)
            outs.append((await req(c, v, addr())).json())
        assert all(o == outs[0] for o in outs) and set(outs[0]) == {"status", "message"}
        assert known not in str(outs)                                                  # the address is never echoed
        bad = await c.post(f"{PUB}/request", json={**who, "email": "not-an-email", "consent": True})
        assert bad.status_code == 422


@DB
@pytest.mark.asyncio
async def test_per_ip_limit_returns_429_independent_of_address(monkeypatch):
    await setup_env(monkeypatch)
    setv(monkeypatch, "M51_VERIFY_IP_PER_HOUR", 3)
    ip = new_ip()
    async with client_for(ip=ip) as c:
        codes = [(await req(c, ids(), addr())).status_code for _ in range(5)]
    assert codes == [200, 200, 200, 429, 429]
    async with client_for(ip=new_ip()) as other:                                       # another network is unaffected
        assert (await req(other, ids(), addr())).status_code == 200


@DB
@pytest.mark.asyncio
async def test_link_flow_binding_single_use_and_personalization(monkeypatch):
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMContact, WebEvent, WebIdentity
    from app.models.m51_seo import M51VisitorVerification
    from app.services import crm_lead_capture_service as lead
    from app.services import web_analytics_service as wa
    await setup_env(monkeypatch)
    email, who = addr(), ids()
    async with AsyncSessionLocal() as db:
        db.add(CRMContact(full_name="Amina Wanjiru", email=email))
        await wa.record_consent(db, who["visitor"], True, False)        # analytics yes, marketing not yet
        await db.commit()
    async with client_for(ip=new_ip()) as c:
        await req(c, who, email)
        (row,) = await outbox_for(email)
        token, code = parse(row.body)
        assert row.channel == "OUTBOX" and "http://localhost:3000/verify-email#t=" in row.body and row.to_email == email
        async with AsyncSessionLocal() as db:
            v = (await db.execute(select(M51VisitorVerification).where(M51VisitorVerification.email_hash == __import__("app.services.m51_visitor_verify_service", fromlist=["x"])._h("em", email)))).scalar_one()
            assert token not in (v.token_hash, v.code_hash) and code not in v.code_hash and len(v.token_hash) == 64     # hashed at rest
            assert await lead.known_values(db, who["visitor"]) == {}                      # not verified yet: no personalization
        # bound to the browser: another session / another visitor cannot use the link
        other_s = (await c.post(f"{PUB}/confirm", json={**who, "session": uuid.uuid4().hex, "token": token})).json()
        other_v = (await c.post(f"{PUB}/confirm", json={**ids(), "token": token})).json()
        assert other_s == other_v == {"verified": False}
        assert (await c.post(f"{PUB}/status", json={"visitor": who["visitor"]})).json() == {"verified": False}
        ok = (await c.post(f"{PUB}/confirm", json={**who, "token": token})).json()
        assert ok == {"verified": True} and email not in str(ok)
        assert (await c.post(f"{PUB}/confirm", json={**who, "token": token})).json() == {"verified": False}     # single use
        assert (await c.post(f"{PUB}/status", json={"visitor": who["visitor"]})).json() == {"verified": True}
    async with AsyncSessionLocal() as db:
        ident = await db.get(WebIdentity, wa.hashed("v", who["visitor"]))
        assert ident.verified_at is not None and ident.email == email
        assert await wa.verified_email(db, who["visitor"]) == email
        assert (await lead.known_values(db, who["visitor"])).get("contact_person_name") == "Amina Wanjiru"       # form shortening input
        ev = (await db.execute(select(WebEvent).where(WebEvent.visitor_hash == wa.hashed("v", who["visitor"]), WebEvent.name == "visitor_email_verified"))).scalars().all()
        assert len(ev) == 1                                                            # analytics consent was given
        v = (await db.execute(select(M51VisitorVerification).where(M51VisitorVerification.visitor_hash == wa.hashed("v", who["visitor"])))).scalar_one()
        assert v.email is None and v.consumed_at is not None                           # address wiped after use
    assert await outbox_for(email) == []                                               # link and code deleted with it


@DB
@pytest.mark.asyncio
async def test_no_analytics_event_without_consent_and_no_cross_account_merge(monkeypatch):
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMContact, WebEvent
    from app.services import web_analytics_service as wa
    await setup_env(monkeypatch)
    email, a, b = addr(), ids(), ids()
    async with AsyncSessionLocal() as db:
        db.add(CRMContact(full_name="Neema Otieno", email=email))
        await db.commit()
    async with client_for(ip=new_ip()) as c:
        for who in (a, b):
            await req(c, who, email)
        rows = await outbox_for(email)
        assert len(rows) == 2
        ta, _ = parse(rows[0].body)
        assert (await c.post(f"{PUB}/confirm", json={**b, "token": ta})).json() == {"verified": False}    # A's link is useless for B
        assert (await c.post(f"{PUB}/confirm", json={**a, "token": ta})).json() == {"verified": True}
        assert (await c.post(f"{PUB}/status", json={"visitor": b["visitor"]})).json() == {"verified": False}  # B is not merged into A
    async with AsyncSessionLocal() as db:
        n = (await db.execute(select(WebEvent).where(WebEvent.visitor_hash == wa.hashed("v", a["visitor"])))).scalars().all()
        assert n == []                                                                 # no analytics consent: no event
        cs = (await db.execute(text("select count(*) from crm_contacts where lower(email)=:e"), {"e": email})).scalar()
        assert cs == 1


@DB
@pytest.mark.asyncio
async def test_code_path_attempts_expiry_and_revocation(monkeypatch):
    from app.db.session import AsyncSessionLocal
    from app.models.m51_seo import M51VisitorVerification
    from app.services import m51_visitor_verify_service as vv
    from app.services import web_analytics_service as wa
    await setup_env(monkeypatch)
    ip = new_ip()
    async with client_for(ip=ip) as c:
        # correct code, wrong address / wrong visitor
        e1, w1 = addr(), ids()
        await req(c, w1, e1)
        _, code1 = parse((await outbox_for(e1))[0].body)
        assert (await c.post(f"{PUB}/confirm", json={**w1, "email": addr(), "code": code1})).json() == {"verified": False}
        assert (await c.post(f"{PUB}/confirm", json={**ids(), "email": e1, "code": code1})).json() == {"verified": False}
        assert (await c.post(f"{PUB}/confirm", json={**w1, "email": e1, "code": code1})).json() == {"verified": True}
        # five wrong guesses revoke the challenge, even the right code afterwards
        e2, w2 = addr(), ids()
        await req(c, w2, e2)
        _, code2 = parse((await outbox_for(e2))[0].body)
        wrong = "000000" if code2 != "000000" else "111111"
        for _ in range(5):
            assert (await c.post(f"{PUB}/confirm", json={**w2, "email": e2, "code": wrong})).json() == {"verified": False}
        assert (await c.post(f"{PUB}/confirm", json={**w2, "email": e2, "code": code2})).json() == {"verified": False}
        # expiry
        e3, w3 = addr(), ids()
        await req(c, w3, e3)
        t3, _ = parse((await outbox_for(e3))[0].body)
        async with AsyncSessionLocal() as db:
            await db.execute(text("update m51_visitor_verifications set expires_at=:t where email_hash=:h"),
                             {"t": datetime.now(timezone.utc) - timedelta(minutes=1), "h": vv._h("em", e3)})
            await db.commit()
        assert (await c.post(f"{PUB}/confirm", json={**w3, "token": t3})).json() == {"verified": False}
        # revocation: visitor withdraws; staff revokes by address; pending links die
        e4, w4 = addr(), ids()
        await req(c, w4, e4)
        t4, _ = parse((await outbox_for(e4))[0].body)
        assert (await c.post(f"{PUB}/confirm", json={**w4, "token": t4})).json()["verified"] is True
        assert (await c.post(f"{PUB}/revoke", json={"visitor": w4["visitor"]})).json() == {"revoked": True}
        assert (await c.post(f"{PUB}/status", json={"visitor": w4["visitor"]})).json() == {"verified": False}
        e5, w5 = addr(), ids()
        await req(c, w5, e5)
        t5, _ = parse((await outbox_for(e5))[0].body)
        await req(c, w5, e5)
        async with AsyncSessionLocal() as db:
            u = await staff(db, "mk", ("marketing.edit",))
            viewer = await staff(db, "vw", ("marketing.view",))
            await db.commit()
        async with client_for(u) as s, client_for(viewer) as vw:
            assert (await vw.post(f"{STAFF}/revoke", json={"email": e5})).status_code == 403
            assert (await vw.get(f"{STAFF}/outbox")).status_code == 403
            assert (await s.post(f"{STAFF}/revoke", json={"email": e5})).status_code == 200
        assert (await c.post(f"{PUB}/confirm", json={**w5, "token": t5})).json() == {"verified": False}
        assert await outbox_for(e5) == []
        # withdrawing marketing consent later also ends personalization
        e6, w6 = addr(), ids()
        await req(c, w6, e6)
        t6, _ = parse((await outbox_for(e6))[0].body)
        await c.post(f"{PUB}/confirm", json={**w6, "token": t6})
        async with AsyncSessionLocal() as db:
            assert await wa.verified_email(db, w6["visitor"]) == e6
            await wa.record_consent(db, w6["visitor"], False, False)
            await db.commit()
            assert await wa.verified_email(db, w6["visitor"]) is None


@DB
@pytest.mark.asyncio
async def test_safe_fallback_when_mail_is_off_or_not_local(monkeypatch):
    from app.db.session import AsyncSessionLocal
    from app.models.m51_seo import M51VisitorVerification
    from app.services import m51_visitor_verify_service as vv
    await setup_env(monkeypatch)
    async with client_for(ip=new_ip()) as c:
        base = (await req(c, ids(), addr())).json()
        setv(monkeypatch, "M51_VERIFY_MAIL_MODE", "off")
        e1 = addr()
        assert (await req(c, ids(), e1)).json() == base and await outbox_for(e1) == []
        setv(monkeypatch, "M51_VERIFY_MAIL_MODE", "mailpit")
        setv(monkeypatch, "M51_MAILPIT_HOST", "smtp.real-provider.example.com")          # a real server is never contacted
        e2 = addr()
        assert (await req(c, ids(), e2)).json() == base and await outbox_for(e2) == []
        async with AsyncSessionLocal() as db:
            row = (await db.execute(select(M51VisitorVerification).where(M51VisitorVerification.email_hash == vv._h("em", e2)))).scalar_one()
            assert row.revoked_at is not None and row.email is None                       # nothing pending: visitor stays unverified
        setv(monkeypatch, "M51_MAILPIT_HOST", "127.0.0.1")
        setv(monkeypatch, "M51_MAILPIT_PORT", 1)                                         # nothing listens: delivery fails, same answer
        assert (await req(c, ids(), addr())).json() == base


@DB
@pytest.mark.asyncio
async def test_outbox_staff_view_and_purge(monkeypatch):
    from app.db.session import AsyncSessionLocal
    await setup_env(monkeypatch)
    e = addr()
    async with client_for(ip=new_ip()) as c:
        await req(c, ids(), e, locale="tr")
    async with AsyncSessionLocal() as db:
        u = await staff(db, "mk", ("marketing.edit",))
        await db.commit()
    async with client_for(u) as s:
        box = (await s.get(f"{STAFF}/outbox")).json()
        mine = [m for m in box if m["to"] == e]
        assert mine and mine[0]["subject"].startswith("E-posta") and "#t=" in mine[0]["body"]
        assert "deleted" in (await s.post(f"{STAFF}/purge")).json()
