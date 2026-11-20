"""M36.S05.T001 journey attribution on disposable PostgreSQL: source precedence, first/last/linear credit,
one journey per customer (no double counting), excluded order states, per-currency revenue and reconciliation."""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal, engine
from app.models.crm import CRMLeadForm, CRMLeadSubmission, CRMRecord, CRMRecordType, CRMSourceType, CRMStatus
from app.models.master import Product, ProductCategory
from app.models.sales import Customer, CustomerChannel, SalesOrder, SOLine, SOStatus
from app.services import crm_attribution_service as attribution

TASK_DB_ENV = "M36_S05_T001_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M36_S05_T001_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m36_s05_t001_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")

D = datetime(2031, 3, 2, 9, 0, tzinfo=timezone.utc)   # a period no other test data falls into


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_attribution_models_and_reconciliation():
    s = uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        c1 = Customer(code=f"AT1-{s}", name="Duka One", channel=CustomerChannel.RETAIL, currency="KES")
        c2 = Customer(code=f"AT2-{s}", name="Duka Two", channel=CustomerChannel.RETAIL, currency="KES")
        c3 = Customer(code=f"AT3-{s}", name="Duka Three", channel=CustomerChannel.RETAIL, currency="KES")
        form = CRMLeadForm(slug=f"lf-{s}", name="Shop sign-up", title="Join POVU")
        prod = Product(sku=f"POVU-ALC-1L-{s}", name="POVU AllClean 1 L", category=list(ProductCategory)[0])
        db.add_all([c1, c2, c3, form, prod])
        await db.flush()
        # journey 1: two form visits (facebook, then google ads) -> opportunity won -> customer c1 with 2 orders (repeat)
        r1 = CRMRecord(record_type=CRMRecordType.OPPORTUNITY, company_name="Duka One", source_type=CRMSourceType.WEBSITE,
                       assigned_customer_id=c1.id, status=CRMStatus.WON, lead_code=f"L1-{s}", opportunity_code=f"O1-{s}")
        # journey 2: no form, field sales -> customer c2 with 1 order in USD
        r2 = CRMRecord(record_type=CRMRecordType.LEAD, company_name="Duka Two", source_type=CRMSourceType.FIELD_SALES,
                       source_detail="Kawangware route", assigned_customer_id=c2.id, lead_code=f"L2-{s}")
        # journey 3: a later record for the same customer c1 -> must not double count c1's orders
        r3 = CRMRecord(record_type=CRMRecordType.LEAD, company_name="Duka One again", source_type=CRMSourceType.REFERRAL,
                       assigned_customer_id=c1.id, lead_code=f"L3-{s}")
        # c3 already belonged to a February record r0; a March record r4 must not take its March orders
        r0 = CRMRecord(record_type=CRMRecordType.LEAD, company_name="Duka Three", source_type=CRMSourceType.EVENT,
                       assigned_customer_id=c3.id, lead_code=f"L0-{s}")
        r4 = CRMRecord(record_type=CRMRecordType.LEAD, company_name="Duka Three", source_type=CRMSourceType.INBOUND,
                       assigned_customer_id=c3.id, lead_code=f"L4-{s}")
        db.add_all([r1, r2, r3, r0, r4])
        await db.flush()
        r1.created_at, r2.created_at, r3.created_at = D, D.replace(hour=10), D.replace(day=5)
        r0.created_at, r4.created_at = D.replace(month=2), D.replace(day=3)
        for when, src, camp in ((D, "facebook", "povu-launch"), (D.replace(hour=12), "google", None)):
            db.add(CRMLeadSubmission(form_id=form.id, received_at=when, status="LEAD", crm_record_id=r1.id,
                                     utm_source=src, utm_campaign=camp))

        def order(cust, day, ccy, qty, price, status=SOStatus.CONFIRMED):
            so = SalesOrder(order_no=f"SO-AT-{s}-{uuid4().hex[:6]}", customer_id=cust.id, order_date=date(2031, 3, day),
                            requested_delivery_date=date(2031, 3, day), currency=ccy, status=status)
            db.add(so)
            return so

        orders = [order(c1, 10, "KES", 10, 210), order(c1, 20, "KES", 5, 210), order(c2, 12, "USD", 4, 25),
                  order(c1, 15, "KES", 99, 210, SOStatus.DRAFT), order(c1, 16, "KES", 99, 210, SOStatus.CANCELLED),
                  order(c1, 1, "KES", 99, 210),    # before the journey started: not counted
                  order(c3, 10, "KES", 7, 100)]    # owned by February's r0: not credited to March's r4
        await db.flush()
        # the USD line has a 10 % discount, stored as a fraction (0.10): 4 x 25 x 0.9 = 90.00
        for so, qty, price, disc in zip(orders, (10, 5, 4, 99, 99, 99, 7), (210, 210, 25, 210, 210, 210, 100),
                                        ("0", "0", "0.10", "0", "0", "0", "0")):
            db.add(SOLine(so_id=so.id, line_no=1, product_id=prod.id, ordered_quantity=Decimal(qty),
                          unit_price=Decimal(price), discount_pct=Decimal(disc)))
        await db.commit()

    async with AsyncSessionLocal() as db:
        first = await attribution.report(db, date(2031, 3, 1), date(2031, 3, 31), "first")
        last = await attribution.report(db, date(2031, 3, 1), date(2031, 3, 31), "last")
        lin = await attribution.report(db, date(2031, 3, 1), date(2031, 3, 31), "linear")

    for rep in (first, last, lin):
        assert rep["reconciled"] is True
        assert rep["totals"] == {"journeys": 4, "customers_with_orders": 2, "orders": 3,
                                 "revenue": {"KES": "3150.00", "USD": "90.00"}}
    by = lambda rep: {r["source"]: r for r in rep["rows"]}  # noqa: E731
    f, l, n = by(first), by(last), by(lin)
    assert f["facebook / povu-launch"]["revenue"] == {"KES": "3150.00"} and f["facebook / povu-launch"]["repeat_customers"] == 1
    assert l["google"]["revenue"] == {"KES": "3150.00"} and "facebook / povu-launch" not in l
    assert n["facebook / povu-launch"]["revenue"] == {"KES": "1575.00"} == n["google"]["revenue"]
    assert f["Field Sales: Kawangware route"]["revenue"] == {"USD": "90.00"}
    assert f["Inbound"]["revenue"] == {} and f["Inbound"]["orders"] == 0             # customer owned by an older record
    assert f["Referral"]["revenue"] == {} and f["Referral"]["orders"] == 0           # later record of c1: no double count
    assert f["facebook / povu-launch"]["won"] == 1 and f["facebook / povu-launch"]["opportunities"] == 1
    with pytest.raises(ValueError):
        await attribution.report(None, date(2031, 3, 1), date(2031, 3, 2), "u-shaped")

    # company filter applies to orders too: another company's order of the same customer is not credited
    from app.models.company import Company
    async with AsyncSessionLocal() as db:
        ca, cb = Company(short_code=f"A{s}", name=f"POVU A {s}"), Company(short_code=f"B{s}", name=f"POVU B {s}")
        cx = Customer(code=f"AX-{s}", name="Duka X", channel=CustomerChannel.RETAIL, currency="KES")
        db.add_all([ca, cb, cx])
        await db.flush()
        rx = CRMRecord(record_type=CRMRecordType.LEAD, company_name="Duka X", source_type=CRMSourceType.CAMPAIGN,
                       assigned_customer_id=cx.id, lead_code=f"LX-{s}", company_id=ca.id)
        db.add(rx)
        await db.flush()
        rx.created_at = datetime(2032, 1, 2, 9, 0, tzinfo=timezone.utc)
        for comp, qty in ((ca, 1), (cb, 50)):
            so = SalesOrder(order_no=f"SO-AX-{s}-{comp.short_code}", customer_id=cx.id, order_date=date(2032, 1, 5),
                            requested_delivery_date=date(2032, 1, 5), currency="KES", status=SOStatus.CONFIRMED, company_id=comp.id)
            db.add(so)
            await db.flush()
            db.add(SOLine(so_id=so.id, line_no=1, product_id=(await db.execute(select(Product.id).where(Product.sku == f"POVU-ALC-1L-{s}"))).scalar_one(),
                          ordered_quantity=Decimal(qty), unit_price=Decimal("100"), discount_pct=Decimal("0")))
        await db.commit()
        rep_a = await attribution.report(db, date(2032, 1, 1), date(2032, 1, 31), "first", str(ca.id))
        assert rep_a["totals"]["revenue"] == {"KES": "100.00"} and rep_a["reconciled"] is True
