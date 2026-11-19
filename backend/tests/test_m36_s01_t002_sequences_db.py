"""M36.S01.T002 sales sequences on disposable PostgreSQL: delays, personalisation, one message per step
(double ticks), consent, reply stop, unsubscribe stop, won stop, pause, automation enrolment."""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal, engine
from app.models.crm import (
    CRMOutboundMessage, CRMRecord, CRMRecordType, CRMSequence, CRMSequenceEnrollment, CRMSequenceStep, CRMStatus,
)
from app.models.email_integration import EmailAccount, EmailProvider, EmailThread, EmailMessage
from app.services import crm_outbound_service as outbound
from app.services import crm_sequence_service as seqs

TASK_DB_ENV = "M36_S01_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M36_S01_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m36_s01_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_sequence_steps_stop_conditions_and_dedupe():
    s = uuid4().hex[:8]
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        seq = CRMSequence(name=f"Onboard {s}")
        db.add(seq)
        await db.flush()
        db.add_all([
            CRMSequenceStep(sequence_id=seq.id, step_no=1, delay_days=0, subject="Hello {contact_name}",
                            body="Thanks {contact_name} from {company_name}. {unknown} {0}"),
            CRMSequenceStep(sequence_id=seq.id, step_no=2, delay_days=3, subject="Following up", body="Price list attached."),
        ])
        leads = {}
        for key in ("happy", "replier", "quitter", "winner", "cold"):
            email = f"{key}-{s}@example.com"
            leads[key] = CRMRecord(record_type=CRMRecordType.LEAD, company_name=f"{key.title()} Shop {s}",
                                   contact_person_name=key.title(), contact_email=email)
            if key != "cold":
                await outbound.record_consent(db, email, "SUBSCRIBED", "form:test", "ok")
        db.add_all(list(leads.values()))
        nomail = CRMRecord(record_type=CRMRecordType.LEAD, company_name=f"No mail {s}")
        db.add(nomail)
        await db.flush()
        enr = {k: await seqs.enroll(db, seq, r, "tester") for k, r in leads.items()}
        with pytest.raises(ValueError, match="no contact e-mail"):
            await seqs.enroll(db, seq, nomail, "tester")
        assert (await seqs.enroll(db, seq, leads["happy"], "tester")).id == enr["happy"].id  # no double enrolment
        await db.commit()
        ids = {k: v.id for k, v in enr.items()}
        lead_ids = {k: v.id for k, v in leads.items()}

    async with AsyncSessionLocal() as db:
        first = await seqs.advance(db, now=now + timedelta(minutes=1))
        again = await seqs.advance(db, now=now + timedelta(minutes=2))           # second tick, same moment
        assert first["queued"] == 4 and first["stopped"] == 1 and again["queued"] == 0
        msgs = (await db.execute(select(CRMOutboundMessage).where(CRMOutboundMessage.purpose == "SEQUENCE",
                CRMOutboundMessage.to_email.like(f"%-{s}@example.com")))).scalars().all()
        assert len(msgs) == 5                                                      # 4 queued + 1 suppressed (cold)
        happy_1 = next(m for m in msgs if m.to_email.startswith("happy"))
        assert happy_1.subject == "Hello Happy" and happy_1.body_text.startswith(f"Thanks Happy from Happy Shop {s}.")
        cold = await db.get(CRMSequenceEnrollment, ids["cold"])
        assert (cold.status, cold.stop_reason) == ("STOPPED", "no marketing consent on record")

        # before step 2: one replies, one unsubscribes, one wins the deal
        acct = EmailAccount(provider=list(EmailProvider)[0], email_address=f"rep-{s}@example.com")
        db.add(acct)
        await db.flush()
        th = EmailThread(account_id=acct.id, subject="Re: Hello")
        db.add(th)
        await db.flush()
        db.add(EmailMessage(thread_id=th.id, from_email=f"Replier-{s}@Example.com", to_emails=[], subject="Re: Hello",
                            received_at=now + timedelta(days=1), is_inbound=True))
        await outbound.record_consent(db, f"quitter-{s}@example.com", "UNSUBSCRIBED", "unsubscribe-link")
        (await db.get(CRMRecord, lead_ids["winner"])).status = CRMStatus.WON
        await db.commit()

        assert (await seqs.advance(db, now=now + timedelta(days=2)))["queued"] == 0  # step 2 not due yet
        result = await seqs.advance(db, now=now + timedelta(days=3, minutes=5))
        assert (result["queued"], result["stopped"], result["errors"]) == (1, 3, 0)
        states = {k: await db.get(CRMSequenceEnrollment, i) for k, i in ids.items()}
        for st in states.values():
            await db.refresh(st)
        assert states["happy"].status == "COMPLETED"
        assert (states["replier"].stop_reason, states["quitter"].stop_reason, states["winner"].stop_reason) == (
            "contact replied", "address is unsubscribed", "record is won")
        step2 = (await db.execute(select(func.count()).select_from(CRMOutboundMessage).where(
            CRMOutboundMessage.dedupe_key.like("seq:%:2"), CRMOutboundMessage.status == "QUEUED",
            CRMOutboundMessage.to_email.like(f"%-{s}@example.com")))).scalar()
        assert step2 == 1


@pytest.mark.asyncio
async def test_automation_rule_enrolls_new_leads():
    from app.models.custom_fields import EntityType, WorkflowTriggerRule
    from app.services import crm_automation_service as auto

    s = uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        seq = CRMSequence(name=f"Auto {s}")
        db.add(seq)
        await db.flush()
        db.add(CRMSequenceStep(sequence_id=seq.id, step_no=1, delay_days=1, subject="Hi", body="Hi"))
        db.add(WorkflowTriggerRule(rule_name=f"Enroll web leads {s}", entity_type=EntityType.CRM_RECORD, trigger_event="created",
                                   action_type="enroll_in_sequence", action_payload={"sequence_id": str(seq.id)},
                                   active_flag=True, created_at=datetime.utcnow() - timedelta(seconds=5)))
        lead = CRMRecord(record_type=CRMRecordType.LEAD, company_name=f"Auto lead {s}", contact_email=f"auto-{s}@example.com")
        db.add(lead)
        await db.commit()
        await auto.enqueue(db)
        await auto.process(db)
        row = (await db.execute(select(CRMSequenceEnrollment).where(CRMSequenceEnrollment.crm_record_id == lead.id))).scalar_one()
        assert (row.status, row.enrolled_by, row.next_step_no) == ("ACTIVE", "automation", 1)
