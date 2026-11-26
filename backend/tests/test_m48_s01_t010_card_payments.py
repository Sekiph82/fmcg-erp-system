"""M48.S01.T010 card payments (Pesapal API 3.0 hosted checkout) + M-Pesa payment-link race audit.

The adapter talks HTTP to the local Pesapal simulator (tests/provider_sim/card_app.py) through provider_client; DB parts
need M48_DB=1 and the task-owned disposable PostgreSQL. Synthetic POVU data only; no real money, no real provider.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload

from tests.provider_sim.card_app import BASE, SIM_KEY, SIM_SECRET, create_card_app

DB = pytest.mark.skipif(os.environ.get("M48_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M48_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


@pytest.fixture
def sim(monkeypatch):
    from app.core import provider_http
    from app.core.config import settings
    from app.services import card_payment_service as cards
    app = create_card_app()
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "local")
    monkeypatch.setattr(settings, "PUBLIC_API_URL", "http://erp.test")
    monkeypatch.setattr(cards, "_live_flag", lambda: True)          # stands for CARD_PAYMENTS_LIVE_ENABLED=true
    monkeypatch.setattr(cards, "_tokens", {})
    provider_http.set_test_transport(httpx.ASGITransport(app=app))
    yield app
    provider_http.set_test_transport(None)


def _ctl(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://pesapal-sim.test/pesapalv3")


# ── adapter contract (no DB) ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pesapal_adapter_contract(sim, monkeypatch):
    from app.core.config import settings
    from app.services import card_payment_service as cards
    p = cards.Pesapal(BASE, SIM_KEY, SIM_SECRET)
    p.ipn_id = await p.register_ipn("http://erp.test/api/v1/public/card-ipn/pesapal")
    assert sim.state.sim["ipns"][p.ipn_id]["ipn_notification_type"] == "GET"
    o = await p.create_order(reference="POVU-INV-1-AB", amount=Decimal("1250.50"), currency="KES",
                             description="POVU invoice INV-1", callback_url="http://erp.test/return",
                             email="duka@example.com", phone=None, name="Mama Duka")
    assert o["redirect_url"].startswith(BASE) and o["tracking_id"]
    s = await p.status(o["tracking_id"])
    assert (s["state"], s["code"]) == ("INVALID", 0)                       # unpaid: Pesapal reads INVALID (0)
    async with _ctl(sim) as c:
        await c.post("/_sim/pay", json={"order_tracking_id": o["tracking_id"], "outcome": "completed", "after_polls": 2})
    assert (await p.status(o["tracking_id"]))["state"] == "INVALID"         # delayed status
    s = await p.status(o["tracking_id"])
    assert s["state"] == "COMPLETED" and s["amount"] == Decimal("1250.50") and s["confirmation_code"].startswith("SIM")
    # 503 twice, then the third try answers: idempotent reads retry with backoff
    async with _ctl(sim) as c:
        await c.post("/_sim/fail", json={"count": 2})
    assert (await p.status(o["tracking_id"]))["state"] == "COMPLETED"
    # an expired/revoked token: one refresh, then the call goes through
    sim.state.sim["tokens"].clear()
    ok, msg = await p.refund(confirmation_code=s["confirmation_code"], amount=Decimal("100"), username="fin@example.com",
                             remarks="Damaged POVU AllClean 1 L")
    assert ok and "successfully" in msg
    ok, msg = await p.refund(confirmation_code=s["confirmation_code"], amount=Decimal("100"), username="fin@example.com",
                             remarks="again")
    assert not ok and "multiple" in msg                                    # one refund per payment
    # a write is never retried on a 5xx (not idempotent)
    async with _ctl(sim) as c:
        await c.post("/_sim/fail", json={"count": 1})
    with pytest.raises(cards.CardError):
        await p.create_order(reference="POVU-INV-1-CD", amount=Decimal("1"), currency="KES", description="x",
                             callback_url="http://erp.test/return", email="duka@example.com", phone=None, name="x")
    assert sim.state.sim["fail"] == 0
    with pytest.raises(cards.CardError, match="credentials"):
        await cards.Pesapal(BASE, SIM_KEY, "wrong-secret-value").status(o["tracking_id"])
    # egress guard: in local mode a real Pesapal host is refused before any socket opens
    from app.core import provider_http
    provider_http.set_test_transport(None)
    with pytest.raises(cards.CardError) as e:
        await cards.Pesapal(cards.LIVE_BASE, SIM_KEY, SIM_SECRET).status("x" * 10)
    assert e.value.status == 503


# ── DB set-up helpers ────────────────────────────────────────────────────────

async def _actor(db, *codes, name="POVU staff"):
    from app.models.role import Permission, Role
    from app.models.user import User
    perms = []
    for code in codes:
        p = (await db.execute(select(Permission).where(Permission.code == code))).scalar_one_or_none()
        if p is None:
            p = Permission(code=code, module=code.split(".")[0], action=code.split(".", 1)[1], name=code, is_active=True)
            db.add(p)
            await db.flush()
        perms.append(p)
    tag = uuid.uuid4().hex
    u = User(email=f"m48c-{tag[:12]}@example.com", username=f"m48c{tag}", full_name=name,
             hashed_password="synthetic-test-only-not-a-credential", is_active=True, is_superuser=False,
             roles=[Role(name=f"POVU m48 card role {tag}", is_active=True, permissions=perms)])
    db.add(u)
    await db.flush()
    return u.id


async def _as(db, uid):
    from app.models.role import Role
    from app.models.user import User
    u = (await db.execute(select(User).where(User.id == uid).options(
        selectinload(User.roles).selectinload(Role.permissions)))).scalar_one()
    perms = [SimpleNamespace(code=p.code, module=p.module, action=p.action, is_active=True) for r in u.roles for p in r.permissions]
    return SimpleNamespace(id=u.id, username=u.username, email=u.email, full_name=u.full_name, is_superuser=False,
                           is_active=True, access_scopes=[], company_id=None,
                           roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])


async def _world(total="5000.00", credit_limit="8000", allow_partial=True, currency="KES"):
    """Customer + issued invoice with its receivables journal, ledger rules for bank receipts, people, a payment link."""
    from app.db.session import AsyncSessionLocal, engine
    from app.models.finance import AccountingPeriod, AccountingPostingRule, AccountType, ChartOfAccount, PeriodStatus
    from app.models.sales import Customer, CustomerChannel, Invoice, InvoiceStatus, SalesOrder
    from app.services import payment_link_service as pls
    from app.services import sales_service as ss
    assert engine.url.port == 25432 and engine.url.host == "127.0.0.1", "only the disposable gate database"
    s = uuid.uuid4().hex[:8]
    today = date.today()
    async with AsyncSessionLocal() as db:
        w = SimpleNamespace(s=s)
        w.rep = await _actor(db, "sales.view", "sales.create", name="POVU Sales Rep")
        w.fin1 = await _actor(db, "finance.view", "finance.create", "finance.approve", name="POVU Finance Officer")
        w.fin2 = await _actor(db, "finance.view", "finance.approve", name="POVU Finance Manager")
        w.viewer = await _actor(db, "sales.view", name="POVU Viewer")
        ar = ChartOfAccount(code=f"CAR{s}", name="POVU trade receivables", account_type=AccountType.ASSET, currency=currency)
        rev = ChartOfAccount(code=f"CRV{s}", name="POVU sales revenue", account_type=AccountType.REVENUE, currency=currency)
        bank = ChartOfAccount(code=f"CBK{s}", name="POVU card clearing (Pesapal)", account_type=AccountType.ASSET, currency=currency)
        db.add_all([ar, rev, bank])
        await db.flush()
        await db.execute(update(AccountingPostingRule).where(AccountingPostingRule.source_event.in_(
            ("SALES_INVOICE_ISSUED", "CUSTOMER_PAYMENT_RECEIVED_BANK"))).values(is_active=False))
        db.add_all([AccountingPostingRule(source_module="sales", source_event="SALES_INVOICE_ISSUED", rule_name=f"inv {s}",
                                          debit_account_id=ar.id, credit_account_id=rev.id, priority=1, is_active=True),
                    AccountingPostingRule(source_module="sales", source_event="CUSTOMER_PAYMENT_RECEIVED_BANK",
                                          rule_name=f"bank {s}", credit_account_id=ar.id, clearing_account_id=bank.id,
                                          priority=1, is_active=True)])
        if not await db.scalar(select(AccountingPeriod.id).where(AccountingPeriod.period_ym == today.strftime("%Y-%m"))):
            db.add(AccountingPeriod(period_ym=today.strftime("%Y-%m"), period_start=today.replace(day=1),
                                    period_end=(today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1),
                                    status=PeriodStatus.OPEN, notes="Synthetic M48 period."))
        cust = Customer(code=f"C48-{s}", name=f"Mama Duka {s}", channel=CustomerChannel.WHOLESALE, currency=currency,
                        email=f"duka-{s}@example.com", credit_limit=Decimal(credit_limit))
        db.add(cust)
        await db.flush()
        so = SalesOrder(order_no=f"SO-C48-{s}", customer_id=cust.id, order_date=today, requested_delivery_date=today, currency=currency)
        db.add(so)
        await db.flush()
        inv = Invoice(invoice_no=f"INV-C48-{s}", so_id=so.id, customer_id=cust.id, currency=currency, invoice_date=today,
                      due_date=today + timedelta(days=30), status=InvoiceStatus.ISSUED, subtotal=Decimal(total),
                      total_amount=Decimal(total), notes="POVU AllClean 1 L x 50 (synthetic)")
        db.add(inv)
        await db.flush()
        await ss._post_sales_journal(db, source_event="SALES_INVOICE_ISSUED", source_id=inv.id, source_ref=inv.invoice_no,
                                     entry_date=today, description="POVU invoice", amount=Decimal(total), currency=currency,
                                     debit_lines=[(ar.id, Decimal(total), "AR")], credit_lines=[(rev.id, Decimal(total), "Sales")],
                                     user_id=w.fin1)
        link, token = await pls.create(db, inv.id, w.rep, 14, allow_partial)
        await db.commit()
        w.ar, w.bank, w.inv, w.cust, w.link, w.token = ar.id, bank.id, inv.id, cust.id, link.id, token
    return w


async def _balance(db, account_id) -> Decimal:
    from app.models.finance import JournalEntry, JournalLine, JournalStatus
    return Decimal((await db.execute(select(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), 0))
                                     .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
                                     .where(JournalLine.account_id == account_id, JournalEntry.status == JournalStatus.POSTED))).scalar_one())


class Api:
    """Staff + public routers on a bare app; get_current_user overridden per call (RBAC still checked)."""

    def __init__(self):
        from fastapi import FastAPI
        from app.api.v1.endpoints import card_payments_public, payment_links
        from app.core.deps import get_current_user
        self.who = None
        app = FastAPI()
        app.include_router(payment_links.router, prefix="/api/v1/payment-links")
        app.include_router(payment_links.public, prefix="/api/v1/public/pay")
        app.include_router(card_payments_public.router, prefix="/api/v1/public/card-ipn")
        app.dependency_overrides[get_current_user] = lambda: self.who
        self.c = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test")

    async def as_(self, uid, method, url, **kw):
        from app.db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            self.who = await _as(db, uid)
        return await self.c.request(method, url, **kw)


async def _reset_config():
    from app.db.session import AsyncSessionLocal
    from app.models.m48_payments import CardProviderConfig
    async with AsyncSessionLocal() as db:
        await db.execute(CardProviderConfig.__table__.delete())
        await db.commit()


async def _setup_provider(api: Api, w, live=True):
    await _reset_config()
    env = "LIVE" if live else "SANDBOX"
    r = await api.as_(w.fin1, "PUT", "/api/v1/payment-links/card/config",
                      json={"environment": env, "consumer_key": SIM_KEY, "consumer_secret": SIM_SECRET, "base_url": BASE})
    assert r.status_code == 200, r.text
    r = await api.as_(w.fin1, "POST", "/api/v1/payment-links/card/config/register-ipn")
    assert r.status_code == 200 and r.json()["ipn_registered"], r.text
    if live:
        assert (await api.as_(w.fin1, "POST", "/api/v1/payment-links/card/config/request-live")).status_code == 200
        r = await api.as_(w.fin1, "POST", "/api/v1/payment-links/card/config/approve-live")
        assert r.status_code == 403                                             # the requester cannot approve
        r = await api.as_(w.fin2, "POST", "/api/v1/payment-links/card/config/approve-live")
        assert r.status_code == 200 and r.json()["mode"] == "LIVE", r.text
    return r.json()


async def _unthrottle(pid):
    from app.db.session import AsyncSessionLocal
    from app.models.m48_payments import CardPayment
    async with AsyncSessionLocal() as db:
        await db.execute(update(CardPayment).where(CardPayment.id == pid).values(last_checked_at=None))
        await db.commit()


async def _pay(sim, pid, outcome="completed", after=0, **kw):
    from app.db.session import AsyncSessionLocal
    from app.models.m48_payments import CardPayment
    async with AsyncSessionLocal() as db:
        tid = (await db.get(CardPayment, pid)).order_tracking_id
    async with _ctl(sim) as c:
        await c.post("/_sim/pay", json={"order_tracking_id": tid, "outcome": outcome, "after_polls": after, **kw})
    return tid


async def _ipn(api, tid):
    r = await api.c.get("/api/v1/public/card-ipn/pesapal", params={"OrderTrackingId": tid, "OrderNotificationType": "IPNCHANGE"})
    assert r.status_code == 200
    return r.json()


async def _collections(inv_id):
    from app.db.session import AsyncSessionLocal
    from app.models.field_ops import CashCollection
    async with AsyncSessionLocal() as db:
        return (await db.execute(select(CashCollection).where(CashCollection.invoice_id == inv_id))).scalars().all()


# ── DB tests ─────────────────────────────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_success_pending_duplicate_ipn_and_gl_exactly_once(sim):
    from app.api.v1.endpoints import collections as collections_api
    from app.db.session import AsyncSessionLocal
    from app.models.m48_payments import CardPayment, CardProviderConfig
    from app.models.payments_hub import PaymentLink
    from app.models.sales import Invoice, InvoiceStatus
    from app.services import card_payment_service as cards
    w = await _world()
    api = Api()
    view = await _setup_provider(api, w)
    assert view["disabled_reasons"] == [] and "consumer_secret" not in str(view)
    async with AsyncSessionLocal() as db:
        cfg = await cards.config(db)
        assert cfg.consumer_secret_stored.startswith("enc:") and SIM_SECRET not in cfg.consumer_secret_stored
    page = (await api.c.get(f"/api/v1/public/pay/{w.token}")).json()
    assert page["providers"]["card"] == "LIVE" and page["amount_due"] == "5000.00"
    r = await api.c.post(f"/api/v1/public/pay/{w.token}/card", json={})
    assert r.status_code == 200 and r.json()["redirect_url"].startswith(BASE) and r.json()["simulated"] is False, r.text
    async with AsyncSessionLocal() as db:
        pid = (await db.execute(select(CardPayment.id).where(CardPayment.link_id == w.link))).scalar_one()
    # the open checkout reserves the balance
    assert (await api.c.get(f"/api/v1/public/pay/{w.token}")).json()["amount_due"] == "0.00"
    tid = await _pay(sim, pid, after=2)
    assert (await _ipn(api, tid))["status"] == 200
    async with AsyncSessionLocal() as db:
        p = await db.get(CardPayment, pid)
        assert (p.status, p.settlement, p.notifications) == ("PENDING", "NONE", 1)   # pending: provider not final yet
    await _unthrottle(pid)
    await _ipn(api, tid)
    assert len(await _collections(w.inv)) == 1
    # replays: immediate (throttled), after the window, concurrent IPNs, concurrent forced re-queries
    await _ipn(api, tid)
    await _unthrottle(pid)
    await _ipn(api, tid)
    await _unthrottle(pid)
    await asyncio.gather(*[_ipn(api, tid) for _ in range(4)])

    async def forced():
        async with AsyncSessionLocal() as db:
            await cards.refresh(db, pid, force=True)
            await db.commit()
    await asyncio.gather(forced(), forced(), forced())
    cols = await _collections(w.inv)
    assert len(cols) == 1 and cols[0].status == "PENDING" and cols[0].amount == Decimal("5000.00")
    assert cols[0].method == "BANK_TRANSFER" and cols[0].client_ref == f"card:{tid}"
    async with AsyncSessionLocal() as db:
        p = await db.get(CardPayment, pid)
        assert (p.status, p.settlement, p.collection_id) == ("COMPLETED", "COLLECTION", cols[0].id)
        assert p.confirmation_code.startswith("SIM") and p.notifications >= 8
        assert (await db.get(PaymentLink, w.link)).status == "PAID"
        assert (await db.get(Invoice, w.inv)).paid_amount == 0              # not money in the books until finance confirms
        rec = await cards.reconciliation(db, w.inv)
        assert rec["credit"]["outstanding"] == "5000.0000" and rec["credit"]["available"] == "3000.0000"
        assert rec["card_payments"][0]["collection"]["posted"] is False
    # finance confirms once → GL once
    async with AsyncSessionLocal() as db:
        fin2 = await _as(db, w.fin2)
        assert (await collections_api.confirm(cols[0].id, db, fin2))["status"] == "CONFIRMED"
    async with AsyncSessionLocal() as db:
        fin2 = await _as(db, w.fin2)
        with pytest.raises(Exception):
            await collections_api.confirm(cols[0].id, db, fin2)                # second confirm refused
    await _unthrottle(pid)
    await _ipn(api, tid)                                                        # late replay after posting: no-op
    async with AsyncSessionLocal() as db:
        inv = await db.get(Invoice, w.inv)
        assert inv.status == InvoiceStatus.PAID and inv.paid_amount == Decimal("5000")
        assert await _balance(db, w.ar) == 0 and await _balance(db, w.bank) == Decimal("5000")
        rec = await cards.reconciliation(db, w.inv)
        assert rec["credit"]["outstanding"] == "0" and rec["card_payments"][0]["collection"]["posted"] is True
    assert len(await _collections(w.inv)) == 1
    # an IPN for an order we never issued: no provider query, documented ack with status 500 (Pesapal retries)
    calls = len(sim.state.sim["calls"])
    assert (await _ipn(api, "unknown-order-0000"))["status"] == 500 and len(sim.state.sim["calls"]) == calls


@DB
@pytest.mark.asyncio
async def test_decline_invalid_expiry_and_late_callback(sim):
    from app.db.session import AsyncSessionLocal
    from app.models.m48_payments import CardPayment
    from app.services import card_payment_service as cards
    from app.services import payment_link_service as pls
    w = await _world(total="6000.00")
    api = Api()
    await _setup_provider(api, w)
    ids = []
    for amt in ("2000", "2000", "2000"):
        r = await api.as_(w.rep, "POST", f"/api/v1/payment-links/{w.link}/card", json={"amount": amt})
        assert r.status_code == 201 and r.json()["redirect_url"], r.text
        ids.append(uuid.UUID(r.json()["id"]))
    r = await api.as_(w.rep, "POST", f"/api/v1/payment-links/{w.link}/card", json={"amount": "1"})
    assert r.status_code == 422                                                # nothing left: all reserved
    declined, abandoned, late = ids
    tid = await _pay(sim, declined, "failed")
    await _ipn(api, tid)
    r = await api.as_(w.rep, "POST", f"/api/v1/payment-links/card-payments/{abandoned}/refresh")
    assert r.json()["status"] == "PENDING"
    async with AsyncSessionLocal() as db:
        assert (await db.get(CardPayment, declined)).status == "FAILED"
        past = datetime.now(timezone.utc) - timedelta(minutes=31)
        await db.execute(update(CardPayment).where(CardPayment.id.in_([abandoned, late])).values(created_at=past))
        await db.commit()
    r = await api.as_(w.rep, "POST", f"/api/v1/payment-links/card-payments/{abandoned}/refresh")
    assert r.json()["status"] == "INVALID"                                     # never paid within the window
    async with AsyncSessionLocal() as db:
        assert await pls.expire_stale(db) >= 1
        await db.commit()
        assert (await db.get(CardPayment, late)).status == "EXPIRED"
    assert (await api.c.get(f"/api/v1/public/pay/{w.token}")).json()["amount_due"] == "6000.00"   # reservations released
    # the "expired" checkout is paid after all: late callback still settles (money moved)
    tid = await _pay(sim, late)
    await _ipn(api, tid)
    async with AsyncSessionLocal() as db:
        p = await db.get(CardPayment, late)
        assert (p.status, p.settlement) == ("COMPLETED", "COLLECTION")
    # someone pays the rest, then a stale checkout is paid too: more than the balance → finance review, no collection
    r = await api.as_(w.rep, "POST", f"/api/v1/payment-links/{w.link}/card", json={"amount": "4000"})
    rest = uuid.UUID(r.json()["id"])
    await _ipn(api, await _pay(sim, rest))
    tid = await _pay(sim, abandoned)
    await _unthrottle(abandoned)
    await _ipn(api, tid)
    async with AsyncSessionLocal() as db:
        p = await db.get(CardPayment, abandoned)
        assert (p.status, p.settlement) == ("COMPLETED", "NEEDS_REVIEW")
        assert p.collection_id is None
    cols = await _collections(w.inv)
    assert sorted(c.amount for c in cols) == [Decimal("2000.00"), Decimal("4000.00")]


@DB
@pytest.mark.asyncio
async def test_partial_full_only_currency_and_amount_mismatch(sim):
    from app.db.session import AsyncSessionLocal
    from app.models.m48_payments import CardPayment
    from app.models.payments_hub import PaymentLink
    w = await _world(total="3000.00")
    api = Api()
    await _setup_provider(api, w)
    r = await api.c.post(f"/api/v1/public/pay/{w.token}/card", json={"amount": "1500.25", "email": "duka@example.com"})
    assert r.status_code == 200 and r.json()["amount"] == "1500.25", r.text
    assert (await api.c.get(f"/api/v1/public/pay/{w.token}")).json()["amount_due"] == "1499.75"
    assert (await api.c.post(f"/api/v1/public/pay/{w.token}/card", json={"amount": "1.005"})).status_code == 422
    assert (await api.c.post(f"/api/v1/public/pay/{w.token}/card", json={"amount": "2000"})).status_code == 422
    # provider reports another amount than the order: no booking, finance review
    async with AsyncSessionLocal() as db:
        pid = (await db.execute(select(CardPayment.id).where(CardPayment.link_id == w.link))).scalar_one()
    await _ipn(api, await _pay(sim, pid, amount=15.0))
    async with AsyncSessionLocal() as db:
        p = await db.get(CardPayment, pid)
        assert (p.status, p.settlement, p.collection_id) == ("COMPLETED", "NEEDS_REVIEW", None)
        assert "15.00" in p.status_description
    # full-amount-only link refuses a partial amount
    w2 = await _world(total="3000.00", allow_partial=False)
    r = await api.as_(w2.rep, "POST", f"/api/v1/payment-links/{w2.link}/card", json={"amount": "1000"})
    assert r.status_code == 422 and "full amount" in r.text
    # link currency no longer matches the invoice → refused before any provider call
    async with AsyncSessionLocal() as db:
        await db.execute(update(PaymentLink).where(PaymentLink.id == w2.link).values(currency="USD"))
        await db.commit()
    calls = len(sim.state.sim["calls"])
    r = await api.as_(w2.rep, "POST", f"/api/v1/payment-links/{w2.link}/card", json={})
    assert r.status_code == 422 and "Currency mismatch" in r.text and len(sim.state.sim["calls"]) == calls
    # an invoice in a currency the card account does not settle
    w3 = await _world(total="3000.00", currency="UGX")
    r = await api.as_(w3.rep, "POST", f"/api/v1/payment-links/{w3.link}/card", json={})
    assert r.status_code == 422 and "KES, USD" in r.text


@DB
@pytest.mark.asyncio
async def test_refund_two_person_after_posting_and_on_unposted_collection(sim):
    from app.api.v1.endpoints import collections as collections_api
    from app.db.session import AsyncSessionLocal
    from app.models.finance import JournalEntry
    from app.models.field_ops import CashCollection
    from app.models.m48_payments import CardPayment, CardRefund
    from app.models.payments_hub import PaymentLink
    from app.models.sales import Invoice, InvoiceStatus
    w = await _world(total="5000.00")
    api = Api()
    await _setup_provider(api, w)
    r = await api.as_(w.rep, "POST", f"/api/v1/payment-links/{w.link}/card", json={"amount": "3000"})
    posted = uuid.UUID(r.json()["id"])
    r = await api.as_(w.rep, "POST", f"/api/v1/payment-links/{w.link}/card", json={"amount": "2000"})
    unposted = uuid.UUID(r.json()["id"])
    for pid in (posted, unposted):
        await _ipn(api, await _pay(sim, pid))
    async with AsyncSessionLocal() as db:
        col = (await db.get(CardPayment, posted)).collection_id
        await collections_api.confirm(col, db, await _as(db, w.fin2))
    async with AsyncSessionLocal() as db:
        assert (await db.get(Invoice, w.inv)).paid_amount == Decimal("3000")
    # request: finance.create; a sales rep or viewer cannot; amount bounded
    url = f"/api/v1/payment-links/card-payments/{posted}/refund"
    assert (await api.as_(w.rep, "POST", url, json={"amount": "3000", "reason": "Damaged cartons"})).status_code == 403
    assert (await api.as_(w.fin1, "POST", url, json={"amount": "3000.01", "reason": "Damaged cartons"})).status_code == 422
    r = await api.as_(w.fin1, "POST", url, json={"amount": "3000", "reason": "Damaged POVU AllClean cartons"})
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    assert (await api.as_(w.fin1, "POST", url, json={"amount": "1", "reason": "again"})).status_code == 409   # one per payment
    assert (await api.as_(w.fin1, "POST", f"/api/v1/payment-links/card-refunds/{rid}/approve")).status_code == 403
    assert (await api.as_(w.rep, "POST", f"/api/v1/payment-links/card-refunds/{rid}/approve")).status_code == 403
    assert sim.state.sim["refunds"] == []                                     # nothing sent before approval
    r = await api.as_(w.fin2, "POST", f"/api/v1/payment-links/card-refunds/{rid}/approve")
    assert r.status_code == 200 and r.json()["status"] == "SUBMITTED", r.text
    assert sim.state.sim["refunds"][0]["amount"] == "3000.00"
    # provider effects the refund → REVERSED on the next status query → refund journal once, AR reopened
    for _ in range(3):
        r = await api.as_(w.fin1, "POST", f"/api/v1/payment-links/card-payments/{posted}/refresh")
        assert r.status_code == 200
    async with AsyncSessionLocal() as db:
        p, ref = await db.get(CardPayment, posted), (await db.execute(select(CardRefund).where(CardRefund.card_payment_id == posted))).scalar_one()
        assert (p.status, p.settlement, ref.status) == ("REVERSED", "REFUNDED", "COMPLETED")
        assert (await db.execute(select(func.count()).select_from(JournalEntry).where(
            JournalEntry.source_event == "CUSTOMER_CARD_REFUND", JournalEntry.source_id == posted))).scalar_one() == 1
        inv = await db.get(Invoice, w.inv)
        assert inv.paid_amount == 0 and inv.status == InvoiceStatus.ISSUED
        assert await _balance(db, w.ar) == Decimal("5000") and await _balance(db, w.bank) == 0
        assert (await db.get(PaymentLink, w.link)).status == "ACTIVE"
    # partial refund of a payment whose collection finance has not confirmed yet: the collection shrinks, no journal
    r = await api.as_(w.fin1, "POST", f"/api/v1/payment-links/card-payments/{unposted}/refund",
                      json={"amount": "500", "reason": "Short delivery of POVU Hand Wash Powder"})
    rid2 = r.json()["id"]
    assert (await api.as_(w.fin2, "POST", f"/api/v1/payment-links/card-refunds/{rid2}/approve")).json()["status"] == "SUBMITTED"
    await api.as_(w.fin1, "POST", f"/api/v1/payment-links/card-payments/{unposted}/refresh")
    async with AsyncSessionLocal() as db:
        p = await db.get(CardPayment, unposted)
        c = await db.get(CashCollection, p.collection_id)
        assert (p.status, c.status, c.amount) == ("REVERSED", "PENDING", Decimal("1500.00"))
        assert p.settlement == "COLLECTION"                                    # partially refunded, rest still to confirm
    # reject path
    w2 = await _world(total="1000.00")
    await _setup_provider(api, w2)
    r = await api.as_(w2.rep, "POST", f"/api/v1/payment-links/{w2.link}/card", json={})
    pid = uuid.UUID(r.json()["id"])
    await _ipn(api, await _pay(sim, pid))
    rid3 = (await api.as_(w2.fin1, "POST", f"/api/v1/payment-links/card-payments/{pid}/refund",
                          json={"amount": "100", "reason": "Customer asked"})).json()["id"]
    assert (await api.as_(w2.fin2, "POST", f"/api/v1/payment-links/card-refunds/{rid3}/reject")).json()["status"] == "REJECTED"
    assert (await api.as_(w2.fin2, "POST", f"/api/v1/payment-links/card-refunds/{rid3}/approve")).status_code == 409


@DB
@pytest.mark.asyncio
async def test_sandbox_payments_never_reach_collections_or_ledger(sim):
    from app.db.session import AsyncSessionLocal
    from app.models.m48_payments import CardPayment
    from app.models.payments_hub import PaymentLink
    w = await _world(total="1200.00")
    api = Api()
    view = await _setup_provider(api, w, live=False)
    assert view["mode"] == "SIMULATED" and any("Sandbox" in x for x in view["disabled_reasons"])
    r = await api.c.post(f"/api/v1/public/pay/{w.token}/card", json={})
    assert r.json()["simulated"] is True and "no real money" in r.json()["message"]
    async with AsyncSessionLocal() as db:
        pid = (await db.execute(select(CardPayment.id).where(CardPayment.link_id == w.link))).scalar_one()
    await _ipn(api, await _pay(sim, pid))
    async with AsyncSessionLocal() as db:
        assert (await db.get(CardPayment, pid)).settlement == "TEST_SETTLED"
        assert (await db.get(PaymentLink, w.link)).status == "TEST_PAID"
    assert await _collections(w.inv) == []
    # LIVE credentials without the second approver stay SIMULATED, with the reason shown
    await _reset_config()
    await api.as_(w.fin1, "PUT", "/api/v1/payment-links/card/config",
                  json={"environment": "LIVE", "consumer_key": SIM_KEY, "consumer_secret": SIM_SECRET, "base_url": BASE})
    v = (await api.as_(w.fin1, "POST", "/api/v1/payment-links/card/config/register-ipn")).json()
    assert v["mode"] == "SIMULATED" and any("requested" in x for x in v["disabled_reasons"])
    # only the official host or a local simulator may be configured
    r = await api.as_(w.fin1, "PUT", "/api/v1/payment-links/card/config",
                      json={"environment": "LIVE", "consumer_key": SIM_KEY, "consumer_secret": SIM_SECRET,
                            "base_url": "https://evil.example.com/v3"})
    assert r.status_code == 422


@DB
@pytest.mark.asyncio
async def test_rbac_on_card_routes(sim):
    w = await _world(total="800.00")
    api = Api()
    await _setup_provider(api, w)
    base = "/api/v1/payment-links"
    assert (await api.as_(w.viewer, "GET", f"{base}/card/config")).status_code == 200
    assert (await api.as_(w.viewer, "GET", f"{base}/reconciliation", params={"invoice_id": str(w.inv)})).status_code == 200
    assert (await api.as_(w.viewer, "POST", f"{base}/{w.link}/card", json={})).status_code == 403
    assert (await api.as_(w.rep, "PUT", f"{base}/card/config", json={"environment": "SANDBOX", "consumer_key": SIM_KEY,
                                                                      "consumer_secret": SIM_SECRET})).status_code == 403
    assert (await api.as_(w.rep, "POST", f"{base}/card/config/request-live")).status_code == 403
    r = await api.as_(w.rep, "POST", f"{base}/{w.link}/card", json={})
    assert r.status_code == 201
    pid = r.json()["id"]
    assert (await api.as_(w.viewer, "POST", f"{base}/card-payments/{pid}/refresh")).status_code == 403
    assert (await api.as_(w.rep, "POST", f"{base}/card-payments/{pid}/refresh")).status_code == 200
    # the real application requires a login on every staff route
    from app.main import app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test") as c:
        assert (await c.get(f"{base}/card/config")).status_code == 401
        assert (await c.post(f"{base}/card-refunds/{uuid.uuid4()}/approve")).status_code == 401


# ── M-Pesa payment-link races (M48.S01.T010 audit) ───────────────────────────

def _mpesa_cb(checkout, receipt):
    item = [{"Name": "MpesaReceiptNumber", "Value": receipt}, {"Name": "Amount", "Value": 1}]
    return {"Body": {"stkCallback": {"MerchantRequestID": "m", "CheckoutRequestID": checkout, "ResultCode": 0,
                                     "ResultDesc": "ok", "CallbackMetadata": {"Item": item}}}}


@DB
@pytest.mark.asyncio
async def test_mpesa_double_callback_and_concurrent_stk_post_once(monkeypatch, sim):
    import random
    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    from app.main import app
    from app.models.payments_hub import PaymentLinkAttempt
    from app.services import mpesa_daraja_service as daraja
    await _reset_config()
    monkeypatch.setattr(settings, "MPESA_CALLBACK_SECRET", "cb-secret")
    pushes = []

    async def live_push(phone, amount, reference, description="Payment"):
        await asyncio.sleep(0.05)                                              # widen the race window
        cid = f"ws_CO_M48_{uuid.uuid4().hex[:12]}"
        pushes.append(cid)
        return cid, "MR1", {"ResponseCode": "0", "CheckoutRequestID": cid}
    monkeypatch.setattr(daraja, "_stk_push_request", live_push)
    w = await _world(total="2500.00")
    ip = f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=(ip, 50000)), base_url="http://erp.test") as c:
        rs = await asyncio.gather(*[c.post(f"/api/v1/public/pay/{w.token}/mpesa", json={"phone": "0712345678"}) for _ in range(3)])
        assert sorted(r.status_code for r in rs) == [200, 422, 422], [r.text for r in rs]   # the balance is reserved once
        assert len(pushes) == 1
        cb = _mpesa_cb(pushes[0], f"QM{uuid.uuid4().hex[:8].upper()}")
        rs = await asyncio.gather(*[c.post("/api/v1/integrations/mpesa/callback?token=cb-secret", json=cb) for _ in range(4)])
        assert all(r.status_code == 200 for r in rs)
        assert (await c.post("/api/v1/integrations/mpesa/callback?token=cb-secret", json=cb)).status_code == 200
    cols = await _collections(w.inv)
    assert len(cols) == 1 and cols[0].amount == Decimal("2500.00") and cols[0].method == "MPESA"
    async with AsyncSessionLocal() as db:
        a = (await db.execute(select(PaymentLinkAttempt).where(PaymentLinkAttempt.link_id == w.link))).scalar_one()
        assert a.status == "SETTLED" and a.collection_id == cols[0].id
