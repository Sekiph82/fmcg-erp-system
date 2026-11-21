"""M40.S01.T001 customer feedback and loyalty on disposable PostgreSQL: portal NPS (general + per delivered order),
one-time public survey links, staff route guards, loyalty points once per fully paid invoice and the portal summary."""
from __future__ import annotations

import os
import re
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import func, select
from starlette.requests import Request

from app.api.v1.endpoints import loyalty as loyalty_ep
from app.api.v1.endpoints import nps as nps_ep
from app.db.session import AsyncSessionLocal, engine
from app.models.master import Warehouse, WarehouseType
from app.models.loyalty import CustomerLoyaltyAccount, LoyaltyTier, LoyaltyTransaction
from app.models.nps import NPSResponse, NPSSurvey
from app.models.sales import (Customer, CustomerChannel, Invoice, InvoiceStatus, SalesOrder, Shipment,
                              ShipmentStatus)
from app.services import customer_feedback_service as fb

TASK_DB_ENV = "M40_S01_T001_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M40_S01_T001_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m40_s01_t001_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _user(*codes):
    perms = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in codes]
    return SimpleNamespace(id=uuid4(), is_superuser=False, access_scopes=[], company_id=None,
                           roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])


def _req(method):
    return Request({"type": "http", "method": method, "path": "/", "headers": []})


@pytest.mark.asyncio
async def test_feedback_links_guards_and_loyalty():
    s = uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]

        a = Customer(code=f"FA-{s}", name=f"Mama Duka {s}", channel=CustomerChannel.DISTRIBUTOR, currency="KES")
        b = Customer(code=f"FB-{s}", name=f"Other Shop {s}", channel=CustomerChannel.DISTRIBUTOR, currency="KES")
        wh = Warehouse(code=f"FW-{s}", name=f"FG {s}", warehouse_type=WarehouseType.FINISHED_GOODS)
        general = NPSSurvey(title=f"How likely {s}", target_type="CUSTOMER", trigger="MANUAL",
                            question_text="How likely are you to recommend POVU to another shop?")
        delivery = NPSSurvey(title=f"Delivery {s}", target_type="CUSTOMER", trigger="DELIVERY",
                             question_text="How was your POVU delivery?")
        db.add_all([a, b, wh, general, delivery])
        await db.flush()
        so = SalesOrder(order_no=f"SO-F-{s}", customer_id=a.id, order_date=date.today(), requested_delivery_date=date.today(), currency="KES")
        so_b = SalesOrder(order_no=f"SO-FB-{s}", customer_id=b.id, order_date=date.today(), requested_delivery_date=date.today(), currency="KES")
        db.add_all([so, so_b])
        await db.flush()
        db.add(Shipment(shipment_no=f"SH-F-{s}", so_id=so.id, warehouse_id=wh.id, status=ShipmentStatus.DELIVERED,
                        scheduled_date=date.today()))
        await db.commit()

        # portal: one general survey + one per delivered order; other customers' orders never appear
        items = await fb.open_surveys(db, a.id)
        mine = {(i["survey_id"], i["so_id"]) for i in items}
        assert (str(general.id), None) in mine and (str(delivery.id), str(so.id)) in mine
        assert all(i["so_id"] != str(so_b.id) for i in items)
        await fb.answer(db, a.id, delivery.id, so.id, 9, "Driver was on time with the POVU AllClean cartons", "portal")
        await db.commit()
        with pytest.raises(fb.FeedbackError) as e:             # answered once only
            await fb.answer(db, a.id, delivery.id, so.id, 3, None, "portal")
        assert e.value.status == 409
        with pytest.raises(fb.FeedbackError) as e:             # cannot answer for another customer's order
            await fb.answer(db, a.id, delivery.id, so_b.id, 3, None, "portal")
        assert e.value.status == 409
        with pytest.raises(fb.FeedbackError) as e:
            await fb.answer(db, a.id, general.id, None, 11, None, "portal")
        assert e.value.status == 422
        assert (str(delivery.id), str(so.id)) not in {(i["survey_id"], i["so_id"]) for i in await fb.open_surveys(db, a.id)}

        # one-time public link: order must belong to the customer; answered once; token stored hashed only
        with pytest.raises(fb.FeedbackError):
            await fb.create_link(db, general.id, a.id, so_b.id, None)
        token = await fb.create_link(db, general.id, b.id, None, None)
        await db.commit()
        assert (await fb.public_survey(db, token))["answered"] is False
        await fb.public_answer(db, token, 10, "Great")
        await db.commit()
        with pytest.raises(fb.FeedbackError) as e:
            await fb.public_answer(db, token, 2, None)
        assert e.value.status == 409
        await db.rollback()
        for obj in (a, b, so, general):
            await db.refresh(obj)
        with pytest.raises(fb.FeedbackError) as e:
            await fb.public_survey(db, "not-a-real-token-" + s)
        assert e.value.status == 404
        assert (await db.execute(select(func.count()).select_from(NPSResponse).where(NPSResponse.customer_id == b.id,
                                                                                   NPSResponse.channel == "link"))).scalar_one() == 1

        # staff routes: reads need sales/CRM view, changes need edit (any signed-in user could before)
        with pytest.raises(HTTPException):
            await loyalty_ep._guard(_req("POST"), _user("crm.view"))
        with pytest.raises(HTTPException):
            await nps_ep._guard(_req("GET"), _user("hr.view"))
        await loyalty_ep._guard(_req("GET"), _user("sales.view"))
        await nps_ep._guard(_req("POST"), _user("crm.edit"))

        # loyalty: not enrolled → nothing; enrolled → points once per fully paid invoice, tier follows
        inv = Invoice(invoice_no=f"INV-F-{s}", so_id=so.id, customer_id=a.id, currency="KES", invoice_date=date.today(),
                      due_date=date.today(), status=InvoiceStatus.PAID, total_amount=Decimal("25000"), subtotal=Decimal("25000"))
        db.add(inv)
        await db.flush()
        assert await fb.award_invoice_points(db, inv) == 0
        assert (await fb.loyalty_summary(db, a.id)) == {"enrolled": False}
        bronze = LoyaltyTier(tier_code=f"BR-{s}", tier_name="Bronze", min_lifetime_points=0, points_per_100_spend=Decimal("1"))
        silver = LoyaltyTier(tier_code=f"SI-{s}", tier_name="Silver", min_lifetime_points=200, points_per_100_spend=Decimal("2"))
        db.add_all([bronze, silver])
        await db.flush()
        db.add(CustomerLoyaltyAccount(customer_id=a.id, tier_id=bronze.id, total_points=0, lifetime_points=0))
        await db.commit()
        assert await fb.award_invoice_points(db, inv) == 250
        assert await fb.award_invoice_points(db, inv) == 0          # once per invoice
        await db.commit()
        summary = await fb.loyalty_summary(db, a.id)
        assert summary["balance"] == 250 and summary["tier"] == "Silver" and summary["history"][0]["points"] == 250
        assert "INV-F-" in summary["history"][0]["description"]
        assert (await db.execute(select(func.count()).select_from(LoyaltyTransaction).where(
            LoyaltyTransaction.reference_id == str(inv.id)))).scalar_one() == 1
