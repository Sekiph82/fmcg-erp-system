"""M43.S01.T007 quotas and forecast on disposable PostgreSQL (run at the M43 gate, M43_S01_DB=1).

Synthetic KES/USD targets: actual = confirmed orders only (drafts/cancelled excluded), net of discount, never
mixing currencies (USD order reported as excluded on a KES quota); forecast categories derived from probability
with override; projection follows assumptions; snapshots store assumptions; rep sees only own quota; CSV export.
"""
from __future__ import annotations

import os
import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(os.environ.get("M43_S01_DB") != "1",
              reason="requires the task-owned disposable PostgreSQL at the M43 head")]


@pytest.fixture
async def world():
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMRecord, CRMRecordType, CRMStatus, SalesQuota
    from app.models.master import Product
    from app.models.sales import Customer, SalesOrder, SOLine, SOStatus
    from app.models.user import User
    async with AsyncSessionLocal() as db:
        rep = User(id=uuid.uuid4(), email=f"rep-{uuid.uuid4().hex[:6]}@povu-demo.test", hashed_password="x",
                   full_name="Synthetic Rep", is_active=True)
        db.add(rep)
        cust = (await db.execute(select(Customer).limit(1))).scalar_one()
        prod = (await db.execute(select(Product).limit(1))).scalar_one()

        def order(status, cur, qty, price, disc="0"):
            so = SalesOrder(id=uuid.uuid4(), order_no=f"SYN-{uuid.uuid4().hex[:8]}", customer_id=cust.id,
                            order_date=date(2026, 12, 10), requested_delivery_date=date(2026, 12, 12), status=status,
                            currency=cur, created_by_id=rep.id)
            so.lines = [SOLine(line_no=1, product_id=prod.id, ordered_quantity=Decimal(qty), unit_price=Decimal(price),
                               discount_pct=Decimal(disc), tax_rate=Decimal("0.16"))]
            return so
        db.add_all([order(SOStatus.CONFIRMED, "KES", "10", "1000", "0.1"),     # 9 000 net
                    order(SOStatus.INVOICED, "KES", "1", "1000"),              # 1 000
                    order(SOStatus.DRAFT, "KES", "100", "1000"),               # excluded (draft)
                    order(SOStatus.CANCELLED, "KES", "100", "1000"),           # excluded
                    order(SOStatus.CONFIRMED, "USD", "1", "500")])             # other currency
        def deal(prob, amount, cur="KES", cat=None):
            return CRMRecord(id=uuid.uuid4(), record_type=CRMRecordType.OPPORTUNITY, company_name="POVU Synthetic Outlet",
                             status=CRMStatus.OPEN, probability_pct=prob, expected_revenue=amount, currency=cur,
                             expected_close_date=date(2026, 12, 20), assigned_rep_id=str(rep.id), forecast_category=cat)
        db.add_all([deal(95, 10000), deal(60, 20000), deal(20, 50000), deal(95, 99999, "USD"), deal(95, 7777, cat="OMITTED")])
        q = SalesQuota(id=uuid.uuid4(), scope_type="REP", scope_ref=str(rep.id), period_type="MONTH",
                       period_start=date(2026, 12, 1), period_end=date(2026, 12, 31), currency="KES", target_amount=40000)
        db.add(q)
        await db.commit()
        yield db, rep, q


async def test_attainment_currency_and_categories(world):
    from app.services import quota_service as quotas
    db, rep, q = world
    a = await quotas.attainment(db, q)
    assert a["actual"] == 10000.0
    assert (a["commit"], a["best_case"], a["pipeline"], a["omitted"]) == (10000.0, 20000.0, 50000.0, 7777.0)
    assert a["projected"] == pytest.approx(10000 + 10000 + 10000 + 5000)
    assert a["excluded_other_currency"] == {"orders": {"USD": 500.0}, "deals": 1}
    b = await quotas.attainment(db, q, {"commit": 1, "best_case": 0, "pipeline": 0})
    assert b["projected"] == 20000.0
    s = await quotas.snapshot(db, q, {"best_case": 0.25})
    await db.commit()
    assert s.assumptions["best_case"] == 0.25 and float(s.actual_amount) == 10000.0
