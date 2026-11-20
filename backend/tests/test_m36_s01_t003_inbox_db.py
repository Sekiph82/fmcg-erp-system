"""M36.S01.T003 unified conversations inbox on disposable PostgreSQL: channel ingestion, duplicate
events, unread state, assignment/status, reopen on a new customer message, and visibility
(personal mailboxes, channel permissions, company separation)."""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal, engine
from app.models.company import Company
from app.models.crm import CRMConversation
from app.models.email_integration import EmailAccount, EmailMessage, EmailProvider, EmailThread
from app.models.helpdesk import HelpdeskTicket, TicketStatus
from app.models.sales import Customer, CustomerChannel
from app.models.user import User
from app.models.whatsapp import WAMessageDirection, WhatsAppConfig, WhatsAppMessage
from app.services import crm_inbox_service as inbox

TASK_DB_ENV = "M36_S01_T003_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M36_S01_T003_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m36_s01_t003_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _user(uid, *codes, superuser=False, company_id=None):
    perms = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in codes]
    return SimpleNamespace(id=uid, is_superuser=superuser, access_scopes=[], company_id=company_id,
                           roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])


async def _mine(db, user, refs, **kw):
    out = await inbox.list_conversations(db, user, **kw)
    return {i["subject"]: i for i in out["items"] if i["subject"] in refs}


@pytest.mark.asyncio
async def test_inbox_ingests_dedupes_tracks_unread_and_scopes():
    s = uuid4().hex[:8]
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        owner = User(email=f"ib-{s}@example.invalid", username=f"ib{s}", full_name="Rep", hashed_password="x")
        other = User(email=f"ib2-{s}@example.invalid", username=f"ib2{s}", full_name="Other", hashed_password="x")
        co_a = Company(short_code=f"A{s}", name=f"POVU A {s}")
        co_b = Company(short_code=f"B{s}", name=f"POVU B {s}")
        db.add_all([owner, other, co_a, co_b])
        await db.flush()
        cust_a = Customer(code=f"IA-{s}", name="Duka A", channel=CustomerChannel.RETAIL, currency="KES", company_id=co_a.id)
        cust_b = Customer(code=f"IB-{s}", name="Duka B", channel=CustomerChannel.RETAIL, currency="KES", company_id=co_b.id)
        mailbox = EmailAccount(provider=list(EmailProvider)[0], email_address=f"rep-{s}@example.invalid", created_by_id=owner.id)
        wa = WhatsAppConfig(display_name=f"POVU WA {s}")
        db.add_all([cust_a, cust_b, mailbox, wa])
        await db.flush()
        thread = EmailThread(account_id=mailbox.id, subject=f"POVU AllClean price {s}", participants=[f"duka-{s}@example.invalid"],
                             linked_module="customer", linked_object_id=cust_a.id, last_message_at=now - timedelta(hours=30))
        db.add(thread)
        await db.flush()
        db.add_all([
            EmailMessage(thread_id=thread.id, from_email=f"duka-{s}@example.invalid", to_emails=[mailbox.email_address],
                         subject=thread.subject, received_at=now - timedelta(hours=30), is_inbound=True),
            WhatsAppMessage(config_id=wa.id, direction=WAMessageDirection.INBOUND, phone=f"+2547{s[:8]}", contact_name="Mama Duka",
                            body="2 cartons POVU-ALC-1L please", linked_module="customer", linked_object_id=cust_b.id),
            HelpdeskTicket(ticket_no=f"TKT-{s}", subject="Broken caps", customer_id=cust_a.id, sla_hours=4),
        ])
        await db.commit()
        ids = SimpleNamespace(owner=owner.id, other=other.id, a=co_a.id, b=co_b.id, wa=wa.id, thread=thread.id, s=s)

    email_subj, wa_subj, tkt_subj = f"POVU AllClean price {s}", "WhatsApp Mama Duka", f"TKT-{s}: Broken caps"
    refs = {email_subj, wa_subj, tkt_subj}
    admin = _user(ids.owner, superuser=True)

    async with AsyncSessionLocal() as db:
        seen = await _mine(db, admin, refs)
        assert set(seen) == refs                                   # all three channels ingested
        assert seen[email_subj]["sla_overdue"] and seen[email_subj]["unread"]
        assert seen[tkt_subj]["sla_due_at"] is not None
        await inbox.sync(db)                                       # replayed sync: no duplicates
        await db.commit()
        n = (await db.execute(select(func.count()).select_from(CRMConversation)
                              .where(CRMConversation.subject.in_(refs)))).scalar_one()
        assert n == 3

    # duplicate WhatsApp delivery (same number) stays one conversation
    async with AsyncSessionLocal() as db:
        db.add(WhatsAppMessage(config_id=ids.wa, direction=WAMessageDirection.INBOUND, phone=f"+2547{s[:8]}",
                               contact_name="Mama Duka", body="2 cartons POVU-ALC-1L please"))
        await db.commit()
        await _mine(db, admin, refs)
        assert (await db.execute(select(func.count()).select_from(CRMConversation)
                                 .where(CRMConversation.source_ref.like(f"{ids.wa}:%")))).scalar_one() == 1

    # a link to a customer that does not exist neither breaks the inbox nor escapes the company filter;
    # a deleted source disappears from the index
    async with AsyncSessionLocal() as db:
        mb = (await db.execute(select(EmailAccount).where(EmailAccount.created_by_id == ids.owner))).scalar_one()
        bogus = EmailThread(account_id=mb.id, subject=f"Bogus link {s}", linked_module="customer", linked_object_id=uuid4(),
                            last_message_at=now)
        db.add(bogus)
        await db.commit()
        assert f"Bogus link {s}" in await _mine(db, admin, refs | {f"Bogus link {s}"})
        row = (await db.execute(select(CRMConversation).where(CRMConversation.subject == f"Bogus link {s}"))).scalar_one()
        assert row.customer_id is None
        await db.delete(await db.get(EmailThread, bogus.id))
        await db.commit()
        assert f"Bogus link {s}" not in await _mine(db, admin, refs | {f"Bogus link {s}"})

    # visibility: personal mailbox, channel permissions, company separation
    rep = _user(ids.owner, "crm.view")
    stranger = _user(ids.other, "crm.view")
    quality = _user(ids.other, "crm.view_own_scope", "quality.view")
    rep_b = _user(ids.owner, "crm.view", company_id=ids.b)
    async with AsyncSessionLocal() as db:
        assert set(await _mine(db, rep, refs)) == {email_subj, wa_subj}
        assert set(await _mine(db, stranger, refs)) == {wa_subj}             # not someone else's mailbox
        assert set(await _mine(db, quality, refs)) == {tkt_subj}             # tickets need quality.view
        assert set(await _mine(db, rep_b, refs)) == {wa_subj}                # company A customers hidden

    # unread per user, assignment, status, reopen
    async with AsyncSessionLocal() as db:
        conv = (await db.execute(select(CRMConversation).where(CRMConversation.subject == email_subj))).scalar_one()
        tkt = (await db.execute(select(CRMConversation).where(CRMConversation.subject == tkt_subj))).scalar_one()
        await inbox.mark_read(db, rep, conv)
        await inbox.assign(db, conv, ids.other)
        inbox.set_status(conv, "CLOSED")
        with pytest.raises(ValueError):
            inbox.set_status(tkt, "CLOSED")
        await inbox.assign(db, tkt, ids.other)
        await db.commit()
        conv_id = conv.id
    async with AsyncSessionLocal() as db:
        assert not (await _mine(db, rep, refs, status="CLOSED"))[email_subj]["unread"]
        assert set(await _mine(db, stranger, refs, view="mine", status="CLOSED")) == {email_subj}  # assignee sees it
        ticket = (await db.execute(select(HelpdeskTicket).where(HelpdeskTicket.ticket_no == f"TKT-{s}"))).scalar_one()
        assert ticket.assigned_to_id == ids.other                            # ticket follows the inbox
        before = (await db.execute(select(CRMConversation.last_message_at).where(CRMConversation.subject == tkt_subj))).scalar_one()
        await inbox.sync(db)
        after = (await db.execute(select(CRMConversation.last_message_at).where(CRMConversation.subject == tkt_subj))).scalar_one()
        assert after == before                                               # assignment is not a new message
        ticket.status = TicketStatus.CLOSED
        db.add(EmailMessage(thread_id=ids.thread, from_email=f"duka-{s}@example.invalid", to_emails=[], subject="re",
                            received_at=datetime.now(timezone.utc) + timedelta(seconds=5), is_inbound=True))
        await db.commit()
    async with AsyncSessionLocal() as db:
        open_items = await _mine(db, rep, refs)
        assert open_items[email_subj]["unread"] and open_items[email_subj]["status"] == "OPEN"   # reopened
        assert open_items[email_subj]["assignee_id"] == str(ids.other)                        # kept
        assert tkt_subj not in await _mine(db, admin, refs)                                    # closed ticket
        conv = await db.get(CRMConversation, conv_id)
        assert conv.closed_at is None
