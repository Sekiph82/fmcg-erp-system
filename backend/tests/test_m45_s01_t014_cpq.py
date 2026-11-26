"""M45.S01.T014 advanced CPQ and contract lifecycle (DB part needs M45_DB=1).

Synthetic quote → promotions (tiered scheme) → multi-step approval (levels, different people, editor refused, send
blocked until complete) → password-protected share link → readiness → accepted → contract from a template →
renewal quote created once → subscription invoice billed by payment link with reminder schedule → credit-note
verification; signature providers: LOCAL active, others NOT_CONFIGURED; quote report.
"""
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest

from app.services import cpq_service as cpq

DB = pytest.mark.skipif(os.environ.get("M45_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M45_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def test_signature_providers():
    assert cpq.SIGNATURE_PROVIDERS["LOCAL"] == "ACTIVE" and cpq.SIGNATURE_PROVIDERS["DOCUSIGN"] == "NOT_CONFIGURED"


def _user(perms=(), su=False):
    from app.core.access_control import has_permission  # noqa: F401
    roles = [SimpleNamespace(name="r", is_active=True, access_scopes=[],
                             permissions=[SimpleNamespace(code=c, is_active=True) for c in perms])]
    return SimpleNamespace(id=uuid.uuid4(), username=f"u{uuid.uuid4().hex[:4]}", is_superuser=su, roles=roles, access_scopes=[])


@DB
@pytest.mark.asyncio
async def test_cpq_lifecycle(monkeypatch):
    from sqlalchemy import func, select
    from app.core.security import hash_password
    from app.db.session import AsyncSessionLocal
    from app.main import app
    from app.models.cpq import BillingAttempt, ContractRenewal, ContractTemplate
    from app.models.crm import CRMDocumentLink
    from app.models.master import Product
    from app.models.promotions import PromoRuleLine, PromoScheme, RewardType, SchemeStatus, SchemeType, TriggerBasis
    from app.models.quotation import Quotation, QuotationLine, QuoteStatus
    from app.models.returns_mgmt import ReturnLine, ReturnOrder
    from app.models.sales import Customer, Invoice, InvoiceLine, InvoiceStatus, SalesOrder, SOStatus
    from app.models.subscription import SubscriptionGenerationLog, SubscriptionTemplate
    from app.services import crm_document_service as docs
    s = uuid.uuid4().hex[:5]
    async with AsyncSessionLocal() as db:
        prod = (await db.execute(select(Product).limit(1))).scalars().first()
        cust = Customer(code=f"CPQ-{s}", name="POVU CPQ Outlet", currency="KES", email=f"cpq{s}@povu-demo.test", credit_limit=Decimal("100000"))
        db.add(cust)
        await db.flush()
        db.add(PromoScheme(scheme_code=f"TIER-{s}", scheme_name="POVU 10+ cartons", scheme_type=SchemeType.TIERED_DISCOUNT,
                           status=SchemeStatus.ACTIVE, valid_from=date.today() - timedelta(days=1), valid_to=date.today() + timedelta(days=30),
                           priority_rank=1, stackable=True))
        await db.flush()
        sch = (await db.execute(select(PromoScheme).where(PromoScheme.scheme_code == f"TIER-{s}"))).scalar_one()
        db.add(PromoRuleLine(scheme_id=sch.id, trigger_basis=TriggerBasis.SKU, trigger_item_id=prod.id, min_trigger_qty=Decimal("10"),
                             reward_type=RewardType.PERCENT_DISCOUNT, reward_percent=Decimal("5")))
        maker = _user(("sales.edit",))
        from app.models.user import User
        db.add(User(id=maker.id, username=maker.username, email=f"{maker.username}@povu-demo.test", full_name="Maker",
                    hashed_password=hash_password(uuid.uuid4().hex), is_active=True))
        q = Quotation(quote_no=f"QT-{s}", customer_id=cust.id, status=QuoteStatus.DRAFT, quote_date=date.today(), currency="KES",
                      created_by_id=maker.id)
        db.add(q)
        await db.flush()
        db.add(QuotationLine(quote_id=q.id, line_no=1, product_id=prod.id, qty=Decimal("20"), unit_price=Decimal("1000"),
                             discount_pct=Decimal("0.28"), tax_rate=Decimal("0.16")))
        await db.flush()
        qid = q.id
        # promotions on the quote
        ev = await cpq.evaluate_promotions(db, qid, apply=True)
        assert any(a["scheme_code"] == f"TIER-{s}" for a in ev["applied"])
        q = await cpq._quote(db, qid)
        assert Decimal(q.discount_pct) > 0
        # multi-step approval: 28%+ needs level 1 (sales.approve) and level 2 (finance.approve)
        st = await cpq.approval_state(db, q)
        assert [l["level"] for l in st["levels"]] == [1, 2] and not st["complete"]
        with pytest.raises(cpq.CPQError):
            await cpq.ensure_levels(db, q, "send it")
        with pytest.raises(cpq.CPQError):
            await cpq.approve_level(db, qid, SimpleNamespace(**{**maker.__dict__}))                    # the price setter
        mgr, fin = _user(("sales.approve",)), _user(("finance.approve",))
        with pytest.raises(cpq.CPQError):
            await cpq.approve_level(db, qid, fin)                                                     # level 1 first
        await cpq.approve_level(db, qid, mgr)
        with pytest.raises(cpq.CPQError):
            await cpq.approve_level(db, qid, mgr)                                                     # same person again
        st = await cpq.approve_level(db, qid, fin)
        assert st["complete"]
        await cpq.ensure_levels(db, q, "send it")
        q.lines[0].discount_pct = Decimal("0.60")                          # raised after approval (e.g. PATCH)
        with pytest.raises(cpq.CPQError):
            await cpq.ensure_levels(db, q, "send it")
        await cpq.approve_level(db, qid, mgr)                              # stale approvals are dropped: approve again
        await cpq.approve_level(db, qid, fin)
        await cpq.ensure_levels(db, q, "send it")
        # readiness: credit and stock
        r = await cpq.readiness(db, qid)
        assert r["credit"]["ok"] and r["approvals"]["complete"] and "stock" in r
        # password-protected share link
        q.status = QuoteStatus.SENT
        link, token = await docs.create_link(db, q, None, 7, "buyer")
        link.password_hash = hash_password("povu-secret")
        await db.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test") as c:
        assert (await c.get(f"/api/v1/public/documents/{token}")).status_code == 401
        assert (await c.get(f"/api/v1/public/documents/{token}", headers={"X-Doc-Password": "wrong-one"})).status_code == 401
        ok = await c.get(f"/api/v1/public/documents/{token}", headers={"X-Doc-Password": "povu-secret"})
        assert ok.status_code == 200 and ok.json()["number"] == f"QT-{s}"
    async with AsyncSessionLocal() as db:
        q = await cpq._quote(db, qid)
        q.status, q.accepted_at = QuoteStatus.ACCEPTED, datetime.now(timezone.utc)
        tpl = ContractTemplate(name=f"Supply {s}", clauses=[{"title": "Prices", "text": "As in quotation {quote_no} for {customer}: {total}."}],
                               term_months=1, auto_renew=True, renewal_notice_days=60)
        db.add(tpl)
        await db.flush()
        ct = await cpq.contract_from_quote(db, qid, tpl.id, maker)
        assert f"QT-{s}" in ct.notes and "POVU CPQ Outlet" in ct.notes and ct.auto_renew
        assert await cpq.renewals_tick(db) >= 1
        ren = (await db.execute(select(ContractRenewal).where(ContractRenewal.contract_id == ct.id))).scalar_one()
        assert ren.renewal_quote_id and (await db.get(Quotation, ren.renewal_quote_id)).quote_no.startswith(f"QT-{s}-R")
        before = (await db.execute(select(func.count()).select_from(Quotation))).scalar_one()
        await cpq.renewals_tick(db)
        assert (await db.execute(select(func.count()).select_from(Quotation))).scalar_one() == before          # once only
        # recurring billing on a subscription order
        so = SalesOrder(order_no=f"SO-SUB-{s}", customer_id=cust_id(q), order_date=date.today(), requested_delivery_date=date.today(),
                        status=SOStatus.INVOICED, currency="KES")
        db.add(so)
        await db.flush()
        tmpl = SubscriptionTemplate(template_code=f"SUB-{s}", template_name="Weekly POVU crates", customer_id=q.customer_id,
                                    recurrence_type="WEEKLY", start_date=date.today(), status="ACTIVE")
        db.add(tmpl)
        await db.flush()
        if True:
            db.add(SubscriptionGenerationLog(template_id=tmpl.id, generated_so_id=so.id, scheduled_date=date.today(), generation_status="GENERATED"))
            inv = Invoice(invoice_no=f"INV-SUB-{s}", so_id=so.id, customer_id=q.customer_id, invoice_date=date.today(),
                          due_date=date.today(), status=InvoiceStatus.ISSUED, currency="KES", total_amount=Decimal("500"), paid_amount=Decimal("0"))
            db.add(inv)
            await db.flush()
            now = datetime.now(timezone.utc)
            assert await cpq.billing_tick(db, now) >= 1
            b = (await db.execute(select(BillingAttempt).where(BillingAttempt.invoice_id == inv.id))).scalar_one()
            assert b.attempts == 1 and b.link_id
            await cpq.billing_tick(db, now + timedelta(hours=1))
            assert b.attempts == 1                                                                   # not before the retry day
            await cpq.billing_tick(db, now + timedelta(days=3, minutes=1))
            assert b.attempts == 2
        # credit note verification
        so2 = SalesOrder(order_no=f"SO-RET-{s}", customer_id=q.customer_id, order_date=date.today(), requested_delivery_date=date.today(),
                         status=SOStatus.INVOICED, currency="KES")
        db.add(so2)
        await db.flush()
        inv2 = Invoice(invoice_no=f"INV-RET-{s}", so_id=so2.id, customer_id=q.customer_id, invoice_date=date.today(), due_date=date.today(),
                       status=InvoiceStatus.ISSUED, currency="KES", total_amount=Decimal("1000"))
        db.add(inv2)
        await db.flush()
        db.add(InvoiceLine(invoice_id=inv2.id, product_id=prod.id, quantity=Decimal("10"), unit_price=Decimal("100"), line_total=Decimal("1000")))
        ro = ReturnOrder(return_no=f"RET-{s}", original_so_id=so2.id, customer_id=q.customer_id, return_date=date.today(), credit_note_no=f"CN-{s}")
        db.add(ro)
        await db.flush()
        db.add(ReturnLine(return_id=ro.id, product_id=prod.id, quantity=Decimal("12"), unit_price=Decimal("120")))
        await db.flush()
        chk = await cpq.verify_credit_note(db, ro.id)
        assert not chk["ok"] and len(chk["issues"]) == 2
        rep = await cpq.report(db)
        assert "by_status" in rep
        await db.rollback()


def cust_id(q):
    return q.customer_id
