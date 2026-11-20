"""Owner 2026-11-20: shops are invoiced when the goods are delivered (and the invoice is e-mailed to them); online
marketplace orders are invoiced when paid, mailed to the buyer, with a paper copy for the parcel."""
from __future__ import annotations

import os
import re
import uuid
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal, engine
from app.models.crm import CRMOutboundMessage
from app.models.finance import AccountingPostingRule, AccountType, ChartOfAccount
from app.models.inventory import Stock, StockType
from app.models.master import Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType
from app.models.sales import (Customer, Invoice, OrderSource, SalesOrder, Shipment, ShipmentLine, ShipmentStatus,
                              SOLine, SOStatus)
from app.models.user import User
from app.services import sales_service
from app.services.invoice_delivery_service import PARCEL_NOTE, invoice_on_delivery, invoice_paid_marketplace_order

TASK_DB_ENV = "M39_INV_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M39_INV_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m39_inv_[a-f0-9]{24}")
pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


async def _dispatched(db, s: str, source: OrderSource, with_rule: bool):
    user = User(email=f"inv-{s}@example.com", username=f"inv{s}", full_name="Desk", hashed_password="x")
    cust = Customer(code=f"C-{s}", name="Mama Shop", email=f"shop-{s}@example.com", payment_terms_days=14)
    prod = Product(sku=f"P-{s}", name="POVU test bottle", category=ProductCategory.OTHER, uom=UnitOfMeasure.PCS)
    wh = Warehouse(code=f"W-{s}", name="FG", warehouse_type=WarehouseType.FINISHED_GOODS)
    db.add_all([user, cust, prod, wh])
    await db.flush()
    if with_rule:
        ar = ChartOfAccount(code=f"AR{s}", name="AR", account_type=AccountType.ASSET, currency="KES")
        rev = ChartOfAccount(code=f"RV{s}", name="Revenue", account_type=AccountType.REVENUE, currency="KES")
        tax = ChartOfAccount(code=f"TX{s}", name="VAT", account_type=AccountType.LIABILITY, currency="KES")
        db.add_all([ar, rev, tax])
        await db.flush()
        db.add(AccountingPostingRule(source_module="sales", source_event="SALES_INVOICE_ISSUED", rule_name="inv",
                                     debit_account_id=ar.id, credit_account_id=rev.id, tax_account_id=tax.id,
                                     priority=1, is_active=True))
    db.add(Stock(stock_type=StockType.PRODUCT, warehouse_id=wh.id, product_id=prod.id, quantity_on_hand=Decimal("10"),
                 quantity_reserved=Decimal("0"), quantity_available=Decimal("10"), is_blocked=False))
    so = SalesOrder(order_no=f"SO-{s}", customer_id=cust.id, order_date=date.today(), requested_delivery_date=date.today(),
                    status=SOStatus.CONFIRMED, currency="KES", source=source)
    db.add(so)
    await db.flush()
    line = SOLine(so_id=so.id, line_no=1, product_id=prod.id, ordered_quantity=Decimal("4"), unit="PCS",
                  unit_price=Decimal("100"), discount_pct=Decimal("0.05"), tax_rate=Decimal("0.16"))
    db.add(line)
    await db.commit()
    await sales_service.allocate_so(db, so, wh.id, user.id)
    await db.commit()
    sh = Shipment(shipment_no=f"SH-{s}", so_id=so.id, warehouse_id=wh.id, status=ShipmentStatus.PENDING,
                  scheduled_date=date.today())
    db.add(sh)
    await db.flush()
    db.add(ShipmentLine(shipment_id=sh.id, so_line_id=line.id, product_id=prod.id, quantity=Decimal("4"), unit="PCS"))
    await db.commit()
    await sales_service.dispatch_shipment(db, sh, date.today(), user.id)
    await db.commit()
    return user, cust, so, sh


def _guard_db():
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
    assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))


@pytest.mark.asyncio
async def test_shop_order_is_invoiced_on_delivery_and_mailed_to_the_shop():
    _guard_db()
    s = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        user, cust, so, sh = await _dispatched(db, s, OrderSource.FIELD_SALES, with_rule=True)
        inv = await invoice_on_delivery(db, sh.id, user.id)
        await db.commit()
        assert inv is not None and inv.shipment_id == sh.id
        assert inv.total_amount == Decimal("440.80")                       # 4 × 100 − 5 % = 380 + 16 % VAT
        assert (inv.due_date - inv.invoice_date).days == 14
        msg = (await db.execute(select(CRMOutboundMessage).where(CRMOutboundMessage.dedupe_key == f"invoice:{inv.id}"))).scalar_one()
        assert msg.purpose == "INVOICE" and msg.to_email == cust.email and msg.status == "QUEUED"
        assert inv.invoice_no in msg.subject and "-5.0%" in msg.body_text and "unsubscribe" not in msg.body_text.lower()
        assert await invoice_on_delivery(db, sh.id, user.id) is None       # once only


@pytest.mark.asyncio
async def test_delivery_never_fails_when_invoicing_cannot_post():
    _guard_db()
    s = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        # an earlier test's rule may exist in this database: deactivate all to simulate "no rule"
        for r in (await db.execute(select(AccountingPostingRule).where(AccountingPostingRule.source_event == "SALES_INVOICE_ISSUED"))).scalars():
            r.is_active = False
        # before finance approves the rule set: the invoice is issued (and mailed), only the ledger entry is missing
        user, _, so, sh = await _dispatched(db, s, OrderSource.MANUAL, with_rule=False)
        inv = await invoice_on_delivery(db, sh.id, user.id)
        assert inv is not None
        await db.commit()
        from app.models.finance import JournalEntry
        assert (await db.execute(select(func.count()).select_from(JournalEntry).where(
            JournalEntry.source_ref == inv.invoice_no))).scalar() == 0

        # after approval (mandatory): no invoice without a rule, and the delivery itself still goes through
        from app.models.utilities import ConfigCategory, SystemConfig
        from app.services.posting_rules_catalog import MANDATORY_KEY
        cfg = (await db.execute(select(SystemConfig).where(SystemConfig.key == MANDATORY_KEY))).scalar_one_or_none()
        if cfg is None:
            cfg = SystemConfig(key=MANDATORY_KEY, category=ConfigCategory.FINANCE, is_editable=False, value="true")
            db.add(cfg)
        cfg.value = "true"
        await db.flush()
        user2, _, so2, sh2 = await _dispatched(db, s + "m", OrderSource.MANUAL, with_rule=False)
        assert await invoice_on_delivery(db, sh2.id, user2.id) is None
        assert (await db.execute(select(func.count()).select_from(Invoice).where(Invoice.so_id == so2.id))).scalar() == 0
        await db.rollback()


@pytest.mark.asyncio
async def test_marketplace_order_is_invoiced_on_payment_with_a_parcel_copy():
    _guard_db()
    s = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        user, _, so, sh = await _dispatched(db, s, OrderSource.ECOMMERCE, with_rule=True)
        assert await invoice_on_delivery(db, sh.id, user.id) is None       # not on delivery
        ar_rule = (await db.execute(select(AccountingPostingRule).where(
            AccountingPostingRule.source_event == "SALES_INVOICE_ISSUED", AccountingPostingRule.is_active.is_(True))
            .order_by(AccountingPostingRule.created_at.desc()).limit(1))).scalar_one()
        bank = ChartOfAccount(code=f"BK{s}", name="Bank", account_type=AccountType.ASSET, currency="KES")
        db.add(bank)
        await db.flush()
        db.add(AccountingPostingRule(source_module="sales", source_event="CUSTOMER_PAYMENT_RECEIVED_BANK", rule_name="bank",
                                     credit_account_id=ar_rule.debit_account_id, clearing_account_id=bank.id,
                                     priority=1, is_active=True))
        await db.flush()
        inv = await invoice_paid_marketplace_order(db, so.id, f"buyer-{s}@example.com", "Ayse", user.id)
        await db.commit()
        assert inv.notes == PARCEL_NOTE and inv.shipment_id is None and inv.total_amount == Decimal("440.80")
        from app.models.sales import InvoiceStatus
        assert inv.status == InvoiceStatus.PAID and inv.paid_amount == Decimal("440.80")   # paid on the marketplace
        msg = (await db.execute(select(CRMOutboundMessage).where(CRMOutboundMessage.dedupe_key == f"invoice:{inv.id}"))).scalar_one()
        assert msg.to_email == f"buyer-{s}@example.com"
        again = await invoice_paid_marketplace_order(db, so.id, f"buyer-{s}@example.com", "Ayse", user.id)
        assert again.id == inv.id                                           # one invoice per paid order
        sh = (await db.execute(select(Shipment).where(Shipment.id == sh.id))).scalar_one()
        with pytest.raises(HTTPException) as e:                             # no second invoice by shipment
            await sales_service.invoice_from_shipment(db, sh, invoice_no=f"X-{s}", invoice_date=date.today(),
                                                      due_date=date.today(), user_id=user.id)
        assert e.value.status_code == 422


@pytest.mark.asyncio
async def test_shop_promotion_is_separate_from_price_and_shows_on_the_invoice():
    """Same list price for every shop; a 5 % promotion only for this shop is listed for it, written as a line
    discount on its order, and named on the invoice e-mail. Another shop sees neither."""
    from datetime import timedelta

    from app.models.promotions import PromoEligibility, PromoRuleLine, PromoScheme, RewardType, SchemeStatus, SchemeType, TriggerBasis
    from app.services.shop_promotions import apply_to_order, customer_promotions

    _guard_db()
    s = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        user, cust, so, sh = await _dispatched(db, s, OrderSource.DISTRIBUTOR, with_rule=True)
        other = Customer(code=f"O-{s}", name="Other shop")
        db.add(other)
        scheme = PromoScheme(scheme_code=f"PR-{s}", scheme_name="Mama Shop 5% November", scheme_type=SchemeType.PERCENT_DISCOUNT,
                             status=SchemeStatus.ACTIVE, valid_from=date.today() - timedelta(days=1),
                             valid_to=date.today() + timedelta(days=30), priority_rank=1)
        db.add(scheme)
        await db.flush()
        db.add(PromoEligibility(scheme_id=scheme.id, applies_to_customer_id=cust.id, active=True))
        db.add(PromoRuleLine(scheme_id=scheme.id, trigger_basis=TriggerBasis.ORDER_TOTAL, min_trigger_qty=Decimal("0"),
                             min_trigger_value=Decimal("0"), reward_type=RewardType.PERCENT_DISCOUNT, reward_percent=Decimal("5")))
        await db.commit()

        mine = [p for p in await customer_promotions(db, cust) if p["code"] == f"PR-{s}"]
        assert mine and mine[0]["only_for_you"] and mine[0]["offers"] == ["5% off the order"]
        assert not [p for p in await customer_promotions(db, other) if p["code"] == f"PR-{s}"]

        line = (await db.execute(select(SOLine).where(SOLine.so_id == so.id))).scalar_one()
        line.discount_pct = Decimal("0")
        await db.flush()
        names = await apply_to_order(db, so, cust)
        await db.commit()
        line = (await db.execute(select(SOLine).where(SOLine.so_id == so.id))).scalar_one()
        assert line.unit_price == Decimal("100") and line.discount_pct == Decimal("0.0500")   # list price kept
        assert names == ["Mama Shop 5% November: 5% off the order"]

        inv = await invoice_on_delivery(db, sh.id, user.id)
        await db.commit()
        assert "Promotion: Mama Shop 5% November" in inv.notes
        msg = (await db.execute(select(CRMOutboundMessage).where(CRMOutboundMessage.dedupe_key == f"invoice:{inv.id}"))).scalar_one()
        assert "Promotions applied" in msg.body_text and "Mama Shop 5% November" in msg.body_text and "-5.0%" in msg.body_text


@pytest.mark.asyncio
async def test_provider_keys_entered_in_the_app_are_encrypted_masked_and_applied(monkeypatch):
    from app.core.config import settings
    from app.models.utilities import SystemConfig
    from app.services import provider_credentials as pc

    for attr in ("MPESA_CONSUMER_KEY", "MPESA_CONSUMER_SECRET", "MPESA_SHORTCODE", "MPESA_PASSKEY", "MPESA_ENV"):
        monkeypatch.setattr(settings, attr, getattr(settings, attr))   # restored after the test
    _guard_db()
    async with AsyncSessionLocal() as db:
        await pc.save(db, "mpesa", {"environment": "sandbox", "shortcode": "174379", "consumer_key": "ck-test-1",
                                    "consumer_secret": "cs-test-1", "passkey": "pk-test-1"}, None)
        await db.commit()
        assert settings.MPESA_CONSUMER_KEY == "ck-test-1" and settings.MPESA_SHORTCODE == "174379"
        raw = (await db.execute(select(SystemConfig.value).where(SystemConfig.key == "provider_credentials.mpesa"))).scalar_one()
        assert "ck-test-1" not in raw and "pk-test-1" not in raw                     # encrypted at rest
        mpesa = next(p for p in await pc.status(db) if p["provider"] == "mpesa")
        assert mpesa["configured"]
        secret = next(f for f in mpesa["fields"] if f["field"] == "passkey")
        assert secret["is_set"] and secret["value"] is None                         # never sent back
        await pc.save(db, "mpesa", {"passkey": "", "shortcode": "600000"}, None)   # blank secret keeps the old one
        await db.commit()
        assert settings.MPESA_PASSKEY == "pk-test-1" and settings.MPESA_SHORTCODE == "600000"
        with pytest.raises(HTTPException):
            await pc.save(db, "mpesa", {"environment": "live"}, None)


@pytest.mark.asyncio
async def test_customer_notice_is_skipped_quietly_without_a_provider(monkeypatch):
    from app.core.config import settings
    from app.services.customer_messaging import notify_customer

    monkeypatch.setattr(settings, "WHATSAPP_ACCESS_TOKEN", "")
    monkeypatch.setattr(settings, "SMS_PROVIDER", "")
    assert await notify_customer("+254700000001", "on the way") == "not-configured"
    assert await notify_customer(None, "on the way") == "no-phone"
