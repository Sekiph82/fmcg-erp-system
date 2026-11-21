"""M41.S01 on disposable PostgreSQL:
T001 discount approval on quotations and sales orders (limit, waiting/approve/reject, never own document, inbox and
     bell, send/accept/confirm blocked until approved, re-check on change) and the quote -> order unit fix;
T002 the quote signer proves an e-mail on file with a one-time code;
T003 KRA eTIMS item codes on products reach the eTIMS payload and gaps block a live submission."""
from __future__ import annotations

import os
import re
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal, engine

TASK_DB_ENV = "M41_S01_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M41_S01_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m41_s01_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


async def _actor(db, *codes):
    from app.models.role import Permission, Role
    from app.models.user import User

    perms = []
    for code in codes:
        p = (await db.execute(select(Permission).where(Permission.code == code))).scalar_one_or_none()
        if p is None:
            p = Permission(code=code, module=code.split(".")[0], action=code.split(".", 1)[1], name=code, is_active=True)
            db.add(p)
        perms.append(p)
    tag = uuid4().hex
    u = User(email=f"m41-{tag}@example.invalid", username=f"m41{tag}", full_name="POVU Sales",
             hashed_password="synthetic-test-only-not-a-credential", is_active=True, is_superuser=False,
             roles=[Role(name=f"POVU m41 role {tag}", is_active=True, permissions=perms)])
    db.add(u)
    await db.flush()
    return u.id


async def _load(db, uid):
    from app.models.role import Role
    from app.models.user import User

    return (await db.execute(select(User).where(User.id == uid).options(
        selectinload(User.roles).selectinload(Role.permissions), selectinload(User.roles).selectinload(Role.access_scopes),
        selectinload(User.access_scopes)))).scalar_one()


async def _setup(db, tag):
    from app.models.master import Product, ProductCategory
    from app.models.sales import Customer, CustomerChannel

    assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
    assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
    assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
    cust = Customer(code=f"M41-{tag}", name="POVU Duka Westlands", channel=CustomerChannel.RETAIL, currency="KES",
                    email=f"buyer-{tag}@duka.example")
    prod = Product(sku=f"POVU-ALLCLEAN-1L-{tag}", name="POVU AllClean 1 L", category=ProductCategory.HOUSEHOLD,
                   selling_price=Decimal("210"))
    db.add_all([cust, prod])
    await db.flush()
    return cust.id, prod.id


@pytest.mark.asyncio
async def test_quote_discount_approval_and_conversion_units():
    from app.api.v1.endpoints import quotation as api
    from app.models.notifications import Notification
    from app.models.quotation import QuoteStatus
    from app.models.sales import SalesOrder, SOLine
    from app.models.utilities import SystemConfig
    from app.schemas.quotation import QuotationCreate, QuotationLineCreate, QuotationUpdate
    from app.services import approval_inbox_service as inbox

    tag = uuid4().hex[:8].upper()
    async with AsyncSessionLocal() as db:
        cust, prod = await _setup(db, tag)
        rep_id = await _actor(db, "sales.view_all", "sales.create_all", "sales.edit_all", "sales.approve_all", "sales.convert_all")
        mgr_id = await _actor(db, "sales.view_all", "sales.approve_all")
        await db.commit()
        rep, mgr = await _load(db, rep_id), await _load(db, mgr_id)

        def body(line_disc, header=Decimal("0")):
            return QuotationCreate(customer_id=cust, quote_date=date(2026, 11, 21), valid_until=date(2099, 1, 1), currency="KES",
                                   discount_pct=header, lines=[QuotationLineCreate(line_no=1, product_id=prod, qty=Decimal("10"),
                                                                                    unit="CTN", unit_price=Decimal("200"),
                                                                                    discount_pct=line_disc, tax_rate=Decimal("16"))])

        small = await api.create_quote(body(Decimal("5")), db, rep)              # 5 % under the default 10 % limit
        assert small.approval_status is None and small.discount_approval_required is False
        # totals: net 10 x 200 less 5 % = 1900, VAT 16 % = 304, total 2204 (tax was counted twice before)
        assert (small.total_amount, small.tax_amount, small.grand_total) == (Decimal("1900.0000"), Decimal("304.0000"), Decimal("2204.0000"))
        # line 8 % + header 5 % = 12.6 % on the whole quote: above 10 %, though each part is below
        big = await api.create_quote(body(Decimal("8"), Decimal("5")), db, rep)
        assert big.approval_status == "PENDING_DISCOUNT" and big.discount_approval_required is True
        assert big.access.can_discount_approve is False                          # creator never decides

        for call in (lambda: api.send_quote(big.id, db, rep),):                  # cannot be sent while waiting
            with pytest.raises(HTTPException) as e:
                await call()
            assert e.value.status_code == 409 and "approval" in e.value.detail
            await db.rollback()
            rep, mgr = await _load(db, rep_id), await _load(db, mgr_id)
        with pytest.raises(HTTPException) as e:                                  # own document
            await api.approve_discount(big.id, api.DiscountDecisionIn(), db, rep)
        assert e.value.status_code == 403
        await db.rollback()
        rep, mgr = await _load(db, rep_id), await _load(db, mgr_id)

        # inbox and bell: the manager sees it, the creator does not
        mine = await inbox.inbox(db, mgr)
        group = next(g for g in mine["groups"] if g["key"] == "quote_discount")
        assert str(big.id) in [i["id"] for i in group["items"]] and str(small.id) not in [i["id"] for i in group["items"]]
        assert all(g["key"] != "quote_discount" or str(big.id) not in [i["id"] for i in g["items"]]
                   for g in (await inbox.inbox(db, rep))["groups"])
        await inbox.notify_new(db)
        bell = (await db.execute(select(Notification.user_id).where(Notification.reference_type == "approval:quote_discount",
                                                                    Notification.reference_id == str(big.id)))).scalars().all()
        assert str(mgr_id) in bell and str(rep_id) not in bell

        # reject needs a reason; the creator is told; the quote stays blocked until changed
        with pytest.raises(HTTPException) as e:
            await api.reject_discount(big.id, api.DiscountDecisionIn(), db, mgr)
        assert e.value.status_code == 422
        await db.rollback()
        rep, mgr = await _load(db, rep_id), await _load(db, mgr_id)
        out = await api.reject_discount(big.id, api.DiscountDecisionIn(reason="Max 10 % for Westlands"), db, mgr)
        assert out.approval_status == "DISCOUNT_REJECTED"
        told = (await db.execute(select(Notification.message).where(Notification.user_id == str(rep_id),
                                                                    Notification.reference_type == "discount_decision"))).scalars().all()
        assert any("Max 10 %" in m for m in told)
        with pytest.raises(HTTPException) as e:
            await api.send_quote(big.id, db, rep)
        assert e.value.status_code == 409
        await db.rollback()
        rep, mgr = await _load(db, rep_id), await _load(db, mgr_id)

        # the rep changes the discount: asked again (still above), then approved, then sent
        changed = await api.update_quote(big.id, QuotationUpdate(discount_pct=Decimal("4"), lines=body(Decimal("8")).lines), db, rep)
        assert changed.approval_status == "PENDING_DISCOUNT"
        ok = await api.approve_discount(big.id, api.DiscountDecisionIn(), db, mgr)
        assert ok.approval_status == "DISCOUNT_APPROVED" and ok.discount_approved_at is not None
        with pytest.raises(HTTPException) as e:                                  # decided once
            await api.approve_discount(big.id, api.DiscountDecisionIn(), db, mgr)
        assert e.value.status_code == 409
        await db.rollback()
        rep, mgr = await _load(db, rep_id), await _load(db, mgr_id)
        # an edit after approval drops it (the approver saw other numbers)
        again = await api.update_quote(big.id, QuotationUpdate(lines=body(Decimal("9")).lines), db, rep)
        assert again.approval_status == "PENDING_DISCOUNT" and again.discount_approved_at is None
        await api.approve_discount(big.id, api.DiscountDecisionIn(), db, mgr)
        sent = await api.send_quote(big.id, db, rep)
        assert sent.status == QuoteStatus.SENT

        # conversion: percentages become fractions, the header discount is folded in, the decision is carried over
        await api.accept_quote(big.id, db, mgr)
        db.expire_all()   # one test session: drop the line objects replaced by the edits (each request has its own session)
        rep, mgr = await _load(db, rep_id), await _load(db, mgr_id)
        conv = await api.convert_to_so(big.id, db, rep)
        so = (await db.execute(select(SalesOrder).where(SalesOrder.id == conv["so_id"]))).scalar_one()
        line = (await db.execute(select(SOLine).where(SOLine.so_id == so.id))).scalar_one()
        assert line.tax_rate == Decimal("0.1600")
        assert line.discount_pct == Decimal("1") - (Decimal("1") - Decimal("0.09")) * (Decimal("1") - Decimal("0.04"))  # 0.1264
        assert so.approval_status == "DISCOUNT_APPROVED" and so.discount_approved_at is not None
        net = line.ordered_quantity * line.unit_price * (1 - line.discount_pct)
        assert net == Decimal("1747.2000")                                       # 2000 less 12.64 %

        # review fixes: a superuser creator cannot approve their own discount; whoever last changed it cannot either
        from app.models.user import User
        from app.services import discount_approval_service as dsvc
        boss_id = await _actor(db, "sales.view_all", "sales.create_all", "sales.edit_all", "sales.approve_all")
        await db.execute(__import__("sqlalchemy").update(User).where(User.id == boss_id).values(is_superuser=True))
        await db.commit()
        boss = await _load(db, boss_id)
        own = await api.create_quote(body(Decimal("30")), db, boss)
        with pytest.raises(HTTPException) as e:
            await api.approve_discount(own.id, api.DiscountDecisionIn(), db, boss)
        assert e.value.status_code == 403
        await db.rollback()
        rep, mgr = await _load(db, rep_id), await _load(db, mgr_id)
        ed_id = await _actor(db, "sales.view_all", "sales.edit_all", "sales.approve_all")
        await db.commit()
        rep, mgr, ed = await _load(db, rep_id), await _load(db, mgr_id), await _load(db, ed_id)
        other = await api.create_quote(body(Decimal("30")), db, rep)
        await api.update_quote(other.id, QuotationUpdate(lines=body(Decimal("40")).lines), db, ed)   # another approver edits it
        with pytest.raises(HTTPException) as e:
            await api.approve_discount(other.id, api.DiscountDecisionIn(), db, ed)
        assert e.value.status_code == 403
        await db.rollback()
        rep, mgr, ed = await _load(db, rep_id), await _load(db, mgr_id), await _load(db, ed_id)
        assert all(str(other.id) not in [i["id"] for i in g["items"]] for g in (await inbox.inbox(db, ed))["groups"])
        assert any(str(other.id) in [i["id"] for i in g["items"]] for g in (await inbox.inbox(db, mgr))["groups"])
        stale = await db.get(__import__("app.models.quotation", fromlist=["Quotation"]).Quotation, other.id)
        stale.approval_status = dsvc.REJECTED
        stale.discount_approved_at = stale.created_at                            # a leftover approval time never counts
        with pytest.raises(HTTPException):
            dsvc.ensure_approved(stale, "send it")
        await db.rollback()
        rep, mgr = await _load(db, rep_id), await _load(db, mgr_id)

        # the limit is a company setting
        db.add(SystemConfig(key="sales.discount_approval_limit_pct", value="15", description="POVU test limit"))
        await db.commit()
        under = await api.create_quote(body(Decimal("12")), db, rep)
        assert under.approval_status is None


@pytest.mark.asyncio
async def test_sales_order_discount_gate_and_fraction_units():
    from pydantic import ValidationError

    from app.api.v1.endpoints import sales as api
    from app.models.sales import SOStatus
    from app.schemas.sales import SOCreate, SOLineCreate

    tag = uuid4().hex[:8].upper()
    async with AsyncSessionLocal() as db:
        cust, prod = await _setup(db, tag)
        rep_id = await _actor(db, "sales.view_all", "sales.create_all", "sales.edit_all")
        mgr_id = await _actor(db, "sales.view_all", "sales.approve_all")
        await db.commit()
        rep, mgr = await _load(db, rep_id), await _load(db, mgr_id)

        with pytest.raises(ValidationError):                                     # 10 typed as a percentage = 1000 %
            SOLineCreate(line_no=1, product_id=prod, ordered_quantity=Decimal("5"), unit_price=Decimal("200"), discount_pct=Decimal("10"))

        def order(disc):
            return SOCreate(order_no=f"SO-M41-{uuid4().hex[:10]}", customer_id=cust, order_date=date(2026, 11, 21), requested_delivery_date=date(2026, 11, 28), currency="KES",
                            lines=[SOLineCreate(line_no=1, product_id=prod, ordered_quantity=Decimal("5"), unit_price=Decimal("200"),
                                                discount_pct=disc, tax_rate=Decimal("0.16"))])

        plain = await api.create_order(order(Decimal("0.05")), db, rep)
        assert plain.approval_status is None
        big = await api.create_order(order(Decimal("0.20")), db, rep)   # above the limit even if an earlier test raised it to 15 %
        assert big.approval_status == "PENDING_DISCOUNT"
        with pytest.raises(HTTPException) as e:
            await api.confirm_order(big.id, db, rep)
        assert e.value.status_code == 409
        await db.rollback()
        rep, mgr = await _load(db, rep_id), await _load(db, mgr_id)
        with pytest.raises(HTTPException) as e:
            await api.approve_order_discount(big.id, api.DiscountDecisionIn(), db, rep)
        assert e.value.status_code == 403
        await db.rollback()
        rep, mgr = await _load(db, rep_id), await _load(db, mgr_id)
        seen = await api.get_order(big.id, db, mgr)
        assert seen.access.can_discount_approve is True
        await api.approve_order_discount(big.id, api.DiscountDecisionIn(), db, mgr)
        rep = await _load(db, rep_id)
        done = await api.confirm_order(big.id, db, rep)
        assert done.status == SOStatus.CONFIRMED


@pytest.mark.asyncio
async def test_signer_code_only_to_email_on_file():
    from starlette.requests import Request

    from app.api.v1.endpoints import documents_public as public
    from app.api.v1.endpoints import quotation as api
    from app.models.crm import CRMQuoteDecision, CRMQuoteSignerCode
    from app.models.quotation import Quotation, QuotationLine, QuoteStatus
    from app.services import crm_document_service as docs

    tag = uuid4().hex[:8].upper()
    async with AsyncSessionLocal() as db:
        cust, prod = await _setup(db, tag)
        rep_id = await _actor(db, "sales.view_all", "sales.edit_all", "sales.approve_all")
        q = Quotation(quote_no=f"QS-M41-{tag}", customer_id=cust, status=QuoteStatus.SENT, quote_date=date(2026, 11, 21),
                      valid_until=date(2099, 1, 1), currency="KES", grand_total=Decimal("2000"))
        db.add(q)
        await db.flush()
        db.add(QuotationLine(quote_id=q.id, line_no=1, product_id=prod, qty=Decimal("10"), unit="CTN",
                             unit_price=Decimal("200"), line_total=Decimal("2000")))
        await db.commit()
        rep = await _load(db, rep_id)
        token = (await api.create_share_link(q.id, api.ShareLinkIn(), db, rep))["url"].rsplit("/d/", 1)[1]
        link = await docs.resolve(db, token)
        req = Request({"type": "http", "method": "POST", "path": "/", "headers": [(b"user-agent", b"Safari")], "client": ("41.90.2.2", 5000)})

        stranger = await docs.request_signer_code(db, link, f"someone-{tag}@elsewhere.example")
        assert stranger is None                                                  # not on file: no usable code made
        code = await docs.request_signer_code(db, link, f"Buyer-{tag}@duka.example")
        await db.commit()
        assert code and len(code) == 6
        row = (await db.execute(select(CRMQuoteSignerCode).where(CRMQuoteSignerCode.link_id == link.id,
                                                                 CRMQuoteSignerCode.email != "-"))).scalar_one()
        decoy = (await db.execute(select(CRMQuoteSignerCode.email).where(CRMQuoteSignerCode.link_id == link.id,
                                                                         CRMQuoteSignerCode.id != row.id))).scalar_one()
        assert decoy == "-"                                                      # counted, but the stranger's address is not kept
        row_id, q_id = row.id, q.id
        assert len(row.code_hash) == 64 and row.code_hash != code and row.email == f"buyer-{tag}@duka.example".lower()  # keyed hash only

        doc = await public.shared_document(token, db)

        def body(**over):
            return public.DecisionIn(**{"decision": "ACCEPTED", "signer_name": "Achieng Otieno", "signer_email": f"buyer-{tag}@duka.example",
                                        "document_hash": doc["document_hash"], "agree": True, "code": code, **over})

        wrong = "000000" if code != "000000" else "111111"
        for over in ({"code": ""}, {"code": wrong}, {"signer_email": f"someone-{tag}@elsewhere.example"}):
            with pytest.raises(HTTPException) as e:
                await public.shared_document_decision(token, body(**over), req, db)
            assert e.value.status_code == 409
            await db.rollback()
        link = await docs.resolve(db, token)
        assert (await db.execute(select(CRMQuoteSignerCode.attempts).where(CRMQuoteSignerCode.id == row_id))).scalar_one() == 2
        r = await public.shared_document_decision(token, body(), req, db)
        assert r["decision"] == "ACCEPTED"
        dec = (await db.execute(select(CRMQuoteDecision).where(CRMQuoteDecision.quotation_id == q_id))).scalar_one()
        assert dec.email_verified_at is not None
        rep = await _load(db, rep_id)
        assert (await api.customer_decision(q_id, db, rep))["email_verified_at"] is not None
        used = (await db.execute(select(CRMQuoteSignerCode.used_at).where(CRMQuoteSignerCode.id == row_id))).scalar_one()
        assert used is not None

        # 5 code requests per link per hour, requests for addresses not on file included (2 so far)
        for _ in range(3):
            await docs.request_signer_code(db, link, f"buyer-{tag}@duka.example")
        await db.commit()
        with pytest.raises(docs.DecisionRefused):
            await docs.request_signer_code(db, link, f"someone-{tag}@elsewhere.example")
        await db.rollback()

        # 10 wrong codes across all codes of a link: the link takes no codes for 24 h, even a right one
        from sqlalchemy import update
        link = await docs.resolve(db, token)
        await db.execute(update(CRMQuoteSignerCode).where(CRMQuoteSignerCode.link_id == link.id)
                         .values(created_at=CRMQuoteSignerCode.created_at - __import__("datetime").timedelta(hours=2)))
        await db.commit()
        fresh = await docs.request_signer_code(db, link, f"buyer-{tag}@duka.example")
        await db.execute(update(CRMQuoteSignerCode).where(CRMQuoteSignerCode.id == row_id).values(attempts=10))
        await db.commit()
        link = await docs.resolve(db, token)
        with pytest.raises(docs.DecisionRefused):
            await docs._use_signer_code(db, link, f"buyer-{tag}@duka.example", fresh)
        await db.rollback()
        with pytest.raises(docs.DecisionRefused):
            await docs.request_signer_code(db, await docs.resolve(db, token), f"buyer-{tag}@duka.example")


@pytest.mark.asyncio
async def test_etims_item_codes_reach_payload_and_gaps_block_live(monkeypatch):
    from app.api.v1.endpoints import tax_regulatory as tax
    from app.core.config import settings
    from app.models.master import Product
    from app.models.sales import Invoice, InvoiceLine, InvoiceStatus
    from app.schemas.master import ProductUpdate
    from app.services.etims_connector import build_etims_payload, missing_item_codes

    tag = uuid4().hex[:8].upper()
    async with AsyncSessionLocal() as db:
        cust, prod = await _setup(db, tag)
        other = Product(sku=f"POVU-HANDWASH-500-{tag}", name="POVU Handwash 500 ml", category="HOUSEHOLD")
        db.add(other)
        await db.flush()
        from app.models.sales import SalesOrder
        so = SalesOrder(order_no=f"SO-M41-{tag}", customer_id=cust, order_date=date(2026, 11, 21),
                        requested_delivery_date=date(2026, 11, 28), currency="KES")
        db.add(so)
        await db.flush()
        inv = Invoice(invoice_no=f"INV-M41-{tag}", so_id=so.id, customer_id=cust, invoice_date=date(2026, 11, 21), due_date=date(2026, 12, 21),
                      status=InvoiceStatus.ISSUED, subtotal=Decimal("3000"), tax_amount=Decimal("480"), total_amount=Decimal("3480"))
        db.add(inv)
        await db.flush()
        db.add_all([InvoiceLine(invoice_id=inv.id, product_id=prod, quantity=Decimal("10"), unit_price=Decimal("200"),
                                discount_pct=Decimal("0"), tax_rate=Decimal("0.16"), line_total=Decimal("2320")),
                    InvoiceLine(invoice_id=inv.id, product_id=other.id, quantity=Decimal("10"), unit_price=Decimal("100"),
                                discount_pct=Decimal("0"), tax_rate=Decimal("0"), line_total=Decimal("1000"))])
        with pytest.raises(Exception):
            ProductUpdate(etims_tax_type="VAT")                                  # only A-E
        p = await db.get(Product, prod)
        for k, v in ProductUpdate(etims_item_code="KE1NTXU0000001", etims_item_class_code="47131800").model_dump(exclude_unset=True).items():
            setattr(p, k, v)
        await db.commit()
        inv_id = inv.id

        loaded = (await db.execute(select(Invoice).options(selectinload(Invoice.lines).selectinload(InvoiceLine.product),
                                                           selectinload(Invoice.customer))
                                   .where(Invoice.id == inv_id))).scalar_one()
        items = build_etims_payload(loaded, settings)["itemList"]
        first = next(i for i in items if i["itemNm"] == "POVU AllClean 1 L")
        assert (first["itemCd"], first["itemClsCd"], first["taxTyCd"]) == ("KE1NTXU0000001", "47131800", "B")  # 16 % -> B
        assert missing_item_codes(loaded) == ["POVU Handwash 500 ml"]           # no codes and 0 % is ambiguous (A/C/D)

        monkeypatch.setattr(settings, "ETIMS_PROVIDER", "http")
        user = await _load(db, await _actor(db, "tax_regulatory.edit_all"))
        await db.commit()
        with pytest.raises(HTTPException) as e:
            await tax.submit_etims(inv_id, db, user)
        assert e.value.status_code == 422 and "POVU Handwash 500 ml" in e.value.detail
