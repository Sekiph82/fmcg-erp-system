"""M36.S01.T001 two-way e-mail on disposable PostgreSQL with a fake IMAP/SMTP server: login test before
connect, encrypted password, import with dedupe / threading / attachment metadata / customer link /
unsubscribe, idempotent replay and UIDVALIDITY reset, SMTP reply headers, failed delivery stores
nothing, disconnect, personal mailboxes."""
from __future__ import annotations

import os
import re
from email.message import EmailMessage as Mime
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import func, select

from app.api.v1.endpoints import email_integration as api
from app.db.session import AsyncSessionLocal, engine
from app.models.crm import CRMContactConsent
from app.models.email_integration import EmailAccount, EmailMessage, EmailProvider, EmailThread
from app.models.sales import Customer, CustomerChannel
from app.models.user import User
from app.schemas.email_integration import EmailAccountCreate, MailboxSettings, SendEmailRequest
from app.services import email_mailbox_service as mbx

TASK_DB_ENV = "M36_S01_T001_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M36_S01_T001_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m36_s01_t001_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


class FakeServer:
    """Stands in for the IMAP/SMTP host: one mailbox, one password."""

    def __init__(self, password):
        self.password, self.validity, self.inbox, self.sent, self.fail_send, self.fetches = password, 7, [], [], False, 0

    def check_login(self, ih, ip, sh, sp, user, password):
        if password != self.password:
            raise mbx.MailboxError("IMAP login failed: authentication failed")

    def fetch_new(self, host, port, user, password, validity, last_uid):
        self.fetches += 1
        self.check_login(host, port, host, port, user, password)
        start = (last_uid or 0) + 1 if validity == self.validity else 1
        return self.validity, [(u, raw) for u, raw in self.inbox if u >= start]

    def smtp_send(self, host, port, user, password, mime):
        if self.fail_send:
            raise mbx.MailboxError("Sending failed: 554 rejected")
        self.sent.append(mime)


def _mail(mid, sender, to, subject, body, reply_to=None, attach=False, auth=None):
    m = Mime()
    m["Message-ID"], m["From"], m["To"], m["Subject"] = mid, sender, to, subject
    m["Date"] = "Fri, 20 Nov 2026 09:00:00 +0300"
    if auth:
        m["Authentication-Results"] = auth
    if reply_to:
        m["In-Reply-To"], m["References"] = reply_to, reply_to
    m.set_content(body)
    if attach:
        m.add_attachment(b"%PDF-1.4 order", maintype="application", subtype="pdf", filename="LPO-POVU.pdf")
    return m.as_bytes()


def _user(uid, superuser=False):
    return SimpleNamespace(id=uid, is_superuser=superuser, full_name="Rep", roles=[], access_scopes=[])


@pytest.mark.asyncio
async def test_mailbox_connect_import_send_disconnect(monkeypatch):
    s = uuid4().hex[:8]
    box = f"sales-{s}@povu.example"
    duka = f"duka-{s}@shops.example"
    srv = FakeServer("app-password-1")
    for name in ("check_login", "fetch_new", "smtp_send"):
        monkeypatch.setattr(mbx, name, getattr(srv, name))
    real_validate = mbx.validate_host
    # IP literals go through the real check (no DNS needed); provider host names are trusted offline
    monkeypatch.setattr(mbx, "validate_host", lambda h, p, ports: real_validate(h, p, ports) if h[0].isdigit() else None)
    for host, port in (("127.0.0.1", 993), ("10.1.2.3", 993), ("169.254.169.254", 993), ("8.8.8.8", 6379)):
        with pytest.raises(mbx.MailboxError):
            real_validate(host, port, mbx.IMAP_PORTS)
    tampered = mbx.encrypt("x")[:-4] + "AAAA"
    with pytest.raises(mbx.MailboxError, match="connect the mailbox again"):
        mbx.decrypt(tampered)

    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        rep = User(email=f"mb-{s}@example.invalid", username=f"mb{s}", full_name="Rep", hashed_password="x")
        other = User(email=f"mb2-{s}@example.invalid", username=f"mb2{s}", full_name="Other", hashed_password="x")
        cust = Customer(code=f"MB-{s}", name="Mama Duka", channel=CustomerChannel.RETAIL, currency="KES", email=duka)
        db.add_all([rep, other, cust])
        await db.commit()
        me, them, cust_id = _user(rep.id), _user(other.id), cust.id

        # wrong password: refused, nothing stored
        with pytest.raises(HTTPException) as e:
            await api.add_account(EmailAccountCreate(provider=EmailProvider.GMAIL, email_address=box, password="wrong"), db, me)
        assert e.value.status_code == 422
        await db.rollback()
        assert (await db.execute(select(func.count()).select_from(EmailAccount).where(EmailAccount.email_address == box))).scalar_one() == 0
        # an internal address is refused before any login attempt
        with pytest.raises(HTTPException) as e:
            await api.add_account(EmailAccountCreate(provider=EmailProvider.SMTP, email_address=box, password="app-password-1",
                                                     imap_host="127.0.0.1", imap_port=993, smtp_host="10.0.0.9", smtp_port=465), db, me)
        assert e.value.status_code == 422 and "public" in e.value.detail
        await db.rollback()

        acc = await api.add_account(EmailAccountCreate(provider=EmailProvider.GMAIL, email_address=box, password="app-password-1"), db, me)
        assert acc.connected and acc.imap_host == "imap.gmail.com" and acc.smtp_port == 465
        row = await db.get(EmailAccount, acc.id)
        assert row.secret_enc and "app-password-1" not in row.secret_enc and mbx.decrypt(row.secret_enc) == "app-password-1"
        acc_id = acc.id

    srv.inbox = [
        (1, _mail(f"<o1-{s}@shops>", f"Mama Duka <{duka}>", box, "Order: POVU AllClean 1 L x 20", "20 cartons please", attach=True)),
        (2, _mail(f"<o2-{s}@shops>", duka, box, "Re: Order: POVU AllClean 1 L x 20", "Friday delivery ok?", reply_to=f"<o1-{s}@shops>")),
        (3, _mail(f"<o1-{s}@shops>", duka, box, "Order: POVU AllClean 1 L x 20", "duplicate delivery of message 1")),
        (4, _mail(f"<u1-{s}@x>", f"promo-{s}@x.example", box, "Re: unsubscribe", "stop",
                  auth="mx.povu.example; dkim=pass header.d=x.example; spf=pass")),
        (5, _mail(f"<u2-{s}@x>", f"victim-{s}@y.example", box, "Unsubscribe", "forged From, no authentication")),
        (6, _mail(f"<bad-{s}@x>", duka, box, "BROKEN", "this one fails to import")),
        (7, _mail(f"<nul-{s}@x>", duka, box, "Price list", "baby wipes" + chr(0) + " please")),
    ]
    real_store = mbx.store

    async def flaky_store(db, acc, p):
        if p.subject == "BROKEN":
            raise RuntimeError("simulated bad message")
        return await real_store(db, acc, p)

    monkeypatch.setattr(mbx, "store", flaky_store)
    async with AsyncSessionLocal() as db:
        r = await api.sync_mailbox(acc_id, db, me)
        assert (r["imported"], r["skipped"], r["failed"]) == (5, 1, 1)   # one bad message does not block the rest
        assert (await db.get(EmailAccount, acc_id)).imap_last_uid == 7
        assert not (await db.execute(select(CRMContactConsent).where(CRMContactConsent.email == f"victim-{s}@y.example"))).first()
        nul = (await db.execute(select(EmailMessage).where(EmailMessage.external_message_id == f"<nul-{s}@x>"))).scalar_one()
        assert chr(0) not in nul.body_text
        threads = (await db.execute(select(EmailThread).where(EmailThread.account_id == acc_id))).scalars().all()
        order = next(t for t in threads if t.subject.startswith("Order"))
        assert len(threads) == 4 and order.message_count == 2 and not order.is_read
        assert (order.linked_module, order.linked_object_id) == ("customer", cust_id)        # sender is a customer
        msgs = (await db.execute(select(EmailMessage).where(EmailMessage.thread_id == order.id)
                                 .order_by(EmailMessage.external_message_id))).scalars().all()
        assert msgs[0].attachments == [{"name": "LPO-POVU.pdf", "type": "application/pdf", "size": 14}]
        consent = (await db.execute(select(CRMContactConsent).where(CRMContactConsent.email == f"promo-{s}@x.example"))).scalar_one()
        assert consent.status == "UNSUBSCRIBED"                                              # DKIM-verified reply
        order_id = order.id

        # replay and a mailbox rebuilt on the server (new UIDVALIDITY): nothing doubles
        assert (await api.sync_mailbox(acc_id, db, me))["imported"] == 0
        srv.validity = 8
        assert (await api.sync_mailbox(acc_id, db, me))["imported"] == 0
        assert (await db.execute(select(func.count()).select_from(EmailMessage).join(EmailThread)
                                 .where(EmailThread.account_id == acc_id))).scalar_one() == 5

        # reply goes out through SMTP with threading headers and is stored in the thread
        req = SendEmailRequest(account_id=acc_id, to_emails=[duka], subject="Re: Order: POVU AllClean 1 L x 20",
                               body_text="Yes, Friday.", thread_id=order_id)
        out = await api.send_email(req, db, me)
        mime = srv.sent[-1]
        assert mime["In-Reply-To"] == f"<o2-{s}@shops>" and f"<o1-{s}@shops>" in mime["References"]
        assert out.message_count == 3 and not out.messages[-1].is_inbound

        # failed delivery: error, nothing stored
        srv.fail_send = True
        with pytest.raises(HTTPException) as e:
            await api.send_email(req, db, me)
        assert e.value.status_code == 502
        await db.rollback()
        assert (await db.get(EmailThread, order_id)).message_count == 3
        srv.fail_send = False

        # wrong password on the server: sync error kept on the account
        srv.password = "rotated"
        with pytest.raises(HTTPException) as e:
            await api.sync_mailbox(acc_id, db, me)
        assert e.value.status_code == 502
        assert "authentication failed" in (await db.get(EmailAccount, acc_id)).sync_error
        with pytest.raises(HTTPException):
            await api.connect_account(acc_id, MailboxSettings(password="wrong-again"), db, me)
        await api.connect_account(acc_id, MailboxSettings(password="rotated"), db, me)

        # thread list and re-linking serialise without lazy loads; a link must point at a real customer
        listed = await api.list_threads(None, None, acc_id, False, 0, 50, db, me)
        assert {t.id for t in listed} >= {order_id} and all(t.messages == [] for t in listed)
        with pytest.raises(HTTPException) as e:
            await api.link_thread(order_id, "customer", uuid4(), None, db, me)
        assert e.value.status_code == 422
        await db.rollback()
        assert (await api.link_thread(order_id, "customer", cust_id, "Mama Duka", db, me)).linked_object_id == cust_id

        # personal mailbox: another user cannot reach it
        for call in (lambda: api.sync_mailbox(acc_id, db, them), lambda: api.send_email(req, db, them)):
            with pytest.raises(HTTPException) as e:
                await call()
            assert e.value.status_code == 404

        # disconnect: password erased, no sync, no sending
        await api.remove_account(acc_id, db, me)
        acc = await db.get(EmailAccount, acc_id)
        assert acc.secret_enc is None and not acc.is_active and not mbx.is_connected(acc)
        before = srv.fetches
        await mbx.sync_all(db)
        assert srv.fetches == before
        with pytest.raises(HTTPException) as e:
            await api.send_email(req, db, me)
        assert e.value.status_code == 404
