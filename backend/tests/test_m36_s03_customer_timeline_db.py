"""M36.S03.T002 unified customer timeline on disposable PostgreSQL: chronology across native sources,
cursor pagination without gaps or repeats, per-source permissions and personal mailboxes."""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal, engine
from app.models.crm import CRMActivity, CRMActivityResult, CRMRecord, CRMRecordType
from app.models.email_integration import EmailAccount, EmailProvider, EmailThread
from app.models.helpdesk import HelpdeskTicket
from app.models.marketing import CRMProfile, CustomerInteraction
from app.models.quotation import Quotation
from app.models.sales import Customer, CustomerChannel, Invoice, Payment, SalesOrder
from app.models.user import User
from app.models.voip import CallLog
from app.services import customer_timeline_service as tl

TASK_DB_ENV = "M36_S03_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M36_S03_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m36_s03_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _user(uid, *codes, superuser=False):
    perms = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in codes]
    return SimpleNamespace(id=uid, is_superuser=superuser, access_scopes=[],
                           roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])


@pytest.mark.asyncio
async def test_timeline_orders_pages_and_hides_by_permission():
    s = uuid4().hex[:8]
    t0 = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        owner = User(email=f"tl-{s}@example.invalid", username=f"tl{s}", full_name="Rep", hashed_password="x")
        other = User(email=f"tl2-{s}@example.invalid", username=f"tl2{s}", full_name="Other", hashed_password="x")
        cust = Customer(code=f"TL-{s}", name="Timeline customer", channel=CustomerChannel.RETAIL, currency="KES")
        db.add_all([owner, other, cust])
        await db.flush()
        rec = CRMRecord(record_type=CRMRecordType.OPPORTUNITY, company_name="Timeline customer", assigned_customer_id=cust.id)
        db.add(rec)
        await db.flush()
        rec.created_at = t0
        so = SalesOrder(order_no=f"SO-TL-{s}", customer_id=cust.id, order_date=date(2026, 10, 4),
                        requested_delivery_date=date(2026, 10, 9))
        db.add(so)
        await db.flush()
        inv = Invoice(invoice_no=f"INV-TL-{s}", so_id=so.id, customer_id=cust.id, invoice_date=date(2026, 10, 6),
                      due_date=date(2026, 11, 6))
        db.add(inv)
        await db.flush()
        profile = CRMProfile(customer_id=cust.id)
        mailbox = EmailAccount(provider=list(EmailProvider)[0], email_address=f"rep-{s}@example.invalid", created_by_id=owner.id)
        db.add_all([profile, mailbox])
        await db.flush()
        db.add_all([
            CRMActivity(crm_record_id=rec.id, activity_type="CALL",
                        subject="Intro call", result_status=CRMActivityResult.COMPLETED,
                        completed_datetime=(t0 + timedelta(days=1)).replace(tzinfo=None)),
            Quotation(quote_no=f"Q-TL-{s}", customer_id=cust.id, quote_date=date(2026, 10, 3)),
            Payment(invoice_id=inv.id, payment_date=date(2026, 10, 8), amount=Decimal("100")),
            HelpdeskTicket(ticket_no=f"T-TL-{s}", subject="Leaking cap", customer_id=cust.id),
            CallLog(call_ref=f"C-TL-{s}", phone_number="+254700000001", customer_id=cust.id, started_at=(t0 + timedelta(days=2, hours=3)).replace(tzinfo=None)),
            CustomerInteraction(crm_profile_id=profile.id, interaction_date=date(2026, 10, 5), channel="visit", summary="Shelf check"),
            EmailThread(account_id=mailbox.id, subject="Price list", linked_object_id=cust.id,
                        last_message_at=t0 + timedelta(days=7)),
        ])
        await db.commit()
        cid, owner_id, other_id = cust.id, owner.id, other.id

    async with AsyncSessionLocal() as db:
        everyone = _user(owner_id, superuser=True)
        full = await tl.timeline(db, cid, everyone, limit=100)
        kinds = [e["type"] for e in full["events"]]
        assert set(kinds) >= {"crm_record", "crm_activity", "quote", "order", "invoice", "payment", "ticket", "call",
                              "interaction", "email"}
        ats = [e["at"] for e in full["events"]]
        assert ats == sorted(ats, reverse=True) and full["next"] is None

        # cursor paging: same events, no gaps, no repeats
        seen, cursor = [], None
        while True:
            page = await tl.timeline(db, cid, everyone, limit=3, before=cursor)
            seen += [e["key"] for e in page["events"]]
            cursor = page["next"]
            if not cursor:
                break
        assert seen == [e["key"] for e in full["events"]]

        # CRM-only user: sales and tickets hidden, someone else's mailbox not shown
        crm_only = await tl.timeline(db, cid, _user(other_id, "crm.view"), limit=100)
        assert {"sales", "tickets"} <= set(crm_only["hidden_sources"])
        assert not {"order", "invoice", "payment", "quote", "ticket", "email"} & {e["type"] for e in crm_only["events"]}
        assert {"crm_record", "call", "interaction"} <= {e["type"] for e in crm_only["events"]}
        mine = await tl.timeline(db, cid, _user(owner_id, "crm.view"), limit=100)
        assert "email" in {e["type"] for e in mine["events"]}  # own mailbox is visible

        only_orders = await tl.timeline(db, cid, everyone, limit=100, types={"order"})
        assert [e["type"] for e in only_orders["events"]] == ["order"]
