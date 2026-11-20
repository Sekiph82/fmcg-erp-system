"""M36.S02.T005 bounce handling on disposable PostgreSQL: a delivery status report (RFC 3464) that arrives
in a connected mailbox marks the address BOUNCED only when it names a CRM e-mail we actually sent;
forged or temporary reports change nothing."""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal, engine
from app.models.crm import CRMContactConsent, CRMOutboundMessage
from app.models.email_integration import EmailAccount, EmailProvider
from app.services import email_mailbox_service as mbx

TASK_DB_ENV = "M36_S02_T005B_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M36_S02_T005B_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m36_s02_t005b_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def dsn(report_id: str, recipient: str, original_id: str, status: str = "5.1.1", action: str = "failed") -> bytes:
    lines = [
        "From: Mail Delivery Subsystem <mailer-daemon@mx.shops.example>",
        "To: marketing@povu.example",
        "Subject: Delivery Status Notification (Failure)",
        f"Message-ID: {report_id}",
        "Date: Sat, 21 Nov 2026 08:00:00 +0300",
        "MIME-Version: 1.0",
        'Content-Type: multipart/report; report-type=delivery-status; boundary="BOUND"',
        "",
        "--BOUND",
        "Content-Type: text/plain",
        "",
        f"Delivery to {recipient} failed permanently.",
        "",
        "--BOUND",
        "Content-Type: message/delivery-status",
        "",
        "Reporting-MTA: dns; mx.shops.example",
        "",
        f"Final-Recipient: rfc822; {recipient}",
        f"Action: {action}",
        f"Status: {status}",
        "",
        "--BOUND",
        "Content-Type: text/rfc822-headers",
        "",
        "From: marketing@povu.example",
        f"To: {recipient}",
        "Subject: New POVU AllClean 1 L price",
        f"Message-ID: {original_id}",
        "",
        "--BOUND--",
        "",
    ]
    return "\r\n".join(lines).encode()


@pytest.mark.asyncio
async def test_bounce_reports_suppress_only_real_sends():
    s = uuid4().hex[:8]
    gone, other, temp = f"gone-{s}@shops.example", f"other-{s}@shops.example", f"busy-{s}@shops.example"
    p = mbx.parse(dsn("<r0@x>", gone, "<c1@povu.example>"))
    assert p.bounces == [(gone, "5.1.1")] and p.bounced_message_id == "<c1@povu.example>"

    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        now = datetime.now(timezone.utc)
        acc = EmailAccount(provider=EmailProvider.SMTP, email_address=f"marketing-{s}@povu.example")
        db.add(acc)
        for addr, mid in ((gone, f"<c1-{s}@povu.example>"), (temp, f"<c3-{s}@povu.example>")):
            db.add(CRMOutboundMessage(dedupe_key=f"camp:{s}:{addr}", purpose="CAMPAIGN", to_email=addr, subject="New price",
                                      body_text="b", status="SENT", attempts=1, next_attempt_at=now, created_at=now,
                                      sent_at=now, provider_message_id=mid))
        await db.flush()

        # real permanent bounce of a mail we sent -> BOUNCED, reason on the outbox row
        await mbx.store(db, acc, mbx.parse(dsn(f"<r1-{s}@x>", gone, f"<c1-{s}@povu.example>")))
        # forged report: the Message-ID was never sent by us (or sent to someone else) -> nothing
        await mbx.store(db, acc, mbx.parse(dsn(f"<r2-{s}@x>", other, f"<forged-{s}@povu.example>")))
        await mbx.store(db, acc, mbx.parse(dsn(f"<r3-{s}@x>", other, f"<c1-{s}@povu.example>")))
        # temporary failure (4.x.x / delayed) -> nothing
        await mbx.store(db, acc, mbx.parse(dsn(f"<r4-{s}@x>", temp, f"<c3-{s}@povu.example>", "4.2.2", "delayed")))
        await db.commit()

        consents = dict((await db.execute(select(CRMContactConsent.email, CRMContactConsent.status)
                                          .where(CRMContactConsent.email.in_([gone, other, temp])))).all())
        assert consents == {gone: "BOUNCED"}
        row = (await db.execute(select(CRMOutboundMessage).where(CRMOutboundMessage.to_email == gone))).scalar_one()
        assert row.status_reason == "bounced (5.1.1)"
