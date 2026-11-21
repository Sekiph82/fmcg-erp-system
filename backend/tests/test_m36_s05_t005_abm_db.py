"""M36.S05.T005 account-based marketing on disposable PostgreSQL: target-account groups and tiers, buying committees,
engagement from recorded rows only, coordinated consent-aware campaign (idempotent), attribution and rights."""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import func, select

from app.api.v1.endpoints import crm_abm as api
from app.db.session import AsyncSessionLocal, engine
from app.models.crm import CRMAccountGroup, CRMOutboundMessage
from app.models.master import Product, ProductCategory
from app.models.meetings import MeetingRecord
from app.models.sales import Customer, CustomerChannel, SalesOrder, SOLine
from app.models.user import User

TASK_DB_ENV = "M36_S05_T005_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M36_S05_T005_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m36_s05_t005_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _user(uid, *codes):
    perms = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in codes]
    return SimpleNamespace(id=uid, username="mkt", is_superuser=False, access_scopes=[],
                           roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])


@pytest.mark.asyncio
async def test_abm_flow():
    s = uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        u = User(email=f"abm-{s}@povu.example", username=f"abm{s}", full_name="Key Accounts", hashed_password="x")
        chain = Customer(code=f"KA-{s}", name=f"Naivas-like Chain {s}", channel=CustomerChannel.DISTRIBUTOR, currency="KES")
        other = Customer(code=f"KB-{s}", name=f"Other Chain {s}", channel=CustomerChannel.DISTRIBUTOR, currency="KES")
        prod = Product(sku=f"POVU-LD-{s}", name=f"POVU Liquid Detergent 1L {s}", category=ProductCategory.HOUSEHOLD)
        db.add_all([u, chain, other, prod])
        await db.commit()
        mkt = _user(u.id, "marketing.edit")
        viewer = _user(u.id, "marketing.view")
        chain_id, other_id, prod_id = chain.id, other.id, prod.id

        # rights: viewers read, only editors change
        with pytest.raises(HTTPException):
            await api.WRITE(viewer)
        with pytest.raises(HTTPException):
            await api.WRITE(_user(u.id, "marketing.create"))
        await api.READ(viewer)
        with pytest.raises(HTTPException):
            await api.READ(_user(u.id, "sales.view"))   # a plain sales right does not open key-account lists

        g = await api.create_group(api.GroupIn(name=f"Strategic chains {s}"), db, mkt)
        gid = __import__("uuid").UUID(g["id"])
        with pytest.raises(HTTPException) as e:
            await api.create_group(api.GroupIn(name=f"Strategic chains {s}"), db, mkt)
        assert e.value.status_code == 409
        await api.add_member(gid, api.MemberIn(customer_id=chain_id, tier=1), db, mkt)
        await api.add_member(gid, api.MemberIn(customer_id=chain_id, tier=2), db, mkt)       # re-add updates the tier
        with pytest.raises(HTTPException):
            await api.add_member(gid, api.MemberIn(customer_id=uuid4()), db, mkt)

        # buying committee; same e-mail twice is refused
        await api.add_contact(chain_id, api.ContactIn(full_name="Grace Buyer", email=f"grace-{s}@chain.example", committee_role="BUYER"), db, mkt)
        await api.add_contact(chain_id, api.ContactIn(full_name="David Director", email=f"david-{s}@chain.example", committee_role="DECISION_MAKER"), db, mkt)
        with pytest.raises(HTTPException) as e:
            await api.add_contact(chain_id, api.ContactIn(full_name="Dup", email=f"GRACE-{s}@chain.example"), db, mkt)
        assert e.value.status_code == 409

        # engagement counts only recorded rows: one meeting and one order for this account
        db.add(MeetingRecord(title="Q1 range review", customer_id=chain_id, scheduled_at=datetime.utcnow(), host_id=mkt.id))
        so = SalesOrder(order_no=f"SO-KA-{s}", customer_id=chain_id, order_date=date.today(), requested_delivery_date=date.today(), currency="KES")
        db.add(so)
        await db.flush()
        db.add(SOLine(so_id=so.id, line_no=1, product_id=prod_id, ordered_quantity=Decimal("10"), unit_price=Decimal("250")))
        await db.commit()
        ov = await api.get_group(gid, 90, db, viewer)
        acc = ov["accounts"][0]
        assert acc["tier"] == 2 and acc["contacts"] == 2 and acc["meetings"] == 1 and acc["orders"] == 1 and acc["order_value"] == 2500.0
        assert acc["key_roles_missing"] == ["CHAMPION"] and acc["emails_sent"] == 0
        assert ov["attribution"] is None                                    # no campaign yet

        from app.models.crm import CRMContactConsent
        db.add(CRMContactConsent(email=f"grace-{s}@chain.example", status="SUBSCRIBED", source="test", updated_at=datetime.now(timezone.utc)))
        await db.commit()
        # coordinated campaign: one message per committee address through the outbox; running it again adds nothing
        out = await api.group_campaign(gid, api.CampaignIn(subject="New POVU range for {company_name}", body="Hello {contact_name}, ...", roles=None), db, mkt)
        assert out == {"queued": 1, "suppressed": 1}           # David has no marketing consent → suppressed, never sent
        again = await api.group_campaign(gid, api.CampaignIn(subject="New POVU range for {company_name}", body="Hello {contact_name}, ...", roles=None), db, mkt)
        assert again == out
        msgs = (await db.execute(select(CRMOutboundMessage).where(CRMOutboundMessage.customer_id == chain_id))).scalars().all()
        assert len(msgs) == 2 and all(m.purpose == "CAMPAIGN" for m in msgs)
        assert all(m.status in ("QUEUED", "SUPPRESSED") for m in msgs)        # the outbox applies consent before sending
        assert any("Grace Buyer" in m.body_text for m in msgs)
        with pytest.raises(HTTPException):
            await api.group_campaign(gid, api.CampaignIn(subject="x x x", body="0123456789", roles=["CEO"]), db, mkt)

        ov = await api.get_group(gid, 90, db, viewer)
        assert ov["attribution"]["orders"] == 1 and ov["attribution"]["order_value"] == 2500.0
        assert other_id not in [a["customer_id"] for a in ov["accounts"]]
        await api.remove_member(gid, chain_id, db, mkt)
        assert (await api.get_group(gid, 90, db, viewer))["accounts"] == []
