"""M49 independent-review fixes F1-F12 (regression tests). DB-gated like the other M49 files: M49_DB=1."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from urllib.parse import urlencode

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.db.session import AsyncSessionLocal, engine
from app.services import ads_adapters as ads
from app.services import audience_sync_adapters as ad
from app.services import audience_sync_service as sv
from tests.m48_ads_support import PW, client, control, login, setup_account
from tests.m49_audience_support import M49
from tests.test_m49_s01_t011_audience_lifecycle import (API, approve_and_sync, hashes, make_people, sim, sim_aud)  # noqa: F401
from tests.test_m49_s01_t004_contact_center import _agent, _num, _queue  # noqa: F401


@pytest.fixture(autouse=True)
async def _dispose():
    yield
    await engine.dispose()


async def _synced(provider: str = "meta"):
    """Author/approver clients and a synced audience of 4 consented members."""
    tag = uuid.uuid4().hex[:6]
    p0 = await setup_account(provider)
    ca, cb = client(), client()
    await login(ca, p0["author"])
    await login(cb, p0["approver"])
    emails = await make_people(tag)
    r = await ca.post("/api/v1/audiences", json={"name": f"POVU AllClean buyers {tag}", "require_consent": False,
                                                   "rules": {"all": [{"field": "city", "op": "eq", "value": f"City-{tag}"}]}})
    aid = r.json()["id"]
    sid = (await ca.post(API, json={"audience_id": aid, "account_id": p0["account"]})).json()["id"]
    await approve_and_sync(ca, cb, sid)
    return ca, cb, p0, sid, emails


async def _drained() -> None:
    await asyncio.gather(*list(sv._TASKS))


async def _members(sid: str) -> dict:
    from app.models.m49_audiences import AudienceSyncMember
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(AudienceSyncMember).where(AudienceSyncMember.sync_id == uuid.UUID(sid)))).scalars().all()
        return {m.email_sha256: m.state for m in rows}


# ── F1 ───────────────────────────────────────────────────────────────────────

@M49
@pytest.mark.parametrize("status", ["UNSUBSCRIBED", "COMPLAINED"])
async def test_f1_unsubscribe_path_reaches_the_platform(sim, status):
    from app.models.m49_audiences import AudienceSuppression
    from app.services import crm_outbound_service as outbound
    ca, cb, p0, sid, emails = await _synced("meta")
    async with AsyncSessionLocal() as db:
        await outbound.record_consent(db, emails[0], status, "unsubscribe-link")      # the public link / feedback / reply path
        await db.commit()
        assert await db.get(AudienceSuppression, ads.hash_email(emails[0])) is not None
    await _drained()
    assert set(next(iter((await sim_aud("meta")).values()))["members"]) == hashes(*emails[1:4])
    assert (await _members(sid))[ads.hash_email(emails[0])] == "REMOVED"


@M49
async def test_f1_provider_failure_never_blocks_and_stays_pending(sim, monkeypatch):
    from app.services import crm_outbound_service as outbound

    async def boom(*a, **k):
        raise ads.AdsError("PROVIDER", "down")
    ca, cb, p0, sid, emails = await _synced("google")
    monkeypatch.setattr(ad, "remove", boom)
    async with AsyncSessionLocal() as db:
        await outbound.record_consent(db, emails[0], "UNSUBSCRIBED", "unsubscribe-link")
        await db.commit()                                                          # not blocked
    await _drained()
    assert (await _members(sid))[ads.hash_email(emails[0])] == "PENDING_REMOVE"    # retried by Reconcile; never re-added
    pv = (await ca.get(f"{API}/{sid}/preview")).json()
    assert pv["remove"] == 1 and pv["add"] == 0


# ── F2 ───────────────────────────────────────────────────────────────────────

@M49
async def test_f2_withdrawal_during_sync_is_not_overwritten(sim, monkeypatch):
    from app.services import crm_outbound_service as outbound
    tag = uuid.uuid4().hex[:6]
    p0 = await setup_account("meta")
    ca, cb = client(), client()
    await login(ca, p0["author"])
    await login(cb, p0["approver"])
    emails = await make_people(tag)
    aid = (await ca.post("/api/v1/audiences", json={"name": f"POVU Hand Wash {tag}", "require_consent": False,
                                                      "rules": {"all": [{"field": "city", "op": "eq", "value": f"City-{tag}"}]}})).json()["id"]
    sid = (await ca.post(API, json={"audience_id": aid, "account_id": p0["account"]})).json()["id"]
    real_add, hit = ad.add, []

    async def add_then_withdraw_midflight(*a, **k):
        out = await real_add(*a, **k)               # the provider now holds everyone ...
        async with AsyncSessionLocal() as db:       # ... and consent is withdrawn before the run marks IN_SYNC
            await outbound.record_consent(db, emails[0], "UNSUBSCRIBED", "unsubscribe-link")
            await db.commit()
        hit.append(1)
        return out
    monkeypatch.setattr(ad, "add", add_then_withdraw_midflight)
    await approve_and_sync(ca, cb, sid)
    await _drained()
    assert hit
    assert (await _members(sid))[ads.hash_email(emails[0])] == "REMOVED"
    assert set(next(iter((await sim_aud("meta")).values()))["members"]) == hashes(*emails[1:4])


# ── F3 ───────────────────────────────────────────────────────────────────────

@M49
@pytest.mark.parametrize("verified", [False, True])
async def test_f3_rsvp_reply_needs_verified_sender(monkeypatch, verified):
    from datetime import datetime, timezone
    from app.models.email_integration import EmailAccount, EmailProvider
    from app.services import calendar_series_service as cal
    from app.services import email_mailbox_service as mail
    seen = []

    async def rec(db, ics, frm):
        seen.append(frm)
        return True
    monkeypatch.setattr(cal, "apply_reply", rec)
    s = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        acc = EmailAccount(provider=EmailProvider.SMTP, email_address=f"sales-{s}@povu-demo.test")
        db.add(acc)
        await db.flush()
        p = mail.Parsed(message_id=f"<r-{s}@x.test>", in_reply_to=None, references=[], from_email="buyer@example.com", from_name=None,
                        to=[acc.email_address], cc=[], subject="Accepted", text="", when=datetime.now(timezone.utc),
                        sender_verified=verified, ics_replies=["BEGIN:VCALENDAR"])
        await mail.store(db, acc, p)
        await db.rollback()
    assert bool(seen) is verified


# ── F4 (no DB) ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("byday,ok", [("1MO", True), ("4FR", True), ("-1FR", True), ("5MO", False), ("-2TU", False), ("-5SU", False)])
def test_f4_byday_ordinals_match_what_graph_can_express(byday, ok):
    from app.services import calendar_series_service as cal
    assert bool(cal._BYDAY.match(byday)) is ok


# ── F5 ───────────────────────────────────────────────────────────────────────

@M49
async def test_f5_callbacks_need_view_or_queue_membership():
    from fastapi import HTTPException
    from app.api.v1.endpoints import voice_cc as api
    from app.models.m49_voice import VoiceCallback
    async with AsyncSessionLocal() as db:
        member = await _agent(db, perms=())
        outsider = await _agent(db, perms=())
        viewer = await _agent(db, perms=("crm.view_all",))
        mgr = await _agent(db, perms=("crm.edit_all",))
        q = await _queue(db, [member])
        mine, other = _num(), _num()
        cb_in = VoiceCallback(phone_number=mine, queue_id=q.id, state="PENDING")
        cb_out = VoiceCallback(phone_number=other, queue_id=None, state="PENDING")
        db.add_all([cb_in, cb_out])
        await db.commit()
        cb_in_id, cb_out_id = cb_in.id, cb_out.id
        nums = lambda rows: {r["phone_number"] for r in rows}  # noqa: E731
        assert not nums(await api.list_callbacks("PENDING", db, outsider)) & {mine, other}
        assert nums(await api.list_callbacks("PENDING", db, member)) & {mine, other} == {mine}
        assert {mine, other} <= nums(await api.list_callbacks("PENDING", db, viewer))
        with pytest.raises(HTTPException) as e:
            await api.finish_callback(cb_in_id, api.CallbackDone(outcome="ANSWERED"), db, outsider)
        assert e.value.status_code == 404
        await db.rollback()
        r = await api.finish_callback(cb_in_id, api.CallbackDone(outcome="ANSWERED"), db, member)
        assert r["state"] == "DONE"
        r = await api.finish_callback(cb_out_id, api.CallbackDone(outcome="ANSWERED"), db, mgr)
        assert r["state"] == "DONE"


# ── F6 ───────────────────────────────────────────────────────────────────────

@M49
async def test_f6_personal_email_endpoints_skip_shared_mailboxes():
    """The shared account is excluded for everyone (superusers included: same filter); the registrant is the
    non-superuser here because a superuser login needs 2FA in the test environment."""
    from app.models.email_integration import EmailAccount, EmailProvider
    from app.models.m49_calendar_mail import SharedMailbox
    from app.models.user import User
    from tests.m48_ads_support import make_user
    s = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        name = await make_user(db, ("marketing.view",), "registrant")
        await db.flush()
        uid = (await db.execute(select(User.id).where(User.username == name))).scalar_one()
        shared = EmailAccount(provider=EmailProvider.SMTP, email_address=f"support-{s}@povu-demo.test", created_by_id=uid)
        personal = EmailAccount(provider=EmailProvider.SMTP, email_address=f"me-{s}@povu-demo.test", created_by_id=uid)
        db.add_all([shared, personal])
        await db.flush()
        db.add(SharedMailbox(provider="google", address=f"support-{s}@povu-demo.test", account_id=shared.id))
        await db.commit()
        sid, pid = str(shared.id), str(personal.id)
    async with client() as c:
        await login(c, name)
        r = await c.get("/api/v1/email/accounts")
        assert r.status_code == 200, r.text
        listed = {a["id"] for a in r.json()}
        assert pid in listed and sid not in listed
        assert (await c.delete(f"/api/v1/email/accounts/{sid}")).status_code == 404
        assert (await c.get("/api/v1/email/threads", params={"account_id": sid})).json() == []


# ── F8 ───────────────────────────────────────────────────────────────────────

@M49
async def test_f8_link_view_redacts_ad_objects_for_non_members(sim):
    from app.models.m49_studio import StudioLink
    from app.models.user import User
    from app.services import marketing_studio_service as ms
    tag = uuid.uuid4().hex[:6]
    p0 = await setup_account("meta")
    ca = client()
    await login(ca, p0["author"])
    await make_people(tag)
    aid = (await ca.post("/api/v1/audiences", json={"name": f"POVU AllClean {tag}", "require_consent": False,
                                                      "rules": {"all": [{"field": "city", "op": "eq", "value": f"City-{tag}"}]}})).json()["id"]
    sid = (await ca.post(API, json={"audience_id": aid, "account_id": p0["account"]})).json()["id"]
    link = StudioLink(id=uuid.uuid4(), campaign_id=uuid.uuid4(), kind="AUDIENCE_SYNC", ref_id=uuid.UUID(sid),
                      label="POVU secret list", created_by="x")
    async with AsyncSessionLocal() as db:
        author = (await db.execute(select(User).where(User.username == p0["author"]))).scalar_one()
        intruder = (await db.execute(select(User).where(User.username == p0["intruder"]))).scalar_one()
        seen = await ms.link_view(db, link, author)
        hidden = await ms.link_view(db, link, intruder)
    assert seen["provider"] == "meta" and seen["label"] == "POVU secret list"
    assert hidden["restricted"] and "provider" not in hidden and "secret" not in str(hidden) and hidden["status"] == "RESTRICTED"


# ── F9 (no DB) ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("url,auth", [("https://api.twilio.com/2010-04-01/R.mp3", True),
                                      ("https://api.twilio.com.evil.test/x.mp3", False),
                                      ("https://api.twilio.com@evil.test/x.mp3", False),
                                      ("http://api.twilio.com/x.mp3", False)])
async def test_f9_twilio_credentials_only_to_the_exact_host(monkeypatch, url, auth):
    from app.services import transcription_pipeline_service as tp
    monkeypatch.setattr(tp, "_cfg", lambda k, d=None: {"VOICE_TWILIO_ACCOUNT_SID": "AC", "VOICE_TWILIO_AUTH_TOKEN": "tok"}.get(k, d))
    call = SimpleNamespace(recording_consent=True, recording_url=url, recording_expires_at=None, provider="twilio")

    class DB:
        async def get(self, *_a):
            return call
    seen = {}

    async def fake_download(u, a):
        seen["auth"] = a
        return b"audio"
    monkeypatch.setattr(tp.legacy, "_download", fake_download)
    try:
        await tp._audio_for(DB(), SimpleNamespace(source_type="call", source_id=1))
    except tp.TxError:          # plain http is refused before any download
        assert url.startswith("http://") and not seen
        return
    assert bool(seen["auth"]) is auth


# ── F10 ──────────────────────────────────────────────────────────────────────

def test_f10_signature_counts_duplicate_keys_and_full_values():
    from starlette.datastructures import FormData
    from app.services import voice_carrier as vc
    form = FormData([("CallSid", "CA1"), ("Digits", "1"), ("Digits", "2"), ("Note", "x" * 900)])
    sig = vc.twilio_signature("tok", "https://e.test/p", form)
    plain = base64.b64encode(hmac.new(b"tok", ("https://e.test/p" + "CallSidCA1" + "Digits1" + "Digits2" + "Note" + "x" * 900).encode(),
                                      hashlib.sha1).digest()).decode()
    assert sig == plain


@M49
async def test_f10_webhook_verifies_untruncated_multidict(monkeypatch):
    from tests.provider_sim import voice2_app as v2
    for k, v in v2.sim_settings("http://127.0.0.1:8767").items():
        monkeypatch.setitem(settings.__dict__, k, v)
    form = [("CallSid", "CA" + uuid.uuid4().hex), ("Digits", "1"), ("Digits", "2"), ("Note", "x" * 900)]
    path = "/api/v1/calls/cc/twilio/webhook?" + urlencode({"step": "status"})
    data = "https://erp.povu-demo.test" + path + "".join(k + v for k, v in sorted(form))
    sig = base64.b64encode(hmac.new(v2.AUTH_TOKEN.encode(), data.encode(), hashlib.sha1).digest()).decode()
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient
    from app.api.v1.endpoints import voice_cc
    mini = FastAPI()
    mini.include_router(voice_cc.router, prefix="/api/v1/calls/cc")
    async with AsyncClient(transport=ASGITransport(app=mini), base_url="http://test") as c:
        r = await c.post(path, content=urlencode(form), headers={"X-Twilio-Signature": sig,
                                                                   "Content-Type": "application/x-www-form-urlencoded"})
        assert r.status_code != 403, r.text
        bad = await c.post(path, content=urlencode(form[:-1]), headers={"X-Twilio-Signature": sig,
                                                                         "Content-Type": "application/x-www-form-urlencoded"})
        assert bad.status_code == 403


# ── F11 ──────────────────────────────────────────────────────────────────────

@M49
async def test_f11_unchanged_over_cap_budget_does_not_block_other_edits():
    from fastapi import HTTPException
    from app.api.v1.endpoints import marketing as mk
    from app.models.marketing import Campaign, CampaignType
    from app.schemas.marketing import CampaignUpdate
    from app.services.marketing_studio_service import cap
    big = cap() + Decimal("1000")
    async with AsyncSessionLocal() as db:
        c = Campaign(campaign_code=f"M49F11-{uuid.uuid4().hex[:8]}", campaign_name="POVU AllClean launch",
                     campaign_type=list(CampaignType)[0], start_date=date(2027, 1, 1), end_date=date(2027, 2, 1), budget=big)
        db.add(c)
        await db.commit()
        r = await mk.update_campaign(str(c.id), CampaignUpdate(budget=big, notes="rename only"), db)
        assert r.notes == "rename only" and r.budget == big
        with pytest.raises(HTTPException) as e:
            await mk.update_campaign(str(c.id), CampaignUpdate(budget=big + 1), db)
        assert e.value.status_code == 409


# ── F12 (no DB) ──────────────────────────────────────────────────────────────

def test_f12_meta_adset_times_use_account_zone_or_explicit_utc():
    from app.services import ads_lifecycle_service as lc
    from app.services.ads_lifecycle_service import START, END
    f = {START: "2027-03-01", END: "2027-03-31"}
    node = SimpleNamespace(level="ADSET")
    nairobi = lc.edit_req("meta", "ADSET", "123", f, node, {"tz": "Africa/Nairobi"}).data
    assert nairobi["start_time"] == "2027-03-01T00:00:00+0300" and nairobi["end_time"] == "2027-03-31T23:59:59+0300"
    ny = lc.edit_req("meta", "ADSET", "123", f, node, {"tz": "America/New_York"}).data     # DST: offset follows the date
    assert ny["start_time"].endswith("-0500") and ny["end_time"].endswith("-0400")
    utc = lc.edit_req("meta", "ADSET", "123", f, node, {"tz": None}).data
    assert utc["start_time"] == "2027-03-01T00:00:00Z" and utc["start_time"][:10] == "2027-03-01"


# ── re-review N1-N3 ──────────────────────────────────────────────────────────

@M49
async def test_n1_every_withdrawal_in_one_session_is_drained(sim):
    """Two withdrawals committed in the same session each reach the platform (the drain flag is per commit)."""
    from app.services import crm_outbound_service as outbound
    ca, cb, p0, sid, emails = await _synced("meta")
    async with AsyncSessionLocal() as db:
        await outbound.record_consent(db, emails[0], "UNSUBSCRIBED", "unsubscribe-link")
        await db.commit()
        await _drained()
        await outbound.record_consent(db, emails[1], "UNSUBSCRIBED", "unsubscribe-link")
        await db.commit()
    await _drained()
    m = await _members(sid)
    assert m[ads.hash_email(emails[0])] == "REMOVED" and m[ads.hash_email(emails[1])] == "REMOVED"


@M49
async def test_n2_bounce_is_not_a_withdrawal_and_authorised_resubscribe_lifts(sim):
    from app.models.m49_audiences import AudienceSuppression
    from app.services import crm_outbound_service as outbound
    ca, cb, p0, sid, emails = await _synced("meta")
    async with AsyncSessionLocal() as db:
        await outbound.record_consent(db, emails[2], "BOUNCED", "bounce report")
        await db.commit()
        assert await db.get(AudienceSuppression, ads.hash_email(emails[2])) is None
        await outbound.record_consent(db, emails[3], "UNSUBSCRIBED", "unsubscribe-link")
        await db.commit()
        assert await db.get(AudienceSuppression, ads.hash_email(emails[3])) is not None
        await outbound.record_consent(db, emails[3], "SUBSCRIBED", "signed form", may_lift_unsubscribe=True)
        await db.commit()
        db.expunge_all()
        assert await db.get(AudienceSuppression, ads.hash_email(emails[3])) is None
    await _drained()
    assert (await _members(sid))[ads.hash_email(emails[2])] == "IN_SYNC"


def test_n3_inbox_hides_own_studio_budget_request():
    import inspect
    from app.services import approval_inbox_service as ib
    src = inspect.getsource(ib)
    assert 'key == "studio_budget"' in src and "model.requested_by != user.username" in src
