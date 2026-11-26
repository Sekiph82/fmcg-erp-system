"""M50.S01.T013 independent-review fixes: one regression test per finding (S1-S9, I1-I2, C1-C2, M1).
Unit tests run anywhere; DB tests need M50_DB=1 and a disposable PostgreSQL."""
import asyncio
import base64
import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import httpcore
import httpx
import pytest
from fastapi import HTTPException

from tests.m50_s01_common import staff

DB = pytest.mark.skipif(os.environ.get("M50_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M50_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def _S():
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from app.db.session import engine
    return async_sessionmaker(engine, expire_on_commit=False)()


def _now():
    return datetime.now(timezone.utc)


# ── S1: DNS rebinding ────────────────────────────────────────────────────────

class _Inner(httpcore.AsyncNetworkBackend):
    def __init__(self):
        self.targets = []

    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        self.targets.append(host)
        return object()

    async def sleep(self, seconds):
        pass


@pytest.mark.asyncio
async def test_s1_resolve_once_validate_all_connect_to_the_validated_ip():
    from app.core import provider_http as ph
    calls = []

    async def rebinding(host, port):             # public on the first lookup, internal afterwards
        calls.append(host)
        return ["93.184.216.34"] if len(calls) == 1 else ["10.0.0.5"]
    inner = _Inner()
    b = ph.PinnedBackend(inner)
    ph.set_resolver(rebinding)
    try:
        await b.connect_tcp("rebind.example.org", 443)
        assert inner.targets == ["93.184.216.34"] and len(calls) == 1          # one lookup, TCP target is the validated IP
        with pytest.raises(ph.EgressBlocked):                                  # the next lookup answers with an internal address
            await b.connect_tcp("rebind.example.org", 443)
        assert inner.targets == ["93.184.216.34"]
        for bad in (["93.184.216.34", "169.254.169.254"], ["127.0.0.1"], ["::1"], ["192.168.1.9"], []):
            async def mixed(host, port, bad=bad):
                return bad
            ph.set_resolver(mixed)
            with pytest.raises(ph.EgressBlocked):
                await b.connect_tcp("evil.example.org", 443)
        with pytest.raises(ph.EgressBlocked):                                  # an IP literal is checked too
            await b.connect_tcp("10.1.2.3", 80)
        assert inner.targets == ["93.184.216.34"]
    finally:
        ph.set_resolver(None)


@pytest.mark.asyncio
async def test_s1_live_client_refuses_a_rebound_name_and_keeps_the_host_header(monkeypatch):
    from app.core import provider_http as ph
    from app.core.config import settings
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "live")
    monkeypatch.setattr(ph, "check_egress", lambda url: None)                   # the pre-flight lookup said "public"
    ph.set_test_transport(None)

    async def internal(host, port):
        return ["10.0.0.5"]
    ph.set_resolver(internal)
    try:
        async with ph.provider_client() as c:
            assert isinstance(c._transport._pool._network_backend, ph.PinnedBackend)
            with pytest.raises(ph.EgressBlocked):
                await c.get("https://rebind.example.org/x")
        # positive path against a real socket: connect to the pinned IP, Host header keeps the original name
        seen = {}

        async def handle(reader, writer):
            seen["req"] = (await reader.readuntil(b"\r\n\r\n")).decode()
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok")
            await writer.drain()
            writer.close()
        srv = await asyncio.start_server(handle, "127.0.0.1", 0)
        port = srv.sockets[0].getsockname()[1]

        async def pinned(host, p):
            return ["127.0.0.1"]
        ph.set_resolver(pinned)
        monkeypatch.setattr(ph, "_public", lambda ip: True)                     # the loopback stands in for a public host
        async with ph.provider_client() as c:
            r = await c.get(f"http://pin.example.org:{port}/hello")
        srv.close()
        assert r.status_code == 200 and f"Host: pin.example.org:{port}" in seen["req"]
    finally:
        ph.set_resolver(None)


@pytest.mark.asyncio
async def test_s1_local_mode_and_test_transport_are_not_pinned(monkeypatch):
    from app.core import provider_http as ph
    from app.core.config import settings
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "local")
    ph.set_test_transport(None)
    async with ph.provider_client() as c:
        assert not isinstance(c._transport._pool._network_backend, ph.PinnedBackend)
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "live")
    tr = httpx.MockTransport(lambda r: httpx.Response(200, text="sim"))
    ph.set_test_transport(tr)
    try:
        async with ph.provider_client() as c:
            assert c._transport is tr
    finally:
        ph.set_test_transport(None)


# ── S4: SSO role mapping and privileged 2FA ──────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_s4_role_mapping_cannot_hand_out_a_privileged_role_through_sso():
    from sqlalchemy import func, select
    from app.models.role import Role
    from app.models.user import User, user_role
    from app.services import sso_service as sso
    tag = uuid.uuid4().hex[:6]
    email = f"sso-{tag}@povu-demo.test"
    async with _S() as db:
        admin = (await db.execute(select(Role).where(Role.name == "admin"))).scalar_one_or_none()
        if admin is None:
            admin = Role(name="admin", is_active=True)
            db.add(admin)
        plain = Role(name=f"plain-{tag}", is_active=True)
        u = User(username=f"sso-{tag}", email=email, full_name="Sso", hashed_password="x", is_active=True)
        db.add_all([plain, u])
        await db.commit()
        uid = u.id
    async with _S() as db:
        with pytest.raises(sso.SSOError) as e:
            await sso.login_user(db, email, ["g-admin"], {"g-admin": "admin"})
        assert e.value.audit_reason == "privileged_2fa_required"
        await db.commit()
    async with _S() as db:
        assert (await db.execute(select(func.count()).select_from(user_role).where(user_role.c.user_id == uid))).scalar_one() == 0
        user = await sso.login_user(db, email, ["g-plain"], {"g-plain": f"plain-{tag}"})      # a harmless mapping still works
        assert [r.name for r in user.roles] == [f"plain-{tag}"]
        await db.rollback()


# ── S2 / S3: proposals ───────────────────────────────────────────────────────

async def _order_sync(db, s, owner=None, editor=None, name="so"):
    from app.models.data_sync import SyncDefinition
    from app.models.master import Product
    from app.models.sales import Customer
    from app.services import m50_sync
    mapping = [{"target": t, "source": t, "transforms": []} for t in
               ("order_no", "customer_code", "order_date", "requested_delivery_date", "sku", "quantity", "unit_price")]
    sync = SyncDefinition(name=f"{name} {s}", source_kind="WEBHOOK", target="sales_orders", key_field="order_no", mapping=mapping,
                          history=[], created_by=owner)
    db.add(sync)
    await db.flush()
    if editor:
        await m50_sync.set_options(db, sync.id, {"mapping_editor": editor})
    return sync


def _rows(s, qty="10"):
    return [{"order_no": f"SO-{s}", "customer_code": f"OC-{s}", "order_date": "2026-11-30", "requested_delivery_date": "2026-12-05",
             "sku": f"POVU-ALC-{s}", "quantity": qty, "unit_price": "340"}]


async def _catalogue(db, s):
    from app.models.master import Product
    from app.models.sales import Customer
    db.add_all([Customer(code=f"OC-{s}", name="Duka Order"), Product(sku=f"POVU-ALC-{s}", name="POVU AllClean 1 L", category="HOUSEHOLD",
                                                                      selling_price=Decimal("350"))])


@DB
@pytest.mark.asyncio
async def test_s2_automation_proposals_are_owned_by_the_sync_owner_who_cannot_approve():
    from sqlalchemy import select
    from app.api.v1.endpoints import data_sync as api
    from app.models.m50_data_sso import SyncProposal
    from app.services import data_sync_service as dss
    from app.services import m50_sync
    s = uuid.uuid4().hex[:5].upper()
    perms = ("sales.create", "sales.create_all")
    async with _S() as db:
        await _catalogue(db, s)
        owner, editor, other = [await staff(db, t, perms) for t in ("owner", "editor", "other")]
        sync = await _order_sync(db, s, owner=owner.username)
        await db.commit()
        # webhook run: the proposal belongs to the sync's creator, not to the string "webhook"
        await dss.run_in(db, sync, _rows(s), dry_run=False, user="webhook", trigger="WEBHOOK", full_snapshot=False)
        await db.commit()
        p = (await db.execute(select(SyncProposal).where(SyncProposal.sync_id == sync.id))).scalar_one()
        assert p.proposed_by == owner.username
        h = api.ApproveIn(payload_hash=m50_sync.payload_hash(p))
        with pytest.raises(HTTPException) as e:
            await api.approve_proposal(p.id, h, db, owner)
        assert e.value.status_code == 403
        await db.rollback()
        await db.refresh(p)
        await db.refresh(sync)
        # the last mapping editor may not approve either (and, for new runs, answers for the proposal)
        await m50_sync.set_options(db, sync.id, {"mapping_editor": editor.username})
        await db.commit()
        with pytest.raises(HTTPException) as e:
            await api.approve_proposal(p.id, h, db, editor)
        assert e.value.status_code == 403
        await db.rollback()
        await db.refresh(p)
        await db.refresh(sync)
        assert await m50_sync.accountable(db, sync, "scheduler") == editor.username
        assert await m50_sync.accountable(db, sync, "webhook") == editor.username
        assert await m50_sync.accountable(db, sync, "alice") == "alice"
        # replay keeps the original proposer: a run replayed by someone else is staged under the accountable owner
        s2 = uuid.uuid4().hex[:5].upper()
        await _catalogue(db, s2)
        await db.commit()
        r = await dss.run_in(db, sync, _rows(s2), dry_run=False, user=other.username, trigger="REPLAY", full_snapshot=False,
                             proposer=await m50_sync.accountable(db, sync, "webhook"))
        await db.commit()
        p2 = (await db.execute(select(SyncProposal).where(SyncProposal.sync_id == sync.id, SyncProposal.key == f"SO-{s2}"))).scalar_one()
        assert p2.proposed_by == editor.username
        # a third person with the right may approve
        out = await api.approve_proposal(p.id, h, db, other)
        assert out["status"] == "APPLIED"


@DB
@pytest.mark.asyncio
async def test_s3_a_changed_pending_payload_cannot_be_approved_with_the_old_view():
    from sqlalchemy import select
    from app.api.v1.endpoints import data_sync as api
    from app.models.m50_data_sso import SyncProposal
    from app.services import data_sync_service as dss
    from app.services import m50_sync
    s = uuid.uuid4().hex[:5].upper()
    async with _S() as db:
        await _catalogue(db, s)
        proposer, approver = [await staff(db, t, ("sales.create", "sales.create_all")) for t in ("prop", "appr")]
        sync = await _order_sync(db, s, owner=proposer.username)
        await db.commit()
        await dss.run_in(db, sync, _rows(s, "10"), dry_run=False, user=proposer.username, full_snapshot=False)
        await db.commit()
        p = (await db.execute(select(SyncProposal).where(SyncProposal.sync_id == sync.id))).scalar_one()
        seen = m50_sync.payload_hash(p)
        assert api._prop(p)["payload_hash"] == seen
        await dss.run_in(db, sync, _rows(s, "999"), dry_run=False, user=proposer.username, full_snapshot=False)   # re-run overwrites it
        await db.commit()
        await db.refresh(p)
        assert p.status == "PENDING" and m50_sync.payload_hash(p) != seen
        with pytest.raises(HTTPException) as e:
            await api.approve_proposal(p.id, api.ApproveIn(payload_hash=seen), db, approver)
        assert e.value.status_code == 409 and "changed" in e.value.detail
        await db.rollback()
        await db.refresh(p)
        with pytest.raises(HTTPException) as e:                          # a missing/garbage hash never approves
            await api.approve_proposal(p.id, api.ApproveIn(payload_hash="0" * 64), db, approver)
        assert e.value.status_code == 409
        await db.rollback()
        await db.refresh(p)
        out = await api.approve_proposal(p.id, api.ApproveIn(payload_hash=m50_sync.payload_hash(p)), db, approver)
        assert out["status"] == "APPLIED"


# ── S5 / S9: add-in refresh race and absolute lifetime ───────────────────────

def _pkce():
    v = secrets.token_urlsafe(48)
    return v, base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).rstrip(b"=").decode()


async def _grant(db, tag="rep"):
    from urllib.parse import urlsplit
    from app.core.config import settings
    from app.services import addin_auth_service as aas
    u = await staff(db, tag, (), superuser=True)
    app = urlsplit(settings.PUBLIC_APP_URL)
    v, ch = _pkce()
    a = await aas.authorize(db, u, "outlook", ch, f"{app.scheme}://{app.netloc}", [])
    t = await aas.exchange(db, a["code"], v, "outlook")
    await db.commit()
    return t


@DB
@pytest.mark.asyncio
async def test_s5_parallel_refresh_with_the_just_rotated_token_is_a_race_not_theft():
    from sqlalchemy import select
    from app.models.m50_data_sso import AddinGrant
    from app.services import addin_auth_service as aas
    async with _S() as db:
        t1 = await _grant(db)
        t2 = await aas.refresh(db, t1["refresh_token"])
        await db.commit()
        with pytest.raises(HTTPException) as e:                       # second request with the same (now rotated) token
            await aas.refresh(db, t1["refresh_token"])
        assert e.value.status_code == 409 and e.value.detail["error"] == "refresh_in_progress"
        await db.rollback()
        g = (await db.execute(select(AddinGrant).where(AddinGrant.prev_refresh_hash == aas.h(t1["refresh_token"])))).scalar_one()
        assert g.revoked_at is None
        t3 = await aas.refresh(db, t2["refresh_token"])               # the grant still works with the newest token
        await db.commit()
        # outside the window the same replay is theft: the whole grant is revoked
        g = (await db.execute(select(AddinGrant).where(AddinGrant.refresh_hash == aas.h(t3["refresh_token"])))).scalar_one()
        g.rotated_at = _now() - timedelta(seconds=30)
        await db.commit()
        with pytest.raises(HTTPException) as e:
            await aas.refresh(db, t2["refresh_token"])
        assert e.value.status_code == 401
        await db.refresh(g)
        assert g.revoked_at is not None and g.revoked_reason == "refresh_reuse"


@DB
@pytest.mark.asyncio
async def test_s9_a_grant_dies_after_its_absolute_lifetime_however_often_it_is_used():
    from sqlalchemy import select
    from app.core.config import settings
    from app.models.m50_data_sso import AddinGrant
    from app.services import addin_auth_service as aas
    async with _S() as db:
        t = await _grant(db)
        g = (await db.execute(select(AddinGrant).where(AddinGrant.refresh_hash == aas.h(t["refresh_token"])))).scalar_one()
        g.created_at = _now() - timedelta(days=31)
        await db.commit()
        with pytest.raises(HTTPException) as e:                       # a valid access token stops too
            await aas.authenticate(db, t["access_token"], "addin.read", "outlook", None)
        assert e.value.status_code == 401
        with pytest.raises(HTTPException) as e:
            await aas.refresh(db, t["refresh_token"])
        assert e.value.status_code == 401
        await db.refresh(g)
        assert g.revoked_reason == "max_lifetime"
        t_ok = await _grant(db, "fresh")                              # a young grant is unaffected
        assert (await aas.refresh(db, t_ok["refresh_token"]))["access_token"]
        await db.commit()


def test_s5_s8_clients_are_single_flight_and_the_gmail_card_shows_the_check_code():
    js = (ROOT / "frontend/public/addin/sidebar.js").read_text(encoding="utf-8")
    assert "inflight" in js and "if (inflight) return inflight" in js and "409" in js
    gs = (ROOT / "addins/gmail/Code.gs").read_text(encoding="utf-8")
    assert "LockService" in gs and "Check code" in gs and "state" in gs
    page = (ROOT / "frontend/src/app/addin/authorize/page.tsx").read_text(encoding="utf-8")
    assert "Check code on this page" in page and "Only continue if you just started this" in page


# ── S6: chat safety flood ────────────────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_s6_one_safety_escalation_per_chat_and_a_per_connection_limit(monkeypatch):
    from sqlalchemy import func, select
    from app.models.consumer_complaints import ConsumerComplaint
    from app.services import crm_chat_service as chat
    from app.services import service_agent as sa
    tag = uuid.uuid4().hex[:8]
    ip = f"198.51.100.{secrets.randbelow(200) + 1}"

    async def say(db, sess, n):
        text = f"I got a rash from POVU AllClean 1 L {tag} case {n}"
        r, extra = await sa._escalate_safety(db, sess, None, text, "en")
        await sa._record(db, sess, None, text, "en", "SAFETY", "RULES", "safety", **extra)
        return r

    async def complaints(db):
        return (await db.execute(select(func.count(ConsumerComplaint.id)).where(ConsumerComplaint.description.like(f"%{tag}%")))).scalar_one()
    async with _S() as db:
        user = SimpleNamespace(full_name="V", email=f"v-{tag}@povu-demo.test", portal_account_id=None)
        sess, _ = await chat.start(db, ip=ip, name="v", email=None, consent=False, page_url=None, honeypot=None, portal_user=user)
        for n in range(5):                                        # five safety messages in one chat
            r = await say(db, sess, n)
            assert "stop using" in r.text.lower() and r.handoff    # the visitor always gets the stop-use advice
        assert await complaints(db) == 1
        for i in range(4):                                        # more chats from the same connection (chat start allows 5/h): 3 reports in all
            s2, _ = await chat.start(db, ip=ip, name="v", email=None, consent=False, page_url=None, honeypot=None, portal_user=user)
            await say(db, s2, 100 + i)
        assert await complaints(db) == 3
        await db.commit()


# ── S7: LIKE wildcards in the thread lookup ──────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_s7_thread_lookup_treats_percent_and_underscore_literally(monkeypatch):
    from tests.test_m50_s01_t011_addin import BASE, _deal, _signin, _staff, mini_app

    async def _no(db, user_id):
        return False
    monkeypatch.setattr("app.services.auth_2fa_policy.requires_privileged_2fa", _no)
    tag = uuid.uuid4().hex[:6]
    async with _S() as db:
        user, cookies = await _staff(db, "rep")
        _, deal = await _deal(db, user, f"b-{tag}@povu-demo.test")
        await db.commit()
        deal_id = str(deal.id)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=mini_app()), base_url="http://erp.test") as c:
        tok, _ = await _signin(c, cookies)
        H = {"Authorization": f"Bearer {tok['access_token']}", "X-Addin-Host": "outlook"}
        for thr in (f"t{tag}-a1", f"t{tag}-b2"):
            r = await c.post(f"{BASE}/log-email", headers=H, json={"crm_record_id": deal_id, "subject": "s", "body": "b", "direction": "IN",
                                                                  "message_id": f"m-{thr}@povu-demo.test", "thread_id": thr})
            assert r.status_code == 201, r.text
        for wild in (f"t{tag}%", f"t{tag}-_1", "%"):
            assert (await c.get(f"{BASE}/thread", params={"thread_id": wild}, headers=H)).json() == [], wild
        assert len((await c.get(f"{BASE}/thread", params={"thread_id": f"t{tag}-a1"}, headers=H)).json()) == 1


# ── I1 / I2: AI budget ───────────────────────────────────────────────────────

async def _clean():
    from sqlalchemy import text
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as s:
        for t in ("ai_budget_counters", "ai_budget_reservations", "ai_usage_log"):
            await s.execute(text(f"DELETE FROM {t}"))
        await s.commit()


async def _counters():
    from sqlalchemy import text
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as s:
        rows = (await s.execute(text("SELECT scope_type, scope_id, cap_cost, reserved_cost, spent_cost FROM ai_budget_counters"))).all()
    return {(r[0], r[1]): (Decimal(r[2]), Decimal(r[3]), Decimal(r[4])) for r in rows}


@DB
@pytest.mark.asyncio
async def test_i1_worst_case_is_reserved_before_each_call_and_the_counter_never_passes_the_cap(monkeypatch):
    from app.core.config import settings
    from app.services import agent_budget as bud
    from app.services import agent_service as ags
    await _clean()
    monkeypatch.setattr(settings, "AI_MAX_TOKENS", 1000, raising=False)
    cfg = {"rate_input_per_1k": 0.0, "rate_output_per_1k": 0.2}            # one call can cost up to 0.2
    agent, user = uuid.uuid4(), uuid.uuid4()
    caps = {"company": 100, "user": 100, "agent": 1.0}
    meters = []
    for i in range(8):                                                    # 8 runs, each holds only a small first reservation
        res = await bud.reserve(agent_id=agent, user_id=user, est_cost=Decimal("0.05"), est_tokens=10, caps=caps, key=f"i1-{i}")
        assert res.ok
        meters.append(ags.Meter(SimpleNamespace(id=uuid.uuid4()), SimpleNamespace(id=agent), user, cfg, caps, res))

    async def call(m):
        try:
            await m.before_call("x" * 40)
            return True
        except ags.BudgetError:
            return False
    ok = await asyncio.gather(*[call(m) for m in meters])
    cap, reserved, spent = (await _counters())[("AGENT", str(agent))]
    assert reserved <= cap and sum(ok) == 4 and not all(ok)               # 0.4 held + 4 x 0.15 more = 1.0 fits, the rest are refused BEFORE a call
    # the refused runs hold nothing beyond their first reservation
    assert reserved == Decimal("0.2") * 4 + Decimal("0.05") * 4
    # settle clamps measured spend to the hold; the overage is logged on the reservation, never charged
    r = meters[0].res
    await bud.record_usage(r.id, 5000, Decimal("0.9"))
    assert await bud.settle(r.id)
    c = (await _counters())[("AGENT", str(agent))]
    assert c[2] == meters[0].reserved and c[2] < Decimal("0.9") and c[1] <= c[0]
    from sqlalchemy import text
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as s:
        note = (await s.execute(text("SELECT note FROM ai_budget_reservations WHERE id=:i"), {"i": r.id})).scalar_one()
    assert "OVERAGE" in note


@pytest.mark.asyncio
async def test_i1_a_call_that_cannot_be_reserved_is_never_made():
    from app.services import ai_provider as aip
    p = aip.ScriptedProvider()

    async def veto():
        raise RuntimeError("cap")
    with pytest.raises(RuntimeError):
        await aip.generate_with_retry(p, "x", before_attempt=veto)
    assert p.calls == 0


@DB
@pytest.mark.asyncio
async def test_i2_heartbeat_keeps_a_live_workers_lease_and_only_the_owner_may_renew(monkeypatch):
    from sqlalchemy import text
    from app.db.session import AsyncSessionLocal
    from app.services import agent_budget as bud
    from app.services import agent_service as ags
    await _clean()
    a, u = uuid.uuid4(), uuid.uuid4()
    caps = {"company": 100, "user": 100, "agent": 5.0}
    r = await bud.reserve(agent_id=a, user_id=u, est_cost=Decimal("0.1"), est_tokens=1, caps=caps, key="i2", lease_s=1)
    monkeypatch.setattr(bud, "HEARTBEAT_SECONDS", 0.05)
    beat = asyncio.create_task(ags._heartbeat(r.id))
    await asyncio.sleep(0.4)
    beat.cancel()
    async with AsyncSessionLocal() as s:
        exp = (await s.execute(text("SELECT expires_at FROM ai_budget_reservations WHERE id=:i"), {"i": r.id})).scalar_one()
    assert exp > _now() + timedelta(seconds=600)                            # renewed without any model call
    assert not [x for x in await bud.recover_stuck(_now() + timedelta(seconds=300)) if x["reservation"] == r.id]   # a live worker is not "crashed"
    async with AsyncSessionLocal() as s:                                    # another worker's reservation cannot be renewed by us
        await s.execute(text("UPDATE ai_budget_reservations SET worker_id='other:1' WHERE id=:i"), {"i": r.id})
        await s.commit()
    assert not await bud.heartbeat(r.id)
    # once recovery settled it, the slow original worker's settle is a no-op (and execute_job then discards its result)
    rec = await bud.recover_stuck(_now() + timedelta(days=1))
    assert any(x["reservation"] == r.id for x in rec)
    assert not await bud.settle(r.id) and not await bud.heartbeat(r.id)


# ── C1: concurrent enrichment apply ──────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_c1_two_people_applying_the_same_enrichment_proposal_apply_it_once():
    from sqlalchemy import select
    from app.models.audit_log import AuditLog
    from app.models.m50_prospecting import M50EnrichmentProposal
    from app.models.sales import Customer
    from app.services import m50_enrichment_service as enr
    tag = uuid.uuid4().hex[:6]
    async with _S() as db:
        a1, a2 = await staff(db, "a1", ("crm.edit_all",)), await staff(db, "a2", ("crm.edit_all",))
        cust = Customer(code=f"SYN-{tag}", name="Duka Moja", currency="KES")
        db.add(cust)
        await db.flush()
        p = M50EnrichmentProposal(customer_id=cust.id, provider="pdl", field="region", value="Rift Valley", source_ref="pdl sim", confidence=0.9,
                                  consent_basis="test", expires_at=_now() + timedelta(days=1))
        db.add(p)
        await db.commit()
        pid, cid = p.id, cust.id

    async def go(user):
        async with _S() as db:
            try:
                out = await enr.apply(db, pid, user)
                await asyncio.sleep(0.3)                              # hold the row lock while the other request arrives
                await db.commit()
                return "ok", out
            except enr.EnrichError as e:
                await db.rollback()
                return "err", e.status
    res = await asyncio.gather(go(a1), go(a2))
    assert sorted(r[0] for r in res) == ["err", "ok"] and [r[1] for r in res if r[0] == "err"] == [409]
    async with _S() as db:
        n = (await db.execute(select(AuditLog).where(AuditLog.event_type == "M50_ENRICHMENT_APPLIED", AuditLog.target_id == str(cid)))).scalars().all()
        assert len(n) == 1 and (await db.get(M50EnrichmentProposal, pid)).status == "APPLIED"


# ── C2: Parquet decompression bomb ───────────────────────────────────────────

def test_c2_parquet_total_uncompressed_size_is_capped_from_the_footer(monkeypatch):
    import pyarrow as pa
    from app.services import parquet_service as pqs
    data = pqs.write([{"sku": "POVU-ALC-1L", "note": "x" * 1000} for _ in range(200)], {"sku": pa.string(), "note": pa.string()})
    assert len(data) < 20_000                                         # compresses to almost nothing ...
    rows, info = pqs.read(data)
    assert len(rows) == 200
    monkeypatch.setattr(pqs, "MAX_UNCOMPRESSED_BYTES", 100)           # footer says the columns inflate past the cap
    with pytest.raises(pqs.ParquetError, match="expand"):
        pqs.read(data)


# ── M1: downgrade keeps the consent evidence ─────────────────────────────────

def test_m1_migration_archives_sa_actions_on_downgrade():
    import importlib.util
    spec = importlib.util.spec_from_file_location("m0080", ROOT / "backend/alembic/versions/20261130_0080_m50_ai_data_platform.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert "sa_actions" in m.EVIDENCE and "sa_actions" in m.TABLES and set(m.EVIDENCE) <= set(m.TABLES)
