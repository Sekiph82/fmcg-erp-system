"""M36.S01.T002 automated sales sequences on the native CRM and the consent-aware outbox.

An enrolment walks a record through the sequence steps; each due step is queued in the outbox as a
SEQUENCE message with dedupe key "seq:<enrolment>:<step>" (so a step is never queued twice, even across
workers or retries). Before every step the enrolment stops if the contact replied (an inbound e-mail from
the address after enrolment, or a rep marked a reply), unsubscribed/bounced, or the record is no longer
open. Consent is enforced by the outbox: without SUBSCRIBED consent the message is stored SUPPRESSED and the
enrolment stops. Delivery rate limits live in the outbox."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm import CRMRecord, CRMSequence, CRMSequenceEnrollment, CRMSequenceStep, CRMStatus
from app.models.email_integration import EmailMessage
from app.services import crm_outbound_service as outbound

logger = logging.getLogger(__name__)
PER_TICK = 100


_PLACEHOLDER = re.compile(r"\{(\w+)\}")


def render(text: str, record: CRMRecord) -> str:
    """Fill {contact_name} and {company_name}; any other {word} is removed (never attribute access, never
    internal ids such as the owner id)."""
    values = {"contact_name": record.contact_person_name or "", "company_name": record.company_name or ""}
    return _PLACEHOLDER.sub(lambda m: values.get(m.group(1), ""), text)


async def enroll(db: AsyncSession, sequence: CRMSequence, record: CRMRecord, by: Optional[str]) -> CRMSequenceEnrollment:
    """Caller commits. Raises ValueError when the record cannot be enrolled."""
    if not record.contact_email:
        raise ValueError("record has no contact e-mail")
    if record.status != CRMStatus.OPEN:
        raise ValueError("only open records can be enrolled")
    existing = (await db.execute(select(CRMSequenceEnrollment).where(
        CRMSequenceEnrollment.sequence_id == sequence.id, CRMSequenceEnrollment.crm_record_id == record.id))).scalar_one_or_none()
    if existing is not None:
        if existing.status == "ACTIVE":
            return existing
        raise ValueError(f"record already went through this sequence ({existing.status.lower()})")
    first = (await db.execute(select(CRMSequenceStep).where(CRMSequenceStep.sequence_id == sequence.id)
                              .order_by(CRMSequenceStep.step_no).limit(1))).scalar_one_or_none()
    if first is None:
        raise ValueError("sequence has no steps")
    from uuid import uuid4

    from sqlalchemy.dialects.postgresql import insert

    now = datetime.now(timezone.utc)
    # insert-or-skip: two concurrent enrolments of the same record end with one row, never a 500
    await db.execute(insert(CRMSequenceEnrollment).values(
        id=uuid4(), sequence_id=sequence.id, crm_record_id=record.id, email=outbound.norm(record.contact_email),
        status="ACTIVE", next_step_no=first.step_no, next_due_at=now + timedelta(days=first.delay_days),
        enrolled_by=by, enrolled_at=now).on_conflict_do_nothing(constraint="uq_crm_sequence_enrollment"))
    return (await db.execute(select(CRMSequenceEnrollment).where(
        CRMSequenceEnrollment.sequence_id == sequence.id, CRMSequenceEnrollment.crm_record_id == record.id))).scalar_one()


def _stop(e: CRMSequenceEnrollment, reason: str, now: datetime) -> None:
    e.status, e.stop_reason, e.finished_at = "STOPPED", reason[:200], now


async def _replied(db: AsyncSession, e: CRMSequenceEnrollment) -> bool:
    return (await db.execute(select(EmailMessage.id).where(
        EmailMessage.is_inbound.is_(True), EmailMessage.received_at >= e.enrolled_at,
        func.lower(EmailMessage.from_email) == e.email).limit(1))).first() is not None


async def _advance_one(db: AsyncSession, e: CRMSequenceEnrollment, now: datetime) -> str:
    record = await db.get(CRMRecord, e.crm_record_id)
    sequence = await db.get(CRMSequence, e.sequence_id)
    if record is None or record.status != CRMStatus.OPEN:
        _stop(e, f"record is {getattr(getattr(record, 'status', None), 'value', 'deleted').lower()}", now)
        return "stopped"
    if sequence is None:
        _stop(e, "sequence deleted", now)
        return "stopped"
    if record.contact_email and outbound.norm(record.contact_email) != e.email:
        e.email = outbound.norm(record.contact_email)  # the rep corrected the address: follow it
    if await _replied(db, e):
        _stop(e, "contact replied", now)
        return "stopped"
    step = (await db.execute(select(CRMSequenceStep).where(
        CRMSequenceStep.sequence_id == e.sequence_id, CRMSequenceStep.step_no == e.next_step_no))).scalar_one_or_none()
    if step is None:
        e.status, e.finished_at = "COMPLETED", now
        return "completed"
    msg = await outbound.queue(db, to_email=e.email, subject=render(step.subject, record), body=render(step.body, record),
                               purpose="SEQUENCE", dedupe_key=f"seq:{e.id}:{step.step_no}",
                               crm_record_id=record.id, created_by=f"sequence:{sequence.name}"[:100],
                               track=bool(sequence.track_engagement))
    if msg.status == "SUPPRESSED":
        _stop(e, msg.status_reason or "suppressed", now)
        return "stopped"
    e.stop_reason = None
    nxt = (await db.execute(select(CRMSequenceStep).where(
        CRMSequenceStep.sequence_id == e.sequence_id, CRMSequenceStep.step_no > step.step_no)
        .order_by(CRMSequenceStep.step_no).limit(1))).scalar_one_or_none()
    if nxt is None:
        e.status, e.finished_at = "COMPLETED", now
        return "queued"
    e.next_step_no, e.next_due_at = nxt.step_no, now + timedelta(days=nxt.delay_days)
    return "queued"


async def advance(db: AsyncSession, now: Optional[datetime] = None) -> dict:
    """Queue due steps (SKIP LOCKED: concurrent workers take different enrolments). Commits."""
    now = now or datetime.now(timezone.utc)
    due = (await db.execute(select(CRMSequenceEnrollment)
        .join(CRMSequence, CRMSequence.id == CRMSequenceEnrollment.sequence_id)
        .where(CRMSequenceEnrollment.status == "ACTIVE", CRMSequenceEnrollment.next_due_at <= now,
               CRMSequence.active_flag.is_(True))  # paused sequences wait without blocking the others
        .order_by(CRMSequenceEnrollment.next_due_at).limit(PER_TICK)
        .with_for_update(skip_locked=True, of=CRMSequenceEnrollment))).scalars().all()
    counts = {"queued": 0, "stopped": 0, "completed": 0, "errors": 0}
    for e in due:
        try:
            async with db.begin_nested():  # one bad enrolment never blocks the others
                counts[await _advance_one(db, e, now)] += 1
        except Exception as exc:
            logger.exception("sequence enrolment %s could not advance", e.id)
            e.next_due_at = now + timedelta(hours=1)  # try again later, others keep moving
            e.stop_reason = f"error: {exc.__class__.__name__}"[:200]
            counts["errors"] += 1
    await db.commit()
    return counts
